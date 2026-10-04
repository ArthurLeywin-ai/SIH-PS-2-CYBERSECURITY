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

# SRC-D mappings (lowercase)
SEVERITY_SRC_D = create_vocab(
    {"STANDARD": "standard", "ELEVATED": "elevated", "HIGH": "high", "UNKNOWN": "unknown"}
)
