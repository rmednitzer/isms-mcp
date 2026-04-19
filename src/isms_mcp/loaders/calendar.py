"""Load the regulatory calendar."""

from __future__ import annotations

from typing import Any

from isms_mcp.loaders._yaml import parse_yaml
from isms_mcp.workspace import WorkspaceRoot

CALENDAR_PATH = "framework-refs/calendar/regulatory-calendar.yaml"


def load_calendar(workspace: WorkspaceRoot) -> list[dict[str, Any]]:
    if not workspace.exists(CALENDAR_PATH):
        return []
    data = parse_yaml(workspace.safe_read_text(CALENDAR_PATH))
    if not isinstance(data, dict):
        return []
    return [m for m in (data.get("milestones") or []) if isinstance(m, dict)]
