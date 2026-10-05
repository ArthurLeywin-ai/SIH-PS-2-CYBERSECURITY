"""Safe, bounded file readers for SAT-SA evidence ingestion.

Supports JSON, JSONL, and CSV with strict encoding, size checks, and streaming where appropriate.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Generator
from pathlib import Path
from typing import Any

from app.backend.errors import InvalidPackageError
from app.backend.logging import get_logger
from app.backend.security import validate_file_safety

logger = get_logger("ingestion.reader")


class EvidenceFileReader:
    """Reads structured evidence files safely with size enforcement and strict utf-8 decoding."""

    def __init__(self, max_file_size_bytes: int = 100 * 1024 * 1024) -> None:
        self.max_file_size_bytes = max_file_size_bytes

    def read_json(self, file_path: Path) -> Any:
        """Safely read and parse a JSON file (object or array)."""
        validate_file_safety(file_path, max_size_bytes=self.max_file_size_bytes)
        try:
            with open(file_path, encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as err:
            logger.error("JSON decode error in file %s: %s", file_path.name, err)
            raise InvalidPackageError(
                f"Corrupt or invalid JSON in {file_path.name}: {err}",
                details={"file": file_path.name, "line": err.lineno, "column": err.colno},
            ) from err
        except UnicodeDecodeError as err:
            logger.error("Unicode decode error in file %s: %s", file_path.name, err)
            raise InvalidPackageError(
                f"File {file_path.name} is not valid UTF-8 text",
                details={"file": file_path.name, "error": str(err)},
            ) from err

    def read_jsonl(self, file_path: Path) -> Generator[tuple[int, dict[str, Any]], None, None]:
        """Safely stream records from a JSONL file, yielding (line_number, record)."""
        validate_file_safety(file_path, max_size_bytes=self.max_file_size_bytes)
        try:
            with open(file_path, encoding="utf-8") as f:
                for line_num, line in enumerate(f, start=1):
                    line_clean = line.strip()
                    if not line_clean:
                        continue
                    try:
                        record = json.loads(line_clean)
                        if isinstance(record, dict):
                            yield line_num, record
                        else:
                            raise InvalidPackageError(f"Line {line_num} in {file_path.name} is not a JSON object")
                    except json.JSONDecodeError as err:
                        raise InvalidPackageError(
                            f"Corrupt JSON line {line_num} in {file_path.name}: {err}",
                            details={"file": file_path.name, "line": line_num},
                        ) from err
        except UnicodeDecodeError as err:
            raise InvalidPackageError(f"File {file_path.name} is not valid UTF-8") from err

    def read_csv(self, file_path: Path) -> Generator[tuple[int, dict[str, str]], None, None]:
        """Safely stream records from a CSV file, yielding (row_number, record_dict)."""
        validate_file_safety(file_path, max_size_bytes=self.max_file_size_bytes)
        try:
            with open(file_path, encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames is None:
                    return
                for row_num, row in enumerate(reader, start=1):
                    yield row_num, dict(row)
        except csv.Error as err:
            raise InvalidPackageError(f"CSV format error in {file_path.name}: {err}") from err
        except UnicodeDecodeError as err:
            raise InvalidPackageError(f"File {file_path.name} is not valid UTF-8") from err
