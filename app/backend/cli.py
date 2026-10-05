"""Command-line interface for the SAT-SA application."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn
from app.backend.config import get_config
from app.backend.ingestion.pipeline import IngestionPipeline
from app.backend.logging import get_logger, setup_logging
from app.backend.persistence.database import get_db_session, get_engine, init_db

logger = get_logger("cli")


def serve() -> None:
    """Start the SAT-SA FastAPI server via uvicorn."""
    parser = argparse.ArgumentParser(description="Run the SAT-SA backend service.")
    parser.add_argument("--host", default=None, help="Host to bind server to")
    parser.add_argument("--port", type=int, default=None, help="Port to bind server to")
    parser.add_argument("--reload", action="store_true", help="Enable live reload (development only)")
    args = parser.parse_args()

    cfg = get_config()
    host = args.host or cfg.host
    port = args.port or cfg.port

    setup_logging()
    logger.info("Starting SAT-SA server at http://%s:%d", host, port)
    uvicorn.run("app.backend.main:app", host=host, port=port, reload=args.reload)


def ingest() -> None:
    """Ingest an evidence package headlessly from the command line."""
    parser = argparse.ArgumentParser(description="Ingest a SAT-SA evidence package.")
    parser.add_argument("package_path", help="Path to evidence package directory")
    parser.add_argument("--fail-on-error", action="store_true", help="Abort on blocking validation errors")
    args = parser.parse_args()

    setup_logging()
    target_path = Path(args.package_path)
    if not target_path.exists():
        logger.error("Package path does not exist: %s", target_path)
        sys.exit(1)

    init_db(get_engine())
    with get_db_session() as session:
        pipeline = IngestionPipeline()
        try:
            res = pipeline.run(target_path, db_session=session, fail_on_error=args.fail_on_error)
            logger.info("Ingestion complete. Status: %s. Records: %s", res.status, res.record_counts)
        except Exception as err:
            logger.error("Ingestion failed: %s", err)
            sys.exit(1)


if __name__ == "__main__":
    serve()
