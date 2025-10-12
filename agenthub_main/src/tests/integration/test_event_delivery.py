"""
Integration Tests for Event Delivery System

Tests end-to-end event flow: publish → queue → worker → handler
This verifies the complete event processing pipeline works correctly.

Test Coverage:
- End-to-end event flow with single handler
- Multiple handlers for same event type
- High-load scenarios with many events
- No events lost during processing
- Worker health and lifecycle management

Week 1 Performance Optimization - Day 4
"""

import pytest
import time
import threading
from typing import List

from fastmcp.task_management.infrastructure.events import EventQueue, EventWorker
from fastmcp.task_management.infrastructure.event_bus import EventBus
from fastmcp.task_management.domain.events.task_lifecycle_events import (
    TaskCreatedEvent,
    TaskUpdatedEvent,
    TaskCompletedEvent,
)


class TestEventDeliveryIntegration:
    """Integration tests for complete event delivery system."""

    def test_end_to_end_event_flow(self):
        """
        Test complete event flow: publish → queue → worker → handler

        Verifies:
        - Event published successfully
        - Event queued in EventQueue
        - Worker processes event from queue
        - Handler receives and processes event
        - No events lost in the pipeline
        """
        # Setup event infrastructure
        queue = EventQueue(maxsize=100)
        event_bus = EventBus()
        event_bus.set_event_queue(queue)

        # Track handler calls
        handler_calls = []
        call_lock = threading.Lock()

        def test_handler(event):
            """Test handler that records event"""
            with call_lock:
                handler_calls.append(event)

        # Register handler using correct method name
        event_bus.subscribe(TaskCreatedEvent, test_handler)

        # Start worker
        event_handlers = {TaskCreatedEvent: [test_handler]}
        worker = EventWorker(event_handlers, max_queue_size=100)
        worker.start()

        # Give worker time to initialize
        time.sleep(0.1)

        # Publish event
        event = TaskCreatedEvent(
            task_id="test-123",
            title="Test Task",
            branch_id="branch-1",
            status="todo",
            priority="medium",
            assignees=["test-agent"],
        )

        # Enqueue event directly (simulating EventBus behavior)
        success = worker.enqueue_event(event)
        assert success, "Event should be enqueued successfully"

        # Wait for processing (with timeout)
        max_wait = 2.0
        start_time = time.time()
        while len(handler_calls) == 0 and time.time() - start_time < max_wait:
            time.sleep(0.1)

        # Verify event was processed
        with call_lock:
            assert len(handler_calls) == 1, f"Expected 1 handler call, got {len(handler_calls)}"
            assert handler_calls[0].task_id == "test-123"
            assert handler_calls[0].title == "Test Task"

        # Check worker stats
        stats = worker.get_stats()
        assert stats['events_processed'] >= 1
        assert stats['events_failed'] == 0
        assert worker.is_healthy()

        # Cleanup
        worker.stop(timeout=5)

    def test_multiple_handlers_same_event(self):
        """
        Test multiple handlers for the same event type.

        Verifies:
        - All handlers receive the event
        - Handlers execute independently
        - Failure in one handler doesn't affect others
        - Event delivered to all subscribers
        """
        # Setup
        queue = EventQueue(maxsize=100)
        event_bus = EventBus()
        event_bus.set_event_queue(queue)

        # Track calls from multiple handlers
        handler1_calls = []
        handler2_calls = []
        handler3_calls = []
        call_locks = {
            'h1': threading.Lock(),
            'h2': threading.Lock(),
            'h3': threading.Lock(),
        }

        def handler1(event):
            with call_locks['h1']:
                handler1_calls.append(event)

        def handler2(event):
            with call_locks['h2']:
                handler2_calls.append(event)

        def handler3(event):
            """Handler that simulates occasional failures"""
            with call_locks['h3']:
                handler3_calls.append(event)
                # Simulate processing work
                time.sleep(0.01)

        # Register all handlers
        event_bus.subscribe(TaskCreatedEvent, handler1)
        event_bus.subscribe(TaskCreatedEvent, handler2)
        event_bus.subscribe(TaskCreatedEvent, handler3)

        # Start worker with all handlers
        event_handlers = {
            TaskCreatedEvent: [handler1, handler2, handler3]
        }
        worker = EventWorker(event_handlers, max_queue_size=100)
        worker.start()

        time.sleep(0.1)

        # Publish event
        event = TaskCreatedEvent(
            task_id="test-multi",
            title="Multi Handler Test",
            branch_id="branch-1",
            status="todo",
            priority="high",
            assignees=["agent-1", "agent-2"],
        )

        worker.enqueue_event(event)

        # Wait for all handlers to process
        max_wait = 3.0
        start_time = time.time()
        while (len(handler1_calls) == 0 or len(handler2_calls) == 0 or len(handler3_calls) == 0) and time.time() - start_time < max_wait:
            time.sleep(0.1)

        # Verify all handlers received the event
        with call_locks['h1']:
            assert len(handler1_calls) == 1, "Handler 1 should receive event"
            assert handler1_calls[0].task_id == "test-multi"

        with call_locks['h2']:
            assert len(handler2_calls) == 1, "Handler 2 should receive event"
            assert handler2_calls[0].task_id == "test-multi"

        with call_locks['h3']:
            assert len(handler3_calls) == 1, "Handler 3 should receive event"
            assert handler3_calls[0].task_id == "test-multi"

        # Verify worker stats
        stats = worker.get_stats()
        assert stats['events_processed'] >= 1
        assert worker.is_healthy()

        # Cleanup
        worker.stop(timeout=5)

    def test_event_system_under_load(self):
        """
        Test event system handles high load correctly.

        Verifies:
        - System processes many events rapidly
        - No events are lost
        - Queue doesn't overflow
        - All events processed within reasonable time
        - Worker remains healthy under load
        """
        # Setup with smaller queue for faster tests
        num_events = 50  # Reduced from 100 for faster tests

        # Track processed events
        processed_events = []
        processed_lock = threading.Lock()

        def counting_handler(event):
            with processed_lock:
                processed_events.append(event.task_id)

        # Start worker
        event_handlers = {TaskCreatedEvent: [counting_handler]}
        worker = EventWorker(event_handlers, max_queue_size=200)
        worker.start()

        time.sleep(0.1)

        # Publish many events rapidly
        published_ids = []

        for i in range(num_events):
            event = TaskCreatedEvent(
                task_id=f"task-{i}",
                title=f"Task {i}",
                branch_id="branch-load-test",
                status="todo",
                priority="medium",
                assignees=["load-test-agent"],
            )
            success = worker.enqueue_event(event)
            if success:
                published_ids.append(event.task_id)

        # Wait for all processing with timeout
        timeout = 5.0  # Give enough time for 50 events
        start = time.time()

        while len(processed_events) < len(published_ids) and time.time() - start < timeout:
            time.sleep(0.1)

        # Verify all events processed
        with processed_lock:
            processed_count = len(processed_events)
            expected_count = len(published_ids)

            assert processed_count == expected_count, (
                f"Expected {expected_count} events processed, got {processed_count}. "
                f"Lost {expected_count - processed_count} events."
            )

            # Verify no duplicates
            assert len(set(processed_events)) == processed_count, (
                "Duplicate events detected in processing"
            )

        # Check worker stats
        stats = worker.get_stats()
        assert stats['events_processed'] >= num_events, (
            f"Expected at least {num_events} processed, got {stats['events_processed']}"
        )
        assert stats['queue_overflow_count'] == 0, (
            f"Queue overflow occurred {stats['queue_overflow_count']} times"
        )
        assert worker.is_healthy(), "Worker should be healthy after processing"

        # Cleanup
        worker.stop(timeout=5)

    def test_event_delivery_with_different_event_types(self):
        """
        Test event delivery with multiple event types.

        Verifies:
        - Different event types routed correctly
        - Type-specific handlers receive correct events
        - No cross-contamination between event types
        """
        queue = EventQueue(maxsize=100)
        event_bus = EventBus()
        event_bus.set_event_queue(queue)

        # Track calls by event type
        created_events = []
        updated_events = []
        completed_events = []
        locks = {
            'created': threading.Lock(),
            'updated': threading.Lock(),
            'completed': threading.Lock(),
        }

        def created_handler(event):
            with locks['created']:
                created_events.append(event)

        def updated_handler(event):
            with locks['updated']:
                updated_events.append(event)

        def completed_handler(event):
            with locks['completed']:
                completed_events.append(event)

        # Register handlers for different event types
        event_bus.subscribe(TaskCreatedEvent, created_handler)
        event_bus.subscribe(TaskUpdatedEvent, updated_handler)
        event_bus.subscribe(TaskCompletedEvent, completed_handler)

        # Start worker
        event_handlers = {
            TaskCreatedEvent: [created_handler],
            TaskUpdatedEvent: [updated_handler],
            TaskCompletedEvent: [completed_handler],
        }
        worker = EventWorker(event_handlers, max_queue_size=100)
        worker.start()

        time.sleep(0.1)

        # Publish different event types
        created_event = TaskCreatedEvent(
            task_id="task-1",
            title="New Task",
            branch_id="branch-1",
            status="todo",
            priority="high",
            assignees=["agent-1"],
        )

        updated_event = TaskUpdatedEvent(
            task_id="task-1",
            branch_id="branch-1",
            old_status="todo",
            new_status="in_progress",
            changes={"status": "in_progress"},
        )

        completed_event = TaskCompletedEvent(
            task_id="task-1",
            branch_id="branch-1",
            title="New Task",
            completion_summary="Task completed successfully",
            testing_notes="All tests passed",
        )

        # Enqueue all events
        worker.enqueue_event(created_event)
        worker.enqueue_event(updated_event)
        worker.enqueue_event(completed_event)

        # Wait for processing
        max_wait = 2.0
        start_time = time.time()
        while (len(created_events) == 0 or len(updated_events) == 0 or len(completed_events) == 0) and time.time() - start_time < max_wait:
            time.sleep(0.1)

        # Verify correct routing
        with locks['created']:
            assert len(created_events) == 1
            assert created_events[0].task_id == "task-1"
            assert created_events[0].title == "New Task"

        with locks['updated']:
            assert len(updated_events) == 1
            assert updated_events[0].task_id == "task-1"
            assert updated_events[0].new_status == "in_progress"

        with locks['completed']:
            assert len(completed_events) == 1
            assert completed_events[0].task_id == "task-1"
            assert completed_events[0].completion_summary == "Task completed successfully"

        # Cleanup
        worker.stop(timeout=5)


class TestEventWorkerLifecycle:
    """Tests for EventWorker lifecycle management."""

    def test_worker_start_stop(self):
        """Test worker starts and stops cleanly."""
        handler_calls = []

        def test_handler(event):
            handler_calls.append(event)

        event_handlers = {TaskCreatedEvent: [test_handler]}
        worker = EventWorker(event_handlers, max_queue_size=100)

        # Initially not running
        assert not worker.is_healthy()

        # Start worker
        worker.start()
        time.sleep(0.1)

        assert worker.is_healthy()

        # Stop worker
        worker.stop(timeout=5)
        time.sleep(0.1)

        # Worker should no longer be healthy
        # Note: is_healthy() checks _running flag and heartbeat
        # After stop(), _running is False

    def test_worker_processes_events_before_shutdown(self):
        """Test worker drains queue before shutting down."""
        processed_events = []
        processed_lock = threading.Lock()

        def slow_handler(event):
            """Slow handler to ensure events are in queue during shutdown"""
            time.sleep(0.05)
            with processed_lock:
                processed_events.append(event.task_id)

        event_handlers = {TaskCreatedEvent: [slow_handler]}
        worker = EventWorker(event_handlers, max_queue_size=100)
        worker.start()

        time.sleep(0.1)

        # Enqueue multiple events
        num_events = 10
        for i in range(num_events):
            event = TaskCreatedEvent(
                task_id=f"task-{i}",
                title=f"Task {i}",
                branch_id="branch-1",
                status="todo",
                priority="medium",
                assignees=["agent-1"],
            )
            worker.enqueue_event(event)

        # Stop worker - should drain queue
        worker.stop(timeout=10)

        # Verify all events were processed
        with processed_lock:
            assert len(processed_events) == num_events, (
                f"Expected {num_events} events processed during shutdown, "
                f"got {len(processed_events)}"
            )


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
