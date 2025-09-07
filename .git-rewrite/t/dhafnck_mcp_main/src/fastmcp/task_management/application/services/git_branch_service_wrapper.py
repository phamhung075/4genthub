"""Git Branch Service Wrapper

Synchronous wrapper for the async GitBranchApplicationService to maintain
compatibility with the existing synchronous interface patterns.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from .git_branch_application_service import GitBranchApplicationService

logger = logging.getLogger(__name__)


class GitBranchServiceWrapper:
    """Synchronous wrapper for GitBranchApplicationService"""
    
    def __init__(self, git_branch_service: Optional[GitBranchApplicationService] = None):
        self._git_branch_service = git_branch_service or GitBranchApplicationService()
        logger.info("GitBranchServiceWrapper initialized")
    
    def _run_async(self, coro):
        """Run async coroutine in sync context"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an event loop, we need to use a different approach
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result()
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop, create a new one
            return asyncio.run(coro)
    
    def create_git_branch(self, project_id: str, git_branch_name: str, git_branch_description: str = "") -> Dict[str, Any]:
        """Create a new git branch within a project"""
        return self._run_async(
            self._git_branch_service.create_git_branch(project_id, git_branch_name, git_branch_description)
        )
    
    def get_git_branch_by_id(self, git_branch_id: str) -> Dict[str, Any]:
        """Get git branch information by git_branch_id"""
        return self._run_async(
            self._git_branch_service.get_git_branch_by_id(git_branch_id)
        )
    
    def list_git_branchs(self, project_id: str) -> Dict[str, Any]:
        """List all git branches for a project"""
        return self._run_async(
            self._git_branch_service.list_git_branchs(project_id)
        )
    
    def update_git_branch(self, git_branch_id: str, git_branch_name: Optional[str] = None, git_branch_description: Optional[str] = None) -> Dict[str, Any]:
        """Update an existing git branch"""
        return self._run_async(
            self._git_branch_service.update_git_branch(git_branch_id, git_branch_name, git_branch_description)
        )
    
    def delete_git_branch(self, project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Delete a git branch"""
        return self._run_async(
            self._git_branch_service.delete_git_branch(project_id, git_branch_id)
        )
    
    def assign_agent_to_branch(self, project_id: str, agent_id: str, git_branch_name: str) -> Dict[str, Any]:
        """Assign an agent to a git branch"""
        return self._run_async(
            self._git_branch_service.assign_agent_to_branch(project_id, agent_id, git_branch_name)
        )
    
    def unassign_agent_from_branch(self, project_id: str, agent_id: str, git_branch_name: str) -> Dict[str, Any]:
        """Unassign an agent from a git branch"""
        return self._run_async(
            self._git_branch_service.unassign_agent_from_branch(project_id, agent_id, git_branch_name)
        )
    
    def get_branch_statistics(self, project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Get statistics for a specific git branch"""
        return self._run_async(
            self._git_branch_service.get_branch_statistics(project_id, git_branch_id)
        )
    
    def archive_branch(self, project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Archive a git branch"""
        return self._run_async(
            self._git_branch_service.archive_branch(project_id, git_branch_id)
        )
    
    def restore_branch(self, project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Restore an archived git branch"""
        return self._run_async(
            self._git_branch_service.restore_branch(project_id, git_branch_id)
        ) 