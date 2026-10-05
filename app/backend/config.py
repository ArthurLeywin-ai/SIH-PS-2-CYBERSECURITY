"""Central configuration management for SAT-SA application."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


class ApplicationConfig(BaseModel):
    """Configuration settings supporting environment variable overrides and sensible defaults."""

    app_name: str = "SAT-SA Supervisory Analytics Tool"
    version: str = "0.1.0"
    environment: str = Field(default_factory=lambda: os.getenv("SATSA_ENV", "development"))
    debug: bool = Field(default_factory=lambda: os.getenv("SATSA_DEBUG", "false").lower() == "true")

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development" or self.debug

    # Server settings
    host: str = Field(default_factory=lambda: os.getenv("SATSA_HOST", "127.0.0.1"))
    port: int = Field(default_factory=lambda: int(os.getenv("SATSA_PORT", "8000")))

    # Database settings
    database_url: str = Field(
        default_factory=lambda: os.getenv(
            "SATSA_DATABASE_URL",
            f"sqlite:///{Path(os.getenv('SATSA_DATA_DIR', './data')).resolve() / 'satsa.db'}",
        )
    )

    # Ingestion and storage boundaries
    evidence_dir: Path = Field(default_factory=lambda: Path(os.getenv("SATSA_EVIDENCE_DIR", "./evidence")).resolve())
    max_package_size_bytes: int = Field(
        default_factory=lambda: int(os.getenv("SATSA_MAX_PACKAGE_SIZE", str(500 * 1024 * 1024)))  # 500 MB
    )
    max_file_size_bytes: int = Field(
        default_factory=lambda: int(os.getenv("SATSA_MAX_FILE_SIZE", str(100 * 1024 * 1024)))  # 100 MB
    )
    allowed_extensions: tuple[str, ...] = (".json", ".csv", ".jsonl")

    # Logging settings
    log_level: str = Field(default_factory=lambda: os.getenv("SATSA_LOG_LEVEL", "INFO").upper())
    log_format: str = Field(default_factory=lambda: os.getenv("SATSA_LOG_FORMAT", "text").lower())

    def ensure_directories(self) -> None:
        """Create configured data and evidence directories if absent."""
        if self.database_url.startswith("sqlite:///"):
            db_file = Path(self.database_url.replace("sqlite:///", ""))
            db_file.parent.mkdir(parents=True, exist_ok=True)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)


_GLOBAL_CONFIG: ApplicationConfig | None = None


def get_config() -> ApplicationConfig:
    """Retrieve or initialize the singleton application configuration."""
    global _GLOBAL_CONFIG
    if _GLOBAL_CONFIG is None:
        _GLOBAL_CONFIG = ApplicationConfig()
        _GLOBAL_CONFIG.ensure_directories()
    return _GLOBAL_CONFIG


def set_config(config: ApplicationConfig) -> None:
    """Explicitly override configuration (useful for testing)."""
    global _GLOBAL_CONFIG
    _GLOBAL_CONFIG = config
    _GLOBAL_CONFIG.ensure_directories()
