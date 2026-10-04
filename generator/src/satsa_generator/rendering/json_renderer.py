"""JSON Source Renderer."""

from __future__ import annotations

import json

from satsa_generator.canonical.oracle import OracleMappingRecord
from satsa_generator.fixture.models import FixtureRecord
from satsa_generator.rendering.interfaces import BaseRenderer, RenderContext


class JSONRenderer(BaseRenderer):
    """Renders canonical records to JSON following profile rules."""

    def render_records(
        self,
        family: str,
        records: list[FixtureRecord],
        context: RenderContext,
    ) -> bytes:
        if not records:
            return b"[]"

        rendered_list = []

        for idx, record in enumerate(records):
            record_dict = record.model_dump(mode="json")
            source_obj = {}

            # Determine primary ID
            canonical_id = None
            for key, val in record_dict.items():
                if key.endswith("_id") and isinstance(val, str) and "-" in val:
                    try:
                        import uuid

                        canonical_id = uuid.UUID(val)
                        break
                    except Exception:
                        pass

            for canonical_field, canonical_value in record_dict.items():
                mapped = self.apply_field_mapping(canonical_field, canonical_value, family, context)
                if mapped:
                    source_name, source_value = mapped
                    source_obj[source_name] = source_value

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

            rendered_list.append(source_obj)

        if context.profile.format == "JSON":
            # Pretty print for standard JSON
            content = json.dumps(rendered_list, indent=2, sort_keys=True)
            return content.encode("utf-8")

        # If needed for JSON Lines
        content = "\n".join(json.dumps(obj, sort_keys=True) for obj in rendered_list)
        return content.encode("utf-8")
