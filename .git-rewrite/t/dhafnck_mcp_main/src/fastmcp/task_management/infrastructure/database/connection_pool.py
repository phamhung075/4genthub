"""Connection Pool Management

This module provides connection pooling functionality.
The system supports both SQLite and PostgreSQL/Supabase with optimized 
pooling for superior performance, concurrent access, and production reliability.
"""

import sqlite3
import threading
import queue
import logging
import time
import os
from typing import Optional, Dict, Any, Union
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# PostgreSQL/Supabase support
try:
    from sqlalchemy import create_engine, pool
    from sqlalchemy.orm import sessionmaker, Session
    from sqlalchemy.pool import QueuePool, NullPool
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

logger = logging.getLogger(__name__)


@dataclass
class PooledConnection:
    """Wrapper for a pooled database connection"""
    connection: sqlite3.Connection
    created_at: datetime = field(default_factory=datetime.now)
    last_used_at: datetime = field(default_factory=datetime.now)
    use_count: int = 0
    
    def is_stale(self, max_age_seconds: int = 3600) -> bool:
        """Check if connection is too old and should be recycled"""
        age = datetime.now() - self.created_at
        return age > timedelta(seconds=max_age_seconds)
    
    def mark_used(self):
        """Mark the connection as used"""
        self.last_used_at = datetime.now()
        self.use_count += 1


class SQLiteConnectionPool:
    """
    Thread-safe SQLite connection pool.
    
    Features:
    - Lazy connection creation
    - Connection recycling after max age
    - Thread-safe operations
    - Connection health checks
    - Performance metrics
    """
    
    def __init__(
        self,
        db_path: str,
        pool_size: int = 10,
        max_overflow: int = 5,
        timeout: float = 30.0,
        recycle_time: int = 3600,
        pre_ping: bool = True
    ):
        """
        Initialize the connection pool.
        
        Args:
            db_path: Path to the SQLite database
            pool_size: Number of persistent connections to maintain
            max_overflow: Maximum overflow connections to create
            timeout: Timeout in seconds to wait for a connection
            recycle_time: Time in seconds before recycling a connection
            pre_ping: Whether to test connections before using them
        """
        self._db_path = db_path
        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self._timeout = timeout
        self._recycle_time = recycle_time
        self._pre_ping = pre_ping
        
        # Connection pool queue
        self._pool = queue.Queue(maxsize=pool_size)
        self._overflow_count = 0
        self._overflow_lock = threading.Lock()
        
        # Statistics
        self._stats = {
            'connections_created': 0,
            'connections_recycled': 0,
            'get_wait_time_total': 0.0,
            'get_count': 0,
            'pool_exhausted_count': 0,
            'connection_errors': 0
        }
        self._stats_lock = threading.Lock()
        
        # Pre-create some connections
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Pre-create initial connections"""
        initial_size = min(3, self._pool_size)  # Start with 3 connections
        for _ in range(initial_size):
            try:
                conn = self._create_connection()
                pooled_conn = PooledConnection(conn)
                self._pool.put(pooled_conn, block=False)
            except queue.Full:
                break
            except Exception as e:
                logger.error(f"Failed to create initial connection: {e}")
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection"""
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        
        # Set pragmas for better performance
        conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
        conn.execute("PRAGMA synchronous=NORMAL")  # Faster writes
        conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        conn.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp tables
        conn.execute("PRAGMA mmap_size=268435456")  # 256MB memory-mapped I/O
        
        with self._stats_lock:
            self._stats['connections_created'] += 1
            
        logger.debug(f"Created new SQLite connection (total: {self._stats['connections_created']})")
        return conn
    
    def _validate_connection(self, conn: sqlite3.Connection) -> bool:
        """Validate that a connection is still usable"""
        if not self._pre_ping:
            return True
            
        try:
            conn.execute("SELECT 1").fetchone()
            return True
        except sqlite3.Error:
            return False
    
    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool.
        
        This is a context manager that automatically returns the connection
        to the pool when done.
        
        Usage:
            with pool.get_connection() as conn:
                conn.execute("SELECT * FROM tasks")
        """
        start_time = time.time()
        pooled_conn = None
        from_pool = True
        
        try:
            # Try to get from pool first
            try:
                pooled_conn = self._pool.get(timeout=self._timeout)
                
                # Check if connection needs recycling
                if pooled_conn.is_stale(self._recycle_time):
                    logger.debug("Recycling stale connection")
                    pooled_conn.connection.close()
                    with self._stats_lock:
                        self._stats['connections_recycled'] += 1
                    pooled_conn = PooledConnection(self._create_connection())
                
                # Validate connection
                elif not self._validate_connection(pooled_conn.connection):
                    logger.debug("Connection failed validation, creating new one")
                    pooled_conn.connection.close()
                    pooled_conn = PooledConnection(self._create_connection())
                
            except queue.Empty:
                # Pool exhausted, try to create overflow connection
                with self._overflow_lock:
                    if self._overflow_count < self._max_overflow:
                        logger.debug("Pool exhausted, creating overflow connection")
                        self._overflow_count += 1
                        from_pool = False
                        conn = self._create_connection()
                        pooled_conn = PooledConnection(conn)
                        
                        with self._stats_lock:
                            self._stats['pool_exhausted_count'] += 1
                    else:
                        raise TimeoutError(
                            f"Connection pool exhausted (size={self._pool_size}, "
                            f"overflow={self._overflow_count}/{self._max_overflow})"
                        )
            
            # Update statistics
            wait_time = time.time() - start_time
            with self._stats_lock:
                self._stats['get_wait_time_total'] += wait_time
                self._stats['get_count'] += 1
            
            # Mark connection as used
            pooled_conn.mark_used()
            
            # Yield the connection
            yield pooled_conn.connection
            
        except Exception as e:
            with self._stats_lock:
                self._stats['connection_errors'] += 1
            logger.error(f"Error getting connection: {e}")
            raise
            
        finally:
            # Return connection to pool if it came from pool
            if pooled_conn and from_pool:
                try:
                    self._pool.put(pooled_conn, block=False)
                except queue.Full:
                    # Pool is full, close the connection
                    pooled_conn.connection.close()
                    logger.debug("Pool full, closing connection")
            elif pooled_conn and not from_pool:
                # Overflow connection, close it
                pooled_conn.connection.close()
                with self._overflow_lock:
                    self._overflow_count -= 1
    
    def close_all(self):
        """Close all connections in the pool"""
        closed_count = 0
        
        # Close pooled connections
        while not self._pool.empty():
            try:
                pooled_conn = self._pool.get_nowait()
                pooled_conn.connection.close()
                closed_count += 1
            except queue.Empty:
                break
        
        logger.info(f"Closed {closed_count} pooled connections")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        with self._stats_lock:
            stats = self._stats.copy()
            
        # Calculate averages
        if stats['get_count'] > 0:
            stats['avg_wait_time'] = stats['get_wait_time_total'] / stats['get_count']
        else:
            stats['avg_wait_time'] = 0.0
            
        # Current pool state
        stats['pool_size'] = self._pool.qsize()
        stats['overflow_count'] = self._overflow_count
        stats['max_pool_size'] = self._pool_size
        stats['max_overflow'] = self._max_overflow
        
        return stats
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close all connections"""
        self.close_all()


# Singleton instance
_pool_instance: Optional[SQLiteConnectionPool] = None
_pool_lock = threading.Lock()


def get_connection_pool(
    db_path: str,
    pool_size: int = 10,
    **kwargs
) -> SQLiteConnectionPool:
    """
    Get or create the singleton connection pool.
    
    Args:
        db_path: Path to the SQLite database
        pool_size: Size of the connection pool
        **kwargs: Additional arguments for pool configuration
        
    Returns:
        The connection pool instance
    """
    global _pool_instance
    
    with _pool_lock:
        if _pool_instance is None:
            _pool_instance = SQLiteConnectionPool(
                db_path=db_path,
                pool_size=pool_size,
                **kwargs
            )
            logger.info(f"Created connection pool with size {pool_size}")
        
        return _pool_instance


def close_connection_pool():
    """Close the singleton connection pool"""
    global _pool_instance
    
    with _pool_lock:
        if _pool_instance:
            _pool_instance.close_all()
            _pool_instance = None
            logger.info("Connection pool closed")


# ===== Supabase/PostgreSQL Connection Pool =====

class SupabaseConnectionPool:
    """Optimized connection pool for Supabase cloud database"""
    
    def __init__(self, database_url: str, **pool_config):
        """
        Initialize connection pool with optimized settings for Supabase.
        
        Args:
            database_url: Supabase connection string
            **pool_config: Additional pool configuration
        """
        if not HAS_SQLALCHEMY:
            raise ImportError("SQLAlchemy required for Supabase connection pooling")
        
        self.database_url = database_url
        
        # Optimal pool settings for Supabase cloud
        default_config = {
            'poolclass': QueuePool,
            'pool_size': 3,           # Small pool for cloud database
            'max_overflow': 7,        # Allow some bursts
            'pool_pre_ping': True,    # Test connections before use
            'pool_recycle': 300,      # Recycle after 5 minutes
            'pool_timeout': 10,       # Wait up to 10 seconds
            'connect_args': {
                'connect_timeout': 5,  # Fast timeout for cloud
                'options': '-c statement_timeout=15000'  # 15 second statement timeout
            }
        }
        
        # Merge with user config
        for key, value in pool_config.items():
            if key == 'connect_args':
                default_config['connect_args'].update(value)
            else:
                default_config[key] = value
        
        # Create engine with connection pooling
        self.engine = create_engine(
            database_url,
            **default_config
        )
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        logger.info(f"Initialized Supabase connection pool (size={default_config['pool_size']}, overflow={default_config['max_overflow']})")
    
    @contextmanager
    def get_session(self) -> Session:
        """Get a database session from the pool"""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get current pool statistics"""
        pool_impl = self.engine.pool
        return {
            'size': pool_impl.size() if hasattr(pool_impl, 'size') else 'N/A',
            'checked_in': pool_impl.checkedin() if hasattr(pool_impl, 'checkedin') else 'N/A',
            'checked_out': pool_impl.checkedout() if hasattr(pool_impl, 'checkedout') else 'N/A',
            'overflow': pool_impl.overflow() if hasattr(pool_impl, 'overflow') else 'N/A',
            'total': pool_impl.total() if hasattr(pool_impl, 'total') else 'N/A',
            'class': pool_impl.__class__.__name__
        }
    
    def close(self):
        """Close all connections in the pool"""
        self.engine.dispose()
        logger.info("Supabase connection pool closed")


# Singleton Supabase pool
_supabase_pool: Optional[SupabaseConnectionPool] = None
_supabase_lock = threading.Lock()


def get_supabase_pool(database_url: Optional[str] = None) -> Optional[SupabaseConnectionPool]:
    """Get or create the Supabase connection pool"""
    global _supabase_pool
    
    if not HAS_SQLALCHEMY:
        return None
    
    with _supabase_lock:
        if _supabase_pool is None:
            # Get URL from environment if not provided
            if database_url is None:
                database_url = os.getenv("SUPABASE_DATABASE_URL") or os.getenv("DATABASE_URL")
            
            if database_url and "supabase" in database_url.lower():
                _supabase_pool = SupabaseConnectionPool(database_url)
                logger.info("Created Supabase connection pool")
        
        return _supabase_pool


def close_supabase_pool():
    """Close the Supabase connection pool"""
    global _supabase_pool
    
    with _supabase_lock:
        if _supabase_pool:
            _supabase_pool.close()
            _supabase_pool = None