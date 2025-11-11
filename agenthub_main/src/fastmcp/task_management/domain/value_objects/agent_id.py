"""Agent ID Value Object"""

from dataclasses import dataclass

from .base_entity_id import EntityId


@dataclass(frozen=True)
class AgentId(EntityId):
    """Value object for an Agent ID, represented as a UUID.

    The value is stored in canonical UUID format (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx).
    This class ensures that only valid UUIDs are used as agent identifiers and normalizes
    them to the standard canonical format for consistency across the system.

    Inherits all functionality from EntityId base class.
    """

    pass
