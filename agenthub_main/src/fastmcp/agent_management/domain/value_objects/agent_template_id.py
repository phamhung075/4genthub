"""AgentTemplate ID Value Object"""

from dataclasses import dataclass

# Import from task_management's base EntityId since it's the single source of truth
from fastmcp.task_management.domain.value_objects.base_entity_id import EntityId


@dataclass(frozen=True)
class AgentTemplateId(EntityId):
    """Value object for an AgentTemplate ID, represented as a UUID.

    The value is stored in canonical UUID format (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx).
    This class ensures that only valid UUIDs are used as agent template identifiers
    and normalizes them to the standard canonical format for consistency across the system.

    Inherits all functionality from EntityId base class including:
    - UUID validation and normalization
    - Factory methods (from_string, generate_new)
    - String/hash operations for use in collections

    Examples:
        >>> template_id = AgentTemplateId.generate_new()
        >>> template_id_from_string = AgentTemplateId.from_string("550e8400-e29b-41d4-a716-446655440000")
    """

    pass
