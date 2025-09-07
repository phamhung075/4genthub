"""Git Branch Application Service

Application layer service for git branch lifecycle management.
Separated from project management for better separation of concerns.
"""

from typing import Optional, Dict, Any, List
import logging
from datetime import datetime
import uuid

from ...domain.entities.git_branch import GitBranch
from ...infrastructure.repositories.git_branch_repository_factory import GitBranchRepositoryFactory
from ...infrastructure.repositories.project_repository_factory import get_default_repository

logger = logging.getLogger(__name__)


class GitBranchApplicationService:
    """Application service for git branch lifecycle management"""
    
    def __init__(self, git_branch_repo=None, project_repo=None, user_id: Optional[str] = None):
        self._git_branch_repo = git_branch_repo or GitBranchRepositoryFactory.create()
        self._project_repo = project_repo or get_default_repository()
        self._user_id = user_id  # Store user context
        logger.info("GitBranchApplicationService initialized")
    
    def _get_user_scoped_repository(self, repository: Any) -> Any:
        """Get a user-scoped version of the repository if it supports user context."""
        if not repository:
            return repository
        if hasattr(repository, 'with_user') and self._user_id:
            return repository.with_user(self._user_id)
        elif hasattr(repository, 'user_id'):
            if self._user_id and repository.user_id != self._user_id:
                repo_class = type(repository)
                if hasattr(repository, 'session'):
                    return repo_class(repository.session, user_id=self._user_id)
        return repository
    
    def with_user(self, user_id: str) -> 'GitBranchApplicationService':
        """Create a new service instance scoped to a specific user."""
        return GitBranchApplicationService(self._git_branch_repo, self._project_repo, user_id)
    
    async def create_git_branch(self, project_id: str, git_branch_name: str, git_branch_description: str = "") -> Dict[str, Any]:
        """Create a new git branch within a project"""
        try:
            # Get user-scoped repositories
            project_repo = self._get_user_scoped_repository(self._project_repo)
            git_branch_repo = self._get_user_scoped_repository(self._git_branch_repo)
            
            # Verify project exists
            project = await project_repo.find_by_id(project_id)
            if not project:
                return {"success": False, "error": f"Project {project_id} not found"}
            
            # Check if branch already exists
            existing_branch = await git_branch_repo.find_by_name(project_id, git_branch_name)
            if existing_branch:
                return {"success": False, "error": f"Git branch {git_branch_name} already exists"}
            
            # Create new branch
            git_branch = await git_branch_repo.create_branch(project_id, git_branch_name, git_branch_description)
            
            return {
                "success": True,
                "git_branch": {
                    "id": git_branch.id,
                    "git_branch_id": git_branch.id,
                    "name": git_branch.name,
                    "description": git_branch.description,
                    "project_id": git_branch.project_id,
                    "created_at": git_branch.created_at.isoformat(),
                    "updated_at": git_branch.updated_at.isoformat()
                },
                "message": f"Git branch {git_branch_name} created successfully"
            }
        except Exception as e:
            logger.error(f"Error creating git branch: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_git_branch_by_id(self, git_branch_id: str) -> Dict[str, Any]:
        """Get git branch information by git_branch_id"""
        try:
            # Find branch by ID across all projects
            all_branches = await self._git_branch_repo.find_all()
            
            for branch in all_branches:
                if branch.id == git_branch_id:
                    return {
                        "success": True,
                        "project_id": branch.project_id,
                        "git_branch_name": branch.name,
                        "git_branch": {
                            "id": branch.id,
                            "git_branch_id": branch.id,
                            "name": branch.name,
                            "description": branch.description,
                            "project_id": branch.project_id,
                            "created_at": branch.created_at.isoformat(),
                            "updated_at": branch.updated_at.isoformat()
                        }
                    }
            
            return {"success": False, "error": f"Git branch with git_branch_id {git_branch_id} not found"}
        except Exception as e:
            logger.error(f"Error getting git branch by ID: {e}")
            return {"success": False, "error": str(e)}
    
    async def list_git_branchs(self, project_id: str) -> Dict[str, Any]:
        """List all git branches for a project"""
        try:
            # Verify project exists
            project = await self._project_repo.find_by_id(project_id)
            if not project:
                return {"success": False, "error": f"Project {project_id} not found"}
            
            branches = await self._git_branch_repo.find_all_by_project(project_id)
            
            branch_list = []
            for branch in branches:
                branch_list.append({
                    "id": branch.id,
                    "git_branch_id": branch.id,
                    "name": branch.name,
                    "description": branch.description,
                    "project_id": branch.project_id,
                    "created_at": branch.created_at.isoformat(),
                    "updated_at": branch.updated_at.isoformat()
                })
            
            return {
                "success": True,
                "project_id": project_id,
                "git_branchs": branch_list,
                "count": len(branch_list)
            }
        except Exception as e:
            logger.error(f"Error listing git branches: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_git_branch(self, git_branch_id: str, git_branch_name: Optional[str] = None, git_branch_description: Optional[str] = None) -> Dict[str, Any]:
        """Update an existing git branch"""
        try:
            # Find branch by ID
            all_branches = await self._git_branch_repo.find_all()
            branch = None
            
            for b in all_branches:
                if b.id == git_branch_id:
                    branch = b
                    break
            
            if not branch:
                return {"success": False, "error": f"Git branch with ID {git_branch_id} not found"}
            
            updated_fields = []
            
            if git_branch_name is not None:
                branch.name = git_branch_name
                updated_fields.append("name")
            
            if git_branch_description is not None:
                branch.description = git_branch_description
                updated_fields.append("description")
            
            if not updated_fields:
                return {"success": False, "error": "No fields to update. Provide git_branch_name and/or git_branch_description."}
            
            # Update timestamp
            branch.updated_at = datetime.now()
            
            # Save changes
            await self._git_branch_repo.update(branch)
            
            return {
                "success": True,
                "git_branch": {
                    "id": branch.id,
                    "git_branch_id": branch.id,
                    "name": branch.name,
                    "description": branch.description,
                    "project_id": branch.project_id,
                    "created_at": branch.created_at.isoformat(),
                    "updated_at": branch.updated_at.isoformat()
                },
                "updated_fields": updated_fields,
                "message": f"Git branch {git_branch_id} updated successfully"
            }
        except Exception as e:
            logger.error(f"Error updating git branch: {e}")
            return {"success": False, "error": str(e)}
    
    async def delete_git_branch(self, project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Delete a git branch"""
        try:
            # Check if branch exists
            branch = await self._git_branch_repo.find_by_id(project_id, git_branch_id)
            if not branch:
                return {"success": False, "error": f"Git branch with ID {git_branch_id} not found in project {project_id}"}
            
            # Delete branch
            success = await self._git_branch_repo.delete(project_id, git_branch_id)
            
            if success:
                return {
                    "success": True,
                    "message": f"Git branch {git_branch_id} deleted successfully"
                }
            else:
                return {"success": False, "error": f"Failed to delete git branch {git_branch_id}"}
        except Exception as e:
            logger.error(f"Error deleting git branch: {e}")
            return {"success": False, "error": str(e)}
    
    async def assign_agent_to_branch(self, project_id: str, agent_id: str, git_branch_name: str) -> Dict[str, Any]:
        """Assign an agent to a git branch"""
        try:
            # Find branch by name
            branch = await self._git_branch_repo.find_by_name(project_id, git_branch_name)
            if not branch:
                return {"success": False, "error": f"Git branch {git_branch_name} not found in project {project_id}"}
            
            # Assign agent
            success = await self._git_branch_repo.assign_agent(project_id, branch.id, agent_id)
            
            if success:
                return {
                    "success": True,
                    "message": f"Agent {agent_id} assigned to git branch {git_branch_name}"
                }
            else:
                return {"success": False, "error": f"Failed to assign agent {agent_id} to git branch {git_branch_name}"}
        except Exception as e:
            logger.error(f"Error assigning agent to git branch: {e}")
            return {"success": False, "error": str(e)}
    
    async def unassign_agent_from_branch(self, project_id: str, agent_id: str, git_branch_name: str) -> Dict[str, Any]:
        """Unassign an agent from a git branch"""
        try:
            # Find branch by name
            branch = await self._git_branch_repo.find_by_name(project_id, git_branch_name)
            if not branch:
                return {"success": False, "error": f"Git branch {git_branch_name} not found in project {project_id}"}
            
            # Unassign agent
            success = await self._git_branch_repo.unassign_agent(project_id, branch.id)
            
            if success:
                return {
                    "success": True,
                    "message": f"Agent {agent_id} unassigned from git branch {git_branch_name}"
                }
            else:
                return {"success": False, "error": f"Failed to unassign agent {agent_id} from git branch {git_branch_name}"}
        except Exception as e:
            logger.error(f"Error unassigning agent from git branch: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_branch_statistics(self, project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Get statistics for a specific git branch"""
        try:
            stats = await self._git_branch_repo.get_branch_statistics(project_id, git_branch_id)
            
            if "error" in stats:
                return {"success": False, "error": stats["error"]}
            
            return {
                "success": True,
                "statistics": stats
            }
        except Exception as e:
            logger.error(f"Error getting branch statistics: {e}")
            return {"success": False, "error": str(e)}
    
    async def archive_branch(self, project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Archive a git branch"""
        try:
            success = await self._git_branch_repo.archive_branch(project_id, git_branch_id)
            
            if success:
                return {
                    "success": True,
                    "message": f"Git branch {git_branch_id} archived successfully"
                }
            else:
                return {"success": False, "error": f"Failed to archive git branch {git_branch_id}"}
        except Exception as e:
            logger.error(f"Error archiving git branch: {e}")
            return {"success": False, "error": str(e)}
    
    async def restore_branch(self, project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Restore an archived git branch"""
        try:
            success = await self._git_branch_repo.restore_branch(project_id, git_branch_id)
            
            if success:
                return {
                    "success": True,
                    "message": f"Git branch {git_branch_id} restored successfully"
                }
            else:
                return {"success": False, "error": f"Failed to restore git branch {git_branch_id}"}
        except Exception as e:
            logger.error(f"Error restoring git branch: {e}")
            return {"success": False, "error": str(e)} 