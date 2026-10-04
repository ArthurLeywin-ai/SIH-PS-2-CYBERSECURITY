"""
Legitimate-control engine — generates first-class operational control context.

From GENERATOR_IMPLEMENTATION_PLAN §12:
- Controls implement operational context records rather than merely
  suppressing a truth label.
- Supports 13 control context types (approved automation, maintenance window,
  accepted risk, emergency workflow, process change, suppression, etc.).
- Ambiguous controls are imperfect: incomplete approval, partial scope,
  or expired effective intervals.
- Generates genuine ExceptionRecord and ProcessChangeRecord objects
  that seamlessly integrate into the operational fixture.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from satsa_generator.core.errors import GeneratorError
from satsa_generator.fixture.models import (
    ControlProcessSubjectLinkRecord,
    ExceptionRecord,
    ProcessChangeRecord,
)
from satsa_generator.ids.service import IDService
from satsa_generator.scenarios.models import (
    ControlContextType,
    LegitimateControlDeclaration,
    ScenarioPlan,
)
from satsa_generator.scenarios.selectors import select_m2_control_reference
from satsa_generator.seeds.manager import SeedManager


class LegitimateControlError(GeneratorError):
    """Raised when legitimate control requirements or references are invalid."""


# Mapping of ControlContextType to ExceptionRecord exception_type
_CONTROL_TO_EXCEPTION_TYPE: dict[ControlContextType, str] = {
    ControlContextType.APPROVED_AUTOMATION: "APPROVED_AUTOMATION",
    ControlContextType.APPROVED_SUPPRESSION: "APPROVED_SUPPRESSION",
    ControlContextType.MAINTENANCE_WINDOW: "MAINTENANCE_WINDOW",
    ControlContextType.LEGITIMATE_BURST: "KNOWN_EXCEPTION",
    ControlContextType.DOCUMENTED_ESCALATION: "EMERGENCY_PROCESS",
    ControlContextType.APPROVED_MONITORING_GAP: "MAINTENANCE_WINDOW",
    ControlContextType.VALID_ORGANIZATIONAL_CONTEXT: "POLICY_CHANGE",
    ControlContextType.ACCEPTED_RISK: "ACCEPTED_RISK",
    ControlContextType.EMERGENCY_WORKFLOW: "EMERGENCY_PROCESS",
    ControlContextType.TOOL_MIGRATION: "MIGRATION_PERIOD",
    ControlContextType.ONBOARDING_DECOMMISSIONING: "TEMPORARY_DECOMMISSIONING",
    ControlContextType.VALID_PROCESS_CHANGE: "WORKFLOW_CHANGE",
    ControlContextType.APPROVED_EXCEPTION: "KNOWN_EXCEPTION",
}

# Mapping of target family to ExceptionRecord target_type
_FAMILY_TO_TARGET_TYPE: dict[str, str] = {
    "case": "CASE",
    "alert": "ALERT",
    "asset": "ASSET",
    "organization": "ORGANIZATION",
    "investigation": "INVESTIGATION",
    "escalation": "ESCALATION",
    "action": "ACTION",
    "monitoring_coverage": "ASSET",
    "resolution": "CASE",
    "closure": "CASE",
}


class LegitimateControlEngine:
    """Generates genuine operational control context records for scenarios."""

    def __init__(self, ids: IDService, seeds: SeedManager) -> None:
        self._ids = ids
        self._seeds = seeds

    def declare_control(
        self,
        plan: ScenarioPlan,
        records: dict[str, list[Any]],
        *,
        is_complete: bool = True,
    ) -> tuple[LegitimateControlDeclaration, dict[str, list[Any]]]:
        """Create and inject legitimate control context into operational records.

        Args:
            plan: The scenario plan requesting control context.
            records: Post-mutation or pre-mutation operational evidence records.
            is_complete: True for LEGITIMATE_UNUSUAL; False for AMBIGUOUS.

        Returns:
            Tuple of (LegitimateControlDeclaration, updated records dictionary).
        """
        control_type = plan.control_context_type or ControlContextType.APPROVED_EXCEPTION
        org_id = UUID(plan.organization_id)

        target_family = plan.target_family
        target_type = _FAMILY_TO_TARGET_TYPE.get(target_family, "ORGANIZATION")

        first_target_id: UUID | None = None
        if plan.target_record_ids:
            try:
                first_target_id = UUID(plan.target_record_ids[0])
            except ValueError:
                first_target_id = None

        # Authoritative M2 control reference selection
        ctrl_refs = records.get("control_process_reference", [])
        if not ctrl_refs:
            raise LegitimateControlError(
                "No control_process_reference records found in operational evidence"
            )

        ref = None
        if plan.control_process_ref_id:
            for r in ctrl_refs:
                if (
                    str(r.control_process_ref_id) == plan.control_process_ref_id
                    or r.reference_code == plan.control_process_ref_id
                ):
                    ref = r
                    break
            if ref is None:
                raise LegitimateControlError(
                    f"Control reference '{plan.control_process_ref_id}' "
                    "not found in operational evidence",
                    context={"control_process_ref_id": plan.control_process_ref_id},
                )
        else:
            ref = select_m2_control_reference(plan.scenario_id, target_family, ctrl_refs)

        exception_type_str = _CONTROL_TO_EXCEPTION_TYPE.get(control_type, "KNOWN_EXCEPTION")

        # Stable timestamps within typical period range
        start_utc = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        end_utc = datetime(2026, 6, 30, 23, 59, 59, tzinfo=UTC)

        exception_uuid = UUID(
            self._ids.generate(
                "control_exception",
                plan.plan_id,
                control_type.value,
                str(is_complete),
            )
        )

        approved_state = "APPROVED" if is_complete else "PENDING"
        applicability_state = "APPLIES" if is_complete else "PARTIALLY_APPLIES"
        quality_state = "VALID" if is_complete else "INCOMPLETE"
        role_code = "ROLE-SOC-LEAD" if is_complete else None
        evidence_token = exception_uuid.hex[:8].upper()
        evidence_ref = f"REF-TICKET-{evidence_token}" if is_complete else "DRAFT-UNCONFIRMED"

        desc = (
            plan.control_context_description
            or f"Legitimate operational control context: {control_type.value}"
        )
        if not is_complete:
            desc = f"[INCOMPLETE_APPROVAL] {desc}"

        exception_record = ExceptionRecord(
            exception_id=exception_uuid,
            source_exception_id=f"EXC-CTRL-{evidence_token}",
            organization_id=org_id,
            exception_type=exception_type_str,
            target_type=target_type,
            target_id=first_target_id,
            rule_expectation_id=ref.control_process_ref_id,
            applicability_state=applicability_state,
            approved_state=approved_state,
            approved_by_role_code=role_code,
            reason=desc,
            effective_start_at_utc=start_utc,
            effective_end_at_utc=end_utc,
            created_at_utc=start_utc,
            evidence_reference=evidence_ref,
            scope_definition={
                "target_family": target_family,
                "scope_status": "CONFIRMED" if is_complete else "UNCONFIRMED",
            },
            exception_quality_state=quality_state,
        )

        # Inject exception record into operational records
        updated_records = {k: list(v) for k, v in records.items()}
        updated_records.setdefault("exception", []).append(exception_record)

        # Subject link resolution / injection
        subject_id = first_target_id if first_target_id is not None else org_id
        subject_links = records.get("control_process_subject_link", [])
        existing_link = next(
            (
                link
                for link in subject_links
                if str(link.control_process_ref_id) == str(ref.control_process_ref_id)
                and str(link.subject_id) == str(subject_id)
            ),
            None,
        )

        if existing_link is not None:
            link_uuid = existing_link.control_process_link_id
        else:
            link_uuid = UUID(
                self._ids.generate(
                    "control_process_link",
                    plan.plan_id,
                    str(subject_id),
                    ref.reference_code,
                )
            )
            new_link = ControlProcessSubjectLinkRecord(
                control_process_link_id=link_uuid,
                control_process_ref_id=ref.control_process_ref_id,
                subject_type=target_type,
                subject_id=subject_id,
                link_role="EXCEPTION_FOR" if is_complete else "SUPPORTS",
                source_type="RULE_CONFIGURATION",
                quality_state="VALID" if is_complete else "INCOMPLETE",
                effective_start_at_utc=start_utc,
                effective_end_at_utc=end_utc,
            )
            updated_records.setdefault("control_process_subject_link", []).append(new_link)

        operational_ids = [str(exception_uuid), str(link_uuid)]

        # For process changes, also inject a ProcessChangeRecord
        if control_type in (
            ControlContextType.VALID_PROCESS_CHANGE,
            ControlContextType.APPROVED_AUTOMATION,
            ControlContextType.TOOL_MIGRATION,
        ):
            proc_change_uuid = UUID(
                self._ids.generate(
                    "control_process_change",
                    plan.plan_id,
                    control_type.value,
                )
            )
            change_type = (
                "TOOLING" if control_type == ControlContextType.TOOL_MIGRATION else "WORKFLOW"
            )
            proc_change_record = ProcessChangeRecord(
                process_change_id=proc_change_uuid,
                organization_id=org_id,
                change_type=change_type,
                effective_at_utc=start_utc,
                end_at_utc=end_utc,
                previous_version="v1.0",
                new_version="v2.0",
                affected_families=[target_family],
                change_summary=desc,
                approved_state=approved_state,
                exception_id=exception_uuid,
            )
            updated_records.setdefault("process_change", []).append(proc_change_record)
            operational_ids.append(str(proc_change_uuid))

        decl_id = self._ids.generate(
            "control_declaration",
            plan.plan_id,
            control_type.value,
        )

        declaration = LegitimateControlDeclaration(
            control_declaration_id=decl_id,
            plan_id=plan.plan_id,
            scenario_id=plan.scenario_id,
            control_context_type=control_type,
            description=desc,
            operational_evidence_ids=operational_ids,
            effective_start_utc=start_utc.isoformat(),
            effective_end_utc=end_utc.isoformat(),
            control_process_ref_id=str(ref.control_process_ref_id),
            control_process_link_id=str(link_uuid),
            is_complete=is_complete,
        )

        return declaration, updated_records
