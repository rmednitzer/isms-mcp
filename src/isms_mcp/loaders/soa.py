"""Load the Statement of Applicability."""

from __future__ import annotations

from typing import Any

from isms_mcp.loaders._yaml import parse_yaml
from isms_mcp.workspace import WorkspaceRoot

INSTANCE_PATH = "instance/governance/soa/soa.yaml"
TEMPLATE_PATH = "template/governance/soa/soa.yaml"


def _resolve_path(workspace: WorkspaceRoot) -> str | None:
    if workspace.exists(INSTANCE_PATH):
        return INSTANCE_PATH
    if workspace.exists(TEMPLATE_PATH):
        return TEMPLATE_PATH
    return None


def load_soa(workspace: WorkspaceRoot) -> dict[str, Any] | None:
    """Return the parsed SoA document, preferring instance over template."""
    path = _resolve_path(workspace)
    if path is None:
        return None
    data = parse_yaml(workspace.safe_read_text(path))
    return data if isinstance(data, dict) else None


def soa_source_path(workspace: WorkspaceRoot) -> str | None:
    return _resolve_path(workspace)
