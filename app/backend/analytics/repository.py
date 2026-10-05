"""Repository for querying operational evidence for analytics and persisting supervisory signals."""

from __future__ import annotations

from uuid import UUID

from app.backend.analytics.features import EntityPeriodFeatures, FeatureExtractor
from app.backend.analytics.models import (
    SupervisoryAttentionSummary,
    SupervisoryAttentionSummaryModel,
    SupervisorySignal,
    SupervisorySignalModel,
)
from app.backend.logging import get_logger
from app.backend.persistence.models import (
    ActionModel,
    AlertModel,
    AssetModel,
    CaseAlertLinkModel,
    CaseModel,
    ClosureModel,
    EscalationModel,
    EvidenceProvenanceModel,
    InvestigationModel,
    MonitoringCoverageModel,
    OrganizationModel,
    ResolutionModel,
    SubmissionEvidenceFamilyModel,
    SubmissionModel,
)
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

logger = get_logger("analytics.repository")


class AnalyticsRepository:
    """Provides efficient batch querying over operational evidence and persistence of signals."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ---------------------------------------------------------------------------
    # Evidence Querying for Feature Construction
    # ---------------------------------------------------------------------------

    def get_organization(self, organization_id: str | UUID) -> OrganizationModel | None:
        return self.session.get(OrganizationModel, str(organization_id))

    def get_submission(self, submission_id: str | UUID) -> SubmissionModel | None:
        return self.session.get(SubmissionModel, str(submission_id))

    def list_all_organizations(self) -> list[OrganizationModel]:
        stmt = select(OrganizationModel).order_by(OrganizationModel.organization_name)
        return list(self.session.execute(stmt).scalars().all())

    def get_entity_features(
        self,
        organization_id: str | UUID,
        submission_id: str | UUID | None = None,
    ) -> EntityPeriodFeatures:
        """Batch load operational records for an entity and extract normalized features.

        When submission_id is supplied, strictly filters operational records to only those
        whose lineage is established in evidence_provenance for this submission.
        """
        org_id = str(organization_id)
        sub_id = str(submission_id) if submission_id else None

        has_prov = False
        prov_subquery = None
        if sub_id:
            prov_count_stmt = (
                select(func.count())
                .select_from(EvidenceProvenanceModel)
                .where(
                    EvidenceProvenanceModel.organization_id == org_id,
                    EvidenceProvenanceModel.submission_id == sub_id,
                )
            )
            has_prov = (self.session.execute(prov_count_stmt).scalar() or 0) > 0

            if has_prov:
                prov_subquery = (
                    select(EvidenceProvenanceModel.canonical_record_id)
                    .where(
                        EvidenceProvenanceModel.organization_id == org_id,
                        EvidenceProvenanceModel.submission_id == sub_id,
                    )
                    .scalar_subquery()
                )
                stmt_alerts = select(AlertModel).where(
                    AlertModel.organization_id == org_id,
                    AlertModel.alert_id.in_(prov_subquery),
                )
                stmt_cases = select(CaseModel).where(
                    CaseModel.organization_id == org_id,
                    CaseModel.case_id.in_(prov_subquery),
                )
                stmt_assets = select(AssetModel).where(
                    AssetModel.organization_id == org_id,
                    AssetModel.asset_id.in_(prov_subquery),
                )
                stmt_cov = select(MonitoringCoverageModel).where(
                    MonitoringCoverageModel.organization_id == org_id,
                    MonitoringCoverageModel.monitoring_coverage_id.in_(prov_subquery),
                )
            else:
                stmt_alerts = select(AlertModel).where(False)
                stmt_cases = select(CaseModel).where(False)
                stmt_assets = select(AssetModel).where(False)
                stmt_cov = select(MonitoringCoverageModel).where(False)
        else:
            stmt_alerts = select(AlertModel).where(AlertModel.organization_id == org_id)
            stmt_cases = select(CaseModel).where(CaseModel.organization_id == org_id)
            stmt_assets = select(AssetModel).where(AssetModel.organization_id == org_id)
            stmt_cov = select(MonitoringCoverageModel).where(MonitoringCoverageModel.organization_id == org_id)

        alerts = list(self.session.execute(stmt_alerts).scalars().all())
        cases = list(self.session.execute(stmt_cases).scalars().all())
        case_ids = [str(c.case_id) for c in cases]

        case_alert_links: list[CaseAlertLinkModel] = []
        investigations: list[InvestigationModel] = []
        escalations: list[EscalationModel] = []
        actions: list[ActionModel] = []
        resolutions: list[ResolutionModel] = []
        closures: list[ClosureModel] = []

        if case_ids:
            if sub_id and has_prov and prov_subquery is not None:
                stmt_links = select(CaseAlertLinkModel).where(
                    CaseAlertLinkModel.case_id.in_(case_ids),
                    CaseAlertLinkModel.case_alert_link_id.in_(prov_subquery),
                )
                stmt_inv = select(InvestigationModel).where(
                    InvestigationModel.case_id.in_(case_ids),
                    InvestigationModel.investigation_id.in_(prov_subquery),
                )
                stmt_esc = select(EscalationModel).where(
                    EscalationModel.case_id.in_(case_ids),
                    EscalationModel.escalation_id.in_(prov_subquery),
                )
                stmt_act = select(ActionModel).where(
                    ActionModel.case_id.in_(case_ids),
                    ActionModel.action_id.in_(prov_subquery),
                )
                stmt_res = select(ResolutionModel).where(
                    ResolutionModel.case_id.in_(case_ids),
                    ResolutionModel.resolution_id.in_(prov_subquery),
                )
                stmt_clo = select(ClosureModel).where(
                    ClosureModel.case_id.in_(case_ids),
                    ClosureModel.closure_id.in_(prov_subquery),
                )
            else:
                stmt_links = select(CaseAlertLinkModel).where(CaseAlertLinkModel.case_id.in_(case_ids))
                stmt_inv = select(InvestigationModel).where(InvestigationModel.case_id.in_(case_ids))
                stmt_esc = select(EscalationModel).where(EscalationModel.case_id.in_(case_ids))
                stmt_act = select(ActionModel).where(ActionModel.case_id.in_(case_ids))
                stmt_res = select(ResolutionModel).where(ResolutionModel.case_id.in_(case_ids))
                stmt_clo = select(ClosureModel).where(ClosureModel.case_id.in_(case_ids))

            case_alert_links = list(self.session.execute(stmt_links).scalars().all())
            investigations = list(self.session.execute(stmt_inv).scalars().all())
            escalations = list(self.session.execute(stmt_esc).scalars().all())
            actions = list(self.session.execute(stmt_act).scalars().all())
            resolutions = list(self.session.execute(stmt_res).scalars().all())
            closures = list(self.session.execute(stmt_clo).scalars().all())

        assets = list(self.session.execute(stmt_assets).scalars().all())
        coverage = list(self.session.execute(stmt_cov).scalars().all())

        # Declared Families (filtered by submission if supplied, else entity submissions)
        stmt_fams = select(SubmissionEvidenceFamilyModel)
        if sub_id:
            stmt_fams = stmt_fams.where(SubmissionEvidenceFamilyModel.submission_id == sub_id)
        else:
            sub_ids_stmt = select(SubmissionModel.submission_id).where(SubmissionModel.organization_id == org_id)
            sub_ids = list(self.session.execute(sub_ids_stmt).scalars().all())
            if sub_ids:
                stmt_fams = stmt_fams.where(SubmissionEvidenceFamilyModel.submission_id.in_(sub_ids))
            else:
                stmt_fams = stmt_fams.where(False)  # empty

        declared_fams = list(self.session.execute(stmt_fams).scalars().all())

        return FeatureExtractor.extract(
            organization_id=org_id,
            submission_id=sub_id,
            alerts=alerts,
            cases=cases,
            case_alert_links=case_alert_links,
            investigations=investigations,
            escalations=escalations,
            actions=actions,
            resolutions=resolutions,
            closures=closures,
            assets=assets,
            coverage=coverage,
            declared_families=declared_fams,
        )

    def get_peer_features(self, exclude_org_id: str) -> list[EntityPeriodFeatures]:
        """Load features across all other organizations in the database."""
        all_orgs = self.list_all_organizations()
        peer_features: list[EntityPeriodFeatures] = []
        for org in all_orgs:
            if str(org.organization_id) != exclude_org_id:
                hist = self.get_historical_submissions(org.organization_id)
                if hist:
                    feat = self.get_entity_features(org.organization_id, hist[-1].submission_id)
                else:
                    feat = self.get_entity_features(org.organization_id)
                peer_features.append(feat)
        return peer_features

    def get_historical_submissions(self, organization_id: str | UUID) -> list[SubmissionModel]:
        """Retrieve all submissions for an organization ordered chronologically."""
        stmt = (
            select(SubmissionModel)
            .where(SubmissionModel.organization_id == str(organization_id))
            .order_by(SubmissionModel.reporting_period_start_at_utc.asc().nulls_last())
        )
        return list(self.session.execute(stmt).scalars().all())

    # ---------------------------------------------------------------------------
    # Signal & Attention Persistence
    # ---------------------------------------------------------------------------

    def save_signals(self, signals: list[SupervisorySignal]) -> None:
        """Persist generated supervisory signals."""
        models: list[SupervisorySignalModel] = []
        for s in signals:
            models.append(
                SupervisorySignalModel(
                    signal_id=s.signal_id,
                    organization_id=s.organization_id,
                    submission_id=s.submission_id,
                    signal_type=s.signal_type.value if hasattr(s.signal_type, "value") else str(s.signal_type),
                    severity=s.severity.value if hasattr(s.severity, "value") else str(s.severity),
                    title=s.title,
                    short_rationale=s.short_rationale,
                    detailed_explanation=s.detailed_explanation,
                    basis=s.basis,
                    observed_value=s.observed_value,
                    expected_value=s.expected_value,
                    confidence=s.confidence,
                    evidence_references=[ref.to_dict() for ref in s.evidence_references],
                    affected_record_ids=s.affected_record_ids,
                    detector_id=s.detector_id,
                    detector_version=s.detector_version,
                    investigation_questions=s.investigation_questions,
                    generated_at_utc=s.generated_at_utc,
                )
            )
        self.session.bulk_save_objects(models)

    def save_attention_summary(self, summary: SupervisoryAttentionSummary) -> None:
        """Persist entity-level attention summary."""
        model = SupervisoryAttentionSummaryModel(
            summary_id=summary.summary_id,
            organization_id=summary.organization_id,
            submission_id=summary.submission_id,
            total_signals=summary.total_signals,
            signals_by_type=summary.signals_by_type,
            signals_by_severity=summary.signals_by_severity,
            attention_score=summary.attention_score,
            attention_band=summary.attention_band,
            strongest_signal_ids=[s.signal_id for s in summary.strongest_signals],
            data_quality_gap_index=summary.data_quality_gap_index,
            summary_rationale=summary.summary_rationale,
            score_decomposition=summary.score_decomposition,
            generated_at_utc=summary.generated_at_utc,
        )
        self.session.add(model)

    def list_signals(
        self,
        organization_id: str | None = None,
        submission_id: str | None = None,
        signal_type: str | None = None,
        severity: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SupervisorySignalModel]:
        """Query persisted supervisory signals with deterministic ordering."""
        stmt = select(SupervisorySignalModel)
        if organization_id:
            stmt = stmt.where(SupervisorySignalModel.organization_id == str(organization_id))
        if submission_id:
            stmt = stmt.where(SupervisorySignalModel.submission_id == str(submission_id))
        if signal_type:
            stmt = stmt.where(SupervisorySignalModel.signal_type == signal_type.upper())
        if severity:
            stmt = stmt.where(SupervisorySignalModel.severity == severity.upper())

        stmt = stmt.order_by(
            desc(SupervisorySignalModel.generated_at_utc),
            SupervisorySignalModel.signal_id.asc(),
        ).offset(offset).limit(limit)

        return list(self.session.execute(stmt).scalars().all())

    def get_signal(self, signal_id: str) -> SupervisorySignalModel | None:
        return self.session.get(SupervisorySignalModel, str(signal_id))

    def get_latest_attention_summary(
        self, organization_id: str
    ) -> SupervisoryAttentionSummaryModel | None:
        """Retrieve the latest supervisory attention summary for an entity."""
        stmt = (
            select(SupervisoryAttentionSummaryModel)
            .where(SupervisoryAttentionSummaryModel.organization_id == str(organization_id))
            .order_by(desc(SupervisoryAttentionSummaryModel.generated_at_utc))
            .limit(1)
        )
        return self.session.execute(stmt).scalars().first()
