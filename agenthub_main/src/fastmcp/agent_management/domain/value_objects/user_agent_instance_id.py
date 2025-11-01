"""UserAgentInstanceId Value Object - Type-safe UUID identifier for user agent instances"""

from dataclasses import dataclass
from fastmcp.task_management.domain.value_objects.base_entity_id import EntityId


@dataclass(frozen=True)
class UserAgentInstanceId(EntityId):
    """Value object for a UserAgentInstance ID, represented as a UUID.

    This provides type safety for user agent instance identifiers throughout the
    agent management domain. Each instance is unique per (user_id, template_id) pair.

    Inherits all functionality from EntityId base class including:
    - UUID validation and normalization to canonical format
    - Factory methods (from_string, generate_new)
    - Equality comparisons and hashing
    - LRU caching for performance

    Examples:
        # Create from string
        instance_id = UserAgentInstanceId.from_string("550e8400-e29b-41d4-a716-446655440001")

        # Generate new
        instance_id = UserAgentInstanceId.generate_new()

        # Use in comparisons
        if instance_id == another_instance_id:
            print("Same instance")
    """
    pass
