"""Canonical Oracle for mapping source outputs back to canonical references."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CanonicalRecordState(BaseModel):
    """The expected canonical state of a record after normalization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    canonical_record_id: UUID
    canonical_family: str
    fields: dict[str, Any]
    relationships: dict[str, UUID | list[UUID]]


@dataclass
class CanonicalOracle:
    """Independent oracle withholding the canonical reference."""

    expected_records: dict[UUID, CanonicalRecordState] = field(default_factory=dict)

    def register_expected_record(self, record: CanonicalRecordState) -> None:
        """Register the expected state of a canonical record."""
        self.expected_records[record.canonical_record_id] = record

    def calculate_oracle_hash(self) -> str:
        """Return a deterministic hash of the entire oracle."""
        sorted_records = sorted(
            [r.model_dump(mode="json") for r in self.expected_records.values()],
            key=lambda x: x["canonical_record_id"],
        )
        content = json.dumps(sorted_records, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return hashlib.sha256(content).hexdigest()
