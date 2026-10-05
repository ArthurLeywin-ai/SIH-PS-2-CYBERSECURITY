"""Canonical normalization service.

Transforms raw parsed evidence records into typed SQLAlchemy persistence models,
creates explicit provenance traces (DATA_SCHEMA.md §4.2, §6.4), and captures
semantic field observations with controlled value states.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.backend.domain.types import ValueState
from app.backend.logging import get_logger
from app.backend.persistence.models import (
    ActionModel,
    AlertModel,
    AssetModel,
    CanonicalFieldObservationModel,
    CaseAlertLinkModel,
    CaseModel,
    ClosureModel,
    ControlProcessReferenceModel,
    ControlProcessSubjectLinkModel,
    EscalationModel,
    EvidenceProvenanceModel,
    ExceptionModel,
    InvestigationModel,
    MonitoringCoverageModel,
    OrganizationModel,
    ProcessChangeModel,
    ResolutionModel,
    SubmissionEvidenceFamilyModel,
    SubmissionManifestModel,
    SubmissionModel,
)

logger = get_logger("ingestion.normalizer")


class EvidenceNormalizer:
    """Normalizes raw parsed dictionary records into database models with provenance."""

    def __init__(self, submissions: list[dict[str, Any]] | None = None) -> None:
        self.provenance_records: list[EvidenceProvenanceModel] = []
        self.observations: list[CanonicalFieldObservationModel] = []
        self.seen_ids: dict[str, set[str]] = {}
        self.case_submission_map: dict[str, str] = {}
        self.case_org_map: dict[str, str] = {}
        self.submissions_by_org: dict[str, list[dict[str, Any]]] = {}
        if submissions:
            self.register_submissions(submissions)

    def register_submissions(self, submissions: list[dict[str, Any]]) -> None:
        """Register submission context for temporal and organizational record scoping."""
        for s in submissions:
            org_id = str(s.get("organization_id"))
            self.submissions_by_org.setdefault(org_id, []).append(s)

    def _resolve_submission_id(self, org_id: str, raw: dict[str, Any]) -> str | None:
        """Deterministically determine the submission_id for an operational record."""
        if raw.get("submission_id"):
            return str(raw["submission_id"])

        case_id = raw.get("case_id")
        if case_id and str(case_id) in self.case_submission_map:
            return self.case_submission_map[str(case_id)]

        org_subs = self.submissions_by_org.get(org_id, [])
        if not org_subs:
            return None
        if len(org_subs) == 1:
            return str(org_subs[0].get("submission_id"))

        # Multiple submissions for entity: match temporal coverage
        rec_dt = (
            self._parse_datetime(raw.get("created_at_utc"))
            or self._parse_datetime(raw.get("started_at_utc"))
            or self._parse_datetime(raw.get("escalated_at_utc"))
            or self._parse_datetime(raw.get("resolved_at_utc"))
            or self._parse_datetime(raw.get("closed_at_utc"))
            or self._parse_datetime(raw.get("effective_start_at_utc"))
            or self._parse_datetime(raw.get("effective_at_utc"))
            or self._parse_datetime(raw.get("linked_at_utc"))
        )
        if rec_dt:
            for sub in org_subs:
                s_start = self._parse_datetime(sub.get("reporting_period_start_at_utc"))
                s_end = self._parse_datetime(sub.get("reporting_period_end_at_utc"))
                if s_start and s_end and s_start <= rec_dt <= s_end:
                    return str(sub.get("submission_id"))

        # Fallback to first submission if no period matched
        return str(org_subs[0].get("submission_id"))

    @staticmethod
    def _get_pk(family: str, raw: dict[str, Any]) -> str | None:
        pk_field = f"{family.rstrip('s')}_id"
        if family == "monitoring_coverage":
            pk_field = "monitoring_coverage_id"
        elif family == "submission_manifests":
            pk_field = "manifest_id"
        elif family == "submission_evidence_families":
            pk_field = "submission_family_id"
        elif family == "control_process_references":
            pk_field = "control_process_ref_id"
        elif family == "control_process_subject_links":
            pk_field = "control_process_link_id"
        elif family == "case_alert_links":
            pk_field = "case_alert_link_id"
        elif family == "exceptions":
            pk_field = "exception_id"
        elif family == "process_changes":
            pk_field = "process_change_id"
        val = raw.get(pk_field)
        return str(val) if val else None

    def normalize_all(
        self,
        family: str,
        records: list[dict[str, Any]],
        source_file: str,
    ) -> list[Any]:
        """Normalize records of a given family and record lineage."""
        normalizer_method = getattr(self, f"_normalize_{family}", None)
        if not normalizer_method:
            logger.warning("No specific normalizer for family '%s'. Skipping normalization.", family)
            return []

        if family not in self.seen_ids:
            self.seen_ids[family] = set()

        models = []
        for idx, raw in enumerate(records, start=1):
            pk_val = self._get_pk(family, raw)
            if pk_val and pk_val in self.seen_ids[family]:
                # Exact duplicate record encountered: preserve provenance to the canonical record
                # per DATA_SCHEMA.md §VAL-003, but avoid duplicate database insertion
                locator = f"row:{idx}"
                org_id = str(raw.get("organization_id", "UNKNOWN"))
                sub_id = self._resolve_submission_id(org_id, raw)
                self._record_provenance(
                    pk_val,
                    family,
                    org_id,
                    sub_id,
                    source_file,
                    locator,
                    "duplicate_record",
                    "duplicate_record",
                    raw.get("source_alert_id") or pk_val,
                )
                continue

            if pk_val:
                self.seen_ids[family].add(pk_val)

            model = normalizer_method(raw, source_file, idx)
            if model:
                models.append(model)
        return models

    # ---------------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------------

    @staticmethod
    def _to_int(val: Any, default: int = 0) -> int:
        if val is None or val == "":
            return default
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _to_float(val: Any, default: float = 0.0) -> float:
        if val is None or val == "":
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _parse_datetime(val: Any) -> datetime | None:
        if isinstance(val, datetime):
            return val
        if not val or not isinstance(val, str):
            return None
        clean = val.strip()
        if clean.endswith("Z"):
            clean = clean[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(clean)
        except ValueError:
            return None

    def _record_provenance(
        self,
        canonical_record_id: str,
        evidence_family: str,
        organization_id: str,
        submission_id: str | None,
        source_file: str,
        source_locator: str,
        source_field: str,
        canonical_field: str,
        raw_val: Any,
        relationship_name: str | None = None,
        target_id: str | None = None,
    ) -> None:
        prov = EvidenceProvenanceModel(
            provenance_id=str(uuid.uuid4()),
            canonical_record_id=canonical_record_id,
            evidence_family=evidence_family,
            organization_id=organization_id,
            submission_id=submission_id,
            source_file=source_file,
            source_record_locator=source_locator,
            source_field=source_field,
            raw_source_value=str(raw_val) if raw_val is not None else None,
            canonical_field=canonical_field,
            relationship_name=relationship_name,
            target_canonical_id=target_id,
        )
        self.provenance_records.append(prov)

    def _record_observation(
        self,
        canonical_record_id: str,
        evidence_family: str,
        field_name: str,
        raw_val: Any,
        normalized_val: Any,
    ) -> None:
        state = ValueState.POPULATED
        if raw_val is None:
            state = ValueState.NOT_PROVIDED
        elif isinstance(raw_val, str) and raw_val.strip().upper() in {
            "NOT_PROVIDED",
            "NOT_APPLICABLE",
            "INVALID",
            "UNKNOWN",
            "NULL",
            "NONE",
        }:
            state = (
                ValueState(raw_val.strip().upper())
                if raw_val.strip().upper() in ValueState._value2member_map_
                else ValueState.NOT_PROVIDED
            )

        obs = CanonicalFieldObservationModel(
            observation_id=str(uuid.uuid4()),
            canonical_record_id=canonical_record_id,
            evidence_family=evidence_family,
            field_name=field_name,
            value_state=state.value,
            raw_value=str(raw_val) if raw_val is not None else None,
            normalized_value=str(normalized_val) if normalized_val is not None else None,
            quality_issue=None if state == ValueState.POPULATED else f"Field observed with state {state.value}",
        )
        self.observations.append(obs)

    # ---------------------------------------------------------------------------
    # Family Normalizers
    # ---------------------------------------------------------------------------

    def _normalize_organizations(self, raw: dict[str, Any], source_file: str, idx: int) -> OrganizationModel:
        org_id = str(raw["organization_id"])
        locator = f"row:{idx}"
        self._record_provenance(
            org_id,
            "organizations",
            org_id,
            None,
            source_file,
            locator,
            "organization_id",
            "organization_id",
            raw.get("organization_id"),
        )
        self._record_observation(
            org_id, "organizations", "organization_name", raw.get("organization_name"), raw.get("organization_name")
        )

        return OrganizationModel(
            organization_id=org_id,
            source_organization_id=raw.get("source_organization_id"),
            organization_name=raw.get("organization_name", "UNKNOWN"),
            organization_alias=raw.get("organization_alias"),
            sector_code=raw.get("sector_code", "UNKNOWN"),
            subsector_code=raw.get("subsector_code"),
            scale_band=raw.get("scale_band", "MEDIUM"),
            operating_model=raw.get("operating_model", "HYBRID"),
            entity_criticality_band=raw.get("entity_criticality_band", "STANDARD"),
            asset_count_declared=self._to_int(raw.get("asset_count_declared"), 0),
            critical_asset_count_declared=self._to_int(raw.get("critical_asset_count_declared"), 0),
            default_timezone=raw.get("default_timezone", "UTC"),
            profile_effective_start_at_utc=self._parse_datetime(raw.get("profile_effective_start_at_utc"))
            or datetime.now(UTC),
            profile_effective_end_at_utc=self._parse_datetime(raw.get("profile_effective_end_at_utc")),
            profile_version=self._to_int(raw.get("profile_version"), 1),
            organization_status=raw.get("organization_status", "ACTIVE"),
        )

    def _normalize_submissions(self, raw: dict[str, Any], source_file: str, idx: int) -> SubmissionModel:
        sub_id = str(raw["submission_id"])
        org_id = str(raw["organization_id"])
        locator = f"row:{idx}"
        self._record_provenance(
            sub_id,
            "submissions",
            org_id,
            sub_id,
            source_file,
            locator,
            "submission_id",
            "submission_id",
            raw.get("submission_id"),
        )
        self._record_provenance(
            sub_id,
            "submissions",
            org_id,
            sub_id,
            source_file,
            locator,
            "organization_id",
            "organization_id",
            org_id,
            relationship_name="organization_id",
            target_id=org_id,
        )

        return SubmissionModel(
            submission_id=sub_id,
            source_submission_id=raw.get("source_submission_id"),
            organization_id=org_id,
            reporting_period_id=raw.get("reporting_period_id"),
            period_maturity_state=raw.get("period_maturity_state", "FINAL"),
            reporting_period_start_at_utc=self._parse_datetime(raw.get("reporting_period_start_at_utc"))
            or datetime.now(UTC),
            reporting_period_end_at_utc=self._parse_datetime(raw.get("reporting_period_end_at_utc"))
            or datetime.now(UTC),
            submitted_at_utc=self._parse_datetime(raw.get("submitted_at_utc")),
        )

    def _normalize_submission_manifests(
        self, raw: dict[str, Any], source_file: str, idx: int
    ) -> SubmissionManifestModel:
        manifest_id = str(raw["manifest_id"])
        sub_id = str(raw["submission_id"])
        locator = f"row:{idx}"
        self._record_provenance(
            manifest_id,
            "submission_manifests",
            "UNKNOWN",
            sub_id,
            source_file,
            locator,
            "manifest_id",
            "manifest_id",
            manifest_id,
        )

        return SubmissionManifestModel(
            manifest_id=manifest_id,
            submission_id=sub_id,
            schema_version=raw.get("schema_version", "1.0.0"),
            dataset_version=raw.get("dataset_version", "1.0.0"),
            generator_version=raw.get("generator_version", "1.0.0"),
            tree_sha256=raw.get("tree_sha256", "UNKNOWN"),
            declared_record_counts=raw.get("declared_record_counts", {}),
            created_at_utc=self._parse_datetime(raw.get("created_at_utc")) or datetime.now(UTC),
        )

    def _normalize_submission_evidence_families(
        self, raw: dict[str, Any], source_file: str, idx: int
    ) -> SubmissionEvidenceFamilyModel:
        fam_id = str(raw["submission_family_id"])
        sub_id = str(raw["submission_id"])
        org_id = str(raw.get("organization_id", "UNKNOWN"))
        locator = f"row:{idx}"
        self._record_provenance(
            fam_id,
            "submission_evidence_families",
            org_id,
            sub_id,
            source_file,
            locator,
            "submission_family_id",
            "submission_family_id",
            fam_id,
        )
        return SubmissionEvidenceFamilyModel(
            submission_family_id=fam_id,
            submission_id=sub_id,
            evidence_family=raw.get("evidence_family", "UNKNOWN"),
            presence_state=raw.get("presence_state", "PRESENT"),
            declared_record_count=self._to_int(raw.get("declared_record_count"), 0),
        )

    def _normalize_control_process_references(
        self, raw: dict[str, Any], source_file: str, idx: int
    ) -> ControlProcessReferenceModel:
        ref_id = str(raw["control_process_ref_id"])
        org_id = str(raw["organization_id"])
        sub_id = self._resolve_submission_id(org_id, raw)
        locator = f"row:{idx}"
        self._record_provenance(
            ref_id,
            "control_process_references",
            org_id,
            sub_id,
            source_file,
            locator,
            "control_process_ref_id",
            "control_process_ref_id",
            ref_id,
        )
        return ControlProcessReferenceModel(
            control_process_ref_id=ref_id,
            organization_id=org_id,
            reference_type=raw.get("reference_type", "POLICY"),
            reference_code=raw.get("reference_code", "UNKNOWN"),
            display_name=raw.get("display_name", "UNKNOWN"),
            authority_body=raw.get("authority_body", "PROJECT_DEMO_CONFIGURATION"),
            effective_start_at_utc=self._parse_datetime(raw.get("effective_start_at_utc")) or datetime.now(UTC),
            effective_end_at_utc=self._parse_datetime(raw.get("effective_end_at_utc")),
        )

    def _normalize_control_process_subject_links(
        self, raw: dict[str, Any], source_file: str, idx: int
    ) -> ControlProcessSubjectLinkModel:
        link_id = str(raw["control_process_link_id"])
        ref_id = str(raw["control_process_ref_id"])
        org_id = str(raw.get("organization_id", "UNKNOWN"))
        sub_id = self._resolve_submission_id(org_id, raw)
        locator = f"row:{idx}"
        self._record_provenance(
            link_id,
            "control_process_subject_links",
            org_id,
            sub_id,
            source_file,
            locator,
            "control_process_link_id",
            "control_process_link_id",
            link_id,
        )
        return ControlProcessSubjectLinkModel(
            control_process_link_id=link_id,
            control_process_ref_id=ref_id,
            subject_type=raw.get("subject_type", "ASSET"),
            subject_id=str(raw["subject_id"]),
        )

    def _normalize_assets(self, raw: dict[str, Any], source_file: str, idx: int) -> AssetModel:
        asset_id = str(raw["asset_id"])
        org_id = str(raw["organization_id"])
        sub_id = self._resolve_submission_id(org_id, raw)
        locator = f"row:{idx}"
        self._record_provenance(
            asset_id, "assets", org_id, sub_id, source_file, locator, "asset_id", "asset_id", asset_id
        )

        return AssetModel(
            asset_id=asset_id,
            source_asset_id=raw.get("source_asset_id") or raw.get("asset_alias"),
            organization_id=org_id,
            asset_class=raw.get("asset_class", "SERVER"),
            criticality=raw.get("asset_criticality") or raw.get("criticality", "TIER_2"),
            operating_status=raw.get("active_status") or raw.get("operating_status", "ACTIVE"),
            effective_start_at_utc=self._parse_datetime(raw.get("effective_start_at_utc")) or datetime.now(UTC),
            effective_end_at_utc=self._parse_datetime(raw.get("effective_end_at_utc")),
        )

    def _normalize_monitoring_coverage(
        self, raw: dict[str, Any], source_file: str, idx: int
    ) -> MonitoringCoverageModel:
        cov_id = str(raw["monitoring_coverage_id"])
        org_id = str(raw["organization_id"])
        asset_id = str(raw["asset_id"])
        sub_id = self._resolve_submission_id(org_id, raw)
        locator = f"row:{idx}"
        self._record_provenance(
            cov_id,
            "monitoring_coverage",
            org_id,
            sub_id,
            source_file,
            locator,
            "asset_id",
            "asset_id",
            asset_id,
            relationship_name="asset_id",
            target_id=asset_id,
        )

        return MonitoringCoverageModel(
            monitoring_coverage_id=cov_id,
            organization_id=org_id,
            asset_id=asset_id,
            monitoring_type=raw.get("monitoring_type") or raw.get("coverage_source_type", "EDR"),
            coverage_state=raw.get("coverage_state") or raw.get("coverage_quality_state", "COVERED"),
            coverage_percentage=self._to_float(raw.get("coverage_percentage"), 100.0),
            effective_start_at_utc=self._parse_datetime(
                raw.get("coverage_start_at_utc") or raw.get("effective_start_at_utc")
            )
            or datetime.now(UTC),
            effective_end_at_utc=self._parse_datetime(
                raw.get("coverage_end_at_utc") or raw.get("effective_end_at_utc")
            ),
        )

    def _normalize_alerts(self, raw: dict[str, Any], source_file: str, idx: int) -> AlertModel:
        alert_id = str(raw["alert_id"])
        org_id = str(raw["organization_id"])
        asset_id = str(raw["asset_id"])
        sub_id = self._resolve_submission_id(org_id, raw)
        locator = f"row:{idx}"
        self._record_provenance(
            alert_id, "alerts", org_id, sub_id, source_file, locator, "alert_id", "alert_id", alert_id
        )
        self._record_provenance(
            alert_id,
            "alerts",
            org_id,
            sub_id,
            source_file,
            locator,
            "asset_id",
            "asset_id",
            asset_id,
            relationship_name="asset_id",
            target_id=asset_id,
        )

        status_val = raw.get("status") or raw.get("alert_status", "NEW")
        summary_val = raw.get("summary") or raw.get("alert_summary", "Operational alert")
        rule_val = raw.get("rule_identifier") or raw.get("source_detection_id")

        self._record_observation(alert_id, "alerts", "status", status_val, status_val)
        self._record_observation(alert_id, "alerts", "disposition", raw.get("disposition"), raw.get("disposition"))

        return AlertModel(
            alert_id=alert_id,
            source_alert_id=raw.get("source_alert_id"),
            organization_id=org_id,
            asset_id=asset_id,
            created_at_utc=self._parse_datetime(raw.get("created_at_utc")) or datetime.now(UTC),
            ingested_at_utc=self._parse_datetime(raw.get("ingested_at_utc")),
            alert_category=raw.get("alert_category", "AUTHENTICATION"),
            severity=raw.get("severity", "MEDIUM"),
            status=status_val,
            disposition=raw.get("disposition", "UNDETERMINED"),
            rule_identifier=rule_val,
            summary=summary_val,
        )

    def _normalize_cases(self, raw: dict[str, Any], source_file: str, idx: int) -> CaseModel:
        case_id = str(raw["case_id"])
        org_id = str(raw["organization_id"])
        sub_id = self._resolve_submission_id(org_id, raw)
        self.case_submission_map[case_id] = sub_id or ""
        self.case_org_map[case_id] = org_id
        locator = f"row:{idx}"
        self._record_provenance(case_id, "cases", org_id, sub_id, source_file, locator, "case_id", "case_id", case_id)
        status_val = raw.get("status") or raw.get("case_status", "OPEN")
        self._record_observation(case_id, "cases", "status", status_val, status_val)

        return CaseModel(
            case_id=case_id,
            source_case_id=raw.get("source_case_id"),
            organization_id=org_id,
            case_type=raw.get("case_type") or raw.get("case_category", "INCIDENT"),
            severity=raw.get("severity", "MEDIUM"),
            priority=raw.get("priority_source_text") or raw.get("priority", "P2"),
            status=status_val,
            disposition=raw.get("disposition", "UNDETERMINED"),
            created_at_utc=self._parse_datetime(raw.get("created_at_utc")) or datetime.now(UTC),
            assigned_at_utc=self._parse_datetime(raw.get("assigned_at_utc")),
            started_at_utc=self._parse_datetime(raw.get("started_at_utc")),
            resolved_at_utc=self._parse_datetime(raw.get("resolved_at_utc")),
            closed_at_utc=self._parse_datetime(raw.get("closed_at_utc")),
            primary_assignee=raw.get("assigned_analyst_pseudonym") or raw.get("primary_assignee"),
        )

    def _normalize_case_alert_links(self, raw: dict[str, Any], source_file: str, idx: int) -> CaseAlertLinkModel:
        link_id = str(raw["case_alert_link_id"])
        case_id = str(raw["case_id"])
        alert_id = str(raw["alert_id"])
        org_id = str(raw.get("organization_id") or self.case_org_map.get(case_id, "UNKNOWN"))
        sub_id = self._resolve_submission_id(org_id, raw)
        locator = f"row:{idx}"
        self._record_provenance(
            link_id,
            "case_alert_links",
            org_id,
            sub_id,
            source_file,
            locator,
            "case_id",
            "case_id",
            case_id,
            relationship_name="case_id",
            target_id=case_id,
        )
        self._record_provenance(
            link_id,
            "case_alert_links",
            org_id,
            sub_id,
            source_file,
            locator,
            "alert_id",
            "alert_id",
            alert_id,
            relationship_name="alert_id",
            target_id=alert_id,
        )

        return CaseAlertLinkModel(
            case_alert_link_id=link_id,
            case_id=case_id,
            alert_id=alert_id,
            link_type=raw.get("link_type", "PRIMARY"),
            linked_at_utc=self._parse_datetime(raw.get("linked_at_utc")) or datetime.now(UTC),
        )

    def _normalize_investigations(self, raw: dict[str, Any], source_file: str, idx: int) -> InvestigationModel:
        inv_id = str(raw["investigation_id"])
        case_id = str(raw["case_id"]) if raw.get("case_id") else None
        org_id = str(raw.get("organization_id") or (self.case_org_map.get(case_id) if case_id else "UNKNOWN"))
        sub_id = self._resolve_submission_id(org_id, raw)
        locator = f"row:{idx}"
        self._record_provenance(
            inv_id,
            "investigations",
            org_id,
            sub_id,
            source_file,
            locator,
            "investigation_id",
            "investigation_id",
            inv_id,
        )

        return InvestigationModel(
            investigation_id=inv_id,
            organization_id=org_id,
            case_id=case_id,
            alert_id=str(raw["alert_id"]) if raw.get("alert_id") else None,
            started_at_utc=self._parse_datetime(raw.get("started_at_utc")) or datetime.now(UTC),
            completed_at_utc=self._parse_datetime(raw.get("ended_at_utc") or raw.get("completed_at_utc")),
            analyst_id=raw.get("analyst_pseudonym") or raw.get("analyst_id"),
            disposition=raw.get("conclusion_code") or raw.get("disposition", "UNDETERMINED"),
            summary=raw.get("summary") or raw.get("investigation_notes", "Investigation performed"),
            notes=raw.get("investigation_notes") or raw.get("notes"),
        )

    def _normalize_escalations(self, raw: dict[str, Any], source_file: str, idx: int) -> EscalationModel:
        esc_id = str(raw["escalation_id"])
        case_id = str(raw["case_id"]) if raw.get("case_id") else None
        org_id = str(raw.get("organization_id") or (self.case_org_map.get(case_id) if case_id else "UNKNOWN"))
        sub_id = self._resolve_submission_id(org_id, raw)
        locator = f"row:{idx}"
        self._record_provenance(
            esc_id, "escalations", org_id, sub_id, source_file, locator, "escalation_id", "escalation_id", esc_id
        )
        return EscalationModel(
            escalation_id=esc_id,
            organization_id=org_id,
            case_id=case_id,
            alert_id=str(raw["alert_id"]) if raw.get("alert_id") else None,
            escalated_at_utc=self._parse_datetime(raw.get("escalated_at_utc")) or datetime.now(UTC),
            escalated_from_tier=raw.get("source_role_code") or raw.get("escalated_from_tier", "TIER_1"),
            escalated_to_tier=raw.get("escalation_level") or raw.get("target_role_code", "TIER_2"),
            reason=raw.get("escalation_reason") or raw.get("reason", "Escalation requested"),
            approved_by=raw.get("target_role_code") or raw.get("approved_by"),
        )

    def _normalize_actions(self, raw: dict[str, Any], source_file: str, idx: int) -> ActionModel:
        act_id = str(raw["action_id"])
        case_id = str(raw["case_id"]) if raw.get("case_id") else None
        org_id = str(raw.get("organization_id") or (self.case_org_map.get(case_id) if case_id else "UNKNOWN"))
        sub_id = self._resolve_submission_id(org_id, raw)
        locator = f"row:{idx}"
        self._record_provenance(
            act_id, "actions", org_id, sub_id, source_file, locator, "action_id", "action_id", act_id
        )
        return ActionModel(
            action_id=act_id,
            organization_id=org_id,
            case_id=case_id,
            alert_id=str(raw["alert_id"]) if raw.get("alert_id") else None,
            asset_id=str(raw["asset_id"]) if raw.get("asset_id") else None,
            action_type=raw.get("action_type", "INVESTIGATE"),
            status=raw.get("action_status") or raw.get("status", "COMPLETED"),
            created_at_utc=self._parse_datetime(raw.get("created_at_utc")) or datetime.now(UTC),
            completed_at_utc=self._parse_datetime(raw.get("completed_at_utc")),
            assigned_to=raw.get("owner_role_code") or raw.get("assigned_to"),
            summary=raw.get("action_summary") or raw.get("summary", "Action taken"),
        )

    def _normalize_resolutions(self, raw: dict[str, Any], source_file: str, idx: int) -> ResolutionModel:
        res_id = str(raw["resolution_id"])
        case_id = str(raw["case_id"]) if raw.get("case_id") else None
        org_id = str(raw.get("organization_id") or (self.case_org_map.get(case_id) if case_id else "UNKNOWN"))
        sub_id = self._resolve_submission_id(org_id, raw)
        locator = f"row:{idx}"
        self._record_provenance(
            res_id, "resolutions", org_id, sub_id, source_file, locator, "resolution_id", "resolution_id", res_id
        )
        return ResolutionModel(
            resolution_id=res_id,
            organization_id=org_id,
            case_id=case_id,
            alert_id=str(raw["alert_id"]) if raw.get("alert_id") else None,
            resolved_at_utc=self._parse_datetime(raw.get("resolved_at_utc")) or datetime.now(UTC),
            resolution_type=raw.get("resolution_type", "REMEDIATED"),
            summary=raw.get("resolution_reason") or raw.get("summary", "Resolution recorded"),
            accepted_by=raw.get("approved_by_role_code") or raw.get("accepted_by"),
        )

    def _normalize_closures(self, raw: dict[str, Any], source_file: str, idx: int) -> ClosureModel:
        clo_id = str(raw["closure_id"])
        case_id = str(raw["case_id"]) if raw.get("case_id") else None
        org_id = str(raw.get("organization_id") or (self.case_org_map.get(case_id) if case_id else "UNKNOWN"))
        sub_id = self._resolve_submission_id(org_id, raw)
        locator = f"row:{idx}"
        self._record_provenance(
            clo_id, "closures", org_id, sub_id, source_file, locator, "closure_id", "closure_id", clo_id
        )
        return ClosureModel(
            closure_id=clo_id,
            organization_id=org_id,
            case_id=case_id,
            alert_id=str(raw["alert_id"]) if raw.get("alert_id") else None,
            resolution_id=str(raw["resolution_id"]) if raw.get("resolution_id") else None,
            closed_at_utc=self._parse_datetime(raw.get("closed_at_utc")) or datetime.now(UTC),
            closure_status=raw.get("closure_status") or raw.get("approval_state", "PROPERLY_CLOSED"),
            disposition=raw.get("disposition", "TRUE_POSITIVE"),
            approved_by=raw.get("closed_by_role_code") or raw.get("approved_by"),
            summary=raw.get("closure_reason") or raw.get("summary", "Case closed"),
        )

    def _normalize_exceptions(self, raw: dict[str, Any], source_file: str, idx: int) -> ExceptionModel:
        exc_id = str(raw["exception_id"])
        org_id = str(raw["organization_id"])
        sub_id = self._resolve_submission_id(org_id, raw)
        locator = f"row:{idx}"
        self._record_provenance(
            exc_id, "exceptions", org_id, sub_id, source_file, locator, "exception_id", "exception_id", exc_id
        )
        return ExceptionModel(
            exception_id=exc_id,
            organization_id=org_id,
            exception_type=raw.get("exception_type", "SECURITY_POLICY"),
            subject_type=raw.get("target_type") or raw.get("subject_type", "ASSET"),
            subject_id=str(raw.get("target_id") or raw.get("subject_id") or exc_id),
            status=raw.get("approved_state") or raw.get("status", "APPROVED"),
            reason=raw.get("reason", "Approved exception"),
            approved_by=raw.get("approved_by_role_code") or raw.get("approved_by"),
            effective_start_at_utc=self._parse_datetime(raw.get("effective_start_at_utc")) or datetime.now(UTC),
            effective_end_at_utc=self._parse_datetime(raw.get("effective_end_at_utc")),
        )

    def _normalize_process_changes(self, raw: dict[str, Any], source_file: str, idx: int) -> ProcessChangeModel:
        chg_id = str(raw["process_change_id"])
        org_id = str(raw["organization_id"])
        sub_id = self._resolve_submission_id(org_id, raw)
        locator = f"row:{idx}"
        self._record_provenance(
            chg_id,
            "process_changes",
            org_id,
            sub_id,
            source_file,
            locator,
            "process_change_id",
            "process_change_id",
            chg_id,
        )
        return ProcessChangeModel(
            process_change_id=chg_id,
            organization_id=org_id,
            change_type=raw.get("change_type", "POLICY_UPDATE"),
            effective_start_at_utc=self._parse_datetime(
                raw.get("effective_at_utc") or raw.get("effective_start_at_utc")
            )
            or datetime.now(UTC),
            effective_end_at_utc=self._parse_datetime(raw.get("end_at_utc") or raw.get("effective_end_at_utc")),
            description=raw.get("change_summary") or raw.get("description", "Process update"),
            authorized_by=raw.get("approved_state") or raw.get("authorized_by"),
        )
