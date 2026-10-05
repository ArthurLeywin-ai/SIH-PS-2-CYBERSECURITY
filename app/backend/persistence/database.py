"""Database engine, connection management, and session handling for SAT-SA."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from app.backend.config import get_config
from app.backend.logging import get_logger
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = get_logger("persistence")


class Base(DeclarativeBase):
    """Base declarative class for all SAT-SA database models."""


def _configure_sqlite_pragmas(dbapi_con, con_record):
    """Enforce SQLite integrity & performance pragmas.
    Foreign key enforcement is relaxed at database-engine level to allow storage of anomalous/unresolved
    supervisory evidence (DATA_SCHEMA.md §9.2), while referential integrity is validated at the application layer.
    """
    cursor = dbapi_con.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF;")
    cursor.execute("PRAGMA journal_mode = WAL;")
    cursor.execute("PRAGMA synchronous = NORMAL;")
    cursor.execute("PRAGMA busy_timeout = 5000;")
    cursor.close()


def create_database_engine(url: str | None = None) -> Engine:
    """Create a configured SQLAlchemy engine."""
    db_url = url or get_config().database_url
    is_sqlite = db_url.startswith("sqlite")

    engine = create_engine(
        db_url,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False} if is_sqlite else {},
    )

    if is_sqlite:
        event.listen(engine, "connect", _configure_sqlite_pragmas)

    return engine


_ENGINE: Engine | None = None
_SESSION_FACTORY: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Retrieve or initialize global engine."""
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = create_database_engine()
    return _ENGINE


def get_session_factory() -> sessionmaker[Session]:
    """Retrieve or initialize sessionmaker factory."""
    global _SESSION_FACTORY
    if _SESSION_FACTORY is None:
        _SESSION_FACTORY = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _SESSION_FACTORY


def init_db(engine: Engine | None = None) -> None:
    """Deterministically create all database tables if they do not exist."""
    import app.backend.analytics.models  # noqa: F401
    import app.backend.persistence.models  # noqa: F401

    eng = engine or get_engine()
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=eng)
    logger.info("Database schema initialized successfully.")


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Provide a transactional database session context."""
    factory = get_session_factory()
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for yielding database session."""
    factory = get_session_factory()
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
