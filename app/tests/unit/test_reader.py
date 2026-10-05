"""Unit tests for evidence file readers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.backend.errors import InvalidPackageError
from app.backend.ingestion.reader import EvidenceFileReader


def test_read_valid_json(tmp_path: Path):
    reader = EvidenceFileReader()
    file_path = tmp_path / "valid.json"
    data = [{"id": 1, "name": "test"}]
    file_path.write_text(json.dumps(data), encoding="utf-8")

    parsed = reader.read_json(file_path)
    assert parsed == data


def test_read_corrupt_json(tmp_path: Path):
    reader = EvidenceFileReader()
    file_path = tmp_path / "corrupt.json"
    file_path.write_text("NOT JSON AT ALL", encoding="utf-8")

    with pytest.raises(InvalidPackageError) as exc_info:
        reader.read_json(file_path)
    assert "Corrupt or invalid JSON" in str(exc_info.value)


def test_read_jsonl(tmp_path: Path):
    reader = EvidenceFileReader()
    file_path = tmp_path / "data.jsonl"
    lines = ['{"line": 1}', '{"line": 2}', '{"line": 3}']
    file_path.write_text("\n".join(lines), encoding="utf-8")

    records = list(reader.read_jsonl(file_path))
    assert len(records) == 3
    assert records[0] == (1, {"line": 1})
    assert records[2] == (3, {"line": 3})


def test_read_csv(tmp_path: Path):
    reader = EvidenceFileReader()
    file_path = tmp_path / "data.csv"
    csv_content = "\ufeffid,name,value\n1,alpha,100\n2,beta,200\n"
    file_path.write_text(csv_content, encoding="utf-8")

    records = list(reader.read_csv(file_path))
    assert len(records) == 2
    assert records[0] == (1, {"id": "1", "name": "alpha", "value": "100"})
    assert records[1] == (2, {"id": "2", "name": "beta", "value": "200"})
