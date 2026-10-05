"""Operational evidence reference resolver and builders for supervisory analytics."""

from __future__ import annotations

from app.backend.analytics.models import EvidenceReference, EvidenceRole
from app.backend.persistence.models import EvidenceProvenanceModel
from sqlalchemy import select
from sqlalchemy.orm import Session


class EvidenceResolver:
    """Resolves operational evidence records to structured references with file lineage."""

    def __init__(self, session: Session | None = None) -> None:
        self.session = session

    def build_reference(
        self,
        record_id: str,
        evidence_family: str,
        role: EvidenceRole,
        description: str | None = None,
        source_file: str | None = None,
        source_record_locator: str | None = None,
    ) -> EvidenceReference:
        """Construct an EvidenceReference, enriching with source file/locator if available."""
        resolved_file = source_file
        resolved_locator = source_record_locator

        if self.session and (resolved_file is None or resolved_locator is None):
            stmt = (
                select(EvidenceProvenanceModel)
                .where(
                    EvidenceProvenanceModel.canonical_record_id == record_id,
                    EvidenceProvenanceModel.evidence_family == evidence_family,
                )
                .limit(1)
            )
            prov = self.session.execute(stmt).scalars().first()
            if prov:
                resolved_file = resolved_file or prov.source_file
                resolved_locator = resolved_locator or prov.source_record_locator

        return EvidenceReference(
            record_id=str(record_id),
            evidence_family=evidence_family,
            role=role,
            source_file=resolved_file,
            source_record_locator=resolved_locator,
            description=description,
        )

    def build_batch_references(
        self,
        record_ids: list[str],
        evidence_family: str,
        role: EvidenceRole,
        description_template: str = "{family} record {id}",
    ) -> list[EvidenceReference]:
        """Construct a list of EvidenceReferences for a batch of record IDs."""
        refs: list[EvidenceReference] = []
        for rid in sorted(record_ids):
            refs.append(
                self.build_reference(
                    record_id=rid,
                    evidence_family=evidence_family,
                    role=role,
                    description=description_template.format(family=evidence_family, id=rid),
                )
            )
        return refs
