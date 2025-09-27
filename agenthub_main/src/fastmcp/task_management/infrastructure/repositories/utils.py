"""Enhanced Repository utility functions for clean architecture.

This module provides comprehensive utility functions for repository operations,
configuration management, and clean architecture compliance. All utilities
support the clean timestamp architecture patterns.

Key Features:
- Database configuration validation and management
- Repository pattern utilities and helpers
- Clean architecture compliance utilities
- Performance optimization helpers
- Timestamp management utilities integration

NO LEGACY SUPPORT:
- No backward compatibility with manual timestamp systems
- No fallback mechanisms for obsolete patterns
- Clean implementation only
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union, Callable, TypeVar, Generic
from contextlib import contextmanager
from functools import wraps

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..database.database_utils import get_database_utils
from ...domain.exceptions.base_exceptions import (
    DatabaseException,
    ValidationException,
    ConfigurationException
)

logger = logging.getLogger(__name__)

# Type variable for repository utilities
T = TypeVar('T')


def get_validated_database_type() -> str:
    """Get and validate the DATABASE_TYPE environment variable.

    Returns:
        str: The validated database type ('postgresql', 'sqlite', or 'supabase')

    Raises:
        ConfigurationException: If DATABASE_TYPE is not set or invalid
    """
    database_type = os.getenv('DATABASE_TYPE')
    if not database_type:
        raise ConfigurationException(
            "DATABASE_TYPE environment variable is not set. "
            "Please set DATABASE_TYPE to 'postgresql', 'sqlite', or 'supabase'"
        )

    valid_types = {'postgresql', 'sqlite', 'supabase'}
    if database_type.lower() not in valid_types:
        raise ConfigurationException(
            f"Invalid DATABASE_TYPE '{database_type}'. "
            f"Must be one of: {', '.join(valid_types)}"
        )

    return database_type.lower()


def get_repository_config() -> Dict[str, Any]:
    """Get complete repository configuration with validation.

    Returns:
        Dict with validated environment, database_type, redis_enabled, and cache settings

    Raises:
        ConfigurationException: If configuration is invalid
    """
    try:
        environment = os.getenv('ENVIRONMENT', 'production').lower()
        database_type = get_validated_database_type()

        # Validate environment
        valid_environments = {'development', 'testing', 'staging', 'production'}
        if environment not in valid_environments:
            logger.warning(f"Unknown environment '{environment}', defaulting to 'production'")
            environment = 'production'

        config = {
            'environment': environment,
            'database_type': database_type,
            'redis_enabled': os.getenv('REDIS_ENABLED', 'true').lower() == 'true',
            'use_cache': os.getenv('USE_CACHE', 'true').lower() == 'true',
            'debug_mode': environment in ('development', 'testing'),
            'performance_mode': os.getenv('PERFORMANCE_MODE', 'true').lower() == 'true',
            'timestamp_events_enabled': True,  # Always enabled in clean architecture
            'clean_architecture_mode': True   # Always enabled
        }

        logger.debug(f"Repository configuration loaded: {config}")
        return config

    except Exception as e:
        logger.error(f"Failed to load repository configuration: {e}")
        raise ConfigurationException(f"Repository configuration error: {str(e)}")


def validate_entity_timestamps(entity: Any) -> Dict[str, Any]:
    """Validate entity timestamps for clean architecture compliance.

    Args:
        entity: Entity to validate timestamps on

    Returns:
        Dict with validation results and timestamp info

    Raises:
        ValidationException: If timestamps are invalid
    """
    try:
        validation_result = {
            "entity_class": entity.__class__.__name__,
            "has_timestamps": False,
            "timestamps_valid": False,
            "created_at": None,
            "updated_at": None,
            "timezone_compliant": False,
            "errors": []
        }

        # Check if entity has timestamp attributes
        has_created_at = hasattr(entity, 'created_at')
        has_updated_at = hasattr(entity, 'updated_at')

        if not (has_created_at and has_updated_at):
            validation_result["errors"].append(
                "Entity missing required timestamp fields (created_at, updated_at)"
            )
            return validation_result

        validation_result["has_timestamps"] = True

        # Validate created_at
        created_at = getattr(entity, 'created_at')
        if created_at is not None:
            if not isinstance(created_at, datetime):
                validation_result["errors"].append(
                    f"created_at must be datetime, got {type(created_at)}"
                )
            else:
                validation_result["created_at"] = created_at.isoformat()
                if created_at.tzinfo is None or created_at.tzinfo != timezone.utc:
                    validation_result["errors"].append(
                        "created_at must be timezone-aware UTC datetime"
                    )

        # Validate updated_at
        updated_at = getattr(entity, 'updated_at')
        if updated_at is not None:
            if not isinstance(updated_at, datetime):
                validation_result["errors"].append(
                    f"updated_at must be datetime, got {type(updated_at)}"
                )
            else:
                validation_result["updated_at"] = updated_at.isoformat()
                if updated_at.tzinfo is None or updated_at.tzinfo != timezone.utc:
                    validation_result["errors"].append(
                        "updated_at must be timezone-aware UTC datetime"
                    )

        # Check timestamp relationship
        if created_at and updated_at and both_are_datetime(created_at, updated_at):
            if updated_at < created_at:
                validation_result["errors"].append(
                    "updated_at cannot be before created_at"
                )

        # Set final validation status
        validation_result["timestamps_valid"] = len(validation_result["errors"]) == 0
        validation_result["timezone_compliant"] = (
            validation_result["timestamps_valid"] and
            created_at and created_at.tzinfo == timezone.utc and
            updated_at and updated_at.tzinfo == timezone.utc
        )

        return validation_result

    except Exception as e:
        logger.error(f"Timestamp validation failed: {e}")
        raise ValidationException(f"Entity timestamp validation error: {str(e)}")


def both_are_datetime(dt1: Any, dt2: Any) -> bool:
    """Check if both values are datetime instances."""
    return isinstance(dt1, datetime) and isinstance(dt2, datetime)


def normalize_query_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize and validate query parameters.

    Args:
        params: Raw query parameters

    Returns:
        Dict with normalized parameters

    Raises:
        ValidationException: If parameters are invalid
    """
    try:
        normalized = {}
        db_utils = get_database_utils()

        for key, value in params.items():
            if value is None:
                continue

            # Handle timestamp fields
            if key.endswith('_at') or key in ('start_time', 'end_time', 'before', 'after'):
                normalized[key] = db_utils.normalize_timestamp(value)

            # Handle string fields
            elif isinstance(value, str):
                # Trim whitespace and handle empty strings
                trimmed = value.strip()
                normalized[key] = trimmed if trimmed else None

            # Handle numeric fields
            elif isinstance(value, (int, float)):
                normalized[key] = value

            # Handle boolean fields
            elif isinstance(value, bool):
                normalized[key] = value

            # Handle list fields
            elif isinstance(value, list):
                normalized[key] = [item for item in value if item is not None]

            # Pass through other types
            else:
                normalized[key] = value

        return normalized

    except Exception as e:
        logger.error(f"Query parameter normalization failed: {e}")
        raise ValidationException(f"Invalid query parameters: {str(e)}")


def with_database_error_handling(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator for consistent database error handling in repositories.

    Args:
        func: Function to wrap with error handling

    Returns:
        Wrapped function with error handling
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except ValidationException:
            # Re-raise validation exceptions as-is
            raise
        except ConfigurationException:
            # Re-raise configuration exceptions as-is
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error in {func.__name__}: {e}")
            raise DatabaseException(f"Database operation failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise DatabaseException(f"Unexpected database error: {str(e)}")

    return wrapper


def get_performance_settings() -> Dict[str, Any]:
    """Get performance optimization settings for repositories.

    Returns:
        Dict with performance configuration
    """
    config = get_repository_config()

    return {
        "batch_size": int(os.getenv('REPO_BATCH_SIZE', '100')),
        "connection_pool_size": int(os.getenv('DB_POOL_SIZE', '10')),
        "query_timeout": int(os.getenv('QUERY_TIMEOUT', '30')),
        "enable_query_cache": config.get('use_cache', True),
        "enable_lazy_loading": config.get('performance_mode', True),
        "timestamp_index_optimization": True,  # Always enabled in clean architecture
        "bulk_operations_enabled": True
    }


def get_repository_health_status() -> Dict[str, Any]:
    """Get repository system health status.

    Returns:
        Dict with health status and metrics
    """
    try:
        db_utils = get_database_utils()
        db_health = db_utils.check_database_health()
        config = get_repository_config()

        return {
            "status": "healthy" if db_health.get("status") == "healthy" else "unhealthy",
            "database_health": db_health,
            "repository_config": {
                "database_type": config["database_type"],
                "environment": config["environment"],
                "timestamp_events_active": config["timestamp_events_enabled"],
                "clean_architecture_mode": config["clean_architecture_mode"]
            },
            "performance_settings": get_performance_settings(),
            "checked_at": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Repository health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "checked_at": datetime.now(timezone.utc).isoformat()
        }


def create_repository_session_context():
    """Create a repository session context manager.

    This is a convenience function that provides access to database sessions
    with automatic error handling and transaction management.

    Returns:
        Context manager for database sessions
    """
    db_utils = get_database_utils()
    return db_utils.get_session()


class RepositoryMetrics:
    """Utility class for collecting repository operation metrics."""

    def __init__(self):
        self.operation_counts: Dict[str, int] = {}
        self.error_counts: Dict[str, int] = {}
        self.start_time = datetime.now(timezone.utc)

    def record_operation(self, operation_name: str) -> None:
        """Record a successful repository operation."""
        self.operation_counts[operation_name] = self.operation_counts.get(operation_name, 0) + 1

    def record_error(self, operation_name: str) -> None:
        """Record a failed repository operation."""
        error_key = f"{operation_name}_error"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics."""
        uptime = datetime.now(timezone.utc) - self.start_time

        return {
            "uptime_seconds": uptime.total_seconds(),
            "operation_counts": self.operation_counts.copy(),
            "error_counts": self.error_counts.copy(),
            "total_operations": sum(self.operation_counts.values()),
            "total_errors": sum(self.error_counts.values()),
            "success_rate": self._calculate_success_rate(),
            "collected_at": datetime.now(timezone.utc).isoformat()
        }

    def _calculate_success_rate(self) -> float:
        """Calculate overall success rate."""
        total_ops = sum(self.operation_counts.values())
        total_errors = sum(self.error_counts.values())

        if total_ops + total_errors == 0:
            return 1.0

        return total_ops / (total_ops + total_errors)


# Global metrics instance
_repository_metrics: Optional[RepositoryMetrics] = None


def get_repository_metrics() -> RepositoryMetrics:
    """Get singleton repository metrics instance."""
    global _repository_metrics
    if _repository_metrics is None:
        _repository_metrics = RepositoryMetrics()
    return _repository_metrics