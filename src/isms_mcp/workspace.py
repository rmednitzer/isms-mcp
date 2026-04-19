"""Workspace root: discovery, canonicalisation, hardened safe reads.

The single most security-sensitive module in the project. Every filesystem
access for ISMS content goes through ``WorkspaceRoot.safe_read_text``,
``WorkspaceRoot.safe_iterdir``, or ``WorkspaceRoot.safe_rglob``; these
methods reject paths that resolve outside the four allow-listed subtrees
after symlink resolution.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from isms_mcp.exceptions import PathEscape, WorkspaceNotConfigured

ALLOWED_SUBTREES = ("docs", "template", "instance", "framework-refs")


@dataclass(frozen=True)
class WorkspaceRoot:
    """Canonicalised, allow-listed view of an ISMS workspace."""

    root: Path
    allowed_prefixes: tuple[Path, ...]

    @classmethod
    def from_env(cls, value: str | None = None) -> WorkspaceRoot:
        raw = value if value is not None else os.environ.get("ISMS_MCP_WORKSPACE")
        if not raw:
            raise WorkspaceNotConfigured("ISMS_MCP_WORKSPACE environment variable is not set.")
        try:
            root = Path(raw).resolve(strict=True)
        except FileNotFoundError as exc:
            raise WorkspaceNotConfigured(f"workspace path does not exist: {raw}") from exc
        if not root.is_dir():
            raise WorkspaceNotConfigured(f"workspace path is not a directory: {root}")
        prefixes: list[Path] = []
        for sub in ALLOWED_SUBTREES:
            prefix = (root / sub).resolve()
            if not prefix.is_relative_to(root):
                raise WorkspaceNotConfigured(
                    f"allow-listed subtree escapes workspace root: {sub} -> {prefix}"
                )
            prefixes.append(prefix)
        return cls(root=root, allowed_prefixes=tuple(prefixes))

    def _resolve_inside(self, rel_path: str | Path) -> Path:
        """Resolve ``rel_path`` against the workspace and verify allow-list.

        Rejections:
          * absolute paths
          * paths containing a NUL byte
          * non-existent targets (``strict=True`` raises ``FileNotFoundError``)
          * resolved paths outside any allow-listed subtree
          * symlinks whose targets escape the allow-list (caught by the same
            check, because ``resolve()`` follows symlinks)
        """
        if isinstance(rel_path, str) and "\x00" in rel_path:
            raise PathEscape("path contains NUL byte")
        rel = Path(rel_path)
        if rel.is_absolute():
            raise PathEscape(f"absolute path not permitted: {rel_path}")
        try:
            candidate = (self.root / rel).resolve(strict=True)
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"workspace file not found: {rel}") from exc
        for prefix in self.allowed_prefixes:
            try:
                if candidate.is_relative_to(prefix):
                    return candidate
            except ValueError:
                continue
        raise PathEscape(f"path escapes workspace allow-list: {rel}")

    def safe_read_text(self, rel_path: str | Path) -> str:
        """Read text from a workspace-relative path, with allow-list enforcement."""
        target = self._resolve_inside(rel_path)
        if not target.is_file():
            raise FileNotFoundError(f"not a regular file: {rel_path}")
        with open(target, encoding="utf-8") as fh:
            return fh.read()

    def exists(self, rel_path: str | Path) -> bool:
        """Return True if ``rel_path`` resolves to an existing path inside the allow-list."""
        try:
            self._resolve_inside(rel_path)
            return True
        except (PathEscape, FileNotFoundError):
            return False

    def safe_iterdir(self, rel_path: str | Path) -> Iterator[Path]:
        """Iterate immediate children of a workspace-relative directory.

        Each yielded path is verified to live inside the allow-list. Symlinks
        whose targets escape are silently dropped.
        """
        target = self._resolve_inside(rel_path)
        if not target.is_dir():
            raise NotADirectoryError(f"not a directory: {rel_path}")
        for child in target.iterdir():
            try:
                resolved = child.resolve(strict=True)
            except FileNotFoundError:
                continue
            for prefix in self.allowed_prefixes:
                try:
                    if resolved.is_relative_to(prefix):
                        yield resolved
                        break
                except ValueError:
                    continue

    def safe_rglob(self, rel_path: str | Path, pattern: str) -> Iterator[Path]:
        """Recursive glob below ``rel_path``, allow-list enforced per yielded path."""
        target = self._resolve_inside(rel_path)
        if not target.is_dir():
            raise NotADirectoryError(f"not a directory: {rel_path}")
        for child in target.rglob(pattern):
            try:
                resolved = child.resolve(strict=True)
            except FileNotFoundError:
                continue
            for prefix in self.allowed_prefixes:
                try:
                    if resolved.is_relative_to(prefix):
                        yield resolved
                        break
                except ValueError:
                    continue

    def read_git_head(self) -> str | None:  # noqa: PLR0911
        """Best-effort read of ``.git/HEAD``; tolerate absence and shallow forms.

        Never shells out. Reads the plain text of ``.git/HEAD`` and, if it is
        a symbolic ref (``ref: refs/heads/main``), reads the dereferenced ref
        file. Returns ``None`` if anything goes wrong.
        """
        git_dir = (self.root / ".git").resolve()
        if not git_dir.is_relative_to(self.root) or not git_dir.is_dir():
            return None
        head = git_dir / "HEAD"
        if not head.is_file():
            return None
        try:
            text = head.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        if text.startswith("ref:"):
            ref_name = text.split(":", 1)[1].strip()
            ref_path = Path(ref_name)
            if ref_path.is_absolute():
                return None
            ref_parts = ref_path.parts
            if (
                not ref_parts
                or ref_parts[0] != "refs"
                or any(part in {"..", ".", ""} for part in ref_parts)
            ):
                return None
            ref_file = (git_dir / ref_path).resolve()
            if not ref_file.is_relative_to(git_dir) or not ref_file.is_file():
                return None
            try:
                return ref_file.read_text(encoding="utf-8").strip() or None
            except OSError:
                return None
        return text or None
