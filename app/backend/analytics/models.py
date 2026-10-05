"""Authoritative models and contracts for SAT-SA supervisory analytics.

Defines:
- Signal types, severity levels, and evidence roles (ARCHITECTURE.md §7.3, §15.2)
- Strongly typed signal contracts
- Entity attention indicator summaries
- SQLAlchemy persistence models for auditability and lineage tracking
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from app.backend.persistence.database import Base
from sqlalchemy import (
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class SignalType(StrEnum):
    """Supported analytical signal categories."""

    EXECUTION_GAP = "EXECUTION_GAP"
    NEGATIVE_SPACE = "NEGATIVE_SPACE"
    STATISTICAL_ANOMALY = "STATISTICAL_ANOMALY"
    PEER_DEVIATION = "PEER_DEVIATION"
    OPERATIONAL_DRIFT = "OPERATIONAL_DRIFT"


class SignalSeverity(StrEnum):
    """Severity and supervisory attention priority levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EvidenceRole(StrEnum):
    """Role of an evidence reference in supporting a supervisory signal (ARCHITECTURE.md §7.3)."""

    TRIGGER = "TRIGGER"
    SUPPORTING = "SUPPORTING"
    MISSING_EXPECTATION = "MISSING_EXPECTATION"
    COUNTEREVIDENCE = "COUNTEREVIDENCE"
    BASELINE_MEMBER = "BASELINE_MEMBER"
    PEER_MEMBER = "PEER_MEMBER"
    QUALITY_LIMITATION = "QUALITY_LIMITATION"


# ---------------------------------------------------------------------------
# Typed In-Memory Contracts
# ---------------------------------------------------------------------------


@dataclass
class EvidenceReference:
    """Explicit reference linking a supervisory signal to canonical operational evidence."""

    record_id: str
    evidence_family: str
    role: EvidenceRole
    source_file: str | None = None
    source_record_locator: str | None = None
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "evidence_family": self.evidence_family,
            "role": self.role.value if isinstance(self.role, EvidenceRole) else str(self.role),
            "source_file": self.source_file,
            "source_record_locator": self.source_record_locator,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceReference:
        role_val = data.get("role", EvidenceRole.SUPPORTING.value)
        return cls(
            record_id=data["record_id"],
            evidence_family=data["evidence_family"],
            role=EvidenceRole(role_val) if role_val in EvidenceRole._value2member_map_ else EvidenceRole.SUPPORTING,
            source_file=data.get("source_file"),
            source_record_locator=data.get("source_record_locator"),
            description=data.get("description"),
        )


@dataclass
class SupervisorySignal:
    """Structured, auditable, explainable supervisory signal."""

    signal_id: str
    organization_id: str
    signal_type: SignalType
    severity: SignalSeverity
    title: str
    short_rationale: str
    detailed_explanation: str
    observed_value: Any
    submission_id: str | None = None
    basis: dict[str, Any] = field(default_factory=dict)
    expected_value: Any | None = None
    confidence: float = 1.0
    evidence_references: list[EvidenceReference] = field(default_factory=list)
    affected_record_ids: list[str] = field(default_factory=list)
    detector_id: str = "DETECTOR_GENERIC"
    detector_version: str = "1.0.0"
    investigation_questions: list[str] = field(default_factory=list)
    generated_at_utc: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "organization_id": self.organization_id,
            "submission_id": self.submission_id,
            "signal_type": (
                self.signal_type.value if isinstance(self.signal_type, SignalType) else str(self.signal_type)
            ),
            "severity": self.severity.value if isinstance(self.severity, SignalSeverity) else str(self.severity),
            "title": self.title,
            "short_rationale": self.short_rationale,
            "detailed_explanation": self.detailed_explanation,
            "basis": self.basis,
            "observed_value": self.observed_value,
            "expected_value": self.expected_value,
            "confidence": round(self.confidence, 4),
            "evidence_references": [ref.to_dict() for ref in self.evidence_references],
            "affected_record_ids": self.affected_record_ids,
            "detector_id": self.detector_id,
            "detector_version": self.detector_version,
            "investigation_questions": self.investigation_questions,
            "generated_at_utc": self.generated_at_utc.isoformat(),
        }


@dataclass
class SupervisoryAttentionSummary:
    """Consolidated entity-level supervisory attention indicator."""

    summary_id: str
    organization_id: str
    submission_id: str | None
    total_signals: int
    signals_by_type: dict[str, int]
    signals_by_severity: dict[str, int]
    attention_score: float
    attention_band: str
    strongest_signals: list[SupervisorySignal] = field(default_factory=list)
    data_quality_gap_index: float = 0.0
    summary_rationale: str = ""
    generated_at_utc: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary_id": self.summary_id,
            "organization_id": self.organization_id,
            "submission_id": self.submission_id,
            "total_signals": self.total_signals,
            "signals_by_type": self.signals_by_type,
            "signals_by_severity": self.signals_by_severity,
            "attention_score": round(self.attention_score, 2),
            "attention_band": self.attention_band,
            "strongest_signals": [sig.to_dict() for sig in self.strongest_signals],
            "data_quality_gap_index": round(self.data_quality_gap_index, 4),
            "summary_rationale": self.summary_rationale,
            "generated_at_utc": self.generated_at_utc.isoformat(),
        }


@dataclass
class AnalyticsRunResult:
    """Outcome of an end-to-end analytical execution run."""

    run_id: str
    organization_id: str
    submission_id: str | None
    signals: list[SupervisorySignal]
    attention_summary: SupervisoryAttentionSummary
    duration_seconds: float
    generated_at_utc: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def signals_count(self) -> int:
        return len(self.signals)

    @property
    def execution_duration_ms(self) -> float:
        return round(self.duration_seconds * 1000.0, 2)


# ---------------------------------------------------------------------------
# SQLAlchemy Database Models for Persistence
# ---------------------------------------------------------------------------


class SupervisorySignalModel(Base):
    """Persisted supervisory signal record for examiner audit and retrieval."""

    __tablename__ = "supervisory_signals"

    signal_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    submission_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    signal_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    short_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    detailed_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    basis: Mapped[dict] = mapped_column(JSON, default=dict)
    observed_value: Mapped[Any] = mapped_column(JSON, nullable=True)
    expected_value: Mapped[Any] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    evidence_references: Mapped[list] = mapped_column(JSON, default=list)
    affected_record_ids: Mapped[list] = mapped_column(JSON, default=list)
    detector_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    detector_version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    investigation_questions: Mapped[list] = mapped_column(JSON, default=list)
    generated_at_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    __table_args__ = (
        Index("idx_signals_org_severity", "organization_id", "severity"),
        Index("idx_signals_org_type", "organization_id", "signal_type"),
    )


class SupervisoryAttentionSummaryModel(Base):
    """Persisted organization attention indicator summary."""

    __tablename__ = "supervisory_attention_summaries"

    summary_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    submission_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    total_signals: Mapped[int] = mapped_column(Integer, default=0)
    signals_by_type: Mapped[dict] = mapped_column(JSON, default=dict)
    signals_by_severity: Mapped[dict] = mapped_column(JSON, default=dict)
    attention_score: Mapped[float] = mapped_column(Float, default=0.0)
    attention_band: Mapped[str] = mapped_column(String(32), default="LOW")
    strongest_signal_ids: Mapped[list] = mapped_column(JSON, default=list)
    data_quality_gap_index: Mapped[float] = mapped_column(Float, default=0.0)
    summary_rationale: Mapped[str] = mapped_column(Text, default="")
    generated_at_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    __table_args__ = (Index("idx_attention_org_generated", "organization_id", "generated_at_utc"),)
