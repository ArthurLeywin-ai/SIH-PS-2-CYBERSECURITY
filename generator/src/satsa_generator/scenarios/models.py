"""
M4 scenario domain models.

Defines the core types for scenario definitions, plans, mutation receipts,
authorization entries, and ground-truth records. These are private domain
objects — none of their fields ever appear in operational output.

All models use Pydantic for validation and immutability, or frozen
dataclasses for lightweight internal use.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ScenarioFamily(enum.StrEnum):
    """Scenario family identifiers from GENERATOR_IMPLEMENTATION_PLAN §11."""

    EXECUTION_GAP = "EXECUTION_GAP"
    NEGATIVE_SPACE = "NEGATIVE_SPACE"
    HISTORICAL_REPETITION = "HISTORICAL_REPETITION"
    PEER_COMPARISON = "PEER_COMPARISON"
    CROSS_RECORD = "CROSS_RECORD"
    LEGITIMATE_UNUSUAL = "LEGITIMATE_UNUSUAL"
    AMBIGUOUS_INSUFFICIENT = "AMBIGUOUS_INSUFFICIENT"


class RealizationState(enum.StrEnum):
    """Four-way realization model from the user specification."""

    CONCERNING = "CONCERNING"
    LEGITIMATE_UNUSUAL = "LEGITIMATE_UNUSUAL"
    AMBIGUOUS = "AMBIGUOUS"
    NORMAL = "NORMAL"


class MutationType(enum.StrEnum):
    """Supported mutation operation types from GENERATOR_IMPLEMENTATION_PLAN §13.2."""

    REMOVE_RECORD = "REMOVE_RECORD"
    REMOVE_FIELD = "REMOVE_FIELD"
    ALTER_FIELD = "ALTER_FIELD"
    ALTER_TIMESTAMP = "ALTER_TIMESTAMP"
    ALTER_STATUS = "ALTER_STATUS"
    REMOVE_RELATIONSHIP = "REMOVE_RELATIONSHIP"
    ADD_CONTEXT_RECORD = "ADD_CONTEXT_RECORD"
    ALTER_PROPENSITY = "ALTER_PROPENSITY"
    DUPLICATE_RECORD = "DUPLICATE_RECORD"
    OMIT_FAMILY = "OMIT_FAMILY"


class AuthorizationStatus(enum.StrEnum):
    """Lifecycle status of a mutation authorization."""

    PLANNED = "PLANNED"
    APPLIED = "APPLIED"
    VALIDATED = "VALIDATED"
    FAILED = "FAILED"


class TruthRecordRole(enum.StrEnum):
    """Role of an operational record in a scenario's ground truth."""

    AFFECTED = "AFFECTED"
    SUPPORTING = "SUPPORTING"
    COUNTEREVIDENCE = "COUNTEREVIDENCE"
    DECOY = "DECOY"
    EXPECTED_BUT_ABSENT = "EXPECTED_BUT_ABSENT"


class ControlContextType(enum.StrEnum):
    """Types of legitimate control context."""

    APPROVED_EXCEPTION = "APPROVED_EXCEPTION"
    VALID_PROCESS_CHANGE = "VALID_PROCESS_CHANGE"
    MAINTENANCE_WINDOW = "MAINTENANCE_WINDOW"
    LEGITIMATE_BURST = "LEGITIMATE_BURST"
    DOCUMENTED_ESCALATION = "DOCUMENTED_ESCALATION"
    APPROVED_MONITORING_GAP = "APPROVED_MONITORING_GAP"
    VALID_ORGANIZATIONAL_CONTEXT = "VALID_ORGANIZATIONAL_CONTEXT"
    APPROVED_AUTOMATION = "APPROVED_AUTOMATION"
    APPROVED_SUPPRESSION = "APPROVED_SUPPRESSION"
    ACCEPTED_RISK = "ACCEPTED_RISK"
    EMERGENCY_WORKFLOW = "EMERGENCY_WORKFLOW"
    TOOL_MIGRATION = "TOOL_MIGRATION"
    ONBOARDING_DECOMMISSIONING = "ONBOARDING_DECOMMISSIONING"


# ---------------------------------------------------------------------------
# Scenario definition (catalog entry)
# ---------------------------------------------------------------------------


class ScenarioDefinition(BaseModel):
    """Immutable typed catalog entry for a scenario.

    Each definition describes a scenario's semantics, prerequisites,
    applicable realizations, and evidence families. It never contains
    subject IDs, hidden seeds, or detector thresholds.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    scenario_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Stable unique scenario identifier (e.g., 'EXEC-GAP-001')",
    )
    family: ScenarioFamily
    version: str = Field(default="1.0.0", max_length=20)
    description: str = Field(min_length=1, max_length=512)
    prerequisites: list[str] = Field(
        default_factory=list,
        description="Semantic prerequisites as human-readable conditions",
    )
    applicable_realizations: list[RealizationState] = Field(
        min_length=1,
        description="Which realization states this scenario supports",
    )
    evidence_families_touched: list[str] = Field(
        min_length=1,
        description="Evidence families affected by this scenario",
    )
    requires_multiple_records: bool = Field(
        default=False,
        description="Whether the scenario requires multiple target records",
    )
    supports_ambiguity: bool = Field(
        default=True,
        description="Whether ambiguous realization is meaningful for this scenario",
    )
    legitimate_control_requirements: list[ControlContextType] = Field(
        default_factory=list,
        description="Control context types required for LEGITIMATE_UNUSUAL realization",
    )
    expected_relationship_impact: list[str] = Field(
        default_factory=list,
        description="Relationships this scenario may affect (e.g., 'alert→case')",
    )
    inapplicable_realization_reasons: dict[str, str] = Field(
        default_factory=dict,
        description="Reasons why specific realizations are not applicable",
    )


# ---------------------------------------------------------------------------
# Scenario plan (private, per-instance)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScenarioPlan:
    """Private plan for a single scenario instance.

    Created by a ScenarioSelector after finding eligible subjects.
    Never appears in operational output.
    """

    plan_id: str
    scenario_id: str
    realization: RealizationState
    organization_id: str
    period_id: str
    target_record_ids: tuple[str, ...]
    target_family: str
    seed_label: str
    control_context_type: ControlContextType | None = None
    control_context_description: str | None = None
    correlation_group_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Authorization entry (private ledger record)
# ---------------------------------------------------------------------------


class AuthorizationEntry(BaseModel):
    """Private authorization for a single deliberate mutation.

    Every mutation MUST have an entry. Missing or duplicate entries
    cause build failure.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    authorization_id: str = Field(min_length=1, max_length=128)
    scenario_id: str = Field(min_length=1, max_length=64)
    plan_id: str = Field(min_length=1, max_length=128)
    realization: RealizationState
    target_record_ids: tuple[str, ...] = Field(min_length=1)
    target_family: str = Field(min_length=1, max_length=64)
    mutation_type: MutationType
    expected_semantic_effect: str = Field(min_length=1, max_length=512)
    seed_label: str = Field(min_length=1, max_length=256)
    status: AuthorizationStatus = Field(default=AuthorizationStatus.PLANNED)


# ---------------------------------------------------------------------------
# Mutation receipt (private, emitted by mutator)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MutationReceipt:
    """Private receipt emitted by a mutator after applying a mutation.

    Records the before/after state for reconciliation and truth writing.
    """

    authorization_id: str
    plan_id: str
    scenario_id: str
    mutation_type: MutationType
    target_record_ids: tuple[str, ...]
    target_family: str
    target_fields: tuple[str, ...]
    before_state: dict[str, Any]
    after_state: dict[str, Any]
    applied: bool = True


# ---------------------------------------------------------------------------
# Ground-truth record (private)
# ---------------------------------------------------------------------------


class GroundTruthRecord(BaseModel):
    """Private ground-truth record for evaluation.

    Contains all information needed to assess what scenario was intended,
    which realization was used, and what operational evidence should
    support the condition. Never enters operational output.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    truth_id: str = Field(min_length=1, max_length=128)
    scenario_id: str = Field(min_length=1, max_length=64)
    scenario_version: str = Field(max_length=20)
    scenario_family: ScenarioFamily
    plan_id: str = Field(min_length=1, max_length=128)
    realization: RealizationState
    classification: Literal[
        "ATTENTION",
        "LEGITIMATE_UNUSUAL",
        "NORMAL",
        "DATA_QUALITY_ONLY",
        "AMBIGUOUS",
    ]
    organization_id: str
    period_id: str
    affected_records: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Records with roles: AFFECTED, SUPPORTING, COUNTEREVIDENCE, etc.",
    )
    expected_evidence_description: str = Field(default="", max_length=1024)
    counterevidence_description: str = Field(default="", max_length=1024)
    mutation_provenance: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Before/after provenance from mutation receipts",
    )
    authorization_ids: list[str] = Field(default_factory=list)
    seed_label: str = Field(min_length=1, max_length=256)
    correlation_group_id: str | None = None
    ambiguity_notes: str = Field(default="", max_length=1024)
    abstention_state: str | None = Field(
        default=None,
        description="Expected insufficient-data state where relevant",
    )
    control_context_type: ControlContextType | None = None
    control_context_description: str | None = None
    evidence_families_touched: list[str] = Field(default_factory=list)
    validator_result: str = Field(default="PENDING", max_length=64)


# ---------------------------------------------------------------------------
# Legitimate control declaration
# ---------------------------------------------------------------------------


class LegitimateControlDeclaration(BaseModel):
    """Declares a legitimate reason/control context for a scenario realization.

    Built as a first-class component alongside scenario realization.
    Uses existing M2 control/process reference entities.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    control_declaration_id: str = Field(min_length=1, max_length=128)
    plan_id: str = Field(min_length=1, max_length=128)
    scenario_id: str = Field(min_length=1, max_length=64)
    control_context_type: ControlContextType
    description: str = Field(min_length=1, max_length=512)
    operational_evidence_ids: list[str] = Field(
        min_length=1,
        description="IDs of operational records that provide the control context",
    )
    effective_start_utc: str = Field(max_length=64)
    effective_end_utc: str | None = Field(default=None, max_length=64)
    is_complete: bool = Field(
        default=True,
        description="False if control evidence is intentionally incomplete (ambiguous)",
    )
