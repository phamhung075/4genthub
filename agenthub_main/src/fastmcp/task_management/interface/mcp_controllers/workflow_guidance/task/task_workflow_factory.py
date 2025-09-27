"""Task workflow guidance factory."""

from typing import Dict, Any

from .task_workflow_guidance import TaskWorkflowGuidance
from ..base import WorkflowGuidanceInterface


class TaskWorkflowFactory:
    """Factory for creating task workflow guidance instances."""
    
    @staticmethod
    def create() -> WorkflowGuidanceInterface:
        """
        Create a new task workflow guidance instance.
        
        Returns:
            TaskWorkflowGuidance instance
        """
        return TaskWorkflowGuidance()
    
    @staticmethod
    def create_with_config(config: Dict[str, Any]) -> WorkflowGuidanceInterface:
        """
        Create a task workflow guidance instance with configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Configured TaskWorkflowGuidance instance
        """
        # For now, just return a standard instance
        # In the future, this could use config to customize behavior
        return TaskWorkflowGuidance()