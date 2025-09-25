"""Create Git Branch Use Case"""

from typing import Dict, Any
from ...domain.repositories.project_repository import ProjectRepository


class CreateGitBranchUseCase:
    """Use case for creating a new git branch within a project"""
    
    def __init__(self, project_repository: ProjectRepository):
        self._project_repository = project_repository
    
    async def execute(self, project_id: str, git_branch_name: str, branch_name: str, branch_description: str = "") -> Dict[str, Any]:
        """Execute the create git branch use case"""
        
        project = await self._project_repository.find_by_id(project_id)
        
        if not project:
            return {
                "success": False,
                "error": f"Project with ID '{project_id}' not found"
            }
        
        try:
            # Create git branch using domain logic
            git_branch = project.create_git_branch(
                git_branch_name=git_branch_name,
                name=branch_name,
                description=branch_description
            )
            
            # Save updated project
            await self._project_repository.update(project)
            
            # Auto-create branch context for hierarchical context inheritance
            try:
                # Use unified context facade for branch context creation
                from ..factories.unified_context_facade_factory import UnifiedContextFacadeFactory
                from ...domain.constants import validate_user_id
                from ...domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError
                from ....config.auth_config import AuthConfig
                
                # Get user_id from request context or handle authentication
                user_id = None
                try:
                    from flask import request as flask_request
                    user_id = getattr(flask_request, 'user_id', None)
                except (ImportError, RuntimeError):
                    # No Flask context or request not available
                    user_id = None
                
                if user_id is None:
                    # Try fallback authentication through AuthConfig
                    auth_config = AuthConfig()
                    if auth_config.is_default_user_allowed():
                        user_id = auth_config.get_fallback_user_id()
                    else:
                        # NO FALLBACKS ALLOWED - user authentication is required
                        raise UserAuthenticationRequiredError("Branch context creation")
                
                user_id = validate_user_id(user_id, "Branch context creation")
                
                # Create unified context facade
                factory = UnifiedContextFacadeFactory()
                context_facade = factory.create_facade(
                    user_id=user_id,
                    project_id=project.id,
                    git_branch_id=git_branch.id
                )
                
                # Create default branch context
                # Timestamps handled by context system
                context_data = {
                    "branch_id": git_branch.id,
                    "branch_name": git_branch.name,
                    "project_id": project.id,
                    "description": git_branch.description,
                    "workflow_state": {},
                    "branch_settings": {}
                }
                
                context_response = context_facade.create_context(
                    level="branch",
                    context_id=git_branch.id,
                    data=context_data
                )
                
                if not context_response["success"]:
                    # Log warning but don't fail branch creation
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to create branch context for {git_branch.id}: {context_response.get('error')}")
                    
            except Exception as context_error:
                # Log context creation error but don't fail branch creation
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Error creating branch context for {git_branch.id}: {context_error}")
            
            return {
                "success": True,
                "git_branch": {
                    "id": git_branch.id,
                    "name": git_branch.name,
                    "description": git_branch.description,
                    "project_id": git_branch.project_id,
                    "created_at": git_branch.created_at.isoformat(),
                    "task_count": git_branch.get_task_count(),
                    "completed_tasks": git_branch.get_completed_task_count(),
                    "progress": git_branch.get_progress_percentage()
                },
                "message": f"Git branch '{git_branch_name}' created successfully"
            }
        
        except ValueError as e:
            return {
                "success": False,
                "error": str(e)
            }