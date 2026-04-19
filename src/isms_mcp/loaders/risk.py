"""Load the risk register and the treatment plan / acceptance log if present."""

from __future__ import annotations

from typing import Any

from isms_mcp.loaders._yaml import parse_yaml
from isms_mcp.workspace import WorkspaceRoot

INSTANCE_PATH = "instance/governance/risk/register.yaml"
TEMPLATE_PATH = "template/governance/risk/register.yaml"


def _resolve_path(workspace: WorkspaceRoot) -> str | None:
    if workspace.exists(INSTANCE_PATH):
        return INSTANCE_PATH
    if workspace.exists(TEMPLATE_PATH):
        return TEMPLATE_PATH
    return None


def load_risks(workspace: WorkspaceRoot) -> list[dict[str, Any]]:
    path = _resolve_path(workspace)
    if path is None:
        return []
    data = parse_yaml(workspace.safe_read_text(path))
    if not isinstance(data, dict):
        return []
    return [r for r in (data.get("risks") or []) if isinstance(r, dict)]
