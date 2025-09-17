"""Domain Exceptions for Connection Management"""

from .connection_exceptions import (
    ConnectionError,
    ServerNotFoundError,
    ConnectionNotFoundError,
    InvalidServerStatusError,
    InvalidConnectionStatusError,
    ServerHealthCheckFailedError,
    ConnectionHealthCheckFailedError,
    StatusBroadcastError
)

__all__ = [
    "ConnectionError",
    "ServerNotFoundError",
    "ConnectionNotFoundError", 
    "InvalidServerStatusError",
    "InvalidConnectionStatusError",
    "ServerHealthCheckFailedError",
    "ConnectionHealthCheckFailedError",
    "StatusBroadcastError"
] 