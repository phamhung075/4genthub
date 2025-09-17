"""Database Session Interface - Domain Layer"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Type, List
from contextlib import contextmanager


class IDatabaseSession(ABC):
    """Domain interface for database session operations"""
    
    @abstractmethod
    def query(self, model_class: Type[Any]) -> 'IQuery':
        """Create a query for the given model class"""
        pass
    
    @abstractmethod
    def add(self, instance: Any) -> None:
        """Add an instance to the session"""
        pass
    
    @abstractmethod
    def delete(self, instance: Any) -> None:
        """Delete an instance from the session"""
        pass
    
    @abstractmethod
    def commit(self) -> None:
        """Commit the current transaction"""
        pass
    
    @abstractmethod
    def rollback(self) -> None:
        """Rollback the current transaction"""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close the session"""
        pass
    
    @abstractmethod
    def flush(self) -> None:
        """Flush pending changes to the database"""
        pass


class IQuery(ABC):
    """Domain interface for database queries"""
    
    @abstractmethod
    def filter(self, *criterion) -> 'IQuery':
        """Filter the query by the given criteria"""
        pass
    
    @abstractmethod
    def filter_by(self, **kwargs) -> 'IQuery':
        """Filter the query by keyword arguments"""
        pass
    
    @abstractmethod
    def first(self) -> Optional[Any]:
        """Return the first result or None"""
        pass
    
    @abstractmethod
    def all(self) -> List[Any]:
        """Return all results"""
        pass
    
    @abstractmethod
    def count(self) -> int:
        """Return the count of results"""
        pass
    
    @abstractmethod
    def order_by(self, *criterion) -> 'IQuery':
        """Order the query by the given criteria"""
        pass
    
    @abstractmethod
    def limit(self, limit: int) -> 'IQuery':
        """Limit the number of results"""
        pass
    
    @abstractmethod
    def offset(self, offset: int) -> 'IQuery':
        """Offset the results"""
        pass


class IDatabaseSessionFactory(ABC):
    """Domain interface for creating database sessions"""
    
    @abstractmethod
    @contextmanager
    def create_session(self):
        """Create a new database session"""
        pass
    
    @abstractmethod
    def get_session(self) -> IDatabaseSession:
        """Get a database session"""
        pass