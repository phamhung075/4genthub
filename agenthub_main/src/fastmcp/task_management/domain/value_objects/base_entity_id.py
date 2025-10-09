"""Abstract Base Class for Entity IDs"""

import uuid
from abc import ABC
from dataclasses import dataclass


@dataclass(frozen=True)
class EntityId(ABC):
    """Abstract base class for all entity IDs represented as UUIDs.

    This class provides common functionality for all entity ID value objects:
    - UUID validation and normalization
    - Canonical format storage (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
    - Common methods for equality, hashing, and string representation
    - Format conversion utilities
    - Factory methods for creation

    Derived classes inherit all functionality and maintain type safety
    (e.g., ProjectId ≠ AgentId even though both are UUIDs).
    """

    value: str

    def __post_init__(self):
        """Validate the entity ID format after initialization."""
        if self.value is None:
            raise ValueError(f"{self.__class__.__name__} cannot be None")

        if not isinstance(self.value, str):
            raise TypeError(
                f"{self.__class__.__name__} value must be a string, got {type(self.value)}"
            )

        value_str = self.value.strip()
        if not value_str:
            raise ValueError(f"{self.__class__.__name__} cannot be empty or whitespace")

        # Validate UUID format using the validation method
        if not self._is_valid_uuid(value_str):
            raise ValueError(
                f"Invalid {self.__class__.__name__} format: '{value_str}'. "
                f"Expected canonical UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            )

        # Normalize to canonical format
        try:
            uuid_obj = uuid.UUID(value_str)
            # Store in canonical format (lowercase with hyphens)
            object.__setattr__(self, 'value', str(uuid_obj))
        except ValueError as e:
            # If UUID parsing fails but validation passed, store as-is
            # (This handles special cases like TaskId hierarchical format)
            object.__setattr__(self, 'value', value_str.lower())

    @staticmethod
    def _is_valid_uuid(value: str) -> bool:
        """Validate if the value is a valid UUID format.

        Can be overridden by subclasses to support additional formats.

        Args:
            value: The string value to validate

        Returns:
            True if the value is a valid UUID, False otherwise
        """
        try:
            uuid.UUID(value)
            return True
        except (ValueError, AttributeError):
            return False

    def __str__(self) -> str:
        """Return the string representation of the ID."""
        return self.value

    def __eq__(self, other):
        """Two EntityIds are equal if they are the same type and have equal values."""
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.value == other.value

    def __hash__(self):
        """Return the hash of the ID's value."""
        return hash(self.value)

    def to_hex_format(self) -> str:
        """Return the ID in hex format (32 chars without dashes)."""
        return self.value.replace('-', '')

    def to_canonical_format(self) -> str:
        """Return the ID in canonical UUID format (with dashes)."""
        return self.value

    @classmethod
    def from_string(cls, value: str):
        """Create an EntityId instance from a string.

        Args:
            value: The string value to create the ID from

        Returns:
            A new instance of the specific EntityId subclass
        """
        return cls(value)

    @classmethod
    def generate_new(cls):
        """Generate a new, unique EntityId using UUIDv4.

        Returns:
            A new instance of the specific EntityId subclass with a unique UUID
        """
        return cls(str(uuid.uuid4()))
