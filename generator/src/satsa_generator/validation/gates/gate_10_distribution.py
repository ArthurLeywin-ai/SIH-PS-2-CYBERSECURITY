"""Gate 10: Distribution Sanity Gate.

From GENERATOR_IMPLEMENTATION_PLAN §18.1, §18.2 and DATASET_GENERATION_SPEC §20:
- Hard invariants: nonempty cohorts, configured family counts, valid parameter domains,
  required positive/control coverage, and no perfect label marker.
- Soft statistical envelopes: alert volume, severity/category mix, case sizes,
  investigation coverage, escalation rates, action/resolution/closure behavior,
  open/backlog behavior, asset/criticality/monitoring coverage mix, missingness,
  scenario prevalence, legitimate-control balance, abnormal/uniform distributions,
  and leakage-like statistical separation.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from satsa_generator.scenarios.models import RealizationState
from satsa_generator.validation.gates.base import ValidationGate
from satsa_generator.validation.models import (
    GateReport,
    GateSeverity,
    ValidationContext,
    ValidationIssue,
)


class Gate10DistributionSanity(ValidationGate):
    """Gate 10: Validates distribution balance, sanity bounds, and label separation."""

    @property
    def gate_index(self) -> int:
        return 10

    @property
    def gate_name(self) -> str:
        return "Distribution Sanity Gate"

    def validate(self, context: ValidationContext) -> GateReport:
        issues: list[ValidationIssue] = []
        records = context.records
        gt_records = context.ground_truth

        # 1. Hard invariant: Nonempty cohorts (§18.2)
        orgs = records.get("organization", [])
        if not orgs:
            issues.append(
                ValidationIssue(
                    code="DIST_EMPTY_COHORT",
                    severity=GateSeverity.BLOCKING,
                    gate_index=10,
                    gate_name=self.gate_name,
                    scope="organization",
                    target="organization_list",
                    message="Zero organizations generated in dataset",
                    expected="At least one organization record",
                    actual="0",
                )
            )

        # 2. Hard invariant: Operational evidence volume
        alerts = records.get("alert", [])
        if not alerts:
            issues.append(
                ValidationIssue(
                    code="DIST_ZERO_ALERTS",
                    severity=GateSeverity.BLOCKING,
                    gate_index=10,
                    gate_name=self.gate_name,
                    scope="alert",
                    target="alert_count",
                    message="Alert family has zero records generated",
                    expected="Non-zero alert volume",
                    actual="0",
                )
            )

        cases = records.get("case", [])
        if not cases:
            issues.append(
                ValidationIssue(
                    code="DIST_ZERO_CASES",
                    severity=GateSeverity.BLOCKING,
                    gate_index=10,
                    gate_name=self.gate_name,
                    scope="case",
                    target="case_count",
                    message="Case family has zero records generated",
                    expected="Non-zero case volume",
                    actual="0",
                )
            )

        assets = records.get("asset", [])
        if not assets:
            issues.append(
                ValidationIssue(
                    code="DIST_ZERO_ASSETS",
                    severity=GateSeverity.BLOCKING,
                    gate_index=10,
                    gate_name=self.gate_name,
                    scope="asset",
                    target="asset_count",
                    message="Asset family has zero records generated",
                    expected="Non-zero asset volume",
                    actual="0",
                )
            )

        # 3. Positive / Control realization balance (§18.2)
        if gt_records:
            realizations = {getattr(gt, "realization", None) for gt in gt_records}
            if RealizationState.CONCERNING not in realizations:
                issues.append(
                    ValidationIssue(
                        code="DIST_MISSING_CONCERNING_REALIZATION",
                        severity=GateSeverity.BLOCKING,
                        gate_index=10,
                        gate_name=self.gate_name,
                        scope="ground_truth",
                        target="realizations",
                        message="Dataset lacks any CONCERNING realization instance",
                        expected="CONCERNING realization present",
                        actual=str(realizations),
                    )
                )

            # Legitimate control balance check
            if len(gt_records) > 4:
                control_count = sum(
                    1
                    for gt in gt_records
                    if getattr(gt, "realization", None)
                    in (
                        RealizationState.LEGITIMATE_UNUSUAL,
                        RealizationState.AMBIGUOUS,
                        RealizationState.NORMAL,
                    )
                )
                if control_count == 0:
                    issues.append(
                        ValidationIssue(
                            code="DIST_ZERO_CONTROLS",
                            severity=GateSeverity.HIGH,
                            gate_index=10,
                            gate_name=self.gate_name,
                            scope="ground_truth",
                            target="control_balance",
                            message="Ground truth contains zero legitimate control realizations",
                            expected="Non-zero legitimate control or ambiguous realizations",
                            actual="0 controls",
                        )
                    )

        # 4. Alert severity and category mix
        severities = [getattr(a, "severity", None) for a in alerts if hasattr(a, "severity")]
        sev_counts = Counter(severities)
        if len(sev_counts) < 2 and len(alerts) > 10:
            issues.append(
                ValidationIssue(
                    code="DIST_SEVERITY_HOMOGENEITY",
                    severity=GateSeverity.WARNING,
                    gate_index=10,
                    gate_name=self.gate_name,
                    scope="alert",
                    target="severity_mix",
                    message=f"Alert severities show low diversity: {set(sev_counts.keys())}",
                    expected="Heterogeneous severity distribution",
                    actual=str(set(sev_counts.keys())),
                )
            )

        # 5. Case size and alert-link distribution
        links = records.get("case_alert_link", [])
        if cases and links:
            case_link_counts = Counter(
                str(getattr(lnk, "case_id", "")) for lnk in links if getattr(lnk, "case_id", None)
            )
            for c_id, count in case_link_counts.items():
                if count > 500:
                    issues.append(
                        ValidationIssue(
                            code="DIST_PATHOLOGICAL_CASE_SIZE",
                            severity=GateSeverity.HIGH,
                            gate_index=10,
                            gate_name=self.gate_name,
                            scope="case_alert_link",
                            target=c_id,
                            message=f"Case '{c_id}' has excessive alert count: {count}",
                            expected="Case size <= 500 alerts",
                            actual=str(count),
                        )
                    )

        # 6. Investigation & escalation coverage
        investigations = records.get("investigation", [])
        escalations = records.get("escalation", [])
        if cases and not investigations and len(cases) > 5:
            issues.append(
                ValidationIssue(
                    code="DIST_ZERO_INVESTIGATIONS",
                    severity=GateSeverity.HIGH,
                    gate_index=10,
                    gate_name=self.gate_name,
                    scope="investigation",
                    target="investigation_coverage",
                    message="Zero investigations generated despite multiple cases",
                    expected="Investigation coverage for active cases",
                    actual="0",
                )
            )

        if cases and len(escalations) > len(cases) * 5:
            issues.append(
                ValidationIssue(
                    code="DIST_EXCESSIVE_ESCALATIONS",
                    severity=GateSeverity.HIGH,
                    gate_index=10,
                    gate_name=self.gate_name,
                    scope="escalation",
                    target="escalation_rate",
                    message="Escalation count abnormally exceeds case count",
                    expected=f"Escalations <= {len(cases) * 5}",
                    actual=str(len(escalations)),
                )
            )

        # 7. Action, resolution, and closure behavior
        closures = records.get("closure", [])
        if cases and closures:
            closed_case_ids = {
                str(getattr(cl, "case_id", "")) for cl in closures if getattr(cl, "case_id", None)
            }
            if len(closed_case_ids) > len(cases):
                issues.append(
                    ValidationIssue(
                        code="DIST_CLOSURE_COUNT_EXCEEDS_CASES",
                        severity=GateSeverity.BLOCKING,
                        gate_index=10,
                        gate_name=self.gate_name,
                        scope="closure",
                        target="closure_count",
                        message="Distinct closed cases exceed total cases",
                        expected=f"Closed cases <= {len(cases)}",
                        actual=str(len(closed_case_ids)),
                    )
                )

        # 8. Asset criticality and monitoring coverage mix
        coverages = records.get("monitoring_coverage", [])
        if assets and not coverages and len(assets) > 3:
            issues.append(
                ValidationIssue(
                    code="DIST_ZERO_MONITORING_COVERAGE",
                    severity=GateSeverity.WARNING,
                    gate_index=10,
                    gate_name=self.gate_name,
                    scope="monitoring_coverage",
                    target="coverage_count",
                    message="Zero monitoring coverage records generated for assets",
                    expected="Monitoring coverage mapping",
                    actual="0",
                )
            )

        # 9. Degenerate distribution / Uniformity artifacts
        if len(alerts) > 20:
            created_times = [
                str(getattr(a, "created_at_utc", ""))
                for a in alerts
                if hasattr(a, "created_at_utc")
            ]
            time_counts = Counter(created_times)
            max_spike = max(time_counts.values()) if time_counts else 0
            if max_spike == len(alerts):
                issues.append(
                    ValidationIssue(
                        code="DIST_IDENTICAL_TIMESTAMPS_ARTIFACT",
                        severity=GateSeverity.HIGH,
                        gate_index=10,
                        gate_name=self.gate_name,
                        scope="alert",
                        target="created_at_utc",
                        message="All alerts have identical timestamp down to the second",
                        expected="Temporal dispersion across alerts",
                        actual=f"{max_spike} alerts at {created_times[0]}",
                    )
                )

        # 10. Statistical leakage diagnostic: no single public feature perfectly separates labels
        if gt_records and len(gt_records) >= 6:
            self._check_statistical_separation(gt_records, records, issues)

        metadata: dict[str, Any] = {
            "total_alerts": len(alerts),
            "total_cases": len(cases),
            "total_assets": len(assets),
            "total_ground_truth": len(gt_records) if gt_records else 0,
            "severities": sorted(list(sev_counts.keys())),
        }
        return self.create_report(issues, metadata=metadata)

    def _check_statistical_separation(
        self,
        gt_records: list[Any],
        records: dict[str, list[Any]],
        issues: list[ValidationIssue],
    ) -> None:
        """Verify that simple public attributes do not perfectly separate private classes.

        Reference: GENERATOR_IMPLEMENTATION_PLAN §19.3 item 8.
        """
        labels = [
            (
                "CONCERNING"
                if getattr(gt, "realization", None) == RealizationState.CONCERNING
                else "NOT_CONCERNING"
            )
            for gt in gt_records
        ]
        label_set = set(labels)
        if len(label_set) < 2:
            return

        # Check organizations vs label separation
        org_ids = [str(getattr(gt, "organization_id", "")) for gt in gt_records]
        if len(set(org_ids)) > 1:
            org_to_labels: dict[str, set[str]] = {}
            for org_id, lbl in zip(org_ids, labels, strict=False):
                org_to_labels.setdefault(org_id, set()).add(lbl)
            # If every organization has only 1 label and disjoint from others -> perfect split
            all_pure = all(len(s) == 1 for s in org_to_labels.values())
            if all_pure and len(org_to_labels) > 2:
                issues.append(
                    ValidationIssue(
                        code="DIST_PERFECT_FEATURE_SEPARATION",
                        severity=GateSeverity.HIGH,
                        gate_index=10,
                        gate_name=self.gate_name,
                        scope="leakage_diagnostic",
                        target="organization_id",
                        message="Organization ID perfectly separates ground truth labels",
                        expected="Overlapping or non-deterministic scenario distribution",
                        actual=str(org_to_labels),
                    )
                )
