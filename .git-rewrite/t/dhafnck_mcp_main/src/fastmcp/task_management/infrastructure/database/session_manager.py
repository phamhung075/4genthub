"""
SQLAlchemy Session Manager

This module provides session management to replace the SQLite connection pool.
It offers context managers and transaction support using SQLAlchemy sessions.
"""

import logging
import threading
import time
from typing import Optional, Dict, Any, ContextManager
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .database_config import get_db_config

logger = logging.getLogger(__name__)


@dataclass
class SessionStats:
    """Session usage statistics"""
    sessions_created: int = 0
    sessions_closed: int = 0
    transactions_committed: int = 0
    transactions_rolled_back: int = 0
    session_wait_time_total: float = 0.0
    session_count: int = 0
    session_errors: int = 0
    
    def get_avg_wait_time(self) -> float:
        """Calculate average session wait time"""
        if self.session_count > 0:
            return self.session_wait_time_total / self.session_count
        return 0.0


class SQLAlchemySessionManager:
    """
    SQLAlchemy Session Manager to replace SQLite connection pool.
    
    Features:
    - Thread-safe session management
    - Transaction support
    - Session reuse within transactions
    - Performance metrics
    - Error handling and logging
    """
    
    def __init__(self):
        """Initialize the session manager"""
        self._db_config = get_db_config()
        self._stats = SessionStats()
        self._stats_lock = threading.Lock()
        
        # Thread-local storage for transaction sessions
        self._local = threading.local()
        
        logger.info("SQLAlchemy session manager initialized")
    
    @contextmanager
    def get_session(self) -> ContextManager[Session]:
        """
        Get a database session context manager.
        
        If we're in a transaction, reuse the transaction session.
        Otherwise, create a new session.
        
        Usage:
            with session_manager.get_session() as session:
                result = session.query(Model).all()
        """
        start_time = time.time()
        
        # Check if we're in a transaction
        if hasattr(self._local, 'transaction_session'):
            # Reuse transaction session
            yield self._local.transaction_session
            return
        
        # Create new session
        session = self._db_config.get_session()
        
        try:
            with self._stats_lock:
                self._stats.sessions_created += 1
                self._stats.session_count += 1
            
            logger.debug(f"Created new session (total: {self._stats.sessions_created})")
            
            yield session
            
            # Commit if no transaction context
            session.commit()
            with self._stats_lock:
                self._stats.transactions_committed += 1
                
        except SQLAlchemyError as e:
            session.rollback()
            with self._stats_lock:
                self._stats.session_errors += 1
                self._stats.transactions_rolled_back += 1
            logger.error(f"Session error: {e}")
            raise
        finally:
            # Update wait time statistics
            wait_time = time.time() - start_time
            with self._stats_lock:
                self._stats.session_wait_time_total += wait_time
                
            # Close session
            session.close()
            with self._stats_lock:
                self._stats.sessions_closed += 1
            
            logger.debug("Session closed")
    
    @contextmanager
    def transaction(self) -> ContextManager['SQLAlchemySessionManager']:
        """
        Start a database transaction.
        
        All operations within this context will be part of
        the same transaction and session.
        
        Usage:
            with session_manager.transaction() as tx_manager:
                with tx_manager.get_session() as session:
                    # All operations in same transaction
                    session.add(model1)
                with tx_manager.get_session() as session:
                    # Same session/transaction as above
                    session.add(model2)
        """
        # Check if already in transaction
        if hasattr(self._local, 'transaction_session'):
            # Nested transaction - reuse existing session
            yield self
            return
        
        # Start new transaction
        session = self._db_config.get_session()
        self._local.transaction_session = session
        
        try:
            with self._stats_lock:
                self._stats.sessions_created += 1
            
            logger.debug("Started database transaction")
            
            yield self
            
            # Commit transaction
            session.commit()
            with self._stats_lock:
                self._stats.transactions_committed += 1
            
            logger.debug("Transaction committed")
            
        except SQLAlchemyError as e:
            session.rollback()
            with self._stats_lock:
                self._stats.session_errors += 1
                self._stats.transactions_rolled_back += 1
            logger.error(f"Transaction failed: {e}")
            raise
        finally:
            # Clean up transaction session
            delattr(self._local, 'transaction_session')
            session.close()
            with self._stats_lock:
                self._stats.sessions_closed += 1
            logger.debug("Transaction session closed")
    
    def execute_query(self, query_func, *args, **kwargs):
        """
        Execute a query function with session management.
        
        Args:
            query_func: Function that takes a session as first argument
            *args: Additional positional arguments for query_func
            **kwargs: Additional keyword arguments for query_func
            
        Returns:
            Result from query_func
        """
        with self.get_session() as session:
            return query_func(session, *args, **kwargs)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session usage statistics"""
        with self._stats_lock:
            stats_dict = {
                'sessions_created': self._stats.sessions_created,
                'sessions_closed': self._stats.sessions_closed,
                'transactions_committed': self._stats.transactions_committed,
                'transactions_rolled_back': self._stats.transactions_rolled_back,
                'session_errors': self._stats.session_errors,
                'avg_wait_time': self._stats.get_avg_wait_time(),
                'total_wait_time': self._stats.session_wait_time_total,
                'session_count': self._stats.session_count,
            }
        
        # Add database info
        db_info = self._db_config.get_database_info()
        stats_dict.update({
            'database_type': db_info['type'],
            'database_url': db_info.get('url', 'N/A'),
        })
        
        return stats_dict
    
    def reset_stats(self):
        """Reset session statistics"""
        with self._stats_lock:
            self._stats = SessionStats()
        logger.info("Session statistics reset")


# Global session manager instance
_session_manager: Optional[SQLAlchemySessionManager] = None
_manager_lock = threading.Lock()


def get_session_manager() -> SQLAlchemySessionManager:
    """
    Get or create the global session manager.
    
    Returns:
        The session manager instance
    """
    global _session_manager
    
    with _manager_lock:
        if _session_manager is None:
            _session_manager = SQLAlchemySessionManager()
            logger.info("Created global session manager")
        
        return _session_manager


def close_session_manager():
    """Close the global session manager"""
    global _session_manager
    
    with _manager_lock:
        if _session_manager:
            # Session manager doesn't need explicit cleanup
            # Sessions are closed individually
            _session_manager = None
            logger.info("Session manager closed")


# Convenience functions for direct use
@contextmanager
def get_session() -> ContextManager[Session]:
    """Get a database session (convenience function)"""
    manager = get_session_manager()
    with manager.get_session() as session:
        yield session


@contextmanager
def transaction() -> ContextManager[SQLAlchemySessionManager]:
    """Start a database transaction (convenience function)"""
    manager = get_session_manager()
    with manager.transaction() as tx_manager:
        yield tx_manager