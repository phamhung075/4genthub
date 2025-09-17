"""Rule Workflow Guidance Factory

Factory for creating Rule workflow guidance instances.
"""

from .rule_workflow_guidance import RuleWorkflowGuidance


class RuleWorkflowFactory:
    """Factory for creating Rule workflow guidance instances."""
    
    @staticmethod
    def create() -> RuleWorkflowGuidance:
        """Create a new Rule workflow guidance instance."""
        return RuleWorkflowGuidance()