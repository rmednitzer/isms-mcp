"""register_query: unified, schema-aware query across the six registers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from isms_mcp import audit
from isms_mcp._pagination import paginate
from isms_mcp.context import ServerContext
from isms_mcp.loaders.registers import load_register
from isms_mcp.models import RegisterName, RegisterQueryResult

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: "FastMCP", ctx: ServerContext) -> None:
    @mcp.tool()
    def register_query(
        register: RegisterName,
        id_prefix: str | None = None,
        owner_role: str | None = None,
        in_scope: bool | None = None,
        lifecycle_status: str | None = None,
        classification: str | None = None,
        free_text: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> RegisterQueryResult:
        """Unified query across assets, facilities, networks, suppliers, data.

        Returns: paginated entries from the named register, each entry typed
        per its JSON Schema. Filters: id_prefix, owner_role, in_scope,
        lifecycle_status, classification, and a case-insensitive free_text
        substring over name and notes fields.
        """
        items, _source = load_register(ctx.workspace, register)
        if id_prefix:
            items = [e for e in items if str(e.get("id", "")).startswith(id_prefix)]
        if owner_role is not None:
            items = [e for e in items if e.get("owner_role") == owner_role]
        if in_scope is not None:
            items = [e for e in items if bool(e.get("in_scope")) == in_scope]
        if lifecycle_status is not None:
            items = [e for e in items if e.get("lifecycle_status") == lifecycle_status]
        if classification is not None:
            items = [
                e
                for e in items
                if e.get("classification") == classification
                or e.get("classification_handled") == classification
            ]
        if free_text:
            needle = free_text.lower()
            items = [
                e
                for e in items
                if needle in str(e.get("name", "")).lower()
                or needle in str(e.get("notes", "")).lower()
            ]
        items = ctx.filter_classification(items, field="classification")
        items = ctx.filter_classification(items, field="classification_handled")
        page_items, pagination = paginate(items, page, page_size)
        result = RegisterQueryResult(register=register, items=page_items, pagination=pagination)
        audit.record(
            tool="register_query",
            workspace=str(ctx.workspace.root),
            transport=ctx.transport_mode,
            payload={
                "register": register,
                "id_prefix": id_prefix,
                "owner_role": owner_role,
                "in_scope": in_scope,
                "lifecycle_status": lifecycle_status,
                "classification": classification,
                "free_text": free_text,
                "page": page,
                "page_size": page_size,
            },
            result_length=len(result.model_dump_json()),
        )
        return result
