"""
Scenario engine — orchestrates scenario selection, control injection,
mutation, validation, and truth recording.

From GENERATOR_IMPLEMENTATION_PLAN §11, §12:
- Coordinates ScenarioSelector, ScenarioMutator, LegitimateControlEngine,
  ScenarioValidator, and GroundTruthWriter.
- Guarantees strict interface separation and copy-on-write semantics.
- Manages the AuthorizationLedger ensuring every deliberate mutation has an
  authorization entry, is consumed, and is validated.
- Ensures private ground truth is strictly separated from operational data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from satsa_generator.core.errors import GeneratorError
from satsa_generator.ids.service import IDService
from satsa_generator.scenarios.catalog import get_catalog, get_scenario
from satsa_generator.scenarios.controls import LegitimateControlEngine
from satsa_generator.scenarios.ledger import AuthorizationLedger
from satsa_generator.scenarios.models import (
    ControlContextType,
    GroundTruthRecord,
    LegitimateControlDeclaration,
    MutationReceipt,
    RealizationState,
    ScenarioPlan,
)
from satsa_generator.scenarios.mutators import ScenarioMutator
from satsa_generator.scenarios.selectors import ScenarioSelector
from satsa_generator.scenarios.truth import GroundTruthWriter, LeakageScanner
from satsa_generator.scenarios.validators import (
    ScenarioValidationReport,
    ScenarioValidator,
)
from satsa_generator.seeds.manager import SeedManager


class ScenarioEngineError(GeneratorError):
    """Raised when the scenario engine encounters an unrecoverable error."""


@dataclass(frozen=True)
class ScenarioExecutionResult:
    """Complete results from running the M4 scenario engine."""

    records: dict[str, list[Any]]
    ground_truth_records: tuple[GroundTruthRecord, ...]
    validation_reports: tuple[ScenarioValidationReport, ...]
    receipts: tuple[MutationReceipt, ...]
    control_declarations: tuple[LegitimateControlDeclaration, ...]
    ledger: AuthorizationLedger
    plans: tuple[ScenarioPlan, ...] = field(default_factory=tuple)


class ScenarioEngine:
    """Orchestrates scenario lifecycle for SAT-SA M4."""

    def __init__(
        self,
        ids: IDService,
        seeds: SeedManager,
        *,
        ledger: AuthorizationLedger | None = None,
    ) -> None:
        self._ids = ids
        self._seeds = seeds
        self._ledger = ledger if ledger is not None else AuthorizationLedger()

        self._selector = ScenarioSelector(seeds, ids)
        self._mutator = ScenarioMutator(seeds, self._ledger)
        self._controls = LegitimateControlEngine(ids, seeds)
        self._validator = ScenarioValidator(self._ledger)
        self._truth_writer = GroundTruthWriter(ids)

    @property
    def ledger(self) -> AuthorizationLedger:
        """Return the authorization ledger."""
        return self._ledger

    @property
    def truth_writer(self) -> GroundTruthWriter:
        """Return the ground truth writer."""
        return self._truth_writer

    def plan_scenarios(
        self,
        records: dict[str, list[Any]],
        *,
        target_org_ids: list[str] | None = None,
        period_id: str = "P01",
        include_all_families: bool = True,
    ) -> list[ScenarioPlan]:
        """Generate a balanced scenario plan across the catalog.

        Selects targets for CONCERNING, LEGITIMATE_UNUSUAL, AMBIGUOUS,
        and NORMAL realizations while reserving targets to avoid
        unintended collision.

        Args:
            records: Pre-mutation operational evidence dictionary.
            target_org_ids: Optional list of organization IDs to target.
            period_id: Target period identifier.
            include_all_families: If True, plans instances for all catalog scenarios.

        Returns:
            List of planned ScenarioPlan objects.
        """
        catalog = get_catalog()
        plans: list[ScenarioPlan] = []
        reserved_ids: set[str] = set()

        # Get available organization IDs from records
        orgs = records.get("organization", [])
        available_org_ids = [str(o.organization_id) for o in orgs]
        if target_org_ids:
            available_org_ids = [o for o in available_org_ids if o in target_org_ids]

        if not available_org_ids:
            raise ScenarioEngineError("No organizations available for scenario planning")

        # Map each scenario to preferred realization state and control type
        scenario_plan_specs: list[tuple[str, RealizationState, ControlContextType | None]] = [
            ("EXEC-GAP-001", RealizationState.CONCERNING, None),
            (
                "EXEC-GAP-001",
                RealizationState.LEGITIMATE_UNUSUAL,
                ControlContextType.APPROVED_AUTOMATION,
            ),
            ("EXEC-GAP-002", RealizationState.CONCERNING, None),
            ("NEG-SPACE-001", RealizationState.CONCERNING, None),
            (
                "NEG-SPACE-001",
                RealizationState.LEGITIMATE_UNUSUAL,
                ControlContextType.MAINTENANCE_WINDOW,
            ),
            ("NEG-SPACE-002", RealizationState.CONCERNING, None),
            ("NEG-SPACE-002", RealizationState.NORMAL, None),
            ("HIST-REP-001", RealizationState.CONCERNING, None),
            ("PEER-CMP-001", RealizationState.CONCERNING, None),
            ("CROSS-REC-001", RealizationState.CONCERNING, None),
            (
                "CROSS-REC-001",
                RealizationState.LEGITIMATE_UNUSUAL,
                ControlContextType.VALID_PROCESS_CHANGE,
            ),
            (
                "LEGIT-CTRL-001",
                RealizationState.LEGITIMATE_UNUSUAL,
                ControlContextType.LEGITIMATE_BURST,
            ),
            ("AMBIG-001", RealizationState.AMBIGUOUS, None),
        ]

        org_cycle_idx = 0
        for scen_id, real_state, ctrl_type in scenario_plan_specs:
            if not include_all_families and scen_id not in catalog:
                continue

            defn = catalog[scen_id]
            if real_state not in defn.applicable_realizations:
                continue

            initial_org = available_org_ids[org_cycle_idx % len(available_org_ids)]
            org_cycle_idx += 1

            ctrl_desc = None
            if ctrl_type:
                ctrl_desc = f"Documented operational control: {ctrl_type.value}"

            # Try initial_org first, then other available orgs while preserving target reservation
            candidate_orgs = [initial_org] + [o for o in available_org_ids if o != initial_org]
            plan = None
            for org_id in candidate_orgs:
                try:
                    plan = self._selector.select(
                        scenario=defn,
                        realization=real_state,
                        records=records,
                        organization_id=org_id,
                        period_id=period_id,
                        reserved_ids=reserved_ids,
                        control_context_type=ctrl_type,
                        control_context_description=ctrl_desc,
                    )
                    plans.append(plan)
                    reserved_ids.update(plan.target_record_ids)
                    break
                except Exception:
                    continue

            if plan is None:
                raise ScenarioEngineError(
                    f"Failed to plan scenario '{scen_id}' across available orgs "
                    f"with realization '{real_state}' without conflicting target reservation",
                    context={"scenario_id": scen_id, "attempted_orgs": candidate_orgs},
                )

        return plans

    def execute_plan(
        self,
        plan: ScenarioPlan,
        records: dict[str, list[Any]],
    ) -> tuple[
        dict[str, list[Any]],
        GroundTruthRecord,
        ScenarioValidationReport,
        list[MutationReceipt],
        LegitimateControlDeclaration | None,
    ]:
        """Execute a single scenario plan.

        1. Generates legitimate control operational context if applicable.
        2. Applies authorized mutations via ScenarioMutator.
        3. Semantically validates operational condition via ScenarioValidator.
        4. Records private ground truth via GroundTruthWriter.

        Returns:
            Tuple of (mutated_records, ground_truth_record, validation_report,
            receipts, control_declaration).
        """
        current_records = {k: list(v) for k, v in records.items()}
        control_decl: LegitimateControlDeclaration | None = None

        # 1. Inject legitimate control context records if required
        if plan.realization == RealizationState.LEGITIMATE_UNUSUAL:
            control_decl, current_records = self._controls.declare_control(
                plan=plan,
                records=current_records,
                is_complete=True,
            )
        elif (
            plan.realization == RealizationState.AMBIGUOUS and plan.control_context_type is not None
        ):
            control_decl, current_records = self._controls.declare_control(
                plan=plan,
                records=current_records,
                is_complete=False,
            )

        # 2. Mutate records
        defn = get_scenario(plan.scenario_id)
        mutated_records, receipts = self._mutator.mutate(
            scenario=defn,
            plan=plan,
            records=current_records,
        )

        # 3. Validate semantic operational conditions
        report = self._validator.validate(
            plan=plan,
            records=mutated_records,
            receipts=receipts,
            fail_loudly=True,
        )

        # 4. Record private ground truth
        gt_record = self._truth_writer.build_and_record(
            plan=plan,
            receipts=receipts,
            report=report,
            control_declaration=control_decl,
        )

        return mutated_records, gt_record, report, receipts, control_decl

    def run_scenarios(
        self,
        records: dict[str, list[Any]],
        plans: list[ScenarioPlan] | None = None,
        *,
        auto_plan: bool = True,
        period_id: str = "P01",
    ) -> ScenarioExecutionResult:
        """Execute a full scenario suite on base operational records.

        Args:
            records: Pre-mutation operational evidence dictionary.
            plans: Optional explicit list of scenario plans.
            auto_plan: If True and plans is None, generates a balanced plan suite.
            period_id: Target period identifier.

        Returns:
            ScenarioExecutionResult containing all mutated records, truth, receipts, and reports.
        """
        current_records = {k: list(v) for k, v in records.items()}
        execution_plans = plans
        if execution_plans is None and auto_plan:
            execution_plans = self.plan_scenarios(current_records, period_id=period_id)
        elif execution_plans is None:
            execution_plans = []

        all_gt_records: list[GroundTruthRecord] = []
        all_reports: list[ScenarioValidationReport] = []
        all_receipts: list[MutationReceipt] = []
        all_control_decls: list[LegitimateControlDeclaration] = []

        for plan in execution_plans:
            (
                current_records,
                gt_record,
                report,
                receipts,
                control_decl,
            ) = self.execute_plan(plan, current_records)

            all_gt_records.append(gt_record)
            all_reports.append(report)
            all_receipts.extend(receipts)
            if control_decl is not None:
                all_control_decls.append(control_decl)

        # Validate authorization ledger completeness (no unused authorizations)
        self._ledger.validate_completeness()

        return ScenarioExecutionResult(
            records=current_records,
            ground_truth_records=tuple(all_gt_records),
            validation_reports=tuple(all_reports),
            receipts=tuple(all_receipts),
            control_declarations=tuple(all_control_decls),
            ledger=self._ledger,
            plans=tuple(execution_plans),
        )

    def write_private_package(self, output_root: Path) -> Path:
        """Write all private ground-truth and ledger outputs to a secure private directory.

        Args:
            output_root: Root directory for private package.

        Returns:
            Path to the written private package directory.
        """
        private_dir = output_root / "private_ground_truth"
        private_dir.mkdir(parents=True, exist_ok=True)

        self._truth_writer.write_to_directory(private_dir)

        # Export authorization ledger
        ledger_path = private_dir / "authorization_ledger.json"
        import json

        ledger_data = self._ledger.export_private()
        ledger_path.write_text(json.dumps(ledger_data, indent=2), encoding="utf-8")

        return private_dir

    @classmethod
    def verify_operational_package_purity(cls, operational_payloads: dict[str, Any]) -> None:
        """Assert that no operational file contains ground-truth or scenario leakage."""
        LeakageScanner.assert_no_leakage(operational_payloads)
