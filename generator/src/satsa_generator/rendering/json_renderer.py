"""JSON Source Renderer."""

from __future__ import annotations

import hashlib
import json
from uuid import UUID

from satsa_generator.fixture.models import FixtureRecord
from satsa_generator.provenance.models import (
    FieldProvenance,
    RelationshipProvenance,
    SourceRecordIndex,
)
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
            if (
                context.profile.get_format(family) == "JSONL"
                or context.profile.json_mode == "lines"
            ):
                return b""
            return b"[]"

        rendered_list = []

        for idx, record in enumerate(records):
            record_dict = record.model_dump(mode="json")
            record_obj_dict = record.model_dump()
            source_obj = {}

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
                canonical_id = UUID(int=idx)

            family_map = context.profile.family_mappings.get(family, {})

            # Get relationships from operational records, NOT from oracle
            rels = self.get_relationships_for_record(canonical_id, family, context)
            for r_k, r_v in rels.items():
                fmap = family_map.get(r_k)
                if fmap and fmap.is_link_object_array:
                    record_dict[r_k] = self.get_link_objects_for_record(
                        canonical_id, family, context
                    )
                elif isinstance(r_v, list):
                    record_dict[r_k] = [str(x) for x in r_v]
                else:
                    record_dict[r_k] = str(r_v)

            fields_to_render = list(family_map.keys()) if family_map else list(record_dict.keys())

            for canonical_field in fields_to_render:
                canonical_value = record_dict.get(canonical_field)
                if canonical_value is None and canonical_field in family_map:
                    canonical_value = family_map[canonical_field].default_if_missing

                mapped = self.apply_field_mapping(canonical_field, canonical_value, family, context)
                if mapped:
                    source_name, source_value, path = mapped

                    if path:
                        # Handle nested dictionaries
                        current = source_obj
                        for p in path[:-1]:
                            if p not in current:
                                current[p] = {}
                            current = current[p]
                        current[path[-1]] = source_value
                        locator_suffix = "." + ".".join(path)
                    else:
                        source_obj[source_name] = source_value
                        locator_suffix = f".{source_name}"

                    context.field_provenance.append(
                        FieldProvenance(
                            source_file_path=context.output_path,
                            source_record_locator=f"[{idx}]{locator_suffix}",
                            source_field_name=path[-1] if path else source_name,
                            canonical_record_id=canonical_id,
                            canonical_field_name=canonical_field,
                            raw_value=source_value,
                        )
                    )

                    if canonical_field in rels:
                        context.relationship_provenance.append(
                            RelationshipProvenance(
                                source_file_path=context.output_path,
                                source_record_locator=f"[{idx}]{locator_suffix}",
                                source_relationship_field=path[-1] if path else source_name,
                                relationship_type=canonical_field,
                                canonical_subject_id=canonical_id,
                                canonical_object_id=rels[canonical_field],
                            )
                        )
                    elif (
                        canonical_field.endswith("_id")
                        and canonical_field != f"{family}_id"
                        and isinstance(record_obj_dict.get(canonical_field), UUID)
                    ):
                        context.relationship_provenance.append(
                            RelationshipProvenance(
                                source_file_path=context.output_path,
                                source_record_locator=f"[{idx}]{locator_suffix}",
                                source_relationship_field=path[-1] if path else source_name,
                                relationship_type=canonical_field,
                                canonical_subject_id=canonical_id,
                                canonical_object_id=record_obj_dict[canonical_field],
                            )
                        )

            rendered_list.append(source_obj)

            row_bytes = json.dumps(source_obj, sort_keys=True).encode("utf-8")
            checksum = hashlib.sha256(row_bytes).hexdigest()

            context.indexes.append(
                SourceRecordIndex(
                    source_file_path=context.output_path,
                    source_profile_id=context.profile.profile_id,
                    organization_id=org_id,
                    submission_id=sub_id,
                    evidence_family=family,
                    canonical_record_id=canonical_id,
                    source_record_locator=f"[{idx}]",
                    source_checksum=checksum,
                )
            )

        family_fmt = context.profile.get_format(family)
        if family_fmt == "JSONL" or (family_fmt == "JSON" and context.profile.json_mode == "lines"):
            content = "\n".join(json.dumps(obj, sort_keys=True) for obj in rendered_list)
            return content.encode("utf-8")
        elif family_fmt == "JSON":
            content = json.dumps(rendered_list, indent=2, sort_keys=True)
            return content.encode("utf-8")

        return b""
