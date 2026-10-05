"""SAT-SA Backend Application Entrypoint.

Provides FastAPI application initialization, deterministic database schema loading,
lifespan hooks, CORS configuration, structured exception handlers, and API versioning.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from app.backend.api.router import api_v1_router
from app.backend.config import get_config
from app.backend.errors import (
    ErrorResponse,
    SATSAAppError,
    satsa_exception_handler,
)
from app.backend.logging import get_logger, setup_logging
from app.backend.persistence.database import get_engine, init_db
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown procedures."""
    setup_logging()
    logger.info("Initializing SAT-SA backend application...")

    # Deterministic database schema initialization
    engine = get_engine()
    init_db(engine)

    # Ensure evidence directory exists
    cfg = get_config()
    cfg.evidence_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Evidence storage directory ready: %s", cfg.evidence_dir)

    yield

    logger.info("Shutting down SAT-SA backend application...")
    engine.dispose()
    logger.info("SAT-SA backend cleanly stopped.")


def create_app() -> FastAPI:
    """FastAPI application factory."""
    cfg = get_config()

    app = FastAPI(
        title="SAT-SA Supervisory Evidence Backend",
        description="Air-gapped supervisory analytics and evidence processing engine.",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if cfg.is_development else None,
        redoc_url="/redoc" if cfg.is_development else None,
        openapi_url="/openapi.json" if cfg.is_development else None,
    )

    # Offline-safe CORS policy (localhost only)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost", "http://127.0.0.1", "http://localhost:3000", "http://localhost:8000"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # Register structured exception handlers
    app.add_exception_handler(SATSAAppError, satsa_exception_handler)

    @app.exception_handler(Exception)
    async def global_generic_exception_handler(request, exc):
        logger.error("Unhandled server exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_SERVER_ERROR",
                message="An unexpected internal error occurred.",
                details=str(exc) if cfg.is_development else None,
            ).model_dump(),
        )

    # Register versioned routes
    app.include_router(api_v1_router)

    return app


app = create_app()
