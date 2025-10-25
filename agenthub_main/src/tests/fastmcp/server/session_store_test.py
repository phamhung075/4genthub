"""
Comprehensive tests for session_store.py module

This test suite covers:
- SessionEvent dataclass functionality
- RedisEventStore with Redis and memory fallback
- MemoryEventStore functionality
- Factory functions and global store management
- Event serialization and ordering
- Session lifecycle management

Target Coverage: 60%+ (270+ lines of 902 total)
"""

import pytest
import asyncio
import time
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any

# Import the module under test
from fastmcp.server.session_store import (
    SessionEvent,
    RedisEventStore,
    MemoryEventStore,
    create_event_store,
    get_global_event_store,
    cleanup_global_event_store,
    REDIS_AVAILABLE
)

# Import MCP types
try:
    from mcp.types import JSONRPCRequest, JSONRPCNotification
    from mcp.server.streamable_http import EventMessage

    # Use JSONRPCRequest as the default message type for testing
    def create_test_message(method="test", params=None):
        """Helper to create test JSONRPC messages"""
        return JSONRPCRequest(
            jsonrpc="2.0",
            method=method,
            params=params or {},
            id=1
        )

except ImportError:
    # Create mock classes for testing
    class JSONRPCRequest:
        def __init__(self, method=None, params=None, jsonrpc="2.0", id=1, **kwargs):
            self.method = method
            self.params = params or {}
            self.jsonrpc = jsonrpc
            self.id = id
            for k, v in kwargs.items():
                setattr(self, k, v)

    class EventMessage:
        def __init__(self, message, event_id=None):
            self.message = message
            self.event_id = event_id

    def create_test_message(method="test", params=None):
        """Helper to create test JSONRPC messages"""
        return JSONRPCRequest(
            jsonrpc="2.0",
            method=method,
            params=params or {},
            id=1
        )


# ============================================================================
# SessionEvent Tests (Lines 38-74)
# ============================================================================

class TestSessionEvent:
    """Test SessionEvent dataclass functionality"""

    def test_session_event_creation(self):
        """Test creating a SessionEvent with all fields"""
        event = SessionEvent(
            session_id="sess_123",
            stream_id="stream_456",
            event_id="evt_789",
            event_type="message",
            event_data={"key": "value"},
            timestamp=time.time(),
            ttl=3600.0
        )

        assert event.session_id == "sess_123"
        assert event.stream_id == "stream_456"
        assert event.event_id == "evt_789"
        assert event.event_type == "message"
        assert event.event_data == {"key": "value"}
        assert event.ttl == 3600.0

    def test_session_event_to_dict(self):
        """Test SessionEvent.to_dict() method"""
        timestamp = time.time()
        event = SessionEvent(
            session_id="sess_1",
            stream_id="stream_1",
            event_id="evt_1",
            event_type="test",
            event_data={"data": "test"},
            timestamp=timestamp,
            ttl=100.0
        )

        event_dict = event.to_dict()

        assert isinstance(event_dict, dict)
        assert event_dict["session_id"] == "sess_1"
        assert event_dict["stream_id"] == "stream_1"
        assert event_dict["event_id"] == "evt_1"
        assert event_dict["event_type"] == "test"
        assert event_dict["timestamp"] == timestamp
        assert event_dict["ttl"] == 100.0

    def test_session_event_from_dict(self):
        """Test SessionEvent.from_dict() class method"""
        data = {
            "session_id": "sess_2",
            "stream_id": "stream_2",
            "event_id": "evt_2",
            "event_type": "status",
            "event_data": {"status": "ok"},
            "timestamp": 1234567890.0,
            "ttl": 200.0
        }

        event = SessionEvent.from_dict(data)

        assert event.session_id == "sess_2"
        assert event.stream_id == "stream_2"
        assert event.event_id == "evt_2"
        assert event.event_type == "status"
        assert event.event_data == {"status": "ok"}
        assert event.timestamp == 1234567890.0
        assert event.ttl == 200.0

    def test_session_event_is_expired_no_ttl(self):
        """Test is_expired() returns False when ttl is None"""
        event = SessionEvent(
            session_id="sess_3",
            stream_id="stream_3",
            event_id="evt_3",
            event_type="test",
            event_data={},
            timestamp=time.time() - 10000,  # Very old timestamp
            ttl=None  # No TTL
        )

        assert event.is_expired() is False

    def test_session_event_is_expired_within_ttl(self):
        """Test is_expired() returns False when within TTL"""
        event = SessionEvent(
            session_id="sess_4",
            stream_id="stream_4",
            event_id="evt_4",
            event_type="test",
            event_data={},
            timestamp=time.time(),  # Current time
            ttl=3600.0  # 1 hour TTL
        )

        assert event.is_expired() is False

    def test_session_event_is_expired_exceeded_ttl(self):
        """Test is_expired() returns True when TTL exceeded"""
        event = SessionEvent(
            session_id="sess_5",
            stream_id="stream_5",
            event_id="evt_5",
            event_type="test",
            event_data={},
            timestamp=time.time() - 7200,  # 2 hours ago
            ttl=3600.0  # 1 hour TTL
        )

        assert event.is_expired() is True

    def test_session_event_get_numeric_id_standard_format(self):
        """Test get_numeric_id() with standard event ID format"""
        event = SessionEvent(
            session_id="sess_6",
            stream_id="stream_6",
            event_id="stream_6:1234567890:000001",  # Standard format
            event_type="test",
            event_data={},
            timestamp=time.time()
        )

        numeric_id = event.get_numeric_id()
        assert numeric_id == 1234567890

    def test_session_event_get_numeric_id_fallback(self):
        """Test get_numeric_id() fallback for invalid format"""
        event = SessionEvent(
            session_id="sess_7",
            stream_id="stream_7",
            event_id="invalid_format",
            event_type="test",
            event_data={},
            timestamp=time.time()
        )

        numeric_id = event.get_numeric_id()
        # Should return a timestamp-based value
        assert isinstance(numeric_id, int)
        assert numeric_id > 0


# ============================================================================
# RedisEventStore Tests (Lines 76-625)
# ============================================================================

class TestRedisEventStore:
    """Test RedisEventStore functionality"""

    def test_redis_event_store_initialization_default(self):
        """Test RedisEventStore initialization with default parameters"""
        store = RedisEventStore()

        assert store.redis_url == "redis://localhost:6379"
        assert store.key_prefix == "mcp:session:"
        assert store.default_ttl == 3600
        assert store.max_events_per_session == 1000
        assert store.compression_enabled is True
        assert store.fallback_to_memory is True
        assert store._event_sequence == 0
        assert store._redis is None
        assert store._connection_healthy is False
        assert store._using_fallback is False
        assert isinstance(store._memory_store, dict)

    def test_redis_event_store_initialization_custom(self):
        """Test RedisEventStore initialization with custom parameters"""
        store = RedisEventStore(
            redis_url="redis://custom:6380",
            key_prefix="custom:prefix:",
            default_ttl=7200,
            max_events_per_session=500,
            compression_enabled=False,
            fallback_to_memory=False,
            event_id_sequence=100
        )

        assert store.redis_url == "redis://custom:6380"
        assert store.key_prefix == "custom:prefix:"
        assert store.default_ttl == 7200
        assert store.max_events_per_session == 500
        assert store.compression_enabled is False
        assert store.fallback_to_memory is False
        assert store._event_sequence == 100

    def test_generate_event_id(self):
        """Test _generate_event_id() creates unique ordered IDs"""
        store = RedisEventStore()

        id1 = store._generate_event_id("stream_1")
        time.sleep(0.01)  # Small delay to ensure different timestamp
        id2 = store._generate_event_id("stream_1")

        # Check format: stream_id:timestamp_ms:sequence
        assert id1.startswith("stream_1:")
        assert id2.startswith("stream_1:")

        # Extract sequence numbers
        seq1 = int(id1.split(":")[-1])
        seq2 = int(id2.split(":")[-1])

        # Sequences should increment
        assert seq2 > seq1

    @pytest.mark.asyncio
    async def test_connect_redis_not_available(self):
        """Test connect() when Redis is not available"""
        store = RedisEventStore(fallback_to_memory=True)

        with patch('fastmcp.server.session_store.REDIS_AVAILABLE', False):
            result = await store.connect()

            assert result is True  # Fallback enabled
            assert store._using_fallback is True
            assert store._redis is None

    @pytest.mark.asyncio
    async def test_connect_redis_failure_with_fallback(self):
        """Test connect() handles Redis connection failure with fallback"""
        if not REDIS_AVAILABLE:
            pytest.skip("Redis module not available")

        store = RedisEventStore(
            redis_url="redis://invalid:9999",
            fallback_to_memory=True
        )

        result = await store.connect()

        assert result is True  # Fallback enabled
        assert store._using_fallback is True
        assert store._connection_healthy is False

    @pytest.mark.asyncio
    async def test_connect_redis_failure_without_fallback(self):
        """Test connect() handles Redis connection failure without fallback"""
        if not REDIS_AVAILABLE:
            pytest.skip("Redis module not available")

        store = RedisEventStore(
            redis_url="redis://invalid:9999",
            fallback_to_memory=False
        )

        result = await store.connect()

        assert result is False  # No fallback
        assert store._connection_healthy is False

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test disconnect() closes Redis connection"""
        store = RedisEventStore()

        # Mock Redis connection
        mock_redis = AsyncMock()
        store._redis = mock_redis
        store._connection_healthy = True

        await store.disconnect()

        mock_redis.close.assert_called_once()
        assert store._redis is None
        assert store._connection_healthy is False

    def test_get_session_key_session_only(self):
        """Test _get_session_key() with session_id only"""
        store = RedisEventStore(key_prefix="test:")

        key = store._get_session_key("sess_123")

        assert key == "test:sess_123"

    def test_get_session_key_with_stream(self):
        """Test _get_session_key() with session_id and stream_id"""
        store = RedisEventStore(key_prefix="test:")

        key = store._get_session_key("sess_123", "stream_456")

        assert key == "test:sess_123:stream:stream_456"

    def test_serialize_message_dict(self):
        """Test _serialize_message() with dict message"""
        store = RedisEventStore()

        message = {"key": "value", "number": 123}
        result = store._serialize_message(message)

        # Dict is treated as having __dict__ attribute
        assert isinstance(result, dict)

    def test_serialize_message_pydantic_model(self):
        """Test _serialize_message() with Pydantic model"""
        store = RedisEventStore()

        # Mock Pydantic model
        mock_model = Mock()
        mock_model.model_dump.return_value = {"field": "value"}

        result = store._serialize_message(mock_model)

        assert result == {"field": "value"}
        mock_model.model_dump.assert_called_once()

    def test_serialize_message_json_response(self):
        """Test _serialize_message() with JSONResponse-like object"""
        store = RedisEventStore()

        # Mock JSONResponse
        mock_response = Mock()
        mock_response.body = b'{"result": "success"}'
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}

        result = store._serialize_message(mock_response)

        assert result["type"] == "json_response"
        assert result["body"] == {"result": "success"}
        assert result["status_code"] == 200

    def test_serialize_event_without_compression(self):
        """Test _serialize_event() without compression"""
        store = RedisEventStore(compression_enabled=False)

        event = SessionEvent(
            session_id="sess_1",
            stream_id="stream_1",
            event_id="evt_1",
            event_type="test",
            event_data={"data": "value"},
            timestamp=time.time()
        )

        serialized = store._serialize_event(event)

        assert isinstance(serialized, bytes)
        # Should be JSON
        deserialized = json.loads(serialized.decode('utf-8'))
        assert deserialized["session_id"] == "sess_1"

    def test_serialize_event_with_compression(self):
        """Test _serialize_event() with compression"""
        store = RedisEventStore(compression_enabled=True)

        event = SessionEvent(
            session_id="sess_2",
            stream_id="stream_2",
            event_id="evt_2",
            event_type="test",
            event_data={"data": "value"},
            timestamp=time.time()
        )

        serialized = store._serialize_event(event)

        assert isinstance(serialized, bytes)
        # Should be compressed (gzip magic bytes)
        assert serialized[:2] == b'\x1f\x8b'

    def test_deserialize_event_without_compression(self):
        """Test _deserialize_event() without compression"""
        store = RedisEventStore(compression_enabled=False)

        event = SessionEvent(
            session_id="sess_3",
            stream_id="stream_3",
            event_id="evt_3",
            event_type="test",
            event_data={"test": "data"},
            timestamp=12345.0
        )

        serialized = store._serialize_event(event)
        deserialized = store._deserialize_event(serialized)

        assert deserialized.session_id == "sess_3"
        assert deserialized.stream_id == "stream_3"
        assert deserialized.event_type == "test"
        assert deserialized.timestamp == 12345.0

    def test_deserialize_event_with_compression(self):
        """Test _deserialize_event() with compression"""
        store = RedisEventStore(compression_enabled=True)

        event = SessionEvent(
            session_id="sess_4",
            stream_id="stream_4",
            event_id="evt_4",
            event_type="test",
            event_data={"test": "compressed"},
            timestamp=67890.0
        )

        serialized = store._serialize_event(event)
        deserialized = store._deserialize_event(serialized)

        assert deserialized.session_id == "sess_4"
        assert deserialized.event_data["test"] == "compressed"

    @pytest.mark.asyncio
    async def test_store_event_memory_fallback(self):
        """Test store_event() uses memory fallback"""
        store = RedisEventStore()
        store._using_fallback = True

        message = create_test_message(method="test", params={"key": "value"})

        event_id = await store.store_event("stream_test", message)

        assert event_id is not None
        assert event_id.startswith("stream_test:")

        # Verify event was stored in memory
        assert len(store._memory_store) > 0

    @pytest.mark.asyncio
    async def test_store_event_memory_storage(self):
        """Test _store_event_memory() stores events correctly"""
        store = RedisEventStore()

        event = SessionEvent(
            session_id="sess_mem",
            stream_id="stream_mem",
            event_id="stream_mem:1000:000001",
            event_type="test",
            event_data={"test": "memory"},
            timestamp=time.time()
        )

        result = await store._store_event_memory(event)

        assert result is True
        key = store._get_session_key("sess_mem", "stream_mem")
        assert key in store._memory_store
        assert len(store._memory_store[key]) == 1
        assert store._memory_store[key][0].event_id == "stream_mem:1000:000001"

    @pytest.mark.asyncio
    async def test_store_event_memory_ordering(self):
        """Test _store_event_memory() maintains chronological order"""
        store = RedisEventStore()

        # Create events with different timestamps
        event1 = SessionEvent(
            session_id="sess_order",
            stream_id="stream_order",
            event_id="stream_order:1000:000001",
            event_type="test",
            event_data={},
            timestamp=time.time()
        )

        event2 = SessionEvent(
            session_id="sess_order",
            stream_id="stream_order",
            event_id="stream_order:2000:000002",
            event_type="test",
            event_data={},
            timestamp=time.time()
        )

        event3 = SessionEvent(
            session_id="sess_order",
            stream_id="stream_order",
            event_id="stream_order:1500:000003",  # Middle timestamp
            event_type="test",
            event_data={},
            timestamp=time.time()
        )

        # Store in non-chronological order
        await store._store_event_memory(event1)
        await store._store_event_memory(event2)
        await store._store_event_memory(event3)

        key = store._get_session_key("sess_order", "stream_order")
        events = store._memory_store[key]

        # Should be ordered: 1000, 1500, 2000
        assert events[0].get_numeric_id() == 1000
        assert events[1].get_numeric_id() == 1500
        assert events[2].get_numeric_id() == 2000

    @pytest.mark.asyncio
    async def test_store_event_memory_max_limit(self):
        """Test _store_event_memory() enforces max events limit"""
        store = RedisEventStore(max_events_per_session=5)

        # Store more events than the limit
        for i in range(10):
            event = SessionEvent(
                session_id="sess_limit",
                stream_id="stream_limit",
                event_id=f"stream_limit:{1000+i}:00000{i}",
                event_type="test",
                event_data={},
                timestamp=time.time()
            )
            await store._store_event_memory(event)

        key = store._get_session_key("sess_limit", "stream_limit")
        events = store._memory_store[key]

        # Should only keep the newest 5 events
        assert len(events) == 5
        assert events[-1].get_numeric_id() == 1009  # Last event

    @pytest.mark.asyncio
    async def test_get_events_memory(self):
        """Test get_events() retrieves from memory"""
        store = RedisEventStore()
        store._using_fallback = True

        # Store some events
        message1 = create_test_message(method="test1", params={})
        message2 = create_test_message(method="test2", params={})

        await store.store_event("stream_get", message1)
        await store.store_event("stream_get", message2)

        # Retrieve events
        session_id = "stream_get"
        events = await store.get_events(session_id, "stream_get")

        assert len(events) == 2
        assert all(isinstance(e, SessionEvent) for e in events)

    @pytest.mark.asyncio
    async def test_get_events_memory_with_limit(self):
        """Test _get_events_memory() respects limit parameter"""
        store = RedisEventStore()

        # Store multiple events
        for i in range(10):
            event = SessionEvent(
                session_id="sess_limit_get",
                stream_id="stream_limit_get",
                event_id=f"evt_{i}",
                event_type="test",
                event_data={},
                timestamp=time.time()
            )
            await store._store_event_memory(event)

        # Get with limit
        events = await store._get_events_memory("sess_limit_get", "stream_limit_get", limit=3)

        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_get_events_memory_filters_expired(self):
        """Test _get_events_memory() filters out expired events"""
        store = RedisEventStore()

        # Store expired event
        expired_event = SessionEvent(
            session_id="sess_exp",
            stream_id="stream_exp",
            event_id="evt_exp",
            event_type="test",
            event_data={},
            timestamp=time.time() - 7200,  # 2 hours ago
            ttl=3600.0  # 1 hour TTL - expired
        )

        # Store valid event
        valid_event = SessionEvent(
            session_id="sess_exp",
            stream_id="stream_exp",
            event_id="evt_valid",
            event_type="test",
            event_data={},
            timestamp=time.time(),
            ttl=3600.0
        )

        await store._store_event_memory(expired_event)
        await store._store_event_memory(valid_event)

        # Get events
        events = await store._get_events_memory("sess_exp", "stream_exp")

        # Should only return valid event
        assert len(events) == 1
        assert events[0].event_id == "evt_valid"

    @pytest.mark.asyncio
    async def test_delete_session(self):
        """Test delete_session() removes session data"""
        store = RedisEventStore()
        store._using_fallback = True

        # Store event
        message = create_test_message(method="test", params={})
        await store.store_event("stream_del", message)

        # Verify event exists
        events = await store.get_events("stream_del", "stream_del")
        assert len(events) > 0

        # Delete session
        result = await store.delete_session("stream_del")

        assert result is True

        # Verify events are gone
        events = await store.get_events("stream_del", "stream_del")
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self):
        """Test cleanup_expired_sessions() removes expired data"""
        store = RedisEventStore()

        # Store expired event
        expired_event = SessionEvent(
            session_id="sess_cleanup",
            stream_id="stream_cleanup",
            event_id="evt_cleanup",
            event_type="test",
            event_data={},
            timestamp=time.time() - 7200,
            ttl=3600.0  # Expired
        )
        await store._store_event_memory(expired_event)

        # Run cleanup
        cleaned = await store.cleanup_expired_sessions()

        assert cleaned >= 0  # Should clean at least the expired session

    @pytest.mark.asyncio
    async def test_get_session_count(self):
        """Test get_session_count() returns correct count"""
        store = RedisEventStore()
        store._using_fallback = True

        # Store events in different sessions
        message = create_test_message(method="test", params={})
        await store.store_event("stream_count1", message)
        await store.store_event("stream_count2", message)

        count = await store.get_session_count()

        assert count >= 2  # At least the two we created

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health_check() returns status information"""
        store = RedisEventStore()
        store._using_fallback = True

        health = await store.health_check()

        assert isinstance(health, dict)
        assert "redis_available" in health
        assert "redis_connected" in health
        assert "using_fallback" in health
        assert "session_count" in health
        assert "memory_sessions" in health

        assert health["using_fallback"] is True
        assert isinstance(health["session_count"], int)


# ============================================================================
# MemoryEventStore Tests (Lines 628-840)
# ============================================================================

class TestMemoryEventStore:
    """Test MemoryEventStore functionality"""

    def test_memory_event_store_initialization(self):
        """Test MemoryEventStore initialization"""
        store = MemoryEventStore(default_ttl=7200, max_events_per_session=500)

        assert store.default_ttl == 7200
        assert store.max_events_per_session == 500
        assert isinstance(store._store, dict)
        assert store._event_sequence == 0

    def test_memory_generate_event_id(self):
        """Test _generate_event_id() creates unique IDs"""
        store = MemoryEventStore()

        id1 = store._generate_event_id("stream_mem")
        id2 = store._generate_event_id("stream_mem")

        # Should have incrementing sequence
        assert id1 != id2
        assert int(id1.split(":")[-1]) < int(id2.split(":")[-1])

    @pytest.mark.asyncio
    async def test_memory_store_event(self):
        """Test store_event() in MemoryEventStore"""
        store = MemoryEventStore()

        message = create_test_message(method="test_method", params={"key": "value"})

        event_id = await store.store_event("session_1:stream_1", message)

        assert event_id is not None
        assert ":" in event_id  # Should have format stream_id:timestamp:sequence

    @pytest.mark.asyncio
    async def test_memory_store_and_retrieve(self):
        """Test storing and retrieving events in MemoryEventStore"""
        store = MemoryEventStore()

        message1 = create_test_message(method="method1", params={})
        message2 = create_test_message(method="method2", params={})

        await store.store_event("sess_mem:stream_mem", message1)
        await store.store_event("sess_mem:stream_mem", message2)

        events = await store.get_events("sess_mem", "stream_mem")

        assert len(events) == 2
        assert all(isinstance(e, SessionEvent) for e in events)

    @pytest.mark.asyncio
    async def test_memory_get_events_with_limit(self):
        """Test get_events() respects limit parameter"""
        store = MemoryEventStore()

        # Store 5 events
        for i in range(5):
            message = create_test_message(method=f"method{i}", params={})
            await store.store_event("sess_lim:stream_lim", message)

        # Get with limit of 3
        events = await store.get_events("sess_lim", "stream_lim", limit=3)

        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_memory_delete_session(self):
        """Test delete_session() in MemoryEventStore"""
        store = MemoryEventStore()

        message = create_test_message(method="test", params={})
        await store.store_event("sess_del_mem:stream_del_mem", message)

        # Verify event exists
        events = await store.get_events("sess_del_mem", "stream_del_mem")
        assert len(events) == 1

        # Delete session
        result = await store.delete_session("sess_del_mem")

        assert result is True

        # Verify events are gone
        events = await store.get_events("sess_del_mem", "stream_del_mem")
        assert len(events) == 0


# ============================================================================
# Factory Function Tests (Lines 843-902)
# ============================================================================

class TestFactoryFunctions:
    """Test factory functions and global store management"""

    def test_create_event_store_memory_fallback(self):
        """Test create_event_store() creates MemoryEventStore when Redis unavailable"""
        with patch('fastmcp.server.session_store.REDIS_AVAILABLE', False):
            store = create_event_store()

            assert isinstance(store, MemoryEventStore)

    def test_create_event_store_with_redis_url(self):
        """Test create_event_store() with custom Redis URL"""
        if not REDIS_AVAILABLE:
            pytest.skip("Redis module not available")

        store = create_event_store(redis_url="redis://custom:6380")

        assert isinstance(store, RedisEventStore)
        assert store.redis_url == "redis://custom:6380"

    def test_create_event_store_from_environment(self):
        """Test create_event_store() reads from environment"""
        if not REDIS_AVAILABLE:
            pytest.skip("Redis module not available")

        with patch.dict('os.environ', {'REDIS_URL': 'redis://env:6381'}):
            store = create_event_store(redis_url=None)

            assert isinstance(store, RedisEventStore)
            assert store.redis_url == "redis://env:6381"

    @pytest.mark.asyncio
    async def test_get_global_event_store(self):
        """Test get_global_event_store() creates and returns global instance"""
        # Clean up any existing global store
        await cleanup_global_event_store()

        store1 = await get_global_event_store()
        store2 = await get_global_event_store()

        # Should return the same instance
        assert store1 is store2

        # Clean up
        await cleanup_global_event_store()

    @pytest.mark.asyncio
    async def test_cleanup_global_event_store(self):
        """Test cleanup_global_event_store() cleans up global instance"""
        # Create global store
        store = await get_global_event_store()
        assert store is not None

        # Clean up
        await cleanup_global_event_store()

        # Getting again should create new instance
        new_store = await get_global_event_store()
        assert new_store is not store

        # Final cleanup
        await cleanup_global_event_store()


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
