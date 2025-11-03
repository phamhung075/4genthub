"""
Task MCP Controller Services

This module contains service classes for task-specific business logic.
"""

# EnrichmentService removed - was unused dead code with wasteful emoji/metadata bloat
from .hint_service import HintService
from .progress_service import ProgressService

__all__ = ["HintService", "ProgressService"]
