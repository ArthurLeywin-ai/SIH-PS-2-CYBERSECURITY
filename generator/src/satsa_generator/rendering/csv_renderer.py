"""CSV Source Renderer."""

from __future__ import annotations

import csv
import io

from satsa_generator.canonical.oracle import OracleMappingRecord
from satsa_generator.fixture.models import FixtureRecord
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
            source_row = {}

            # Map fields and record in oracle
            for canonical_field, canonical_value in record_dict.items():
                mapped = self.apply_field_mapping(canonical_field, canonical_value, family, context)
                if mapped:
                    source_name, source_value = mapped
                    source_row[source_name] = source_value

                    # Register in oracle
                    # Extract the primary ID if present for lineage (assumes ID ends with _id)
                    canonical_id = None
                    for key, val in record_dict.items():
                        if key.endswith("_id") and isinstance(val, str) and "-" in val:
                            try:
                                import uuid

                                canonical_id = uuid.UUID(val)
                                break
                            except Exception:
                                pass

                    if canonical_id:
                        context.oracle.register_mapping(
                            OracleMappingRecord(
                                source_profile=context.profile.profile_id,
                                source_file_path=context.output_path,
                                source_record_index=idx,
                                source_field_name=source_name,
                                canonical_family=family,
                                canonical_record_id=canonical_id,
                                canonical_field_name=canonical_field,
                                canonical_value=canonical_value,
                                rendered_value=source_value,
                            )
                        )

            if writer is None:
                # Initialize CSV headers based on the first mapped row
                writer = csv.DictWriter(
                    output, fieldnames=list(source_row.keys()), lineterminator="\n"
                )
                writer.writeheader()

            writer.writerow(source_row)

        return output.getvalue().encode("utf-8")
