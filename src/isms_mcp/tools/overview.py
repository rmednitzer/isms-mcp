"""isms_info: one-shot orientation tool."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from isms_mcp import MCP_SPEC_REVISION, audit
from isms_mcp.context import ServerContext
from isms_mcp.loaders._yaml import parse_yaml
from isms_mcp.models import IsmsInfo

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def _get(d: dict[str, Any] | None, key: str, default: Any = None) -> Any:
    if not isinstance(d, dict):
        return default
    val = d.get(key, default)
    return val if val is not None else default


def _stringify_date(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def build(ctx: ServerContext) -> IsmsInfo:
    config: dict[str, Any] = {}
    if ctx.workspace.exists("instance/config.yaml"):
        parsed = parse_yaml(ctx.workspace.safe_read_text("instance/config.yaml"))
        if isinstance(parsed, dict):
            config = parsed
    entity = _get(config, "entity", {}) or {}
    classification = _get(config, "classification", {}) or {}
    rendered = ctx.workspace.exists("instance/governance/soa/soa.yaml")
    return IsmsInfo(
        entity_legal_name=entity.get("legal_name"),
        entity_short_name=entity.get("short_name"),
        jurisdiction=entity.get("jurisdiction"),
        nisg2026_category=classification.get("nisg2026_category"),
        gdpr_role=classification.get("gdpr_role"),
        iso27001_target_cert_date=_stringify_date(classification.get("iso27001_target_cert_date")),
        primary_language=entity.get("primary_language", "en"),
        authority_language=entity.get("authority_language", "de"),
        workspace_path=str(ctx.workspace.root),
        template_is_rendered=rendered,
        isms_repo_rev=ctx.workspace.read_git_head(),
        spec_revision=MCP_SPEC_REVISION,
    )


def register(mcp: FastMCP, ctx: ServerContext) -> None:
    @mcp.tool()
    def isms_info() -> IsmsInfo:
        """Orientation snapshot of the ISMS workspace.

        Returns: entity legal name, jurisdiction, NISG 2026 category, GDPR role,
        ISO 27001 target certification date, configured languages, workspace
        path, whether the template has been rendered into instance/, the ISMS
        repository revision (if .git is present), and the implemented MCP spec
        revision.
        """
        result = build(ctx)
        audit.record(
            tool="isms_info",
            workspace=str(ctx.workspace.root),
            transport=ctx.transport_mode,
            payload={},
            result_length=len(result.model_dump_json()),
        )
        return result
