"""
Description Package

This package contains tool descriptions separated from controller logic
for better maintainability and organization.
"""

from .description_loader import description_loader, DescriptionLoader

__all__ = ['description_loader', 'DescriptionLoader']
