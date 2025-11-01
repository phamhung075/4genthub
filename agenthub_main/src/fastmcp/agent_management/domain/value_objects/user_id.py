"""UserId Value Object - Type-safe UUID identifier for users"""

from dataclasses import dataclass
from fastmcp.task_management.domain.value_objects.base_entity_id import EntityId


@dataclass(frozen=True)
class UserId(EntityId):
    """Value object for a User ID, represented as a UUID.

    This provides type safety for user identifiers throughout the agent management
    domain. Inherits all functionality from EntityId base class including:
    - UUID validation and normalization to canonical format
    - Factory methods (from_string, generate_new)
    - Equality comparisons and hashing
    - LRU caching for performance

    Examples:
        # Create from string
        user_id = UserId.from_string("550e8400-e29b-41d4-a716-446655440000")

        # Generate new
        user_id = UserId.generate_new()

        # Use in comparisons
        if user_id == another_user_id:
            print("Same user")
    """
    pass
