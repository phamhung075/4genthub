"""
Description package for connection management tools.

This package contains tool descriptions separated from controller logic,
following the same architecture pattern as task management.
"""

from .description_loader import connection_description_loader

__all__ = ['connection_description_loader']