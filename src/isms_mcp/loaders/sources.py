"""Load the authoritative-source registry."""

from __future__ import annotations

from typing import Any

from isms_mcp.loaders._yaml import parse_yaml
from isms_mcp.workspace import WorkspaceRoot

REGISTRY_PATH = "framework-refs/sources/registry.yaml"


def load_sources(workspace: WorkspaceRoot) -> list[dict[str, Any]]:
    if not workspace.exists(REGISTRY_PATH):
        return []
    data = parse_yaml(workspace.safe_read_text(REGISTRY_PATH))
    if not isinstance(data, dict):
        return []
    return [s for s in (data.get("sources") or []) if isinstance(s, dict)]
