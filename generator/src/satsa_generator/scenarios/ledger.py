"""
Authorization ledger — tracks every deliberate mutation.

Every mutation applied by M4 scenario mutators MUST have a corresponding
authorization entry in this ledger. The ledger enforces:

- No unauthorized mutations (missing authorization = build failure)
- No duplicate authorizations (duplicate ID = build failure)
- No conflicting authorizations (same target, conflicting mutations = build failure)
- No unused authorizations (unused = validation failure)
- Validators must NOT silently repair mutations

The ledger is PRIVATE and must never enter the operational package.
"""

from __future__ import annotations

from satsa_generator.core.errors import GeneratorError
from satsa_generator.scenarios.models import (
    AuthorizationEntry,
    AuthorizationStatus,
    MutationReceipt,
)


class AuthorizationError(GeneratorError):
    """Raised when authorization constraints are violated."""


class AuthorizationLedger:
    """Private mutation authorization ledger.

    Thread-unsafe by design — the generator is single-threaded and
    deterministic. The ledger maintains insertion order for
    reproducible validation.
    """

    def __init__(self) -> None:
        self._entries: dict[str, AuthorizationEntry] = {}
        self._target_index: dict[str, list[str]] = {}  # target_record_id -> [auth_ids]
        self._consumed: set[str] = set()

    @property
    def entries(self) -> dict[str, AuthorizationEntry]:
        """Return a read-only view of all authorization entries."""
        return dict(self._entries)

    @property
    def size(self) -> int:
        """Number of authorization entries."""
        return len(self._entries)

    def authorize(self, entry: AuthorizationEntry) -> None:
        """Register a mutation authorization.

        Raises:
            AuthorizationError: If the authorization ID is duplicate or
                conflicts with an existing authorization on the same target.
        """
        if entry.authorization_id in self._entries:
            raise AuthorizationError(
                f"Duplicate authorization ID: '{entry.authorization_id}'",
                context={
                    "authorization_id": entry.authorization_id,
                    "existing_scenario": self._entries[entry.authorization_id].scenario_id,
                },
            )

        # Check for conflicting authorizations on the same target records
        for target_id in entry.target_record_ids:
            existing_auth_ids = self._target_index.get(target_id, [])
            for existing_id in existing_auth_ids:
                existing = self._entries[existing_id]
                if (
                    existing.mutation_type == entry.mutation_type
                    and existing.target_family == entry.target_family
                    and existing.scenario_id != entry.scenario_id
                ):
                    raise AuthorizationError(
                        f"Conflicting authorization on target '{target_id}': "
                        f"existing '{existing_id}' ({existing.scenario_id}) "
                        f"conflicts with '{entry.authorization_id}' ({entry.scenario_id}) "
                        f"for mutation type '{entry.mutation_type}'",
                        context={
                            "target_id": target_id,
                            "existing_auth": existing_id,
                            "new_auth": entry.authorization_id,
                        },
                    )

        self._entries[entry.authorization_id] = entry
        for target_id in entry.target_record_ids:
            self._target_index.setdefault(target_id, []).append(entry.authorization_id)

    def consume(self, receipt: MutationReceipt) -> None:
        """Mark an authorization as consumed by a mutation receipt.

        Raises:
            AuthorizationError: If the authorization does not exist or
                has already been consumed.
        """
        auth_id = receipt.authorization_id
        if auth_id not in self._entries:
            raise AuthorizationError(
                f"Unauthorized mutation: no authorization for '{auth_id}'",
                context={"authorization_id": auth_id, "plan_id": receipt.plan_id},
            )

        if auth_id in self._consumed:
            raise AuthorizationError(
                f"Authorization '{auth_id}' has already been consumed",
                context={"authorization_id": auth_id},
            )

        entry = self._entries[auth_id]
        # Update status to APPLIED (create new immutable entry)
        updated = AuthorizationEntry(
            authorization_id=entry.authorization_id,
            scenario_id=entry.scenario_id,
            plan_id=entry.plan_id,
            realization=entry.realization,
            target_record_ids=entry.target_record_ids,
            target_family=entry.target_family,
            mutation_type=entry.mutation_type,
            expected_semantic_effect=entry.expected_semantic_effect,
            seed_label=entry.seed_label,
            status=AuthorizationStatus.APPLIED,
        )
        self._entries[auth_id] = updated
        self._consumed.add(auth_id)

    def mark_validated(self, authorization_id: str) -> None:
        """Mark an authorization as validated.

        Raises:
            AuthorizationError: If not found or not in APPLIED state.
        """
        if authorization_id not in self._entries:
            raise AuthorizationError(
                f"Cannot validate unknown authorization: '{authorization_id}'",
            )
        entry = self._entries[authorization_id]
        if entry.status != AuthorizationStatus.APPLIED:
            raise AuthorizationError(
                f"Cannot validate authorization '{authorization_id}' "
                f"in status '{entry.status}' (expected APPLIED)",
            )
        updated = AuthorizationEntry(
            authorization_id=entry.authorization_id,
            scenario_id=entry.scenario_id,
            plan_id=entry.plan_id,
            realization=entry.realization,
            target_record_ids=entry.target_record_ids,
            target_family=entry.target_family,
            mutation_type=entry.mutation_type,
            expected_semantic_effect=entry.expected_semantic_effect,
            seed_label=entry.seed_label,
            status=AuthorizationStatus.VALIDATED,
        )
        self._entries[authorization_id] = updated

    def mark_failed(self, authorization_id: str) -> None:
        """Mark an authorization as failed."""
        if authorization_id not in self._entries:
            raise AuthorizationError(
                f"Cannot mark unknown authorization as failed: '{authorization_id}'",
            )
        entry = self._entries[authorization_id]
        updated = AuthorizationEntry(
            authorization_id=entry.authorization_id,
            scenario_id=entry.scenario_id,
            plan_id=entry.plan_id,
            realization=entry.realization,
            target_record_ids=entry.target_record_ids,
            target_family=entry.target_family,
            mutation_type=entry.mutation_type,
            expected_semantic_effect=entry.expected_semantic_effect,
            seed_label=entry.seed_label,
            status=AuthorizationStatus.FAILED,
        )
        self._entries[authorization_id] = updated

    def is_authorized(self, target_record_id: str, mutation_type: str) -> bool:
        """Check if a mutation on a target is authorized."""
        auth_ids = self._target_index.get(target_record_id, [])
        return any(
            self._entries[aid].mutation_type == mutation_type
            for aid in auth_ids
            if aid not in self._consumed
        )

    def get_authorization_for_target(self, target_record_id: str) -> list[AuthorizationEntry]:
        """Get all authorizations for a specific target record."""
        auth_ids = self._target_index.get(target_record_id, [])
        return [self._entries[aid] for aid in auth_ids]

    def validate_completeness(self) -> list[str]:
        """Check for unused authorizations.

        Returns:
            List of error messages for unused authorizations.

        Raises:
            AuthorizationError: If any authorization was never consumed.
        """
        errors: list[str] = []
        for auth_id, entry in self._entries.items():
            if entry.status == AuthorizationStatus.PLANNED:
                errors.append(
                    f"Unused authorization: '{auth_id}' for scenario "
                    f"'{entry.scenario_id}' was never consumed"
                )
        if errors:
            raise AuthorizationError(
                f"Authorization ledger has {len(errors)} unused authorization(s)",
                context={"unused": errors},
            )
        return []

    def export_private(self) -> list[dict]:
        """Export ledger for private ground-truth package.

        Returns entries in insertion order for deterministic output.
        """
        return [entry.model_dump(mode="json") for entry in self._entries.values()]
