"""Security boundary and attack vector tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.backend.security import (
    SecurityError,
    sanitize_filename,
    validate_file_safety,
    validate_path_traversal,
)


def test_path_traversal_relative_escape(tmp_path: Path):
    base_dir = tmp_path / "safe_zone"
    base_dir.mkdir()
    outside_target = tmp_path / "safe_zone" / ".." / "secret.txt"

    with pytest.raises(SecurityError) as exc_info:
        validate_path_traversal(outside_target, base_dir)
    assert "Path traversal violation" in str(exc_info.value)


def test_path_traversal_restricted_system_directories():
    restricted_paths = ["/etc/passwd", "/var/log/syslog", "/proc/cpuinfo", "/sys/kernel"]
    for path_str in restricted_paths:
        with pytest.raises(SecurityError) as exc_info:
            validate_path_traversal(path_str)
        assert "restricted system directory" in str(exc_info.value)


def test_file_safety_disallowed_extension(tmp_path: Path):
    bad_file = tmp_path / "malicious.sh"
    bad_file.write_text("#!/bin/sh\nrm -rf /")

    with pytest.raises(SecurityError) as exc_info:
        validate_file_safety(bad_file, allowed_extensions=(".json", ".csv", ".jsonl"))
    assert "Prohibited file extension" in str(exc_info.value)


def test_file_safety_oversized_file(tmp_path: Path):
    large_file = tmp_path / "big_data.json"
    # Write 2000 bytes
    large_file.write_bytes(b"A" * 2000)

    # Set threshold to 1000 bytes
    with pytest.raises(SecurityError) as exc_info:
        validate_file_safety(large_file, max_size_bytes=1000)
    assert "exceeds safety limit" in str(exc_info.value)


def test_file_safety_nonexistent_file(tmp_path: Path):
    missing_file = tmp_path / "ghost.json"
    with pytest.raises(SecurityError) as exc_info:
        validate_file_safety(missing_file)
    assert "Target file does not exist" in str(exc_info.value)


def test_file_safety_directory_target(tmp_path: Path):
    sub_dir = tmp_path / "some_dir"
    sub_dir.mkdir()
    with pytest.raises(SecurityError) as exc_info:
        validate_file_safety(sub_dir)
    assert "not a regular file" in str(exc_info.value)


def test_sanitize_filename():
    assert sanitize_filename("../../../malicious_file.json") == "malicious_file.json"
    assert sanitize_filename("safe_export.csv") == "safe_export.csv"
    with pytest.raises(SecurityError):
        sanitize_filename("path/traversal..escape.json")
