import re

families = {
    "organization": ["organization_id", "source_organization_id", "organization_name", "entity_criticality_band", "organization_status", "profile_effective_start_at_utc"],
    "submission": ["submission_id", "organization_id", "period_maturity_state", "reporting_period_start_at_utc"],
    "submission_manifest": ["manifest_id", "submission_id", "created_at_utc"],
    "submission_family": ["submission_family_id", "submission_id", "evidence_family", "presence_state"],
    "control_process_reference": ["control_process_ref_id", "organization_id", "reference_type", "reference_code", "display_name"],
    "control_process_subject_link": ["control_process_link_id", "control_process_ref_id", "subject_type"],
    "asset": ["asset_id", "source_asset_id", "organization_id", "asset_class"],
    "monitoring_coverage": ["monitoring_coverage_id", "organization_id", "asset_id", "monitoring_type"],
    "alert": ["alert_id", "organization_id", "asset_id", "created_at_utc", "alert_category", "severity", "disposition"],
    "case": ["case_id", "organization_id", "case_type", "severity", "created_at_utc", "alerts"],
    "case_alert_link": ["case_alert_link_id", "case_id", "alert_id", "link_type"],
    "investigation": ["investigation_id", "organization_id", "case_id", "alert_id", "started_at_utc", "disposition"],
    "escalation": ["escalation_id", "organization_id", "case_id", "alert_id", "escalated_at_utc"],
    "action": ["action_id", "organization_id", "asset_id", "alert_id", "case_id", "action_type"],
    "resolution": ["resolution_id", "organization_id", "case_id", "alert_id", "resolved_at_utc"],
    "closure": ["closure_id", "organization_id", "case_id", "alert_id", "resolution_id", "closed_at_utc"],
    "exception": ["exception_id", "organization_id", "exception_type"],
    "process_change": ["process_change_id", "organization_id", "change_type"],
}

def to_pascal(s):
    return "".join(x.capitalize() for x in s.split("_"))

def to_camel(s):
    parts = s.split("_")
    return parts[0] + "".join(x.capitalize() for x in parts[1:])

def to_mixed(s):
    parts = s.split("_")
    if len(parts) > 1:
        return parts[0][:3] + "_" + parts[-1]
    return s[:3]

SRC_D_NAMES = {
    "organization": {
        "organization_id": "org_id",
        "source_organization_id": "sou_org_id",
        "organization_name": "org_name",
        "entity_criticality_band": "ent_cri_band",
        "organization_status": "org_status",
        "profile_effective_start_at_utc": "pro_eff_utc",
    },
    "submission": {
        "submission_id": "sub_id",
        "organization_id": "org_id",
        "period_maturity_state": "per_mat_state",
        "reporting_period_start_at_utc": "rep_per_utc",
    },
    "submission_manifest": {
        "manifest_id": "man_id",
        "submission_id": "sub_id",
        "created_at_utc": "cre_at_utc",
    },
    "submission_family": {
        "submission_family_id": "sub_fam_id",
        "submission_id": "sub_id",
        "evidence_family": "evi_family",
        "presence_state": "pre_state",
    },
    "control_process_reference": {
        "control_process_ref_id": "con_pro_id",
        "organization_id": "org_id",
        "reference_type": "ref_type",
        "reference_code": "ref_code",
        "display_name": "dis_name",
    },
    "control_process_subject_link": {
        "control_process_link_id": "con_pro_link_id",
        "control_process_ref_id": "con_pro_id",
        "subject_type": "sub_type",
    },
    "asset": {
        "asset_id": "ass_id",
        "source_asset_id": "sou_ass_id",
        "organization_id": "org_id",
        "asset_class": "ass_class",
    },
    "monitoring_coverage": {
        "monitoring_coverage_id": "mon_cov_id",
        "organization_id": "org_id",
        "asset_id": "ass_id",
        "monitoring_type": "mon_type",
    },
    "alert": {
        "alert_id": "ale_id",
        "organization_id": "org_id",
        "asset_id": "ass_id",
        "created_at_utc": "cre_at_utc",
        "alert_category": "ale_cat",
        "severity": "ale_sev",
        "disposition": "ale_disp",
    },
    "case": {
        "case_id": "cas_id",
        "organization_id": "org_id",
        "case_type": "cas_type",
        "severity": "cas_sev",
        "created_at_utc": "cre_at_utc",
        "alerts": "alerts",
    },
    "case_alert_link": {
        "case_alert_link_id": "cas_ale_id",
        "case_id": "cas_id",
        "alert_id": "ale_id",
        "link_type": "lin_type",
    },
    "investigation": {
        "investigation_id": "inv_id",
        "organization_id": "org_id",
        "case_id": "cas_id",
        "alert_id": "ale_id",
        "started_at_utc": "sta_at_utc",
        "disposition": "inv_disp",
    },
    "escalation": {
        "escalation_id": "esc_id",
        "organization_id": "org_id",
        "case_id": "cas_id",
        "alert_id": "ale_id",
        "escalated_at_utc": "esc_at_utc",
    },
    "action": {
        "action_id": "act_id",
        "organization_id": "org_id",
        "asset_id": "ass_id",
        "alert_id": "ale_id",
        "case_id": "cas_id",
        "action_type": "act_type",
    },
    "resolution": {
        "resolution_id": "res_id",
        "organization_id": "org_id",
        "case_id": "cas_id",
        "alert_id": "ale_id",
        "resolved_at_utc": "res_at_utc",
        "resolution_type": "res_type",
    },
    "closure": {
        "closure_id": "clo_id",
        "organization_id": "org_id",
        "case_id": "cas_id",
        "alert_id": "ale_id",
        "resolution_id": "res_id",
        "closed_at_utc": "clo_at_utc",
        "disposition": "clo_disp",
    },
    "exception": {
        "exception_id": "exc_id",
        "organization_id": "org_id",
        "exception_type": "exc_type",
    },
    "process_change": {
        "process_change_id": "pro_cha_id",
        "organization_id": "org_id",
        "change_type": "cha_type",
    },
}

SRC_E_NAMES = {
    "organization": {
        "organization_id": "org_id",
        "source_organization_id": "legacy_org_code",
        "organization_name": "entity_name",
        "entity_criticality_band": "criticality_tier",
        "organization_status": "lifecycle_status",
        "profile_effective_start_at_utc": "valid_from_utc",
    },
    "submission": {
        "submission_id": "sub_id",
        "organization_id": "org_id",
        "period_maturity_state": "maturity_level",
        "reporting_period_start_at_utc": "period_start_utc",
    },
    "submission_manifest": {
        "manifest_id": "manifest_id",
        "submission_id": "sub_id",
        "created_at_utc": "manifest_timestamp_utc",
    },
    "submission_family": {
        "submission_family_id": "family_decl_id",
        "submission_id": "sub_id",
        "evidence_family": "family_name",
        "presence_state": "presence_status",
    },
    "control_process_reference": {
        "control_process_ref_id": "ref_id",
        "organization_id": "org_id",
        "reference_type": "control_type",
        "reference_code": "framework_code",
        "display_name": "title",
    },
    "control_process_subject_link": {
        "control_process_link_id": "link_id",
        "control_process_ref_id": "ref_id",
        "subject_type": "target_type",
    },
    "asset": {
        "asset_id": "asset_id",
        "source_asset_id": "external_asset_tag",
        "organization_id": "org_id",
        "asset_class": "device_type",
    },
    "monitoring_coverage": {
        "monitoring_coverage_id": "coverage_id",
        "organization_id": "org_id",
        "asset_id": "asset_id",
        "monitoring_type": "sensor_type",
    },
    "alert": {
        "alert_id": "id",
        "organization_id": "org_id",
        "asset_id": "target_asset_id",
        "created_at_utc": "timestamp_utc",
        "alert_category": "event_category",
        "severity": "event_severity",
        "disposition": "outcome",
    },
    "case": {
        "case_id": "case_id",
        "organization_id": "org_id",
        "case_type": "incident_type",
        "severity": "severity",
        "created_at_utc": "opened_at_utc",
        "alerts": "linked_alert_ids",
    },
    "case_alert_link": {
        "case_alert_link_id": "link_id",
        "case_id": "parent_case_id",
        "alert_id": "child_alert_id",
        "link_type": "link_role",
    },
    "investigation": {
        "investigation_id": "inv_id",
        "organization_id": "org_id",
        "case_id": "case_id",
        "alert_id": "alert_id",
        "started_at_utc": "start_timestamp_utc",
        "disposition": "outcome",
    },
    "escalation": {
        "escalation_id": "esc_id",
        "organization_id": "org_id",
        "case_id": "case_id",
        "alert_id": "alert_id",
        "escalated_at_utc": "escalated_timestamp_utc",
    },
    "action": {
        "action_id": "action_id",
        "organization_id": "org_id",
        "asset_id": "asset_id",
        "alert_id": "alert_id",
        "case_id": "case_id",
        "action_type": "response_action",
    },
    "resolution": {
        "resolution_id": "resolution_id",
        "organization_id": "org_id",
        "case_id": "case_id",
        "alert_id": "alert_id",
        "resolved_at_utc": "resolved_timestamp_utc",
    },
    "closure": {
        "closure_id": "closure_id",
        "organization_id": "org_id",
        "case_id": "case_id",
        "alert_id": "alert_id",
        "resolution_id": "resolution_id",
        "closed_at_utc": "closed_timestamp_utc",
    },
    "exception": {
        "exception_id": "exception_id",
        "organization_id": "org_id",
        "exception_type": "deviation_category",
    },
    "process_change": {
        "process_change_id": "change_id",
        "organization_id": "org_id",
        "change_type": "modification_type",
    },
}

def generate_profile(prof_id):
    lines = []
    lines.append(f'def get_{prof_id.lower().replace("-", "_")}() -> ProfileDefinition:')
    lines.append(f'    return ProfileDefinition(')
    lines.append(f'        profile_id="{prof_id}",')
    
    if prof_id == "SRC-A":
        lines.append('        format="CSV",')
        lines.append('        timestamp_format="iso_z",')
    elif prof_id == "SRC-B":
        lines.append('        format="CSV",')
        lines.append('        timestamp_format="local_iana",')
        lines.append('        case_naming="pascal_case",')
        lines.append('        timezone="America/New_York",')
    elif prof_id == "SRC-C":
        lines.append('        format="JSON",')
        lines.append('        timestamp_format="iso_offset_ms",')
        lines.append('        case_naming="camel_case",')
        lines.append('        relationships_nested=True,')
    elif prof_id == "SRC-D":
        lines.append('        format="JSONL",')
        lines.append('        timestamp_format="date_only",')
        lines.append('        case_naming="mixed",')
        lines.append('        per_family_timestamp_format={')
        for fam in ["alert", "case", "case_alert_link", "investigation", "escalation", "action", "resolution", "closure", "exception", "process_change"]:
            lines.append(f'            "{fam}": "iso_offset",')
        for fam in ["organization", "submission", "submission_manifest", "submission_family", "control_process_reference", "control_process_subject_link", "asset", "monitoring_coverage"]:
            lines.append(f'            "{fam}": "date_only",')
        lines.append('        },')
    elif prof_id == "SRC-E":
        lines.append('        format="CSV",')
        lines.append('        version="2.0",')
        lines.append('        timestamp_format="iso_z",')
        lines.append('        case_naming="mixed",')
        lines.append('        per_family_format={')
        for fam in ["organization", "submission", "submission_manifest", "submission_family", "control_process_reference", "control_process_subject_link", "asset", "monitoring_coverage"]:
            lines.append(f'            "{fam}": "CSV",')
        for fam in ["alert", "case", "case_alert_link", "investigation", "escalation", "action", "resolution", "closure", "exception", "process_change"]:
            lines.append(f'            "{fam}": "JSON",')
        lines.append('        },')

    lines.append('        family_mappings={')
    
    for fam, fields in families.items():
        lines.append(f'            "{fam}": {{')
        for f in fields:
            is_native = (f == f"{fam}_id" or f == "manifest_id" and fam == "submission_manifest")
            
            if prof_id == "SRC-A":
                src_name = f
            elif prof_id == "SRC-B":
                src_name = to_pascal(f)
            elif prof_id == "SRC-C":
                src_name = to_camel(f)
            elif prof_id == "SRC-D":
                src_name = SRC_D_NAMES.get(fam, {}).get(f, to_mixed(f))
            elif prof_id == "SRC-E":
                src_name = SRC_E_NAMES.get(fam, {}).get(f, to_mixed(f))

            args = [f'source_name="{src_name}"']
            if is_native:
                args.append("is_native_id=True")

            if prof_id == "SRC-C" and not is_native and "id" not in src_name.lower():
                args.append(f'path=["details", "{src_name}"]')
            elif prof_id == "SRC-C" and fam == "case" and f == "alerts":
                args.append('path=["details", "alerts"]')

            # Vocabulary mappings
            if f == "entity_criticality_band":
                if prof_id == "SRC-B": args.append("vocabulary=CRITICALITY_BAND_SRC_B")
                elif prof_id == "SRC-C": args.append("vocabulary=CRITICALITY_BAND_SRC_C")
                elif prof_id == "SRC-D": args.append("vocabulary=CRITICALITY_BAND_SRC_D")
                elif prof_id == "SRC-E": args.append("vocabulary=CRITICALITY_BAND_SRC_E")
            elif f == "severity":
                if prof_id == "SRC-B": args.append("vocabulary=SEVERITY_SRC_B")
                elif prof_id == "SRC-C": args.append("vocabulary=SEVERITY_SRC_C")
                elif prof_id == "SRC-D": args.append("vocabulary=SEVERITY_SRC_D")
                elif prof_id == "SRC-E": args.append("vocabulary=SEVERITY_SRC_E")
            elif f in ("organization_status", "alert_status", "case_status"):
                if prof_id == "SRC-B": args.append("vocabulary=STATUS_SRC_B")
                elif prof_id == "SRC-C": args.append("vocabulary=STATUS_SRC_C")
                elif prof_id == "SRC-D": args.append("vocabulary=STATUS_SRC_D")
                elif prof_id == "SRC-E": args.append("vocabulary=STATUS_SRC_E")
            elif f == "period_maturity_state":
                if prof_id == "SRC-B": args.append("vocabulary=MATURITY_SRC_B")
                elif prof_id == "SRC-C": args.append("vocabulary=MATURITY_SRC_C")
                elif prof_id == "SRC-D": args.append("vocabulary=MATURITY_SRC_D")
                elif prof_id == "SRC-E": args.append("vocabulary=MATURITY_SRC_E")
            elif f == "alert_category":
                if prof_id == "SRC-D": args.append("vocabulary=CATEGORY_SRC_D")
                elif prof_id == "SRC-E": args.append("vocabulary=CATEGORY_SRC_E")
            elif f == "disposition":
                if prof_id == "SRC-D": args.append("vocabulary=DISPOSITION_SRC_D")
                elif prof_id == "SRC-E": args.append("vocabulary=DISPOSITION_SRC_E")

            # Reference array / link handling
            if f == "alerts" and fam == "case":
                if prof_id in ("SRC-A", "SRC-B"):
                    args.append("is_present=False")
                elif prof_id in ("SRC-D", "SRC-E"):
                    args.append("is_reference_array=True")

            # Missing fields
            if f == "source_organization_id" and prof_id in ("SRC-B", "SRC-D"):
                args.append("is_present=False")

            mapping_str = f'"{f}": FieldMapping({", ".join(args)}),'
            if len(f"                {mapping_str}") > 95:
                args_str = ",\n                    ".join(args)
                lines.append(f'                "{f}": FieldMapping(\n                    {args_str}\n                ),')
            else:
                lines.append(f'                {mapping_str}')
        lines.append('            },')
    lines.append('        }')
    lines.append('    )')
    return "\n".join(lines)

out = []
out.append('''"""Catalog of M3 Source Profiles."""

from __future__ import annotations

from satsa_generator.profiles.models import FieldMapping, ProfileDefinition
from satsa_generator.profiles.vocabulary import (
    CATEGORY_SRC_D,
    CATEGORY_SRC_E,
    CRITICALITY_BAND_SRC_B,
    CRITICALITY_BAND_SRC_C,
    CRITICALITY_BAND_SRC_D,
    CRITICALITY_BAND_SRC_E,
    DISPOSITION_SRC_D,
    DISPOSITION_SRC_E,
    MATURITY_SRC_B,
    MATURITY_SRC_C,
    MATURITY_SRC_D,
    MATURITY_SRC_E,
    SEVERITY_SRC_B,
    SEVERITY_SRC_C,
    SEVERITY_SRC_D,
    SEVERITY_SRC_E,
    STATUS_SRC_B,
    STATUS_SRC_C,
    STATUS_SRC_D,
    STATUS_SRC_E,
)


''')

for pid in ["SRC-A", "SRC-B", "SRC-C", "SRC-D", "SRC-E"]:
    out.append(generate_profile(pid))
    out.append("\n")

out.append('''def get_profile(profile_id: str) -> ProfileDefinition:
    profiles = {
        "SRC-A": get_src_a,
        "SRC-B": get_src_b,
        "SRC-C": get_src_c,
        "SRC-D": get_src_d,
        "SRC-E": get_src_e,
    }
    return profiles[profile_id]()
''')

with open("src/satsa_generator/profiles/catalog.py", "w") as f:
    f.write("\n".join(out))

print("Successfully generated src/satsa_generator/profiles/catalog.py!")
