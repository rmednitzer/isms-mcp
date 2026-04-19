"""regulatory_calendar: query upcoming regulatory milestones."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from isms_mcp import audit
from isms_mcp.context import ServerContext
from isms_mcp.loaders.calendar import load_calendar
from isms_mcp.models import CalendarMilestone, CalendarResult, ConfidenceName

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def _coerce_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def register(mcp: FastMCP, ctx: ServerContext) -> None:
    @mcp.tool()
    def regulatory_calendar(
        within_days: int | None = None,
        source_id: str | None = None,
        confidence: ConfidenceName | None = None,
    ) -> CalendarResult:
        """Filtered query over the regulatory calendar.

        Returns: list of milestones with id, source_id, event, date,
        confidence, obligations triggered, artefacts requiring readiness,
        responsible role, and days_until_due relative to today.
        """
        milestones = load_calendar(ctx.workspace)
        today = date.today()
        out: list[CalendarMilestone] = []
        for m in milestones:
            if source_id and m.get("source_id") != source_id:
                continue
            if confidence and m.get("confidence") != confidence:
                continue
            d = _coerce_date(m.get("date"))
            days_until: int | None = (d - today).days if d else None
            if within_days is not None:
                if days_until is None or days_until < 0 or days_until > within_days:
                    continue
            out.append(
                CalendarMilestone(
                    id=str(m.get("id", "")),
                    source_id=str(m.get("source_id", "")),
                    event=str(m.get("event", "")),
                    date=d.isoformat() if d else str(m.get("date", "")),
                    confidence=m.get("confidence"),
                    obligations_triggered=list(m.get("obligations_triggered") or []),
                    artifacts_requiring_readiness=list(
                        m.get("artifacts_requiring_readiness") or []
                    ),
                    review_at=str(m["review_at"]) if m.get("review_at") else None,
                    responsible_role=m.get("responsible_role"),
                    days_until_due=days_until,
                )
            )
        out.sort(key=lambda x: x.date)
        result = CalendarResult(items=out, total=len(out))
        audit.record(
            tool="regulatory_calendar",
            workspace=str(ctx.workspace.root),
            transport=ctx.transport_mode,
            payload={
                "within_days": within_days,
                "source_id": source_id,
                "confidence": confidence,
            },
            result_length=len(result.model_dump_json()),
        )
        return result
