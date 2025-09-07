"""
Project Application Facade
"""
from typing import Dict, Any, Optional

from ..services.project_management_service import ProjectManagementService
from ...infrastructure.repositories.project_repository_factory import GlobalRepositoryManager

class ProjectApplicationFacade:
    def __init__(self, project_service: Optional[ProjectManagementService] = None, user_id: Optional[str] = None):
        if project_service:
            self._project_service = project_service
        else:
            # Create project service with user context if provided
            self._project_service = ProjectManagementService(GlobalRepositoryManager.get_default(), user_id)
    
    def with_user(self, user_id: str) -> 'ProjectApplicationFacade':
        """Create a new facade instance scoped to a specific user."""
        return ProjectApplicationFacade(self._project_service.with_user(user_id))

    async def manage_project(
        self,
        action: str,
        project_id: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        user_id: Optional[str] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Facade method to route project management actions to the service layer."""
        
        if action == "create":
            if not name:
                return {"success": False, "error": "Missing required field: name"}
            # Use user-scoped service if user_id is provided
            service = self._project_service.with_user(user_id) if user_id else self._project_service
            return await service.create_project(name, description or "")
        
        elif action == "get":
            if project_id:
                return await self._project_service.get_project(project_id)
            elif name:
                return await self._project_service.get_project_by_name(name)
            else:
                return {"success": False, "error": "Missing required field: project_id or name"}

        elif action == "list":
            # Always include branches to optimize frontend performance
            return await self._project_service.list_projects(include_branches=True)

        elif action == "update":
            if not project_id:
                return {"success": False, "error": "Missing required field: project_id"}
            return await self._project_service.update_project(project_id, name, description)

        elif action == "project_health_check":
            return await self._project_service.project_health_check(project_id)
            
        elif action == "cleanup_obsolete":
            return await self._project_service.cleanup_obsolete(project_id)
            
        elif action == "validate_integrity":
            return await self._project_service.validate_integrity(project_id)
            
        elif action == "rebalance_agents":
            return await self._project_service.rebalance_agents(project_id)
            
        elif action == "delete":
            if not project_id:
                return {"success": False, "error": "Missing required field: project_id"}
            return await self._project_service.delete_project(project_id, force)
            
        else:
            return {"success": False, "error": f"Invalid action: {action}"}
    
    async def create_project(self, name: str, description: str = "") -> Dict[str, Any]:
        """
        Create a new project with auto-generated UUID.
        
        This method is expected by the TDD tests.
        
        Args:
            name: Project name
            description: Project description
            
        Returns:
            Response with created project
        """
        return await self.manage_project("create", name=name, description=description)
    
    async def get_project(self, project_id: str) -> Dict[str, Any]:
        """
        Get project details by ID.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Response with project details
        """
        return await self.manage_project("get", project_id=project_id) 