"""Workspace root: discovery, canonicalisation, hardened safe reads.

The single most security-sensitive module in the project. Every filesystem
access for ISMS content goes through ``WorkspaceRoot.safe_read`` or
``WorkspaceRoot.safe_iterdir``; both reject paths that resolve outside the
four allow-listed subtrees after symlink resolution.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

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
            raise WorkspaceNotConfigured(
                "ISMS_MCP_WORKSPACE environment variable is not set."
            )
        try:
            root = Path(raw).resolve(strict=True)
        except FileNotFoundError as exc:
            raise WorkspaceNotConfigured(
                f"workspace path does not exist: {raw}"
            ) from exc
        if not root.is_dir():
            raise WorkspaceNotConfigured(f"workspace path is not a directory: {root}")
        prefixes = tuple((root / sub).resolve() for sub in ALLOWED_SUBTREES)
        return cls(root=root, allowed_prefixes=prefixes)

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
        with open(target, "r", encoding="utf-8") as fh:
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

    def read_git_head(self) -> str | None:
        """Best-effort read of ``.git/HEAD``; tolerate absence and shallow forms.

        Never shells out. Reads the plain text of ``.git/HEAD`` and, if it is
        a symbolic ref (``ref: refs/heads/main``), reads the dereferenced ref
        file. Returns ``None`` if anything goes wrong.
        """
        head = self.root / ".git" / "HEAD"
        if not head.is_file():
            return None
        try:
            text = head.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        if text.startswith("ref:"):
            ref_name = text.split(":", 1)[1].strip()
            ref_file = self.root / ".git" / ref_name
            if not ref_file.is_file():
                return None
            try:
                return ref_file.read_text(encoding="utf-8").strip() or None
            except OSError:
                return None
        return text or None
