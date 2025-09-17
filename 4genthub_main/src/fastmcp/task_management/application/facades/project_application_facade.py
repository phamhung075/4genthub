"""
Project Application Facade
"""
from typing import Dict, Any, Optional

from ..services.project_management_service import ProjectManagementService
from ...domain.interfaces.repository_factory import IProjectRepositoryFactory
from ...infrastructure.repositories.project_repository_factory import GlobalRepositoryManager

class ProjectApplicationFacade:
    def __init__(self, project_service: Optional[ProjectManagementService] = None, user_id: Optional[str] = None):
        # Store user_id for use in manage_project
        self._user_id = user_id
        
        if project_service:
            self._project_service = project_service
        else:
            # Create project service with user context if provided
            if user_id:
                repository = GlobalRepositoryManager.get_for_user(user_id)
                self._project_service = ProjectManagementService(repository, user_id)
            else:
                # Fallback for backward compatibility - will raise an error if no user_id is provided later
                self._project_service = ProjectManagementService(GlobalRepositoryManager.get_default(), user_id)
    
    def with_user(self, user_id: str) -> 'ProjectApplicationFacade':
        """Create a new facade instance scoped to a specific user."""
        return ProjectApplicationFacade(self._project_service.with_user(user_id), user_id)

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
            # Use user-scoped service - prioritize parameter user_id, fallback to instance user_id
            effective_user_id = user_id or self._user_id
            service = self._project_service.with_user(effective_user_id) if effective_user_id else self._project_service
            return await service.create_project(name, description or "")
        
        elif action == "get":
            if project_id:
                return await self._project_service.get_project(project_id)
            elif name:
                return await self._project_service.get_project_by_name(name)
            else:
                return {"success": False, "error": "Missing required field: project_id or name"}

        elif action == "list":
            # Use user-scoped service - prioritize parameter user_id, fallback to instance user_id
            effective_user_id = user_id or self._user_id
            service = self._project_service.with_user(effective_user_id) if effective_user_id else self._project_service
            # Always include branches to optimize frontend performance
            return await service.list_projects(include_branches=True)

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
    
    async def get_project_by_name(self, name: str) -> Dict[str, Any]:
        """
        Get project details by name.
        
        Args:
            name: Project name
            
        Returns:
            Response with project details
        """
        return await self.manage_project("get", name=name)
    
    async def list_projects(self) -> Dict[str, Any]:
        """
        List all projects.
        
        Returns:
            Response with project list
        """
        return await self.manage_project("list")
    
    async def update_project(self, project_id: str, name: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Update an existing project.
        
        Args:
            project_id: Project identifier
            name: New project name (optional)
            description: New project description (optional)
            
        Returns:
            Response with updated project details
        """
        return await self.manage_project("update", project_id=project_id, name=name, description=description)
    
    async def delete_project(self, project_id: str, force: bool = False) -> Dict[str, Any]:
        """
        Delete a project.
        
        Args:
            project_id: Project identifier
            force: Force deletion even if project has dependencies
            
        Returns:
            Response confirming deletion
        """
        return await self.manage_project("delete", project_id=project_id, force=force)
    
    async def project_health_check(self, project_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform a health check on a project.
        
        Args:
            project_id: Project identifier
            user_id: User identifier (optional)
            
        Returns:
            Response with health check results
        """
        return await self.manage_project("project_health_check", project_id=project_id, user_id=user_id)
    
    async def cleanup_obsolete(self, project_id: str, force: bool = False, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Clean up obsolete project data.
        
        Args:
            project_id: Project identifier
            force: Force cleanup operation
            user_id: User identifier (optional)
            
        Returns:
            Response with cleanup results
        """
        return await self.manage_project("cleanup_obsolete", project_id=project_id, force=force, user_id=user_id)
    
    async def validate_integrity(self, project_id: str, force: bool = False, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate project data integrity.
        
        Args:
            project_id: Project identifier
            force: Force validation operation
            user_id: User identifier (optional)
            
        Returns:
            Response with validation results
        """
        return await self.manage_project("validate_integrity", project_id=project_id, force=force, user_id=user_id)
    
    async def rebalance_agents(self, project_id: str, force: bool = False, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Rebalance agents across the project.
        
        Args:
            project_id: Project identifier
            force: Force rebalancing operation
            user_id: User identifier (optional)
            
        Returns:
            Response with rebalancing results
        """
        return await self.manage_project("rebalance_agents", project_id=project_id, force=force, user_id=user_id) 