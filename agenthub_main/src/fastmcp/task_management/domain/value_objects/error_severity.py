"""Error Severity Value Object"""

from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels for prioritizing handling and alerting."""

    LOW = "low"  # Can be retried or ignored
    MEDIUM = "medium"  # Should be logged and monitored
    HIGH = "high"  # Requires immediate attention
    CRITICAL = "critical"  # System-breaking, requires immediate action
