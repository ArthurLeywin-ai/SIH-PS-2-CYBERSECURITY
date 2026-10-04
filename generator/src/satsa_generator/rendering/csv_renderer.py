"""CSV Source Renderer."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from uuid import UUID

from satsa_generator.fixture.models import FixtureRecord
from satsa_generator.provenance.models import (
    FieldProvenance,
    RelationshipProvenance,
    SourceRecordIndex,
)
from satsa_generator.rendering.interfaces import BaseRenderer, RenderContext


class CSVRenderer(BaseRenderer):
    """Renders canonical records to CSV following profile rules."""

    def render_records(
        self,
        family: str,
        records: list[FixtureRecord],
        context: RenderContext,
    ) -> bytes:
        if not records:
            return b""

        output = io.StringIO()
        writer = None

        for idx, record in enumerate(records):
            record_dict = record.model_dump(mode="json")
            record_obj_dict = record.model_dump()
            source_row = {}

            canonical_id = None
            org_id = None
            sub_id = None

            for key, val in record_obj_dict.items():
                if key.endswith("_id") and isinstance(val, UUID) and canonical_id is None:
                            canonical_id = val
                if key == "organization_id" and isinstance(val, UUID):
                    org_id = val
                if key == "submission_id" and isinstance(val, UUID):
                    sub_id = val

            if not canonical_id:
                # Fallback if no specific ID is found (shouldn't happen in M2 models)
                canonical_id = UUID(int=idx)

            rels = {}
            if context.oracle and canonical_id in context.oracle.expected_records:
                rels = context.oracle.expected_records[canonical_id].relationships
                for r_k, r_v in rels.items():
                    if isinstance(r_v, list):
                        record_dict[r_k] = [str(x) for x in r_v]

            for canonical_field, canonical_value in record_dict.items():
                mapped = self.apply_field_mapping(canonical_field, canonical_value, family, context)
                if mapped:
                    source_name, source_value, _ = mapped

                    if isinstance(source_value, list):
                        # Convert list to a JSON string for CSV rendering
                        source_value = json.dumps(source_value)

                    source_row[source_name] = source_value

                    context.field_provenance.append(
                        FieldProvenance(
                            source_file_path=context.output_path,
                            source_record_locator=f"row:{idx + 1}",
                            source_field_name=source_name,
                            canonical_record_id=canonical_id,
                            canonical_field_name=canonical_field,
                        )
                    )

                    if canonical_field in rels:
                        context.relationship_provenance.append(
                            RelationshipProvenance(
                                source_file_path=context.output_path,
                                source_record_locator=f"row:{idx + 1}",
                                source_relationship_field=source_name,
                                relationship_type=canonical_field,
                                canonical_subject_id=canonical_id,
                                canonical_object_id=rels[canonical_field],
                            )
                        )

            if writer is None:
                writer = csv.DictWriter(
                    output, fieldnames=list(source_row.keys()), lineterminator="\n"
                )
                writer.writeheader()

            writer.writerow(source_row)

            row_bytes = json.dumps(source_row, sort_keys=True).encode("utf-8")
            checksum = hashlib.sha256(row_bytes).hexdigest()

            context.indexes.append(
                SourceRecordIndex(
                    source_file_path=context.output_path,
                    source_profile_id=context.profile.profile_id,
                    organization_id=org_id,
                    submission_id=sub_id,
                    evidence_family=family,
                    canonical_record_id=canonical_id,
                    source_record_locator=f"row:{idx + 1}",
                    source_checksum=checksum,
                )
            )

        return output.getvalue().encode("utf-8")
