"""Vocabulary mappings for source profiles."""

from satsa_generator.profiles.models import VocabularyMap


def create_vocab(mapping: dict[str, str | int], on_unknown: str = "fail") -> VocabularyMap:
    reverse_map = {v: k for k, v in mapping.items()}
    return VocabularyMap(
        canonical_to_source=mapping, source_to_canonical=reverse_map, on_unknown=on_unknown
    )


# SRC-B mappings (Numeric/abbreviated, strict failure on unknown)
CRITICALITY_BAND_SRC_B = create_vocab({"STANDARD": 1, "ELEVATED": 2, "HIGH": 3, "UNKNOWN": 0})

SEVERITY_SRC_B = create_vocab(
    {
        "INFORMATIONAL": 0,
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
        "CRITICAL": 4,
        "UNKNOWN": -1,
    }
)

STATUS_SRC_B = create_vocab(
    {"ACTIVE": "ACT", "INACTIVE": "INA", "DECOMMISSIONING": "DEC", "UNKNOWN": "UNK"}
)

MATURITY_SRC_B = create_vocab({"MATURE": 1, "IMMATURE": 0, "PARTIAL": 2, "UNKNOWN": -1})

# SRC-C mappings (vendor-like text variants)
CRITICALITY_BAND_SRC_C = create_vocab(
    {"STANDARD": "normal", "ELEVATED": "warning", "HIGH": "critical", "UNKNOWN": "unknown"}
)

SEVERITY_SRC_C = create_vocab(
    {
        "INFORMATIONAL": "informational",
        "LOW": "low",
        "MEDIUM": "warning",
        "HIGH": "high",
        "CRITICAL": "critical",
        "UNKNOWN": "unknown",
    }
)

STATUS_SRC_C = create_vocab(
    {
        "ACTIVE": "running",
        "INACTIVE": "stopped",
        "DECOMMISSIONING": "decommissioned",
        "UNKNOWN": "unknown",
    }
)

MATURITY_SRC_C = create_vocab(
    {"MATURE": "mature", "IMMATURE": "immature", "PARTIAL": "partial", "UNKNOWN": "unknown"}
)

# SRC-D mappings (lowercase/free-text with unknowns, pass-through for unknown)
CRITICALITY_BAND_SRC_D = create_vocab(
    {"STANDARD": "standard", "ELEVATED": "elevated", "HIGH": "high", "UNKNOWN": "unknown"},
    on_unknown="pass_through",
)

SEVERITY_SRC_D = create_vocab(
    {
        "INFORMATIONAL": "informational",
        "LOW": "low",
        "MEDIUM": "medium",
        "HIGH": "high",
        "CRITICAL": "critical",
        "UNKNOWN": "unknown",
    },
    on_unknown="pass_through",
)

STATUS_SRC_D = create_vocab(
    {
        "ACTIVE": "active",
        "INACTIVE": "inactive",
        "DECOMMISSIONING": "decommissioning",
        "UNKNOWN": "unknown",
    },
    on_unknown="pass_through",
)

MATURITY_SRC_D = create_vocab(
    {"MATURE": "mature", "IMMATURE": "immature", "PARTIAL": "partial", "UNKNOWN": "unknown"},
    on_unknown="pass_through",
)

# SRC-E mappings (versioned/v2 vocabulary drift, strict failure on unknown)
CRITICALITY_BAND_SRC_E = create_vocab(
    {"STANDARD": "STD", "ELEVATED": "ELE", "HIGH": "HI", "UNKNOWN": "UNK"}
)

SEVERITY_SRC_E = create_vocab(
    {
        "INFORMATIONAL": "INFO",
        "LOW": "LOW",
        "MEDIUM": "MED",
        "HIGH": "HI",
        "CRITICAL": "CRIT",
        "UNKNOWN": "UNK",
    }
)

STATUS_SRC_E = create_vocab(
    {"ACTIVE": "ACT", "INACTIVE": "INACT", "DECOMMISSIONING": "DECOM", "UNKNOWN": "UNK"}
)

MATURITY_SRC_E = create_vocab(
    {"MATURE": "MAT", "IMMATURE": "IMAT", "PARTIAL": "PART", "UNKNOWN": "UNK"}
)

# Category mappings for SRC-D (free-text variants, pass-through)
CATEGORY_SRC_D = create_vocab(
    {
        "AUTHENTICATION": "auth",
        "AUTHORIZATION": "authz",
        "ENDPOINT": "endpoint",
        "NETWORK": "net",
        "NETWORK_ANOMALY": "net-anom",
        "APPLICATION": "app",
        "DATA_ACCESS": "data-access",
        "DATA_EXFILTRATION": "data-exfil",
        "MALWARE": "malware",
        "POLICY_VIOLATION": "policy-viol",
        "AVAILABILITY": "avail",
        "OTHER": "other",
        "UNKNOWN": "unknown",
    },
    on_unknown="pass_through",
)

# Category mappings for SRC-E (v2 abbreviated codes, strict failure on unknown)
CATEGORY_SRC_E = create_vocab(
    {
        "AUTHENTICATION": "AUTHN",
        "AUTHORIZATION": "AUTHZ",
        "ENDPOINT": "EP",
        "NETWORK": "NET",
        "NETWORK_ANOMALY": "NET_ANOM",
        "APPLICATION": "APP",
        "DATA_ACCESS": "DACC",
        "DATA_EXFILTRATION": "EXFIL",
        "MALWARE": "MALW",
        "POLICY_VIOLATION": "POL",
        "AVAILABILITY": "AVAIL",
        "OTHER": "OTH",
        "UNKNOWN": "UNK",
    }
)

# Disposition mappings for SRC-D (free-text variants, pass-through)
DISPOSITION_SRC_D = create_vocab(
    {
        "TRUE_POSITIVE": "true-positive",
        "FALSE_POSITIVE": "false-positive",
        "BENIGN": "benign",
        "DUPLICATE": "duplicate",
        "SUPPRESSED": "suppressed",
        "ACCEPTED_RISK": "accepted-risk",
        "NO_ACTION_REQUIRED": "no-action",
        "CONFIRMED_INCIDENT": "confirmed",
        "OTHER": "other",
        "UNKNOWN": "unknown",
    },
    on_unknown="pass_through",
)

# Disposition mappings for SRC-E (v2 codes, strict failure on unknown)
DISPOSITION_SRC_E = create_vocab(
    {
        "TRUE_POSITIVE": "TP",
        "FALSE_POSITIVE": "FP",
        "BENIGN": "BEN",
        "DUPLICATE": "DUP",
        "SUPPRESSED": "SUP",
        "ACCEPTED_RISK": "ARISK",
        "NO_ACTION_REQUIRED": "NAR",
        "CONFIRMED_INCIDENT": "CI",
        "OTHER": "OTH",
        "UNKNOWN": "UNK",
    }
)

# SRC-E V1 pre-migration vocabularies (canonical terms, pre-drift)
CRITICALITY_BAND_SRC_E_V1 = create_vocab(
    {"STANDARD": "STANDARD", "ELEVATED": "ELEVATED", "HIGH": "HIGH", "UNKNOWN": "UNKNOWN"}
)

SEVERITY_SRC_E_V1 = create_vocab(
    {
        "INFORMATIONAL": "INFORMATIONAL",
        "LOW": "LOW",
        "MEDIUM": "MEDIUM",
        "HIGH": "HIGH",
        "CRITICAL": "CRITICAL",
        "UNKNOWN": "UNKNOWN",
    }
)

STATUS_SRC_E_V1 = create_vocab(
    {
        "ACTIVE": "ACTIVE",
        "INACTIVE": "INACTIVE",
        "DECOMMISSIONING": "DECOMMISSIONING",
        "UNKNOWN": "UNKNOWN",
    }
)

MATURITY_SRC_E_V1 = create_vocab(
    {
        "MATURE": "MATURE",
        "IMMATURE": "IMMATURE",
        "PARTIAL": "PARTIAL",
        "UNKNOWN": "UNKNOWN",
    }
)

CATEGORY_SRC_E_V1 = create_vocab(
    {
        "AUTHENTICATION": "AUTHENTICATION",
        "AUTHORIZATION": "AUTHORIZATION",
        "ENDPOINT": "ENDPOINT",
        "NETWORK": "NETWORK",
        "NETWORK_ANOMALY": "NETWORK_ANOMALY",
        "APPLICATION": "APPLICATION",
        "DATA_ACCESS": "DATA_ACCESS",
        "DATA_EXFILTRATION": "DATA_EXFILTRATION",
        "MALWARE": "MALWARE",
        "POLICY_VIOLATION": "POLICY_VIOLATION",
        "AVAILABILITY": "AVAILABILITY",
        "OTHER": "OTHER",
        "UNKNOWN": "UNKNOWN",
    }
)

DISPOSITION_SRC_E_V1 = create_vocab(
    {
        "TRUE_POSITIVE": "TRUE_POSITIVE",
        "FALSE_POSITIVE": "FALSE_POSITIVE",
        "BENIGN": "BENIGN",
        "DUPLICATE": "DUPLICATE",
        "SUPPRESSED": "SUPPRESSED",
        "ACCEPTED_RISK": "ACCEPTED_RISK",
        "NO_ACTION_REQUIRED": "NO_ACTION_REQUIRED",
        "CONFIRMED_INCIDENT": "CONFIRMED_INCIDENT",
        "OTHER": "OTHER",
        "UNKNOWN": "UNKNOWN",
    }
)

# V2 aliases matching V2 drift
CRITICALITY_BAND_SRC_E_V2 = CRITICALITY_BAND_SRC_E
SEVERITY_SRC_E_V2 = SEVERITY_SRC_E
STATUS_SRC_E_V2 = STATUS_SRC_E
MATURITY_SRC_E_V2 = MATURITY_SRC_E
CATEGORY_SRC_E_V2 = CATEGORY_SRC_E
DISPOSITION_SRC_E_V2 = DISPOSITION_SRC_E
