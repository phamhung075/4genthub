"""
Database Connection Retry Logic Module

This module provides retry logic and error handling for database connections,
particularly useful for cloud databases like Supabase that may have transient
connection issues.
"""

import time
import logging
from typing import Optional, Callable, Any, TypeVar
from functools import wraps
from sqlalchemy.exc import OperationalError, DatabaseError, TimeoutError
from psycopg2 import OperationalError as Psycopg2OperationalError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ConnectionRetryConfig:
    """Configuration for connection retry behavior"""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is retryable.
    
    Args:
        error: The exception to check
        
    Returns:
        bool: True if the error is retryable, False otherwise
    """
    retryable_errors = (
        OperationalError,
        TimeoutError,
        Psycopg2OperationalError,
    )
    
    if isinstance(error, retryable_errors):
        error_msg = str(error).lower()
        # Check for specific retryable conditions
        retryable_conditions = [
            "timeout",
            "connection",
            "could not connect",
            "connection refused",
            "connection reset",
            "broken pipe",
            "server closed the connection",
            "terminating connection",
            "connection dropped",
            "no route to host",
            "network is unreachable",
            "connection timed out",
        ]
        return any(condition in error_msg for condition in retryable_conditions)
    
    return False


def calculate_delay(
    attempt: int,
    config: ConnectionRetryConfig
) -> float:
    """
    Calculate the delay before the next retry attempt.
    
    Args:
        attempt: The current attempt number (0-indexed)
        config: The retry configuration
        
    Returns:
        float: The delay in seconds
    """
    delay = min(
        config.initial_delay * (config.exponential_base ** attempt),
        config.max_delay
    )
    
    if config.jitter:
        import random
        # Add jitter to prevent thundering herd
        delay = delay * (0.5 + random.random())
    
    return delay


def with_connection_retry(
    config: Optional[ConnectionRetryConfig] = None
) -> Callable:
    """
    Decorator to add retry logic to database operations.
    
    Args:
        config: Optional retry configuration. If not provided, uses defaults.
        
    Returns:
        Decorated function with retry logic
    """
    if config is None:
        config = ConnectionRetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_error = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    last_error = e
                    
                    if not is_retryable_error(e) or attempt >= config.max_retries:
                        logger.error(
                            f"Non-retryable error or max retries reached in {func.__name__}: {e}"
                        )
                        raise
                    
                    delay = calculate_delay(attempt, config)
                    logger.warning(
                        f"Retryable error in {func.__name__} (attempt {attempt + 1}/{config.max_retries + 1}): {e}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    time.sleep(delay)
            
            # This should not be reached, but just in case
            if last_error:
                raise last_error
            raise RuntimeError(f"Unexpected state in retry logic for {func.__name__}")
        
        return wrapper
    return decorator


class ConnectionPool:
    """
    Enhanced connection pool with retry logic and health checks.
    """
    
    def __init__(self, engine, retry_config: Optional[ConnectionRetryConfig] = None):
        self.engine = engine
        self.retry_config = retry_config or ConnectionRetryConfig()
        self._healthy = True
        self._last_health_check = 0
        self._health_check_interval = 30  # seconds
    
    @with_connection_retry()
    def get_connection(self):
        """
        Get a connection from the pool with retry logic.
        
        Returns:
            A database connection
        """
        return self.engine.connect()
    
    def is_healthy(self) -> bool:
        """
        Check if the connection pool is healthy.
        
        Returns:
            bool: True if healthy, False otherwise
        """
        current_time = time.time()
        
        # Use cached health status if recent
        if current_time - self._last_health_check < self._health_check_interval:
            return self._healthy
        
        # Perform health check
        try:
            with self.get_connection() as conn:
                conn.execute("SELECT 1")
                self._healthy = True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self._healthy = False
        
        self._last_health_check = current_time
        return self._healthy
    
    def reset(self):
        """Reset the connection pool by disposing and recreating connections."""
        try:
            self.engine.dispose()
            logger.info("Connection pool reset successfully")
            self._healthy = True
        except Exception as e:
            logger.error(f"Failed to reset connection pool: {e}")
            self._healthy = False


def create_resilient_engine(database_url: str, **engine_kwargs):
    """
    Create a SQLAlchemy engine with enhanced resilience for cloud databases.
    
    Args:
        database_url: The database connection URL
        **engine_kwargs: Additional arguments for create_engine
        
    Returns:
        A SQLAlchemy engine with retry logic
    """
    from sqlalchemy import create_engine, event
    
    # Set default resilient configurations
    resilient_defaults = {
        'pool_pre_ping': True,  # Always check connection health
        'pool_recycle': 180,  # Recycle connections every 3 minutes
        'pool_timeout': 120,  # Extended timeout for cloud databases
        'pool_size': 3,  # Minimal pool size for stability
        'max_overflow': 5,  # Very limited overflow
    }
    
    # Merge with provided kwargs
    for key, value in resilient_defaults.items():
        if key not in engine_kwargs:
            engine_kwargs[key] = value
    
    engine = create_engine(database_url, **engine_kwargs)
    
    # Add connection event listeners for additional resilience
    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_conn, connection_record):
        """Configure connection on creation."""
        connection_record.info['connect_time'] = time.time()
    
    @event.listens_for(engine, "checkout")
    def receive_checkout(dbapi_conn, connection_record, connection_proxy):
        """Validate connection on checkout."""
        # Check if connection is too old
        connect_time = connection_record.info.get('connect_time', 0)
        if time.time() - connect_time > 1800:  # 30 minutes
            # Force reconnection for old connections
            raise OperationalError("Connection too old, forcing reconnection", None, None)
    
    return engine


# Export common retry configuration
DEFAULT_RETRY_CONFIG = ConnectionRetryConfig(
    max_retries=5,  # Increased retries for cloud databases
    initial_delay=2.0,  # Start with longer delay
    max_delay=60.0,  # Allow longer max delay for cloud recovery
    exponential_base=2.0,
    jitter=True
)