"""Context ID Type Detector

This module provides utilities to detect whether a given ID is a project ID, 
git branch ID, or task ID by using the proper application layer services.
"""

import logging
from typing import Tuple, Optional
from ...application.services.context_detection_service import ContextDetectionService

logger = logging.getLogger(__name__)


class ContextIDDetector:
    """Detects the type of a given ID by checking through the application layer"""
    
    def __init__(self):
        """Initialize with context detection service"""
        self._service = ContextDetectionService()
    
    @staticmethod
    def detect_id_type(context_id: str) -> Tuple[str, Optional[str]]:
        """
        Detect whether the given ID is a project, git branch, or task ID.
        
        Args:
            context_id: The ID to check
            
        Returns:
            Tuple of (id_type, project_id) where:
            - id_type is one of: "project", "git_branch", "task", "unknown"
            - project_id is the associated project ID (None for unknown)
        """
        # Create service instance for static method
        service = ContextDetectionService()
        return service.detect_id_type(context_id)
    
    @staticmethod
    def get_context_level_for_id(context_id: str) -> str:
        """
        Get the appropriate context level for a given ID.
        
        Args:
            context_id: The ID to check
            
        Returns:
            The context level: "project", "task", or "task" (default)
        """
        # Create service instance for static method
        service = ContextDetectionService()
        return service.get_context_level_for_id(context_id)