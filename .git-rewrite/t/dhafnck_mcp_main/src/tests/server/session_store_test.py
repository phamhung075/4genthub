"""
Tests for session store implementations.
"""

import pytest
import asyncio
import time
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from fastmcp.server.session_store import (
    SessionEvent,
    RedisEventStore,
    MemoryEventStore,
    create_event_store,
    get_global_event_store,
    cleanup_global_event_store,
)
from mcp.types import JSONRPCMessage
from mcp.server.streamable_http import EventMessage


class TestSessionEvent:
    """Test the SessionEvent data class."""

    def test_session_event_creation(self):
        """Test creating a session event."""
        event = SessionEvent(
            session_id="session-123",
            stream_id="stream-456",
            event_id="event-789",
            event_type="message",
            event_data={"test": "data"},
            timestamp=time.time()
        )
        
        assert event.session_id == "session-123"
        assert event.stream_id == "stream-456"
        assert event.event_id == "event-789"
        assert event.event_type == "message"
        assert event.event_data == {"test": "data"}

    def test_session_event_to_dict(self):
        """Test converting session event to dictionary."""
        timestamp = time.time()
        event = SessionEvent(
            session_id="session-123",
            stream_id="stream-456",
            event_id="event-789",
            event_type="message",
            event_data={"test": "data"},
            timestamp=timestamp,
            ttl=3600
        )
        
        event_dict = event.to_dict()
        assert event_dict["session_id"] == "session-123"
        assert event_dict["stream_id"] == "stream-456"
        assert event_dict["event_id"] == "event-789"
        assert event_dict["timestamp"] == timestamp
        assert event_dict["ttl"] == 3600

    def test_session_event_from_dict(self):
        """Test creating session event from dictionary."""
        timestamp = time.time()
        event_dict = {
            "session_id": "session-123",
            "stream_id": "stream-456",
            "event_id": "event-789",
            "event_type": "message",
            "event_data": {"test": "data"},
            "timestamp": timestamp,
            "ttl": 3600
        }
        
        event = SessionEvent.from_dict(event_dict)
        assert event.session_id == "session-123"
        assert event.stream_id == "stream-456"
        assert event.event_type == "message"
        assert event.timestamp == timestamp

    def test_session_event_is_expired(self):
        """Test checking if event is expired."""
        # Event without TTL should never expire
        event = SessionEvent(
            session_id="test",
            stream_id="test",
            event_id="test",
            event_type="test",
            event_data={},
            timestamp=time.time()
        )
        assert not event.is_expired()
        
        # Event with future TTL should not be expired
        future_event = SessionEvent(
            session_id="test",
            stream_id="test",
            event_id="test",
            event_type="test",
            event_data={},
            timestamp=time.time(),
            ttl=3600
        )
        assert not future_event.is_expired()
        
        # Event with past TTL should be expired
        past_event = SessionEvent(
            session_id="test",
            stream_id="test",
            event_id="test",
            event_type="test",
            event_data={},
            timestamp=time.time() - 7200,  # 2 hours ago
            ttl=3600  # 1 hour TTL
        )
        assert past_event.is_expired()

    def test_get_numeric_id(self):
        """Test extracting numeric ID from event ID."""
        # Standard format
        event = SessionEvent(
            session_id="test",
            stream_id="test",
            event_id="stream-123:1234567890123:000001",
            event_type="test",
            event_data={},
            timestamp=time.time()
        )
        assert event.get_numeric_id() == 1234567890123
        
        # Invalid format should return current timestamp
        event_invalid = SessionEvent(
            session_id="test",
            stream_id="test",
            event_id="invalid-format",
            event_type="test",
            event_data={},
            timestamp=time.time()
        )
        numeric_id = event_invalid.get_numeric_id()
        assert isinstance(numeric_id, int)
        assert numeric_id > 0


class TestMemoryEventStore:
    """Test the MemoryEventStore class."""

    @pytest.fixture
    def memory_store(self):
        """Create a memory event store."""
        return MemoryEventStore(default_ttl=3600, max_events_per_session=100)

    @pytest.mark.asyncio
    async def test_store_event(self, memory_store):
        """Test storing an event."""
        message = JSONRPCMessage(method="test", params={"data": "test"})
        event_id = await memory_store.store_event("session-123:stream-456", message)
        
        assert event_id is not None
        assert ":" in event_id
        assert len(memory_store._store) == 1

    @pytest.mark.asyncio
    async def test_get_events(self, memory_store):
        """Test retrieving events."""
        # Store some events
        for i in range(5):
            message = JSONRPCMessage(method=f"test-{i}", params={"index": i})
            await memory_store.store_event("session-123:stream-456", message)
        
        # Retrieve events
        events = await memory_store.get_events("session-123", "stream-456")
        assert len(events) == 5
        assert events[0].event_data["message"]["method"] == "test-0"
        assert events[4].event_data["message"]["method"] == "test-4"

    @pytest.mark.asyncio
    async def test_get_events_with_limit(self, memory_store):
        """Test retrieving events with limit."""
        # Store more events than limit
        for i in range(10):
            message = JSONRPCMessage(method=f"test-{i}", params={"index": i})
            await memory_store.store_event("session-123:stream-456", message)
        
        # Retrieve with limit
        events = await memory_store.get_events("session-123", "stream-456", limit=5)
        assert len(events) == 5

    @pytest.mark.asyncio
    async def test_delete_session(self, memory_store):
        """Test deleting a session."""
        # Store events
        message = JSONRPCMessage(method="test", params={})
        await memory_store.store_event("session-123:stream-456", message)
        
        # Delete session
        success = await memory_store.delete_session("session-123")
        assert success is True
        assert len(memory_store._store) == 0

    @pytest.mark.asyncio
    async def test_replay_events_after(self, memory_store):
        """Test replaying events after a given event ID."""
        # Store events with controlled timing
        event_ids = []
        for i in range(3):
            message = JSONRPCMessage(method=f"test-{i}", params={"index": i})
            event_id = await memory_store.store_event("session-123:stream-456", message)
            event_ids.append(event_id)
            await asyncio.sleep(0.01)  # Ensure different timestamps
        
        # Mock callback
        sent_events = []
        async def mock_callback(event_message: EventMessage):
            sent_events.append(event_message)
        
        # Replay events after the first one
        last_sent_id = await memory_store.replay_events_after(event_ids[0], mock_callback)
        
        assert len(sent_events) == 2  # Should replay events 1 and 2
        assert last_sent_id == event_ids[2]

    @pytest.mark.asyncio
    async def test_serialize_message_json_response(self, memory_store):
        """Test serializing a JSONResponse-like object."""
        # Mock JSONResponse
        mock_response = Mock()
        mock_response.body = json.dumps({"result": "success"}).encode('utf-8')
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        
        serialized = memory_store._serialize_message(mock_response)
        assert serialized["type"] == "json_response"
        assert serialized["body"]["result"] == "success"
        assert serialized["status_code"] == 200

    @pytest.mark.asyncio
    async def test_serialize_message_pydantic(self, memory_store):
        """Test serializing a Pydantic-like model."""
        # Mock Pydantic model
        mock_model = Mock()
        mock_model.model_dump = Mock(return_value={"field": "value"})
        
        serialized = memory_store._serialize_message(mock_model)
        assert serialized == {"field": "value"}

    def test_generate_event_id(self, memory_store):
        """Test generating unique event IDs."""
        event_id1 = memory_store._generate_event_id("stream-123")
        event_id2 = memory_store._generate_event_id("stream-123")
        
        assert event_id1 != event_id2
        assert event_id1.startswith("stream-123:")
        assert event_id2.startswith("stream-123:")
        
        # Check sequence numbers are incrementing
        seq1 = int(event_id1.split(':')[2])
        seq2 = int(event_id2.split(':')[2])
        assert seq2 > seq1


class TestRedisEventStore:
    """Test the RedisEventStore class."""

    @pytest.fixture
    def redis_store(self):
        """Create a Redis event store."""
        return RedisEventStore(
            redis_url="redis://localhost:6379",
            key_prefix="test:mcp:",
            default_ttl=3600,
            fallback_to_memory=True
        )

    @pytest.mark.asyncio
    @patch('fastmcp.server.session_store.REDIS_AVAILABLE', False)
    async def test_connect_no_redis_available(self, redis_store):
        """Test connecting when Redis is not available."""
        success = await redis_store.connect()
        assert success is True  # Should succeed with memory fallback
        assert redis_store._using_fallback is True

    @pytest.mark.asyncio
    @patch('fastmcp.server.session_store.REDIS_AVAILABLE', True)
    async def test_connect_redis_error(self, redis_store):
        """Test connecting when Redis connection fails."""
        # Mock redis connection to fail
        with patch('redis.asyncio.from_url', side_effect=ConnectionError("Connection failed")):
            success = await redis_store.connect()
            assert success is True  # Should succeed with memory fallback
            assert redis_store._using_fallback is True

    @pytest.mark.asyncio
    async def test_store_event_memory_fallback(self, redis_store):
        """Test storing event with memory fallback."""
        redis_store._using_fallback = True
        
        message = JSONRPCMessage(method="test", params={"data": "test"})
        event_id = await redis_store.store_event("session-123:stream-456", message)
        
        assert event_id is not None
        assert len(redis_store._memory_store) == 1

    @pytest.mark.asyncio
    async def test_get_events_memory_fallback(self, redis_store):
        """Test getting events with memory fallback."""
        redis_store._using_fallback = True
        
        # Store event
        message = JSONRPCMessage(method="test", params={"data": "test"})
        await redis_store.store_event("session-123:stream-456", message)
        
        # Get events
        events = await redis_store.get_events("session-123", "stream-456")
        assert len(events) == 1
        assert events[0].event_type == "message"

    @pytest.mark.asyncio
    async def test_delete_session_memory_fallback(self, redis_store):
        """Test deleting session with memory fallback."""
        redis_store._using_fallback = True
        
        # Store event
        message = JSONRPCMessage(method="test", params={"data": "test"})
        await redis_store.store_event("session-123:stream-456", message)
        
        # Delete session
        success = await redis_store.delete_session("session-123")
        assert success is True
        assert len(redis_store._memory_store) == 0

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, redis_store):
        """Test cleaning up expired sessions."""
        redis_store._using_fallback = True
        
        # Create expired event
        event = SessionEvent(
            session_id="expired",
            stream_id="expired:stream",
            event_id="event-1",
            event_type="message",
            event_data={},
            timestamp=time.time() - 7200,  # 2 hours ago
            ttl=3600  # 1 hour TTL
        )
        
        key = redis_store._get_session_key(event.session_id, event.stream_id)
        redis_store._memory_store[key] = [event]
        
        # Clean up
        cleaned = await redis_store.cleanup_expired_sessions()
        assert cleaned == 1
        assert len(redis_store._memory_store) == 0

    @pytest.mark.asyncio
    async def test_get_session_count(self, redis_store):
        """Test getting session count."""
        redis_store._using_fallback = True
        
        # Store events for different sessions
        for i in range(3):
            message = JSONRPCMessage(method="test", params={})
            await redis_store.store_event(f"session-{i}:stream", message)
        
        count = await redis_store.get_session_count()
        assert count == 3

    @pytest.mark.asyncio
    async def test_health_check(self, redis_store):
        """Test health check."""
        redis_store._using_fallback = True
        
        health = await redis_store.health_check()
        assert health["using_fallback"] is True
        assert health["redis_connected"] is False
        assert "session_count" in health
        assert "memory_sessions" in health

    def test_get_session_key(self, redis_store):
        """Test generating session keys."""
        key1 = redis_store._get_session_key("session-123")
        assert key1 == "test:mcp:session-123"
        
        key2 = redis_store._get_session_key("session-123", "stream-456")
        assert key2 == "test:mcp:session-123:stream:stream-456"

    def test_serialize_deserialize_event(self, redis_store):
        """Test serializing and deserializing events."""
        event = SessionEvent(
            session_id="test",
            stream_id="test:stream",
            event_id="event-123",
            event_type="message",
            event_data={"test": "data"},
            timestamp=time.time()
        )
        
        # Serialize
        serialized = redis_store._serialize_event(event)
        assert isinstance(serialized, bytes)
        
        # Deserialize
        deserialized = redis_store._deserialize_event(serialized)
        assert deserialized.session_id == event.session_id
        assert deserialized.event_data == event.event_data


class TestEventStoreFactory:
    """Test the event store factory functions."""

    def test_create_event_store_memory(self):
        """Test creating memory event store."""
        with patch('fastmcp.server.session_store.REDIS_AVAILABLE', False):
            store = create_event_store()
            assert isinstance(store, MemoryEventStore)

    def test_create_event_store_redis(self):
        """Test creating Redis event store."""
        with patch('fastmcp.server.session_store.REDIS_AVAILABLE', True):
            store = create_event_store(redis_url="redis://localhost:6379")
            assert isinstance(store, RedisEventStore)

    @pytest.mark.asyncio
    async def test_get_global_event_store(self):
        """Test getting global event store."""
        # Clear any existing global store
        import fastmcp.server.session_store
        fastmcp.server.session_store._global_event_store = None
        
        with patch('fastmcp.server.session_store.REDIS_AVAILABLE', False):
            store = await get_global_event_store()
            assert isinstance(store, MemoryEventStore)
            
            # Should return same instance
            store2 = await get_global_event_store()
            assert store is store2

    @pytest.mark.asyncio
    async def test_cleanup_global_event_store(self):
        """Test cleaning up global event store."""
        # Create a mock Redis store
        mock_store = Mock(spec=RedisEventStore)
        mock_store.disconnect = AsyncMock()
        
        import fastmcp.server.session_store
        fastmcp.server.session_store._global_event_store = mock_store
        
        await cleanup_global_event_store()
        
        mock_store.disconnect.assert_called_once()
        assert fastmcp.server.session_store._global_event_store is None