"""Tests for exception classes."""

from isms_mcp.exceptions import (
    ClassificationDenied,
    IsmsMcpError,
    PathEscape,
    WorkspaceNotConfigured,
)


def test_hierarchy() -> None:
    assert issubclass(PathEscape, IsmsMcpError)
    assert issubclass(WorkspaceNotConfigured, IsmsMcpError)
    assert issubclass(ClassificationDenied, IsmsMcpError)


def test_path_escape_message() -> None:
    exc = PathEscape("test message")
    assert str(exc) == "test message"


def test_workspace_not_configured_message() -> None:
    exc = WorkspaceNotConfigured("missing var")
    assert str(exc) == "missing var"
