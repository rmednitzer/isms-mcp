"""Scan ``instance/evidence/**/*.json`` for attestations.

Returns the latest attestation per evidence_task_id, plus a flat list of
attestation summaries useful for control_status drill-downs.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from isms_mcp.workspace import WorkspaceRoot

EVIDENCE_DIR = "instance/evidence"


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def scan_attestations(workspace: WorkspaceRoot) -> list[dict[str, Any]]:
    """Return all readable attestation records under instance/evidence/.

    Tolerant: silently skips files that do not parse or that are not dicts.
    """
    if not workspace.exists(EVIDENCE_DIR):
        return []
    out: list[dict[str, Any]] = []
    for path in workspace.safe_rglob(EVIDENCE_DIR, "*.json"):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        # Stamp the relative path inside the workspace for traceability.
        try:
            data["__path"] = str(Path(path).relative_to(workspace.root))
        except ValueError:
            data["__path"] = str(path)
        out.append(data)
    return out


def latest_per_task(attestations: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Return mapping ``evidence_task_id -> latest attestation`` by ``collected_at``."""
    latest: dict[str, dict[str, Any]] = {}
    for att in attestations:
        tid = att.get("evidence_task_id")
        if not isinstance(tid, str):
            continue
        ts = _parse_iso(att.get("collected_at"))
        if ts is None:
            continue
        prev = latest.get(tid)
        prev_ts = _parse_iso(prev.get("collected_at")) if prev else None
        if prev_ts is None or ts > prev_ts:
            latest[tid] = att
    return latest


def latest_per_control(attestations: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Return mapping ``control_id -> latest attestation`` by ``collected_at``."""
    latest: dict[str, dict[str, Any]] = {}
    for att in attestations:
        cid = att.get("control_id")
        if not isinstance(cid, str):
            continue
        ts = _parse_iso(att.get("collected_at"))
        if ts is None:
            continue
        prev = latest.get(cid)
        prev_ts = _parse_iso(prev.get("collected_at")) if prev else None
        if prev_ts is None or ts > prev_ts:
            latest[cid] = att
    return latest


def collected_date(att: dict[str, Any]) -> date | None:
    ts = _parse_iso(att.get("collected_at"))
    return ts.date() if ts else None
