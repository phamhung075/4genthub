"""
Response Formatter Utilities

Standardized response formatting for MCP controllers to ensure consistent
response structure across all endpoints.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ResponseStatus(Enum):
    """Standard response status codes"""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    PARTIAL = "partial"


class ErrorCodes(Enum):
    """Standard error codes for consistent error handling"""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    CONFLICT = "CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    BAD_REQUEST = "BAD_REQUEST"
    TIMEOUT = "TIMEOUT"


class StandardResponseFormatter:
    """Standard response formatter for MCP controllers"""

    @staticmethod
    def success(
        data: Any = None, message: str = "Operation completed successfully"
    ) -> dict[str, Any]:
        """Format a successful response"""
        return {
            "status": ResponseStatus.SUCCESS.value,
            "message": message,
            "data": data,
            "timestamp": datetime.now(UTC).isoformat(),
            "success": True,
        }

    @staticmethod
    def error(
        error_code: ErrorCodes, message: str, details: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Format an error response"""
        return {
            "status": ResponseStatus.ERROR.value,
            "error_code": error_code.value,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now(UTC).isoformat(),
            "success": False,
        }

    @staticmethod
    def warning(
        data: Any = None,
        message: str = "Operation completed with warnings",
        warnings: list[str] | None = None,
    ) -> dict[str, Any]:
        """Format a warning response"""
        return {
            "status": ResponseStatus.WARNING.value,
            "message": message,
            "data": data,
            "warnings": warnings or [],
            "timestamp": datetime.now(UTC).isoformat(),
            "success": True,
        }

    @staticmethod
    def partial(
        data: Any = None,
        message: str = "Operation partially completed",
        completed: int = 0,
        total: int = 0,
    ) -> dict[str, Any]:
        """Format a partial success response"""
        return {
            "status": ResponseStatus.PARTIAL.value,
            "message": message,
            "data": data,
            "progress": {
                "completed": completed,
                "total": total,
                "percentage": (completed / total * 100) if total > 0 else 0,
            },
            "timestamp": datetime.now(UTC).isoformat(),
            "success": True,
        }

    @staticmethod
    def validation_error(errors: dict[str, list[str]]) -> dict[str, Any]:
        """Format a validation error response"""
        return StandardResponseFormatter.error(
            ErrorCodes.VALIDATION_ERROR,
            "Validation failed",
            {"validation_errors": errors},
        )

    @staticmethod
    def not_found(resource: str, identifier: str = "") -> dict[str, Any]:
        """Format a not found error response"""
        message = f"{resource} not found"
        if identifier:
            message += f" with identifier: {identifier}"

        return StandardResponseFormatter.error(
            ErrorCodes.NOT_FOUND,
            message,
            {"resource": resource, "identifier": identifier},
        )

    @staticmethod
    def unauthorized(message: str = "Authentication required") -> dict[str, Any]:
        """Format an unauthorized error response"""
        return StandardResponseFormatter.error(ErrorCodes.UNAUTHORIZED, message)

    @staticmethod
    def forbidden(message: str = "Access forbidden") -> dict[str, Any]:
        """Format a forbidden error response"""
        return StandardResponseFormatter.error(ErrorCodes.FORBIDDEN, message)
