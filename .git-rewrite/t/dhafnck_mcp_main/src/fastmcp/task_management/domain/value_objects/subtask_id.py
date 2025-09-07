"""Subtask ID value object"""

import re
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class SubtaskId:
    """Value object for a Subtask ID, represented as a UUID."""

    value: str

    def __post_init__(self):
        """Validate the SubtaskId format after initialization."""
        if not isinstance(self.value, str):
            raise TypeError(f"Subtask ID value must be a string, got {type(self.value)}")

        value_str = self.value.strip()
        if not value_str:
            raise ValueError("Subtask ID cannot be empty or whitespace")

        # UUID (32-char hex or canonical 36-char with hyphens)
        uuid_pattern = r'^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$'
        if not re.match(uuid_pattern, value_str.lower()):
            raise ValueError(
                f"Invalid Subtask ID format: '{value_str}'. Expected canonical UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            )

        # Store in canonical UUID format
        if "-" not in value_str and len(value_str) == 32:
            # Convert hex format to canonical
            hex_value = value_str.lower()
            canonical_value = f"{hex_value[:8]}-{hex_value[8:12]}-{hex_value[12:16]}-{hex_value[16:20]}-{hex_value[20:]}"
            object.__setattr__(self, 'value', canonical_value)
        else:
            # Already in canonical format
            object.__setattr__(self, 'value', value_str.lower())

    @classmethod
    def generate_new(cls) -> "SubtaskId":
        """Generate a new, unique SubtaskId using UUIDv4."""
        return cls(str(uuid.uuid4()))

    def __str__(self) -> str:
        """Return the string representation of the ID."""
        return self.value

    def __repr__(self) -> str:
        """Return a developer-friendly representation."""
        return f"SubtaskId('{self.value}')"

    def __eq__(self, other) -> bool:
        if isinstance(other, SubtaskId):
            return self.value == other.value
        return False

    def __hash__(self) -> int:
        return hash(self.value)
    
    def to_canonical_format(self) -> str:
        """Return the UUID in canonical format with dashes."""
        # Value is already stored in canonical format
        return self.value
    
    def to_hex_format(self) -> str:
        """Return the UUID in hex format without dashes (32 characters)."""
        return self.value.replace('-', '')