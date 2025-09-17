"""
Base ORM Repository using SQLAlchemy

This module provides a base class for all ORM repositories,
handling common database operations and session management.
"""

import logging
from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from contextlib import contextmanager

from ..database.database_config import get_session
from ...domain.exceptions.base_exceptions import (
    DatabaseException,
    ResourceNotFoundException,
    ValidationException
)

logger = logging.getLogger(__name__)

# Type variable for model classes
ModelType = TypeVar("ModelType")


class BaseORMRepository(Generic[ModelType]):
    """
    Base repository class using SQLAlchemy ORM.
    
    Provides common CRUD operations and session management
    for all repository implementations.
    """
    
    def __init__(self, model_class: Type[ModelType]):
        """
        Initialize base repository.
        
        Args:
            model_class: The SQLAlchemy model class for this repository
        """
        self.model_class = model_class
        self._session: Optional[Session] = None
    
    @contextmanager
    def get_db_session(self):
        """
        Get a database session context manager.
        
        If a session is already active (from a transaction),
        use it. Otherwise, create a new session.
        """
        # CRITICAL FIX: Check for transaction session first (higher priority)
        if hasattr(self, '_session') and self._session:
            # Use existing session from transaction - HIGHEST PRIORITY
            yield self._session
        elif hasattr(self, 'session') and self.session:
            # Fall back to session attribute from BaseUserScopedRepository
            yield self.session
        else:
            # Create new session
            session = get_session()
            try:
                yield session
                session.commit()
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error: {e}")
                raise DatabaseException(
                    message=f"Database operation failed: {str(e)}",
                    operation=self.__class__.__name__,
                    table=self.model_class.__tablename__
                )
            finally:
                session.close()
    
    @contextmanager
    def transaction(self):
        """
        Start a database transaction.
        
        All operations within this context will be part of
        the same transaction.
        """
        session = get_session()
        self._session = session
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Transaction failed: {e}")
            raise DatabaseException(
                message=f"Transaction failed: {str(e)}",
                operation="transaction",
                table=self.model_class.__tablename__
            )
        finally:
            self._session = None
            session.close()
    
    def create(self, **kwargs) -> ModelType:
        """
        Create a new record.
        
        Args:
            **kwargs: Model attributes
            
        Returns:
            Created model instance
        """
        with self.get_db_session() as session:
            try:
                instance = self.model_class(**kwargs)
                session.add(instance)
                session.flush()  # Get the ID before commit
                session.refresh(instance)  # Refresh to get all defaults
                return instance
            except IntegrityError as e:
                raise ValidationException(
                    message=f"Integrity constraint violation: {str(e)}",
                    field="unknown",
                    value=str(kwargs)
                )
    
    def get_by_id(self, id: Any) -> Optional[ModelType]:
        """
        Get a record by ID.
        
        Args:
            id: Primary key value
            
        Returns:
            Model instance or None if not found
        """
        with self.get_db_session() as session:
            return session.query(self.model_class).filter(
                self.model_class.id == id
            ).first()
    
    def get_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[ModelType]:
        """
        Get all records with optional pagination.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of model instances
        """
        with self.get_db_session() as session:
            query = session.query(self.model_class)
            
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            return query.all()
    
    def update(self, id: Any, **kwargs) -> Optional[ModelType]:
        """
        Update a record by ID.
        
        Args:
            id: Primary key value
            **kwargs: Fields to update
            
        Returns:
            Updated model instance or None if not found
        """
        with self.get_db_session() as session:
            instance = session.query(self.model_class).filter(
                self.model_class.id == id
            ).first()
            
            if not instance:
                return None
            
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            
            session.flush()
            session.refresh(instance)
            return instance
    
    def delete(self, id: Any) -> bool:
        """
        Delete a record by ID.
        
        Args:
            id: Primary key value
            
        Returns:
            True if deleted, False if not found
        """
        with self.get_db_session() as session:
            instance = session.query(self.model_class).filter(
                self.model_class.id == id
            ).first()
            
            if not instance:
                return False
            
            session.delete(instance)
            # Ensure the deletion is committed
            # The context manager only commits if no session was passed in
            # So we need to explicitly commit if we have a passed-in session
            if hasattr(self, 'session') and self.session:
                session.commit()
            return True
    
    def exists(self, **filters) -> bool:
        """
        Check if a record exists with given filters.
        
        Args:
            **filters: Field filters
            
        Returns:
            True if exists, False otherwise
        """
        with self.get_db_session() as session:
            query = session.query(self.model_class)
            
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    query = query.filter(getattr(self.model_class, key) == value)
            
            return query.first() is not None
    
    def count(self, **filters) -> int:
        """
        Count records with optional filters.
        
        Args:
            **filters: Field filters
            
        Returns:
            Number of matching records
        """
        with self.get_db_session() as session:
            query = session.query(self.model_class)
            
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    query = query.filter(getattr(self.model_class, key) == value)
            
            return query.count()
    
    def find_by(self, **filters) -> List[ModelType]:
        """
        Find records by filters.
        
        Args:
            **filters: Field filters
            
        Returns:
            List of matching model instances
        """
        with self.get_db_session() as session:
            query = session.query(self.model_class)
            
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    query = query.filter(getattr(self.model_class, key) == value)
            
            return query.all()
    
    def find_one_by(self, **filters) -> Optional[ModelType]:
        """
        Find one record by filters.
        
        Args:
            **filters: Field filters
            
        Returns:
            First matching model instance or None
        """
        with self.get_db_session() as session:
            query = session.query(self.model_class)
            
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    query = query.filter(getattr(self.model_class, key) == value)
            
            return query.first()
    
    def bulk_create(self, records: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Create multiple records in a single transaction.
        
        Args:
            records: List of dictionaries with model attributes
            
        Returns:
            List of created model instances
        """
        with self.get_db_session() as session:
            instances = []
            for record in records:
                instance = self.model_class(**record)
                session.add(instance)
                instances.append(instance)
            
            session.flush()
            for instance in instances:
                session.refresh(instance)
            
            return instances
    
    def execute_query(self, query_func, **kwargs):
        """
        Execute a custom query function.
        
        Args:
            query_func: Function that takes a session and returns a query
            **kwargs: Additional arguments for the query function
            
        Returns:
            Query result
        """
        with self.get_db_session() as session:
            return query_func(session, **kwargs)