"""Security boundaries, path traversal protection, and file safety checks."""

from __future__ import annotations

import os
from pathlib import Path

from app.backend.logging import get_logger

logger = get_logger("security")


class SecurityError(Exception):
    """Raised when security boundaries, path checks, or size limits are violated."""


def validate_path_traversal(target_path: Path | str, base_dir: Path | str | None = None) -> Path:
    """Ensure a target path resolves strictly within the allowed base directory.

    Protects against path traversal attacks (e.g. '../', absolute system path breakouts, symlink attacks).
    """
    resolved_target = Path(target_path).resolve()

    if base_dir is not None:
        resolved_base = Path(base_dir).resolve()
        try:
            resolved_target.relative_to(resolved_base)
        except ValueError as err:
            logger.warning(
                "Path traversal attempt detected: target '%s' is outside base '%s'",
                resolved_target,
                resolved_base,
            )
            raise SecurityError(f"Path traversal violation: '{target_path}' is outside permitted root.") from err

    # Prevent access to system roots
    prohibited_roots = ("/etc", "/var", "/usr", "/root", "/proc", "/sys", "/dev")
    for prob in prohibited_roots:
        if str(resolved_target).startswith(prob):
            logger.warning("Attempted access to restricted system directory: %s", resolved_target)
            raise SecurityError(f"Access to restricted system directory '{prob}' is prohibited.")

    return resolved_target


def validate_file_safety(
    file_path: Path,
    *,
    allowed_extensions: tuple[str, ...] = (".json", ".csv", ".jsonl"),
    max_size_bytes: int = 100 * 1024 * 1024,
) -> None:
    """Validate file extension, existence, and size bounds before reading."""
    if not file_path.exists():
        raise SecurityError(f"Target file does not exist: {file_path}")

    if not file_path.is_file():
        raise SecurityError(f"Target path is not a regular file: {file_path}")

    # Check extension
    suffix = file_path.suffix.lower()
    if suffix not in allowed_extensions:
        raise SecurityError(f"Prohibited file extension '{suffix}'. Allowed: {list(allowed_extensions)}")

    # Check size bounds
    file_size = file_path.stat().st_size
    if file_size > max_size_bytes:
        raise SecurityError(f"File size ({file_size} bytes) exceeds safety limit ({max_size_bytes} bytes).")


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal or control characters."""
    clean = os.path.basename(filename)
    if ".." in clean or "/" in clean or "\\" in clean:
        raise SecurityError(f"Invalid filename characters in: {filename}")
    return clean
