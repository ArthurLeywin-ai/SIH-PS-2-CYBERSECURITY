"""
Generator-specific error hierarchy.

Every error is explicit, loud, and carries structured context for diagnostics.
The generator must never silently repair invalid data or swallow exceptions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class GeneratorError(Exception):
    """Base error for all generator failures."""

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        self.context = context or {}
        super().__init__(message)


class ConfigurationError(GeneratorError):
    """Raised when configuration is invalid, missing, or contradictory.

    Includes unresolved references, forbidden detector keys, version mismatches,
    and path separation violations.
    """


class SeedError(GeneratorError):
    """Raised for seed-related failures.

    Includes duplicate stream labels, unnamed RNG requests, invalid entropy
    sources, and prohibited global random access.
    """


class DeterminismError(GeneratorError):
    """Raised when deterministic generation invariants are violated.

    Includes hash mismatches, non-reproducible output, and seed isolation
    failures.
    """


class ValidationError(GeneratorError):
    """Raised when a validation gate fails.

    Carries the gate identifier, severity, scope, expected/actual values,
    and validator version for structured diagnostics.
    """


class SchemaContractError(ValidationError):
    """Raised when generated data violates DATA_SCHEMA.md contracts.

    Includes required field absence, type mismatches, invalid vocabularies,
    and relationship cardinality violations.
    """


class RelationshipIntegrityError(ValidationError):
    """Raised when referential or ownership integrity is violated across records."""


class TemporalIntegrityError(ValidationError):
    """Raised when timestamp ordering or temporal interval consistency is violated."""


class LeakageError(GeneratorError):
    """Raised when ground-truth information appears in operational output.

    This is always a blocking failure — the build must stop immediately.
    Leakage includes scenario IDs, labels, mutation markers, private seeds,
    and answer-key identifiers in any operational surface.
    """


class PackagingError(GeneratorError):
    """Raised during package assembly failures.

    Includes cross-domain file paths, hash mismatches, missing manifests,
    and package membership violations.
    """


class FixtureBuildError(GeneratorError):
    """Raised when the deterministic Milestone 1 fixture cannot be built."""


@dataclass(frozen=True)
class ValidationIssue:
    """Structured validation finding for gate reports.

    Attributes:
        gate: Validation gate identifier (e.g., 'schema', 'referential', 'temporal').
        code: Machine-readable issue code.
        severity: One of 'BLOCKING', 'ERROR', 'WARNING', 'INFO'.
        scope_type: What was validated (e.g., 'FIELD', 'RECORD', 'RELATIONSHIP').
        scope_id: Identifier of the validated target.
        message: Human-readable explanation.
        expected: What was expected.
        actual: What was found.
        validator_version: Version of the validator that produced this issue.
        context: Additional structured context.
    """

    gate: str
    code: str
    severity: str
    scope_type: str
    scope_id: str
    message: str
    expected: Any = None
    actual: Any = None
    validator_version: str = "0.1.0"
    context: dict[str, Any] = field(default_factory=dict)
