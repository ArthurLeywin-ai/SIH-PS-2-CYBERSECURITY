"""
Deterministic ID service.

From GENERATOR_IMPLEMENTATION_PLAN §5.5:
- Use a dataset-version namespace UUID + stable logical key to derive canonical UUIDs.
- Logical keys use public operational identity (organization, period, family,
  ordinal/source locator), never scenario ID/classification.
- Source-native IDs are rendered by source profile and may be absent.
- Scenario truth references operational IDs after they are assigned;
  operational IDs are never derived from truth labels.
- Changing row sort must not change logical IDs.
"""

from __future__ import annotations

import uuid


class IDService:
    """Deterministic UUID generation using namespace-based UUIDv5.

    All IDs are derived from a fixed dataset namespace UUID and a logical
    key string. The same namespace + key always produces the same UUID,
    regardless of execution order, parallelism, or platform.

    The namespace itself is part of the frozen version tuple, so different
    dataset versions produce different IDs for the same logical entity.

    Attributes:
        _namespace: The dataset-version namespace UUID.
    """

    def __init__(self, dataset_namespace: str) -> None:
        """Initialize the ID service.

        Args:
            dataset_namespace: A valid UUID string used as the namespace
                              for UUIDv5 generation.

        Raises:
            ValueError: If dataset_namespace is not a valid UUID.
        """
        try:
            self._namespace = uuid.UUID(dataset_namespace)
        except (ValueError, AttributeError, TypeError) as e:
            raise ValueError(
                f"dataset_namespace must be a valid UUID string, got: {dataset_namespace}"
            ) from e

    @property
    def namespace(self) -> uuid.UUID:
        """The dataset namespace UUID."""
        return self._namespace

    def generate(self, *key_parts: str) -> str:
        """Generate a deterministic UUID from logical key parts.

        The key parts are joined with '/' to form a stable logical key.
        This ensures that the same logical entity always gets the same ID.

        Args:
            *key_parts: Components of the logical key (e.g., org_id, period_id,
                       family, ordinal). Must not include scenario IDs or
                       truth labels.

        Returns:
            UUID string (lowercase hex with hyphens).

        Raises:
            ValueError: If no key parts are provided or any part is empty.

        Example:
            >>> svc = IDService("12345678-1234-5678-1234-567812345678")
            >>> svc.generate("CSE-001", "P01", "alert", "0001")
            'a1b2c3d4-...'  # Always the same for these inputs
        """
        if not key_parts:
            raise ValueError("At least one key part is required for ID generation.")
        for i, part in enumerate(key_parts):
            if not isinstance(part, str):
                raise TypeError(f"Key part at index {i} must be a string.")
            if not part or not part.strip():
                raise ValueError(f"Key part at index {i} must not be empty.")

        logical_key = "/".join(key_parts)
        return str(uuid.uuid5(self._namespace, logical_key))

    def generate_source_id(self, org_id: str, source_system: str, record_type: str,
                           ordinal: int) -> str:
        """Generate a deterministic source-native-style ID.

        Source IDs look like operational system identifiers but are fully
        deterministic. They use a different construction from canonical UUIDs
        to simulate real source-system behavior.

        Args:
            org_id: Organization identifier.
            source_system: Source system name (e.g., "SRC-A").
            record_type: Record type abbreviation (e.g., "ALT", "CSE", "INV").
            ordinal: Zero-based ordinal within the source system scope.

        Returns:
            Source-style ID string (e.g., "ALT-CSE001-SRC-A-00042").
        """
        # Strip CSE- prefix for compact source IDs
        org_num = org_id.replace("CSE-", "")
        return f"{record_type}-{org_num}-{source_system}-{ordinal:05d}"

    def __repr__(self) -> str:
        return f"IDService(namespace={self._namespace})"
