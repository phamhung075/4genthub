"""Project ID Value Object"""

from dataclasses import dataclass

from .base_entity_id import EntityId


@dataclass(frozen=True)
class ProjectId(EntityId):
    """Value object for a Project ID, represented as a UUID.

    The value is stored in canonical UUID format (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx).
    This class ensures that only valid UUIDs are used as project identifiers and normalizes
    them to the standard canonical format for consistency across the system.

    Inherits all functionality from EntityId base class.
    """

    pass
