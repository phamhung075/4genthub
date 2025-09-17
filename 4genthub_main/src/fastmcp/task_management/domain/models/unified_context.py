"""
Unified context module - provides compatibility imports for domain models.

This module provides a compatibility layer for imports that expect
the domain.models.unified_context module structure.
"""

# Import ContextLevel from its actual location
from ..value_objects.context_enums import ContextLevel

# Re-export for compatibility
__all__ = ['ContextLevel']