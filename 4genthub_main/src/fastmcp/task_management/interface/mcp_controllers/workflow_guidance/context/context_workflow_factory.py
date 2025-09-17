"""Context Workflow Guidance Factory"""

from .context_workflow_guidance import ContextWorkflowGuidance


class ContextWorkflowFactory:
    """Factory for creating context workflow guidance instances."""
    
    @staticmethod
    def create() -> ContextWorkflowGuidance:
        """Create a new context workflow guidance instance."""
        return ContextWorkflowGuidance()