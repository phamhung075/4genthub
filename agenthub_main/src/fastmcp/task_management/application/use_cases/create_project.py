"""Create Project Use Case"""

from typing import Dict, Any
from ...domain.entities.project import Project
from ...domain.repositories.project_repository import ProjectRepository


# NOTE: We previously changed this signature and broke consumers that still
# rely on the (project_id, name, description) order.  Restore backward
# compatibility while keeping the convenience of auto-generated IDs when the
# caller does not provide one.

class CreateProjectUseCase:
    """Use case for creating a new project"""

    def __init__(self, project_repository: ProjectRepository):
        self._project_repository = project_repository

    async def execute(
        self,
        project_id: str | None,
        name: str | None = None,
        description: str = "",
    ) -> Dict[str, Any]:
        """Execute the create-project use case.

        This method now supports **two** calling conventions:

        1. Legacy: ``execute(project_id, name, description)``
        2. New   : ``execute(None, name, description)`` — project_id will be auto-generated.
        """

        from uuid import uuid4

        # If the caller uses the new convenience form the first positional
        # argument (project_id) will be ``None`` and *name* will contain the
        # actual project name.
        if name is None:
            # The caller used old signature but passed only (name, description)
            # – treat *project_id* as *name* and generate ID.
            name = project_id  # type: ignore
            project_id = None

        # Ensure we have required fields now.
        if name is None:
            return {"success": False, "error": "Project name is required"}

        # Auto-generate ID when not supplied.
        project_id = project_id or str(uuid4())

        try:
            # Create project entity using the domain factory method
            # This automatically handles timestamps via BaseTimestampEntity
            project = Project.create(
                name=name,
                description=description
            )
            # Override the auto-generated ID if one was provided
            if project_id:
                project.id = project_id

            # Create default main task tree so the project has at least one branch
            project.create_git_branch(
                git_branch_name="main",
                name="main",
                description="Main task tree for the project",
            )

            # Persist via repository (allows duplicate detection etc.)
            await self._project_repository.save(project)
            
            # Auto-create project context for hierarchical context inheritance
            try:
                
                # Use unified context facade for project context creation
                from ...application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory
                from ...domain.constants import validate_user_id
                from ...domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError
                from ....config.auth_config import AuthConfig
                
                # Get user_id from repository context or handle authentication
                # Note: The repository should already be user-scoped by the service layer
                user_id = None
                if hasattr(self._project_repository, 'user_id'):
                    user_context = getattr(self._project_repository, 'user_id', None)
                    
                    # Extract actual user ID string from user context object
                    if user_context is not None:
                        if hasattr(user_context, 'user_id'):
                            user_id = user_context.user_id
                        elif hasattr(user_context, 'id'):
                            user_id = user_context.id
                        elif isinstance(user_context, str):
                            user_id = user_context
                        else:
                            # Try to get user ID directly from the context manager
                            try:
                                from ....auth.middleware.request_context_middleware import get_current_user_id
                                user_id = get_current_user_id()
                            except Exception:
                                pass
                
                if user_id is None:
                    # NO FALLBACKS ALLOWED - user authentication is required
                    raise UserAuthenticationRequiredError("Project context creation")
                
                user_id = validate_user_id(user_id, "Project context creation")
                
                # Create unified context facade factory and ensure global context exists
                factory = UnifiedContextFacadeFactory()
                
                # Auto-create user-scoped global context if it doesn't exist
                # This is required for the hierarchical context system to function properly
                global_context_created = factory.auto_create_global_context(user_id=user_id)
                if not global_context_created:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to ensure global context exists for user {user_id} - proceeding with project context creation")
                
                context_facade = factory.create_facade(
                    user_id=user_id,
                    project_id=project.id
                )
                
                # Create default project context
                # Timestamps handled by context system
                context_data = {
                    "project_id": project.id,
                    "name": project.name,
                    "description": project.description,
                    "configuration": {},
                    "standards": {},
                    "team_settings": {}
                }
                
                context_response = context_facade.create_context(
                    level="project",
                    context_id=project.id,
                    data=context_data
                )
                
                if not context_response["success"]:
                    # Log warning but don't fail project creation
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to create project context for {project.id}: {context_response.get('error')}")
                else:
                    # Log success for debugging
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"Successfully created project context for {project.id}")
                    
            except Exception as context_error:
                # Log context creation error but don't fail project creation
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Error creating project context for {project.id}: {context_error}")

        except ValueError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            # Surface unexpected errors but don't hide detail – tests rely on informative messages.
            return {"success": False, "error": str(e)}

        return {
            "success": True,
            "project": {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat(),
                "git_branchs": list(project.git_branchs.keys()),
            },
        }