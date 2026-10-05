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


def validate_package_safety(
    package_path: Path | str,
    base_dir: Path | str | None = None,
    max_package_size_bytes: int = 500 * 1024 * 1024,
) -> Path:
    """Validate package path safety, enforce evidence boundary, and verify package-size limit.

    1. Resolves package path canonical form and validates path traversal against base_dir.
    2. Ensures symlinks cannot escape the permitted evidence boundary.
    3. Recursively calculates total file size without loading contents into memory.
    4. Rejects packages exceeding max_package_size_bytes.
    """
    resolved_pkg = validate_path_traversal(package_path, base_dir=base_dir)

    if not resolved_pkg.exists():
        # Missing package path will be handled by pipeline existence check
        return resolved_pkg

    if not resolved_pkg.is_dir():
        return resolved_pkg

    boundary = Path(base_dir).resolve() if base_dir is not None else resolved_pkg

    total_size = 0
    visited_dirs: set[Path] = set()

    for root, dirs, files in os.walk(resolved_pkg, followlinks=False):
        current_dir = Path(root).resolve()
        if current_dir in visited_dirs:
            continue
        visited_dirs.add(current_dir)

        # 1. Check directory entries for symlinks escaping boundary
        for dname in list(dirs):
            dpath = Path(root) / dname
            if dpath.is_symlink():
                resolved_d = dpath.resolve()
                try:
                    resolved_d.relative_to(boundary)
                except ValueError as err:
                    logger.warning(
                        "Symlink directory escape detected: '%s' points to '%s' outside '%s'",
                        dpath,
                        resolved_d,
                        boundary,
                    )
                    raise SecurityError(
                        f"Symlink directory '{dname}' escapes permitted evidence boundary: {resolved_d}"
                    ) from err
                if resolved_d in visited_dirs:
                    dirs.remove(dname)

        # 2. Check files for symlinks and calculate total size
        for fname in files:
            fpath = Path(root) / fname
            resolved_f = fpath.resolve()
            try:
                resolved_f.relative_to(boundary)
            except ValueError as err:
                logger.warning(
                    "Symlink file escape detected: '%s' points to '%s' outside '%s'",
                    fpath,
                    resolved_f,
                    boundary,
                )
                raise SecurityError(
                    f"Symlink file '{fname}' escapes permitted evidence boundary: {resolved_f}"
                ) from err

            if resolved_f.is_file():
                try:
                    file_size = resolved_f.stat().st_size
                except OSError as err:
                    raise SecurityError(f"Cannot stat package file '{fpath}': {err}") from err

                total_size += file_size
                if total_size > max_package_size_bytes:
                    logger.warning(
                        "Package size limit exceeded: total %d bytes > limit %d bytes",
                        total_size,
                        max_package_size_bytes,
                    )
                    msg = (
                        f"Package total size ({total_size} bytes) "
                        f"exceeds configured limit ({max_package_size_bytes} bytes)."
                    )
                    raise SecurityError(msg)

    return resolved_pkg

