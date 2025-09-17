"""Logging Service Interface - Domain Layer"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from enum import Enum


class LogLevel(Enum):
    """Log levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ILogger(ABC):
    """Domain interface for logging operations"""
    
    @abstractmethod
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message"""
        pass
    
    @abstractmethod
    def info(self, message: str, **kwargs) -> None:
        """Log info message"""
        pass
    
    @abstractmethod
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message"""
        pass
    
    @abstractmethod
    def error(self, message: str, **kwargs) -> None:
        """Log error message"""
        pass
    
    @abstractmethod
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message"""
        pass
    
    @abstractmethod
    def log(self, level: LogLevel, message: str, **kwargs) -> None:
        """Log message with specific level"""
        pass


class ILoggingService(ABC):
    """Domain interface for logging service"""
    
    @abstractmethod
    def get_logger(self, name: str) -> ILogger:
        """Get a logger by name"""
        pass
    
    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure logging service"""
        pass
    
    @abstractmethod
    def set_level(self, level: LogLevel) -> None:
        """Set logging level"""
        pass
    
    @abstractmethod
    def add_handler(self, handler_config: Dict[str, Any]) -> None:
        """Add a log handler"""
        pass
    
    @abstractmethod
    def remove_handler(self, handler_name: str) -> None:
        """Remove a log handler"""
        pass