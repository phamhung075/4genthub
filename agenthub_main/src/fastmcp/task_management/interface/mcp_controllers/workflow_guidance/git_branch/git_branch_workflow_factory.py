"""Git Branch Workflow Guidance Factory

Factory for creating Git Branch workflow guidance instances.
"""

from .git_branch_workflow_guidance import GitBranchWorkflowGuidance


class GitBranchWorkflowFactory:
    """Factory for creating Git Branch workflow guidance instances."""
    
    @staticmethod
    def create() -> GitBranchWorkflowGuidance:
        """Create a new Git Branch workflow guidance instance."""
        return GitBranchWorkflowGuidance()