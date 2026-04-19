"""Custom exceptions for the isms-mcp server."""

from __future__ import annotations


class IsmsMcpError(Exception):
    """Base error class."""


class PathEscape(IsmsMcpError):
    """Raised when a requested path resolves outside the workspace allow-list."""


class WorkspaceNotConfigured(IsmsMcpError):
    """Raised when ISMS_MCP_WORKSPACE is missing or unresolvable."""


class ClassificationDenied(IsmsMcpError):
    """Raised when an entry is blocked by transport classification policy."""
