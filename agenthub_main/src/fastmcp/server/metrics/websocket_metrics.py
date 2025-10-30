"""
WebSocket Metrics for Prometheus Monitoring

This module provides comprehensive Prometheus metrics for WebSocket message queue
monitoring, including queue sizes, retry rates, delivery latency, and connection tracking.

Metrics exposed:
- websocket_connections: Active WebSocket connections (Gauge)
- websocket_message_queue_size: Messages queued per user (Gauge)
- websocket_message_retries_total: Total retry attempts (Counter)
- websocket_message_delivery_seconds: Message delivery latency (Histogram)
- websocket_broadcast_duration_seconds: Broadcast operation duration (Histogram)
- websocket_message_queue_max_size: Maximum queue size per user (Gauge)
"""

import logging
from prometheus_client import Counter, Gauge, Histogram
from typing import Optional
import time
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# ============================================================================
# PROMETHEUS METRICS DEFINITIONS
# ============================================================================

# Connection tracking
websocket_connections = Gauge(
    'websocket_connections',
    'Number of active WebSocket connections',
    ['status']  # Labels: 'active', 'authenticated', 'unauthenticated'
)

# Queue size metrics
websocket_message_queue_size = Gauge(
    'websocket_message_queue_size',
    'Current number of queued messages per user',
    ['user_id']  # Label: user_id for per-user tracking
)

websocket_message_queue_max_size = Gauge(
    'websocket_message_queue_max_size',
    'Maximum queue size reached per user',
    ['user_id']
)

# Retry tracking
websocket_message_retries_total = Counter(
    'websocket_message_retries_total',
    'Total number of message retry attempts',
    ['result', 'attempt']  # Labels: result ('success'/'failure'), attempt (1, 2, 3)
)

# Delivery latency
websocket_message_delivery_seconds = Histogram(
    'websocket_message_delivery_seconds',
    'Message delivery time in seconds',
    ['delivery_type']  # Labels: 'immediate', 'retry', 'failed'
)

# Broadcast operation duration
websocket_broadcast_duration_seconds = Histogram(
    'websocket_broadcast_duration_seconds',
    'Time spent broadcasting messages to all connections',
    ['event_type', 'entity_type']  # Labels: event_type, entity_type
)

# ============================================================================
# HELPER FUNCTIONS FOR METRICS COLLECTION
# ============================================================================

def update_connection_count(active: int, authenticated: int, unauthenticated: int) -> None:
    """
    Update connection count metrics.

    Args:
        active: Total active connections
        authenticated: Authenticated connections
        unauthenticated: Unauthenticated connections
    """
    try:
        websocket_connections.labels(status='active').set(active)
        websocket_connections.labels(status='authenticated').set(authenticated)
        websocket_connections.labels(status='unauthenticated').set(unauthenticated)
    except Exception as e:
        logger.warning(f"Failed to update connection metrics: {e}")


def update_queue_size(user_id: str, size: int) -> None:
    """
    Update queue size for a specific user.

    Args:
        user_id: User identifier
        size: Current queue size
    """
    try:
        websocket_message_queue_size.labels(user_id=user_id).set(size)

        # Track maximum queue size
        current_max = websocket_message_queue_max_size.labels(user_id=user_id)._value._value
        if size > current_max:
            websocket_message_queue_max_size.labels(user_id=user_id).set(size)
    except Exception as e:
        logger.warning(f"Failed to update queue size metrics for user {user_id}: {e}")


def clear_queue_metrics(user_id: str) -> None:
    """
    Clear queue metrics when queue is empty.

    Args:
        user_id: User identifier
    """
    try:
        websocket_message_queue_size.labels(user_id=user_id).set(0)
    except Exception as e:
        logger.warning(f"Failed to clear queue metrics for user {user_id}: {e}")


def record_retry_attempt(success: bool, attempt: int) -> None:
    """
    Record a retry attempt.

    Args:
        success: Whether the retry succeeded
        attempt: Retry attempt number (1, 2, 3)
    """
    try:
        result = 'success' if success else 'failure'
        websocket_message_retries_total.labels(
            result=result,
            attempt=str(attempt)
        ).inc()
    except Exception as e:
        logger.warning(f"Failed to record retry attempt: {e}")


def record_delivery_time(delivery_type: str, duration_seconds: float) -> None:
    """
    Record message delivery time.

    Args:
        delivery_type: Type of delivery ('immediate', 'retry', 'failed')
        duration_seconds: Time taken in seconds
    """
    try:
        websocket_message_delivery_seconds.labels(
            delivery_type=delivery_type
        ).observe(duration_seconds)
    except Exception as e:
        logger.warning(f"Failed to record delivery time: {e}")


@contextmanager
def track_broadcast_duration(event_type: str, entity_type: str):
    """
    Context manager to track broadcast operation duration.

    Args:
        event_type: Type of event being broadcast
        entity_type: Type of entity involved

    Usage:
        with track_broadcast_duration('created', 'task'):
            # broadcast code here
            pass
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        try:
            websocket_broadcast_duration_seconds.labels(
                event_type=event_type,
                entity_type=entity_type
            ).observe(duration)
        except Exception as e:
            logger.warning(f"Failed to record broadcast duration: {e}")


# ============================================================================
# METRICS COLLECTION HELPERS
# ============================================================================

def get_metrics_summary() -> dict:
    """
    Get a summary of current metrics for debugging/logging.

    Returns:
        Dictionary with current metric values
    """
    try:
        return {
            "active_connections": websocket_connections.labels(status='active')._value._value,
            "authenticated_connections": websocket_connections.labels(status='authenticated')._value._value,
            "total_retries": sum(
                metric._value._value
                for metric in websocket_message_retries_total.collect()[0].samples
            ),
        }
    except Exception as e:
        logger.warning(f"Failed to generate metrics summary: {e}")
        return {}
