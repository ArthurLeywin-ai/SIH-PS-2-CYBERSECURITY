"""
Seed manager — HMAC-SHA-256 child derivation with named RNG registry.

From GENERATOR_IMPLEMENTATION_PLAN §5:
- Use a 256-bit master seed as HMAC key.
- Derive child entropy with HMAC-SHA-256(master_seed, utf-8 label).
- Feed resulting entropy into pinned NumPy SeedSequence/PCG64DXSM.
- Labels follow a stable grammar and must be unique.
- Registry refuses unnamed/default RNG creation.
- Direct use of Python global random, NumPy global state, system time,
  process ID, or nondeterministic hash iteration is prohibited.
"""

from __future__ import annotations

import hashlib
import hmac

from numpy.random import PCG64DXSM, Generator, SeedSequence

from satsa_generator.core.errors import SeedError


class SeedManager:
    """Manages deterministic random stream derivation from a master seed.

    The master seed is a 256-bit (32-byte) secret. Child streams are
    derived by HMAC-SHA-256(master_seed, label.encode('utf-8')), where
    label is a stable, unique string following the grammar:

        <split>/<component>/<organization>/<period>/<family>/<purpose>/<version>

    Unused dimensions may be omitted according to documented rules.

    Attributes:
        _master_seed: The 32-byte master seed (kept in memory, never logged).
        _registry: Maps label -> (fingerprint, Generator) for audit.
        _public_alias: Opaque public alias for the master seed.
    """

    def __init__(self, master_seed: bytes, *, public_alias: str | None = None) -> None:
        """Initialize the seed manager.

        Args:
            master_seed: Exactly 32 bytes of entropy.

        Raises:
            SeedError: If master_seed is not exactly 32 bytes.
        """
        if not isinstance(master_seed, bytes):
            raise SeedError(
                "Master seed must be bytes.",
                context={"received_type": type(master_seed).__name__},
            )
        if len(master_seed) != 32:
            raise SeedError(
                f"Master seed must be exactly 32 bytes (256 bits), got {len(master_seed)}.",
                context={"received_length": len(master_seed)},
            )
        self._master_seed = master_seed
        self._registry: dict[str, tuple[str, Generator]] = {}
        # An alias, when supplied, is independently assigned by seed custody.
        # It is deliberately not derived from seed bytes.
        self._public_alias = public_alias

    @property
    def public_alias(self) -> str | None:
        """Return the independently assigned custody alias, when available."""
        return self._public_alias

    @property
    def registered_labels(self) -> list[str]:
        """List of all registered stream labels (for audit/diagnostics)."""
        return sorted(self._registry.keys())

    def get_rng(self, label: str) -> Generator:
        """Get or create a named deterministic RNG for the given label.

        If the label has already been registered, returns the same Generator.
        If not, derives a new child stream and registers it.

        Args:
            label: Unique stream label following the stable grammar.

        Returns:
            A NumPy Generator backed by PCG64DXSM.

        Raises:
            SeedError: If label is empty or invalid.
        """
        if not label or not label.strip():
            raise SeedError(
                "RNG stream label must not be empty. "
                "Direct use of unnamed/default RNG is prohibited.",
                context={"label": label},
            )

        if label in self._registry:
            return self._registry[label][1]

        # Derive child entropy
        child_entropy = self._derive_child_entropy(label)

        # Create NumPy generator with pinned bit generator
        seed_seq = SeedSequence(int.from_bytes(child_entropy, byteorder="big"))
        bit_gen = PCG64DXSM(seed_seq)
        rng = Generator(bit_gen)

        # Record fingerprint (first 8 bytes of child entropy hex — safe to log)
        fingerprint = child_entropy[:8].hex()
        self._registry[label] = (fingerprint, rng)

        return rng

    def get_child_seed_bytes(self, label: str) -> bytes:
        """Derive 32 bytes of child entropy for the given label.

        Useful when the caller needs raw bytes rather than a NumPy Generator,
        for example to pass to a sub-component or serialize privately.

        Args:
            label: Unique stream label.

        Returns:
            32 bytes of deterministic child entropy.

        Raises:
            SeedError: If label is empty.
        """
        if not label or not label.strip():
            raise SeedError(
                "Seed derivation label must not be empty.",
                context={"label": label},
            )
        return self._derive_child_entropy(label)

    def get_fingerprint(self, label: str) -> str:
        """Get the public fingerprint for a registered stream.

        Fingerprints are safe to include in public diagnostics. They are
        the first 8 bytes (16 hex chars) of the derived child entropy.

        Args:
            label: Previously registered stream label.

        Returns:
            Hex fingerprint string.

        Raises:
            SeedError: If label has not been registered.
        """
        if label not in self._registry:
            raise SeedError(
                f"Stream label not registered: '{label}'",
                context={"label": label, "registered": list(self._registry.keys())},
            )
        return self._registry[label][0]

    def public_ledger(self) -> dict[str, str]:
        """Return a sorted label-to-fingerprint diagnostic ledger."""
        return {
            label: self._registry[label][0]
            for label in sorted(self._registry)
        }

    def private_ledger_hash(self) -> str:
        """Hash registered labels and full child entropy without exposing it."""
        digest = hashlib.sha256()
        for label in sorted(self._registry):
            encoded_label = label.encode("utf-8")
            digest.update(len(encoded_label).to_bytes(4, "big"))
            digest.update(encoded_label)
            digest.update(self._derive_child_entropy(label))
        return digest.hexdigest()

    def verify_known_answer(self, label: str, expected_first_int: int) -> bool:
        """Known-answer test: verify that a stream produces the expected first value.

        This is a determinism sanity check — if the same label with the same
        master seed doesn't produce the same first random integer, something
        is wrong with the platform/dependency versions.

        Args:
            label: Stream label to test (will be registered if not already).
            expected_first_int: Expected first value from rng.integers(0, 2**63).

        Returns:
            True if the known answer matches.
        """
        # Create a fresh generator (don't consume from the registered one)
        child_entropy = self._derive_child_entropy(label)
        seed_seq = SeedSequence(int.from_bytes(child_entropy, byteorder="big"))
        bit_gen = PCG64DXSM(seed_seq)
        test_rng = Generator(bit_gen)
        actual = int(test_rng.integers(0, 2**63))
        return actual == expected_first_int

    def _derive_child_entropy(self, label: str) -> bytes:
        """Derive 32 bytes of child entropy via HMAC-SHA-256.

        HMAC(master_seed, label.encode('utf-8'))
        """
        return hmac.new(
            self._master_seed,
            label.encode("utf-8"),
            hashlib.sha256,
        ).digest()

    def __repr__(self) -> str:
        alias = f"{self._public_alias[:16]}..." if self._public_alias else "unassigned"
        return (
            f"SeedManager(alias={alias}, "
            f"streams={len(self._registry)})"
        )
