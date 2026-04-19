"""Tests for workspace data loaders."""

import json
from datetime import date as date_cls
from pathlib import Path

import pytest

from isms_mcp.loaders._yaml import parse_yaml
from isms_mcp.loaders.calendar import load_calendar
from isms_mcp.loaders.controls import (
    implementation_statement_path,
    load_evidence_plan,
    load_mapping,
)
from isms_mcp.loaders.decisions import load_decisions
from isms_mcp.loaders.evidence import (
    collected_date,
    latest_per_control,
    latest_per_task,
    scan_attestations,
)
from isms_mcp.loaders.registers import load_register
from isms_mcp.loaders.risk import load_risks
from isms_mcp.loaders.soa import load_soa, soa_source_path
from isms_mcp.loaders.sources import load_sources
from isms_mcp.workspace import ALLOWED_SUBTREES, WorkspaceRoot


@pytest.fixture()
def workspace(tmp_path: Path) -> WorkspaceRoot:
    for sub in ALLOWED_SUBTREES:
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    return WorkspaceRoot.from_env(str(tmp_path))


# =========================================================================
# YAML parser
# =========================================================================


class TestParseYaml:
    def test_parse_dict(self) -> None:
        result = parse_yaml("key: value\n")
        assert result == {"key": "value"}

    def test_parse_list(self) -> None:
        result = parse_yaml("- a\n- b\n")
        assert result == ["a", "b"]

    def test_empty_returns_none(self) -> None:
        assert parse_yaml("") is None

    def test_safe_loader_rejects_python_objects(self) -> None:
        with pytest.raises(  # type: ignore[call-overload]
            (ValueError, TypeError, Exception),
        ):
            parse_yaml("!!python/object:os.system ['echo hello']")


# =========================================================================
# SoA loader
# =========================================================================


class TestSoaLoader:
    def test_load_from_instance(self, workspace: WorkspaceRoot) -> None:
        soa_dir = workspace.root / "instance" / "governance" / "soa"
        soa_dir.mkdir(parents=True)
        (soa_dir / "soa.yaml").write_text(
            "controls:\n  - id: A.5.1\n    title: Test\n    applicable: yes\n    status: planned\n"
        )
        result = load_soa(workspace)
        assert result is not None
        assert len(result["controls"]) == 1
        assert result["controls"][0]["id"] == "A.5.1"

    def test_fallback_to_template(self, workspace: WorkspaceRoot) -> None:
        soa_dir = workspace.root / "template" / "governance" / "soa"
        soa_dir.mkdir(parents=True)
        (soa_dir / "soa.yaml").write_text("controls:\n  - id: A.5.2\n    title: Tmpl\n")
        result = load_soa(workspace)
        assert result is not None
        assert result["controls"][0]["id"] == "A.5.2"

    def test_missing_returns_none(self, workspace: WorkspaceRoot) -> None:
        assert load_soa(workspace) is None

    def test_soa_source_path_instance(self, workspace: WorkspaceRoot) -> None:
        soa_dir = workspace.root / "instance" / "governance" / "soa"
        soa_dir.mkdir(parents=True)
        (soa_dir / "soa.yaml").write_text("controls: []\n")
        assert soa_source_path(workspace) == "instance/governance/soa/soa.yaml"


# =========================================================================
# Controls loader
# =========================================================================


class TestControlsLoader:
    def test_load_mapping(self, workspace: WorkspaceRoot) -> None:
        ctrl_dir = workspace.root / "instance" / "governance" / "controls"
        ctrl_dir.mkdir(parents=True)
        (ctrl_dir / "mapping.yaml").write_text(
            "mappings:\n  - iso27001: A.5.1\n    nisg2026: [M1]\n"
        )
        result = load_mapping(workspace)
        assert len(result) == 1
        assert result[0]["iso27001"] == "A.5.1"

    def test_load_evidence_plan(self, workspace: WorkspaceRoot) -> None:
        ctrl_dir = workspace.root / "instance" / "governance" / "controls"
        ctrl_dir.mkdir(parents=True)
        (ctrl_dir / "evidence-plan.yaml").write_text(
            "evidence_tasks:\n  - id: ET-001\n    control_ids: [A.5.1]\n    cadence_days: 90\n"
        )
        result = load_evidence_plan(workspace)
        assert len(result) == 1
        assert result[0]["id"] == "ET-001"

    def test_implementation_statement_path(self, workspace: WorkspaceRoot) -> None:
        impl_dir = workspace.root / "instance" / "governance" / "controls" / "implementation"
        impl_dir.mkdir(parents=True)
        (impl_dir / "A.5.1.md").write_text("# Implementation\n")
        result = implementation_statement_path(workspace, "A.5.1")
        assert result is not None
        assert "A.5.1.md" in result

    def test_implementation_statement_missing(self, workspace: WorkspaceRoot) -> None:
        assert implementation_statement_path(workspace, "A.99.99") is None


# =========================================================================
# Registers loader
# =========================================================================


class TestRegistersLoader:
    def test_load_assets(self, workspace: WorkspaceRoot) -> None:
        reg_dir = workspace.root / "instance" / "governance" / "assets"
        reg_dir.mkdir(parents=True)
        (reg_dir / "register.yaml").write_text("assets:\n  - id: ASSET-001\n    name: Laptop\n")
        items, source = load_register(workspace, "assets")
        assert len(items) == 1
        assert items[0]["id"] == "ASSET-001"
        assert source is not None

    def test_unknown_register_raises(self, workspace: WorkspaceRoot) -> None:
        with pytest.raises(KeyError, match="unknown register"):
            load_register(workspace, "bogus")

    def test_missing_register_empty(self, workspace: WorkspaceRoot) -> None:
        items, source = load_register(workspace, "data")
        assert items == []
        assert source is None


# =========================================================================
# Risk loader
# =========================================================================


class TestRiskLoader:
    def test_load_risks(self, workspace: WorkspaceRoot) -> None:
        risk_dir = workspace.root / "instance" / "governance" / "risk"
        risk_dir.mkdir(parents=True)
        (risk_dir / "register.yaml").write_text(
            "risks:\n  - id: R-001\n    title: Phishing\n    status: identified\n"
        )
        result = load_risks(workspace)
        assert len(result) == 1
        assert result[0]["id"] == "R-001"

    def test_missing_returns_empty(self, workspace: WorkspaceRoot) -> None:
        assert load_risks(workspace) == []


# =========================================================================
# Calendar loader
# =========================================================================


class TestCalendarLoader:
    def test_load_calendar(self, workspace: WorkspaceRoot) -> None:
        cal_dir = workspace.root / "framework-refs" / "calendar"
        cal_dir.mkdir(parents=True)
        (cal_dir / "regulatory-calendar.yaml").write_text(
            "milestones:\n"
            "  - id: M1\n"
            "    source_id: S1\n"
            "    event: Deadline\n"
            "    date: 2026-12-31\n"
        )
        result = load_calendar(workspace)
        assert len(result) == 1
        assert result[0]["id"] == "M1"

    def test_missing_returns_empty(self, workspace: WorkspaceRoot) -> None:
        assert load_calendar(workspace) == []


# =========================================================================
# Evidence loader
# =========================================================================


class TestEvidenceLoader:
    def test_scan_attestations(self, workspace: WorkspaceRoot) -> None:
        ev_dir = workspace.root / "instance" / "evidence" / "task1"
        ev_dir.mkdir(parents=True)
        att = {
            "evidence_task_id": "ET-001",
            "control_id": "A.5.1",
            "collected_at": "2026-01-15T10:00:00Z",
            "collected_by": "auditor",
        }
        (ev_dir / "att.json").write_text(json.dumps(att))
        result = scan_attestations(workspace)
        assert len(result) == 1
        assert result[0]["evidence_task_id"] == "ET-001"
        assert "__path" in result[0]

    def test_scan_skips_invalid_json(self, workspace: WorkspaceRoot) -> None:
        ev_dir = workspace.root / "instance" / "evidence"
        ev_dir.mkdir(parents=True, exist_ok=True)
        (ev_dir / "bad.json").write_text("not json{{{")
        assert scan_attestations(workspace) == []

    def test_latest_per_task(self) -> None:
        atts = [
            {"evidence_task_id": "ET-001", "collected_at": "2026-01-01T00:00:00Z"},
            {"evidence_task_id": "ET-001", "collected_at": "2026-06-01T00:00:00Z"},
            {"evidence_task_id": "ET-002", "collected_at": "2026-03-01T00:00:00Z"},
        ]
        result = latest_per_task(atts)
        assert result["ET-001"]["collected_at"] == "2026-06-01T00:00:00Z"
        assert result["ET-002"]["collected_at"] == "2026-03-01T00:00:00Z"

    def test_latest_per_control(self) -> None:
        atts = [
            {"control_id": "A.5.1", "collected_at": "2026-01-01T00:00:00Z"},
            {"control_id": "A.5.1", "collected_at": "2026-06-01T00:00:00Z"},
        ]
        result = latest_per_control(atts)
        assert result["A.5.1"]["collected_at"] == "2026-06-01T00:00:00Z"

    def test_collected_date(self) -> None:
        att = {"collected_at": "2026-03-15T10:00:00Z"}
        assert collected_date(att) == date_cls(2026, 3, 15)

    def test_collected_date_missing(self) -> None:
        assert collected_date({}) is None


# =========================================================================
# Decisions loader
# =========================================================================


class TestDecisionsLoader:
    def test_load_with_frontmatter(self, workspace: WorkspaceRoot) -> None:
        dec_dir = workspace.root / "docs" / "decisions"
        dec_dir.mkdir(parents=True)
        (dec_dir / "DEC-2026-001.md").write_text(
            "---\ntitle: Test Decision\nstatus: approved\n---\nBody text here.\n"
        )
        result = load_decisions(workspace)
        assert len(result) == 1
        assert result[0]["frontmatter"]["title"] == "Test Decision"
        assert "Body text here." in result[0]["body"]

    def test_load_without_frontmatter(self, workspace: WorkspaceRoot) -> None:
        dec_dir = workspace.root / "docs" / "decisions"
        dec_dir.mkdir(parents=True)
        (dec_dir / "DEC-2026-002.md").write_text("No frontmatter here.\n")
        result = load_decisions(workspace)
        assert len(result) == 1
        assert result[0]["frontmatter"] == {}

    def test_missing_dir(self, workspace: WorkspaceRoot) -> None:
        assert load_decisions(workspace) == []


# =========================================================================
# Sources loader
# =========================================================================


class TestSourcesLoader:
    def test_load_sources(self, workspace: WorkspaceRoot) -> None:
        src_dir = workspace.root / "framework-refs" / "sources"
        src_dir.mkdir(parents=True)
        (src_dir / "registry.yaml").write_text(
            "sources:\n  - id: ISO-27001\n    short_title: ISO 27001\n"
        )
        result = load_sources(workspace)
        assert len(result) == 1
        assert result[0]["id"] == "ISO-27001"

    def test_missing_returns_empty(self, workspace: WorkspaceRoot) -> None:
        assert load_sources(workspace) == []
