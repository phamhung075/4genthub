"""
Metrics module for Prometheus monitoring

Provides comprehensive metrics for WebSocket operations, message queues,
retry mechanisms, and connection tracking.
"""

from .websocket_metrics import (
    # Metrics
    websocket_connections,
    websocket_message_queue_size,
    websocket_message_queue_max_size,
    websocket_message_retries_total,
    websocket_message_delivery_seconds,
    websocket_broadcast_duration_seconds,
    # Helper functions
    update_connection_count,
    update_queue_size,
    clear_queue_metrics,
    record_retry_attempt,
    record_delivery_time,
    track_broadcast_duration,
    get_metrics_summary,
)

__all__ = [
    # Metrics
    "websocket_connections",
    "websocket_message_queue_size",
    "websocket_message_queue_max_size",
    "websocket_message_retries_total",
    "websocket_message_delivery_seconds",
    "websocket_broadcast_duration_seconds",
    # Helper functions
    "update_connection_count",
    "update_queue_size",
    "clear_queue_metrics",
    "record_retry_attempt",
    "record_delivery_time",
    "track_broadcast_duration",
    "get_metrics_summary",
]
