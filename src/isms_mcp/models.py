"""Pydantic models for tool inputs and structured outputs.

FastMCP derives JSON Schemas from these types and the agent receives them as
structured tool output (per MCP spec revision 2025-06-18 and later).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# =========================================================================
# Pagination
# =========================================================================


class Pagination(BaseModel):
    """Pagination envelope returned alongside list payloads."""

    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=200)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)


# =========================================================================
# isms_info
# =========================================================================


class IsmsInfo(BaseModel):
    entity_legal_name: str | None
    entity_short_name: str | None
    jurisdiction: str | None
    nisg2026_category: str | None
    gdpr_role: str | None
    iso27001_target_cert_date: str | None
    primary_language: str
    authority_language: str
    workspace_path: str
    template_is_rendered: bool
    isms_repo_rev: str | None
    spec_revision: str


# =========================================================================
# SoA
# =========================================================================

ThemeName = Literal["organisational", "people", "physical", "technological"]
ApplicableFlag = Literal["yes", "no"]
ControlStatusName = Literal[
    "not_assessed", "planned", "implementing", "implemented", "monitored"
]


class SoaEntry(BaseModel):
    id: str
    title: str
    theme: ThemeName | None = None
    applicable: ApplicableFlag
    justification_ref: str | None = None
    exclusion_ref: str | None = None
    implementation_ref: str | None = None
    status: ControlStatusName
    evidence_task_ids: list[str] = Field(default_factory=list)
    owner: str | None = None
    last_review_date: str | None = None


class SoaQuery(BaseModel):
    control_id_prefix: str | None = None
    theme: ThemeName | None = None
    applicable: ApplicableFlag | None = None
    status: ControlStatusName | None = None
    owner: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class SoaQueryResult(BaseModel):
    items: list[SoaEntry]
    pagination: Pagination


# =========================================================================
# Crosswalk + control_status
# =========================================================================


class CrosswalkSlice(BaseModel):
    iso27001: list[str] = Field(default_factory=list)
    nisg2026: list[str] = Field(default_factory=list)
    implreg_2024_2690: list[str] = Field(default_factory=list, alias="implreg-2024-2690")
    gdpr: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class EvidenceTaskSummary(BaseModel):
    id: str
    control_ids: list[str]
    cadence_days: int | None = None
    mode: str | None = None
    owner_role: str | None = None
    sop_ref: str | None = None


class AttestationSummary(BaseModel):
    evidence_task_id: str | None = None
    control_id: str | None = None
    collected_at: str
    collected_by: str | None = None
    collection_method: str | None = None
    path: str


class ControlStatus(BaseModel):
    control_id: str
    title: str
    theme: ThemeName | None = None
    soa: SoaEntry | None
    implementation_statement_present: bool
    implementation_statement_path: str | None
    evidence_tasks: list[EvidenceTaskSummary]
    latest_attestation: AttestationSummary | None
    days_since_last_attestation: int | None
    cadence_days: int | None
    stale: bool
    crosswalk: CrosswalkSlice


class CrosswalkQuery(BaseModel):
    control_id: str
    framework: str | None = None


# =========================================================================
# Registers
# =========================================================================

RegisterName = Literal["assets", "facilities", "networks", "suppliers", "data"]


class RegisterQuery(BaseModel):
    register: RegisterName
    id_prefix: str | None = None
    owner_role: str | None = None
    in_scope: bool | None = None
    lifecycle_status: str | None = None
    classification: str | None = None
    free_text: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class RegisterEntry(BaseModel):
    """Generic shape: registers are heterogeneous; preserve all fields."""

    model_config = {"extra": "allow"}

    id: str


class RegisterQueryResult(BaseModel):
    register: RegisterName
    items: list[dict[str, Any]]
    pagination: Pagination


# =========================================================================
# Risk
# =========================================================================

RiskStatus = Literal[
    "identified", "assessed", "treating", "treated", "accepted", "closed"
]
RiskTreatment = Literal["accept", "mitigate", "transfer", "avoid"]
RatingLow = Literal["low", "medium", "high", "severe"]


class RiskEntry(BaseModel):
    model_config = {"extra": "allow"}

    id: str
    title: str
    status: RiskStatus


class RiskQuery(BaseModel):
    status: RiskStatus | None = None
    treatment: RiskTreatment | None = None
    min_residual: RatingLow | None = None
    owner: str | None = None
    asset_ref: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class RiskQueryResult(BaseModel):
    items: list[dict[str, Any]]
    pagination: Pagination


# =========================================================================
# Evidence age
# =========================================================================

EvidenceState = Literal["ok", "stale", "never"]
EvidenceStateFilter = Literal["ok", "stale", "never", "all"]


class EvidenceAgeQuery(BaseModel):
    state: EvidenceStateFilter = "stale"
    control_id_prefix: str | None = None
    owner_role: str | None = None


class EvidenceAgeEntry(BaseModel):
    task_id: str
    control_ids: list[str]
    cadence_days: int | None
    last_collected_at: str | None
    age_days: int | None
    state: EvidenceState
    sop_ref: str | None
    owner_role: str | None


class EvidenceAgeResult(BaseModel):
    items: list[EvidenceAgeEntry]
    total: int


# =========================================================================
# Coverage
# =========================================================================


class CoverageQuery(BaseModel):
    theme: ThemeName | None = None
    applicable_only: bool = True


class CoverageReport(BaseModel):
    total_controls: int
    applicable: int
    with_implementation_statement: int
    without_implementation_statement: list[str]
    with_evidence_task_bound: int
    without_evidence_task_bound: list[str]
    with_recent_evidence: int
    stale_evidence: list[str]
    never_collected: list[str]


# =========================================================================
# Calendar + sources
# =========================================================================

ConfidenceName = Literal["certain", "likely", "uncertain", "planned"]


class CalendarQuery(BaseModel):
    within_days: int | None = Field(default=None, ge=0)
    source_id: str | None = None
    confidence: ConfidenceName | None = None


class CalendarMilestone(BaseModel):
    id: str
    source_id: str
    event: str
    date: str
    confidence: ConfidenceName | None = None
    obligations_triggered: list[str] = Field(default_factory=list)
    artifacts_requiring_readiness: list[str] = Field(default_factory=list)
    review_at: str | None = None
    responsible_role: str | None = None
    days_until_due: int | None = None


class CalendarResult(BaseModel):
    items: list[CalendarMilestone]
    total: int


class SourceQuery(BaseModel):
    jurisdiction: str | None = None
    tracking_mode: str | None = None


class SourceEntry(BaseModel):
    model_config = {"extra": "allow"}

    id: str
    short_title: str
    long_title: str | None = None
    jurisdiction: str | None = None
    type: str | None = None
    current_version: str | None = None
    current_version_date: str | None = None
    check_frequency_days: int | None = None
    next_check_date: str | None = None
    tracking_mode: str | None = None
    responsible_role: str | None = None


class SourceResult(BaseModel):
    items: list[SourceEntry]
    total: int


# =========================================================================
# Impact probe
# =========================================================================


class ImpactProbeQuery(BaseModel):
    source_id: str


class ImpactProbe(BaseModel):
    source_id: str
    source_title: str
    current_version: str | None
    iso27001_controls_affected: list[str]
    gdpr_articles_affected: list[str]
    implementation_statements_to_revisit: list[str]
    soa_entries_to_update: list[str]
    evidence_tasks_bound: list[str]
    suppliers_in_scope_with_matching_data_residency: list[str]
    calendar_milestones: list[str]
    suggested_artefacts_to_bump: list[str]


# =========================================================================
# Decisions
# =========================================================================


class DecisionSearchQuery(BaseModel):
    query: str = Field(min_length=1)
    include_draft: bool = True
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class DecisionHit(BaseModel):
    id: str
    title: str | None
    status: str | None
    approved_date: str | None
    approved_by: str | None
    context: str
    path: str


class DecisionSearchResult(BaseModel):
    items: list[DecisionHit]
    pagination: Pagination


# =========================================================================
# Validation
# =========================================================================

ValidatorName = Literal[
    "frontmatter",
    "registers",
    "calendar",
    "crossrefs",
    "law_references",
    "signatures",
    "supersession",
    "bilingual",
    "doc_type_coverage",
]


class ValidateQuery(BaseModel):
    validators: list[ValidatorName] | None = None


class Violation(BaseModel):
    path: str
    rule: str
    message: str


class ValidationResult(BaseModel):
    validator: str
    status: Literal["pass", "fail", "skipped"]
    files_checked: int
    violations: list[Violation]
    elapsed_ms: int


class ValidateResult(BaseModel):
    results: list[ValidationResult]
