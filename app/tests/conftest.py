"""Pytest fixtures for SAT-SA application testing."""
# ruff: noqa: E402

from __future__ import annotations

import sys
import tempfile
from collections.abc import Generator
from pathlib import Path

# Ensure repository root and generator source are on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
GEN_SRC = REPO_ROOT / "generator" / "src"
if GEN_SRC.exists() and str(GEN_SRC) not in sys.path:
    sys.path.insert(0, str(GEN_SRC))

import pytest
from app.backend.main import app
from app.backend.persistence.database import (
    create_database_engine,
    get_db,
    init_db,
)
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture(scope="session")
def test_temp_dir() -> Generator[Path, None, None]:
    """Provide a session-scoped temporary directory."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def test_db_engine(tmp_path: Path) -> Generator[Engine, None, None]:
    """Create a temporary SQLite database engine for testing."""
    db_file = tmp_path / "test_satsa.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_database_engine(db_url)
    init_db(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def test_db_session(test_db_engine: Engine) -> Generator[Session, None, None]:
    """Provide a test database session."""
    factory = sessionmaker(bind=test_db_engine, autocommit=False, autoflush=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(test_db_engine: Engine, tmp_path: Path) -> Generator[TestClient, None, None]:
    """FastAPI TestClient wired to the temporary test database and storage."""
    factory = sessionmaker(bind=test_db_engine, autocommit=False, autoflush=False)

    def override_get_db() -> Generator[Session, None, None]:
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    # Create temporary evidence directory
    ev_dir = tmp_path / "evidence_storage"
    ev_dir.mkdir(parents=True, exist_ok=True)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
