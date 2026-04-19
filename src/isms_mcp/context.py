"""Server-wide context shared with all tool registrations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from isms_mcp.workspace import WorkspaceRoot

TransportMode = Literal["stdio", "http"]


@dataclass(frozen=True)
class ServerContext:
    """Read-only context exposed to every tool registration."""

    workspace: WorkspaceRoot
    transport_mode: TransportMode
    allow_restricted: bool

    def filter_classification(
        self,
        items: list[dict[str, Any]],
        field: str = "classification",
    ) -> list[dict[str, Any]]:
        """Drop ``classification: restricted`` entries when the active transport disallows them."""
        if self.allow_restricted:
            return items
        return [item for item in items if item.get(field) != "restricted"]
