"""
Compatibility module for unified context facade factory.

This module provides backward compatibility for tests that expect the
UnifiedContextFacadeFactory to be in the infrastructure.factories package.
"""

# Import the actual factory from its new location
from ...application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory

# Re-export for backward compatibility
__all__ = ['UnifiedContextFacadeFactory']