"""Test event bus infrastructure"""

import pytest
import asyncio
from datetime import datetime
from typing import List, Optional
from unittest.mock import Mock, AsyncMock, patch
import uuid

from fastmcp.shared.infrastructure.messaging.event_bus import (
    EventBus,
    DomainEvent,
    EventMetadata,
    EventPriority,
    EventHandler,
    get_event_bus,
    set_event_bus
)


# Test events
class TestEvent(DomainEvent):
    """Test event for testing"""
    def __init__(self, data: str):
        super().__init__()
        self.data = data


class AnotherTestEvent(DomainEvent):
    """Another test event"""
    def __init__(self, value: int):
        super().__init__()
        self.value = value


class TestEventBus:
    """Test event bus functionality"""

    @pytest.fixture
    async def event_bus(self):
        """Create event bus instance"""
        bus = EventBus(max_queue_size=100, worker_count=2)
        await bus.start()
        yield bus
        await bus.stop()

    @pytest.mark.asyncio
    async def test_event_bus_initialization(self):
        """Test event bus initialization"""
        bus = EventBus(
            max_queue_size=50,
            enable_dead_letter_queue=True,
            worker_count=3
        )
        
        assert bus.max_queue_size == 50
        assert bus.enable_dead_letter_queue is True
        assert bus.worker_count == 3
        assert not bus._is_running
        assert len(bus._workers) == 0

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping event bus"""
        bus = EventBus(worker_count=2)
        
        # Start
        await bus.start()
        assert bus._is_running
        assert len(bus._workers) == 2
        
        # Start again (should be idempotent)
        await bus.start()
        assert len(bus._workers) == 2
        
        # Stop
        await bus.stop()
        assert not bus._is_running
        assert len(bus._workers) == 0

    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe(self, event_bus):
        """Test event subscription and unsubscription"""
        handler = Mock()
        
        # Subscribe
        sub_id = event_bus.subscribe(TestEvent, handler)
        assert sub_id.startswith("TestEvent_")
        assert TestEvent in event_bus._handlers
        assert len(event_bus._handlers[TestEvent]) == 1
        
        # Unsubscribe
        removed = event_bus.unsubscribe(TestEvent, handler)
        assert removed
        assert TestEvent not in event_bus._handlers
        
        # Unsubscribe non-existent
        removed = event_bus.unsubscribe(TestEvent, handler)
        assert not removed

    @pytest.mark.asyncio
    async def test_subscribe_with_priority(self, event_bus):
        """Test handler priority ordering"""
        handler1 = Mock()
        handler2 = Mock()
        handler3 = Mock()
        
        event_bus.subscribe(TestEvent, handler2, priority=5)
        event_bus.subscribe(TestEvent, handler1, priority=10)
        event_bus.subscribe(TestEvent, handler3, priority=1)
        
        handlers = event_bus.get_handlers_for_event(TestEvent)
        assert handlers[0].handler == handler1  # Highest priority
        assert handlers[1].handler == handler2
        assert handlers[2].handler == handler3  # Lowest priority

    @pytest.mark.asyncio
    async def test_subscribe_all(self, event_bus):
        """Test global event subscription"""
        global_handler = Mock()
        
        sub_id = event_bus.subscribe_all(global_handler)
        assert sub_id.startswith("global_")
        assert len(event_bus._global_handlers) == 1
        
        # Global handler should receive all events
        handlers = event_bus.get_handlers_for_event(TestEvent)
        assert any(h.handler == global_handler for h in handlers)

    @pytest.mark.asyncio
    async def test_publish_and_handle(self, event_bus):
        """Test event publishing and handling"""
        handled_events = []
        
        async def handler(event: TestEvent):
            handled_events.append(event)
        
        event_bus.subscribe(TestEvent, handler)
        
        # Publish event
        event = TestEvent("test data")
        await event_bus.publish(event)
        
        # Wait for processing
        await event_bus.wait_for_empty_queue(timeout=1.0)
        
        assert len(handled_events) == 1
        assert handled_events[0].data == "test data"

    @pytest.mark.asyncio
    async def test_async_and_sync_handlers(self, event_bus):
        """Test both async and sync handlers"""
        async_results = []
        sync_results = []
        
        async def async_handler(event: TestEvent):
            await asyncio.sleep(0.01)
            async_results.append(event.data)
        
        def sync_handler(event: TestEvent):
            sync_results.append(event.data)
        
        event_bus.subscribe(TestEvent, async_handler)
        event_bus.subscribe(TestEvent, sync_handler)
        
        event = TestEvent("test")
        await event_bus.publish(event)
        await event_bus.wait_for_empty_queue(timeout=1.0)
        
        assert async_results == ["test"]
        assert sync_results == ["test"]

    @pytest.mark.asyncio
    async def test_event_filter(self, event_bus):
        """Test event filtering"""
        filtered_events = []
        
        def handler(event: TestEvent):
            filtered_events.append(event)
        
        def filter_func(event: TestEvent) -> bool:
            return event.data.startswith("pass")
        
        event_bus.subscribe(TestEvent, handler, filter_func=filter_func)
        
        # Publish events
        await event_bus.publish(TestEvent("pass test"))
        await event_bus.publish(TestEvent("fail test"))
        await event_bus.wait_for_empty_queue(timeout=1.0)
        
        assert len(filtered_events) == 1
        assert filtered_events[0].data == "pass test"

    @pytest.mark.asyncio
    async def test_event_priority(self, event_bus):
        """Test event priority in metadata"""
        event = TestEvent("test")
        
        await event_bus.publish(
            event,
            priority=EventPriority.CRITICAL,
            correlation_id="corr-123",
            user_id="user-456"
        )
        
        assert event.metadata.priority == EventPriority.CRITICAL
        assert event.metadata.correlation_id == "corr-123"
        assert event.metadata.user_id == "user-456"

    @pytest.mark.asyncio
    async def test_batch_publish(self, event_bus):
        """Test batch event publishing"""
        handled_events = []
        
        def handler(event: TestEvent):
            handled_events.append(event)
        
        event_bus.subscribe(TestEvent, handler)
        
        # Publish batch
        events = [TestEvent(f"event-{i}") for i in range(5)]
        await event_bus.publish_batch(events)
        await event_bus.wait_for_empty_queue(timeout=1.0)
        
        assert len(handled_events) == 5
        assert all(e.data.startswith("event-") for e in handled_events)

    @pytest.mark.asyncio
    async def test_error_handling_and_retry(self, event_bus):
        """Test error handling and retry mechanism"""
        attempt_count = 0
        
        def failing_handler(event: TestEvent):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception("Handler error")
        
        event_bus.subscribe(TestEvent, failing_handler)
        
        event = TestEvent("test")
        event.metadata.max_retries = 3
        
        await event_bus.publish(event)
        await asyncio.sleep(5)  # Wait for retries with backoff
        
        # Should attempt multiple times
        assert attempt_count >= 2

    @pytest.mark.asyncio
    async def test_dead_letter_queue(self, event_bus):
        """Test dead letter queue functionality"""
        def always_fail_handler(event: TestEvent):
            raise Exception("Always fails")
        
        event_bus.subscribe(TestEvent, always_fail_handler)
        
        event = TestEvent("test")
        event.metadata.max_retries = 1
        
        await event_bus.publish(event)
        await asyncio.sleep(3)  # Wait for retries
        
        # Check dead letter queue
        dlq = event_bus.get_dead_letter_queue()
        assert len(dlq) > 0
        assert dlq[0][0].data == "test"

    @pytest.mark.asyncio
    async def test_replay_dead_letter_queue(self, event_bus):
        """Test replaying dead letter queue"""
        handled = []
        fail_count = 0
        
        def conditional_handler(event: TestEvent):
            nonlocal fail_count
            if fail_count < 2:
                fail_count += 1
                raise Exception("Fail first time")
            handled.append(event)
        
        event_bus.subscribe(TestEvent, conditional_handler)
        
        # First attempt will fail
        event = TestEvent("test")
        event.metadata.max_retries = 0  # No auto-retry
        
        await event_bus.publish(event)
        await asyncio.sleep(1)
        
        assert len(event_bus.get_dead_letter_queue()) > 0
        
        # Replay
        replayed = await event_bus.replay_dead_letter_queue()
        await event_bus.wait_for_empty_queue(timeout=1.0)
        
        assert replayed > 0
        assert len(handled) > 0

    @pytest.mark.asyncio
    async def test_metrics(self, event_bus):
        """Test metrics collection"""
        handled = []
        
        def handler(event: TestEvent):
            handled.append(event)
        
        event_bus.subscribe(TestEvent, handler)
        
        # Publish events
        for i in range(5):
            await event_bus.publish(TestEvent(f"test-{i}"))
        
        await event_bus.wait_for_empty_queue(timeout=1.0)
        
        metrics = event_bus.get_metrics()
        assert metrics["events_published"] == 5
        assert metrics["events_processed"] == 5
        assert metrics["handler_count"] > 0

    @pytest.mark.asyncio
    async def test_handler_metrics(self, event_bus):
        """Test handler performance metrics"""
        async def slow_handler(event: TestEvent):
            await asyncio.sleep(0.1)
        
        wrapper = EventHandler(
            handler=slow_handler,
            event_type=TestEvent,
            is_async=True
        )
        
        event = TestEvent("test")
        await wrapper.handle(event)
        
        assert wrapper.call_count == 1
        assert wrapper.error_count == 0
        assert wrapper.avg_duration_ms > 90  # Should be > 100ms

    @pytest.mark.asyncio
    async def test_queue_full(self, event_bus):
        """Test behavior when queue is full"""
        # Fill the queue
        event_bus._event_queue = asyncio.Queue(maxsize=1)
        
        await event_bus.publish(TestEvent("first"))
        
        # This should raise
        with pytest.raises(Exception):
            await asyncio.wait_for(
                event_bus.publish(TestEvent("second")),
                timeout=0.1
            )

    def test_global_event_bus(self):
        """Test global event bus singleton"""
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        
        assert bus1 is bus2
        
        # Set new instance
        new_bus = EventBus()
        set_event_bus(new_bus)
        
        bus3 = get_event_bus()
        assert bus3 is new_bus
        assert bus3 is not bus1


class TestEventMetadata:
    """Test event metadata"""

    def test_metadata_defaults(self):
        """Test metadata default values"""
        metadata = EventMetadata()
        
        assert isinstance(metadata.event_id, str)
        assert isinstance(metadata.timestamp, datetime)
        assert metadata.source is None
        assert metadata.user_id is None
        assert metadata.correlation_id is None
        assert metadata.priority == EventPriority.NORMAL
        assert metadata.retry_count == 0
        assert metadata.max_retries == 3

    def test_metadata_custom_values(self):
        """Test metadata with custom values"""
        metadata = EventMetadata(
            event_id="custom-id",
            source="test-source",
            user_id="user-123",
            correlation_id="corr-456",
            priority=EventPriority.HIGH,
            retry_count=2,
            max_retries=5
        )
        
        assert metadata.event_id == "custom-id"
        assert metadata.source == "test-source"
        assert metadata.user_id == "user-123"
        assert metadata.correlation_id == "corr-456"
        assert metadata.priority == EventPriority.HIGH
        assert metadata.retry_count == 2
        assert metadata.max_retries == 5


class TestDomainEvent:
    """Test domain event base class"""

    def test_event_name(self):
        """Test event name generation"""
        event = TestEvent("data")
        assert event.get_event_name() == "TestEvent"
        
        another = AnotherTestEvent(42)
        assert another.get_event_name() == "AnotherTestEvent"

    def test_event_metadata(self):
        """Test event metadata"""
        event = TestEvent("data")
        assert isinstance(event.metadata, EventMetadata)
        assert event.metadata.priority == EventPriority.NORMAL


class TestEventPriority:
    """Test event priority enum"""

    def test_priority_values(self):
        """Test priority enum values"""
        assert EventPriority.LOW.value == 1
        assert EventPriority.NORMAL.value == 2
        assert EventPriority.HIGH.value == 3
        assert EventPriority.CRITICAL.value == 4

    def test_priority_comparison(self):
        """Test priority comparison"""
        assert EventPriority.LOW.value < EventPriority.NORMAL.value
        assert EventPriority.NORMAL.value < EventPriority.HIGH.value
        assert EventPriority.HIGH.value < EventPriority.CRITICAL.value