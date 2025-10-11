"""
Progress Percentage Value Object

This value object encapsulates the business rule that progress percentages
must be between 0 and 100 (inclusive). It provides a type-safe way to handle
progress percentage validation throughout the domain.

Following DDD principles, business rules belong in the domain layer, not in
application services or interface controllers.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProgressPercentage:
    """
    Immutable value object representing a progress percentage (0-100).

    This encapsulates the business rule that progress must be within
    the valid range of 0-100 inclusive.

    Attributes:
        value: The percentage value (0-100)

    Raises:
        ValueError: If the percentage is not between 0 and 100
    """

    value: int

    def __post_init__(self):
        """Validate that percentage is within the valid range."""
        if not isinstance(self.value, int):
            raise TypeError(
                f"Progress percentage must be an integer, got {type(self.value).__name__}"
            )

        if not 0 <= self.value <= 100:
            raise ValueError(
                f"Progress percentage must be between 0 and 100, got {self.value}"
            )

    @classmethod
    def from_any(cls, value: any) -> "ProgressPercentage":
        """
        Create ProgressPercentage from any input, attempting type conversion.

        This factory method provides flexible instantiation from various input types
        (int, str, float) while maintaining validation.

        Args:
            value: The value to convert to progress percentage

        Returns:
            ProgressPercentage instance

        Raises:
            TypeError: If value cannot be converted to integer
            ValueError: If value is not between 0 and 100
        """
        if value is None:
            raise ValueError("Progress percentage cannot be None")

        # Handle integer input
        if isinstance(value, int):
            return cls(value)

        # Handle string or float input
        try:
            int_value = int(value)
            return cls(int_value)
        except (ValueError, TypeError) as e:
            raise TypeError(
                f"Cannot convert {type(value).__name__} to progress percentage: {value}"
            ) from e

    def to_int(self) -> int:
        """Get the integer value of the progress percentage."""
        return self.value

    def __str__(self) -> str:
        """String representation of progress percentage."""
        return f"{self.value}%"

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"ProgressPercentage(value={self.value})"

    def __eq__(self, other) -> bool:
        """Compare progress percentages by value."""
        if isinstance(other, ProgressPercentage):
            return self.value == other.value
        if isinstance(other, int):
            return self.value == other
        return False

    def __lt__(self, other) -> bool:
        """Support less-than comparison."""
        if isinstance(other, ProgressPercentage):
            return self.value < other.value
        if isinstance(other, int):
            return self.value < other
        return NotImplemented

    def __le__(self, other) -> bool:
        """Support less-than-or-equal comparison."""
        if isinstance(other, ProgressPercentage):
            return self.value <= other.value
        if isinstance(other, int):
            return self.value <= other
        return NotImplemented

    def __gt__(self, other) -> bool:
        """Support greater-than comparison."""
        if isinstance(other, ProgressPercentage):
            return self.value > other.value
        if isinstance(other, int):
            return self.value > other
        return NotImplemented

    def __ge__(self, other) -> bool:
        """Support greater-than-or-equal comparison."""
        if isinstance(other, ProgressPercentage):
            return self.value >= other.value
        if isinstance(other, int):
            return self.value >= other
        return NotImplemented

    def is_complete(self) -> bool:
        """Check if progress is complete (100%)."""
        return self.value == 100

    def is_not_started(self) -> bool:
        """Check if progress has not started (0%)."""
        return self.value == 0

    def is_in_progress(self) -> bool:
        """Check if progress is in progress (1-99%)."""
        return 0 < self.value < 100
