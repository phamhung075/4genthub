"""Global error handling middleware for FastAPI."""

import time
import traceback
from typing import Callable, Dict, Any
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..task_management.domain.exceptions.task_exceptions import TaskDomainError, ErrorSeverity
from ..task_management.domain.exceptions.base_exceptions import (
    TaskManagementException,
    ValidationException,
    ResourceNotFoundException,
    DatabaseException
)

# Try to use custom logger, fall back to standard logging if it fails
try:
    from ..task_management.infrastructure.logging import TaskManagementLogger
    logger = TaskManagementLogger.get_logger(__name__)
except Exception:
    import logging
    logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware to handle all exceptions and return consistent error responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and handle any exceptions."""
        start_time = time.time()
        request_id = request.headers.get("X-Request-ID", str(time.time()))
        
        # Add request context to logger
        try:
            ctx_logger = TaskManagementLogger.add_context(
                logger,
                operation=f"{request.method} {request.url.path}",
                user_id=request.headers.get("X-User-ID")
            )
        except (AttributeError, NameError):
            # Fall back to regular logger if TaskManagementLogger not available
            ctx_logger = logger
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Log successful requests
            duration = time.time() - start_time
            ctx_logger.info(
                f"Request completed successfully",
                extra={
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "request_id": request_id
                }
            )
            
            return response
            
        except ValidationException as e:
            # Handle validation errors
            duration = time.time() - start_time
            ctx_logger.warning(
                f"Validation error: {str(e)}",
                extra={
                    "error_code": e.error_code,
                    "field": e.context.get("field"),
                    "duration_ms": round(duration * 1000, 2),
                    "request_id": request_id
                }
            )
            
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "success": False,
                    "error": e.user_message,
                    "error_code": e.error_code,
                    "details": e.context,
                    "request_id": request_id
                }
            )
            
        except ResourceNotFoundException as e:
            # Handle not found errors
            duration = time.time() - start_time
            ctx_logger.warning(
                f"Resource not found: {str(e)}",
                extra={
                    "error_code": e.error_code,
                    "resource_type": e.context.get("resource_type"),
                    "resource_id": e.context.get("resource_id"),
                    "duration_ms": round(duration * 1000, 2),
                    "request_id": request_id
                }
            )
            
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "success": False,
                    "error": e.user_message,
                    "error_code": e.error_code,
                    "details": e.context,
                    "request_id": request_id
                }
            )
            
        except DatabaseException as e:
            # Handle database errors
            duration = time.time() - start_time
            ctx_logger.error(
                f"Database error: {str(e)}",
                exc_info=True,
                extra={
                    "error_code": e.error_code,
                    "operation": e.context.get("operation"),
                    "table": e.context.get("table"),
                    "duration_ms": round(duration * 1000, 2),
                    "request_id": request_id
                }
            )
            
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "success": False,
                    "error": "Database operation failed. Please try again later.",
                    "error_code": e.error_code,
                    "request_id": request_id,
                    "recoverable": e.recoverable
                }
            )
            
        except TaskDomainError as e:
            # Handle task domain errors
            duration = time.time() - start_time
            
            # Map severity to HTTP status codes
            status_code_map = {
                ErrorSeverity.LOW: status.HTTP_400_BAD_REQUEST,
                ErrorSeverity.MEDIUM: status.HTTP_409_CONFLICT,
                ErrorSeverity.HIGH: status.HTTP_500_INTERNAL_SERVER_ERROR,
                ErrorSeverity.CRITICAL: status.HTTP_503_SERVICE_UNAVAILABLE
            }
            
            http_status = status_code_map.get(e.severity, status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            ctx_logger.error(
                f"Task domain error: {str(e)}",
                exc_info=(e.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]),
                extra={
                    "error_code": e.error_code,
                    "severity": e.severity.value,
                    "context": e.context,
                    "duration_ms": round(duration * 1000, 2),
                    "request_id": request_id
                }
            )
            
            return JSONResponse(
                status_code=http_status,
                content={
                    "success": False,
                    "error": str(e),
                    "error_code": e.error_code,
                    "severity": e.severity.value,
                    "details": e.context,
                    "request_id": request_id,
                    "recoverable": e.recoverable
                }
            )
            
        except TaskManagementException as e:
            # Handle general task management errors
            duration = time.time() - start_time
            ctx_logger.error(
                f"Task management error: {str(e)}",
                exc_info=True,
                extra={
                    "error_code": e.error_code,
                    "severity": e.severity.value,
                    "context": e.context,
                    "duration_ms": round(duration * 1000, 2),
                    "request_id": request_id
                }
            )
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "error": e.user_message,
                    "error_code": e.error_code,
                    "details": e.context,
                    "request_id": request_id,
                    "recoverable": e.recoverable
                }
            )
            
        except Exception as e:
            # Handle unexpected errors
            duration = time.time() - start_time
            error_trace = traceback.format_exc()
            
            ctx_logger.critical(
                f"Unexpected error: {str(e)}",
                extra={
                    "error_type": type(e).__name__,
                    "error_trace": error_trace,
                    "duration_ms": round(duration * 1000, 2),
                    "request_id": request_id
                }
            )
            
            # In production, don't expose internal errors
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "error": "An unexpected error occurred. Please try again later.",
                    "error_code": "INTERNAL_ERROR",
                    "request_id": request_id,
                    "recoverable": True
                }
            )


def create_error_response(
    error_code: str,
    message: str,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    details: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """Create a standardized error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": message,
            "error_code": error_code,
            "details": details or {}
        }
    )