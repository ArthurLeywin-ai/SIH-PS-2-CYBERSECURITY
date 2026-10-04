"""Vocabulary mappings for source profiles."""

from satsa_generator.profiles.models import VocabularyMap


def create_vocab(mapping: dict[str, str | int], on_unknown: str = "fail") -> VocabularyMap:
    reverse_map = {v: k for k, v in mapping.items()}
    return VocabularyMap(
        canonical_to_source=mapping, source_to_canonical=reverse_map, on_unknown=on_unknown
    )


# SRC-B mappings (Numeric/abbreviated)
SEVERITY_SRC_B = create_vocab({"STANDARD": 1, "ELEVATED": 2, "HIGH": 3, "UNKNOWN": 0})

STATUS_SRC_B = create_vocab({"ACTIVE": "ACT", "INACTIVE": "INA", "UNKNOWN": "UNK"})

MATURITY_SRC_B = create_vocab({"MATURE": 1, "IMMATURE": 0, "PARTIAL": 2, "UNKNOWN": -1})

# SRC-C mappings (vendor-like text variants)
SEVERITY_SRC_C = create_vocab(
    {"STANDARD": "normal", "ELEVATED": "warning", "HIGH": "critical", "UNKNOWN": "unknown"}
)

STATUS_SRC_C = create_vocab({"ACTIVE": "running", "INACTIVE": "stopped", "UNKNOWN": "unknown"})

# SRC-D mappings (lowercase/free-text with unknowns, pass-through for unknown)
SEVERITY_SRC_D = create_vocab(
    {"STANDARD": "standard", "ELEVATED": "elevated", "HIGH": "high", "UNKNOWN": "unknown"},
    on_unknown="pass_through"
)

STATUS_SRC_D = create_vocab(
    {"ACTIVE": "active", "INACTIVE": "inactive", "UNKNOWN": "unknown"},
    on_unknown="pass_through"
)

MATURITY_SRC_D = create_vocab(
    {"MATURE": "mature", "IMMATURE": "immature", "PARTIAL": "partial", "UNKNOWN": "unknown"},
    on_unknown="pass_through"
)

# SRC-E mappings (versioned/v2 vocabulary drift)
SEVERITY_SRC_E = create_vocab(
    {"STANDARD": "std", "ELEVATED": "ele", "HIGH": "hi", "CRITICAL": "crit", "UNKNOWN": "unk"}
)

STATUS_SRC_E = create_vocab(
    {"ACTIVE": "act", "INACTIVE": "inact", "UNKNOWN": "unk"}
)

MATURITY_SRC_E = create_vocab(
    {"MATURE": "mat", "IMMATURE": "imat", "PARTIAL": "part", "UNKNOWN": "unk"}
)

# Category mappings for SRC-D (free-text variants)
CATEGORY_SRC_D = create_vocab(
    {
        "AUTHENTICATION": "auth",
        "ENDPOINT": "endpoint",
        "NETWORK": "net",
        "APPLICATION": "app",
        "DATA_ACCESS": "data-access",
        "MALWARE": "malware",
        "POLICY_VIOLATION": "policy-viol",
        "AVAILABILITY": "avail",
        "OTHER": "other",
        "UNKNOWN": "unknown",
    },
    on_unknown="pass_through"
)

# Category mappings for SRC-E (v2 abbreviated)
CATEGORY_SRC_E = create_vocab(
    {
        "AUTHENTICATION": "AUTHN",
        "ENDPOINT": "EP",
        "NETWORK": "NET",
        "APPLICATION": "APP",
        "DATA_ACCESS": "DACC",
        "MALWARE": "MALW",
        "POLICY_VIOLATION": "POL",
        "AVAILABILITY": "AVAIL",
        "OTHER": "OTH",
        "UNKNOWN": "UNK",
    }
)

# Disposition mappings for SRC-D
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
    on_unknown="pass_through"
)

# Disposition mappings for SRC-E
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
