"""Git Branch ID Value Object"""

from dataclasses import dataclass

from .base_entity_id import EntityId


@dataclass(frozen=True)
class GitBranchId(EntityId):
    """Value object for a Git Branch ID, represented as a UUID.

    The value is stored in canonical UUID format (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx).
    This class ensures that only valid UUIDs are used as git branch identifiers and normalizes
    them to the standard canonical format for consistency across the system.

    Inherits all functionality from EntityId base class.
    """
    pass
