"""
Quality mutation engine — orchestrates planning, authorization, and execution
of data-quality mutations.

From GENERATOR_IMPLEMENTATION_PLAN §13:
- §13.1 Authorization record registered before execution
- §13.2 All 13 quality mutation operations supported
- §13.3 Deterministic 4-stage ordering:
  family/submission -> schema/layout -> record duplication/relationship -> field/value
- §13.4 Unexpected-defect detection: reconcile post-mutation defects against authorizations
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from satsa_generator.core.errors import GeneratorError
from satsa_generator.core.types import ValueState
from satsa_generator.ids.service import IDService
from satsa_generator.quality.models import (
    QualityExecutionResult,
    QualityMutationStage,
    QualityMutationType,
    QualityPlan,
    get_mutation_stage,
)
from satsa_generator.quality.mutators import get_quality_mutator
from satsa_generator.scenarios.ledger import AuthorizationLedger
from satsa_generator.scenarios.models import (
    AuthorizationEntry,
    AuthorizationStatus,
    MutationReceipt,
    MutationType,
    RealizationState,
)
from satsa_generator.seeds.manager import SeedManager


class QualityEngineError(GeneratorError):
    """Raised when quality mutation engine encounters an error."""


class QualityMutationEngine:
    """Coordinates data-quality mutation planning, authorization, and execution."""

    def __init__(
        self,
        ids: IDService,
        seeds: SeedManager,
        ledger: AuthorizationLedger,
    ) -> None:
        self._ids = ids
        self._seeds = seeds
        self._ledger = ledger

    @property
    def ledger(self) -> AuthorizationLedger:
        """Return the authorization ledger."""
        return self._ledger

    def plan_all_quality_mutations(
        self,
        records: dict[str, list[Any]],
        *,
        period_id: str = "P01",
    ) -> list[QualityPlan]:
        """Generate a complete, deterministic plan covering all 13 quality mutation types."""
        plans: list[QualityPlan] = []
        orgs = records.get("organization", [])
        if not orgs:
            raise QualityEngineError("Cannot plan quality mutations without organization records")

        org_id = str(orgs[0].organization_id)

        # 1. MISSING_FIELD: Alert optional field
        alerts = records.get("alert", [])
        if alerts:
            target_alert = alerts[0]
            plan_id = self._ids.generate("qual_auth", "missing_field", str(target_alert.alert_id))
            plans.append(
                QualityPlan(
                    plan_id=plan_id,
                    mutation_type=QualityMutationType.MISSING_FIELD,
                    target_family="alert",
                    target_record_id=str(target_alert.alert_id),
                    organization_id=org_id,
                    period_id=period_id,
                    target_field="source_alert_id",
                    expected_canonical_state=ValueState.NOT_PROVIDED,
                    expected_quality_issue="Optional source ID omitted",
                    expected_eligibility_consequence="Canonical UUID retained",
                    seed_label="quality/missing_field/alert/v1",
                )
            )

        # 2. MISSING_FAMILY: Submission family declaration
        sub_fams = records.get("submission_family", [])
        if sub_fams:
            target_fam = sub_fams[-1]
            plan_id = self._ids.generate(
                "qual_auth", "missing_family", str(target_fam.submission_family_id)
            )
            plans.append(
                QualityPlan(
                    plan_id=plan_id,
                    mutation_type=QualityMutationType.MISSING_FAMILY,
                    target_family=target_fam.evidence_family,
                    target_record_id=str(target_fam.submission_family_id),
                    organization_id=org_id,
                    period_id=period_id,
                    expected_canonical_state=ValueState.NOT_PROVIDED,
                    expected_quality_issue=(
                        f"Family {target_fam.evidence_family} not provided in submission"
                    ),
                    expected_eligibility_consequence="Downstream analytics blocked for family",
                    seed_label="quality/missing_family/v1",
                )
            )

        # 3. PARTIAL_SUBMISSION: Submission record
        subs = records.get("submission", [])
        if subs:
            target_sub = subs[0]
            plan_id = self._ids.generate("qual_auth", "partial_sub", str(target_sub.submission_id))
            plans.append(
                QualityPlan(
                    plan_id=plan_id,
                    mutation_type=QualityMutationType.PARTIAL_SUBMISSION,
                    target_family="submission",
                    target_record_id=str(target_sub.submission_id),
                    organization_id=org_id,
                    period_id=period_id,
                    expected_canonical_state=ValueState.UNKNOWN,
                    expected_quality_issue="Partial submission coverage period",
                    expected_eligibility_consequence="Reporting scope marked partial",
                    seed_label="quality/partial_submission/v1",
                )
            )

        # 4. MALFORMED_VALUE: Priority text or note
        if len(alerts) > 1:
            target_alert = alerts[1]
            plan_id = self._ids.generate("qual_auth", "malformed_val", str(target_alert.alert_id))
            plans.append(
                QualityPlan(
                    plan_id=plan_id,
                    mutation_type=QualityMutationType.MALFORMED_VALUE,
                    target_family="alert",
                    target_record_id=str(target_alert.alert_id),
                    organization_id=org_id,
                    period_id=period_id,
                    target_field="severity",
                    parameters={"malformed_value": "MALFORMED_PRIORITY_##%"},
                    expected_canonical_state=ValueState.INVALID,
                    expected_quality_issue="Unparseable raw priority token",
                    expected_eligibility_consequence="Default priority fallback applied",
                    seed_label="quality/malformed_value/v1",
                )
            )

        # 5. EXACT_DUPLICATE: Duplicate an alert
        if len(alerts) > 2:
            target_alert = alerts[2]
            plan_id = self._ids.generate("qual_auth", "exact_dup", str(target_alert.alert_id))
            plans.append(
                QualityPlan(
                    plan_id=plan_id,
                    mutation_type=QualityMutationType.EXACT_DUPLICATE,
                    target_family="alert",
                    target_record_id=str(target_alert.alert_id),
                    organization_id=org_id,
                    period_id=period_id,
                    expected_canonical_state=ValueState.OBSERVED_VALUE,
                    expected_quality_issue="Exact duplicate record emitted",
                    expected_eligibility_consequence="Deduplication required in analytical layer",
                    seed_label="quality/exact_duplicate/v1",
                )
            )

        # 6. CONFLICTING_DUPLICATE: Conflicting duplicate alert
        if len(alerts) > 3:
            target_alert = alerts[3]
            plan_id = self._ids.generate("qual_auth", "conflicting_dup", str(target_alert.alert_id))
            plans.append(
                QualityPlan(
                    plan_id=plan_id,
                    mutation_type=QualityMutationType.CONFLICTING_DUPLICATE,
                    target_family="alert",
                    target_record_id=str(target_alert.alert_id),
                    organization_id=org_id,
                    period_id=period_id,
                    expected_canonical_state=ValueState.INVALID,
                    expected_quality_issue="Conflicting duplicate record with altered severity",
                    expected_eligibility_consequence="Flagged as DUPLICATE_CONFLICTING",
                    seed_label="quality/conflicting_duplicate/v1",
                )
            )

        # 7. BROKEN_RELATIONSHIP: Case-alert link or alert asset link
        links = records.get("case_alert_link", [])
        if links:
            target_link = links[0]
            plan_id = self._ids.generate(
                "qual_auth", "broken_rel", str(target_link.case_alert_link_id)
            )
            plans.append(
                QualityPlan(
                    plan_id=plan_id,
                    mutation_type=QualityMutationType.BROKEN_RELATIONSHIP,
                    target_family="case_alert_link",
                    target_record_id=str(target_link.case_alert_link_id),
                    organization_id=org_id,
                    period_id=period_id,
                    target_relationship="alert_id",
                    expected_canonical_state=ValueState.NO_SUBMITTED_EVIDENCE,
                    expected_quality_issue="Unresolved alert foreign key",
                    expected_eligibility_consequence="Flagged as BROKEN_RELATIONSHIP",
                    seed_label="quality/broken_relationship/v1",
                )
            )

        # 8. TIMESTAMP_PROBLEM: Out of order timestamp
        cases = records.get("case", [])
        if cases:
            target_case = cases[0]
            plan_id = self._ids.generate("qual_auth", "timestamp_prob", str(target_case.case_id))
            plans.append(
                QualityPlan(
                    plan_id=plan_id,
                    mutation_type=QualityMutationType.TIMESTAMP_PROBLEM,
                    target_family="case",
                    target_record_id=str(target_case.case_id),
                    organization_id=org_id,
                    period_id=period_id,
                    target_field="created_at_utc",
                    expected_canonical_state=ValueState.INVALID,
                    expected_quality_issue="Impossible future event timestamp",
                    expected_eligibility_consequence="Temporal validation anomaly",
                    seed_label="quality/timestamp_problem/v1",
                )
            )

        # 9. SCHEMA_DRIFT: Alert workflow version drift
        if len(alerts) > 4:
            target_alert = alerts[4]
            plan_id = self._ids.generate("qual_auth", "schema_drift", str(target_alert.alert_id))
            plans.append(
                QualityPlan(
                    plan_id=plan_id,
                    mutation_type=QualityMutationType.SCHEMA_DRIFT,
                    target_family="alert",
                    target_record_id=str(target_alert.alert_id),
                    organization_id=org_id,
                    period_id=period_id,
                    target_field="workflow_version",
                    expected_canonical_state=ValueState.OBSERVED_VALUE,
                    expected_quality_issue="Workflow schema version drift",
                    expected_eligibility_consequence="Schema evolution tracking required",
                    seed_label="quality/schema_drift/v1",
                )
            )

        # 10. VOCABULARY_DRIFT: Priority vocabulary drift
        if len(alerts) > 5:
            target_alert = alerts[5]
            plan_id = self._ids.generate("qual_auth", "vocab_drift", str(target_alert.alert_id))
            plans.append(
                QualityPlan(
                    plan_id=plan_id,
                    mutation_type=QualityMutationType.VOCABULARY_DRIFT,
                    target_family="alert",
                    target_record_id=str(target_alert.alert_id),
                    organization_id=org_id,
                    period_id=period_id,
                    target_field="severity",
                    expected_canonical_state=ValueState.UNKNOWN,
                    expected_quality_issue="Unmapped custom vocabulary token",
                    expected_eligibility_consequence="Mapped to UNKNOWN vocabulary warning",
                    seed_label="quality/vocabulary_drift/v1",
                )
            )

        # 11. LATE_ARRIVAL: Alert arrives in later submission
        if len(alerts) > 6:
            target_alert = alerts[6]
            plan_id = self._ids.generate("qual_auth", "late_arrival", str(target_alert.alert_id))
            plans.append(
                QualityPlan(
                    plan_id=plan_id,
                    mutation_type=QualityMutationType.LATE_ARRIVAL,
                    target_family="alert",
                    target_record_id=str(target_alert.alert_id),
                    organization_id=org_id,
                    period_id=period_id,
                    target_field="created_at_utc",
                    expected_canonical_state=ValueState.OBSERVED_VALUE,
                    expected_quality_issue="Event submitted in subsequent reporting submission",
                    expected_eligibility_consequence="Late arrival reconciliation required",
                    seed_label="quality/late_arrival/v1",
                )
            )

        # 12. COUNT_MISMATCH: Manifest count altered
        sub_fams = records.get("submission_family", [])
        if sub_fams:
            target_sub_fam = sub_fams[0]
            plan_id = self._ids.generate(
                "qual_auth", "count_mismatch", str(target_sub_fam.submission_family_id)
            )
            plans.append(
                QualityPlan(
                    plan_id=plan_id,
                    mutation_type=QualityMutationType.COUNT_MISMATCH,
                    target_family="submission_family",
                    target_record_id=str(target_sub_fam.submission_family_id),
                    organization_id=org_id,
                    period_id=period_id,
                    target_field="declared_record_count",
                    expected_canonical_state=ValueState.INVALID,
                    expected_quality_issue="Submission family declared count mismatch",
                    expected_eligibility_consequence="Submission quality audit warning",
                    seed_label="quality/count_mismatch/v1",
                )
            )

        # 13. SOURCE_ID_ABSENCE: Case source ID omitted
        if cases:
            target_case = cases[-1]
            plan_id = self._ids.generate("qual_auth", "source_id_absence", str(target_case.case_id))
            plans.append(
                QualityPlan(
                    plan_id=plan_id,
                    mutation_type=QualityMutationType.SOURCE_ID_ABSENCE,
                    target_family="case",
                    target_record_id=str(target_case.case_id),
                    organization_id=org_id,
                    period_id=period_id,
                    target_field="case_id",
                    expected_canonical_state=ValueState.NOT_PROVIDED,
                    expected_quality_issue="Native source case ID omitted",
                    expected_eligibility_consequence="Canonical UUID used as sole identifier",
                    seed_label="quality/source_id_absence/v1",
                )
            )

        return plans

    def pre_authorize_plans(self, plans: list[QualityPlan]) -> list[AuthorizationEntry]:
        """Register authorizations in AuthorizationLedger for quality plans prior to execution."""
        authorizations: list[AuthorizationEntry] = []
        for plan in plans:
            m_type = MutationType(plan.mutation_type.value)
            auth_entry = AuthorizationEntry(
                authorization_id=plan.plan_id,
                scenario_id="QUALITY_ENGINE",
                plan_id=plan.plan_id,
                realization=RealizationState.CONCERNING,
                target_record_ids=(plan.target_record_id,),
                target_family=plan.target_family,
                mutation_type=m_type,
                expected_semantic_effect=plan.expected_quality_issue
                or f"Quality mutation {plan.mutation_type}",
                seed_label=plan.seed_label or f"quality/{plan.mutation_type.value.lower()}/v1",
                status=AuthorizationStatus.PLANNED,
                target_field=plan.target_field,
                expected_canonical_state=plan.expected_canonical_state.value,
                expected_quality_issue=plan.expected_quality_issue,
            )
            self._ledger.authorize(auth_entry)
            authorizations.append(auth_entry)
        return authorizations

    def execute_quality_mutations(
        self,
        records: dict[str, list[Any]],
        plans: list[QualityPlan] | None = None,
        source_exports_root: Path | None = None,
    ) -> QualityExecutionResult:
        """Execute quality mutations with strict 4-stage ordering and unexpected defect checking."""
        if plans is None:
            plans = self.plan_all_quality_mutations(records)

        # Pre-authorize all plans in the ledger first
        auths = self.pre_authorize_plans(plans)

        # Order plans deterministically by stage (§13.3)
        stage_order = {
            QualityMutationStage.STAGE_1_FAMILY_SUBMISSION: 1,
            QualityMutationStage.STAGE_2_SCHEMA_LAYOUT: 2,
            QualityMutationStage.STAGE_3_RECORD_RELATIONSHIP: 3,
            QualityMutationStage.STAGE_4_FIELD_VALUE: 4,
        }
        sorted_plans = sorted(
            plans,
            key=lambda p: (stage_order[get_mutation_stage(p.mutation_type)], p.plan_id),
        )

        current_records = records
        receipts: list[MutationReceipt] = []

        for plan in sorted_plans:
            mutator_fn = get_quality_mutator(plan.mutation_type)
            current_records, receipt = mutator_fn(
                plan,
                current_records,
                self._seeds,
                self._ledger,
                source_exports_root=source_exports_root,
            )
            receipts.append(receipt)

        # Reconcile unexpected defects (§13.4):
        # Every receipt must have a consumed authorization
        applied_auth_ids = {r.authorization_id for r in receipts}
        for auth in auths:
            if auth.authorization_id not in applied_auth_ids:
                raise QualityEngineError(
                    f"Unconsumed quality authorization detected: {auth.authorization_id}"
                )

        return QualityExecutionResult(
            records=current_records,
            receipts=tuple(receipts),
            plans=tuple(sorted_plans),
            authorizations=tuple(auths),
        )
