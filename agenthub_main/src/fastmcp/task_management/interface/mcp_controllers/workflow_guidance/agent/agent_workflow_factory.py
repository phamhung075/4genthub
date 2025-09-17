"""Agent Workflow Guidance Factory

Factory for creating Agent workflow guidance instances.
"""

from .agent_workflow_guidance import AgentWorkflowGuidance


class AgentWorkflowFactory:
    """Factory for creating Agent workflow guidance instances."""
    
    @staticmethod
    def create() -> AgentWorkflowGuidance:
        """Create a new Agent workflow guidance instance."""
        return AgentWorkflowGuidance()