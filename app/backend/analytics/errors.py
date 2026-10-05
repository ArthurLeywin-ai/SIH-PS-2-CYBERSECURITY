"""Structured exceptions for the SAT-SA supervisory analytics engine."""

from __future__ import annotations

from typing import Any

from app.backend.errors import SATSAAppError
from fastapi import status


class AnalyticsError(SATSAAppError):
    """Base exception for supervisory analytics operations."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "ANALYTICS_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Any = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            status_code=status_code,
            details=details,
        )


class InsufficientDataError(AnalyticsError):
    """Raised when data or peer population is insufficient for robust analytical conclusions."""

    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(
            message,
            error_code="INSUFFICIENT_DATA",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class DetectorExecutionError(AnalyticsError):
    """Raised when a specific supervisory detector encounters an unexpected runtime error."""

    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(
            message,
            error_code="DETECTOR_EXECUTION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )
