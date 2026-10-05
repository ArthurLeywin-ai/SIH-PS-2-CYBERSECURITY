"""
Data-quality mutation models.

Implements the data-quality mutation types and authorization contracts
specified in GENERATOR_IMPLEMENTATION_PLAN §13 and DATASET_GENERATION_SPEC §21.

Every quality defect is deliberate, pre-authorized in the private
AuthorizationLedger, traceable to a named RNG stream, and produces a
private MutationReceipt.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any

from satsa_generator.core.types import ValueState
from satsa_generator.scenarios.models import (
    AuthorizationEntry,
    MutationReceipt,
)


class QualityMutationType(enum.StrEnum):
    """The 13 data-quality mutation types from GENERATOR_IMPLEMENTATION_PLAN §13.2."""

    MISSING_FIELD = "MISSING_FIELD"
    MISSING_FAMILY = "MISSING_FAMILY"
    PARTIAL_SUBMISSION = "PARTIAL_SUBMISSION"
    MALFORMED_VALUE = "MALFORMED_VALUE"
    EXACT_DUPLICATE = "EXACT_DUPLICATE"
    CONFLICTING_DUPLICATE = "CONFLICTING_DUPLICATE"
    BROKEN_RELATIONSHIP = "BROKEN_RELATIONSHIP"
    TIMESTAMP_PROBLEM = "TIMESTAMP_PROBLEM"
    SCHEMA_DRIFT = "SCHEMA_DRIFT"
    VOCABULARY_DRIFT = "VOCABULARY_DRIFT"
    LATE_ARRIVAL = "LATE_ARRIVAL"
    COUNT_MISMATCH = "COUNT_MISMATCH"
    SOURCE_ID_ABSENCE = "SOURCE_ID_ABSENCE"


class QualityMutationStage(enum.StrEnum):
    """Deterministic 4-stage mutation ordering from GENERATOR_IMPLEMENTATION_PLAN §13.3."""

    STAGE_1_FAMILY_SUBMISSION = "STAGE_1_FAMILY_SUBMISSION"
    STAGE_2_SCHEMA_LAYOUT = "STAGE_2_SCHEMA_LAYOUT"
    STAGE_3_RECORD_RELATIONSHIP = "STAGE_3_RECORD_RELATIONSHIP"
    STAGE_4_FIELD_VALUE = "STAGE_4_FIELD_VALUE"


def get_mutation_stage(mutation_type: QualityMutationType) -> QualityMutationStage:
    """Return the mandatory execution stage for a quality mutation type."""
    if mutation_type in (
        QualityMutationType.MISSING_FAMILY,
        QualityMutationType.PARTIAL_SUBMISSION,
        QualityMutationType.COUNT_MISMATCH,
        QualityMutationType.LATE_ARRIVAL,
    ):
        return QualityMutationStage.STAGE_1_FAMILY_SUBMISSION
    elif mutation_type in (
        QualityMutationType.SCHEMA_DRIFT,
        QualityMutationType.SOURCE_ID_ABSENCE,
    ):
        return QualityMutationStage.STAGE_2_SCHEMA_LAYOUT
    elif mutation_type in (
        QualityMutationType.EXACT_DUPLICATE,
        QualityMutationType.CONFLICTING_DUPLICATE,
        QualityMutationType.BROKEN_RELATIONSHIP,
    ):
        return QualityMutationStage.STAGE_3_RECORD_RELATIONSHIP
    else:
        return QualityMutationStage.STAGE_4_FIELD_VALUE


@dataclass(frozen=True)
class QualityPlan:
    """Plan for applying a single authorized data-quality mutation."""

    plan_id: str
    mutation_type: QualityMutationType
    target_family: str
    target_record_id: str
    organization_id: str
    period_id: str
    target_field: str | None = None
    target_relationship: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    expected_source_rendering: str | None = None
    expected_canonical_state: ValueState = ValueState.NOT_PROVIDED
    expected_quality_issue: str = ""
    expected_eligibility_consequence: str = ""
    seed_label: str = ""
    validator_id: str = "VAL-QUALITY"
    correlation_group: str | None = None


@dataclass(frozen=True)
class QualityExecutionResult:
    """Outcome of executing quality mutations across records."""

    records: dict[str, list[Any]]
    receipts: tuple[MutationReceipt, ...]
    plans: tuple[QualityPlan, ...]
    authorizations: tuple[AuthorizationEntry, ...]
