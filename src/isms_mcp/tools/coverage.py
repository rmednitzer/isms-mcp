"""control_coverage: SoA-wide coverage report."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

from isms_mcp import audit
from isms_mcp.context import ServerContext
from isms_mcp.loaders.controls import implementation_statement_path, load_evidence_plan
from isms_mcp.loaders.evidence import collected_date, latest_per_task, scan_attestations
from isms_mcp.loaders.soa import load_soa
from isms_mcp.models import CoverageReport, ThemeName

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP, ctx: ServerContext) -> None:
    @mcp.tool()
    def control_coverage(  # noqa: PLR0912
        theme: ThemeName | None = None,
        applicable_only: bool = True,
    ) -> CoverageReport:
        """SoA-wide coverage report: implementation, evidence binding, recency.

        Returns: counts of total, applicable, with/without implementation
        statement, with/without evidence task bound, with recent evidence,
        plus lists of stale and never-collected control IDs.
        """
        soa = load_soa(ctx.workspace) or {}
        controls = list(soa.get("controls") or [])
        if theme is not None:
            controls = [c for c in controls if c.get("theme") == theme]
        applicable = [c for c in controls if c.get("applicable") == "yes"]
        scope = applicable if applicable_only else controls

        plan = load_evidence_plan(ctx.workspace)
        tasks_by_control: dict[str, list[dict[str, Any]]] = {}
        for t in plan:
            for cid in t.get("control_ids") or []:
                tasks_by_control.setdefault(str(cid), []).append(t)

        attestations = scan_attestations(ctx.workspace)
        latest_task = latest_per_task(attestations)

        with_impl: list[str] = []
        without_impl: list[str] = []
        with_evidence: list[str] = []
        without_evidence: list[str] = []
        with_recent: list[str] = []
        stale: list[str] = []
        never: list[str] = []
        today = date.today()
        for c in scope:
            cid = str(c.get("id", ""))
            if implementation_statement_path(ctx.workspace, cid):
                with_impl.append(cid)
            else:
                without_impl.append(cid)
            tasks = tasks_by_control.get(cid, [])
            if tasks:
                with_evidence.append(cid)
            else:
                without_evidence.append(cid)
                continue
            best_age: int | None = None
            cadence_min = min(
                (int(t["cadence_days"]) for t in tasks if t.get("cadence_days")), default=None
            )
            for t in tasks:
                tid = str(t.get("id", ""))
                att = latest_task.get(tid)
                d = collected_date(att) if att else None
                if d is None:
                    continue
                age = (today - d).days
                if best_age is None or age < best_age:
                    best_age = age
            if best_age is None:
                never.append(cid)
            elif cadence_min is not None and best_age > cadence_min:
                stale.append(cid)
            else:
                with_recent.append(cid)

        result = CoverageReport(
            total_controls=len(controls),
            applicable=len(applicable),
            with_implementation_statement=len(with_impl),
            without_implementation_statement=without_impl,
            with_evidence_task_bound=len(with_evidence),
            without_evidence_task_bound=without_evidence,
            with_recent_evidence=len(with_recent),
            stale_evidence=stale,
            never_collected=never,
        )
        audit.record(
            tool="control_coverage",
            workspace=str(ctx.workspace.root),
            transport=ctx.transport_mode,
            payload={"theme": theme, "applicable_only": applicable_only},
            result_length=len(result.model_dump_json()),
        )
        return result
