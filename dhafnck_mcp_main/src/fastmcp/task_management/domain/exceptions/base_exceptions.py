"""Base exception hierarchy for the task management system."""

from typing import Optional, Dict, Any
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels for prioritizing handling and alerting."""
    LOW = "low"          # Can be retried or ignored
    MEDIUM = "medium"    # Should be logged and monitored
    HIGH = "high"        # Requires immediate attention
    CRITICAL = "critical"  # System-breaking, requires immediate action


class TaskManagementException(Exception):
    """Base exception for all task management errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True,
        user_message: Optional[str] = None
    ):
        """
        Initialize base exception.
        
        Args:
            message: Technical error message for logging
            error_code: Standardized error code for categorization
            severity: Error severity level
            context: Additional context data
            recoverable: Whether the operation can be retried
            user_message: User-friendly error message
        """
        super().__init__(message)
        self.error_code = error_code or self.__class__.__name__
        self.severity = severity
        self.context = context or {}
        self.recoverable = recoverable
        self.user_message = user_message or message
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for serialization."""
        return {
            "error_code": self.error_code,
            "message": str(self),
            "user_message": self.user_message,
            "severity": self.severity.value,
            "recoverable": self.recoverable,
            "context": self.context,
            "type": self.__class__.__name__
        }


class ValidationException(TaskManagementException):
    """Raised when input validation fails."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        """Initialize validation exception with field details."""
        context = kwargs.get("context", {})
        if field:
            context["field"] = field
        if value is not None:
            context["value"] = str(value)
            
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            severity=ErrorSeverity.LOW,
            recoverable=True,
            context=context,
            **kwargs
        )


class ResourceNotFoundException(TaskManagementException):
    """Raised when a requested resource cannot be found."""
    
    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        message: Optional[str] = None,
        **kwargs
    ):
        """Initialize resource not found exception."""
        if not message:
            message = f"{resource_type} with id '{resource_id}' not found"
            
        super().__init__(
            message=message,
            error_code=f"{resource_type.upper()}_NOT_FOUND",
            severity=ErrorSeverity.MEDIUM,
            recoverable=False,
            context={
                "resource_type": resource_type,
                "resource_id": resource_id
            },
            **kwargs
        )


class ResourceAlreadyExistsException(TaskManagementException):
    """Raised when attempting to create a resource that already exists."""
    
    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        message: Optional[str] = None,
        **kwargs
    ):
        """Initialize resource already exists exception."""
        if not message:
            message = f"{resource_type} with id '{resource_id}' already exists"
            
        super().__init__(
            message=message,
            error_code=f"{resource_type.upper()}_ALREADY_EXISTS",
            severity=ErrorSeverity.LOW,
            recoverable=False,
            context={
                "resource_type": resource_type,
                "resource_id": resource_id
            },
            **kwargs
        )


class OperationNotPermittedException(TaskManagementException):
    """Raised when an operation is not permitted due to business rules."""
    
    def __init__(
        self,
        operation: str,
        reason: str,
        message: Optional[str] = None,
        **kwargs
    ):
        """Initialize operation not permitted exception."""
        if not message:
            message = f"Operation '{operation}' not permitted: {reason}"
            
        super().__init__(
            message=message,
            error_code="OPERATION_NOT_PERMITTED",
            severity=ErrorSeverity.MEDIUM,
            recoverable=False,
            context={
                "operation": operation,
                "reason": reason
            },
            **kwargs
        )


class DatabaseException(TaskManagementException):
    """Base exception for database-related errors."""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        table: Optional[str] = None,
        **kwargs
    ):
        """Initialize database exception."""
        context = kwargs.get("context", {})
        if operation:
            context["operation"] = operation
        if table:
            context["table"] = table
        
        # Remove error_code from kwargs if present to avoid conflict
        kwargs.pop('error_code', None)
            
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            severity=ErrorSeverity.HIGH,
            recoverable=True,
            context=context,
            **kwargs
        )


class DatabaseConnectionException(DatabaseException):
    """Raised when database connection fails."""
    
    def __init__(self, message: str = "Failed to connect to database", **kwargs):
        """Initialize database connection exception."""
        super().__init__(
            message=message,
            error_code="DATABASE_CONNECTION_ERROR",
            severity=ErrorSeverity.CRITICAL,
            recoverable=True,
            **kwargs
        )


class DatabaseIntegrityException(DatabaseException):
    """Raised when database integrity constraints are violated."""
    
    def __init__(
        self,
        message: str,
        constraint: Optional[str] = None,
        **kwargs
    ):
        """Initialize database integrity exception."""
        context = kwargs.get("context", {})
        if constraint:
            context["constraint"] = constraint
            
        super().__init__(
            message=message,
            error_code="DATABASE_INTEGRITY_ERROR",
            severity=ErrorSeverity.MEDIUM,
            recoverable=False,
            context=context,
            **kwargs
        )


class ConcurrencyException(TaskManagementException):
    """Raised when concurrent operations conflict."""
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs
    ):
        """Initialize concurrency exception."""
        context = kwargs.get("context", {})
        if resource_type:
            context["resource_type"] = resource_type
        if resource_id:
            context["resource_id"] = resource_id
            
        super().__init__(
            message=message,
            error_code="CONCURRENCY_ERROR",
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            context=context,
            **kwargs
        )


class ExternalServiceException(TaskManagementException):
    """Raised when external service calls fail."""
    
    def __init__(
        self,
        service: str,
        message: str,
        status_code: Optional[int] = None,
        **kwargs
    ):
        """Initialize external service exception."""
        context = kwargs.get("context", {})
        context["service"] = service
        if status_code:
            context["status_code"] = status_code
            
        super().__init__(
            message=message,
            error_code=f"{service.upper()}_SERVICE_ERROR",
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            context=context,
            **kwargs
        )


class ConfigurationException(TaskManagementException):
    """Raised when configuration is invalid or missing."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        **kwargs
    ):
        """Initialize configuration exception."""
        context = kwargs.get("context", {})
        if config_key:
            context["config_key"] = config_key
            
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            severity=ErrorSeverity.CRITICAL,
            recoverable=False,
            context=context,
            **kwargs
        )


class RepositoryError(DatabaseException):
    """Raised when repository operations fail."""
    
    def __init__(
        self,
        message: str,
        repository: Optional[str] = None,
        **kwargs
    ):
        """Initialize repository exception."""
        context = kwargs.get("context", {})
        if repository:
            context["repository"] = repository
            
        # Remove error_code from kwargs if present to avoid conflict
        kwargs.pop('error_code', None)
        
        super().__init__(
            message=message,
            error_code="REPOSITORY_ERROR",
            operation="repository",
            **kwargs
        )


class NotFoundError(ResourceNotFoundException):
    """Alias for ResourceNotFoundException for backward compatibility."""
    pass


class ValidationError(ValidationException):
    """Alias for ValidationException for backward compatibility."""
    pass