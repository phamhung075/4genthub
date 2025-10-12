# Performance Fix Implementation Plan
## DDD Refactoring Phase 1-8 Performance Issues Resolution

**Document Version:** 1.0
**Created:** 2025-10-11
**Status:** Planning
**Priority:** CRITICAL
**Target Improvement:** 80% reduction in request latency (150ms → <30ms)

---

## Executive Summary

### Problem Statement

The DDD refactoring (Phases 1-8) introduced a **3-5x performance degradation** compared to the legacy system. The primary bottleneck is the **synchronous domain event publishing system** introduced in Phase 5, which blocks request threads and adds 50-150ms overhead per event.

**Current Performance:**
- Task creation: ~150ms per operation (vs. 30ms baseline)
- Event publishing: 50-150ms blocking time per event
- Throughput: 20-30 tasks/second (vs. 100+ baseline)

**Performance Breakdown:**
- **70-80% slowdown:** Domain event publishing (synchronous, blocking)
- **10-15% slowdown:** UUID validation (no caching, 5 regex patterns)
- **5-10% slowdown:** Eager relationship loading (unnecessary JOINs)
- **5% overhead:** Rich domain entity operations (acceptable DDD cost)

### Architecture Decision

**Selected Approach:** Event Queue with Background Worker (Option B)

**Why This Approach:**
1. **Robustness:** Guaranteed event delivery with retry logic
2. **Observability:** Full visibility into event processing pipeline
3. **Scalability:** Handles traffic spikes without blocking requests
4. **DDD Compliance:** Maintains domain event semantics while fixing performance
5. **Industry Standard:** Battle-tested pattern (AWS SQS, RabbitMQ, Celery)

**Expected Impact:**
- ✅ **80% latency reduction:** 150ms → <30ms per request
- ✅ **5x throughput increase:** 20-30 → 100+ tasks/second
- ✅ **Zero event loss:** 100% delivery guarantee with retry
- ✅ **Improved observability:** Queue metrics, event tracking, health monitoring

### Risk Level: MEDIUM

**Key Risks:**
- Event loss if worker crashes (MITIGATED: persistence + retry)
- Event ordering issues (MITIGATED: single FIFO worker)
- Memory overflow under load (MITIGATED: backpressure + alerts)
- Worker thread failure (MITIGATED: health checks + auto-restart)

**Rollback Strategy:**
- Feature flag for instant rollback
- Parallel implementation (new alongside old)
- Gradual rollout with monitoring
- Clear success/failure criteria

---

## Table of Contents

1. [Detailed Architecture Design](#detailed-architecture-design)
2. [Implementation Guide](#implementation-guide)
3. [Migration Plan](#migration-plan)
4. [Risk & Mitigation](#risk--mitigation)
5. [Testing & Validation](#testing--validation)
6. [Monitoring & Operations](#monitoring--operations)
7. [Timeline & Milestones](#timeline--milestones)

---

## Detailed Architecture Design

### Current Architecture (Problematic)

```
┌─────────────────────────────────────────────────────────────┐
│                    HTTP Request Thread                       │
│                                                               │
│  FastAPI Endpoint                                             │
│      ↓                                                        │
│  Application Facade                                           │
│      ↓                                                        │
│  Repository.save()                                            │
│      ↓                                                        │
│  publish_entity_events()  ←─────────────────┐               │
│      ↓                                       │               │
│  EventBus.publish_sync()                     │               │
│      ↓                                       │               │
│  asyncio.create_task() / loop.run_until_complete()          │
│      ↓                                       │               │
│  loop.run_in_executor(thread_pool, handler) │               │
│      ↓                                       │               │
│  ⏰ BLOCKS 50-150ms per event ⏰            │               │
│                                               │               │
│  Event Handler Execution (in thread pool)    │               │
│      ↓                                       │               │
│  Returns to request thread  ─────────────────┘               │
│      ↓                                                        │
│  Response sent to client                                      │
└─────────────────────────────────────────────────────────────┘

PROBLEM: Request thread blocks waiting for event processing!
```

### New Architecture (Solution)

```
┌─────────────────────────────────────────────────────────────┐
│                    HTTP Request Thread                       │
│                                                               │
│  FastAPI Endpoint                                             │
│      ↓                                                        │
│  Application Facade                                           │
│      ↓                                                        │
│  Repository.save()                                            │
│      ↓                                                        │
│  EventPublisher.publish(event)                                │
│      ↓                                                        │
│  EventQueue.put(event)  ←── Thread-safe queue                │
│      ↓                                                        │
│  ✅ IMMEDIATE RETURN (<5ms) ✅                               │
│      ↓                                                        │
│  Response sent to client                                      │
└─────────────────────────────────────────────────────────────┘

                            ║
                            ║ Asynchronous Processing
                            ║
                            ↓

┌─────────────────────────────────────────────────────────────┐
│                   Background Worker Thread                   │
│                                                               │
│  while running:                                               │
│      event = EventQueue.get()  ←── Blocking (worker only)    │
│      ↓                                                        │
│      for handler in event.handlers:                           │
│          try:                                                 │
│              handler.execute(event)                           │
│              log_success(event)                               │
│          except Exception as e:                               │
│              retry_with_backoff(event, e)                     │
│              alert_if_failed(event, e)                        │
│                                                               │
│  Health monitoring, metrics, graceful shutdown                │
└─────────────────────────────────────────────────────────────┘

SOLUTION: Request returns immediately, events processed in background!
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Core Components                        │
└─────────────────────────────────────────────────────────────┘

1. EventQueue (Thread-Safe)
   ├── Queue[DomainEvent]  (Python queue.Queue)
   ├── max_size: 10,000 events
   ├── put(event) → None (non-blocking for producer)
   ├── get() → DomainEvent (blocking for consumer)
   ├── size() → int (for monitoring)
   └── Backpressure when full (blocks publisher)

2. EventWorker (Background Thread)
   ├── Thread daemon: False (graceful shutdown)
   ├── Event loop: while running
   ├── Handler execution: sequential
   ├── Error handling: retry with exponential backoff
   ├── Health check: heartbeat every 10s
   └── Graceful shutdown: process queue on exit

3. EventPublisher (Facade)
   ├── publish(event) → None (immediate return)
   ├── Feature flag: ENABLE_ASYNC_EVENT_QUEUE
   ├── Fallback: sync publishing if flag off
   ├── Metrics: queue depth, publish latency
   └── Backpressure handling: alert + block if full

4. EventBus (Updated)
   ├── register_handler(event_type, handler)
   ├── publish(event) → routes to EventPublisher
   ├── Backward compatible interface
   └── Remove: asyncio wrappers, blocking code

5. Monitoring & Observability
   ├── Metrics: queue depth, latency, failures
   ├── Logging: event lifecycle, errors
   ├── Alerts: queue overflow, worker death
   └── Health endpoint: /health/events
```

### Data Flow Diagram

```
Request Processing Flow:
========================

1. HTTP Request
   ↓
2. Facade Layer (business logic)
   ↓
3. Repository.save(entity)
   ↓
4. Entity.collect_events() → [DomainEvent]
   ↓
5. publish_entity_events(events)
   ↓
6. FOR EACH event:
   │
   ├─→ EventPublisher.publish(event)
   │   │
   │   ├─→ EventQueue.put(event)  [<5ms]
   │   │
   │   └─→ RETURN IMMEDIATELY ✅
   │
   └─→ Next event
   ↓
7. HTTP Response (all events queued)

Background Processing Flow:
===========================

EventWorker.run():
   ↓
   LOOP:
   │
   ├─→ event = EventQueue.get()  [blocking wait]
   │   ↓
   │   handlers = EventBus.get_handlers(event.type)
   │   ↓
   │   FOR EACH handler:
   │   │
   │   ├─→ TRY:
   │   │   │
   │   │   ├─→ handler.execute(event)
   │   │   ├─→ log_event_processed(event)
   │   │   └─→ update_metrics(success=True)
   │   │
   │   └─→ EXCEPT Exception:
   │       │
   │       ├─→ log_error(event, exception)
   │       ├─→ retry_queue.put(event, backoff)
   │       ├─→ update_metrics(success=False)
   │       └─→ alert_if_threshold_exceeded()
   │
   └─→ CONTINUE (next event)
```

### Error Handling Strategy

```
Error Handling & Retry Logic:
==============================

┌─────────────────────────────────────────────────────────────┐
│                    Event Processing                          │
│                                                               │
│  event = queue.get()                                          │
│      ↓                                                        │
│  TRY execute handler                                          │
│      ├─→ SUCCESS → log + metrics + continue                  │
│      │                                                        │
│      └─→ EXCEPTION:                                          │
│          │                                                    │
│          ├─→ Attempt 1: retry immediately                    │
│          ├─→ Attempt 2: retry after 1s                       │
│          ├─→ Attempt 3: retry after 5s                       │
│          ├─→ Attempt 4: retry after 15s                      │
│          ├─→ Attempt 5: retry after 30s                      │
│          │                                                    │
│          └─→ FINAL FAILURE:                                  │
│              │                                                │
│              ├─→ Log to error log                            │
│              ├─→ Save to dead_letter_queue table             │
│              ├─→ Alert via monitoring                        │
│              ├─→ Increment failure metrics                   │
│              └─→ Continue processing (don't crash)           │
└─────────────────────────────────────────────────────────────┘

Retry Backoff Schedule:
- Attempt 1: Immediate (0s)
- Attempt 2: 1s delay
- Attempt 3: 5s delay
- Attempt 4: 15s delay
- Attempt 5: 30s delay (final)

Dead Letter Queue:
- Table: event_processing_failures
- Columns: event_id, event_type, payload, error, attempts, timestamp
- Retention: 30 days
- Manual replay: admin endpoint
```

### Graceful Shutdown

```
Application Shutdown Flow:
==========================

1. Receive shutdown signal (SIGTERM, SIGINT)
   ↓
2. Stop accepting new requests
   ↓
3. Signal EventWorker to stop
   │
   └─→ worker.stop_flag = True
   ↓
4. Wait for EventWorker to finish current event
   ↓
5. Process remaining events in queue
   │
   ├─→ Set timeout: 30 seconds
   │
   ├─→ While queue not empty AND timeout not reached:
   │   │
   │   ├─→ event = queue.get_nowait()
   │   ├─→ process(event)
   │   └─→ continue
   │
   └─→ If timeout reached:
       │
       ├─→ Log remaining events
       ├─→ Persist queue to disk (recovery)
       └─→ Exit
   ↓
6. Close database connections
   ↓
7. Exit application

Recovery on Restart:
- Load persisted events from disk
- Re-queue for processing
- Resume normal operation
```

---

## Implementation Guide

### Week 1: Core Implementation (Critical Path)

#### Day 1: Event Queue Infrastructure

**File 1: `agenthub_main/src/fastmcp/task_management/infrastructure/events/event_queue.py` (NEW)**

**Purpose:** Thread-safe event queue with backpressure

**Implementation:**
```python
"""
Event Queue - Thread-safe queue for domain events
Provides backpressure and monitoring for event processing
"""
from queue import Queue, Full, Empty
from threading import Thread, Event as ThreadEvent
from typing import Callable, Optional, Dict, Any
import logging
import time
from datetime import datetime

from ...domain.events.base import DomainEvent

logger = logging.getLogger(__name__)


class EventQueue:
    """Thread-safe FIFO queue for domain events"""

    def __init__(self, max_size: int = 10000):
        self._queue: Queue[DomainEvent] = Queue(maxsize=max_size)
        self._max_size = max_size
        self._stop_event = ThreadEvent()

        # Metrics
        self._total_enqueued = 0
        self._total_dequeued = 0
        self._total_dropped = 0

    def put(self, event: DomainEvent, timeout: float = 5.0) -> bool:
        """
        Add event to queue (blocking with timeout if full)

        Returns:
            True if enqueued successfully
            False if queue full and timeout reached
        """
        try:
            self._queue.put(event, block=True, timeout=timeout)
            self._total_enqueued += 1

            # Alert if queue depth concerning
            depth = self.size()
            if depth > self._max_size * 0.8:
                logger.warning(
                    f"Event queue depth at {depth}/{self._max_size} (80% full)"
                )

            return True

        except Full:
            logger.error(
                f"Event queue full! Dropped event: {event.event_type}",
                extra={"event": event.to_dict()}
            )
            self._total_dropped += 1
            return False

    def get(self, timeout: Optional[float] = 1.0) -> Optional[DomainEvent]:
        """
        Get event from queue (blocking with timeout)

        Returns:
            DomainEvent if available
            None if timeout or stop signal
        """
        if self._stop_event.is_set():
            return None

        try:
            event = self._queue.get(block=True, timeout=timeout)
            self._total_dequeued += 1
            return event

        except Empty:
            return None

    def size(self) -> int:
        """Current queue depth"""
        return self._queue.qsize()

    def is_empty(self) -> bool:
        """Check if queue is empty"""
        return self._queue.empty()

    def stop(self):
        """Signal queue to stop (for graceful shutdown)"""
        self._stop_event.set()

    def metrics(self) -> Dict[str, Any]:
        """Get queue metrics"""
        return {
            "queue_depth": self.size(),
            "max_size": self._max_size,
            "total_enqueued": self._total_enqueued,
            "total_dequeued": self._total_dequeued,
            "total_dropped": self._total_dropped,
            "utilization_pct": (self.size() / self._max_size) * 100
        }


class EventWorker:
    """Background worker thread for processing events"""

    def __init__(
        self,
        queue: EventQueue,
        event_bus: Any,  # EventBus type
        shutdown_timeout: int = 30
    ):
        self._queue = queue
        self._event_bus = event_bus
        self._shutdown_timeout = shutdown_timeout
        self._stop_flag = False
        self._thread: Optional[Thread] = None
        self._last_heartbeat = datetime.now()

        # Metrics
        self._events_processed = 0
        self._events_failed = 0

    def start(self):
        """Start the worker thread"""
        if self._thread and self._thread.is_alive():
            logger.warning("Worker already running")
            return

        self._stop_flag = False
        self._thread = Thread(target=self._run, daemon=False, name="EventWorker")
        self._thread.start()
        logger.info("Event worker started")

    def stop(self):
        """Stop the worker thread gracefully"""
        logger.info("Stopping event worker...")
        self._stop_flag = True
        self._queue.stop()

        if self._thread:
            self._thread.join(timeout=self._shutdown_timeout)
            if self._thread.is_alive():
                logger.error(
                    f"Worker did not stop within {self._shutdown_timeout}s timeout"
                )
            else:
                logger.info("Event worker stopped gracefully")

    def _run(self):
        """Main worker loop"""
        logger.info("Event worker running")

        while not self._stop_flag:
            try:
                # Update heartbeat
                self._last_heartbeat = datetime.now()

                # Get event from queue (with timeout for shutdown check)
                event = self._queue.get(timeout=1.0)

                if event is None:
                    continue

                # Process event with retry logic
                self._process_event_with_retry(event)

            except Exception as e:
                logger.error(f"Unexpected error in worker loop: {e}", exc_info=True)
                time.sleep(1)  # Prevent tight loop on persistent errors

        # Graceful shutdown: process remaining events
        self._drain_queue()
        logger.info("Event worker exited")

    def _process_event_with_retry(self, event: DomainEvent):
        """Process event with exponential backoff retry"""
        max_attempts = 5
        backoff_delays = [0, 1, 5, 15, 30]  # seconds

        for attempt in range(1, max_attempts + 1):
            try:
                # Execute all handlers for this event type
                self._event_bus._execute_handlers(event)

                # Success
                self._events_processed += 1
                logger.debug(
                    f"Event processed: {event.event_type}",
                    extra={"event_id": event.event_id, "attempt": attempt}
                )
                return

            except Exception as e:
                logger.error(
                    f"Event processing failed (attempt {attempt}/{max_attempts}): "
                    f"{event.event_type} - {e}",
                    extra={"event": event.to_dict(), "error": str(e)},
                    exc_info=True
                )

                if attempt < max_attempts:
                    delay = backoff_delays[attempt - 1]
                    if delay > 0:
                        logger.info(f"Retrying in {delay}s...")
                        time.sleep(delay)
                else:
                    # Final failure - send to dead letter queue
                    self._handle_final_failure(event, e)
                    self._events_failed += 1

    def _handle_final_failure(self, event: DomainEvent, error: Exception):
        """Handle event that failed all retries"""
        logger.critical(
            f"Event failed after all retries: {event.event_type}",
            extra={
                "event": event.to_dict(),
                "error": str(error),
                "action": "sent_to_dead_letter_queue"
            }
        )

        # TODO: Persist to dead_letter_queue table for manual replay
        # For now, just log

    def _drain_queue(self):
        """Process remaining events during shutdown"""
        logger.info("Draining event queue...")
        start_time = time.time()
        processed = 0

        while not self._queue.is_empty():
            if time.time() - start_time > self._shutdown_timeout:
                remaining = self._queue.size()
                logger.warning(
                    f"Shutdown timeout reached. {remaining} events remain in queue."
                )
                # TODO: Persist remaining events to disk for recovery
                break

            event = self._queue.get(timeout=0.1)
            if event:
                try:
                    self._event_bus._execute_handlers(event)
                    processed += 1
                except Exception as e:
                    logger.error(f"Error draining event: {e}")

        logger.info(f"Drained {processed} events from queue")

    def is_alive(self) -> bool:
        """Check if worker thread is alive"""
        return self._thread is not None and self._thread.is_alive()

    def heartbeat_age(self) -> float:
        """Seconds since last heartbeat"""
        return (datetime.now() - self._last_heartbeat).total_seconds()

    def metrics(self) -> Dict[str, Any]:
        """Get worker metrics"""
        return {
            "is_alive": self.is_alive(),
            "heartbeat_age_seconds": self.heartbeat_age(),
            "events_processed": self._events_processed,
            "events_failed": self._events_failed,
            "failure_rate_pct": (
                (self._events_failed / self._events_processed * 100)
                if self._events_processed > 0 else 0
            )
        }
```

**Risk Level:** LOW (new file, isolated component)

**Testing Strategy:**
```python
def test_event_queue_put_get():
    queue = EventQueue(max_size=100)
    event = TaskCreatedEvent(...)

    assert queue.put(event) == True
    assert queue.size() == 1
    assert queue.get() == event
    assert queue.is_empty()

def test_event_queue_backpressure():
    queue = EventQueue(max_size=2)
    queue.put(event1)
    queue.put(event2)

    # Queue full - should timeout
    assert queue.put(event3, timeout=0.1) == False
    assert queue.metrics()["total_dropped"] == 1

def test_event_worker_processing():
    queue = EventQueue()
    worker = EventWorker(queue, event_bus)
    worker.start()

    queue.put(event)
    time.sleep(0.5)  # Allow processing

    assert worker.metrics()["events_processed"] == 1
    worker.stop()
```

---

**File 2: `agenthub_main/src/fastmcp/task_management/infrastructure/events/__init__.py` (NEW)**

**Purpose:** Module initialization and exports

**Implementation:**
```python
"""
Event infrastructure package
Provides event queue, worker, and publishing mechanisms
"""
from .event_queue import EventQueue, EventWorker

__all__ = ["EventQueue", "EventWorker"]
```

**Risk Level:** LOW

---

#### Day 2: Event Bus Refactoring

**File 3: `agenthub_main/src/fastmcp/task_management/infrastructure/event_bus.py` (MODIFY)**

**Current Lines:** (Need to check file first)
**Changes Required:**

1. Remove asyncio wrapper code
2. Add EventQueue integration
3. Add feature flag support
4. Keep backward-compatible interface

**Implementation Changes:**
```python
# BEFORE (Problematic):
def publish_sync(self, event: DomainEvent):
    """Synchronous publish - BLOCKS request thread"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            task = asyncio.create_task(self._async_publish(event))
            # BLOCKING: wait for async task
            loop.run_until_complete(task)
        else:
            loop.run_until_complete(self._async_publish(event))
    except Exception as e:
        logger.error(f"Event publishing failed: {e}")

async def _async_publish(self, event: DomainEvent):
    """Execute handlers in thread pool - ADDS OVERHEAD"""
    handlers = self._handlers.get(event.event_type, [])
    for handler in handlers:
        await asyncio.get_event_loop().run_in_executor(
            None, handler.execute, event
        )

# AFTER (Fixed):
from ..settings import settings
from .events.event_queue import EventQueue

class EventBus:
    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._event_queue: Optional[EventQueue] = None

    def set_event_queue(self, queue: EventQueue):
        """Set event queue for async processing"""
        self._event_queue = queue

    def publish(self, event: DomainEvent):
        """
        Publish event (async if queue enabled, sync otherwise)

        Feature flag: ENABLE_ASYNC_EVENT_QUEUE
        """
        if settings.ENABLE_ASYNC_EVENT_QUEUE and self._event_queue:
            # Async mode: queue and return immediately
            success = self._event_queue.put(event, timeout=5.0)
            if not success:
                logger.error(
                    f"Failed to queue event (queue full): {event.event_type}"
                )
                # Fallback to sync if queue unavailable
                self._execute_handlers(event)
        else:
            # Sync mode: execute immediately (fallback)
            self._execute_handlers(event)

    def _execute_handlers(self, event: DomainEvent):
        """Execute all handlers for event type (synchronous)"""
        handlers = self._handlers.get(event.event_type, [])

        for handler in handlers:
            try:
                handler.execute(event)
            except Exception as e:
                logger.error(
                    f"Event handler failed: {handler.__class__.__name__} "
                    f"for {event.event_type} - {e}",
                    exc_info=True
                )
                # Don't stop processing other handlers

    def register_handler(self, event_type: str, handler: EventHandler):
        """Register event handler"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    # Remove: publish_sync, _async_publish, all asyncio code
```

**Risk Level:** MEDIUM (core component, many dependencies)

**Dependencies:**
- Requires EventQueue implemented first
- Requires feature flag in settings

**Testing Strategy:**
```python
def test_event_bus_async_publish():
    """Test async publishing with queue"""
    bus = EventBus()
    queue = EventQueue()
    bus.set_event_queue(queue)

    with mock.patch.dict(os.environ, {"ENABLE_ASYNC_EVENT_QUEUE": "true"}):
        bus.publish(event)

        # Should return immediately
        assert queue.size() == 1

def test_event_bus_sync_fallback():
    """Test sync fallback when flag disabled"""
    bus = EventBus()
    handler = mock.Mock()
    bus.register_handler("test_event", handler)

    with mock.patch.dict(os.environ, {"ENABLE_ASYNC_EVENT_QUEUE": "false"}):
        bus.publish(TestEvent())

        # Handler executed immediately
        assert handler.execute.called
```

---

#### Day 3: Settings & Repository Updates

**File 4: `agenthub_main/src/fastmcp/settings.py` (MODIFY)**

**Add Feature Flag:**
```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Event Queue Configuration
    ENABLE_ASYNC_EVENT_QUEUE: bool = Field(
        default=False,
        description="Enable async event queue for non-blocking event publishing"
    )
    EVENT_QUEUE_MAX_SIZE: int = Field(
        default=10000,
        description="Maximum events in queue before backpressure"
    )
    EVENT_WORKER_SHUTDOWN_TIMEOUT: int = Field(
        default=30,
        description="Seconds to wait for worker shutdown"
    )
```

**Risk Level:** LOW

---

**File 5: `agenthub_main/src/fastmcp/task_management/infrastructure/repositories/event_publishing_mixin.py` (MODIFY)**

**Current Lines:** Check file
**Changes:** Remove asyncio wrappers, simplify

**Implementation:**
```python
# BEFORE (Complex):
def publish_entity_events(self, entity):
    """Publish entity events - BLOCKS"""
    events = entity.collect_events()
    for event in events:
        try:
            # Asyncio wrapper - ADDS OVERHEAD
            self.event_bus.publish_sync(event)
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
    entity.clear_events()

# AFTER (Simple):
def publish_entity_events(self, entity):
    """Publish entity events - NON-BLOCKING"""
    events = entity.collect_events()

    for event in events:
        # Just publish - queue handles async
        self.event_bus.publish(event)

    entity.clear_events()
```

**Risk Level:** LOW (simplification only)

---

**File 6: `agenthub_main/src/fastmcp/task_management/domain/value_objects/base_entity_id.py` (MODIFY)**

**Add UUID Validation Caching:**
```python
from functools import lru_cache

class BaseEntityId:
    # Existing UUID_PATTERNS...

    @staticmethod
    @lru_cache(maxsize=128)
    def _compile_pattern(pattern: str):
        """Cache compiled regex patterns"""
        return re.compile(pattern)

    def _validate_uuid_format(self, value: str) -> bool:
        """Validate UUID format (with caching)"""
        # Use cached patterns
        for pattern_str in self.UUID_PATTERNS:
            pattern = self._compile_pattern(pattern_str)
            if pattern.match(value):
                return True
        return False
```

**Risk Level:** LOW (optimization only)

**Expected Impact:** 5-10ms reduction in validation overhead

---

#### Day 4: Application Initialization

**File 7: `agenthub_main/src/fastmcp/task_management/application/services/__init__.py` (MODIFY)**

**Add Event System Initialization:**
```python
"""
Application services initialization
Sets up event queue and worker on startup
"""
from ...infrastructure.events import EventQueue, EventWorker
from ...infrastructure.event_bus import get_event_bus
from ...settings import settings

# Global event infrastructure
_event_queue: Optional[EventQueue] = None
_event_worker: Optional[EventWorker] = None


def initialize_event_system():
    """Initialize async event system (call on app startup)"""
    global _event_queue, _event_worker

    if not settings.ENABLE_ASYNC_EVENT_QUEUE:
        logger.info("Async event queue disabled")
        return

    logger.info("Initializing async event system...")

    # Create queue
    _event_queue = EventQueue(max_size=settings.EVENT_QUEUE_MAX_SIZE)

    # Create worker
    event_bus = get_event_bus()
    _event_worker = EventWorker(
        queue=_event_queue,
        event_bus=event_bus,
        shutdown_timeout=settings.EVENT_WORKER_SHUTDOWN_TIMEOUT
    )

    # Connect queue to event bus
    event_bus.set_event_queue(_event_queue)

    # Start worker
    _event_worker.start()

    logger.info("Async event system initialized")


def shutdown_event_system():
    """Shutdown event system gracefully (call on app shutdown)"""
    global _event_queue, _event_worker

    if _event_worker:
        logger.info("Shutting down event worker...")
        _event_worker.stop()

    logger.info("Event system shutdown complete")


def get_event_metrics():
    """Get event system metrics for monitoring"""
    if not _event_queue or not _event_worker:
        return {"enabled": False}

    return {
        "enabled": True,
        "queue": _event_queue.metrics(),
        "worker": _event_worker.metrics()
    }
```

**Risk Level:** LOW

---

**File 8: `agenthub_main/src/fastmcp/server/mcp_entry_point.py` (MODIFY)**

**Add Startup/Shutdown Hooks:**
```python
from ..task_management.application.services import (
    initialize_event_system,
    shutdown_event_system
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan (startup/shutdown)"""
    # Startup
    logger.info("Application starting...")
    initialize_event_system()  # ADD THIS

    yield

    # Shutdown
    logger.info("Application shutting down...")
    shutdown_event_system()  # ADD THIS

app = FastAPI(lifespan=lifespan)
```

**Risk Level:** LOW

---

#### Day 5: Testing & Validation

**File 9: `agenthub_main/src/tests/performance/test_event_system_performance.py` (NEW)**

**Performance Test Suite:**
```python
"""
Performance tests for event system
Validates async event queue performance improvements
"""
import pytest
import time
from unittest.mock import Mock

from fastmcp.task_management.infrastructure.events import EventQueue, EventWorker
from fastmcp.task_management.infrastructure.event_bus import EventBus
from fastmcp.task_management.domain.events.task_events import TaskCreatedEvent


class TestEventSystemPerformance:

    def test_event_publishing_latency_baseline(self):
        """
        Test: Event publishing latency
        Baseline: <5ms per event (queue put)
        """
        queue = EventQueue()
        event_bus = EventBus()
        event_bus.set_event_queue(queue)

        event = TaskCreatedEvent(task_id="test", title="Test")

        start = time.perf_counter()
        for _ in range(100):
            event_bus.publish(event)
        end = time.perf_counter()

        avg_latency_ms = ((end - start) / 100) * 1000

        assert avg_latency_ms < 5.0, \
            f"Event publishing too slow: {avg_latency_ms:.2f}ms (target: <5ms)"

    def test_event_processing_throughput(self):
        """
        Test: Event processing throughput
        Target: 100+ events/second
        """
        queue = EventQueue()
        event_bus = EventBus()
        handler = Mock()
        event_bus.register_handler("task.created", handler)

        worker = EventWorker(queue, event_bus)
        worker.start()

        try:
            # Queue 100 events
            events = [
                TaskCreatedEvent(task_id=f"task_{i}", title=f"Task {i}")
                for i in range(100)
            ]

            start = time.perf_counter()
            for event in events:
                queue.put(event)

            # Wait for processing
            while not queue.is_empty():
                time.sleep(0.01)

            end = time.perf_counter()

            throughput = 100 / (end - start)

            assert throughput > 100, \
                f"Throughput too low: {throughput:.1f} events/s (target: >100/s)"

            assert handler.execute.call_count == 100

        finally:
            worker.stop()

    def test_task_creation_end_to_end_performance(self):
        """
        Test: Complete task creation with events
        Target: <30ms per task (down from 150ms)
        """
        # This will be implemented with full integration test
        # Requires: database, facades, repositories
        pass

    def test_concurrent_event_publishing(self):
        """
        Test: Concurrent event publishing
        Validates thread safety and no blocking
        """
        import threading

        queue = EventQueue()
        event_bus = EventBus()
        event_bus.set_event_queue(queue)

        def publish_events(count: int):
            for i in range(count):
                event = TaskCreatedEvent(task_id=f"task_{i}", title=f"Task {i}")
                event_bus.publish(event)

        threads = [
            threading.Thread(target=publish_events, args=(100,))
            for _ in range(10)
        ]

        start = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        end = time.perf_counter()

        # 1000 events published concurrently
        total_time_ms = (end - start) * 1000

        # Should complete quickly (no blocking)
        assert total_time_ms < 100, \
            f"Concurrent publishing too slow: {total_time_ms:.1f}ms"

        # All events queued
        assert queue.size() == 1000
```

**Risk Level:** LOW

---

### Week 2: Secondary Optimizations

#### Database Query Optimization

**File 10: `agenthub_main/src/fastmcp/task_management/infrastructure/repositories/orm/task_repository.py`**

**Changes:**
- Add lazy loading for relationships
- Implement selective eager loading (load related entities only when needed)

```python
# BEFORE (Always eager loads):
def get_by_id(self, task_id: TaskId) -> Optional[Task]:
    orm_task = self.session.query(TaskORM).options(
        joinedload(TaskORM.subtasks),  # Always loads
        joinedload(TaskORM.context),   # Always loads
        joinedload(TaskORM.git_branch) # Always loads
    ).filter(TaskORM.id == str(task_id)).first()

# AFTER (Lazy by default, eager when specified):
def get_by_id(
    self,
    task_id: TaskId,
    include_subtasks: bool = False,
    include_context: bool = False
) -> Optional[Task]:
    query = self.session.query(TaskORM)

    if include_subtasks:
        query = query.options(joinedload(TaskORM.subtasks))
    if include_context:
        query = query.options(joinedload(TaskORM.context))

    orm_task = query.filter(TaskORM.id == str(task_id)).first()
```

**Risk Level:** LOW
**Expected Impact:** 10-20ms reduction for queries not needing relationships

---

### Week 3: Validation & Production Readiness

#### Monitoring Endpoint

**File 11: `agenthub_main/src/fastmcp/server/health.py` (NEW)**

**Implementation:**
```python
"""
Health check endpoints for monitoring
"""
from fastapi import APIRouter
from ..task_management.application.services import get_event_metrics

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/events")
async def event_system_health():
    """
    Event system health check

    Returns:
        - enabled: bool
        - queue_depth: int
        - worker_alive: bool
        - heartbeat_age: float
        - metrics: dict
    """
    metrics = get_event_metrics()

    if not metrics["enabled"]:
        return {
            "status": "disabled",
            "enabled": False
        }

    queue_metrics = metrics["queue"]
    worker_metrics = metrics["worker"]

    # Health checks
    is_healthy = (
        worker_metrics["is_alive"] and
        worker_metrics["heartbeat_age_seconds"] < 30 and
        queue_metrics["queue_depth"] < 5000
    )

    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "enabled": True,
        "queue": queue_metrics,
        "worker": worker_metrics,
        "alerts": _get_alerts(queue_metrics, worker_metrics)
    }


def _get_alerts(queue_metrics, worker_metrics):
    """Generate alerts based on metrics"""
    alerts = []

    if queue_metrics["queue_depth"] > 10000:
        alerts.append({
            "level": "critical",
            "message": "Queue depth exceeded maximum (overflow risk)"
        })
    elif queue_metrics["queue_depth"] > 5000:
        alerts.append({
            "level": "warning",
            "message": "Queue depth elevated (trending toward overflow)"
        })

    if not worker_metrics["is_alive"]:
        alerts.append({
            "level": "critical",
            "message": "Worker thread dead (events not processing)"
        })
    elif worker_metrics["heartbeat_age_seconds"] > 30:
        alerts.append({
            "level": "warning",
            "message": "Worker heartbeat stale (possible hang)"
        })

    if worker_metrics["failure_rate_pct"] > 5:
        alerts.append({
            "level": "warning",
            "message": f"Event failure rate elevated ({worker_metrics['failure_rate_pct']:.1f}%)"
        })

    return alerts
```

**Risk Level:** LOW

---

## Migration Plan

### Phase 1: Preparation (Days 1-2)

**Objectives:**
- Implement core event queue infrastructure
- Add feature flag
- Deploy to dev environment
- Run initial tests

**Steps:**
1. ✅ Implement EventQueue and EventWorker (Day 1)
2. ✅ Update EventBus with feature flag (Day 2)
3. ✅ Add settings and initialization (Day 2)
4. ✅ Deploy to dev with flag OFF
5. ✅ Run smoke tests

**Success Criteria:**
- All tests pass with flag OFF (sync mode)
- No regressions in functionality
- Dev deployment successful

**Rollback Plan:**
- Not needed (no changes active yet)

---

### Phase 2: Dev Testing (Days 3-4)

**Objectives:**
- Enable async events in dev environment
- Validate performance improvements
- Test error handling and edge cases

**Steps:**
1. ✅ Enable flag in dev: `ENABLE_ASYNC_EVENT_QUEUE=true`
2. ✅ Run performance benchmarks
3. ✅ Test concurrent operations
4. ✅ Verify event delivery (100% rate)
5. ✅ Test worker graceful shutdown
6. ✅ Simulate failures (queue overflow, worker crash)

**Success Criteria:**
- 80% latency reduction confirmed
- 100% event delivery rate
- All edge cases handled correctly
- No memory leaks or resource issues

**Rollback Plan:**
- Set flag to false if critical issues
- No data loss (queue drains on shutdown)

---

### Phase 3: Canary Deployment (Days 5-6)

**Objectives:**
- Enable for 10% of production traffic
- Monitor closely for issues
- Validate in production environment

**Implementation:**
```python
# In EventBus.publish():
def publish(self, event: DomainEvent):
    # Gradual rollout: random 10% to async
    if settings.ENABLE_ASYNC_EVENT_QUEUE and self._event_queue:
        if random.random() < settings.ASYNC_EVENT_ROLLOUT_PCT:
            # Async path
            self._event_queue.put(event)
        else:
            # Sync path (existing)
            self._execute_handlers(event)
    else:
        # Sync path
        self._execute_handlers(event)

# Settings:
ASYNC_EVENT_ROLLOUT_PCT: float = 0.10  # 10% initially
```

**Monitoring:**
- Request latency (should drop for 10%)
- Event delivery rate (should be 100%)
- Error rate (should not increase)
- Queue metrics (depth, processing time)

**Success Criteria:**
- No increase in errors
- Latency improves for canary group
- 100% event delivery maintained

**Rollback Plan:**
- Set `ASYNC_EVENT_ROLLOUT_PCT=0.0` for instant rollback
- OR set `ENABLE_ASYNC_EVENT_QUEUE=false` for full rollback

---

### Phase 4: Gradual Rollout (Days 7-9)

**Objectives:**
- Increase rollout percentage incrementally
- Monitor each step
- Reach 100% deployment

**Schedule:**
- Day 7: 25% → Monitor 4 hours
- Day 8: 50% → Monitor 4 hours
- Day 8: 75% → Monitor 4 hours
- Day 9: 100% → Monitor 24 hours

**Monitoring at Each Step:**
```python
# Metrics to track:
{
    "avg_request_latency_ms": {
        "async_path": 28.5,    # Target: <30ms
        "sync_path": 145.2     # Baseline: ~150ms
    },
    "event_delivery_rate": 100.0,  # Target: 100%
    "queue_depth_p95": 45,         # Target: <100
    "worker_uptime_pct": 99.98,    # Target: >99.9%
    "error_rate_pct": 0.02         # Target: <0.1%
}
```

**Success Criteria (Each Step):**
- Request latency: async <30ms, sync ~150ms
- Event delivery: 100%
- Queue depth: <100 (p95)
- Worker uptime: >99.9%
- Error rate: <0.1%

**Rollback Triggers:**
- Error rate increase >50%
- Event loss rate >0.1%
- Queue overflow (depth >10k sustained)
- Worker failures >3 in 1 hour

**Rollback Steps:**
1. Reduce rollout percentage to last known good
2. If issues persist, set to 0% or disable flag
3. Investigate root cause
4. Fix and retry

---

### Phase 5: Full Deployment & Cleanup (Days 10-15)

**Objectives:**
- Confirm 100% success
- Remove old sync code
- Remove feature flags
- Update documentation

**Steps:**
1. ✅ Validate 100% deployment (48 hours monitoring)
2. ✅ Remove old asyncio wrapper code from EventBus
3. ✅ Remove feature flags (always async now)
4. ✅ Remove rollout percentage logic
5. ✅ Update documentation
6. ✅ Knowledge transfer to team

**Files to Clean Up:**
```python
# EventBus: Remove
- publish_sync() method
- _async_publish() method
- All asyncio imports and wrappers

# Settings: Remove (or set default=True permanently)
- ENABLE_ASYNC_EVENT_QUEUE (make always True)
- ASYNC_EVENT_ROLLOUT_PCT (remove)

# EventPublisher: Simplify
- Remove fallback logic
- Always use queue
```

**Final Validation:**
- Load test at scale (1000 tasks/min for 1 hour)
- Verify all metrics within targets
- Document lessons learned
- Create runbook for operations

**Success Criteria:**
- 80% latency reduction achieved and stable
- 100% event delivery confirmed over 48 hours
- Code clean and simplified
- Team trained and documentation complete

---

## Risk & Mitigation

### Risk Matrix

| Risk | Probability | Impact | Severity | Mitigation |
|------|-------------|--------|----------|------------|
| Event Loss | Medium | Critical | HIGH | Persistence + retry + dead letter queue |
| Event Ordering | Low | Medium | MEDIUM | Single FIFO worker + sequence numbers |
| Memory Overflow | Medium | Medium | MEDIUM | Backpressure + alerts + queue limits |
| Worker Failure | Low | High | MEDIUM | Health checks + auto-restart + monitoring |
| Performance Regression | Low | Medium | MEDIUM | Feature flag + gradual rollout + metrics |
| Data Corruption | Very Low | Critical | MEDIUM | Event validation + handler idempotency |

---

### Risk 1: Event Loss

**Scenario:** Worker crashes, events in queue are lost

**Probability:** Medium (worker crashes are possible)

**Impact:** Critical (business logic failures, data inconsistency)

**Mitigation Strategy:**

1. **Event Persistence (Priority 1):**
```python
class EventQueue:
    def put(self, event: DomainEvent, timeout: float = 5.0) -> bool:
        # Persist to disk BEFORE queuing
        self._persist_event(event)

        try:
            self._queue.put(event, block=True, timeout=timeout)
            self._total_enqueued += 1
            return True
        except Full:
            # Event persisted, can be replayed
            logger.error(f"Queue full, event persisted: {event.event_id}")
            return False

    def _persist_event(self, event: DomainEvent):
        """Write event to disk for recovery"""
        event_file = f"{self._persistence_dir}/{event.event_id}.json"
        with open(event_file, 'w') as f:
            json.dump(event.to_dict(), f)
```

2. **At-Least-Once Delivery:**
   - Mark event as "processing" when worker picks it up
   - Mark as "completed" when handler succeeds
   - On startup, re-queue events not marked "completed"

3. **Dead Letter Queue:**
   - Events that fail all retries go to DLQ
   - DLQ table: `event_processing_failures`
   - Manual replay via admin endpoint

4. **Monitoring:**
   - Alert if event processing lag >5 seconds
   - Alert if worker heartbeat stale >30 seconds
   - Dashboard showing event lifecycle

**Validation:**
```python
def test_event_recovery_after_crash():
    queue = EventQueue(persistence_dir="/tmp/events")
    worker = EventWorker(queue, event_bus)
    worker.start()

    # Queue 100 events
    for i in range(100):
        queue.put(TaskCreatedEvent(task_id=f"task_{i}"))

    # Simulate crash
    worker._thread.terminate()  # Hard kill

    # Restart
    new_worker = EventWorker(queue, event_bus)
    new_worker.start()

    # Should recover persisted events
    time.sleep(2)
    assert handler.execute.call_count == 100  # All delivered
```

---

### Risk 2: Event Ordering

**Scenario:** Events processed out of order causing state inconsistencies

**Probability:** Low (single worker maintains FIFO)

**Impact:** Medium (could cause incorrect state transitions)

**Mitigation Strategy:**

1. **FIFO Queue Guarantee:**
   - Use single worker thread (maintains order)
   - Python `queue.Queue` provides FIFO ordering
   - Process events sequentially

2. **Event Sequence Numbers:**
```python
class DomainEvent:
    def __init__(self, ...):
        self.event_id = str(uuid.uuid4())
        self.sequence_number = self._get_next_sequence()
        self.timestamp = datetime.now()

    @staticmethod
    def _get_next_sequence():
        # Global atomic counter
        return _event_sequence_counter.increment()
```

3. **Out-of-Order Detection:**
```python
class EventWorker:
    def _process_event(self, event: DomainEvent):
        # Check if events are in order
        if event.sequence_number != self._last_sequence + 1:
            logger.warning(
                f"Out-of-order event detected: "
                f"expected {self._last_sequence + 1}, "
                f"got {event.sequence_number}"
            )

        self._execute_handlers(event)
        self._last_sequence = event.sequence_number
```

4. **Critical Events (Synchronous):**
   - For events requiring strict ordering, use sync path
   - Example: `TaskStatusChangedEvent` (must be in order)

```python
class EventBus:
    CRITICAL_EVENTS = {
        "task.status_changed",  # Must maintain order
        "task.deleted"          # Must be immediate
    }

    def publish(self, event: DomainEvent):
        if event.event_type in self.CRITICAL_EVENTS:
            # Synchronous for critical events
            self._execute_handlers(event)
        else:
            # Async for non-critical events
            self._event_queue.put(event)
```

**Validation:**
```python
def test_event_ordering():
    queue = EventQueue()
    worker = EventWorker(queue, event_bus)
    worker.start()

    processed_order = []

    def track_order(event):
        processed_order.append(event.sequence_number)

    handler = Mock(side_effect=track_order)
    event_bus.register_handler("test", handler)

    # Queue 100 events rapidly
    for i in range(100):
        queue.put(TestEvent(sequence_number=i))

    # Wait for processing
    while not queue.is_empty():
        time.sleep(0.01)

    worker.stop()

    # Verify FIFO order maintained
    assert processed_order == list(range(100))
```

---

### Risk 3: Memory Overflow

**Scenario:** Queue grows unbounded under heavy load

**Probability:** Medium (traffic spikes are common)

**Impact:** Medium (memory exhaustion, OOM killer)

**Mitigation Strategy:**

1. **Queue Size Limits:**
   - Max size: 10,000 events
   - Backpressure: block publisher if full
   - Alert at 50% (5,000 events)

2. **Backpressure Mechanism:**
```python
class EventQueue:
    def put(self, event: DomainEvent, timeout: float = 5.0) -> bool:
        try:
            # Will block if queue full (backpressure)
            self._queue.put(event, block=True, timeout=timeout)
            return True
        except Full:
            # Alert and drop (or fallback to sync)
            logger.critical(
                f"Event queue full ({self._max_size}). "
                f"Applying backpressure."
            )
            # Fallback: process synchronously
            self._sync_fallback(event)
            return False
```

3. **Monitoring & Alerts:**
```python
def monitor_queue_depth():
    metrics = get_event_metrics()
    depth = metrics["queue"]["queue_depth"]
    max_size = metrics["queue"]["max_size"]

    if depth > max_size * 0.8:
        alert(
            level="warning",
            message=f"Queue at {depth}/{max_size} (80% full)"
        )

    if depth >= max_size:
        alert(
            level="critical",
            message=f"Queue full! Backpressure active."
        )
```

4. **Auto-Scaling Workers (Future):**
   - Start additional workers if queue > 1000
   - Scale down if queue < 100 for 5 minutes
   - Max 10 workers (prevent resource exhaustion)

**Validation:**
```python
def test_queue_backpressure():
    queue = EventQueue(max_size=10)

    # Fill queue
    for i in range(10):
        assert queue.put(TestEvent()) == True

    # Queue full - should timeout
    start = time.time()
    result = queue.put(TestEvent(), timeout=1.0)
    elapsed = time.time() - start

    assert result == False  # Failed to enqueue
    assert elapsed >= 1.0   # Blocked for timeout period
    assert queue.size() == 10  # Queue still full
```

---

### Risk 4: Worker Thread Failure

**Scenario:** Worker thread crashes and stops processing

**Probability:** Low (but impacts are severe)

**Impact:** High (no events processed, system stalls)

**Mitigation Strategy:**

1. **Health Monitoring:**
```python
class EventWorker:
    def _run(self):
        while not self._stop_flag:
            try:
                # Update heartbeat
                self._last_heartbeat = datetime.now()

                # Process events...

            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                # DON'T exit - continue processing
                time.sleep(1)
```

2. **Watchdog & Auto-Restart:**
```python
class EventWorkerSupervisor:
    """Monitors worker and restarts if dead"""

    def __init__(self, worker: EventWorker):
        self._worker = worker
        self._check_thread = Thread(target=self._monitor, daemon=True)
        self._check_thread.start()

    def _monitor(self):
        while True:
            time.sleep(10)  # Check every 10 seconds

            if not self._worker.is_alive():
                logger.critical("Worker dead! Restarting...")
                self._worker.start()

            elif self._worker.heartbeat_age() > 30:
                logger.critical("Worker heartbeat stale! Restarting...")
                self._worker.stop()
                self._worker.start()
```

3. **Health Check Endpoint:**
```python
@app.get("/health/events")
async def event_health():
    metrics = get_event_metrics()
    worker = metrics["worker"]

    if not worker["is_alive"]:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "reason": "worker_dead"}
        )

    if worker["heartbeat_age_seconds"] > 30:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "reason": "worker_stale"}
        )

    return {"status": "healthy", "metrics": metrics}
```

4. **Alerting:**
   - PagerDuty alert if worker dead >1 minute
   - Slack alert if heartbeat stale >30 seconds
   - Dashboard showing worker uptime %

**Validation:**
```python
def test_worker_auto_restart():
    worker = EventWorker(queue, event_bus)
    supervisor = EventWorkerSupervisor(worker)

    worker.start()
    assert worker.is_alive()

    # Simulate crash
    worker._thread.terminate()
    time.sleep(0.5)
    assert not worker.is_alive()

    # Supervisor should restart
    time.sleep(11)  # Wait for check cycle
    assert worker.is_alive()
```

---

### Risk 5: Performance Regression

**Scenario:** New system doesn't improve performance as expected

**Probability:** Low (architecture is sound)

**Impact:** Medium (wasted effort, still slow)

**Mitigation Strategy:**

1. **Feature Flag (Instant Rollback):**
   - One line change to disable: `ENABLE_ASYNC_EVENT_QUEUE=false`
   - System reverts to sync mode immediately
   - No data loss, no downtime

2. **Gradual Rollout:**
   - 10% → 25% → 50% → 75% → 100%
   - Monitor each step for 4-8 hours
   - Roll back if metrics worsen

3. **Performance Benchmarks:**
```python
# Run BEFORE and AFTER deployment
def benchmark_task_creation():
    times = []
    for _ in range(1000):
        start = time.perf_counter()
        facade.create_task(...)
        end = time.perf_counter()
        times.append((end - start) * 1000)

    return {
        "avg_ms": statistics.mean(times),
        "p50_ms": statistics.median(times),
        "p95_ms": statistics.quantiles(times, n=20)[18],
        "p99_ms": statistics.quantiles(times, n=100)[98]
    }

# Target (after optimization):
{
    "avg_ms": 28.5,   # <30ms
    "p50_ms": 25.0,   # <30ms
    "p95_ms": 45.0,   # <50ms
    "p99_ms": 65.0    # <100ms
}

# Baseline (before optimization):
{
    "avg_ms": 147.3,
    "p50_ms": 135.0,
    "p95_ms": 245.0,
    "p99_ms": 380.0
}
```

4. **Success Criteria (Go/No-Go):**
   - ✅ GO: Latency reduced >70%
   - ✅ GO: Event delivery rate 100%
   - ❌ NO-GO: Latency reduced <50% → investigate
   - ❌ NO-GO: Event loss >0.1% → rollback

**Rollback Decision Tree:**
```
Performance Validation:
├─ Latency reduced >70%?
│  ├─ YES → Continue rollout
│  └─ NO → Is it >50%?
│     ├─ YES → Investigate, partial success
│     └─ NO → ROLLBACK (failed)
│
├─ Event delivery 100%?
│  ├─ YES → Continue
│  └─ NO → IMMEDIATE ROLLBACK (critical)
│
├─ Error rate increased?
│  ├─ NO → Continue
│  └─ YES → By how much?
│     ├─ <25% → Monitor, acceptable
│     └─ >25% → ROLLBACK (unacceptable)
```

---

## Testing & Validation

### Test Strategy Overview

**Test Pyramid:**
```
        /\
       /  \
      / E2E \  ← 10% (Integration + performance)
     /      \
    /  INTE  \  ← 30% (Component integration)
   /  GRATION \
  /            \
 /     UNIT     \  ← 60% (Isolated components)
/________________\
```

---

### Unit Tests (60% of tests)

**Test Coverage Requirements:**
- EventQueue: 95% coverage
- EventWorker: 95% coverage
- EventBus: 90% coverage
- Event handlers: 85% coverage

**File: `tests/unit/infrastructure/events/test_event_queue.py`**

```python
"""Unit tests for EventQueue"""
import pytest
from queue import Full
from fastmcp.task_management.infrastructure.events import EventQueue


class TestEventQueue:

    def test_put_and_get(self):
        """Test basic put/get operations"""
        queue = EventQueue(max_size=100)
        event = create_test_event()

        assert queue.put(event) == True
        assert queue.size() == 1
        assert queue.get() == event
        assert queue.is_empty() == True

    def test_fifo_ordering(self):
        """Test FIFO ordering is maintained"""
        queue = EventQueue()
        events = [create_test_event(id=i) for i in range(10)]

        for event in events:
            queue.put(event)

        retrieved = []
        while not queue.is_empty():
            retrieved.append(queue.get())

        assert retrieved == events

    def test_max_size_enforcement(self):
        """Test queue max size is enforced"""
        queue = EventQueue(max_size=5)

        # Fill queue
        for i in range(5):
            assert queue.put(create_test_event()) == True

        # Next put should fail (timeout)
        assert queue.put(create_test_event(), timeout=0.1) == False
        assert queue.metrics()["total_dropped"] == 1

    def test_backpressure_blocking(self):
        """Test backpressure blocks publisher"""
        import threading
        import time

        queue = EventQueue(max_size=2)
        queue.put(create_test_event())
        queue.put(create_test_event())

        # Queue full
        assert queue.size() == 2

        # This should block
        blocked = False
        def try_put():
            nonlocal blocked
            blocked = True
            queue.put(create_test_event(), timeout=2.0)

        thread = threading.Thread(target=try_put)
        thread.start()

        time.sleep(0.5)
        assert blocked == True  # Thread blocked
        assert thread.is_alive() == True  # Still waiting

        # Consume one event (unblock)
        queue.get()
        thread.join(timeout=3)
        assert not thread.is_alive()  # Completed

    def test_metrics_tracking(self):
        """Test metrics are tracked correctly"""
        queue = EventQueue(max_size=10)

        # Enqueue 3
        for i in range(3):
            queue.put(create_test_event())

        # Dequeue 1
        queue.get()

        # Try to overflow
        for i in range(8):
            queue.put(create_test_event())
        queue.put(create_test_event(), timeout=0.1)  # Dropped

        metrics = queue.metrics()
        assert metrics["total_enqueued"] == 11
        assert metrics["total_dequeued"] == 1
        assert metrics["total_dropped"] == 1
        assert metrics["queue_depth"] == 10
        assert metrics["utilization_pct"] == 100.0
```

**File: `tests/unit/infrastructure/events/test_event_worker.py`**

```python
"""Unit tests for EventWorker"""
import pytest
import time
from unittest.mock import Mock, patch
from fastmcp.task_management.infrastructure.events import EventQueue, EventWorker


class TestEventWorker:

    def test_worker_starts_and_stops(self):
        """Test worker lifecycle"""
        queue = EventQueue()
        event_bus = Mock()
        worker = EventWorker(queue, event_bus)

        # Not running initially
        assert worker.is_alive() == False

        # Start
        worker.start()
        assert worker.is_alive() == True

        # Stop
        worker.stop()
        assert worker.is_alive() == False

    def test_worker_processes_events(self):
        """Test worker processes queued events"""
        queue = EventQueue()
        event_bus = Mock()
        worker = EventWorker(queue, event_bus)

        worker.start()

        # Queue 3 events
        events = [create_test_event(id=i) for i in range(3)]
        for event in events:
            queue.put(event)

        # Wait for processing
        time.sleep(0.5)

        # Verify all processed
        assert event_bus._execute_handlers.call_count == 3
        for event in events:
            event_bus._execute_handlers.assert_any_call(event)

        worker.stop()

    def test_worker_retry_on_failure(self):
        """Test worker retries failed events"""
        queue = EventQueue()
        event_bus = Mock()

        # First 2 calls fail, 3rd succeeds
        event_bus._execute_handlers.side_effect = [
            Exception("Fail 1"),
            Exception("Fail 2"),
            None  # Success
        ]

        worker = EventWorker(queue, event_bus)
        worker.start()

        event = create_test_event()
        queue.put(event)

        # Wait for retries
        time.sleep(3)

        # Should have called 3 times (2 retries)
        assert event_bus._execute_handlers.call_count == 3
        assert worker.metrics()["events_processed"] == 1
        assert worker.metrics()["events_failed"] == 0

        worker.stop()

    def test_worker_final_failure_handling(self):
        """Test worker handles final failure correctly"""
        queue = EventQueue()
        event_bus = Mock()

        # Always fail
        event_bus._execute_handlers.side_effect = Exception("Always fail")

        worker = EventWorker(queue, event_bus)
        worker.start()

        event = create_test_event()
        queue.put(event)

        # Wait for all retries (5 attempts)
        time.sleep(10)

        # Should have tried 5 times
        assert event_bus._execute_handlers.call_count == 5
        assert worker.metrics()["events_failed"] == 1

        worker.stop()

    def test_worker_graceful_shutdown(self):
        """Test worker drains queue on shutdown"""
        queue = EventQueue()
        event_bus = Mock()
        worker = EventWorker(queue, event_bus, shutdown_timeout=5)

        worker.start()

        # Queue 10 events
        for i in range(10):
            queue.put(create_test_event(id=i))

        # Stop immediately (while events in queue)
        worker.stop()

        # All events should be processed
        assert event_bus._execute_handlers.call_count == 10
        assert queue.is_empty() == True

    def test_worker_heartbeat(self):
        """Test worker heartbeat updates"""
        queue = EventQueue()
        event_bus = Mock()
        worker = EventWorker(queue, event_bus)

        worker.start()

        time.sleep(0.5)
        age1 = worker.heartbeat_age()
        assert age1 < 1.0

        time.sleep(1)
        age2 = worker.heartbeat_age()
        assert age2 < 2.0

        worker.stop()
```

---

### Integration Tests (30% of tests)

**File: `tests/integration/infrastructure/test_event_system_integration.py`**

```python
"""Integration tests for complete event system"""
import pytest
import time
from fastmcp.task_management.infrastructure.events import EventQueue, EventWorker
from fastmcp.task_management.infrastructure.event_bus import EventBus
from fastmcp.task_management.domain.events.task_events import TaskCreatedEvent


class TestEventSystemIntegration:

    def test_end_to_end_event_flow(self):
        """Test complete event flow: publish → queue → worker → handler"""
        # Setup
        queue = EventQueue()
        event_bus = EventBus()
        event_bus.set_event_queue(queue)

        handler_calls = []
        def test_handler(event):
            handler_calls.append(event)

        event_bus.register_handler("task.created", test_handler)

        worker = EventWorker(queue, event_bus)
        worker.start()

        # Publish event
        event = TaskCreatedEvent(task_id="test-123", title="Test Task")
        event_bus.publish(event)

        # Wait for processing
        time.sleep(0.5)

        # Verify
        assert len(handler_calls) == 1
        assert handler_calls[0].task_id == "test-123"

        worker.stop()

    def test_multiple_handlers_same_event(self):
        """Test multiple handlers for same event type"""
        queue = EventQueue()
        event_bus = EventBus()
        event_bus.set_event_queue(queue)

        handler1_calls = []
        handler2_calls = []

        event_bus.register_handler("task.created", lambda e: handler1_calls.append(e))
        event_bus.register_handler("task.created", lambda e: handler2_calls.append(e))

        worker = EventWorker(queue, event_bus)
        worker.start()

        event = TaskCreatedEvent(task_id="test", title="Test")
        event_bus.publish(event)

        time.sleep(0.5)

        # Both handlers executed
        assert len(handler1_calls) == 1
        assert len(handler2_calls) == 1

        worker.stop()

    def test_event_system_under_load(self):
        """Test event system handles load correctly"""
        queue = EventQueue(max_size=1000)
        event_bus = EventBus()
        event_bus.set_event_queue(queue)

        processed_count = 0
        def counting_handler(event):
            nonlocal processed_count
            processed_count += 1

        event_bus.register_handler("task.created", counting_handler)

        worker = EventWorker(queue, event_bus)
        worker.start()

        # Publish 500 events rapidly
        for i in range(500):
            event = TaskCreatedEvent(task_id=f"task-{i}", title=f"Task {i}")
            event_bus.publish(event)

        # Wait for all processing
        timeout = 10
        start = time.time()
        while processed_count < 500 and time.time() - start < timeout:
            time.sleep(0.1)

        # Verify all processed
        assert processed_count == 500
        assert queue.is_empty()

        worker.stop()
```

---

### Performance Tests (10% of tests)

**File: `tests/performance/test_event_system_performance.py`**

```python
"""Performance tests for event system"""
import pytest
import time
import statistics
from concurrent.futures import ThreadPoolExecutor

from fastmcp.task_management.infrastructure.events import EventQueue, EventWorker
from fastmcp.task_management.infrastructure.event_bus import EventBus
from fastmcp.task_management.domain.events.task_events import TaskCreatedEvent


class TestEventSystemPerformance:

    @pytest.mark.performance
    def test_publish_latency_baseline(self):
        """
        Test: Event publishing latency
        Target: <5ms per publish (avg)
        """
        queue = EventQueue()
        event_bus = EventBus()
        event_bus.set_event_queue(queue)

        latencies = []

        for i in range(1000):
            event = TaskCreatedEvent(task_id=f"task-{i}", title=f"Task {i}")

            start = time.perf_counter()
            event_bus.publish(event)
            end = time.perf_counter()

            latencies.append((end - start) * 1000)

        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]
        p99_latency = statistics.quantiles(latencies, n=100)[98]

        print(f"\nPublish Latency:")
        print(f"  Avg: {avg_latency:.2f}ms")
        print(f"  P95: {p95_latency:.2f}ms")
        print(f"  P99: {p99_latency:.2f}ms")

        assert avg_latency < 5.0, f"Avg latency too high: {avg_latency:.2f}ms"
        assert p95_latency < 10.0, f"P95 latency too high: {p95_latency:.2f}ms"

    @pytest.mark.performance
    def test_processing_throughput(self):
        """
        Test: Event processing throughput
        Target: >100 events/second
        """
        queue = EventQueue()
        event_bus = EventBus()
        event_bus.set_event_queue(queue)

        processed = []
        def handler(event):
            processed.append(event)

        event_bus.register_handler("task.created", handler)

        worker = EventWorker(queue, event_bus)
        worker.start()

        # Queue 1000 events
        events = [
            TaskCreatedEvent(task_id=f"task-{i}", title=f"Task {i}")
            for i in range(1000)
        ]

        start = time.perf_counter()
        for event in events:
            queue.put(event)

        # Wait for all processing
        while len(processed) < 1000:
            time.sleep(0.01)

        end = time.perf_counter()

        duration = end - start
        throughput = 1000 / duration

        print(f"\nProcessing Throughput:")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Throughput: {throughput:.1f} events/s")

        assert throughput > 100, f"Throughput too low: {throughput:.1f} events/s"

        worker.stop()

    @pytest.mark.performance
    def test_concurrent_publishing(self):
        """
        Test: Concurrent publishing performance
        Target: No blocking, linear scaling
        """
        queue = EventQueue(max_size=10000)
        event_bus = EventBus()
        event_bus.set_event_queue(queue)

        def publish_batch(thread_id: int, count: int):
            latencies = []
            for i in range(count):
                event = TaskCreatedEvent(
                    task_id=f"task-{thread_id}-{i}",
                    title=f"Task {i}"
                )
                start = time.perf_counter()
                event_bus.publish(event)
                end = time.perf_counter()
                latencies.append((end - start) * 1000)
            return latencies

        # 10 threads, 100 events each = 1000 total
        with ThreadPoolExecutor(max_workers=10) as executor:
            start = time.perf_counter()
            futures = [
                executor.submit(publish_batch, i, 100)
                for i in range(10)
            ]
            results = [f.result() for f in futures]
            end = time.perf_counter()

        all_latencies = [lat for batch in results for lat in batch]
        avg_latency = statistics.mean(all_latencies)
        total_time = end - start

        print(f"\nConcurrent Publishing:")
        print(f"  Threads: 10")
        print(f"  Events: 1000")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Avg latency: {avg_latency:.2f}ms")

        # Should complete quickly (no blocking)
        assert total_time < 2.0, f"Concurrent publishing too slow: {total_time:.2f}s"
        assert avg_latency < 10.0, f"High latency under concurrency: {avg_latency:.2f}ms"

    @pytest.mark.performance
    @pytest.mark.slow
    def test_sustained_load_1hour(self):
        """
        Test: Sustained load for 1 hour
        Target: Stable performance, no memory leaks
        """
        pytest.skip("Long-running test - run manually")

        queue = EventQueue()
        event_bus = EventBus()
        event_bus.set_event_queue(queue)

        processed = 0
        def handler(event):
            nonlocal processed
            processed += 1

        event_bus.register_handler("task.created", handler)

        worker = EventWorker(queue, event_bus)
        worker.start()

        # Run for 1 hour at 100 events/min
        duration_seconds = 3600
        events_per_minute = 100
        interval = 60 / events_per_minute

        start = time.time()
        event_count = 0

        while time.time() - start < duration_seconds:
            event = TaskCreatedEvent(
                task_id=f"task-{event_count}",
                title=f"Task {event_count}"
            )
            event_bus.publish(event)
            event_count += 1

            time.sleep(interval)

        # Wait for final processing
        time.sleep(10)

        # Verify
        assert processed == event_count

        # Check memory usage (should be stable)
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        assert memory_mb < 500, f"Memory leak detected: {memory_mb:.1f}MB"

        worker.stop()
```

---

### Load Testing (Production Validation)

**File: `tests/load/locustfile.py`**

```python
"""
Locust load test for event system
Run: locust -f locustfile.py --host=http://localhost:8000
"""
from locust import HttpUser, task, between


class TaskCreationUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(10)
    def create_task(self):
        """Create task (triggers events)"""
        self.client.post("/api/tasks", json={
            "title": "Load test task",
            "description": "Testing event system performance",
            "git_branch_id": "test-branch-id"
        })

    @task(5)
    def update_task(self):
        """Update task (triggers events)"""
        self.client.patch("/api/tasks/test-task-id", json={
            "status": "in_progress"
        })

    @task(1)
    def health_check(self):
        """Check event system health"""
        self.client.get("/health/events")


# Load test scenarios:
# 1. Baseline: 10 users, 5 min → Should handle easily
# 2. Peak load: 100 users, 10 min → Test sustained load
# 3. Spike: 500 users, 2 min → Test queue capacity
# 4. Stress: 1000 users until failure → Find limits

# Success criteria:
# - Baseline: 0% errors, <30ms avg response
# - Peak: <1% errors, <50ms avg response
# - Spike: <5% errors, queue doesn't overflow
# - Stress: Find max capacity, graceful degradation
```

---

## Monitoring & Operations

### Metrics to Track

**System Metrics:**
```python
# Event Queue Metrics
event_queue_depth_current: Gauge  # Current queue size
event_queue_depth_max: Gauge      # Max size configured
event_queue_utilization_pct: Gauge  # (current/max) * 100
event_queue_enqueued_total: Counter  # Total events queued
event_queue_dequeued_total: Counter  # Total events processed
event_queue_dropped_total: Counter   # Total events dropped

# Event Worker Metrics
event_worker_alive: Gauge  # 1=alive, 0=dead
event_worker_heartbeat_age_seconds: Gauge  # Age of last heartbeat
event_worker_processed_total: Counter  # Total events processed
event_worker_failed_total: Counter  # Total events failed
event_worker_failure_rate_pct: Gauge  # (failed/processed) * 100

# Performance Metrics
event_publish_latency_seconds: Histogram  # Time to queue event
event_process_latency_seconds: Histogram  # Time to process event
request_latency_seconds: Histogram  # End-to-end request time
```

**Business Metrics:**
```python
# Task Operations (by event type)
task_created_total: Counter
task_updated_total: Counter
task_completed_total: Counter
task_deleted_total: Counter

# Event Types
events_by_type_total: Counter  # Labels: event_type
```

---

### Logging Strategy

**Log Levels:**
- **DEBUG:** Event lifecycle (queued, processing, completed)
- **INFO:** Worker startup/shutdown, health status
- **WARNING:** Queue depth >50%, worker heartbeat stale, retry attempts
- **ERROR:** Handler failures, queue full, backpressure
- **CRITICAL:** Worker dead, persistent failures, data loss risk

**Structured Logging:**
```python
import structlog

logger = structlog.get_logger()

# Event queued
logger.debug(
    "event_queued",
    event_id=event.event_id,
    event_type=event.event_type,
    queue_depth=queue.size(),
    timestamp=datetime.now().isoformat()
)

# Event processing started
logger.debug(
    "event_processing_started",
    event_id=event.event_id,
    event_type=event.event_type,
    worker_id=worker.id
)

# Event processed successfully
logger.info(
    "event_processed",
    event_id=event.event_id,
    event_type=event.event_type,
    processing_time_ms=elapsed_ms,
    handlers_executed=len(handlers)
)

# Handler failure (with retry)
logger.error(
    "handler_failed",
    event_id=event.event_id,
    event_type=event.event_type,
    handler=handler.__class__.__name__,
    error=str(exception),
    attempt=attempt_number,
    max_attempts=max_attempts,
    will_retry=(attempt < max_attempts)
)

# Worker heartbeat stale
logger.warning(
    "worker_heartbeat_stale",
    worker_id=worker.id,
    heartbeat_age_seconds=age,
    threshold_seconds=30,
    action="checking_thread_status"
)

# Queue depth critical
logger.critical(
    "queue_depth_critical",
    queue_depth=queue.size(),
    max_size=queue.max_size,
    utilization_pct=utilization,
    action="backpressure_active",
    recommendation="scale_workers_or_reduce_load"
)
```

---

### Alerting Rules

**Critical Alerts (Page immediately):**
```yaml
# Worker Dead
alert: EventWorkerDead
expr: event_worker_alive == 0
for: 1m
severity: critical
summary: "Event worker is dead - events not processing"
action: "Auto-restart attempted, manual intervention may be needed"

# Queue Overflow
alert: EventQueueOverflow
expr: event_queue_depth_current >= event_queue_depth_max
for: 30s
severity: critical
summary: "Event queue full - backpressure active, events may be dropped"
action: "Scale workers or reduce event generation"

# High Failure Rate
alert: EventProcessingFailureRateHigh
expr: event_worker_failure_rate_pct > 10
for: 5m
severity: critical
summary: "Event processing failure rate >10%"
action: "Check handler code, database connectivity, external services"
```

**Warning Alerts (Notify, not page):**
```yaml
# Queue Depth Elevated
alert: EventQueueDepthElevated
expr: event_queue_depth_current > (event_queue_depth_max * 0.5)
for: 5m
severity: warning
summary: "Event queue >50% full - trending toward overflow"
action: "Monitor closely, consider scaling workers"

# Worker Heartbeat Stale
alert: EventWorkerHeartbeatStale
expr: event_worker_heartbeat_age_seconds > 30
for: 2m
severity: warning
summary: "Worker heartbeat stale - possible hang"
action: "Check worker thread, may need restart"

# Latency Degradation
alert: EventProcessingLatencyHigh
expr: histogram_quantile(0.95, event_process_latency_seconds) > 0.1
for: 10m
severity: warning
summary: "Event processing p95 latency >100ms"
action: "Check handler performance, database queries"
```

---

### Dashboard Design

**Grafana Dashboard: Event System Health**

```
┌─────────────────────────────────────────────────────────────┐
│                    Event System Health                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Worker    │  │    Queue    │  │  Throughput │         │
│  │   Status    │  │    Depth    │  │  (events/s) │         │
│  │             │  │             │  │             │         │
│  │  ● ALIVE    │  │   245/10k   │  │     127     │         │
│  │             │  │    (2.4%)   │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                               │
│  Request Latency (ms)                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                       │   │
│  │  150 ┤                    ╭╮                         │   │
│  │      │                   ╭╯╰╮ ← Before (sync)        │   │
│  │  100 ┤                  ╭╯  ╰╮                       │   │
│  │      │                 ╭╯    ╰╮                      │   │
│  │   50 ┤╭───────────────╮        ╭──────────────╮     │   │
│  │      ││  ← After      │        │              │     │   │
│  │    0 ┼┴───────────────┴────────┴──────────────┴───  │   │
│  │      └──────────────────────────────────────────     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  Queue Depth Over Time                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 10000 ┤                                             │   │
│  │       │                                             │   │
│  │  5000 ┤         ╭╮                                  │   │
│  │       │        ╭╯╰╮                                 │   │
│  │     0 ┼────────╯──╰─────────────────────────────   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  Event Processing Stats                                      │
│  ┌──────────────────┬──────────────────┬─────────────┐     │
│  │  Total Processed │  Total Failed    │ Failure %   │     │
│  │                  │                  │             │     │
│  │     1,247,394    │       23         │    0.002%   │     │
│  └──────────────────┴──────────────────┴─────────────┘     │
│                                                               │
│  Event Types Breakdown                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  task.created:       45% ████████████              │   │
│  │  task.updated:       30% ████████                  │   │
│  │  task.completed:     15% ████                      │   │
│  │  task.deleted:        5% ██                        │   │
│  │  context.updated:     5% ██                        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

### Runbook: Event System Operations

**Incident Response Procedures:**

#### 1. Worker Dead

**Symptoms:**
- Alert: `EventWorkerDead`
- Health endpoint returns 503
- Events not processing

**Diagnosis:**
```bash
# Check worker status
curl http://localhost:8000/health/events

# Check logs
tail -f logs/app.log | grep "worker"

# Check thread status
ps aux | grep EventWorker
```

**Resolution:**
```python
# Automatic: Supervisor restarts worker
# Manual (if auto-restart failed):
from fastmcp.task_management.application.services import _event_worker

if not _event_worker.is_alive():
    _event_worker.start()
```

**Prevention:**
- Ensure supervisor running
- Monitor heartbeat continuously
- Investigate crash logs

---

#### 2. Queue Overflow

**Symptoms:**
- Alert: `EventQueueOverflow` or `EventQueueDepthElevated`
- Backpressure active
- Slow request times

**Diagnosis:**
```bash
# Check queue depth
curl http://localhost:8000/health/events | jq '.queue.queue_depth'

# Check event generation rate
# (from metrics dashboard)
```

**Resolution:**

**Option A: Scale Workers (Future)**
```python
# Add more worker threads
from fastmcp.task_management.application.services import scale_event_workers

scale_event_workers(count=5)  # Add 5 workers
```

**Option B: Reduce Event Generation**
```python
# Temporarily disable non-critical events
CRITICAL_EVENTS_ONLY = True

def publish(self, event):
    if CRITICAL_EVENTS_ONLY and event.event_type not in CRITICAL_EVENTS:
        return  # Skip non-critical events
    # ... normal flow
```

**Option C: Increase Queue Size**
```bash
# Update setting (requires restart)
export EVENT_QUEUE_MAX_SIZE=50000
```

**Prevention:**
- Monitor queue depth trends
- Alert at 50% capacity
- Plan for traffic spikes

---

#### 3. High Failure Rate

**Symptoms:**
- Alert: `EventProcessingFailureRateHigh`
- Events failing handlers
- Dead letter queue growing

**Diagnosis:**
```bash
# Check failure logs
tail -f logs/app.log | grep "handler_failed"

# Check DLQ
SELECT * FROM event_processing_failures
ORDER BY timestamp DESC
LIMIT 100;

# Identify failing handler
SELECT handler, COUNT(*) as failures
FROM event_processing_failures
GROUP BY handler
ORDER BY failures DESC;
```

**Resolution:**

**Step 1: Identify Root Cause**
- Database connectivity issues?
- External service down?
- Bug in handler code?

**Step 2: Fix Handler or Disable**
```python
# Quick fix: Disable failing handler
event_bus.unregister_handler("task.created", BrokenHandler)

# Or: Fix handler code and redeploy
```

**Step 3: Replay Failed Events**
```python
# Admin endpoint (future)
POST /admin/events/replay
{
    "event_ids": ["uuid1", "uuid2", ...]
}
```

**Prevention:**
- Test handlers thoroughly
- Add circuit breakers for external services
- Monitor handler performance

---

### Operational Checklist

**Daily:**
- [ ] Check event system health dashboard
- [ ] Review queue depth trends
- [ ] Check worker uptime %
- [ ] Review failure rate

**Weekly:**
- [ ] Analyze event processing performance
- [ ] Review dead letter queue
- [ ] Check for memory leaks
- [ ] Update capacity planning

**Monthly:**
- [ ] Load test at scale
- [ ] Review and update alerting thresholds
- [ ] Optimize slow handlers
- [ ] Plan infrastructure scaling

---

## Timeline & Milestones

### Week 1: Critical Implementation (Oct 12-18)

**Day 1 (Mon): Event Queue Foundation**
- ✅ Implement EventQueue class
- ✅ Implement EventWorker class
- ✅ Unit tests for queue and worker
- ✅ Deliverable: Working event queue infrastructure
- **Risk:** LOW - New isolated code

**Day 2 (Tue): Event Bus Refactoring**
- ✅ Update EventBus for async publishing
- ✅ Add feature flag support
- ✅ Integration with EventQueue
- ✅ Deliverable: Refactored EventBus
- **Risk:** MEDIUM - Core component

**Day 3 (Wed): System Integration**
- ✅ Add settings and configuration
- ✅ Update repositories (remove asyncio)
- ✅ Add UUID caching
- ✅ Deliverable: Integrated system
- **Risk:** LOW - Cleanup and optimization

**Day 4 (Thu): Application Startup**
- ✅ Implement startup/shutdown hooks
- ✅ Add health check endpoint
- ✅ Deploy to dev environment
- ✅ Deliverable: Running system in dev
- **Risk:** LOW - Infrastructure setup

**Day 5 (Fri): Testing & Validation**
- ✅ Performance benchmarks
- ✅ Integration tests
- ✅ Dev environment validation
- ✅ Deliverable: Test report
- **Risk:** LOW - Validation phase

**Week 1 Success Criteria:**
- ✅ All tests passing
- ✅ 80% latency reduction in dev
- ✅ 100% event delivery in dev
- ✅ Feature flag working
- ✅ Ready for canary deployment

---

### Week 2: Rollout & Optimization (Oct 19-25)

**Day 6 (Mon): Canary Preparation**
- ✅ Finalize monitoring dashboards
- ✅ Set up alerting rules
- ✅ Deploy to production (flag OFF)
- ✅ Deliverable: Production-ready system
- **Risk:** LOW - Preparation only

**Day 7 (Tue): Canary Deployment (10%)**
- ✅ Enable for 10% of traffic
- ✅ Monitor metrics closely (4 hours)
- ✅ Validate performance improvement
- ✅ Deliverable: Canary success report
- **Risk:** MEDIUM - First production traffic
- **Go/No-Go Decision:** Continue if metrics meet targets

**Day 8 (Wed): Gradual Rollout (25% → 50%)**
- ✅ Increase to 25% (monitor 4 hours)
- ✅ Increase to 50% (monitor 4 hours)
- ✅ Deliverable: Majority traffic migrated
- **Risk:** MEDIUM - Higher traffic volume

**Day 9 (Thu): Full Deployment (75% → 100%)**
- ✅ Increase to 75% (monitor 4 hours)
- ✅ Increase to 100% (monitor overnight)
- ✅ Deliverable: Full migration complete
- **Risk:** MEDIUM - All traffic on new system

**Day 10 (Fri): Secondary Optimizations**
- ✅ Implement lazy loading for queries
- ✅ Selective eager loading
- ✅ Fine-tune event priorities
- ✅ Deliverable: Additional optimizations
- **Risk:** LOW - Incremental improvements

**Week 2 Success Criteria:**
- ✅ 100% deployment achieved
- ✅ 80% latency reduction confirmed
- ✅ Zero event loss
- ✅ No increase in error rate
- ✅ System stable for 24+ hours

---

### Week 3: Validation & Production Readiness (Oct 26-Nov 1)

**Day 11 (Mon): Load Testing**
- ✅ Baseline load test (10 users, 5 min)
- ✅ Peak load test (100 users, 10 min)
- ✅ Spike test (500 users, 2 min)
- ✅ Deliverable: Load test report
- **Risk:** LOW - Testing phase

**Day 12 (Tue): Stress Testing**
- ✅ Stress test (find limits)
- ✅ Sustained load test (1 hour at peak)
- ✅ Chaos engineering (kill worker, overflow queue)
- ✅ Deliverable: Capacity planning data
- **Risk:** LOW - Controlled testing

**Day 13 (Wed): Code Cleanup**
- ✅ Remove old sync event code
- ✅ Remove feature flags
- ✅ Remove rollout logic
- ✅ Code review and refactoring
- ✅ Deliverable: Clean codebase
- **Risk:** LOW - Cleanup only

**Day 14 (Thu): Documentation**
- ✅ Update architecture docs
- ✅ Create runbooks
- ✅ Write knowledge transfer materials
- ✅ Update API documentation
- ✅ Deliverable: Complete documentation
- **Risk:** NONE - Documentation

**Day 15 (Fri): Knowledge Transfer & Sign-off**
- ✅ Team training session
- ✅ Operations handover
- ✅ Final validation
- ✅ Project sign-off
- ✅ Deliverable: Project complete
- **Risk:** NONE - Handover

**Week 3 Success Criteria:**
- ✅ System passes all load tests
- ✅ Capacity limits documented
- ✅ Code clean and maintainable
- ✅ Documentation complete
- ✅ Team trained and confident

---

### Project Milestones

**Milestone 1: Core Implementation (End of Week 1)**
- Event queue infrastructure complete
- EventBus refactored for async
- System working in dev environment
- 80% performance improvement confirmed

**Milestone 2: Production Rollout (End of Week 2)**
- Canary deployment successful
- Full migration to async events
- 100% event delivery maintained
- Additional optimizations applied

**Milestone 3: Production Ready (End of Week 3)**
- System validated at scale
- Code cleaned and optimized
- Documentation complete
- Team trained and operations ready

**Final Success Metrics:**
- ✅ Request latency: <30ms (from 150ms)
- ✅ Throughput: 100+ tasks/second
- ✅ Event delivery: 100% guaranteed
- ✅ System stability: 99.9% uptime
- ✅ Zero data loss
- ✅ Team confidence: High

---

## Appendix

### A. Architecture Decision Record (ADR)

**ADR-001: Async Event Queue for Performance**

**Status:** Approved
**Date:** 2025-10-11
**Decision Makers:** Architecture Team

**Context:**
DDD refactoring introduced 3-5x performance degradation. Primary bottleneck is synchronous event publishing blocking request threads.

**Decision:**
Implement thread-safe event queue with background worker for asynchronous event processing.

**Alternatives Considered:**
1. Fire-and-forget (rejected: no delivery guarantee)
2. Event queue with worker (SELECTED)
3. Hybrid sync/async (rejected: too complex)

**Consequences:**
- **Positive:** 80% latency reduction, better scalability, maintains DDD principles
- **Negative:** Additional complexity, operational overhead
- **Risks:** Event loss (mitigated), ordering issues (mitigated)

**Implementation:** 3 weeks, gradual rollout with feature flags

---

### B. Event System API Reference

**EventQueue:**
```python
class EventQueue:
    def __init__(self, max_size: int = 10000): ...
    def put(self, event: DomainEvent, timeout: float = 5.0) -> bool: ...
    def get(self, timeout: Optional[float] = 1.0) -> Optional[DomainEvent]: ...
    def size(self) -> int: ...
    def is_empty(self) -> bool: ...
    def stop(self): ...
    def metrics(self) -> Dict[str, Any]: ...
```

**EventWorker:**
```python
class EventWorker:
    def __init__(self, queue: EventQueue, event_bus: EventBus, shutdown_timeout: int = 30): ...
    def start(self): ...
    def stop(self): ...
    def is_alive(self) -> bool: ...
    def heartbeat_age(self) -> float: ...
    def metrics(self) -> Dict[str, Any]: ...
```

**EventBus:**
```python
class EventBus:
    def publish(self, event: DomainEvent): ...
    def register_handler(self, event_type: str, handler: EventHandler): ...
    def set_event_queue(self, queue: EventQueue): ...
```

---

### C. Configuration Reference

**Environment Variables:**
```bash
# Event Queue Configuration
ENABLE_ASYNC_EVENT_QUEUE=true          # Enable async event processing
EVENT_QUEUE_MAX_SIZE=10000              # Max queue capacity
EVENT_WORKER_SHUTDOWN_TIMEOUT=30        # Shutdown timeout (seconds)

# Rollout Configuration (temporary)
ASYNC_EVENT_ROLLOUT_PCT=1.0            # 1.0 = 100% async, 0.0 = 0% async

# Monitoring
EVENT_METRICS_ENABLED=true              # Enable Prometheus metrics
EVENT_LOGGING_LEVEL=INFO                # DEBUG, INFO, WARNING, ERROR
```

**Settings Class:**
```python
class Settings(BaseSettings):
    ENABLE_ASYNC_EVENT_QUEUE: bool = False
    EVENT_QUEUE_MAX_SIZE: int = 10000
    EVENT_WORKER_SHUTDOWN_TIMEOUT: int = 30
    ASYNC_EVENT_ROLLOUT_PCT: float = 1.0
    EVENT_METRICS_ENABLED: bool = True
    EVENT_LOGGING_LEVEL: str = "INFO"
```

---

### D. Troubleshooting Guide

**Problem: Events not processing**
- Check: Worker alive? (`/health/events`)
- Check: Queue not full? (metrics)
- Check: Feature flag enabled?
- Solution: Restart worker, check logs

**Problem: Queue overflow**
- Check: Event generation rate too high?
- Check: Worker processing slow?
- Solution: Scale workers or reduce events

**Problem: High latency**
- Check: Queue depth high?
- Check: Handler slow?
- Solution: Optimize handlers, scale workers

**Problem: Event loss**
- Check: Worker crashes?
- Check: Queue persistence enabled?
- Solution: Enable persistence, check DLQ

---

## Conclusion

This implementation plan provides a comprehensive, step-by-step approach to fixing the performance issues introduced during DDD refactoring. By implementing an asynchronous event queue with background worker, we can achieve an **80% reduction in request latency** while maintaining **100% event delivery** and **DDD architectural principles**.

**Key Takeaways:**
- ✅ **Architecture:** Event queue with background worker (industry standard)
- ✅ **Performance:** 150ms → <30ms per request (5x improvement)
- ✅ **Reliability:** 100% event delivery with retry and persistence
- ✅ **Safety:** Feature flags and gradual rollout minimize risk
- ✅ **Observability:** Comprehensive monitoring and alerting

**Next Steps:**
1. Review and approve this plan
2. Assign development resources
3. Begin Week 1 implementation
4. Follow the roadmap with daily standups
5. Measure and report progress against milestones

**Success depends on:**
- Disciplined execution of the plan
- Continuous monitoring during rollout
- Quick response to issues
- Team collaboration and communication

---

**Document Prepared By:** System Architect
**Review Status:** Pending Approval
**Implementation Start:** Upon Approval
**Expected Completion:** 3 weeks from start
