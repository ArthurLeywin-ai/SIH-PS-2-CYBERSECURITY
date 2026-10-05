"""Structured application exceptions and HTTP error handling for SAT-SA."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.backend.logging import get_logger
from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = get_logger("errors")


class ErrorResponse(BaseModel):
    """Standardized error payload returned across all API endpoints."""

    error_code: str
    message: str
    details: Any = None
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp_utc: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


# ---------------------------------------------------------------------------
# Application Exception Hierarchy
# ---------------------------------------------------------------------------


class SATSAAppError(Exception):
    """Base exception for all SAT-SA application errors."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details


class InvalidRequestError(SATSAAppError):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(
            message,
            error_code="INVALID_REQUEST",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class NotFoundError(SATSAAppError):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(
            message,
            error_code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ConflictError(SATSAAppError):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(
            message,
            error_code="CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class InvalidPackageError(SATSAAppError):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(
            message,
            error_code="INVALID_EVIDENCE_PACKAGE",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class PackageValidationFailureError(SATSAAppError):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(
            message,
            error_code="VALIDATION_FAILURE",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class SecurityViolationError(SATSAAppError):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(
            message,
            error_code="SECURITY_VIOLATION",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


# ---------------------------------------------------------------------------
# FastAPI Global Exception Handlers
# ---------------------------------------------------------------------------


async def satsa_exception_handler(request: Request, exc: SATSAAppError) -> JSONResponse:
    """Handle custom SATSAAppError exceptions with structured JSON."""
    logger.warning(
        "Application error [%s]: %s (path: %s)",
        exc.error_code,
        exc.message,
        request.url.path,
    )
    payload = ErrorResponse(
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions safely without leaking internal stack traces."""
    logger.error("Unhandled server exception on %s: %s", request.url.path, str(exc), exc_info=exc)
    payload = ErrorResponse(
        error_code="INTERNAL_SERVER_ERROR",
        message="An internal server error occurred. Please contact the examiner system administrator.",
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=payload.model_dump(),
    )
