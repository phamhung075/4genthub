"""Centralized logging configuration for the task management system."""

import logging
import logging.handlers
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
import json


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "task_id"):
            log_data["task_id"] = record.task_id
        if hasattr(record, "project_id"):
            log_data["project_id"] = record.project_id
        if hasattr(record, "operation"):
            log_data["operation"] = record.operation
        if hasattr(record, "error_code"):
            log_data["error_code"] = record.error_code
            
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)


class TaskManagementLogger:
    """Centralized logger configuration for task management system."""
    
    _configured = False
    _loggers: Dict[str, logging.Logger] = {}
    
    @classmethod
    def configure(
        cls,
        log_level: str = "INFO",
        log_dir: Optional[str] = None,
        enable_console: bool = True,
        enable_file: bool = True,
        enable_json: bool = False,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ) -> None:
        """
        Configure the logging system.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Directory for log files (default: logs/)
            enable_console: Enable console output
            enable_file: Enable file output
            enable_json: Use JSON format for logs
            max_bytes: Maximum size of log file before rotation
            backup_count: Number of backup files to keep
        """
        if cls._configured:
            return
            
        # Set up log directory
        if log_dir is None:
            # Check if running in Docker container
            if os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER"):
                # In Docker, use /data/logs which is writable
                log_dir = os.environ.get("LOG_DIR", "/data/logs")
            else:
                # On host, use local logs directory
                log_dir = os.environ.get("LOG_DIR", "logs")
        
        log_path = Path(log_dir)
        try:
            log_path.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # If we can't create the log directory, disable file logging
            print(f"Warning: Cannot create log directory {log_path}, disabling file logging")
            enable_file = False
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))
        
        # Remove existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            if enable_json:
                console_handler.setFormatter(JSONFormatter())
            else:
                console_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)
        
        # File handlers
        if enable_file:
            # Main log file with rotation
            file_handler = logging.handlers.RotatingFileHandler(
                log_path / "dhafnck_mcp.log",
                maxBytes=max_bytes,
                backupCount=backup_count
            )
            if enable_json:
                file_handler.setFormatter(JSONFormatter())
            else:
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
                )
                file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
            
            # Error log file
            error_handler = logging.handlers.RotatingFileHandler(
                log_path / "dhafnck_mcp_errors.log",
                maxBytes=max_bytes,
                backupCount=backup_count
            )
            error_handler.setLevel(logging.ERROR)
            if enable_json:
                error_handler.setFormatter(JSONFormatter())
            else:
                error_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s\n%(exc_info)s'
                )
                error_handler.setFormatter(error_formatter)
            root_logger.addHandler(error_handler)
        
        # Configure specific loggers
        cls._configure_module_loggers(log_level)
        
        cls._configured = True
        
    @classmethod
    def _configure_module_loggers(cls, log_level: str) -> None:
        """Configure logging levels for specific modules."""
        # Task management modules
        logging.getLogger("fastmcp.task_management").setLevel(log_level)
        
        # Database operations - more verbose
        logging.getLogger("fastmcp.task_management.infrastructure.repositories").setLevel(
            logging.DEBUG if log_level == "DEBUG" else logging.INFO
        )
        
        # Cache operations
        logging.getLogger("fastmcp.task_management.application.services.context_cache_service").setLevel(
            logging.DEBUG if log_level == "DEBUG" else logging.INFO
        )
        
        # External libraries - less verbose
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("uvicorn").setLevel(logging.INFO)
        
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger instance with the given name.
        
        Args:
            name: Logger name (usually __name__)
            
        Returns:
            Configured logger instance
        """
        if not cls._configured:
            cls.configure()
            
        if name not in cls._loggers:
            cls._loggers[name] = logging.getLogger(name)
            
        return cls._loggers[name]
    
    @classmethod
    def add_context(
        cls,
        logger: logging.Logger,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
        project_id: Optional[str] = None,
        operation: Optional[str] = None
    ) -> logging.LoggerAdapter:
        """
        Add contextual information to logger.
        
        Args:
            logger: Base logger
            user_id: User identifier
            task_id: Task identifier
            project_id: Project identifier
            operation: Current operation name
            
        Returns:
            Logger adapter with context
        """
        extra = {}
        if user_id:
            extra["user_id"] = user_id
        if task_id:
            extra["task_id"] = task_id
        if project_id:
            extra["project_id"] = project_id
        if operation:
            extra["operation"] = operation
            
        return logging.LoggerAdapter(logger, extra)


def log_operation(operation: str):
    """
    Decorator to log operation execution with timing.
    
    Usage:
        @log_operation("create_task")
        async def create_task(...):
            ...
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            logger = TaskManagementLogger.get_logger(func.__module__)
            start_time = datetime.now(timezone.utc)
            
            # Extract context from arguments if available
            context = {}
            if "task_id" in kwargs:
                context["task_id"] = kwargs["task_id"]
            if "project_id" in kwargs:
                context["project_id"] = kwargs["project_id"]
                
            ctx_logger = TaskManagementLogger.add_context(logger, operation=operation, **context)
            
            ctx_logger.info(f"Starting {operation}")
            
            try:
                result = await func(*args, **kwargs)
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                ctx_logger.info(f"Completed {operation} in {duration:.3f}s")
                return result
            except Exception as e:
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                ctx_logger.error(
                    f"Failed {operation} after {duration:.3f}s: {str(e)}",
                    exc_info=True,
                    extra={"error_code": getattr(e, "error_code", "UNKNOWN")}
                )
                raise
                
        def sync_wrapper(*args, **kwargs):
            logger = TaskManagementLogger.get_logger(func.__module__)
            start_time = datetime.now(timezone.utc)
            
            # Extract context from arguments if available
            context = {}
            if "task_id" in kwargs:
                context["task_id"] = kwargs["task_id"]
            if "project_id" in kwargs:
                context["project_id"] = kwargs["project_id"]
                
            ctx_logger = TaskManagementLogger.add_context(logger, operation=operation, **context)
            
            ctx_logger.info(f"Starting {operation}")
            
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                ctx_logger.info(f"Completed {operation} in {duration:.3f}s")
                return result
            except Exception as e:
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                ctx_logger.error(
                    f"Failed {operation} after {duration:.3f}s: {str(e)}",
                    exc_info=True,
                    extra={"error_code": getattr(e, "error_code", "UNKNOWN")}
                )
                raise
                
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator


# Initialize default configuration
def init_logging():
    """Initialize logging with environment-based configuration."""
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    log_dir = os.environ.get("LOG_DIR", "logs")
    enable_json = os.environ.get("LOG_FORMAT", "text").lower() == "json"
    
    TaskManagementLogger.configure(
        log_level=log_level,
        log_dir=log_dir,
        enable_json=enable_json
    )