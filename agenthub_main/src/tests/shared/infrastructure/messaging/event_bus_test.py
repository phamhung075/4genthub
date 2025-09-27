"""Test event bus infrastructure

Comprehensive test coverage for event bus including:
- Event publishing and handling
- Async/sync handler support
- Priority-based execution
- Retry mechanisms
- Dead letter queue
- Performance metrics
"""

import pytest
import asyncio
from datetime import datetime, timezone
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
class SampleEvent(DomainEvent):
    """Sample event for testing"""
    def __init__(self, data: str):
        super().__init__()
        self.data = data


class AnotherSampleEvent(DomainEvent):
    """Another sample event"""
    def __init__(self, value: int):
        super().__init__()
        self.value = value


class SampleEventBus:
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
        sub_id = event_bus.subscribe(SampleEvent, handler)
        assert sub_id.startswith("SampleEvent_")
        assert SampleEvent in event_bus._handlers
        assert len(event_bus._handlers[SampleEvent]) == 1
        
        # Unsubscribe
        removed = event_bus.unsubscribe(SampleEvent, handler)
        assert removed
        assert SampleEvent not in event_bus._handlers
        
        # Unsubscribe non-existent
        removed = event_bus.unsubscribe(SampleEvent, handler)
        assert not removed

    @pytest.mark.asyncio
    async def test_subscribe_with_priority(self, event_bus):
        """Test handler priority ordering"""
        handler1 = Mock()
        handler2 = Mock()
        handler3 = Mock()
        
        event_bus.subscribe(SampleEvent, handler2, priority=5)
        event_bus.subscribe(SampleEvent, handler1, priority=10)
        event_bus.subscribe(SampleEvent, handler3, priority=1)
        
        handlers = event_bus.get_handlers_for_event(SampleEvent)
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
        handlers = event_bus.get_handlers_for_event(SampleEvent)
        assert any(h.handler == global_handler for h in handlers)

    @pytest.mark.asyncio
    async def test_publish_and_handle(self, event_bus):
        """Test event publishing and handling"""
        handled_events = []
        
        async def handler(event: SampleEvent):
            handled_events.append(event)
        
        event_bus.subscribe(SampleEvent, handler)
        
        # Publish event
        event = SampleEvent("test data")
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
        
        async def async_handler(event: SampleEvent):
            await asyncio.sleep(0.01)
            async_results.append(event.data)
        
        def sync_handler(event: SampleEvent):
            sync_results.append(event.data)
        
        event_bus.subscribe(SampleEvent, async_handler)
        event_bus.subscribe(SampleEvent, sync_handler)
        
        event = SampleEvent("test")
        await event_bus.publish(event)
        await event_bus.wait_for_empty_queue(timeout=1.0)
        
        assert async_results == ["test"]
        assert sync_results == ["test"]

    @pytest.mark.asyncio
    async def test_event_filter(self, event_bus):
        """Test event filtering"""
        filtered_events = []
        
        def handler(event: SampleEvent):
            filtered_events.append(event)
        
        def filter_func(event: SampleEvent) -> bool:
            return event.data.startswith("pass")
        
        event_bus.subscribe(SampleEvent, handler, filter_func=filter_func)
        
        # Publish events
        await event_bus.publish(SampleEvent("pass test"))
        await event_bus.publish(SampleEvent("fail test"))
        await event_bus.wait_for_empty_queue(timeout=1.0)
        
        assert len(filtered_events) == 1
        assert filtered_events[0].data == "pass test"

    @pytest.mark.asyncio
    async def test_event_priority(self, event_bus):
        """Test event priority in metadata"""
        event = SampleEvent("test")
        
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
        
        def handler(event: SampleEvent):
            handled_events.append(event)
        
        event_bus.subscribe(SampleEvent, handler)
        
        # Publish batch
        events = [SampleEvent(f"event-{i}") for i in range(5)]
        await event_bus.publish_batch(events)
        await event_bus.wait_for_empty_queue(timeout=1.0)
        
        assert len(handled_events) == 5
        assert all(e.data.startswith("event-") for e in handled_events)

    @pytest.mark.asyncio
    async def test_error_handling_and_retry(self, event_bus):
        """Test error handling and retry mechanism"""
        attempt_count = 0
        
        def failing_handler(event: SampleEvent):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception("Handler error")
        
        event_bus.subscribe(SampleEvent, failing_handler)
        
        event = SampleEvent("test")
        event.metadata.max_retries = 3
        
        await event_bus.publish(event)
        await asyncio.sleep(5)  # Wait for retries with backoff
        
        # Should attempt multiple times
        assert attempt_count >= 2

    @pytest.mark.asyncio
    async def test_dead_letter_queue(self, event_bus):
        """Test dead letter queue functionality"""
        def always_fail_handler(event: SampleEvent):
            raise Exception("Always fails")
        
        event_bus.subscribe(SampleEvent, always_fail_handler)
        
        event = SampleEvent("test")
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
        
        def conditional_handler(event: SampleEvent):
            nonlocal fail_count
            if fail_count < 2:
                fail_count += 1
                raise Exception("Fail first time")
            handled.append(event)
        
        event_bus.subscribe(SampleEvent, conditional_handler)
        
        # First attempt will fail
        event = SampleEvent("test")
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
        
        def handler(event: SampleEvent):
            handled.append(event)
        
        event_bus.subscribe(SampleEvent, handler)
        
        # Publish events
        for i in range(5):
            await event_bus.publish(SampleEvent(f"test-{i}"))
        
        await event_bus.wait_for_empty_queue(timeout=1.0)
        
        metrics = event_bus.get_metrics()
        assert metrics["events_published"] == 5
        assert metrics["events_processed"] == 5
        assert metrics["handler_count"] > 0

    @pytest.mark.asyncio
    async def test_handler_metrics(self, event_bus):
        """Test handler performance metrics"""
        async def slow_handler(event: SampleEvent):
            await asyncio.sleep(0.1)
        
        wrapper = EventHandler(
            handler=slow_handler,
            event_type=SampleEvent,
            is_async=True
        )
        
        event = SampleEvent("test")
        await wrapper.handle(event)
        
        assert wrapper.call_count == 1
        assert wrapper.error_count == 0
        assert wrapper.avg_duration_ms > 90  # Should be > 100ms

    @pytest.mark.asyncio
    async def test_queue_full(self, event_bus):
        """Test behavior when queue is full"""
        # Fill the queue
        event_bus._event_queue = asyncio.Queue(maxsize=1)
        
        await event_bus.publish(SampleEvent("first"))
        
        # This should raise
        with pytest.raises(Exception):
            await asyncio.wait_for(
                event_bus.publish(SampleEvent("second")),
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


class SampleEventMetadata:
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
        event = SampleEvent("data")
        assert event.get_event_name() == "SampleEvent"
        
        another = AnotherSampleEvent(42)
        assert another.get_event_name() == "AnotherSampleEvent"

    def test_event_metadata(self):
        """Test event metadata"""
        event = SampleEvent("data")
        assert isinstance(event.metadata, EventMetadata)
        assert event.metadata.priority == EventPriority.NORMAL


class SampleEventPriority:
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


class SampleEventBusAdvanced:
    """Advanced test scenarios for event bus"""
    
    @pytest.fixture
    async def event_bus(self):
        """Create event bus instance"""
        bus = EventBus(max_queue_size=100, worker_count=2)
        await bus.start()
        yield bus
        await bus.stop()
    
    @pytest.mark.asyncio
    async def test_multiple_handlers_same_event(self, event_bus):
        """Test multiple handlers for the same event type"""
        results = []
        
        def handler1(event: SampleEvent):
            results.append(f"handler1: {event.data}")
        
        def handler2(event: SampleEvent):
            results.append(f"handler2: {event.data}")
        
        async def handler3(event: SampleEvent):
            await asyncio.sleep(0.01)
            results.append(f"handler3: {event.data}")
        
        event_bus.subscribe(SampleEvent, handler1, priority=1)
        event_bus.subscribe(SampleEvent, handler2, priority=3)
        event_bus.subscribe(SampleEvent, handler3, priority=2)
        
        await event_bus.publish(SampleEvent("test"))
        await event_bus.wait_for_empty_queue(timeout=1.0)
        
        # Check all handlers were called in priority order
        assert len(results) == 3
        assert results[0].startswith("handler2")  # Highest priority
        assert results[1].startswith("handler3")
        assert results[2].startswith("handler1")  # Lowest priority
    
    @pytest.mark.asyncio
    async def test_handler_error_isolation(self, event_bus):
        """Test that handler errors don't affect other handlers"""
        successful_results = []
        
        def failing_handler(event: SampleEvent):
            raise Exception("Handler failed")
        
        def successful_handler(event: SampleEvent):
            successful_results.append(event.data)
        
        event_bus.subscribe(SampleEvent, failing_handler)
        event_bus.subscribe(SampleEvent, successful_handler)
        
        await event_bus.publish(SampleEvent("test"))
        await event_bus.wait_for_empty_queue(timeout=1.0)
        
        # Successful handler should still execute
        assert len(successful_results) == 1
        assert successful_results[0] == "test"
    
    @pytest.mark.asyncio
    async def test_concurrent_event_processing(self, event_bus):
        """Test concurrent processing of multiple events"""
        processed_events = []
        processing_lock = asyncio.Lock()
        
        async def slow_handler(event: SampleEvent):
            async with processing_lock:
                await asyncio.sleep(0.05)
                processed_events.append(event.data)
        
        event_bus.subscribe(SampleEvent, slow_handler)
        
        # Publish multiple events
        for i in range(5):
            await event_bus.publish(SampleEvent(f"event-{i}"))
        
        start_time = datetime.now(timezone.utc)
        await event_bus.wait_for_empty_queue(timeout=5.0)
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        # With worker_count=2, should process faster than sequential
        assert len(processed_events) == 5
        assert duration < 0.25  # Should be faster than 5 * 0.05 = 0.25s
    
    @pytest.mark.asyncio
    async def test_event_metadata_preservation(self, event_bus):
        """Test that event metadata is preserved through processing"""
        received_event = None
        
        def handler(event: SampleEvent):
            nonlocal received_event
            received_event = event
        
        event_bus.subscribe(SampleEvent, handler)
        
        event = SampleEvent("test")
        original_id = event.metadata.event_id
        original_timestamp = event.metadata.timestamp
        
        await event_bus.publish(
            event,
            priority=EventPriority.HIGH,
            correlation_id="corr-123",
            user_id="user-456"
        )
        
        await event_bus.wait_for_empty_queue(timeout=1.0)
        
        assert received_event is not None
        assert received_event.metadata.event_id == original_id
        assert received_event.metadata.timestamp == original_timestamp
        assert received_event.metadata.priority == EventPriority.HIGH
        assert received_event.metadata.correlation_id == "corr-123"
        assert received_event.metadata.user_id == "user-456"
    
    @pytest.mark.asyncio
    async def test_handler_metrics_accuracy(self, event_bus):
        """Test accuracy of handler performance metrics"""
        async def timed_handler(event: SampleEvent):
            await asyncio.sleep(0.1)  # 100ms
        
        event_bus.subscribe(SampleEvent, timed_handler)
        
        # Process multiple events
        for _ in range(3):
            await event_bus.publish(SampleEvent("test"))
        
        await event_bus.wait_for_empty_queue(timeout=2.0)
        
        metrics = event_bus.get_metrics()
        assert metrics["events_published"] == 3
        assert metrics["events_processed"] == 3
        
        # Check handler-specific metrics
        handler_metrics = metrics["handler_metrics"]
        handler_key = next(iter(handler_metrics.keys()))
        handler_stats = handler_metrics[handler_key]
        
        assert handler_stats["calls"] == 3
        assert handler_stats["errors"] == 0
        assert 90 < handler_stats["avg_duration_ms"] < 110  # ~100ms
    
    @pytest.mark.asyncio
    async def test_dead_letter_queue_with_custom_retry_policy(self, event_bus):
        """Test dead letter queue with custom retry settings"""
        attempt_counts = {}
        
        def failing_handler(event: SampleEvent):
            if event.data not in attempt_counts:
                attempt_counts[event.data] = 0
            attempt_counts[event.data] += 1
            raise Exception(f"Failed on attempt {attempt_counts[event.data]}")
        
        event_bus.subscribe(SampleEvent, failing_handler)
        
        # Create events with different retry settings
        event1 = SampleEvent("event1")
        event1.metadata.max_retries = 1
        
        event2 = SampleEvent("event2")
        event2.metadata.max_retries = 0  # No retries
        
        await event_bus.publish(event1)
        await event_bus.publish(event2)
        
        # Wait for processing and retries
        await asyncio.sleep(3)
        
        # Check attempt counts
        assert attempt_counts["event1"] == 2  # Original + 1 retry
        assert attempt_counts["event2"] == 1  # Original only
        
        # Both should be in dead letter queue
        dlq = event_bus.get_dead_letter_queue()
        dlq_events = [item[0].data for item in dlq]
        assert "event1" in dlq_events
        assert "event2" in dlq_events
    
    @pytest.mark.asyncio
    async def test_global_handler_with_type_specific_handlers(self, event_bus):
        """Test interaction between global and type-specific handlers"""
        type_specific_results = []
        global_results = []
        
        def type_handler(event: SampleEvent):
            type_specific_results.append(f"type: {event.data}")
        
        def global_handler(event: DomainEvent):
            if isinstance(event, SampleEvent):
                global_results.append(f"global: {event.data}")
            elif isinstance(event, AnotherSampleEvent):
                global_results.append(f"global: {event.value}")
        
        event_bus.subscribe(SampleEvent, type_handler)
        event_bus.subscribe_all(global_handler)
        
        # Publish different event types
        await event_bus.publish(SampleEvent("test1"))
        await event_bus.publish(AnotherSampleEvent(42))
        
        await event_bus.wait_for_empty_queue(timeout=1.0)
        
        assert len(type_specific_results) == 1
        assert type_specific_results[0] == "type: test1"
        assert len(global_results) == 2
        assert "global: test1" in global_results
        assert "global: 42" in global_results
    
    @pytest.mark.asyncio
    async def test_event_bus_cleanup_on_stop(self, event_bus):
        """Test proper cleanup when stopping event bus"""
        processed = []
        
        async def slow_handler(event: SampleEvent):
            await asyncio.sleep(0.1)
            processed.append(event.data)
        
        event_bus.subscribe(SampleEvent, slow_handler)
        
        # Publish events
        for i in range(5):
            await event_bus.publish(SampleEvent(f"event-{i}"))
        
        # Stop bus (should wait for queue to empty)
        await event_bus.stop()
        
        # All events should be processed
        assert len(processed) == 5
        assert not event_bus._is_running
        assert len(event_bus._workers) == 0
    
    @pytest.mark.asyncio
    async def test_filter_function_with_metadata(self, event_bus):
        """Test filtering based on event metadata"""
        high_priority_events = []
        
        def handler(event: SampleEvent):
            high_priority_events.append(event)
        
        def priority_filter(event: SampleEvent) -> bool:
            return event.metadata.priority.value >= EventPriority.HIGH.value
        
        event_bus.subscribe(SampleEvent, handler, filter_func=priority_filter)
        
        # Publish events with different priorities
        await event_bus.publish(SampleEvent("low"), priority=EventPriority.LOW)
        await event_bus.publish(SampleEvent("normal"), priority=EventPriority.NORMAL)
        await event_bus.publish(SampleEvent("high"), priority=EventPriority.HIGH)
        await event_bus.publish(SampleEvent("critical"), priority=EventPriority.CRITICAL)
        
        await event_bus.wait_for_empty_queue(timeout=1.0)
        
        # Only high and critical priority events should be handled
        assert len(high_priority_events) == 2
        event_data = [e.data for e in high_priority_events]
        assert "high" in event_data
        assert "critical" in event_data


class SampleEventBusStressTest:
    """Stress tests for event bus"""
    
    @pytest.mark.asyncio
    async def test_high_volume_event_processing(self):
        """Test event bus under high load"""
        bus = EventBus(max_queue_size=1000, worker_count=4)
        await bus.start()
        
        processed_count = 0
        lock = asyncio.Lock()
        
        async def counter_handler(event: SampleEvent):
            nonlocal processed_count
            async with lock:
                processed_count += 1
        
        bus.subscribe(SampleEvent, counter_handler)
        
        # Publish many events rapidly
        event_count = 500
        start_time = datetime.now(timezone.utc)
        
        publish_tasks = []
        for i in range(event_count):
            task = bus.publish(SampleEvent(f"event-{i}"))
            publish_tasks.append(task)
        
        await asyncio.gather(*publish_tasks)
        await bus.wait_for_empty_queue(timeout=10.0)
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        assert processed_count == event_count
        assert duration < 5.0  # Should process 500 events in under 5 seconds
        
        metrics = bus.get_metrics()
        assert metrics["events_published"] == event_count
        assert metrics["events_processed"] == event_count
        assert metrics["events_failed"] == 0
        
        await bus.stop()
    
    @pytest.mark.asyncio
    async def test_queue_full_behavior_under_stress(self):
        """Test behavior when queue reaches capacity"""
        bus = EventBus(max_queue_size=10, worker_count=1)
        await bus.start()
        
        # Slow handler to create backpressure
        async def slow_handler(event: SampleEvent):
            await asyncio.sleep(0.1)
        
        bus.subscribe(SampleEvent, slow_handler)
        
        # Try to publish more events than queue size
        publish_tasks = []
        failed_publishes = 0
        
        for i in range(15):
            try:
                await asyncio.wait_for(
                    bus.publish(SampleEvent(f"event-{i}")),
                    timeout=0.01
                )
            except (asyncio.QueueFull, asyncio.TimeoutError):
                failed_publishes += 1
        
        # Some publishes should fail due to full queue
        assert failed_publishes > 0
        
        await bus.stop()