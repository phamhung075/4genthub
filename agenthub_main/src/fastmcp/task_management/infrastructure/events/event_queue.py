"""
Event Queue Implementation

Thread-safe FIFO queue for asynchronous event processing with backpressure handling.
This implementation follows the performance optimization plan for Week 1, Day 1.

Key Features:
- Thread-safe operations using queue.Queue
- Bounded queue with maxsize=10000 for backpressure
- Comprehensive error handling
- Graceful shutdown support
- Metrics tracking for monitoring
"""

from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class QueueState(Enum):
    """Queue operational states"""
    RUNNING = "running"
    PAUSED = "paused"
    SHUTDOWN = "shutdown"


@dataclass
class QueueMetrics:
    """Queue performance metrics"""
    total_enqueued: int = 0
    total_dequeued: int = 0
    total_dropped: int = 0
    total_errors: int = 0
    current_size: int = 0
    max_size_reached: int = 0
    last_enqueue_time: datetime | None = None
    last_dequeue_time: datetime | None = None


class EventQueue:
    """
    Thread-safe FIFO queue for async event processing.

    This queue implements backpressure by limiting queue size and
    dropping events when capacity is exceeded. It provides comprehensive
    error handling and metrics tracking.

    Attributes:
        maxsize: Maximum queue capacity (default: 10000)
        timeout: Default timeout for blocking operations in seconds
        state: Current operational state of the queue
        metrics: Performance metrics tracking
    """

    def __init__(self, maxsize: int = 10000, timeout: float = 0.1):
        """
        Initialize the event queue.

        Args:
            maxsize: Maximum number of events in queue (backpressure threshold)
            timeout: Default timeout for blocking operations in seconds
        """
        self._queue = queue.Queue(maxsize=maxsize)
        self._maxsize = maxsize
        self._timeout = timeout
        self._state = QueueState.RUNNING
        self._state_lock = threading.Lock()
        self._metrics = QueueMetrics()
        self._metrics_lock = threading.Lock()

        logger.info(
            f"EventQueue initialized with maxsize={maxsize}, timeout={timeout}s"
        )

    def put(self, event: Any, block: bool = True, timeout: float | None = None) -> bool:
        """
        Add an event to the queue.

        Implements backpressure by dropping events when queue is full (non-blocking mode).
        In blocking mode, waits up to timeout seconds for space to become available.

        Args:
            event: The event to enqueue
            block: If True, wait for space; if False, drop event when full
            timeout: Timeout in seconds for blocking mode (None = use default)

        Returns:
            True if event was enqueued successfully, False if dropped

        Raises:
            ValueError: If queue is in SHUTDOWN state
        """
        with self._state_lock:
            if self._state == QueueState.SHUTDOWN:
                raise ValueError("Cannot enqueue events: queue is shutdown")

            if self._state == QueueState.PAUSED:
                logger.warning("Queue is paused, dropping event")
                self._increment_dropped()
                return False

        try:
            # Use provided timeout or default
            wait_timeout = timeout if timeout is not None else self._timeout

            # Attempt to enqueue
            self._queue.put(event, block=block, timeout=wait_timeout if block else None)

            # Update metrics on success
            with self._metrics_lock:
                self._metrics.total_enqueued += 1
                self._metrics.current_size = self._queue.qsize()
                self._metrics.last_enqueue_time = datetime.now(UTC)

                # Track max size reached
                if self._metrics.current_size > self._metrics.max_size_reached:
                    self._metrics.max_size_reached = self._metrics.current_size

            logger.debug(
                f"Event enqueued successfully. Queue size: {self._queue.qsize()}/{self._maxsize}"
            )
            return True

        except queue.Full:
            # Queue is full - backpressure triggered
            logger.warning(
                f"Queue full ({self._maxsize}), dropping event. "
                f"Total dropped: {self._metrics.total_dropped + 1}"
            )
            self._increment_dropped()
            return False

        except Exception as e:
            logger.error(f"Error enqueueing event: {e}", exc_info=True)
            self._increment_errors()
            return False

    def get(self, block: bool = True, timeout: float | None = None) -> Any | None:
        """
        Remove and return an event from the queue.

        Args:
            block: If True, wait for an event; if False, return None if empty
            timeout: Timeout in seconds for blocking mode (None = wait forever)

        Returns:
            The next event from queue, or None if empty (non-blocking) or timeout

        Raises:
            ValueError: If queue is in SHUTDOWN state
        """
        with self._state_lock:
            if self._state == QueueState.SHUTDOWN:
                raise ValueError("Cannot dequeue events: queue is shutdown")

        try:
            event = self._queue.get(block=block, timeout=timeout)

            # Update metrics
            with self._metrics_lock:
                self._metrics.total_dequeued += 1
                self._metrics.current_size = self._queue.qsize()
                self._metrics.last_dequeue_time = datetime.now(UTC)

            logger.debug(
                f"Event dequeued successfully. Queue size: {self._queue.qsize()}/{self._maxsize}"
            )
            return event

        except queue.Empty:
            # Queue is empty
            logger.debug("Queue is empty, no events available")
            return None

        except Exception as e:
            logger.error(f"Error dequeuing event: {e}", exc_info=True)
            self._increment_errors()
            return None

    def put_nowait(self, event: Any) -> bool:
        """
        Add an event to queue without blocking (convenience method).

        Args:
            event: The event to enqueue

        Returns:
            True if enqueued successfully, False if queue is full
        """
        return self.put(event, block=False)

    def get_nowait(self) -> Any | None:
        """
        Get an event from queue without blocking (convenience method).

        Returns:
            The next event, or None if queue is empty
        """
        return self.get(block=False)

    def size(self) -> int:
        """
        Get current queue size.

        Returns:
            Number of events currently in queue
        """
        return self._queue.qsize()

    def is_empty(self) -> bool:
        """
        Check if queue is empty.

        Returns:
            True if queue has no events, False otherwise
        """
        return self._queue.empty()

    def is_full(self) -> bool:
        """
        Check if queue is at capacity.

        Returns:
            True if queue is at maxsize, False otherwise
        """
        return self._queue.full()

    def clear(self) -> int:
        """
        Remove all events from queue.

        Returns:
            Number of events removed
        """
        count = 0
        try:
            while not self._queue.empty():
                self._queue.get_nowait()
                count += 1
        except queue.Empty:
            pass

        logger.info(f"Queue cleared: {count} events removed")

        with self._metrics_lock:
            self._metrics.current_size = 0

        return count

    def pause(self) -> None:
        """
        Pause the queue (new events will be dropped).
        """
        with self._state_lock:
            self._state = QueueState.PAUSED
        logger.info("Queue paused")

    def resume(self) -> None:
        """
        Resume the queue after pause.
        """
        with self._state_lock:
            if self._state == QueueState.PAUSED:
                self._state = QueueState.RUNNING
        logger.info("Queue resumed")

    def shutdown(self, drain: bool = True) -> int:
        """
        Shutdown the queue gracefully.

        Args:
            drain: If True, process remaining events; if False, drop them

        Returns:
            Number of events remaining (dropped if drain=False)
        """
        with self._state_lock:
            self._state = QueueState.SHUTDOWN

        remaining = self.size()

        if not drain and remaining > 0:
            dropped = self.clear()
            logger.warning(f"Queue shutdown without draining: {dropped} events dropped")
            return dropped

        logger.info(f"Queue shutdown: {remaining} events remaining for processing")
        return remaining

    def get_metrics(self) -> dict[str, Any]:
        """
        Get current queue metrics.

        Returns:
            Dictionary containing queue performance metrics
        """
        with self._metrics_lock:
            return {
                "state": self._state.value,
                "current_size": self._metrics.current_size,
                "maxsize": self._maxsize,
                "total_enqueued": self._metrics.total_enqueued,
                "total_dequeued": self._metrics.total_dequeued,
                "total_dropped": self._metrics.total_dropped,
                "total_errors": self._metrics.total_errors,
                "max_size_reached": self._metrics.max_size_reached,
                "utilization_percent": (
                    (self._metrics.current_size / self._maxsize * 100)
                    if self._maxsize > 0 else 0
                ),
                "drop_rate_percent": (
                    (self._metrics.total_dropped / (self._metrics.total_enqueued + self._metrics.total_dropped) * 100)
                    if (self._metrics.total_enqueued + self._metrics.total_dropped) > 0 else 0
                ),
                "last_enqueue_time": (
                    self._metrics.last_enqueue_time.isoformat()
                    if self._metrics.last_enqueue_time else None
                ),
                "last_dequeue_time": (
                    self._metrics.last_dequeue_time.isoformat()
                    if self._metrics.last_dequeue_time else None
                ),
            }

    def reset_metrics(self) -> None:
        """Reset all metrics to initial values."""
        with self._metrics_lock:
            self._metrics = QueueMetrics()
        logger.info("Queue metrics reset")

    def _increment_dropped(self) -> None:
        """Increment dropped events counter."""
        with self._metrics_lock:
            self._metrics.total_dropped += 1

    def _increment_errors(self) -> None:
        """Increment error counter."""
        with self._metrics_lock:
            self._metrics.total_errors += 1

    def __repr__(self) -> str:
        """String representation of queue."""
        return (
            f"EventQueue(state={self._state.value}, "
            f"size={self.size()}/{self._maxsize}, "
            f"enqueued={self._metrics.total_enqueued}, "
            f"dropped={self._metrics.total_dropped})"
        )
