"""evidence_age: structured equivalent of the evidence_age_report collector."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from isms_mcp import audit
from isms_mcp.context import ServerContext
from isms_mcp.loaders.controls import load_evidence_plan
from isms_mcp.loaders.evidence import collected_date, latest_per_task, scan_attestations
from isms_mcp.models import EvidenceAgeEntry, EvidenceAgeResult, EvidenceStateFilter

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: "FastMCP", ctx: ServerContext) -> None:
    @mcp.tool()
    def evidence_age(
        state: EvidenceStateFilter = "stale",
        control_id_prefix: str | None = None,
        owner_role: str | None = None,
    ) -> EvidenceAgeResult:
        """Evidence task ages with staleness against configured cadence.

        Returns: list of evidence tasks with task_id, control_ids, cadence_days,
        last_collected_at (or null), age_days (or null), state (ok|stale|never),
        sop_ref, owner_role. Default state filter is ``stale``.
        """
        plan = load_evidence_plan(ctx.workspace)
        attestations = scan_attestations(ctx.workspace)
        latest = latest_per_task(attestations)
        today = date.today()
        items: list[EvidenceAgeEntry] = []
        for task in plan:
            tid = str(task.get("id", ""))
            cids = list(task.get("control_ids") or [])
            cadence = task.get("cadence_days")
            owner = task.get("owner_role")
            sop_ref = task.get("sop_ref")
            if control_id_prefix and not any(c.startswith(control_id_prefix) for c in cids):
                continue
            if owner_role is not None and owner != owner_role:
                continue
            att = latest.get(tid)
            d = collected_date(att) if att else None
            if d is None:
                age = None
                row_state = "never"
            else:
                age = (today - d).days
                row_state = "stale" if (cadence is not None and age > int(cadence)) else "ok"
            if state != "all" and row_state != state:
                continue
            items.append(
                EvidenceAgeEntry(
                    task_id=tid,
                    control_ids=cids,
                    cadence_days=int(cadence) if cadence is not None else None,
                    last_collected_at=str(att.get("collected_at")) if att and att.get("collected_at") else None,
                    age_days=age,
                    state=row_state,
                    sop_ref=sop_ref,
                    owner_role=owner,
                )
            )
        result = EvidenceAgeResult(items=items, total=len(items))
        audit.record(
            tool="evidence_age",
            workspace=str(ctx.workspace.root),
            transport=ctx.transport_mode,
            payload={
                "state": state,
                "control_id_prefix": control_id_prefix,
                "owner_role": owner_role,
            },
            result_length=len(result.model_dump_json()),
        )
        return result
