"""Unit tests for configuration loading and logging system."""

from __future__ import annotations

import logging

from app.backend.config import ApplicationConfig, get_config
from app.backend.logging import JSONFormatter, get_logger


def test_config_defaults():
    cfg = get_config()
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 8000
    assert "sqlite" in cfg.database_url
    assert cfg.max_file_size_bytes == 100 * 1024 * 1024


def test_config_env_overrides(monkeypatch):
    monkeypatch.setenv("SATSA_HOST", "0.0.0.0")
    monkeypatch.setenv("SATSA_PORT", "9999")
    monkeypatch.setenv("SATSA_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("SATSA_DATABASE_URL", "sqlite:///custom.db")

    cfg = ApplicationConfig()
    assert cfg.host == "0.0.0.0"
    assert cfg.port == 9999
    assert cfg.log_level == "DEBUG"
    assert cfg.database_url == "sqlite:///custom.db"


def test_json_formatter():
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message %s",
        args=("arg1",),
        exc_info=None,
    )
    output = formatter.format(record)
    assert '"level": "INFO"' in output
    assert '"logger": "test_logger"' in output
    assert "Test message arg1" in output


def test_get_logger():
    log = get_logger("my_service")
    assert log.name == "satsa.my_service"
