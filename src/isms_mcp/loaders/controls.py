"""Load Annex A, GDPR Art.32, NISG measures, Implementing Reg, mapping.yaml.

Also resolves implementation-statement files at controls/implementation/<id>.md.
"""

from __future__ import annotations

from typing import Any

from isms_mcp.loaders._yaml import parse_yaml
from isms_mcp.workspace import WorkspaceRoot


def _yaml_at(workspace: WorkspaceRoot, *candidates: str) -> dict[str, Any]:
    for path in candidates:
        if workspace.exists(path):
            data = parse_yaml(workspace.safe_read_text(path))
            if isinstance(data, dict):
                return data
    return {}


def load_mapping(workspace: WorkspaceRoot) -> list[dict[str, Any]]:
    data = _yaml_at(
        workspace,
        "instance/governance/controls/mapping.yaml",
        "template/governance/controls/mapping.yaml",
    )
    return [m for m in (data.get("mappings") or []) if isinstance(m, dict)]


def load_evidence_plan(workspace: WorkspaceRoot) -> list[dict[str, Any]]:
    data = _yaml_at(
        workspace,
        "instance/governance/controls/evidence-plan.yaml",
        "template/governance/controls/evidence-plan.yaml",
    )
    return [t for t in (data.get("evidence_tasks") or []) if isinstance(t, dict)]


def load_annex_a(workspace: WorkspaceRoot) -> list[dict[str, Any]]:
    data = _yaml_at(
        workspace,
        "instance/governance/controls/annex-a-27001.yaml",
        "template/governance/controls/annex-a-27001.yaml",
    )
    return [c for c in (data.get("controls") or []) if isinstance(c, dict)]


def implementation_statement_path(workspace: WorkspaceRoot, control_id: str) -> str | None:
    """Return the relative path of the implementation statement, or None."""
    candidates = (
        f"instance/governance/controls/implementation/{control_id}.md",
        f"template/governance/controls/implementation/{control_id}.md",
    )
    for path in candidates:
        if workspace.exists(path):
            return path
    return None
