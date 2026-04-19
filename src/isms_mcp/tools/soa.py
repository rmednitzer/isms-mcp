"""soa_query: filtered listing of the Statement of Applicability."""

from __future__ import annotations

from typing import TYPE_CHECKING

from isms_mcp import audit
from isms_mcp._pagination import paginate
from isms_mcp.context import ServerContext
from isms_mcp.loaders.controls import (
    implementation_statement_path,
    load_evidence_plan,
    load_mapping,
)
from isms_mcp.loaders.evidence import (
    collected_date,
    latest_per_control,
    latest_per_task,
    scan_attestations,
)
from isms_mcp.loaders.soa import load_soa
from isms_mcp.models import (
    ApplicableFlag,
    AttestationSummary,
    ControlStatus,
    ControlStatusName,
    CrosswalkSlice,
    EvidenceTaskSummary,
    SoaEntry,
    SoaQueryResult,
    ThemeName,
)

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def _to_soa_entry(raw: dict) -> SoaEntry:
    return SoaEntry(
        id=raw.get("id", ""),
        title=raw.get("title", ""),
        theme=raw.get("theme"),
        applicable=raw.get("applicable", "yes"),
        justification_ref=raw.get("justification_ref"),
        exclusion_ref=raw.get("exclusion_ref"),
        implementation_ref=raw.get("implementation_ref"),
        status=raw.get("status", "not_assessed"),
        evidence_task_ids=list(raw.get("evidence_task_ids") or []),
        owner=raw.get("owner"),
        last_review_date=str(raw["last_review_date"]) if raw.get("last_review_date") else None,
    )


def _crosswalk_for(control_id: str, mapping: list[dict]) -> CrosswalkSlice:
    for entry in mapping:
        if entry.get("iso27001") == control_id:
            return CrosswalkSlice(
                iso27001=[control_id],
                nisg2026=list(entry.get("nisg2026") or []),
                gdpr=list(entry.get("gdpr") or []),
                **{"implreg-2024-2690": list(entry.get("implreg-2024-2690") or [])},
            )
    return CrosswalkSlice(iso27001=[control_id])


def register(mcp: "FastMCP", ctx: ServerContext) -> None:
    @mcp.tool()
    def soa_query(
        control_id_prefix: str | None = None,
        theme: ThemeName | None = None,
        applicable: ApplicableFlag | None = None,
        status: ControlStatusName | None = None,
        owner: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> SoaQueryResult:
        """Filtered listing of the Statement of Applicability.

        Returns: page of SoA entries matching the filters, plus pagination
        metadata. Each entry has id, title, theme, applicable, status,
        owner role, evidence task IDs, and the implementation reference.
        """
        soa = load_soa(ctx.workspace) or {}
        controls: list[dict] = list(soa.get("controls") or [])
        if control_id_prefix:
            controls = [c for c in controls if str(c.get("id", "")).startswith(control_id_prefix)]
        if theme is not None:
            controls = [c for c in controls if c.get("theme") == theme]
        if applicable is not None:
            controls = [c for c in controls if c.get("applicable") == applicable]
        if status is not None:
            controls = [c for c in controls if c.get("status") == status]
        if owner is not None:
            controls = [c for c in controls if c.get("owner") == owner]
        page_items, pagination = paginate(controls, page, page_size)
        result = SoaQueryResult(
            items=[_to_soa_entry(c) for c in page_items],
            pagination=pagination,
        )
        audit.record(
            tool="soa_query",
            workspace=str(ctx.workspace.root),
            transport=ctx.transport_mode,
            payload={
                "control_id_prefix": control_id_prefix,
                "theme": theme,
                "applicable": applicable,
                "status": status,
                "owner": owner,
                "page": page,
                "page_size": page_size,
            },
            result_length=len(result.model_dump_json()),
        )
        return result

    @mcp.tool()
    def control_status(control_id: str) -> ControlStatus:
        """Drill into one Annex A control across SoA, implementation, and evidence.

        Returns: SoA entry, presence and path of implementation statement,
        bound evidence tasks, latest attestation (if any), days since last
        attestation, the minimum cadence across bound tasks, a stale flag,
        and the cross-framework crosswalk for the control.
        """
        from datetime import date

        soa = load_soa(ctx.workspace) or {}
        controls = list(soa.get("controls") or [])
        soa_raw = next((c for c in controls if c.get("id") == control_id), None)
        soa_entry = _to_soa_entry(soa_raw) if soa_raw else None

        impl_path = implementation_statement_path(ctx.workspace, control_id)

        plan = load_evidence_plan(ctx.workspace)
        bound = [t for t in plan if control_id in (t.get("control_ids") or [])]
        evidence_tasks = [
            EvidenceTaskSummary(
                id=t.get("id", ""),
                control_ids=list(t.get("control_ids") or []),
                cadence_days=t.get("cadence_days"),
                mode=t.get("mode"),
                owner_role=t.get("owner_role"),
                sop_ref=t.get("sop_ref"),
            )
            for t in bound
        ]
        cadence_days = min((t.cadence_days for t in evidence_tasks if t.cadence_days), default=None)

        attestations = scan_attestations(ctx.workspace)
        per_control = latest_per_control(attestations)
        per_task = latest_per_task(attestations)
        latest_raw = per_control.get(control_id)
        if latest_raw is None:
            for t in bound:
                tid = t.get("id")
                if isinstance(tid, str) and tid in per_task:
                    candidate = per_task[tid]
                    if latest_raw is None:
                        latest_raw = candidate
                    else:
                        a = collected_date(candidate)
                        b = collected_date(latest_raw)
                        if a and b and a > b:
                            latest_raw = candidate
        latest = None
        days_since: int | None = None
        if latest_raw is not None:
            latest = AttestationSummary(
                evidence_task_id=latest_raw.get("evidence_task_id"),
                control_id=latest_raw.get("control_id"),
                collected_at=str(latest_raw.get("collected_at", "")),
                collected_by=latest_raw.get("collected_by"),
                collection_method=latest_raw.get("collection_method"),
                path=str(latest_raw.get("__path", "")),
            )
            d = collected_date(latest_raw)
            if d is not None:
                days_since = (date.today() - d).days
        stale = bool(
            cadence_days is not None
            and (days_since is None or days_since > cadence_days)
        )

        return ControlStatus(
            control_id=control_id,
            title=(soa_raw or {}).get("title", ""),
            theme=(soa_raw or {}).get("theme"),
            soa=soa_entry,
            implementation_statement_present=impl_path is not None,
            implementation_statement_path=impl_path,
            evidence_tasks=evidence_tasks,
            latest_attestation=latest,
            days_since_last_attestation=days_since,
            cadence_days=cadence_days,
            stale=stale,
            crosswalk=_crosswalk_for(control_id, load_mapping(ctx.workspace)),
        )
