"""
Tests for Session Store

This module tests the Redis-based EventStore implementation including:
- Redis EventStore functionality with connection management
- Session event storage and retrieval
- Event serialization and deserialization
- Memory fallback when Redis is unavailable
- Last-Event-ID support for session recovery
- Event cleanup and session management
- Health checking and statistics
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4
from collections import namedtuple

from fastmcp.server.session_store import (
    RedisEventStore,
    MemoryEventStore, 
    SessionEvent,
    create_event_store,
    get_global_event_store,
    cleanup_global_event_store
)

# Mock Redis for testing
MockRedis = namedtuple('MockRedis', ['from_url', 'ConnectionPool'])
MockConnectionPool = namedtuple('MockConnectionPool', ['from_url'])


class TestSessionEvent:
    """Test suite for SessionEvent data structure"""
    
    def test_session_event_creation(self):
        """Test SessionEvent creation with all fields"""
        timestamp = time.time()
        event_data = {"message": "test", "user": "test_user"}
        
        event = SessionEvent(
            session_id="session-123",
            stream_id="stream-456",
            event_id="event-789",
            event_type="message",
            event_data=event_data,
            timestamp=timestamp,
            ttl=3600
        )
        
        assert event.session_id == "session-123"
        assert event.stream_id == "stream-456"
        assert event.event_id == "event-789"
        assert event.event_type == "message"
        assert event.event_data == event_data
        assert event.timestamp == timestamp
        assert event.ttl == 3600
    
    def test_session_event_to_dict(self):
        """Test SessionEvent serialization to dictionary"""
        timestamp = time.time()
        event_data = {"key": "value"}
        
        event = SessionEvent(
            session_id="session-123",
            stream_id="stream-456",
            event_id="event-789",
            event_type="message",
            event_data=event_data,
            timestamp=timestamp,
            ttl=3600
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["session_id"] == "session-123"
        assert event_dict["stream_id"] == "stream-456" 
        assert event_dict["event_id"] == "event-789"
        assert event_dict["event_type"] == "message"
        assert event_dict["event_data"] == event_data
        assert event_dict["timestamp"] == timestamp
        assert event_dict["ttl"] == 3600
    
    def test_session_event_from_dict(self):
        """Test SessionEvent deserialization from dictionary"""
        timestamp = time.time()
        event_data = {"key": "value"}
        
        event_dict = {
            "session_id": "session-123",
            "stream_id": "stream-456",
            "event_id": "event-789",
            "event_type": "message",
            "event_data": event_data,
            "timestamp": timestamp,
            "ttl": 3600
        }
        
        event = SessionEvent.from_dict(event_dict)
        
        assert event.session_id == "session-123"
        assert event.stream_id == "stream-456"
        assert event.event_id == "event-789"
        assert event.event_type == "message"
        assert event.event_data == event_data
        assert event.timestamp == timestamp
        assert event.ttl == 3600
    
    def test_session_event_is_expired(self):
        """Test SessionEvent expiration checking"""
        current_time = time.time()
        
        # Not expired event
        event_active = SessionEvent(
            session_id="session-123",
            stream_id="stream-456",
            event_id="event-789",
            event_type="message",
            event_data={},
            timestamp=current_time,
            ttl=3600  # 1 hour TTL
        )
        
        assert not event_active.is_expired()
        
        # Expired event
        event_expired = SessionEvent(
            session_id="session-123",
            stream_id="stream-456",
            event_id="event-789",
            event_type="message",
            event_data={},
            timestamp=current_time - 7200,  # 2 hours ago
            ttl=3600  # 1 hour TTL
        )
        
        assert event_expired.is_expired()
        
        # Event without TTL (never expires)
        event_no_ttl = SessionEvent(
            session_id="session-123",
            stream_id="stream-456",
            event_id="event-789",
            event_type="message",
            event_data={},
            timestamp=current_time - 7200,
            ttl=None
        )
        
        assert not event_no_ttl.is_expired()
    
    def test_session_event_get_numeric_id(self):
        """Test SessionEvent numeric ID extraction for ordering"""
        # Test standard format: stream_id:timestamp:sequence
        event1 = SessionEvent(
            session_id="session-123",
            stream_id="stream-456",
            event_id="stream-456:1234567890123:000001",
            event_type="message",
            event_data={},
            timestamp=time.time()
        )
        
        assert event1.get_numeric_id() == 1234567890123
        
        # Test invalid format fallback
        event2 = SessionEvent(
            session_id="session-123",
            stream_id="stream-456",
            event_id="invalid-format",
            event_type="message",
            event_data={},
            timestamp=time.time()
        )
        
        numeric_id = event2.get_numeric_id()
        assert isinstance(numeric_id, int)
        assert numeric_id > 0


class TestRedisEventStore:
    """Test suite for RedisEventStore"""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client"""
        client = AsyncMock()
        client.ping = AsyncMock(return_value=True)
        client.pipeline = Mock()
        client.zadd = AsyncMock()
        client.zremrangebyrank = AsyncMock()
        client.expire = AsyncMock()
        client.zrange = AsyncMock()
        client.keys = AsyncMock()
        client.delete = AsyncMock()
        client.info = AsyncMock(return_value={
            "connected_clients": 1,
            "used_memory_human": "1M",
            "uptime_in_seconds": 3600
        })
        client.close = AsyncMock()
        return client
    
    @pytest.fixture
    def event_store(self):
        """Create RedisEventStore instance"""
        return RedisEventStore(
            redis_url="redis://localhost:6379",
            default_ttl=3600,
            max_events_per_session=100
        )
    
    def test_redis_event_store_initialization(self, event_store):
        """Test RedisEventStore initialization"""
        assert event_store.redis_url == "redis://localhost:6379"
        assert event_store.default_ttl == 3600
        assert event_store.max_events_per_session == 100
        assert event_store.fallback_to_memory is True
        assert event_store._connection_healthy is False
        assert event_store._using_fallback is False
        assert isinstance(event_store._memory_store, dict)
    
    def test_redis_event_store_custom_config(self):
        """Test RedisEventStore with custom configuration"""
        store = RedisEventStore(
            redis_url="redis://custom:6380",
            key_prefix="custom:session:",
            default_ttl=7200,
            max_events_per_session=500,
            compression_enabled=False,
            fallback_to_memory=False
        )
        
        assert store.redis_url == "redis://custom:6380"
        assert store.key_prefix == "custom:session:"
        assert store.default_ttl == 7200
        assert store.max_events_per_session == 500
        assert store.compression_enabled is False
        assert store.fallback_to_memory is False
    
    def test_generate_event_id(self, event_store):
        """Test event ID generation"""
        stream_id = "test-stream"
        
        event_id1 = event_store._generate_event_id(stream_id)
        event_id2 = event_store._generate_event_id(stream_id)
        
        # Check format: stream_id:timestamp_ms:sequence
        assert event_id1.startswith(f"{stream_id}:")
        assert event_id2.startswith(f"{stream_id}:")
        assert event_id1 != event_id2  # Should be unique
        
        # Check sequence increases
        seq1 = int(event_id1.split(':')[2])
        seq2 = int(event_id2.split(':')[2])
        assert seq2 == seq1 + 1
    
    @pytest.mark.asyncio
    async def test_connect_success(self, event_store, mock_redis_client):
        """Test successful Redis connection"""
        with patch('fastmcp.server.session_store.redis') as mock_redis:
            mock_redis.from_url.return_value = mock_redis_client
            
            result = await event_store.connect()
            
            assert result is True
            assert event_store._connection_healthy is True
            assert event_store._using_fallback is False
            mock_redis_client.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_failure_with_fallback(self, event_store):
        """Test Redis connection failure with memory fallback"""
        with patch('fastmcp.server.session_store.redis') as mock_redis:
            mock_redis.from_url.side_effect = ConnectionError("Redis not available")
            
            result = await event_store.connect()
            
            assert result is True  # Succeeds due to fallback
            assert event_store._connection_healthy is False
            assert event_store._using_fallback is True
    
    @pytest.mark.asyncio
    async def test_connect_failure_no_fallback(self):
        """Test Redis connection failure without fallback"""
        event_store = RedisEventStore(
            redis_url="redis://localhost:6379",
            fallback_to_memory=False
        )
        
        with patch('fastmcp.server.session_store.redis') as mock_redis:
            mock_redis.from_url.side_effect = ConnectionError("Redis not available")
            
            result = await event_store.connect()
            
            assert result is False
            assert event_store._connection_healthy is False
            assert event_store._using_fallback is False
    
    @pytest.mark.asyncio 
    async def test_connect_redis_not_available(self):
        """Test connection when Redis module not available"""
        event_store = RedisEventStore(redis_url="redis://localhost:6379")
        
        with patch('fastmcp.server.session_store.REDIS_AVAILABLE', False):
            result = await event_store.connect()
            
            assert result is True  # Succeeds due to fallback
            assert event_store._connection_healthy is False
            assert event_store._using_fallback is True
    
    @pytest.mark.asyncio
    async def test_disconnect(self, event_store, mock_redis_client):
        """Test Redis disconnection"""
        event_store._redis = mock_redis_client
        
        await event_store.disconnect()
        
        mock_redis_client.close.assert_called_once()
        assert event_store._redis is None
        assert event_store._connection_healthy is False
    
    def test_get_session_key(self, event_store):
        """Test session key generation"""
        session_id = "session-123"
        stream_id = "stream-456"
        
        # Without stream ID
        key1 = event_store._get_session_key(session_id)
        assert key1 == "mcp:session:session-123"
        
        # With stream ID
        key2 = event_store._get_session_key(session_id, stream_id)
        assert key2 == "mcp:session:session-123:stream:stream-456"
    
    def test_serialize_message_json_response(self, event_store):
        """Test message serialization for JSON response objects"""
        # Mock JSONResponse object
        mock_response = Mock()
        mock_response.body = b'{"message": "test", "status": "success"}'
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        
        result = event_store._serialize_message(mock_response)
        
        assert result["type"] == "json_response"
        assert result["body"] == {"message": "test", "status": "success"}
        assert result["status_code"] == 200
        assert result["headers"]["Content-Type"] == "application/json"
    
    def test_serialize_message_pydantic_model(self, event_store):
        """Test message serialization for Pydantic models"""
        # Mock Pydantic model
        mock_model = Mock()
        mock_model.model_dump.return_value = {"id": "123", "name": "test"}
        
        result = event_store._serialize_message(mock_model)
        
        assert result == {"id": "123", "name": "test"}
        mock_model.model_dump.assert_called_once()
    
    def test_serialize_message_dict_object(self, event_store):
        """Test message serialization for dict-like objects"""
        # Real object with __dict__ instead of Mock
        class TestObj:
            def __init__(self):
                self.name = "test"
                self.value = 42
                self.json_serializable = "yes"
                # Use a lambda instead of Mock to create a non-serializable object
                self.non_serializable = lambda x: x
        
        obj = TestObj()
        result = event_store._serialize_message(obj)
        
        # Should contain the serializable fields
        assert "name" in result
        assert "value" in result
        assert "json_serializable" in result
        assert "non_serializable" in result
        assert result["name"] == "test"
        assert result["value"] == 42
        assert result["json_serializable"] == "yes"
        # non_serializable should be converted to string
        assert isinstance(result["non_serializable"], str)
    
    def test_serialize_message_fallback(self, event_store):
        """Test message serialization fallback"""
        # Object that can't be serialized
        class UnserializableObj:
            def __init__(self):
                self.data = "test"
        
        obj = UnserializableObj()
        
        result = event_store._serialize_message(obj)
        
        assert result["type"] == "UnserializableObj"
        assert "message" in result
    
    def test_serialize_event_with_compression(self, event_store):
        """Test event serialization with compression enabled"""
        event = SessionEvent(
            session_id="session-123",
            stream_id="stream-456", 
            event_id="event-789",
            event_type="message",
            event_data={"key": "value"},
            timestamp=time.time()
        )
        
        serialized = event_store._serialize_event(event)
        
        assert isinstance(serialized, bytes)
        assert len(serialized) > 0
    
    def test_serialize_event_without_compression(self):
        """Test event serialization without compression"""
        event_store = RedisEventStore(compression_enabled=False)
        
        event = SessionEvent(
            session_id="session-123",
            stream_id="stream-456",
            event_id="event-789", 
            event_type="message",
            event_data={"key": "value"},
            timestamp=time.time()
        )
        
        serialized = event_store._serialize_event(event)
        
        assert isinstance(serialized, bytes)
        # Should be valid JSON
        event_dict = json.loads(serialized.decode('utf-8'))
        assert event_dict["session_id"] == "session-123"
    
    def test_deserialize_event_with_compression(self, event_store):
        """Test event deserialization with compression"""
        event = SessionEvent(
            session_id="session-123",
            stream_id="stream-456",
            event_id="event-789",
            event_type="message", 
            event_data={"key": "value"},
            timestamp=time.time()
        )
        
        # Serialize then deserialize
        serialized = event_store._serialize_event(event)
        deserialized = event_store._deserialize_event(serialized)
        
        assert deserialized is not None
        assert deserialized.session_id == event.session_id
        assert deserialized.stream_id == event.stream_id
        assert deserialized.event_id == event.event_id
        assert deserialized.event_type == event.event_type
        assert deserialized.event_data == event.event_data
    
    def test_deserialize_event_without_compression(self):
        """Test event deserialization without compression"""
        event_store = RedisEventStore(compression_enabled=False)
        
        event = SessionEvent(
            session_id="session-123",
            stream_id="stream-456",
            event_id="event-789",
            event_type="message",
            event_data={"key": "value"},
            timestamp=time.time()
        )
        
        # Serialize then deserialize
        serialized = event_store._serialize_event(event)
        deserialized = event_store._deserialize_event(serialized)
        
        assert deserialized is not None
        assert deserialized.session_id == event.session_id
    
    def test_deserialize_event_corrupted(self, event_store):
        """Test event deserialization with corrupted data"""
        corrupted_data = b"corrupted_data_not_json_or_pickle"
        
        result = event_store._deserialize_event(corrupted_data)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_store_event_redis_success(self, event_store, mock_redis_client):
        """Test successful event storage in Redis"""
        # Setup Redis connection
        event_store._redis = mock_redis_client
        event_store._connection_healthy = True
        
        # Setup pipeline mock
        mock_pipeline = Mock()
        mock_pipeline.zadd = Mock()
        mock_pipeline.zremrangebyrank = Mock()
        mock_pipeline.expire = Mock()
        mock_pipeline.execute = AsyncMock()
        mock_redis_client.pipeline.return_value = mock_pipeline
        
        # Create mock JSONRPC message
        from mcp.types import JSONRPCNotification
        message = JSONRPCNotification(jsonrpc="2.0", method="test", params={"data": "test"})
        
        # Store event
        event_id = await event_store.store_event("test-stream", message)
        
        assert event_id is not None
        assert event_id.startswith("test-stream:")
        mock_pipeline.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_event_redis_failure_fallback(self, event_store, mock_redis_client):
        """Test event storage with Redis failure and memory fallback"""
        # Setup Redis connection that fails
        event_store._redis = mock_redis_client
        event_store._connection_healthy = True
        
        # Make pipeline fail
        mock_redis_client.pipeline.side_effect = Exception("Redis error")
        
        # Create mock message
        from mcp.types import JSONRPCNotification
        message = JSONRPCNotification(jsonrpc="2.0", method="test", params={"data": "test"})
        
        # Store event
        event_id = await event_store.store_event("test-stream", message)
        
        assert event_id is not None
        assert event_id.startswith("test-stream:")
        # Should have fallen back to memory storage
        assert len(event_store._memory_store) > 0
    
    @pytest.mark.asyncio
    async def test_store_event_memory_fallback(self, event_store):
        """Test event storage in memory fallback"""
        # Set to use memory fallback
        event_store._using_fallback = True
        
        # Create mock message
        from mcp.types import JSONRPCNotification
        message = JSONRPCNotification(jsonrpc="2.0", method="test", params={"data": "test"})
        
        # Store event
        event_id = await event_store.store_event("test-stream", message)
        
        assert event_id is not None
        assert event_id.startswith("test-stream:")
        assert len(event_store._memory_store) == 1
    
    @pytest.mark.asyncio
    async def test_get_events_redis(self, event_store, mock_redis_client):
        """Test getting events from Redis"""
        # Setup Redis connection
        event_store._redis = mock_redis_client
        event_store._connection_healthy = True
        event_store._using_fallback = False
        
        # Create mock serialized event
        event = SessionEvent(
            session_id="session-123",
            stream_id="stream-456",
            event_id="event-789",
            event_type="message",
            event_data={"key": "value"},
            timestamp=time.time()
        )
        serialized_event = event_store._serialize_event(event)
        
        # Mock Redis response
        mock_redis_client.zrange.return_value = [serialized_event]
        
        # Get events
        events = await event_store.get_events("session-123", "stream-456")
        
        assert len(events) == 1
        assert events[0].session_id == "session-123"
        assert events[0].stream_id == "stream-456"
        mock_redis_client.zrange.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_events_memory(self, event_store):
        """Test getting events from memory"""
        # Set to use memory
        event_store._using_fallback = True
        
        # Store an event in memory first
        from mcp.types import JSONRPCNotification
        message = JSONRPCNotification(jsonrpc="2.0", method="test", params={"data": "test"})
        await event_store.store_event("test-stream", message)
        
        # Get events
        events = await event_store.get_events("test-stream", "test-stream")
        
        assert len(events) == 1
        assert events[0].session_id == "test-stream"
    
    @pytest.mark.asyncio
    async def test_delete_session_redis(self, event_store, mock_redis_client):
        """Test session deletion from Redis"""
        # Setup Redis connection
        event_store._redis = mock_redis_client
        event_store._connection_healthy = True
        event_store._using_fallback = False
        
        # Mock Redis keys response
        mock_redis_client.keys.return_value = [
            "mcp:session:session-123:stream:1",
            "mcp:session:session-123:stream:2"
        ]
        
        # Delete session
        result = await event_store.delete_session("session-123")
        
        assert result is True
        mock_redis_client.keys.assert_called_once_with("mcp:session:session-123*")
        mock_redis_client.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_session_memory(self, event_store):
        """Test session deletion from memory"""
        # Add some data to memory store
        event_store._memory_store["mcp:session:session-123:stream:1"] = []
        event_store._memory_store["mcp:session:session-123:stream:2"] = []
        event_store._memory_store["mcp:session:other-session"] = []
        
        # Delete session
        result = await event_store.delete_session("session-123")
        
        assert result is True
        assert "mcp:session:session-123:stream:1" not in event_store._memory_store
        assert "mcp:session:session-123:stream:2" not in event_store._memory_store
        assert "mcp:session:other-session" in event_store._memory_store  # Should remain
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, event_store):
        """Test cleanup of expired sessions"""
        # Add expired events to memory store
        current_time = time.time()
        
        expired_event = SessionEvent(
            session_id="session-expired",
            stream_id="stream-1",
            event_id="event-1",
            event_type="message",
            event_data={},
            timestamp=current_time - 7200,  # 2 hours ago
            ttl=3600  # 1 hour TTL
        )
        
        active_event = SessionEvent(
            session_id="session-active",
            stream_id="stream-2", 
            event_id="event-2",
            event_type="message",
            event_data={},
            timestamp=current_time,
            ttl=3600
        )
        
        event_store._memory_store["session-expired"] = [expired_event]
        event_store._memory_store["session-active"] = [active_event]
        
        # Cleanup
        cleaned_count = await event_store.cleanup_expired_sessions()
        
        assert cleaned_count == 1
        assert "session-expired" not in event_store._memory_store
        assert "session-active" in event_store._memory_store
    
    @pytest.mark.asyncio
    async def test_get_session_count(self, event_store, mock_redis_client):
        """Test getting session count"""
        # Setup Redis connection
        event_store._redis = mock_redis_client
        event_store._connection_healthy = True
        event_store._using_fallback = False
        
        # Mock Redis keys
        mock_redis_client.keys.return_value = ["key1", "key2", "key3"]
        
        # Add memory sessions
        event_store._memory_store["mem1"] = []
        event_store._memory_store["mem2"] = []
        
        count = await event_store.get_session_count()
        
        assert count == 5  # 3 from Redis + 2 from memory
    
    @pytest.mark.asyncio
    async def test_health_check(self, event_store, mock_redis_client):
        """Test health check functionality"""
        # Setup Redis connection
        event_store._redis = mock_redis_client
        event_store._connection_healthy = True
        event_store._using_fallback = False
        
        # Mock session count
        mock_redis_client.keys.return_value = ["key1", "key2"]
        event_store._memory_store["mem1"] = []
        
        health = await event_store.health_check()
        
        assert isinstance(health, dict)
        assert "redis_available" in health
        assert "redis_connected" in health
        assert "using_fallback" in health
        assert "session_count" in health
        assert "memory_sessions" in health
        assert health["session_count"] == 3  # 2 Redis + 1 memory


class TestMemoryEventStore:
    """Test suite for MemoryEventStore"""
    
    @pytest.fixture
    def event_store(self):
        """Create MemoryEventStore instance"""
        return MemoryEventStore(default_ttl=3600, max_events_per_session=100)
    
    def test_memory_event_store_initialization(self, event_store):
        """Test MemoryEventStore initialization"""
        assert event_store.default_ttl == 3600
        assert event_store.max_events_per_session == 100
        assert isinstance(event_store._store, dict)
        assert len(event_store._store) == 0
    
    @pytest.mark.asyncio
    async def test_store_event_memory(self, event_store):
        """Test event storage in memory"""
        from mcp.types import JSONRPCNotification
        message = JSONRPCNotification(jsonrpc="2.0", method="test", params={"data": "test"})
        
        # Store event
        event_id = await event_store.store_event("test-stream", message)
        
        assert event_id is not None
        assert event_id.startswith("test-stream:")
        assert len(event_store._store) == 1
    
    @pytest.mark.asyncio
    async def test_get_events_memory(self, event_store):
        """Test getting events from memory"""
        from mcp.types import JSONRPCNotification
        message = JSONRPCNotification(jsonrpc="2.0", method="test", params={"data": "test"})
        
        # Store event
        await event_store.store_event("test-stream", message)
        
        # Get events
        events = await event_store.get_events("test-stream", "test-stream")
        
        assert len(events) == 1
        assert events[0].session_id == "test-stream"
    
    @pytest.mark.asyncio
    async def test_delete_session_memory(self, event_store):
        """Test session deletion from memory"""
        from mcp.types import JSONRPCNotification
        message = JSONRPCNotification(jsonrpc="2.0", method="test", params={"data": "test"})
        
        # Store events
        await event_store.store_event("session-123", message)
        await event_store.store_event("session-456", message)
        
        assert len(event_store._store) == 2
        
        # Delete one session
        result = await event_store.delete_session("session-123")
        
        assert result is True
        assert len(event_store._store) == 1
        
        # Verify correct session was deleted
        remaining_keys = list(event_store._store.keys())
        assert all("session-123" not in key for key in remaining_keys)
        assert any("session-456" in key for key in remaining_keys)


class TestEventStoreFactory:
    """Test suite for event store factory functions"""
    
    def test_create_event_store_with_redis_url(self):
        """Test creating event store with Redis URL"""
        with patch('fastmcp.server.session_store.REDIS_AVAILABLE', True):
            store = create_event_store(redis_url="redis://localhost:6379")
            
            assert isinstance(store, RedisEventStore)
            assert store.redis_url == "redis://localhost:6379"
    
    def test_create_event_store_without_redis(self):
        """Test creating event store without Redis"""
        with patch('fastmcp.server.session_store.REDIS_AVAILABLE', False):
            store = create_event_store(redis_url="redis://localhost:6379")
            
            assert isinstance(store, MemoryEventStore)
    
    def test_create_event_store_environment_url(self):
        """Test creating event store with URL from environment"""
        with patch('fastmcp.server.session_store.REDIS_AVAILABLE', True):
            with patch('os.getenv', return_value="redis://env:6379"):
                store = create_event_store()
                
                assert isinstance(store, RedisEventStore)
                assert store.redis_url == "redis://env:6379"
    
    @pytest.mark.asyncio
    async def test_get_global_event_store(self):
        """Test getting global event store"""
        # Clean up any existing global store
        await cleanup_global_event_store()
        
        with patch('fastmcp.server.session_store.REDIS_AVAILABLE', False):
            store = await get_global_event_store()
            
            assert store is not None
            assert isinstance(store, MemoryEventStore)
            
            # Should return same instance on subsequent calls
            store2 = await get_global_event_store()
            assert store is store2
    
    @pytest.mark.asyncio
    async def test_cleanup_global_event_store(self):
        """Test cleanup of global event store"""
        # Create global store first
        with patch('fastmcp.server.session_store.REDIS_AVAILABLE', False):
            await get_global_event_store()
        
        # Cleanup
        await cleanup_global_event_store()
        
        # Verify cleanup occurred (this is mainly for Redis store)
        # For memory store, cleanup just sets the global to None
        # We can't directly test the global variable, but we can test 
        # that a new store is created on next call
        with patch('fastmcp.server.session_store.REDIS_AVAILABLE', False):
            new_store = await get_global_event_store()
            assert new_store is not None


class TestEventStoreIntegration:
    """Integration tests for event store functionality"""
    
    @pytest.fixture
    def memory_store(self):
        """Create memory event store for integration tests"""
        return MemoryEventStore(default_ttl=3600, max_events_per_session=10)
    
    @pytest.mark.asyncio
    async def test_full_session_lifecycle(self, memory_store):
        """Test complete session lifecycle"""
        from mcp.types import JSONRPCNotification
        
        session_id = "integration-session"
        stream_id = "integration-session:integration-stream"
        
        # Store multiple events
        messages = [
            JSONRPCNotification(jsonrpc="2.0", method="login", params={"user": "test"}),
            JSONRPCNotification(jsonrpc="2.0", method="action", params={"action": "click"}),
            JSONRPCNotification(jsonrpc="2.0", method="logout", params={"user": "test"})
        ]
        
        event_ids = []
        for message in messages:
            event_id = await memory_store.store_event(stream_id, message)
            event_ids.append(event_id)
        
        # Retrieve events
        events = await memory_store.get_events(session_id, "integration-stream", limit=10)
        
        assert len(events) == 3
        assert events[0].event_data["message"]["method"] == "login"
        assert events[1].event_data["message"]["method"] == "action"
        assert events[2].event_data["message"]["method"] == "logout"
        
        # Test event ordering
        for i in range(len(events) - 1):
            assert events[i].get_numeric_id() <= events[i + 1].get_numeric_id()
        
        # Delete session
        result = await memory_store.delete_session(session_id)
        assert result is True
        
        # Verify deletion
        events_after_delete = await memory_store.get_events(session_id, stream_id)
        assert len(events_after_delete) == 0
    
    @pytest.mark.asyncio
    async def test_event_expiration_handling(self, memory_store):
        """Test event expiration and cleanup"""
        from mcp.types import JSONRPCNotification
        
        # Create events with different expiration times
        current_time = time.time()
        
        # Store event that will expire
        event_id1 = await memory_store.store_event(
            "expire-stream", 
            JSONRPCNotification(jsonrpc="2.0", method="expire", params={})
        )
        
        # Manually set expiration in the past
        key = "mcp:session:expire-stream:stream:expire-stream"
        if key in memory_store._store:
            memory_store._store[key][0].timestamp = current_time - 7200
            memory_store._store[key][0].ttl = 3600  # 1 hour TTL
        
        # Store event that won't expire
        event_id2 = await memory_store.store_event(
            "active-stream",
            JSONRPCNotification(jsonrpc="2.0", method="active", params={})
        )
        
        # Get events (should filter expired ones)
        expired_events = await memory_store.get_events("expire-stream", "expire-stream")
        active_events = await memory_store.get_events("active-stream", "active-stream")
        
        assert len(expired_events) == 0  # Expired event filtered out
        assert len(active_events) == 1   # Active event remains
    
    @pytest.mark.asyncio
    async def test_max_events_per_session_limit(self, memory_store):
        """Test max events per session limit enforcement"""
        from mcp.types import JSONRPCNotification
        
        session_stream = "limit-test-stream"
        
        # Store more events than the limit (10)
        for i in range(15):
            await memory_store.store_event(
                session_stream,
                JSONRPCNotification(jsonrpc="2.0", method="event", params={"index": i})
            )
        
        # Should only keep the most recent 10 events
        events = await memory_store.get_events("limit-test-stream", session_stream)
        
        assert len(events) == 10
        
        # Verify we kept the most recent events (5-14)
        event_indices = [event.event_data["message"]["params"]["index"] for event in events]
        assert min(event_indices) == 5
        assert max(event_indices) == 14
    
    @pytest.mark.asyncio
    async def test_concurrent_event_storage(self, memory_store):
        """Test concurrent event storage"""
        from mcp.types import JSONRPCNotification
        
        # Create multiple concurrent tasks
        async def store_events(stream_prefix, count):
            event_ids = []
            for i in range(count):
                event_id = await memory_store.store_event(
                    f"{stream_prefix}-{i}",
                    JSONRPCNotification(jsonrpc="2.0", method="concurrent", params={"stream": stream_prefix, "index": i})
                )
                event_ids.append(event_id)
            return event_ids
        
        # Run concurrent tasks
        tasks = [
            store_events("stream-a", 5),
            store_events("stream-b", 5),
            store_events("stream-c", 5)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all events were stored
        total_events = sum(len(result) for result in results)
        assert total_events == 15
        
        # Verify all event IDs are unique
        all_event_ids = [event_id for result in results for event_id in result]
        assert len(all_event_ids) == len(set(all_event_ids))
        
        # Verify events can be retrieved
        total_stored = 0
        for stream_prefix in ["stream-a", "stream-b", "stream-c"]:
            for i in range(5):
                events = await memory_store.get_events(f"{stream_prefix}-{i}", f"{stream_prefix}-{i}")
                total_stored += len(events)
        
        assert total_stored == 15