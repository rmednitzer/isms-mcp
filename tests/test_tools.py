"""Tests for MCP tool implementations with mock workspace data."""

import json
from pathlib import Path

import pytest

from isms_mcp.context import ServerContext
from isms_mcp.tools import register_all
from isms_mcp.workspace import ALLOWED_SUBTREES, WorkspaceRoot


class DummyMcp:
    """Minimal MCP stub that captures registered tool functions."""

    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


@pytest.fixture()
def workspace(tmp_path: Path) -> WorkspaceRoot:
    for sub in ALLOWED_SUBTREES:
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    return WorkspaceRoot.from_env(str(tmp_path))


@pytest.fixture()
def populated_workspace(workspace: WorkspaceRoot) -> WorkspaceRoot:
    """Workspace with sample data for all tool tests."""
    root = workspace.root

    # SoA
    soa_dir = root / "instance" / "governance" / "soa"
    soa_dir.mkdir(parents=True, exist_ok=True)
    (soa_dir / "soa.yaml").write_text(
        "controls:\n"
        "  - id: A.5.1\n"
        "    title: Policies for information security\n"
        "    theme: organisational\n"
        "    applicable: yes\n"
        "    status: implemented\n"
        "    owner: ciso\n"
        "    evidence_task_ids: [ET-001]\n"
        "  - id: A.5.2\n"
        "    title: Review of policies\n"
        "    theme: organisational\n"
        "    applicable: yes\n"
        "    status: planned\n"
        "    owner: ciso\n"
        "  - id: A.7.1\n"
        "    title: Physical security perimeters\n"
        "    theme: physical\n"
        "    applicable: no\n"
        "    status: not_assessed\n"
        "    exclusion_ref: DOC-EXC-001\n"
    )

    # Controls mapping
    ctrl_dir = root / "instance" / "governance" / "controls"
    ctrl_dir.mkdir(parents=True, exist_ok=True)
    (ctrl_dir / "mapping.yaml").write_text(
        "mappings:\n  - iso27001: A.5.1\n    nisg2026: [M1, M2]\n    gdpr: [Art.32]\n"
    )

    # Evidence plan
    (ctrl_dir / "evidence-plan.yaml").write_text(
        "evidence_tasks:\n"
        "  - id: ET-001\n"
        "    control_ids: [A.5.1]\n"
        "    cadence_days: 90\n"
        "    owner_role: ciso\n"
        "    mode: automated\n"
    )

    # Implementation statement
    impl_dir = ctrl_dir / "implementation"
    impl_dir.mkdir(parents=True, exist_ok=True)
    (impl_dir / "A.5.1.md").write_text("# A.5.1 Implementation\nPolicy published.\n")

    # Evidence attestation
    ev_dir = root / "instance" / "evidence" / "ET-001"
    ev_dir.mkdir(parents=True, exist_ok=True)
    (ev_dir / "att-2026-01.json").write_text(
        json.dumps(
            {
                "evidence_task_id": "ET-001",
                "control_id": "A.5.1",
                "collected_at": "2026-01-15T10:00:00Z",
                "collected_by": "auditor",
                "collection_method": "automated",
            }
        )
    )

    # Registers
    asset_dir = root / "instance" / "governance" / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    (asset_dir / "register.yaml").write_text(
        "assets:\n"
        "  - id: ASSET-001\n"
        "    name: Production Server\n"
        "    owner_role: it-ops\n"
        "    in_scope: true\n"
        "    classification: internal\n"
        "  - id: ASSET-002\n"
        "    name: Secret Database\n"
        "    owner_role: dba\n"
        "    in_scope: true\n"
        "    classification: restricted\n"
    )

    # Risk register
    risk_dir = root / "instance" / "governance" / "risk"
    risk_dir.mkdir(parents=True, exist_ok=True)
    (risk_dir / "register.yaml").write_text(
        "risks:\n"
        "  - id: R-001\n"
        "    title: Phishing attack\n"
        "    status: assessed\n"
        "    treatment: mitigate\n"
        "    residual_rating: medium\n"
        "    owner: ciso\n"
        "    asset_refs: [ASSET-001]\n"
        "  - id: R-002\n"
        "    title: Data breach\n"
        "    status: identified\n"
        "    treatment: mitigate\n"
        "    residual_rating: high\n"
        "    owner: dpo\n"
    )

    # Calendar
    cal_dir = root / "framework-refs" / "calendar"
    cal_dir.mkdir(parents=True, exist_ok=True)
    (cal_dir / "regulatory-calendar.yaml").write_text(
        "milestones:\n"
        "  - id: CAL-001\n"
        "    source_id: NISG-2026\n"
        "    event: NISG enforcement\n"
        "    date: 2027-01-01\n"
        "    confidence: certain\n"
        "    obligations_triggered: [register]\n"
    )

    # Config
    (root / "instance" / "config.yaml").write_text(
        "entity:\n"
        "  legal_name: Test GmbH\n"
        "  short_name: test\n"
        "  jurisdiction: AT\n"
        "  primary_language: en\n"
        "  authority_language: de\n"
        "classification:\n"
        "  nisg2026_category: essential\n"
        "  gdpr_role: controller\n"
        "  iso27001_target_cert_date: 2027-06-30\n"
    )

    return workspace


@pytest.fixture()
def ctx(populated_workspace: WorkspaceRoot) -> ServerContext:
    return ServerContext(
        workspace=populated_workspace,
        transport_mode="stdio",
        allow_restricted=True,
    )


@pytest.fixture()
def mcp(ctx: ServerContext) -> DummyMcp:
    m = DummyMcp()
    register_all(m, ctx)
    return m


# =========================================================================
# isms_info
# =========================================================================


class TestIsmsInfo:
    def test_returns_entity_info(self, mcp: DummyMcp) -> None:
        result = mcp.tools["isms_info"]()
        assert result.entity_legal_name == "Test GmbH"
        assert result.jurisdiction == "AT"
        assert result.template_is_rendered is True

    def test_spec_revision_present(self, mcp: DummyMcp) -> None:
        result = mcp.tools["isms_info"]()
        assert result.spec_revision is not None


# =========================================================================
# soa_query
# =========================================================================


class TestSoaQuery:
    def test_unfiltered(self, mcp: DummyMcp) -> None:
        result = mcp.tools["soa_query"]()
        assert result.pagination.total == 3

    def test_filter_by_theme(self, mcp: DummyMcp) -> None:
        result = mcp.tools["soa_query"](theme="physical")
        assert result.pagination.total == 1
        assert result.items[0].id == "A.7.1"

    def test_filter_by_applicable(self, mcp: DummyMcp) -> None:
        result = mcp.tools["soa_query"](applicable="yes")
        assert result.pagination.total == 2

    def test_filter_by_status(self, mcp: DummyMcp) -> None:
        result = mcp.tools["soa_query"](status="implemented")
        assert result.pagination.total == 1

    def test_filter_by_owner(self, mcp: DummyMcp) -> None:
        result = mcp.tools["soa_query"](owner="ciso")
        assert result.pagination.total == 2

    def test_filter_by_prefix(self, mcp: DummyMcp) -> None:
        result = mcp.tools["soa_query"](control_id_prefix="A.5")
        assert result.pagination.total == 2

    def test_pagination(self, mcp: DummyMcp) -> None:
        result = mcp.tools["soa_query"](page=1, page_size=2)
        assert len(result.items) == 2
        assert result.pagination.pages == 2


# =========================================================================
# control_status
# =========================================================================


class TestControlStatus:
    def test_existing_control(self, mcp: DummyMcp) -> None:
        result = mcp.tools["control_status"](control_id="A.5.1")
        assert result.control_id == "A.5.1"
        assert result.soa is not None
        assert result.implementation_statement_present is True
        assert len(result.evidence_tasks) == 1

    def test_nonexistent_control(self, mcp: DummyMcp) -> None:
        result = mcp.tools["control_status"](control_id="A.99.99")
        assert result.soa is None
        assert result.implementation_statement_present is False

    def test_crosswalk(self, mcp: DummyMcp) -> None:
        result = mcp.tools["control_status"](control_id="A.5.1")
        assert "A.5.1" in result.crosswalk.iso27001
        assert "M1" in result.crosswalk.nisg2026


# =========================================================================
# register_query
# =========================================================================


class TestRegisterQuery:
    def test_all_assets(self, mcp: DummyMcp) -> None:
        result = mcp.tools["register_query"](register="assets")
        assert result.pagination.total == 2

    def test_filter_by_owner_role(self, mcp: DummyMcp) -> None:
        result = mcp.tools["register_query"](register="assets", owner_role="it-ops")
        assert result.pagination.total == 1

    def test_classification_filter_restricted_denied(
        self, populated_workspace: WorkspaceRoot
    ) -> None:
        ctx = ServerContext(
            workspace=populated_workspace,
            transport_mode="http",
            allow_restricted=False,
        )
        m = DummyMcp()
        register_all(m, ctx)
        result = m.tools["register_query"](register="assets")
        assert result.pagination.total == 1
        assert result.items[0]["id"] == "ASSET-001"

    def test_empty_register(self, mcp: DummyMcp) -> None:
        result = mcp.tools["register_query"](register="suppliers")
        assert result.pagination.total == 0

    def test_free_text_search(self, mcp: DummyMcp) -> None:
        result = mcp.tools["register_query"](register="assets", free_text="production")
        assert result.pagination.total == 1


# =========================================================================
# risk_query
# =========================================================================


class TestRiskQuery:
    def test_all_risks(self, mcp: DummyMcp) -> None:
        result = mcp.tools["risk_query"]()
        assert result.pagination.total == 2

    def test_filter_by_status(self, mcp: DummyMcp) -> None:
        result = mcp.tools["risk_query"](status="assessed")
        assert result.pagination.total == 1

    def test_filter_by_min_residual(self, mcp: DummyMcp) -> None:
        result = mcp.tools["risk_query"](min_residual="high")
        assert result.pagination.total == 1

    def test_filter_by_asset_ref(self, mcp: DummyMcp) -> None:
        result = mcp.tools["risk_query"](asset_ref="ASSET-001")
        assert result.pagination.total == 1


# =========================================================================
# evidence_age
# =========================================================================


class TestEvidenceAge:
    def test_all_evidence(self, mcp: DummyMcp) -> None:
        result = mcp.tools["evidence_age"](state="all")
        assert result.total >= 1

    def test_filter_by_control_prefix(self, mcp: DummyMcp) -> None:
        result = mcp.tools["evidence_age"](state="all", control_id_prefix="A.5")
        assert result.total >= 1


# =========================================================================
# control_coverage
# =========================================================================


class TestControlCoverage:
    def test_coverage_report(self, mcp: DummyMcp) -> None:
        result = mcp.tools["control_coverage"]()
        assert result.total_controls == 3
        assert result.applicable == 2

    def test_filter_by_theme(self, mcp: DummyMcp) -> None:
        result = mcp.tools["control_coverage"](theme="organisational")
        assert result.total_controls == 2


# =========================================================================
# regulatory_calendar
# =========================================================================


class TestRegulatoryCalendar:
    def test_all_milestones(self, mcp: DummyMcp) -> None:
        result = mcp.tools["regulatory_calendar"]()
        assert result.total >= 1

    def test_filter_by_source(self, mcp: DummyMcp) -> None:
        result = mcp.tools["regulatory_calendar"](source_id="NISG-2026")
        assert result.total == 1

    def test_filter_by_confidence(self, mcp: DummyMcp) -> None:
        result = mcp.tools["regulatory_calendar"](confidence="certain")
        assert result.total == 1
        result_none = mcp.tools["regulatory_calendar"](confidence="uncertain")
        assert result_none.total == 0


# =========================================================================
# Smoke test from original test_smoke.py (ensuring backward compat)
# =========================================================================


def test_register_all_registers_expected_tools() -> None:
    mcp = DummyMcp()
    ctx = ServerContext(
        workspace=WorkspaceRoot(root=Path("/"), allowed_prefixes=(Path("/"),)),
        transport_mode="stdio",
        allow_restricted=True,
    )
    register_all(mcp, ctx)
    assert set(mcp.tools.keys()) == {
        "isms_info",
        "soa_query",
        "control_status",
        "register_query",
        "risk_query",
        "evidence_age",
        "control_coverage",
        "regulatory_calendar",
    }
