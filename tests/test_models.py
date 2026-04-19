"""Tests for Pydantic models: validation, serialization, edge cases."""

import pytest
from pydantic import ValidationError

from isms_mcp.models import (
    CalendarMilestone,
    CoverageReport,
    IsmsInfo,
    Pagination,
    RegisterQuery,
    RegisterQueryResult,
    RiskEntry,
    SoaEntry,
    SoaQuery,
)


class TestPagination:
    def test_valid(self) -> None:
        p = Pagination(page=1, page_size=50, total=100, pages=2)
        assert p.page == 1

    def test_page_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            Pagination(page=0, page_size=50, total=100, pages=2)

    def test_page_size_max(self) -> None:
        with pytest.raises(ValidationError):
            Pagination(page=1, page_size=201, total=100, pages=2)


class TestSoaEntry:
    def test_minimal(self) -> None:
        entry = SoaEntry(
            id="A.5.1",
            title="Test",
            applicable="yes",
            status="planned",
        )
        assert entry.id == "A.5.1"
        assert entry.evidence_task_ids == []

    def test_with_all_fields(self) -> None:
        entry = SoaEntry(
            id="A.5.1",
            title="Test",
            theme="organisational",
            applicable="yes",
            status="implemented",
            owner="ciso",
            evidence_task_ids=["ET-001"],
            justification_ref="DOC-001",
        )
        assert entry.theme == "organisational"
        assert len(entry.evidence_task_ids) == 1


class TestSoaQuery:
    def test_defaults(self) -> None:
        q = SoaQuery()
        assert q.page == 1
        assert q.page_size == 50
        assert q.control_id_prefix is None


class TestRegisterQuery:
    def test_alias_field(self) -> None:
        q = RegisterQuery(register_name="assets")
        data = q.model_dump(by_alias=True)
        assert data["register"] == "assets"

    def test_from_alias(self) -> None:
        q = RegisterQuery.model_validate({"register": "facilities"})
        assert q.register_name == "facilities"


class TestRegisterQueryResult:
    def test_alias_serialization(self) -> None:
        r = RegisterQueryResult(
            register_name="assets",
            items=[],
            pagination=Pagination(page=1, page_size=50, total=0, pages=0),
        )
        data = r.model_dump(by_alias=True)
        assert data["register"] == "assets"


class TestRiskEntry:
    def test_extra_fields_allowed(self) -> None:
        entry = RiskEntry(
            id="R-001",
            title="Test",
            status="identified",
            extra_field="allowed",
        )
        assert entry.id == "R-001"


class TestCoverageReport:
    def test_full_report(self) -> None:
        report = CoverageReport(
            total_controls=10,
            applicable=8,
            with_implementation_statement=6,
            without_implementation_statement=["A.5.3", "A.5.4"],
            with_evidence_task_bound=5,
            without_evidence_task_bound=["A.5.5"],
            with_recent_evidence=3,
            stale_evidence=["A.5.6"],
            never_collected=["A.5.7"],
        )
        assert report.total_controls == 10


class TestIsmsInfo:
    def test_creation(self) -> None:
        info = IsmsInfo(
            entity_legal_name="Test GmbH",
            entity_short_name="test",
            jurisdiction="AT",
            nisg2026_category="essential",
            gdpr_role="controller",
            iso27001_target_cert_date="2027-06-30",
            primary_language="en",
            authority_language="de",
            workspace_path="/ws",
            template_is_rendered=True,
            isms_repo_rev=None,
            spec_revision="2025-11-25",
        )
        assert info.entity_legal_name == "Test GmbH"


class TestCalendarMilestone:
    def test_with_days_until(self) -> None:
        m = CalendarMilestone(
            id="M1",
            source_id="S1",
            event="Deadline",
            date="2027-01-01",
            days_until_due=365,
        )
        assert m.days_until_due == 365
