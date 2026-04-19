"""Tests for WorkspaceRoot: path validation, allow-list enforcement, security."""

import os
import tempfile
from pathlib import Path

import pytest

from isms_mcp.exceptions import PathEscape, WorkspaceNotConfigured
from isms_mcp.workspace import ALLOWED_SUBTREES, WorkspaceRoot


@pytest.fixture()
def workspace(tmp_path: Path) -> WorkspaceRoot:
    """Create a minimal workspace with the four allow-listed subtrees."""
    for sub in ALLOWED_SUBTREES:
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    return WorkspaceRoot.from_env(str(tmp_path))


class TestFromEnv:
    def test_missing_env_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ISMS_MCP_WORKSPACE", raising=False)
        with pytest.raises(WorkspaceNotConfigured, match="not set"):
            WorkspaceRoot.from_env()

    def test_nonexistent_path_raises(self, tmp_path: Path) -> None:
        with pytest.raises(WorkspaceNotConfigured, match="does not exist"):
            WorkspaceRoot.from_env(str(tmp_path / "nope"))

    def test_file_not_dir_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("hi")
        with pytest.raises(WorkspaceNotConfigured, match="not a directory"):
            WorkspaceRoot.from_env(str(f))

    def test_valid_workspace(self, workspace: WorkspaceRoot) -> None:
        assert workspace.root.is_dir()
        assert len(workspace.allowed_prefixes) == len(ALLOWED_SUBTREES)

    def test_env_variable_fallback(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        for sub in ALLOWED_SUBTREES:
            (tmp_path / sub).mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("ISMS_MCP_WORKSPACE", str(tmp_path))
        ws = WorkspaceRoot.from_env()
        assert ws.root == tmp_path.resolve()


class TestResolveInside:
    def test_absolute_path_rejected(self, workspace: WorkspaceRoot) -> None:
        with pytest.raises(PathEscape, match="absolute path"):
            workspace._resolve_inside("/etc/passwd")

    def test_nul_byte_rejected(self, workspace: WorkspaceRoot) -> None:
        with pytest.raises(PathEscape, match="NUL"):
            workspace._resolve_inside("docs/foo\x00bar")

    def test_traversal_rejected(self, workspace: WorkspaceRoot) -> None:
        with pytest.raises((PathEscape, FileNotFoundError)):
            workspace._resolve_inside("docs/../../etc/passwd")

    def test_outside_allow_list_rejected(self, workspace: WorkspaceRoot) -> None:
        # Create a file outside the allow-listed subtrees
        (workspace.root / "secret.txt").write_text("secret")
        with pytest.raises(PathEscape, match="escapes"):
            workspace._resolve_inside("secret.txt")

    def test_allowed_path_resolves(self, workspace: WorkspaceRoot) -> None:
        (workspace.root / "docs" / "test.md").write_text("hello")
        result = workspace._resolve_inside("docs/test.md")
        assert result.is_file()


class TestSafeReadText:
    def test_read_allowed_file(self, workspace: WorkspaceRoot) -> None:
        (workspace.root / "docs" / "test.md").write_text("content here")
        assert workspace.safe_read_text("docs/test.md") == "content here"

    def test_read_directory_raises(self, workspace: WorkspaceRoot) -> None:
        with pytest.raises(FileNotFoundError, match="not a regular file"):
            workspace.safe_read_text("docs")

    def test_read_nonexistent_raises(self, workspace: WorkspaceRoot) -> None:
        with pytest.raises(FileNotFoundError):
            workspace.safe_read_text("docs/missing.md")


class TestExists:
    def test_existing_file(self, workspace: WorkspaceRoot) -> None:
        (workspace.root / "docs" / "present.md").write_text("yes")
        assert workspace.exists("docs/present.md") is True

    def test_missing_file(self, workspace: WorkspaceRoot) -> None:
        assert workspace.exists("docs/absent.md") is False

    def test_outside_allow_list(self, workspace: WorkspaceRoot) -> None:
        (workspace.root / "secret.txt").write_text("nope")
        assert workspace.exists("secret.txt") is False


class TestSafeIterdir:
    def test_lists_children(self, workspace: WorkspaceRoot) -> None:
        (workspace.root / "docs" / "a.md").write_text("a")
        (workspace.root / "docs" / "b.md").write_text("b")
        children = list(workspace.safe_iterdir("docs"))
        names = {c.name for c in children}
        assert names == {"a.md", "b.md"}

    def test_not_a_dir_raises(self, workspace: WorkspaceRoot) -> None:
        (workspace.root / "docs" / "file.md").write_text("x")
        with pytest.raises(NotADirectoryError):
            list(workspace.safe_iterdir("docs/file.md"))


class TestSafeRglob:
    def test_recursive_glob(self, workspace: WorkspaceRoot) -> None:
        (workspace.root / "instance" / "sub").mkdir(parents=True)
        (workspace.root / "instance" / "a.yaml").write_text("a")
        (workspace.root / "instance" / "sub" / "b.yaml").write_text("b")
        results = list(workspace.safe_rglob("instance", "*.yaml"))
        names = {r.name for r in results}
        assert names == {"a.yaml", "b.yaml"}


class TestSymlinks:
    def test_symlink_inside_allowed(self, workspace: WorkspaceRoot) -> None:
        target = workspace.root / "docs" / "real.md"
        target.write_text("real")
        link = workspace.root / "docs" / "link.md"
        link.symlink_to(target)
        assert workspace.safe_read_text("docs/link.md") == "real"

    def test_symlink_escaping_rejected(self, workspace: WorkspaceRoot) -> None:
        # Create a file outside the workspace
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("escaped")
            outside = f.name
        try:
            link = workspace.root / "docs" / "escape.txt"
            link.symlink_to(outside)
            with pytest.raises(PathEscape, match="escapes"):
                workspace.safe_read_text("docs/escape.txt")
        finally:
            os.unlink(outside)


class TestReadGitHead:
    def test_no_git_dir(self, workspace: WorkspaceRoot) -> None:
        assert workspace.read_git_head() is None

    def test_detached_head(self, workspace: WorkspaceRoot) -> None:
        git_dir = workspace.root / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("abc123def456\n")
        assert workspace.read_git_head() == "abc123def456"

    def test_symbolic_ref(self, workspace: WorkspaceRoot) -> None:
        git_dir = workspace.root / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
        refs_dir = git_dir / "refs" / "heads"
        refs_dir.mkdir(parents=True)
        (refs_dir / "main").write_text("deadbeef\n")
        assert workspace.read_git_head() == "deadbeef"

    def test_malformed_ref_returns_none(self, workspace: WorkspaceRoot) -> None:
        git_dir = workspace.root / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: ../../../etc/passwd\n")
        assert workspace.read_git_head() is None
