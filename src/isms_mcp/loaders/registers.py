"""Load the five governance registers: assets, facilities, networks, suppliers, data."""

from __future__ import annotations

from typing import Any

from isms_mcp.loaders._yaml import parse_yaml
from isms_mcp.workspace import WorkspaceRoot

REGISTERS: dict[str, dict[str, str]] = {
    "assets": {
        "instance": "instance/governance/assets/register.yaml",
        "template": "template/governance/assets/register.yaml",
        "collection_key": "assets",
    },
    "facilities": {
        "instance": "instance/governance/assets/facilities.yaml",
        "template": "template/governance/assets/facilities.yaml",
        "collection_key": "facilities",
    },
    "networks": {
        "instance": "instance/governance/assets/networks.yaml",
        "template": "template/governance/assets/networks.yaml",
        "collection_key": "segments",
    },
    "suppliers": {
        "instance": "instance/governance/supply-chain/register.yaml",
        "template": "template/governance/supply-chain/register.yaml",
        "collection_key": "suppliers",
    },
    "data": {
        "instance": "instance/governance/data/inventory.yaml",
        "template": "template/governance/data/inventory.yaml",
        "collection_key": "processing_activities",
    },
}


def _resolve_path(workspace: WorkspaceRoot, register: str) -> str | None:
    spec = REGISTERS[register]
    if workspace.exists(spec["instance"]):
        return spec["instance"]
    if workspace.exists(spec["template"]):
        return spec["template"]
    return None


def load_register(
    workspace: WorkspaceRoot, register: str
) -> tuple[list[dict[str, Any]], str | None]:
    """Return ``(items, source_path)``; items is empty if the register is absent."""
    if register not in REGISTERS:
        raise KeyError(f"unknown register: {register}")
    path = _resolve_path(workspace, register)
    if path is None:
        return [], None
    data = parse_yaml(workspace.safe_read_text(path))
    if not isinstance(data, dict):
        return [], path
    items = data.get(REGISTERS[register]["collection_key"], []) or []
    return [item for item in items if isinstance(item, dict)], path
