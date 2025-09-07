"""Event Store infrastructure for persisting domain events.

This module provides event persistence capabilities for event sourcing
and audit logging in the Vision System architecture.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Type
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
import asyncio
from pathlib import Path
import pickle
import sqlite3
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class StoredEvent:
    """Represents a stored event with metadata."""
    event_id: str
    event_type: str
    event_data: Dict[str, Any]
    aggregate_id: Optional[str]
    aggregate_type: Optional[str]
    timestamp: datetime
    version: int = 1
    metadata: Optional[Dict[str, Any]] = None


class EventStore:
    """
    Event store for persisting domain events.
    
    Supports multiple storage backends and provides event sourcing capabilities.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the event store.
        
        Args:
            storage_path: Optional path for persistent storage
        """
        self.storage_path = storage_path or ":memory:"
        self._initialize_storage()
        self._event_handlers: List[Any] = []
        
    def _initialize_storage(self) -> None:
        """Initialize the storage backend."""
        # Create SQLite database for event storage
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    event_data TEXT NOT NULL,
                    aggregate_id TEXT,
                    aggregate_type TEXT,
                    timestamp TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_aggregate_id 
                ON events(aggregate_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_type 
                ON events(event_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON events(timestamp)
            """)
            
            conn.commit()
            
        logger.info(f"Event store initialized with storage: {self.storage_path}")
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(self.storage_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    async def append(self, event: Any) -> str:
        """
        Append an event to the store.
        
        Args:
            event: The domain event to store
            
        Returns:
            The event ID
        """
        import uuid
        
        # Generate event ID
        event_id = str(uuid.uuid4())
        
        # Extract aggregate information if available
        aggregate_id = None
        aggregate_type = None
        
        if hasattr(event, 'aggregate_id'):
            aggregate_id = str(event.aggregate_id)
        elif hasattr(event, 'task_id'):
            aggregate_id = str(event.task_id)
        elif hasattr(event, 'project_id'):
            aggregate_id = str(event.project_id)
            
        if hasattr(event, 'aggregate_type'):
            aggregate_type = event.aggregate_type
        elif hasattr(event, '__class__'):
            # Infer from class name
            class_name = event.__class__.__name__
            if 'Task' in class_name:
                aggregate_type = 'Task'
            elif 'Project' in class_name:
                aggregate_type = 'Project'
            elif 'Agent' in class_name:
                aggregate_type = 'Agent'
        
        # Serialize event data
        event_data = self._serialize_event(event)
        
        # Create stored event
        stored_event = StoredEvent(
            event_id=event_id,
            event_type=event.__class__.__name__,
            event_data=event_data,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            timestamp=datetime.now(timezone.utc),
            version=1,
            metadata={
                'source': 'event_store',
                'environment': 'production'
            }
        )
        
        # Store in database
        await self._store_event(stored_event)
        
        logger.debug(f"Stored event {event_id} of type {event.__class__.__name__}")
        
        return event_id
    
    async def _store_event(self, event: StoredEvent) -> None:
        """Store an event in the database."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO events (
                    event_id, event_type, event_data, aggregate_id,
                    aggregate_type, timestamp, version, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id,
                event.event_type,
                json.dumps(event.event_data),
                event.aggregate_id,
                event.aggregate_type,
                event.timestamp.isoformat(),
                event.version,
                json.dumps(event.metadata) if event.metadata else None
            ))
            conn.commit()
    
    def _serialize_event(self, event: Any) -> Dict[str, Any]:
        """Serialize an event to a dictionary."""
        if hasattr(event, 'to_dict'):
            return event.to_dict()
        elif hasattr(event, '__dict__'):
            data = {}
            for key, value in event.__dict__.items():
                if not key.startswith('_'):
                    # Handle special types
                    if isinstance(value, datetime):
                        data[key] = value.isoformat()
                    elif hasattr(value, '__dict__'):
                        data[key] = str(value)
                    else:
                        data[key] = value
            return data
        else:
            return {'data': str(event)}
    
    async def get_events(self,
                         aggregate_id: Optional[str] = None,
                         event_type: Optional[str] = None,
                         from_timestamp: Optional[datetime] = None,
                         to_timestamp: Optional[datetime] = None,
                         limit: int = 100) -> List[StoredEvent]:
        """
        Get events from the store with optional filtering.
        
        Args:
            aggregate_id: Filter by aggregate ID
            event_type: Filter by event type
            from_timestamp: Filter events after this timestamp
            to_timestamp: Filter events before this timestamp
            limit: Maximum number of events to return
            
        Returns:
            List of stored events
        """
        query = "SELECT * FROM events WHERE 1=1"
        params = []
        
        if aggregate_id:
            query += " AND aggregate_id = ?"
            params.append(aggregate_id)
            
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
            
        if from_timestamp:
            query += " AND timestamp >= ?"
            params.append(from_timestamp.isoformat())
            
        if to_timestamp:
            query += " AND timestamp <= ?"
            params.append(to_timestamp.isoformat())
            
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        events = []
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            for row in cursor:
                events.append(StoredEvent(
                    event_id=row['event_id'],
                    event_type=row['event_type'],
                    event_data=json.loads(row['event_data']),
                    aggregate_id=row['aggregate_id'],
                    aggregate_type=row['aggregate_type'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    version=row['version'],
                    metadata=json.loads(row['metadata']) if row['metadata'] else None
                ))
        
        return events
    
    async def get_aggregate_events(self, 
                                   aggregate_id: str,
                                   from_version: Optional[int] = None) -> List[StoredEvent]:
        """
        Get all events for an aggregate.
        
        Args:
            aggregate_id: The aggregate ID
            from_version: Optional version to start from
            
        Returns:
            List of events for the aggregate
        """
        query = "SELECT * FROM events WHERE aggregate_id = ?"
        params = [aggregate_id]
        
        if from_version:
            query += " AND version > ?"
            params.append(from_version)
            
        query += " ORDER BY timestamp ASC"
        
        events = []
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            for row in cursor:
                events.append(StoredEvent(
                    event_id=row['event_id'],
                    event_type=row['event_type'],
                    event_data=json.loads(row['event_data']),
                    aggregate_id=row['aggregate_id'],
                    aggregate_type=row['aggregate_type'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    version=row['version'],
                    metadata=json.loads(row['metadata']) if row['metadata'] else None
                ))
        
        return events
    
    async def get_event_by_id(self, event_id: str) -> Optional[StoredEvent]:
        """
        Get a specific event by ID.
        
        Args:
            event_id: The event ID
            
        Returns:
            The stored event or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM events WHERE event_id = ?",
                (event_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return StoredEvent(
                    event_id=row['event_id'],
                    event_type=row['event_type'],
                    event_data=json.loads(row['event_data']),
                    aggregate_id=row['aggregate_id'],
                    aggregate_type=row['aggregate_type'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    version=row['version'],
                    metadata=json.loads(row['metadata']) if row['metadata'] else None
                )
        
        return None
    
    async def get_event_count(self,
                              aggregate_id: Optional[str] = None,
                              event_type: Optional[str] = None) -> int:
        """
        Get count of events with optional filtering.
        
        Args:
            aggregate_id: Filter by aggregate ID
            event_type: Filter by event type
            
        Returns:
            Count of events
        """
        query = "SELECT COUNT(*) as count FROM events WHERE 1=1"
        params = []
        
        if aggregate_id:
            query += " AND aggregate_id = ?"
            params.append(aggregate_id)
            
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            return row['count'] if row else 0
    
    async def create_snapshot(self, 
                             aggregate_id: str,
                             aggregate_type: str,
                             snapshot_data: Dict[str, Any],
                             version: int) -> str:
        """
        Create a snapshot of an aggregate's current state.
        
        Args:
            aggregate_id: The aggregate ID
            aggregate_type: The aggregate type
            snapshot_data: The snapshot data
            version: The version number
            
        Returns:
            The snapshot ID
        """
        import uuid
        
        snapshot_event = {
            'event_id': str(uuid.uuid4()),
            'event_type': f'{aggregate_type}Snapshot',
            'event_data': snapshot_data,
            'aggregate_id': aggregate_id,
            'aggregate_type': aggregate_type,
            'timestamp': datetime.now(timezone.utc),
            'version': version,
            'metadata': {'is_snapshot': True}
        }
        
        stored_event = StoredEvent(**snapshot_event)
        await self._store_event(stored_event)
        
        logger.info(f"Created snapshot for {aggregate_type} {aggregate_id} at version {version}")
        
        return snapshot_event['event_id']
    
    async def get_latest_snapshot(self, 
                                  aggregate_id: str) -> Optional[StoredEvent]:
        """
        Get the latest snapshot for an aggregate.
        
        Args:
            aggregate_id: The aggregate ID
            
        Returns:
            The latest snapshot or None
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM events 
                WHERE aggregate_id = ? 
                AND event_type LIKE '%Snapshot'
                ORDER BY timestamp DESC
                LIMIT 1
            """, (aggregate_id,))
            
            row = cursor.fetchone()
            if row:
                return StoredEvent(
                    event_id=row['event_id'],
                    event_type=row['event_type'],
                    event_data=json.loads(row['event_data']),
                    aggregate_id=row['aggregate_id'],
                    aggregate_type=row['aggregate_type'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    version=row['version'],
                    metadata=json.loads(row['metadata']) if row['metadata'] else None
                )
        
        return None
    
    def clear(self) -> None:
        """Clear all events from the store (use with caution)."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM events")
                conn.commit()
            logger.warning("All events cleared from event store")
        except sqlite3.OperationalError as e:
            if "no such table: events" in str(e):
                # Table doesn't exist, nothing to clear
                logger.debug("Events table doesn't exist, nothing to clear")
            else:
                raise
    
    def __repr__(self) -> str:
        """String representation of the event store."""
        return f"EventStore(storage_path='{self.storage_path}')"


# Global event store instance
_global_event_store: Optional[EventStore] = None


def get_event_store(storage_path: Optional[str] = None) -> EventStore:
    """Get the global event store instance."""
    global _global_event_store
    if _global_event_store is None:
        _global_event_store = EventStore(storage_path)
    return _global_event_store


def reset_event_store() -> None:
    """Reset the global event store (mainly for testing)."""
    global _global_event_store
    if _global_event_store:
        _global_event_store.clear()
    _global_event_store = None