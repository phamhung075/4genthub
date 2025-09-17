"""
Redis-based EventStore Implementation for MCP Session Persistence

This module provides a Redis-backed EventStore implementation that integrates
with the existing caching infrastructure to enable persistent MCP sessions.
This solves the session connection issues by providing proper session storage
and recovery capabilities.

Author: System Architect Agent
Date: 2025-01-27
Purpose: Fix 4genthub_http session persistence issues
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import pickle
import hashlib
import uuid

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from mcp.server.streamable_http import EventStore, EventMessage
from mcp.types import JSONRPCMessage
from collections.abc import Callable, Awaitable

logger = logging.getLogger(__name__)


@dataclass
class SessionEvent:
    """Session event data structure"""
    session_id: str
    stream_id: str  # Add stream_id for proper stream management
    event_id: str   # Unique event ID for Last-Event-ID support
    event_type: str
    event_data: Dict[str, Any]
    timestamp: float
    ttl: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionEvent':
        """Create from dictionary"""
        return cls(**data)
    
    def is_expired(self) -> bool:
        """Check if event has expired"""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl

    def get_numeric_id(self) -> int:
        """Extract numeric part of event ID for ordering"""
        try:
            # Event ID format: stream_id:timestamp_ms:sequence
            parts = self.event_id.split(':')
            if len(parts) >= 2:
                return int(parts[1])  # Use timestamp for ordering
            return int(time.time() * 1000)
        except (ValueError, IndexError):
            return int(time.time() * 1000)


class RedisEventStore(EventStore):
    """Redis-based EventStore for MCP session persistence"""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        key_prefix: str = "mcp:session:",
        default_ttl: int = 3600,  # 1 hour
        max_events_per_session: int = 1000,
        compression_enabled: bool = True,
        fallback_to_memory: bool = True,
        event_id_sequence: int = 0  # Add sequence counter for unique IDs
    ):
        """
        Initialize Redis EventStore
        
        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for Redis keys
            default_ttl: Default TTL for session events in seconds
            max_events_per_session: Maximum events to store per session
            compression_enabled: Whether to compress event data
            fallback_to_memory: Whether to fallback to memory if Redis unavailable
            event_id_sequence: Starting sequence number for event IDs
        """
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl
        self.max_events_per_session = max_events_per_session
        self.compression_enabled = compression_enabled
        self.fallback_to_memory = fallback_to_memory
        self._event_sequence = event_id_sequence
        
        # Redis connection
        self._redis: Optional[redis.Redis] = None
        self._connection_healthy = False
        
        # Memory fallback
        self._memory_store: Dict[str, List[SessionEvent]] = {}
        self._using_fallback = False
        
        logger.info(f"RedisEventStore initialized with URL: {redis_url}")
    
    def _generate_event_id(self, stream_id: str) -> str:
        """Generate a unique, ordered event ID for Last-Event-ID support"""
        timestamp_ms = int(time.time() * 1000)
        self._event_sequence += 1
        return f"{stream_id}:{timestamp_ms}:{self._event_sequence:06d}"
    
    async def connect(self) -> bool:
        """Connect to Redis"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, using memory fallback")
            self._using_fallback = True
            return self.fallback_to_memory
        
        try:
            self._redis = redis.from_url(
                self.redis_url,
                decode_responses=False,  # We handle encoding ourselves
                socket_connect_timeout=2,  # Reduced timeout for faster fallback
                socket_timeout=3,  # Reduced timeout
                retry_on_timeout=False,  # Disable retries for faster fallback
                health_check_interval=30,
                retry_on_error=[],  # Don't retry on specific errors
                connection_pool=redis.ConnectionPool.from_url(
                    self.redis_url,
                    max_connections=10,
                    socket_connect_timeout=2,
                    socket_timeout=3
                )
            )
            
            # Test connection with short timeout
            await asyncio.wait_for(self._redis.ping(), timeout=2.0)
            self._connection_healthy = True
            self._using_fallback = False
            
            logger.info("Successfully connected to Redis for session storage")
            return True
            
        except (ConnectionError, asyncio.TimeoutError, OSError) as e:
            logger.warning(f"Redis not available ({type(e).__name__}): {e}")
            self._connection_healthy = False
            
            if self.fallback_to_memory:
                logger.info("Falling back to memory-based session storage")
                self._using_fallback = True
                return True
            
            return False
        except Exception as e:
            logger.error(f"Unexpected Redis connection error: {e}")
            self._connection_healthy = False
            
            if self.fallback_to_memory:
                logger.info("Falling back to memory-based session storage")
                self._using_fallback = True
                return True
            
            return False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self._redis:
            try:
                await self._redis.close()
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")
            finally:
                self._redis = None
                self._connection_healthy = False
    
    def _get_session_key(self, session_id: str, stream_id: str = None) -> str:
        """Get Redis key for session/stream"""
        if stream_id:
            return f"{self.key_prefix}{session_id}:stream:{stream_id}"
        return f"{self.key_prefix}{session_id}"
    
    def _serialize_message(self, message: Any) -> Dict[str, Any]:
        """Safely serialize message objects to prevent JSON serialization errors"""
        try:
            # Handle FastAPI JSONResponse objects
            if hasattr(message, 'body') and hasattr(message, 'status_code'):
                # This is likely a JSONResponse object
                try:
                    if hasattr(message, 'body') and isinstance(message.body, bytes):
                        # Decode JSON body
                        import json as json_lib
                        body = json_lib.loads(message.body.decode('utf-8'))
                        return {
                            "type": "json_response",
                            "body": body,
                            "status_code": getattr(message, 'status_code', 200),
                            "headers": dict(getattr(message, 'headers', {}))
                        }
                except Exception:
                    # Fallback for JSONResponse
                    return {
                        "type": "json_response", 
                        "body": str(message.body) if hasattr(message, 'body') else None,
                        "status_code": getattr(message, 'status_code', 200)
                    }
            
            # Handle Pydantic models
            if hasattr(message, 'model_dump'):
                return message.model_dump()
            
            # Handle dict-like objects
            if hasattr(message, '__dict__'):
                # Recursively serialize nested objects
                result = {"type": type(message).__name__, "message": str(message)}
                for key, value in message.__dict__.items():
                    try:
                        # Test if value is JSON serializable
                        json.dumps(value)
                        result[key] = value
                    except TypeError:
                        # Convert non-serializable values to string
                        result[key] = str(value)
                return result
            
            # Handle other types by converting to string
            return {"message": str(message), "type": type(message).__name__}
            
        except Exception as e:
            logger.error(f"Failed to serialize message: {e}")
            return {"error": f"Serialization failed: {str(e)}", "type": type(message).__name__}
    
    def _serialize_event(self, event: SessionEvent) -> bytes:
        """Serialize event for storage"""
        try:
            if self.compression_enabled:
                import gzip
                data = json.dumps(event.to_dict()).encode('utf-8')
                return gzip.compress(data)
            else:
                return json.dumps(event.to_dict()).encode('utf-8')
        except Exception as e:
            logger.error(f"Failed to serialize event: {e}")
            # Fallback to pickle
            return pickle.dumps(event)
    
    def _deserialize_event(self, data: bytes) -> Optional[SessionEvent]:
        """Deserialize event from storage"""
        try:
            if self.compression_enabled:
                import gzip
                decompressed = gzip.decompress(data)
                event_dict = json.loads(decompressed.decode('utf-8'))
                return SessionEvent.from_dict(event_dict)
            else:
                event_dict = json.loads(data.decode('utf-8'))
                return SessionEvent.from_dict(event_dict)
        except Exception as e:
            # Try pickle fallback
            try:
                return pickle.loads(data)
            except Exception as e2:
                logger.error(f"Failed to deserialize event: {e}, {e2}")
                return None
    
    async def store_event(
        self,
        stream_id: str,
        message: JSONRPCMessage
    ) -> str:
        """Store an event for a session"""
        # Generate a unique, ordered event ID
        event_id = self._generate_event_id(stream_id)
        
        # Extract session_id from stream_id if needed
        # Assuming stream_id format is session_id or session_id:stream_name
        session_id = stream_id.split(':')[0] if ':' in stream_id else stream_id
        
        # Create session event from the message
        event = SessionEvent(
            session_id=session_id,
            stream_id=stream_id,
            event_id=event_id,
            event_type="message",
            event_data={
                "message": self._serialize_message(message),
                "event_id": event_id
            },
            timestamp=time.time(),
            ttl=self.default_ttl
        )
        
        if self._using_fallback:
            await self._store_event_memory(event)
        else:
            await self._store_event_redis(event)
        
        return event_id
    
    async def _store_event_redis(self, event: SessionEvent) -> bool:
        """Store event in Redis using sorted sets for proper ordering"""
        if not self._connection_healthy or not self._redis:
            if self.fallback_to_memory:
                return await self._store_event_memory(event)
            return False
        
        try:
            session_key = self._get_session_key(event.session_id, event.stream_id)
            serialized_event = self._serialize_event(event)
            
            # Use Redis sorted set with timestamp as score for proper ordering
            pipe = self._redis.pipeline()
            score = event.get_numeric_id()  # Use timestamp for ordering
            pipe.zadd(session_key, {serialized_event: score})
            
            # Trim to max events (keep newest)
            pipe.zremrangebyrank(session_key, 0, -(self.max_events_per_session + 1))
            
            # Set TTL on the key
            pipe.expire(session_key, event.ttl or self.default_ttl)
            
            await pipe.execute()
            
            logger.debug(f"Stored event {event.event_type} for session {event.session_id}, stream {event.stream_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store event in Redis: {e}")
            self._connection_healthy = False
            
            if self.fallback_to_memory:
                return await self._store_event_memory(event)
            
            return False
    
    async def _store_event_memory(self, event: SessionEvent) -> bool:
        """Store event in memory fallback with proper ordering"""
        try:
            key = self._get_session_key(event.session_id, event.stream_id)
            
            if key not in self._memory_store:
                self._memory_store[key] = []
            
            events = self._memory_store[key]
            
            # Insert in chronological order (oldest first)
            inserted = False
            for i, existing_event in enumerate(events):
                if event.get_numeric_id() < existing_event.get_numeric_id():
                    events.insert(i, event)
                    inserted = True
                    break
            
            if not inserted:
                events.append(event)  # Add to end if newest
            
            # Trim to max events (keep newest)
            if len(events) > self.max_events_per_session:
                self._memory_store[key] = events[-self.max_events_per_session:]
            
            logger.debug(f"Stored event {event.event_type} for session {event.session_id}, stream {event.stream_id} in memory")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store event in memory: {e}")
            return False
    
    async def get_events(
        self,
        session_id: str,
        stream_id: str = None,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[SessionEvent]:
        """Get events for a session/stream"""
        if self._using_fallback:
            return await self._get_events_memory(session_id, stream_id, event_type, limit)
        else:
            return await self._get_events_redis(session_id, stream_id, event_type, limit)
    
    async def _get_events_redis(
        self,
        session_id: str,
        stream_id: str = None,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[SessionEvent]:
        """Get events from Redis"""
        if not self._connection_healthy or not self._redis:
            if self.fallback_to_memory:
                return await self._get_events_memory(session_id, stream_id, event_type, limit)
            return []
        
        try:
            session_key = self._get_session_key(session_id, stream_id)
            
            # Get events in chronological order (oldest first)
            raw_events = await self._redis.zrange(session_key, 0, limit - 1, withscores=False)
            
            events = []
            for raw_event in raw_events:
                event = self._deserialize_event(raw_event)
                if event and not event.is_expired():
                    if event_type is None or event.event_type == event_type:
                        events.append(event)
            
            logger.debug(f"Retrieved {len(events)} events for session {session_id}, stream {stream_id} from Redis")
            return events
            
        except Exception as e:
            logger.error(f"Failed to get events from Redis: {e}")
            self._connection_healthy = False
            
            if self.fallback_to_memory:
                return await self._get_events_memory(session_id, stream_id, event_type, limit)
            
            return []
    
    async def _get_events_memory(
        self,
        session_id: str,
        stream_id: str = None,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[SessionEvent]:
        """Get events from memory fallback"""
        try:
            key = self._get_session_key(session_id, stream_id)
            
            if key not in self._memory_store:
                return []
            
            events = self._memory_store[key]
            filtered_events = []
            
            for event in events:
                if not event.is_expired():
                    if event_type is None or event.event_type == event_type:
                        filtered_events.append(event)
                        if len(filtered_events) >= limit:
                            break
            
            logger.debug(f"Retrieved {len(filtered_events)} events for session {session_id}, stream {stream_id} from memory")
            return filtered_events
            
        except Exception as e:
            logger.error(f"Failed to get events from memory: {e}")
            return []
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete all events for a session"""
        success = True
        
        if not self._using_fallback and self._connection_healthy and self._redis:
            try:
                # Delete all keys matching the session pattern
                pattern = f"{self.key_prefix}{session_id}*"
                keys = await self._redis.keys(pattern)
                if keys:
                    await self._redis.delete(*keys)
                logger.debug(f"Deleted session {session_id} from Redis")
            except Exception as e:
                logger.error(f"Failed to delete session from Redis: {e}")
                success = False
        
        # Also clean from memory fallback
        try:
            keys_to_delete = [key for key in self._memory_store.keys() if key.startswith(f"{self.key_prefix}{session_id}")]
            for key in keys_to_delete:
                del self._memory_store[key]
            logger.debug(f"Deleted session {session_id} from memory")
        except Exception as e:
            logger.error(f"Failed to delete session from memory: {e}")
            success = False
        
        return success
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        cleaned = 0
        
        # Clean memory store
        try:
            expired_sessions = []
            for session_id, events in self._memory_store.items():
                # Remove expired events
                valid_events = [e for e in events if not e.is_expired()]
                if not valid_events:
                    expired_sessions.append(session_id)
                else:
                    self._memory_store[session_id] = valid_events
            
            for session_id in expired_sessions:
                del self._memory_store[session_id]
                cleaned += 1
            
            logger.debug(f"Cleaned {cleaned} expired sessions from memory")
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
        
        return cleaned
    
    async def get_session_count(self) -> int:
        """Get total number of active sessions"""
        count = 0
        
        if not self._using_fallback and self._connection_healthy and self._redis:
            try:
                # Count Redis keys with our prefix
                pattern = f"{self.key_prefix}*"
                keys = await self._redis.keys(pattern)
                count += len(keys)
            except Exception as e:
                logger.error(f"Failed to count Redis sessions: {e}")
        
        # Add memory sessions
        count += len(self._memory_store)
        
        return count
    
    async def health_check(self) -> Dict[str, Any]:
        """Get health status of the event store"""
        health = {
            "redis_available": REDIS_AVAILABLE,
            "redis_connected": self._connection_healthy,
            "using_fallback": self._using_fallback,
            "session_count": await self.get_session_count(),
            "memory_sessions": len(self._memory_store)
        }
        
        if self._redis:
            try:
                info = await self._redis.info()
                health["redis_info"] = {
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory": info.get("used_memory_human", "unknown"),
                    "uptime": info.get("uptime_in_seconds", 0)
                }
            except Exception as e:
                health["redis_error"] = str(e)
        
        return health
    
    async def replay_events_after(
        self,
        last_event_id: str,
        send_callback: Callable[[EventMessage], Awaitable[None]]
    ) -> str | None:
        """
        Replay events after the given event ID
        
        This method properly handles Last-Event-ID for session recovery.
        
        Args:
            last_event_id: The ID of the last event that was processed
            send_callback: Callback to send events to the client
            
        Returns:
            The ID of the last event sent, or None if no events were sent
        """
        try:
            # Parse the last event ID to extract session, stream, and timestamp info
            # Format: stream_id:timestamp_ms:sequence
            parts = last_event_id.split(':')
            if len(parts) < 2:
                logger.warning(f"Invalid last_event_id format: {last_event_id}")
                return None
            
            stream_id = parts[0]
            last_timestamp = int(parts[1])
            session_id = stream_id.split(':')[0] if ':' in stream_id else stream_id
            
            # Get all events for the session/stream
            events = await self.get_events(session_id, stream_id, limit=1000)
            
            # Filter events after the last timestamp
            events_to_replay = []
            for event in events:
                if event.get_numeric_id() > last_timestamp:
                    events_to_replay.append(event)
            
            # Sort events by timestamp to ensure proper order
            events_to_replay.sort(key=lambda e: e.get_numeric_id())
            
            # Send events through callback
            last_sent_id = None
            for event in events_to_replay:
                # Create JSON-RPC message from the session event
                message = JSONRPCMessage(
                    method="session/event",
                    params={
                        "event_type": event.event_type,
                        "event_data": event.event_data,
                        "timestamp": event.timestamp,
                        "session_id": event.session_id,
                        "stream_id": event.stream_id
                    }
                )
                
                # Create EventMessage with proper event ID
                event_message = EventMessage(message=message, event_id=event.event_id)
                
                # Send via callback
                await send_callback(event_message)
                last_sent_id = event.event_id
            
            logger.debug(f"Replayed {len(events_to_replay)} events for session {session_id}, stream {stream_id}")
            return last_sent_id
            
        except Exception as e:
            logger.error(f"Failed to replay events: {e}")
            return None


class MemoryEventStore(EventStore):
    """Memory-only EventStore fallback with improved Last-Event-ID support"""
    
    def __init__(self, default_ttl: int = 3600, max_events_per_session: int = 1000):
        self.default_ttl = default_ttl
        self.max_events_per_session = max_events_per_session
        self._store: Dict[str, List[SessionEvent]] = {}
        self._event_sequence = 0
        logger.info("MemoryEventStore initialized (fallback mode)")
    
    def _generate_event_id(self, stream_id: str) -> str:
        """Generate a unique, ordered event ID for Last-Event-ID support"""
        timestamp_ms = int(time.time() * 1000)
        self._event_sequence += 1
        return f"{stream_id}:{timestamp_ms}:{self._event_sequence:06d}"
    
    def _serialize_message(self, message: Any) -> Dict[str, Any]:
        """Safely serialize message objects to prevent JSON serialization errors"""
        try:
            # Handle FastAPI JSONResponse objects
            if hasattr(message, 'body') and hasattr(message, 'status_code'):
                # This is likely a JSONResponse object
                try:
                    if hasattr(message, 'body') and isinstance(message.body, bytes):
                        # Decode JSON body
                        import json as json_lib
                        body = json_lib.loads(message.body.decode('utf-8'))
                        return {
                            "type": "json_response",
                            "body": body,
                            "status_code": getattr(message, 'status_code', 200),
                            "headers": dict(getattr(message, 'headers', {}))
                        }
                except Exception:
                    # Fallback for JSONResponse
                    return {
                        "type": "json_response", 
                        "body": str(message.body) if hasattr(message, 'body') else None,
                        "status_code": getattr(message, 'status_code', 200)
                    }
            
            # Handle Pydantic models
            if hasattr(message, 'model_dump'):
                return message.model_dump()
            
            # Handle dict-like objects
            if hasattr(message, '__dict__'):
                # Recursively serialize nested objects
                result = {"type": type(message).__name__, "message": str(message)}
                for key, value in message.__dict__.items():
                    try:
                        # Test if value is JSON serializable
                        json.dumps(value)
                        result[key] = value
                    except TypeError:
                        # Convert non-serializable values to string
                        result[key] = str(value)
                return result
            
            # Handle other types by converting to string
            return {"message": str(message), "type": type(message).__name__}
            
        except Exception as e:
            logger.error(f"Failed to serialize message: {e}")
            return {"error": f"Serialization failed: {str(e)}", "type": type(message).__name__}
    
    async def store_event(
        self,
        stream_id: str,
        message: JSONRPCMessage
    ) -> str:
        """Store an event for a session"""
        # Generate a unique, ordered event ID
        event_id = self._generate_event_id(stream_id)
        
        # Extract session_id from stream_id
        if ':' in stream_id:
            session_id, actual_stream_id = stream_id.split(':', 1)
        else:
            session_id = stream_id
            actual_stream_id = stream_id
        
        # Create session event from the message
        event = SessionEvent(
            session_id=session_id,
            stream_id=stream_id,  # Keep original stream_id
            event_id=event_id,
            event_type="message",
            event_data={
                "message": self._serialize_message(message),
                "event_id": event_id
            },
            timestamp=time.time(),
            ttl=self.default_ttl
        )
        
        key = f"mcp:session:{session_id}:stream:{actual_stream_id}"
        
        if key not in self._store:
            self._store[key] = []
        
        events = self._store[key]
        
        # Insert in chronological order (oldest first)
        inserted = False
        for i, existing_event in enumerate(events):
            if event.get_numeric_id() < existing_event.get_numeric_id():
                events.insert(i, event)
                inserted = True
                break
        
        if not inserted:
            events.append(event)  # Add to end if newest
        
        # Trim to max events (keep newest)
        if len(events) > self.max_events_per_session:
            self._store[key] = events[-self.max_events_per_session:]
        
        return event_id
    
    async def get_events(
        self,
        session_id: str,
        stream_id: str = None,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[SessionEvent]:
        """Get events for a session/stream"""
        key = f"mcp:session:{session_id}:stream:{stream_id}" if stream_id else f"mcp:session:{session_id}"
        
        if key not in self._store:
            return []
        
        events = self._store[key]
        filtered_events = []
        
        for event in events:
            if not event.is_expired():
                if event_type is None or event.event_type == event_type:
                    filtered_events.append(event)
                    if len(filtered_events) >= limit:
                        break
        
        return filtered_events
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete all events for a session"""
        keys_to_delete = [key for key in self._store.keys() if key.startswith(f"mcp:session:{session_id}")]
        for key in keys_to_delete:
            del self._store[key]
        return True
    
    async def replay_events_after(
        self,
        last_event_id: str,
        send_callback: Callable[[EventMessage], Awaitable[None]]
    ) -> str | None:
        """
        Replay events after the given event ID (Memory implementation)
        
        This method properly handles Last-Event-ID for session recovery.
        """
        try:
            # Parse the last event ID to extract session, stream, and timestamp info
            parts = last_event_id.split(':')
            if len(parts) < 2:
                logger.warning(f"Invalid last_event_id format: {last_event_id}")
                return None
            
            stream_id = parts[0]
            last_timestamp = int(parts[1])
            session_id = stream_id.split(':')[0] if ':' in stream_id else stream_id
            
            # Get all events for the session/stream
            events = await self.get_events(session_id, stream_id, limit=1000)
            
            # Filter events after the last timestamp
            events_to_replay = []
            for event in events:
                if event.get_numeric_id() > last_timestamp:
                    events_to_replay.append(event)
            
            # Sort events by timestamp to ensure proper order
            events_to_replay.sort(key=lambda e: e.get_numeric_id())
            
            # Send events through callback
            last_sent_id = None
            for event in events_to_replay:
                # Create JSON-RPC message from the session event
                message = JSONRPCMessage(
                    method="session/event",
                    params={
                        "event_type": event.event_type,
                        "event_data": event.event_data,
                        "timestamp": event.timestamp,
                        "session_id": event.session_id,
                        "stream_id": event.stream_id
                    }
                )
                
                # Create EventMessage with proper event ID
                event_message = EventMessage(message=message, event_id=event.event_id)
                
                # Send via callback
                await send_callback(event_message)
                last_sent_id = event.event_id
            
            logger.debug(f"Replayed {len(events_to_replay)} events for session {session_id}, stream {stream_id} (memory)")
            return last_sent_id
            
        except Exception as e:
            logger.error(f"Failed to replay events (memory): {e}")
            return None


def create_event_store(
    redis_url: Optional[str] = None,
    fallback_to_memory: bool = True,
    **kwargs
) -> EventStore:
    """
    Factory function to create appropriate EventStore
    
    Args:
        redis_url: Redis connection URL (if None, tries environment)
        fallback_to_memory: Whether to fallback to memory if Redis unavailable
        **kwargs: Additional arguments for EventStore
    
    Returns:
        EventStore instance (Redis or Memory-based)
    """
    import os
    
    # Try to get Redis URL from environment if not provided
    if redis_url is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    if REDIS_AVAILABLE and redis_url:
        logger.info(f"Creating RedisEventStore with URL: {redis_url}")
        return RedisEventStore(
            redis_url=redis_url,
            fallback_to_memory=fallback_to_memory,
            **kwargs
        )
    else:
        logger.warning("Redis not available, creating MemoryEventStore")
        return MemoryEventStore(**kwargs)


# Global event store instance
_global_event_store: Optional[EventStore] = None


async def get_global_event_store() -> EventStore:
    """Get or create global EventStore instance"""
    global _global_event_store
    
    if _global_event_store is None:
        _global_event_store = create_event_store()
        
        # Initialize connection if it's a Redis store
        if isinstance(_global_event_store, RedisEventStore):
            await _global_event_store.connect()
    
    return _global_event_store


async def cleanup_global_event_store():
    """Cleanup global EventStore instance"""
    global _global_event_store
    
    if _global_event_store and isinstance(_global_event_store, RedisEventStore):
        await _global_event_store.disconnect()
    
    _global_event_store = None 