import re

profiles = {
    "SRC-A": {"case": "snake", "timestamp": "iso_z", "vocab": "canonical", "extra_args": ""},
    "SRC-B": {"case": "pascal", "timestamp": "local_iana", "vocab": "numeric", "extra_args": ', case_naming="pascal_case", timezone="America/New_York"'},
    "SRC-C": {"case": "camel", "timestamp": "iso_offset_ms", "vocab": "vendor", "extra_args": ', case_naming="camel_case", relationships_nested=True'},
    "SRC-D": {"case": "mixed", "timestamp": "date_only", "vocab": "free", "extra_args": ', case_naming="mixed"'},
    "SRC-E": {"case": "v2", "timestamp": "iso_z", "vocab": "numeric", "extra_args": ', version="2.0"'},
}

families = {
    "organization": ["organization_id", "source_organization_id", "organization_name", "entity_criticality_band", "organization_status", "profile_effective_start_at_utc"],
    "submission": ["submission_id", "organization_id", "period_maturity_state", "reporting_period_start_at_utc"],
    "submission_manifest": ["manifest_id", "submission_id", "created_at_utc"],
    "submission_family": ["submission_family_id", "submission_id", "evidence_family", "presence_state"],
    "control_process_reference": ["control_process_ref_id", "organization_id", "reference_type", "reference_code", "display_name"],
    "control_process_subject_link": ["control_process_link_id", "control_process_ref_id", "subject_type"],
    "asset": ["asset_id", "source_asset_id", "organization_id", "asset_class"],
    "monitoring_coverage": ["monitoring_coverage_id", "organization_id", "asset_id", "monitoring_type"],
    "alert": ["alert_id", "organization_id", "asset_id", "created_at_utc"],
    "case": ["case_id", "organization_id", "case_type", "severity", "created_at_utc"],
    "case_alert_link": ["case_alert_link_id", "case_id", "alert_id", "link_type"],
    "investigation": ["investigation_id", "organization_id", "case_id", "alert_id", "started_at_utc"],
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

def generate_profile(prof_id, p_info):
    lines = []
    lines.append(f'def get_{prof_id.lower().replace("-", "_")}() -> ProfileDefinition:')
    lines.append(f'    return ProfileDefinition(')
    lines.append(f'        profile_id="{prof_id}",')
    lines.append(f'        format={"\\"CSV\\"" if prof_id in ["SRC-A", "SRC-B", "SRC-E"] else ("\\"JSON\\"" if prof_id == "SRC-C" else "\\"JSONL\\"")},')
    lines.append(f'        timestamp_format="{p_info["timestamp"]}"{p_info["extra_args"]},')
    lines.append(f'        family_mappings={{')
    
    for fam, fields in families.items():
        lines.append(f'            "{fam}": {{')
        for f in fields:
            is_native = (f == f"{fam}_id" or f == "manifest_id" and fam == "submission_manifest")
            
            if p_info["case"] == "snake":
                src_name = f
            elif p_info["case"] == "pascal":
                src_name = to_pascal(f)
            elif p_info["case"] == "camel":
                src_name = to_camel(f)
            elif p_info["case"] == "mixed":
                src_name = to_mixed(f)
            elif p_info["case"] == "v2":
                src_name = "v2_" + to_mixed(f)

            if p_info["case"] == "camel" and not is_native and "id" not in src_name.lower():
                path_arg = f', path=["details", "{src_name}"]'
            else:
                path_arg = ""

            args = [f'source_name="{src_name}"']
            if is_native:
                args.append("is_native_id=True")
            if path_arg:
                args.append(f'path=["details", "{src_name}"]')
                
            # special cases for vocabulary (just picking one if it fits)
            if f == "entity_criticality_band":
                if prof_id == "SRC-B" or prof_id == "SRC-E": args.append("vocabulary=SEVERITY_SRC_B")
                if prof_id == "SRC-C": args.append("vocabulary=SEVERITY_SRC_C")
                if prof_id == "SRC-D": args.append("vocabulary=SEVERITY_SRC_D")
            if f == "organization_status":
                if prof_id == "SRC-B": args.append("vocabulary=STATUS_SRC_B")
                if prof_id == "SRC-C": args.append("vocabulary=STATUS_SRC_C")
            if f == "period_maturity_state":
                if prof_id == "SRC-B": args.append("vocabulary=MATURITY_SRC_B")
                
            # simulate missing fields for some profiles
            if f == "source_organization_id" and prof_id in ["SRC-B", "SRC-D"]:
                args.append("is_present=False")
                
            lines.append(f'                "{f}": FieldMapping({", ".join(args)}),')
        lines.append(f'            }},')
    lines.append(f'        }}')
    lines.append(f'    )')
    return "\n".join(lines)

out = []
out.append('"""Catalog of M3 Source Profiles."""\n')
out.append('from __future__ import annotations\n')
out.append('from satsa_generator.profiles.models import FieldMapping, ProfileDefinition')
out.append('from satsa_generator.profiles.vocabulary import (')
out.append('    MATURITY_SRC_B, SEVERITY_SRC_B, SEVERITY_SRC_C, SEVERITY_SRC_D, STATUS_SRC_B, STATUS_SRC_C')
out.append(')\n')

for pid, pinfo in profiles.items():
    out.append(generate_profile(pid, pinfo))
    out.append('\n')

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

with open('src/satsa_generator/profiles/catalog.py', 'w') as f:
    f.write("\n".join(out))

