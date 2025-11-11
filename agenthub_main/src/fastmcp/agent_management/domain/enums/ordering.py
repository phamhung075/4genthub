"""Ordering enums for repository queries"""

from enum import Enum


class InstanceOrdering(str, Enum):
    """Ordering options for UserAgentInstance queries.

    Following DDD principles, domain layer defines valid business options.
    Infrastructure layer translates these to SQL queries.
    """

    CREATED_DESC = "created_desc"  # Newest first (default for marketplace)
    CREATED_ASC = "created_asc"  # Oldest first
    UPDATED_DESC = "updated_desc"  # Recently updated first
    UPDATED_ASC = "updated_asc"  # Least recently updated first
    NAME_ASC = "name_asc"  # Alphabetical A-Z
    NAME_DESC = "name_desc"  # Alphabetical Z-A
