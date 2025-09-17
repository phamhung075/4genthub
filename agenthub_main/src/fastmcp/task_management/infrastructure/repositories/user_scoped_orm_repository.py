"""
User-Scoped ORM Repository

This module provides a repository class that combines BaseORMRepository
with BaseUserScopedRepository to ensure all ORM operations are properly
filtered by user_id for data isolation.
"""

import logging
from typing import Optional, List, Dict, Any, TypeVar, Generic
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .base_orm_repository import BaseORMRepository
from .base_user_scoped_repository import BaseUserScopedRepository

logger = logging.getLogger(__name__)

ModelType = TypeVar('ModelType')


class UserScopedORMRepository(BaseORMRepository[ModelType], BaseUserScopedRepository, Generic[ModelType]):
    """
    Repository that combines ORM functionality with user-based data isolation.
    
    This class ensures that all database operations are automatically scoped
    to a specific user, preventing cross-user data access.
    """
    
    def __init__(self, model_class, session: Optional[Session] = None, user_id: Optional[str] = None):
        """
        Initialize user-scoped ORM repository.
        
        Args:
            model_class: SQLAlchemy model class
            session: Database session
            user_id: User ID for data isolation
        """
        # Initialize BaseORMRepository
        BaseORMRepository.__init__(self, model_class)
        # Initialize BaseUserScopedRepository
        BaseUserScopedRepository.__init__(self, session or self.get_db_session(), user_id)
    
    def get_by_id(self, id: Any) -> Optional[ModelType]:
        """Get a model by ID with user isolation."""
        with self.get_db_session() as session:
            query = session.query(self.model_class)
            
            # Apply user filter
            query = self.apply_user_filter(query)
            
            model = query.filter(self.model_class.id == id).first()
            
            if model:
                self.log_access('read', self.model_class.__name__, str(id))
            
            return model
    
    def get_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[ModelType]:
        """Get all models with user isolation."""
        with self.get_db_session() as session:
            query = session.query(self.model_class)
            
            # Apply user filter
            query = self.apply_user_filter(query)
            
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            models = query.all()
            
            self.log_access('list', self.model_class.__name__)
            
            return models
    
    def create(self, **kwargs) -> ModelType:
        """Create a new model with automatic user_id injection."""
        # Add user_id to the data
        kwargs = self.set_user_id(kwargs)
        
        # Use parent's create method
        model = super().create(**kwargs)
        
        self.log_access('create', self.model_class.__name__, str(model.id))
        
        return model
    
    def update(self, id: Any, **kwargs) -> Optional[ModelType]:
        """Update a model with user isolation."""
        with self.get_db_session() as session:
            query = session.query(self.model_class)
            
            # Apply user filter
            query = self.apply_user_filter(query)
            
            model = query.filter(self.model_class.id == id).first()
            
            if not model:
                return None
            
            # Ensure user ownership
            self.ensure_user_ownership(model)
            
            # Remove user_id from updates to prevent changing it
            kwargs.pop('user_id', None)
            
            # Update fields
            for key, value in kwargs.items():
                if hasattr(model, key):
                    setattr(model, key, value)
            
            session.commit()
            session.refresh(model)
            
            self.log_access('update', self.model_class.__name__, str(id))
            
            return model
    
    def delete(self, id: Any) -> bool:
        """Delete a model with user isolation."""
        with self.get_db_session() as session:
            query = session.query(self.model_class)
            
            # Apply user filter
            query = self.apply_user_filter(query)
            
            model = query.filter(self.model_class.id == id).first()
            
            if not model:
                return False
            
            # Ensure user ownership
            self.ensure_user_ownership(model)
            
            session.delete(model)
            session.commit()
            
            self.log_access('delete', self.model_class.__name__, str(id))
            
            return True
    
    def find_by(self, **filters) -> List[ModelType]:
        """Find models by filters with user isolation."""
        with self.get_db_session() as session:
            query = session.query(self.model_class)
            
            # Apply user filter FIRST
            query = self.apply_user_filter(query)
            
            # Apply additional filters
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    query = query.filter(getattr(self.model_class, key) == value)
            
            models = query.all()
            
            self.log_access('search', self.model_class.__name__)
            
            return models
    
    def find_one_by(self, **filters) -> Optional[ModelType]:
        """Find one model by filters with user isolation."""
        with self.get_db_session() as session:
            query = session.query(self.model_class)
            
            # Apply user filter FIRST
            query = self.apply_user_filter(query)
            
            # Apply additional filters
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    query = query.filter(getattr(self.model_class, key) == value)
            
            model = query.first()
            
            if model:
                self.log_access('search', self.model_class.__name__)
            
            return model
    
    def count(self, **filters) -> int:
        """Count models with user isolation."""
        with self.get_db_session() as session:
            query = session.query(self.model_class)
            
            # Apply user filter
            query = self.apply_user_filter(query)
            
            # Apply additional filters
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    query = query.filter(getattr(self.model_class, key) == value)
            
            return query.count()
    
    def exists(self, **filters) -> bool:
        """Check if a model exists with user isolation."""
        return self.count(**filters) > 0
    
    def bulk_create(self, records: List[Dict[str, Any]]) -> List[ModelType]:
        """Create multiple records with user isolation."""
        # Add user_id to all records
        records = [self.set_user_id(record) for record in records]
        
        # Use parent's bulk_create
        models = super().bulk_create(records)
        
        self.log_access('bulk_create', self.model_class.__name__, f'count={len(models)}')
        
        return models
    
    def bulk_update(self, ids: List[Any], updates: Dict[str, Any]) -> int:
        """Update multiple records with user isolation."""
        with self.get_db_session() as session:
            query = session.query(self.model_class)
            
            # Apply user filter
            query = self.apply_user_filter(query)
            
            # Filter by IDs
            query = query.filter(self.model_class.id.in_(ids))
            
            # Remove user_id from updates
            updates.pop('user_id', None)
            
            # Perform bulk update
            count = query.update(updates, synchronize_session=False)
            session.commit()
            
            self.log_access('bulk_update', self.model_class.__name__, f'count={count}')
            
            return count
    
    def bulk_delete(self, ids: List[Any]) -> int:
        """Delete multiple records with user isolation."""
        with self.get_db_session() as session:
            query = session.query(self.model_class)
            
            # Apply user filter
            query = self.apply_user_filter(query)
            
            # Filter by IDs
            query = query.filter(self.model_class.id.in_(ids))
            
            # Get count before deletion
            count = query.count()
            
            # Perform bulk delete
            query.delete(synchronize_session=False)
            session.commit()
            
            self.log_access('bulk_delete', self.model_class.__name__, f'count={count}')
            
            return count