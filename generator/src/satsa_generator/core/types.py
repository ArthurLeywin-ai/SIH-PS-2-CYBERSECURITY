"""
Shared immutable types and enumerations used across the generator.

All enums and types that appear in multiple modules live here to prevent
circular imports and ensure a single source of truth. This module must
not import from any downstream generator module.
"""

from __future__ import annotations

import enum


# ---------------------------------------------------------------------------
# Dataset and package enums
# ---------------------------------------------------------------------------

class PackageDomain(str, enum.Enum):
    """Physical separation domains for generated packages."""

    OPERATIONAL = "operational_evidence"
    GROUND_TRUTH = "ground_truth_private"
    EVALUATION = "evaluation_private"
    BINDING = "binding_private"


class BenchmarkTier(str, enum.Enum):
    """Benchmark volume tiers from DATASET_GENERATION_SPEC §18."""

    DETERMINISTIC_FIXTURE = "deterministic_fixture"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    HELD_OUT = "held_out"


class SplitID(str, enum.Enum):
    """Dataset split identifiers."""

    DEVELOPMENT = "development"
    VALIDATION = "validation"
    HELD_OUT = "held_out"


# ---------------------------------------------------------------------------
# Period and maturity
# ---------------------------------------------------------------------------

class PeriodMaturity(str, enum.Enum):
    """Period maturity states from DATASET_GENERATION_SPEC §6.2."""

    MATURE = "MATURE"
    PARTIAL = "PARTIAL"
    IMMATURE = "IMMATURE"
    UNKNOWN = "UNKNOWN"


class FamilyPresence(str, enum.Enum):
    """Evidence family presence states from DATA_SCHEMA.md §21.3."""

    PROVIDED = "PROVIDED"
    NOT_PROVIDED = "NOT_PROVIDED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# Evidence families
# ---------------------------------------------------------------------------

class EvidenceFamily(str, enum.Enum):
    """Operational evidence families from DATA_SCHEMA.md."""

    ORGANIZATION = "organization"
    SUBMISSION = "submission"
    ASSET = "asset"
    MONITORING_COVERAGE = "monitoring_coverage"
    ALERT = "alert"
    CASE = "case"
    CASE_ALERT_LINK = "case_alert_link"
    INVESTIGATION = "investigation"
    ESCALATION = "escalation"
    ACTION = "action"
    RESOLUTION = "resolution"
    CLOSURE = "closure"
    EXCEPTION = "exception"
    PROCESS_CHANGE = "process_change"
    CONTROL_PROCESS_REFERENCE = "control_process_reference"
    CONTROL_PROCESS_SUBJECT_LINK = "control_process_subject_link"
    SOURCE_FILE = "source_file"
    SOURCE_RECORD = "source_record"


# ---------------------------------------------------------------------------
# Severity and controlled vocabularies
# ---------------------------------------------------------------------------

class Severity(str, enum.Enum):
    """Canonical severity vocabulary from DATA_SCHEMA.md §18.1."""

    INFORMATIONAL = "INFORMATIONAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class AlertStatus(str, enum.Enum):
    """Canonical alert status vocabulary."""

    NEW = "NEW"
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_INVESTIGATION = "IN_INVESTIGATION"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    SUPPRESSED = "SUPPRESSED"
    REOPENED = "REOPENED"
    UNKNOWN = "UNKNOWN"


class CaseStatus(str, enum.Enum):
    """Canonical case status vocabulary."""

    NEW = "NEW"
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_INVESTIGATION = "IN_INVESTIGATION"
    PENDING = "PENDING"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    REOPENED = "REOPENED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


class Disposition(str, enum.Enum):
    """Canonical disposition vocabulary."""

    TRUE_POSITIVE = "TRUE_POSITIVE"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    BENIGN = "BENIGN"
    DUPLICATE = "DUPLICATE"
    SUPPRESSED = "SUPPRESSED"
    ACCEPTED_RISK = "ACCEPTED_RISK"
    NO_ACTION_REQUIRED = "NO_ACTION_REQUIRED"
    CONFIRMED_INCIDENT = "CONFIRMED_INCIDENT"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class AssetCriticality(str, enum.Enum):
    """Canonical asset criticality vocabulary."""

    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class MonitoringStatus(str, enum.Enum):
    """Canonical monitoring status vocabulary."""

    COVERED = "COVERED"
    PARTIALLY_COVERED = "PARTIALLY_COVERED"
    NOT_COVERED = "NOT_COVERED"
    ONBOARDING = "ONBOARDING"
    DEGRADED = "DEGRADED"
    SUSPENDED = "SUSPENDED"
    UNKNOWN = "UNKNOWN"


class FindingCategory(str, enum.Enum):
    """Finding category vocabulary (for ground-truth references only)."""

    EXECUTION_GAP = "EXECUTION_GAP"
    NEGATIVE_SPACE = "NEGATIVE_SPACE"
    HISTORICAL_DEVIATION = "HISTORICAL_DEVIATION"
    PEER_DEVIATION = "PEER_DEVIATION"
    CROSS_RECORD_INCONSISTENCY = "CROSS_RECORD_INCONSISTENCY"
    REPETITIVE_INVESTIGATION = "REPETITIVE_INVESTIGATION"
    ANOMALY_LEAD = "ANOMALY_LEAD"
    DATA_QUALITY = "DATA_QUALITY"


class TrueCategory(str, enum.Enum):
    """Private ground-truth classification (never in operational output)."""

    ATTENTION = "ATTENTION"
    LEGITIMATE_UNUSUAL = "LEGITIMATE_UNUSUAL"
    NORMAL = "NORMAL"
    DATA_QUALITY_ONLY = "DATA_QUALITY_ONLY"
    AMBIGUOUS = "AMBIGUOUS"


class ValueState(str, enum.Enum):
    """Seven canonical value states from DATA_SCHEMA.md §12.1."""

    OBSERVED_VALUE = "OBSERVED_VALUE"
    OBSERVED_ZERO = "OBSERVED_ZERO"
    NOT_PROVIDED = "NOT_PROVIDED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INVALID = "INVALID"
    NO_SUBMITTED_EVIDENCE = "NO_SUBMITTED_EVIDENCE"
    UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# Source profile identifiers
# ---------------------------------------------------------------------------

class SourceProfile(str, enum.Enum):
    """Source layout profile identifiers from DATASET_GENERATION_SPEC §14."""

    SRC_A = "SRC-A"
    SRC_B = "SRC-B"
    SRC_C = "SRC-C"
    SRC_D = "SRC-D"
    SRC_E = "SRC-E"
