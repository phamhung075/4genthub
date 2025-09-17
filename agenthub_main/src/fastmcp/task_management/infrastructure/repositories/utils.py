"""Repository utility functions for shared functionality."""

import os
from typing import Dict, Any


def get_validated_database_type() -> str:
    """
    Get and validate the DATABASE_TYPE environment variable.

    Returns:
        str: The validated database type

    Raises:
        ValueError: If DATABASE_TYPE is not set in environment variables
    """
    database_type = os.getenv('DATABASE_TYPE')
    if not database_type:
        raise ValueError(
            "DATABASE_TYPE environment variable is not set. "
            "Please set DATABASE_TYPE to 'postgresql', 'sqlite', or 'supabase'"
        )
    return database_type


def get_repository_config() -> Dict[str, Any]:
    """
    Get complete repository configuration from environment variables.

    Returns:
        Dict with environment, database_type, redis_enabled, and use_cache settings

    Raises:
        ValueError: If DATABASE_TYPE is not set
    """
    return {
        'environment': os.getenv('ENVIRONMENT', 'production'),
        'database_type': get_validated_database_type(),
        'redis_enabled': os.getenv('REDIS_ENABLED', 'true').lower() == 'true',
        'use_cache': os.getenv('USE_CACHE', 'true').lower() == 'true'
    }