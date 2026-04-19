"""risk_query: filtered listing of the risk register."""

from __future__ import annotations

from typing import TYPE_CHECKING

from isms_mcp import audit
from isms_mcp._pagination import paginate
from isms_mcp.context import ServerContext
from isms_mcp.loaders.risk import load_risks
from isms_mcp.models import RatingLow, RiskQueryResult, RiskStatus, RiskTreatment

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

_RATING_ORDER = {"low": 0, "medium": 1, "high": 2, "severe": 3}


def _rating_at_least(value: str | None, threshold: str) -> bool:
    if not isinstance(value, str):
        return False
    head = value.split()[0].lower() if value else ""
    return _RATING_ORDER.get(head, -1) >= _RATING_ORDER[threshold]


def register(mcp: FastMCP, ctx: ServerContext) -> None:
    @mcp.tool()
    def risk_query(
        status: RiskStatus | None = None,
        treatment: RiskTreatment | None = None,
        min_residual: RatingLow | None = None,
        owner: str | None = None,
        asset_ref: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> RiskQueryResult:
        """Filtered listing of the risk register.

        Returns: paginated risks matching the filters. An empty register is a
        normal v1 state; the result has items=[] and total=0 in that case.
        """
        items = load_risks(ctx.workspace)
        if status is not None:
            items = [r for r in items if r.get("status") == status]
        if treatment is not None:
            items = [r for r in items if r.get("treatment") == treatment]
        if min_residual is not None:
            items = [r for r in items if _rating_at_least(r.get("residual_rating"), min_residual)]
        if owner is not None:
            items = [r for r in items if r.get("owner") == owner]
        if asset_ref is not None:
            items = [r for r in items if asset_ref in (r.get("asset_refs") or [])]
        page_items, pagination = paginate(items, page, page_size)
        result = RiskQueryResult(items=page_items, pagination=pagination)
        audit.record(
            tool="risk_query",
            workspace=str(ctx.workspace.root),
            transport=ctx.transport_mode,
            payload={
                "status": status,
                "treatment": treatment,
                "min_residual": min_residual,
                "owner": owner,
                "asset_ref": asset_ref,
                "page": page,
                "page_size": page_size,
            },
            result_length=len(result.model_dump_json()),
        )
        return result
