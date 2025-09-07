"""
Project API Controller

This controller handles frontend project management operations following proper DDD architecture.
It serves as the interface layer, delegating business logic to application facades.
"""

import logging
from typing import Dict, Any, Optional

from ...application.facades.project_application_facade import ProjectApplicationFacade
from ...application.dtos.project.create_project_request import CreateProjectRequest
from ...application.dtos.project.update_project_request import UpdateProjectRequest

logger = logging.getLogger(__name__)


class ProjectAPIController:
    """
    API Controller for project management operations.
    
    This controller provides a clean interface between frontend routes and
    application services, ensuring proper separation of concerns.
    """
    
    def __init__(self):
        """Initialize the controller"""
        pass
    
    async def create_project(self, request: CreateProjectRequest, user_id: str, session) -> Dict[str, Any]:
        """
        Create a new project.
        
        Args:
            request: Project creation request data
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Project creation result
        """
        try:
            # Create project facade with proper user context
            facade = ProjectApplicationFacade(user_id=user_id)
            
            # Delegate to facade - pass name and description directly
            result = await facade.create_project(request.name, request.description or "")
            
            logger.info(f"Project created successfully for user {user_id}: {result.get('project', {}).get('id')}")
            
            return {
                "success": True,
                "project": result.get("project"),
                "message": "Project created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error creating project for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create project"
            }
    
    async def list_projects(self, user_id: str, session) -> Dict[str, Any]:
        """
        List projects for a user.
        
        Args:
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            List of projects
        """
        try:
            # Create project facade with proper user context
            facade = ProjectApplicationFacade(user_id=user_id)
            
            # Delegate to facade
            result = await facade.list_projects()
            
            logger.info(f"Listed {len(result.get('projects', []))} projects for user {user_id}")
            
            return {
                "success": True,
                "projects": result.get("projects", []),
                "count": len(result.get("projects", [])),
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"Error listing projects for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to list projects"
            }
    
    async def get_project(self, project_id: str, user_id: str, session) -> Dict[str, Any]:
        """
        Get a specific project.
        
        Args:
            project_id: Project identifier
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Project details
        """
        try:
            # Create project facade with proper user context
            facade = ProjectApplicationFacade(user_id=user_id)
            
            # Delegate to facade
            project = await facade.get_project(project_id)
            
            if not project:
                return {
                    "success": False,
                    "error": "Project not found",
                    "message": "Project not found or access denied"
                }
            
            logger.info(f"Retrieved project {project_id} for user {user_id}")
            
            return {
                "success": True,
                "project": project
            }
            
        except Exception as e:
            logger.error(f"Error getting project {project_id} for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get project"
            }
    
    async def update_project(self, project_id: str, request: UpdateProjectRequest, user_id: str, session) -> Dict[str, Any]:
        """
        Update a project.
        
        Args:
            project_id: Project identifier
            request: Project update request
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Updated project details
        """
        try:
            # Create project facade with proper user context
            facade = ProjectApplicationFacade(user_id=user_id)
            
            # First check if project exists
            existing_project = await facade.get_project(project_id)
            if not existing_project:
                return {
                    "success": False,
                    "error": "Project not found",
                    "message": "Project not found or access denied"
                }
            
            # Delegate to facade - pass individual parameters
            updated_project = await facade.update_project(project_id, request.name, request.description)
            
            logger.info(f"Updated project {project_id} for user {user_id}")
            
            return {
                "success": True,
                "project": updated_project,
                "message": "Project updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Error updating project {project_id} for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to update project"
            }
    
    async def delete_project(self, project_id: str, user_id: str, session) -> Dict[str, Any]:
        """
        Delete a project.
        
        Args:
            project_id: Project identifier
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Deletion result
        """
        try:
            # Create project facade with proper user context
            facade = ProjectApplicationFacade(user_id=user_id)
            
            # First check if project exists
            existing_project = await facade.get_project(project_id)
            if not existing_project:
                return {
                    "success": False,
                    "error": "Project not found", 
                    "message": "Project not found or access denied"
                }
            
            # Delegate to facade
            result = await facade.delete_project(project_id)
            
            # Check if deletion was successful
            if result and result.get("success"):
                logger.info(f"Deleted project {project_id} for user {user_id}")
                return {
                    "success": True,
                    "message": f"Project {project_id} deleted successfully for user {user_id}"
                }
            else:
                # Deletion failed
                error_msg = result.get("error", "Unknown error during deletion") if result else "Deletion returned None"
                logger.error(f"Failed to delete project {project_id}: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "message": "Failed to delete project"
                }
            
        except Exception as e:
            logger.error(f"Error deleting project {project_id} for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to delete project"
            }
    
    async def get_project_health(self, project_id: str, user_id: str, session) -> Dict[str, Any]:
        """
        Get project health status.
        
        Args:
            project_id: Project identifier
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Project health status
        """
        try:
            # Create project facade with proper user context
            facade = ProjectApplicationFacade(user_id=user_id)
            
            # First check if project exists
            existing_project = await facade.get_project(project_id)
            if not existing_project:
                return {
                    "success": False,
                    "error": "Project not found",
                    "message": "Project not found or access denied"
                }
            
            # Delegate to facade for health check
            health_result = await facade.project_health_check(project_id)
            
            logger.info(f"Retrieved project health for {project_id} by user {user_id}")
            
            return {
                "success": True,
                "health": health_result,
                "message": "Project health retrieved successfully"
            }
            
        except Exception as e:
            logger.error(f"Error getting project health {project_id} for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get project health"
            }