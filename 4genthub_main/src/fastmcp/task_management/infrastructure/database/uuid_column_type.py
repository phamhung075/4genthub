"""
Unified UUID Column Type for Cross-Database Compatibility

This module provides a unified UUID column type that works with both:
- PostgreSQL: Uses native UUID type
- SQLite: Uses VARCHAR(36) with UUID string format

This resolves the schema type mismatches identified in database validation.

ENHANCED: Now supports automatic conversion of string user IDs to deterministic UUIDs
using uuid5 with a namespace, ensuring the ORM model remains the source of truth while
accepting flexible input formats like 'test-user-123'.
"""

from sqlalchemy import String, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql.sqltypes import String as SQLString
import uuid
from typing import Any

# Namespace UUID for deterministic user ID conversion
# This ensures the same string input always generates the same UUID
USER_ID_NAMESPACE = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')


class UnifiedUUID(TypeDecorator):
    """
    UUID column type that adapts to the database engine:
    - PostgreSQL: Uses native UUID type
    - SQLite: Uses VARCHAR(36)
    
    Always stores and returns string representations for consistency.
    """
    
    # Use UUID as the default impl to fix schema validation reporting
    # The load_dialect_impl method will handle the correct database-specific type
    impl = UUID
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        """Load the appropriate column type based on the database dialect."""
        if dialect.name == 'postgresql':
            # Use native UUID type with as_uuid=True to properly match database schema
            # The process_result_value method will handle string conversion
            return dialect.type_descriptor(UUID(as_uuid=True))
        else:
            # SQLite and other databases - use String with VARCHAR(36)
            return dialect.type_descriptor(String(36))
    
    def process_bind_param(self, value: Any, dialect):
        """
        Process value before storing in database.
        
        ENHANCED: Now handles both UUID and string formats by converting
        non-UUID strings to deterministic UUIDs using uuid5.
        Properly handles PostgreSQL native UUID vs SQLite string storage.
        """
        if value is None:
            return None
        
        # Handle UUID objects
        if isinstance(value, uuid.UUID):
            if dialect.name == 'postgresql':
                return value  # PostgreSQL can accept UUID objects directly
            else:
                return str(value)  # SQLite needs string representation
        
        # Handle string inputs
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("Empty string is not a valid UUID or user ID")
            
            try:
                # Try to parse as existing UUID first
                uuid_obj = uuid.UUID(value)
                if dialect.name == 'postgresql':
                    return uuid_obj  # Return UUID object for PostgreSQL
                else:
                    return value  # Return string for SQLite
            except ValueError:
                # Not a valid UUID format - convert string to deterministic UUID
                # This handles cases like 'test-user-123' by converting to valid UUID
                try:
                    converted_uuid = uuid.uuid5(USER_ID_NAMESPACE, value)
                    if dialect.name == 'postgresql':
                        return converted_uuid  # Return UUID object for PostgreSQL
                    else:
                        return str(converted_uuid)  # Return string for SQLite
                except Exception as e:
                    raise ValueError(f"Cannot convert '{value}' to UUID: {str(e)}")
        
        raise TypeError(f"Expected UUID or string, got {type(value)}")
    
    def process_result_value(self, value: Any, dialect):
        """Process value when loading from database."""
        if value is None:
            return None
        
        # Always return string representation for consistency
        if isinstance(value, uuid.UUID):
            return str(value)
        
        return str(value)


def create_uuid_column(primary_key: bool = False, nullable: bool = True):
    """
    Create a UUID column with proper constraints.
    
    Args:
        primary_key: Whether this is a primary key column
        nullable: Whether NULL values are allowed
        
    Returns:
        Configured UnifiedUUID column
    """
    return UnifiedUUID(length=36, primary_key=primary_key, nullable=nullable)


def generate_uuid_string() -> str:
    """Generate a new UUID as a string."""
    return str(uuid.uuid4())


def normalize_user_id_to_uuid(user_id: str) -> str:
    """
    Convert any user ID string to a valid UUID string.
    
    This function provides the same conversion logic used by UnifiedUUID
    for consistent user ID handling throughout the system.
    
    Args:
        user_id: User ID string (can be UUID format or any string like 'test-user-123')
        
    Returns:
        Valid UUID string (deterministic for the same input)
        
    Raises:
        ValueError: If user_id is empty or None
    """
    if not user_id:
        raise ValueError("User ID cannot be empty")
    
    user_id = str(user_id).strip()
    if not user_id:
        raise ValueError("User ID cannot be empty")
    
    try:
        # Try to parse as existing UUID first
        uuid.UUID(user_id)
        return user_id
    except ValueError:
        # Not a valid UUID format - convert string to deterministic UUID
        converted_uuid = uuid.uuid5(USER_ID_NAMESPACE, user_id)
        return str(converted_uuid)