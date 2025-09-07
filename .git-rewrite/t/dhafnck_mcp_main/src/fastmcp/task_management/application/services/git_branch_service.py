"""
Service for managing Git Branches
"""
from typing import Dict, Any, Optional
import logging

from ...domain.repositories.project_repository import ProjectRepository
from ...domain.entities.git_branch import GitBranch
from ...infrastructure.repositories.project_repository_factory import GlobalRepositoryManager
from .unified_context_service import UnifiedContextService

logger = logging.getLogger(__name__)

class GitBranchService:
    def __init__(self, project_repo: Optional[ProjectRepository] = None, 
                 hierarchical_context_service: Optional[UnifiedContextService] = None,
                 user_id: Optional[str] = None):
        self._user_id = user_id  # Store user context
        
        # Create project repository with proper authentication context
        if project_repo:
            self._project_repo = project_repo
        elif user_id:
            # If we have a user_id, get a user-specific repository
            self._project_repo = GlobalRepositoryManager.get_for_user(user_id)
        else:
            # Fallback to default repository (may require compatibility mode)
            self._project_repo = GlobalRepositoryManager.get_default()
        # Initialize git branch repository with user context
        from ...infrastructure.repositories.orm.git_branch_repository import ORMGitBranchRepository
        self._git_branch_repo = ORMGitBranchRepository(user_id=user_id)
        # Initialize hierarchical context service for branch context creation
        if hierarchical_context_service:
            self._hierarchical_context_service = hierarchical_context_service
        else:
            from ..factories.unified_context_facade_factory import UnifiedContextFacadeFactory
            factory = UnifiedContextFacadeFactory()
            self._hierarchical_context_service = factory.create_unified_service()

    def with_user(self, user_id: str) -> 'GitBranchService':
        """Create a new service instance scoped to a specific user."""
        return GitBranchService(self._project_repo, self._hierarchical_context_service, user_id)

    def _get_user_scoped_repository(self, repository):
        """Get user-scoped repository if user_id is available."""
        if self._user_id and hasattr(repository, 'with_user'):
            return repository.with_user(self._user_id)
        return repository

    async def create_git_branch(self, project_id: str, branch_name: str, description: str = "") -> Dict[str, Any]:
        project_repo = self._get_user_scoped_repository(self._project_repo)
        project = await project_repo.find_by_id(project_id)
        if not project:
            return {"success": False, "error": f"Project {project_id} not found"}
            
        # Check if branch already exists using the repository
        git_branch_repo = self._get_user_scoped_repository(self._git_branch_repo)
        existing_branch = await git_branch_repo.find_by_name(project_id, branch_name)
        if existing_branch:
            return {"success": False, "error": f"Git branch '{branch_name}' already exists in project {project_id}"}

        # Create branch using the repository which properly persists it
        git_branch = await git_branch_repo.create_branch(project_id, branch_name, description)
        
        # Create corresponding branch context in hierarchical context system
        try:
            # Prepare branch context data compatible with UnifiedContextService
            branch_context_data = {
                "project_id": project_id,  # Required for BranchContext
                "git_branch_name": branch_name,
                "branch_settings": {
                    "feature_flags": {},
                    "branch_workflow": {},
                    "testing_strategy": {},
                    "deployment_config": {},
                    "collaboration_settings": {},
                    "agent_assignments": {}
                },
                "metadata": {
                    "branch_description": description,
                    "auto_created": True,
                    "created_by": "git_branch_service"
                }
            }
            
            # Use synchronous create_context method
            branch_context_result = self._hierarchical_context_service.create_context(
                level="branch",
                context_id=git_branch.id,
                data=branch_context_data,
                project_id=project_id
            )
            
            if branch_context_result.get("success", False):
                logger.info(f"Successfully created branch context for git branch {git_branch.id} in project {project_id}")
            else:
                logger.warning(f"Branch context creation returned non-success: {branch_context_result.get('error', 'Unknown error')}")
            
        except Exception as context_error:
            # Log the error but don't fail the git branch creation
            logger.error(f"Failed to create branch context for git branch {git_branch.id}: {context_error}")
            # Note: We continue with git branch creation even if context creation fails
            # This ensures backward compatibility and prevents git branch creation from failing
        
        # Also add to project entity for consistency
        project.add_git_branch(git_branch)
        await project_repo.update(project)
        
        # Return format expected by integration test
        return {
            "success": True, 
            "git_branch": {
                "id": git_branch.id,
                "name": git_branch.name,
                "description": git_branch.description,
                "project_id": git_branch.project_id
            },
            "message": f"Git branch '{branch_name}' created successfully"
        }

    async def get_git_branch(self, project_id: str, branch_name: str) -> Dict[str, Any]:
        project_repo = self._get_user_scoped_repository(self._project_repo)
        project = await project_repo.find_by_id(project_id)
        if not project:
            return {"success": False, "error": f"Project {project_id} not found"}
        
        git_branch = project.get_git_branch(branch_name)
        if not git_branch:
            return {"success": False, "error": f"Git branch '{branch_name}' not found in project {project_id}"}
            
        return {"success": True, "git_branch": git_branch.to_dict()}

    async def list_git_branchs(self, project_id: str) -> Dict[str, Any]:
        project_repo = self._get_user_scoped_repository(self._project_repo)
        project = await project_repo.find_by_id(project_id)
        if not project:
            return {"success": False, "error": f"Project {project_id} not found"}
            
        return {"success": True, "git_branchs": [branch.to_dict() for branch in project.git_branchs.values()]}

    async def delete_git_branch(self, git_branch_id: str) -> Dict[str, Any]:
        """Delete a git branch and its associated data."""
        try:
            # First get the branch ID to find the project_id
            git_branch_repo = self._get_user_scoped_repository(self._git_branch_repo)
            result = await git_branch_repo.get_git_branch_by_id(git_branch_id)
            if not result.get("success"):
                return {"success": False, "error": f"Git branch {git_branch_id} not found", "error_code": "NOT_FOUND"}
            
            git_branch_data = result.get("git_branch", {})
            project_id = git_branch_data.get("project_id")
            
            # Delete the git branch using repository
            await git_branch_repo.delete_branch(git_branch_id)
            
            # Delete associated branch context
            try:
                delete_result = self._hierarchical_context_service.delete_context(
                    level="branch",
                    context_id=git_branch_id
                )
                if delete_result.get("success", False):
                    logger.info(f"Successfully deleted branch context for git branch {git_branch_id}")
                else:
                    logger.warning(f"Branch context deletion returned non-success: {delete_result.get('error', 'Unknown error')}")
            except Exception as context_error:
                # Log the error but don't fail the deletion
                logger.warning(f"Failed to delete branch context for git branch {git_branch_id}: {context_error}")
            
            # Remove from project entity
            if project_id:
                project_repo = self._get_user_scoped_repository(self._project_repo)
                project = await project_repo.find_by_id(project_id)
                if project and git_branch_id in project.git_branchs:
                    del project.git_branchs[git_branch_id]
                    await project_repo.update(project)
            
            logger.info(f"Successfully deleted git branch {git_branch_id}")
            
            return {
                "success": True,
                "message": f"Git branch {git_branch_id} deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to delete git branch {git_branch_id}: {e}")
            return {"success": False, "error": f"Failed to delete git branch: {str(e)}", "error_code": "DELETE_FAILED"}

    async def create_missing_branch_context(self, branch_id: str, project_id: str = None, branch_name: str = "", description: str = "") -> Dict[str, Any]:
        """
        Create branch context for existing git branch that doesn't have one.
        This is a helper method to fix existing branches without contexts.
        """
        try:
            # Verify the git branch exists
            git_branch_repo = self._get_user_scoped_repository(self._git_branch_repo)
            git_branch = await git_branch_repo.find_by_id(branch_id)
            if not git_branch:
                return {"success": False, "error": f"Git branch {branch_id} not found"}
            
            # Use branch data from the git branch
            actual_project_id = project_id or git_branch.project_id
            if not branch_name:
                branch_name = git_branch.name
            if not description:
                description = git_branch.description or f"Branch context for {git_branch.name}"
            
            # Create branch context data compatible with UnifiedContextService
            branch_context_data = {
                "project_id": actual_project_id,  # Required for BranchContext
                "git_branch_name": branch_name,
                "branch_settings": {
                    "feature_flags": {},
                    "branch_workflow": {},
                    "testing_strategy": {},
                    "deployment_config": {},
                    "collaboration_settings": {},
                    "agent_assignments": {}
                },
                "metadata": {
                    "branch_description": description,
                    "auto_created": True,
                    "created_by": "git_branch_service_missing_context_fix"
                }
            }
            
            # Create the branch context using synchronous method
            branch_context_result = self._hierarchical_context_service.create_context(
                level="branch",
                context_id=branch_id,
                data=branch_context_data,
                project_id=actual_project_id
            )
            
            if branch_context_result.get("success", False):
                logger.info(f"Successfully created missing branch context for branch {branch_id}")
                return {
                    "success": True,
                    "branch_context": branch_context_result.get("context"),
                    "message": f"Branch context created for branch {branch_id}"
                }
            else:
                logger.error(f"Failed to create missing branch context for branch {branch_id}: {branch_context_result.get('error', 'Unknown error')}")
                return {
                    "success": False,
                    "error": f"Failed to create branch context: {branch_context_result.get('error', 'Unknown error')}"
                }
            
        except Exception as e:
            logger.error(f"Failed to create branch context for branch {branch_id}: {e}")
            return {"success": False, "error": f"Failed to create branch context: {str(e)}"} 