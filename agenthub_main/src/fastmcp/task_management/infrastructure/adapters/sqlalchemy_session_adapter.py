"""SQLAlchemy Session Adapter - Infrastructure Layer"""

from typing import Any, Optional, Type, List
from contextlib import contextmanager
from sqlalchemy.orm import Session

from ...domain.interfaces.database_session import IDatabaseSession, IQuery, IDatabaseSessionFactory
from ..database.database_config import get_db_session, get_db_config


class SQLAlchemyQuery(IQuery):
    """SQLAlchemy implementation of IQuery"""
    
    def __init__(self, query):
        self._query = query
    
    def filter(self, *criterion) -> 'IQuery':
        """Filter the query by the given criteria"""
        return SQLAlchemyQuery(self._query.filter(*criterion))
    
    def filter_by(self, **kwargs) -> 'IQuery':
        """Filter the query by keyword arguments"""
        return SQLAlchemyQuery(self._query.filter_by(**kwargs))
    
    def first(self) -> Optional[Any]:
        """Return the first result or None"""
        return self._query.first()
    
    def all(self) -> List[Any]:
        """Return all results"""
        return self._query.all()
    
    def count(self) -> int:
        """Return the count of results"""
        return self._query.count()
    
    def order_by(self, *criterion) -> 'IQuery':
        """Order the query by the given criteria"""
        return SQLAlchemyQuery(self._query.order_by(*criterion))
    
    def limit(self, limit: int) -> 'IQuery':
        """Limit the number of results"""
        return SQLAlchemyQuery(self._query.limit(limit))
    
    def offset(self, offset: int) -> 'IQuery':
        """Offset the results"""
        return SQLAlchemyQuery(self._query.offset(offset))


class SQLAlchemySessionAdapter(IDatabaseSession):
    """SQLAlchemy implementation of IDatabaseSession"""
    
    def __init__(self, session: Session):
        self._session = session
    
    def query(self, model_class: Type[Any]) -> IQuery:
        """Create a query for the given model class"""
        return SQLAlchemyQuery(self._session.query(model_class))
    
    def add(self, instance: Any) -> None:
        """Add an instance to the session"""
        self._session.add(instance)
    
    def delete(self, instance: Any) -> None:
        """Delete an instance from the session"""
        self._session.delete(instance)
    
    def commit(self) -> None:
        """Commit the current transaction"""
        self._session.commit()
    
    def rollback(self) -> None:
        """Rollback the current transaction"""
        self._session.rollback()
    
    def close(self) -> None:
        """Close the session"""
        self._session.close()
    
    def flush(self) -> None:
        """Flush pending changes to the database"""
        self._session.flush()


class SQLAlchemySessionFactory(IDatabaseSessionFactory):
    """SQLAlchemy implementation of IDatabaseSessionFactory"""
    
    @contextmanager
    def create_session(self):
        """Create a new database session"""
        with get_db_session() as session:
            yield SQLAlchemySessionAdapter(session)
    
    def get_session(self) -> IDatabaseSession:
        """Get a database session"""
        db_config = get_db_config()
        session = Session(db_config.engine)
        return SQLAlchemySessionAdapter(session)