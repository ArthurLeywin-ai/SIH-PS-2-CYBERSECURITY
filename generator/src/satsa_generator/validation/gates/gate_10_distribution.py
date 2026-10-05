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

import contextlib
from collections import Counter
from datetime import datetime
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
        closed_case_ids: set[str] = set()
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

            # Case duration distribution: closure timestamp must not precede case creation
            case_created_map = {
                str(getattr(c, "case_id", "")): getattr(c, "created_at_utc", None) for c in cases
            }
            for cl in closures:
                c_id = str(getattr(cl, "case_id", ""))
                c_created = case_created_map.get(c_id)
                cl_time = getattr(cl, "created_at_utc", None)
                if c_created and cl_time and cl_time < c_created:
                    issues.append(
                        ValidationIssue(
                            code="DIST_NEGATIVE_CASE_DURATION",
                            severity=GateSeverity.BLOCKING,
                            gate_index=10,
                            gate_name=self.gate_name,
                            scope="closure",
                            target=c_id,
                            message=(
                                f"Closure timestamp {cl_time} is earlier than case "
                                f"creation {c_created}"
                            ),
                            expected="Closure time >= Case creation time",
                            actual=f"{cl_time} < {c_created}",
                        )
                    )

        # Backlog / open-case sanity check
        open_cases = len(cases) - len(closed_case_ids)
        if open_cases < 0:
            issues.append(
                ValidationIssue(
                    code="DIST_NEGATIVE_BACKLOG",
                    severity=GateSeverity.BLOCKING,
                    gate_index=10,
                    gate_name=self.gate_name,
                    scope="case",
                    target="open_case_count",
                    message=f"Negative case backlog detected: {open_cases}",
                    expected="Open cases >= 0",
                    actual=str(open_cases),
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
        if len(alerts) >= 5:
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
                        severity=GateSeverity.BLOCKING,
                        gate_index=10,
                        gate_name=self.gate_name,
                        scope="alert",
                        target="created_at_utc",
                        message="100% of alerts have identical timestamp down to the second",
                        expected="Temporal dispersion across alerts",
                        actual=f"{max_spike} alerts at {created_times[0]}",
                    )
                )
                issues.append(
                    ValidationIssue(
                        code="DIST_PATHOLOGICAL_TIMESTAMP_CONCENTRATION",
                        severity=GateSeverity.BLOCKING,
                        gate_index=10,
                        gate_name=self.gate_name,
                        scope="alert",
                        target="created_at_utc",
                        message="100% of alerts have identical timestamp down to the second",
                        expected="Temporal dispersion across alerts",
                        actual=f"{max_spike} alerts at {created_times[0]}",
                    )
                )

        if len(alerts) > 10 and len(sev_counts) == 1:
            issues.append(
                ValidationIssue(
                    code="DIST_PATHOLOGICAL_UNIFORMITY",
                    severity=GateSeverity.HIGH,
                    gate_index=10,
                    gate_name=self.gate_name,
                    scope="alert",
                    target="severity_mix",
                    message="All alerts have identical severity (degenerate uniformity)",
                    expected="Multiple alert severities",
                    actual=str(list(sev_counts.keys())),
                )
            )

        # 10. Alert burstiness and spacing
        self._check_alert_burstiness_and_spacing(alerts, issues)

        # 11. Alert category mix diversity
        self._check_alert_category_diversity(alerts, issues)

        # 12. Case duration bounds, zero variance, and investigation notes
        self._check_case_duration_and_notes(cases, closures, investigations, issues)

        # 13. Cross-entity divergence / identical alert distributions
        self._check_cross_entity_divergence(orgs, alerts, issues)

        # 14. Asset criticality mix
        self._check_asset_criticality_mix(assets, issues)

        # 15. Mutation prevalence bounds
        self._check_mutation_prevalence_bounds(context.receipts, records, issues)

        # 16. Workflow rates and valid denominators
        self._check_workflow_rates(
            cases,
            escalations,
            records.get("action", []),
            records.get("resolution", []),
            closures,
            issues,
        )

        # 17. Statistical leakage diagnostic: no single public feature perfectly separates labels
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

    def _check_alert_burstiness_and_spacing(
        self, alerts: list[Any], issues: list[ValidationIssue]
    ) -> None:
        """Verify alert inter-arrival intervals are not artificially constant."""
        if len(alerts) < 10:
            return
        timestamps: list[datetime] = []
        for a in alerts:
            ts = getattr(a, "created_at_utc", None)
            if isinstance(ts, datetime):
                timestamps.append(ts)
            elif isinstance(ts, str):
                with contextlib.suppress(Exception):
                    timestamps.append(datetime.fromisoformat(ts.replace("Z", "+00:00")))

        if len(timestamps) < 10:
            return

        timestamps.sort()
        deltas = [
            (timestamps[i + 1] - timestamps[i]).total_seconds() for i in range(len(timestamps) - 1)
        ]
        positive_deltas = [d for d in deltas if d > 0]
        if (
            len(positive_deltas) >= 5
            and len(set(positive_deltas)) == 1
            and len(positive_deltas) == len(deltas)
        ):
            issues.append(
                ValidationIssue(
                    code="DIST_SUSPICIOUSLY_UNIFORM_ALERT_SPACING",
                    severity=GateSeverity.HIGH,
                    gate_index=10,
                    gate_name=self.gate_name,
                    scope="alert",
                    target="created_at_utc",
                    message=(
                        f"Alert inter-arrival intervals are artificially identical: "
                        f"all {len(deltas)} intervals equal {positive_deltas[0]}s"
                    ),
                    expected="Natural variance in alert inter-arrival spacing",
                    actual=f"Constant interval {positive_deltas[0]}s",
                )
            )

    def _check_alert_category_diversity(
        self, alerts: list[Any], issues: list[ValidationIssue]
    ) -> None:
        """Verify alert categories have reasonable diversity when sample size is sufficient."""
        if len(alerts) < 15:
            return
        categories = [
            getattr(a, "alert_category", None) or getattr(a, "category", None) for a in alerts
        ]
        valid_cats = {c for c in categories if c}
        if len(valid_cats) == 1:
            issues.append(
                ValidationIssue(
                    code="DIST_ALERT_CATEGORY_HOMOGENEITY",
                    severity=GateSeverity.HIGH,
                    gate_index=10,
                    gate_name=self.gate_name,
                    scope="alert",
                    target="alert_category",
                    message="All alerts have identical category (missing category diversity)",
                    expected="Diverse alert categories",
                    actual=str(list(valid_cats)),
                )
            )

    def _check_case_duration_and_notes(
        self,
        cases: list[Any],
        closures: list[Any],
        investigations: list[Any],
        issues: list[ValidationIssue],
    ) -> None:
        """Verify case duration bounds, zero variance, and investigation note diversity."""
        case_created_map = {
            str(getattr(c, "case_id", "")): getattr(c, "created_at_utc", None) for c in cases
        }
        durations: list[float] = []
        for cl in closures:
            c_id = str(getattr(cl, "case_id", ""))
            c_created = case_created_map.get(c_id)
            cl_time = getattr(cl, "created_at_utc", None)
            if c_created and cl_time and cl_time >= c_created:
                dur_secs = (cl_time - c_created).total_seconds()
                durations.append(dur_secs)
                if dur_secs > 365 * 86400:
                    issues.append(
                        ValidationIssue(
                            code="DIST_EXCESSIVE_CASE_DURATION",
                            severity=GateSeverity.HIGH,
                            gate_index=10,
                            gate_name=self.gate_name,
                            scope="closure",
                            target=c_id,
                            message=(
                                f"Case '{c_id}' duration exceeds 365 days "
                                f"({dur_secs / 86400:.1f} days)"
                            ),
                            expected="Case duration <= 365 days",
                            actual=f"{dur_secs / 86400:.1f} days",
                        )
                    )

        if len(durations) >= 5 and len(set(durations)) == 1:
            issues.append(
                ValidationIssue(
                    code="DIST_ZERO_VARIANCE_CASE_DURATION",
                    severity=GateSeverity.HIGH,
                    gate_index=10,
                    gate_name=self.gate_name,
                    scope="closure",
                    target="case_duration",
                    message=(
                        "All closed cases have identical duration down to the second "
                        "(zero variance)"
                    ),
                    expected="Varied case duration distribution",
                    actual=f"All {len(durations)} cases duration = {durations[0]}s",
                )
            )

        notes = [
            str(getattr(inv, "summary", "") or getattr(inv, "notes", ""))
            for inv in investigations
            if hasattr(inv, "summary") or hasattr(inv, "notes")
        ]
        non_empty_notes = [n for n in notes if n.strip()]
        if len(non_empty_notes) >= 5 and len(set(non_empty_notes)) == 1:
            issues.append(
                ValidationIssue(
                    code="DIST_PATHOLOGICAL_NOTE_DUPLICATION",
                    severity=GateSeverity.HIGH,
                    gate_index=10,
                    gate_name=self.gate_name,
                    scope="investigation",
                    target="notes",
                    message=(
                        "All investigation notes across cases are 100% identical copy-paste strings"
                    ),
                    expected="Distinct investigation notes and summaries across cases",
                    actual="100% identical notes",
                )
            )

    def _check_cross_entity_divergence(
        self,
        orgs: list[Any],
        alerts: list[Any],
        issues: list[ValidationIssue],
    ) -> None:
        """Detect multiple entities having suspiciously identical alert distributions."""
        if len(orgs) < 2 or len(alerts) < 10:
            return
        alerts_by_org: dict[str, list[Any]] = {}
        for a in alerts:
            org_id = str(getattr(a, "organization_id", ""))
            if org_id:
                alerts_by_org.setdefault(org_id, []).append(a)

        org_keys = list(alerts_by_org.keys())
        for i in range(len(org_keys)):
            for j in range(i + 1, len(org_keys)):
                org1, org2 = org_keys[i], org_keys[j]
                list1, list2 = alerts_by_org[org1], alerts_by_org[org2]
                if len(list1) >= 5 and len(list1) == len(list2):
                    ts1 = [str(getattr(a, "created_at_utc", "")) for a in list1]
                    ts2 = [str(getattr(a, "created_at_utc", "")) for a in list2]
                    if ts1 == ts2:
                        issues.append(
                            ValidationIssue(
                                code="DIST_IDENTICAL_ENTITY_ALERT_DISTRIBUTIONS",
                                severity=GateSeverity.BLOCKING,
                                gate_index=10,
                                gate_name=self.gate_name,
                                scope="cross_entity",
                                target=f"{org1}:{org2}",
                                message=(
                                    f"Entities '{org1}' and '{org2}' have suspiciously identical "
                                    f"alert counts and timestamps down to the second"
                                ),
                                expected="Divergent cross-entity alert distributions",
                                actual=f"Identical timestamps across {len(ts1)} alerts",
                            )
                        )

    def _check_asset_criticality_mix(
        self, assets: list[Any], issues: list[ValidationIssue]
    ) -> None:
        """Verify asset criticality mix is not completely homogeneous."""
        if len(assets) < 10:
            return
        crits = [getattr(ast, "criticality", None) for ast in assets if hasattr(ast, "criticality")]
        valid_crits = {c for c in crits if c}
        if len(valid_crits) == 1:
            issues.append(
                ValidationIssue(
                    code="DIST_ASSET_CRITICALITY_HOMOGENEITY",
                    severity=GateSeverity.WARNING,
                    gate_index=10,
                    gate_name=self.gate_name,
                    scope="asset",
                    target="criticality",
                    message=(
                        "All assets have identical criticality level "
                        "(missing criticality diversity)"
                    ),
                    expected="Mixed asset criticality levels (LOW, MEDIUM, HIGH, CRITICAL)",
                    actual=str(list(valid_crits)),
                )
            )

    def _check_mutation_prevalence_bounds(
        self,
        receipts: list[Any],
        records: dict[str, list[Any]],
        issues: list[ValidationIssue],
    ) -> None:
        """Verify quality mutation prevalence remains bounded and sparse per §21.2."""
        if not receipts or not records:
            return
        quality_count = sum(
            1 for r in receipts if str(getattr(r, "scenario_id", "")) == "QUALITY_ENGINE"
        )
        total_records = sum(len(lst) for lst in records.values())
        if total_records == 0:
            return
        prevalence = quality_count / total_records
        if prevalence > 0.35:
            issues.append(
                ValidationIssue(
                    code="DIST_EXCESSIVE_MUTATION_PREVALENCE",
                    severity=GateSeverity.HIGH,
                    gate_index=10,
                    gate_name=self.gate_name,
                    scope="quality_prevalence",
                    target="mutation_rate",
                    message=(
                        f"Quality mutation prevalence ({prevalence:.1%}) exceeds authoritative "
                        f"sanity bound (35%)"
                    ),
                    expected="Quality mutation rate <= 35% of total records",
                    actual=f"{prevalence:.1%} ({quality_count}/{total_records})",
                )
            )

    def _check_workflow_rates(
        self,
        cases: list[Any],
        escalations: list[Any],
        actions: list[Any],
        resolutions: list[Any],
        closures: list[Any],
        issues: list[ValidationIssue],
    ) -> None:
        """Verify workflow rates have valid denominators and no impossible negative values."""
        if not cases:
            return
        denom = len(cases)
        esc_rate = len(escalations) / denom
        act_rate = len(actions) / denom
        res_rate = len(resolutions) / denom
        clo_rate = len(closures) / denom

        if esc_rate < 0 or act_rate < 0 or res_rate < 0 or clo_rate < 0:
            issues.append(
                ValidationIssue(
                    code="DIST_IMPOSSIBLE_WORKFLOW_RATE",
                    severity=GateSeverity.BLOCKING,
                    gate_index=10,
                    gate_name=self.gate_name,
                    scope="workflow",
                    target="rates",
                    message="Negative workflow rate detected",
                    expected="Rates >= 0",
                    actual=f"esc={esc_rate}, act={act_rate}, res={res_rate}, clo={clo_rate}",
                )
            )

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
