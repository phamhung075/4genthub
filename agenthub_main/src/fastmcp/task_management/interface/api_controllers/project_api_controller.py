"""
Project API Controller

This controller handles frontend project management operations following proper DDD architecture.
It serves as the interface layer, delegating business logic to application facades.
"""

import logging
from datetime import UTC, datetime

from fastmcp.types import (
    ApiResponse,
    DeleteResponse,
    ProjectDTO,
    ProjectResponse,
    ProjectsResponse,
)

from ...application.dtos.project.create_project_request import CreateProjectRequest
from ...application.dtos.project.update_project_request import UpdateProjectRequest
from ...application.facades.project_application_facade import ProjectApplicationFacade

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

    async def create_project(
        self, request: CreateProjectRequest, user_id: str, session
    ) -> ProjectResponse:
        """
        Create a new project.

        Args:
            request: Project creation request data
            user_id: Authenticated user ID
            session: Database session

        Returns:
            ProjectResponse with created project
        """
        try:
            # Create project facade with proper user context
            facade = ProjectApplicationFacade(user_id=user_id)

            # Delegate to facade - pass name and description directly
            result = await facade.create_project(
                request.name, request.description or ""
            )

            # Extract project data from result
            project_data = result.get("project", {})

            logger.info(
                f"Project created successfully for user {user_id}: {project_data.get('id')}"
            )

            # Create ProjectDTO manually
            project_dto = ProjectDTO(
                id=project_data.get("id"),
                name=project_data.get("name"),
                description=project_data.get("description"),
                created_at=project_data.get("created_at"),
                updated_at=project_data.get("updated_at"),
                owner_id=project_data.get("owner_id"),
                status=project_data.get("status"),
                branch_count=project_data.get("branch_count", 0),
                task_count=project_data.get("task_count", 0),
                git_branchs=project_data.get("git_branchs"),
                branches=project_data.get("branches"),
            )

            return ProjectResponse(
                success=True,
                project=project_dto,
                message="Project created successfully",
                timestamp=datetime.now(UTC).isoformat(),
            )

        except Exception as e:
            logger.error(f"Error creating project for user {user_id}: {e}")
            return ProjectResponse(
                success=False,
                project=None,
                error=str(e),
                message="Failed to create project",
                timestamp=datetime.now(UTC).isoformat(),
            )

    async def list_projects(self, user_id: str, session) -> ProjectsResponse:
        """
        List projects for a user.

        Args:
            user_id: Authenticated user ID
            session: Database session

        Returns:
            ProjectsResponse with list of projects
        """
        try:
            # Create project facade with proper user context
            facade = ProjectApplicationFacade(user_id=user_id)

            # Delegate to facade
            result = await facade.list_projects()

            # Extract projects data from result
            projects_data = result.get("projects", [])

            logger.info(f"Listed {len(projects_data)} projects for user {user_id}")

            # Create ProjectDTO instances manually for each project
            project_dtos = [
                ProjectDTO(
                    id=p.get("id"),
                    name=p.get("name"),
                    description=p.get("description"),
                    created_at=p.get("created_at"),
                    updated_at=p.get("updated_at"),
                    owner_id=p.get("owner_id"),
                    status=p.get("status"),
                    branch_count=p.get("branch_count", 0),
                    task_count=p.get("task_count", 0),
                    git_branchs=p.get("git_branchs"),
                    branches=p.get("branches"),
                )
                for p in projects_data
            ]

            return ProjectsResponse(
                success=True,
                projects=project_dtos,
                total=len(project_dtos),
                timestamp=datetime.now(UTC).isoformat(),
            )

        except Exception as e:
            logger.error(f"Error listing projects for user {user_id}: {e}")
            return ProjectsResponse(
                success=False,
                projects=[],
                error=str(e),
                message="Failed to list projects",
                timestamp=datetime.now(UTC).isoformat(),
            )

    async def get_project(
        self, project_id: str, user_id: str, session
    ) -> ProjectResponse:
        """
        Get a specific project.

        Args:
            project_id: Project identifier
            user_id: Authenticated user ID
            session: Database session

        Returns:
            ProjectResponse with project details
        """
        try:
            # Create project facade with proper user context
            facade = ProjectApplicationFacade(user_id=user_id)

            # Delegate to facade
            project_response = await facade.get_project(project_id)

            # Check if response is successful and contains project data
            if not project_response or not project_response.get("success"):
                error_msg = project_response.get("error", "Project not found") if project_response else "Project not found"
                return ProjectResponse(
                    success=False,
                    project=None,
                    error=error_msg,
                    message="Project not found or access denied",
                    timestamp=datetime.now(UTC).isoformat(),
                )

            # Extract the actual project dict from the response
            project_data = project_response.get("project", {})

            logger.info(f"Retrieved project {project_id} for user {user_id}")

            # Create ProjectDTO from extracted project data
            project_dto = ProjectDTO(
                id=project_data.get("id"),
                name=project_data.get("name"),
                description=project_data.get("description"),
                created_at=project_data.get("created_at"),
                updated_at=project_data.get("updated_at"),
                owner_id=project_data.get("owner_id"),
                status=project_data.get("status"),
                branch_count=project_data.get("branch_count", 0),
                task_count=project_data.get("task_count", 0),
                git_branchs=project_data.get("git_branchs"),
                branches=project_data.get("branches"),
            )

            return ProjectResponse(
                success=True,
                project=project_dto,
                timestamp=datetime.now(UTC).isoformat(),
            )

        except Exception as e:
            logger.error(f"Error getting project {project_id} for user {user_id}: {e}")
            return ProjectResponse(
                success=False,
                project=None,
                error=str(e),
                message="Failed to get project",
                timestamp=datetime.now(UTC).isoformat(),
            )

    async def update_project(
        self, project_id: str, request: UpdateProjectRequest, user_id: str, session
    ) -> ProjectResponse:
        """
        Update a project.

        Args:
            project_id: Project identifier
            request: Project update request
            user_id: Authenticated user ID
            session: Database session

        Returns:
            ProjectResponse with updated project details
        """
        try:
            # Create project facade with proper user context
            facade = ProjectApplicationFacade(user_id=user_id)

            # First check if project exists
            existing_project = await facade.get_project(project_id)
            if not existing_project:
                return ProjectResponse(
                    success=False,
                    project=None,
                    error="Project not found",
                    message="Project not found or access denied",
                    timestamp=datetime.now(UTC).isoformat(),
                )

            # Delegate to facade - pass individual parameters
            updated_project_data = await facade.update_project(
                project_id, request.name, request.description
            )

            logger.info(f"Updated project {project_id} for user {user_id}")

            # Create ProjectDTO manually
            project_dto = ProjectDTO(
                id=updated_project_data.get("id"),
                name=updated_project_data.get("name"),
                description=updated_project_data.get("description"),
                created_at=updated_project_data.get("created_at"),
                updated_at=updated_project_data.get("updated_at"),
                owner_id=updated_project_data.get("owner_id"),
                status=updated_project_data.get("status"),
                branch_count=updated_project_data.get("branch_count", 0),
                task_count=updated_project_data.get("task_count", 0),
                git_branchs=updated_project_data.get("git_branchs"),
                branches=updated_project_data.get("branches"),
            )

            return ProjectResponse(
                success=True,
                project=project_dto,
                message="Project updated successfully",
                timestamp=datetime.now(UTC).isoformat(),
            )

        except Exception as e:
            logger.error(f"Error updating project {project_id} for user {user_id}: {e}")
            return ProjectResponse(
                success=False,
                project=None,
                error=str(e),
                message="Failed to update project",
                timestamp=datetime.now(UTC).isoformat(),
            )

    async def delete_project(
        self, project_id: str, user_id: str, session
    ) -> DeleteResponse:
        """
        Delete a project.

        Args:
            project_id: Project identifier
            user_id: Authenticated user ID
            session: Database session

        Returns:
            DeleteResponse with deletion result
        """
        try:
            # Create project facade with proper user context
            facade = ProjectApplicationFacade(user_id=user_id)

            # First check if project exists
            existing_project = await facade.get_project(project_id)
            if not existing_project:
                return DeleteResponse(
                    success=False,
                    deleted=False,
                    error="Project not found",
                    message="Project not found or access denied",
                    timestamp=datetime.now(UTC).isoformat(),
                )

            # Delegate to facade
            result = await facade.delete_project(project_id)

            # Check if deletion was successful
            if result and result.get("success"):
                logger.info(f"Deleted project {project_id} for user {user_id}")
                return DeleteResponse(
                    success=True,
                    deleted=True,
                    id=project_id,
                    message=f"Project {project_id} deleted successfully",
                    timestamp=datetime.now(UTC).isoformat(),
                )
            else:
                # Deletion failed
                error_msg = (
                    result.get("error", "Unknown error during deletion")
                    if result
                    else "Deletion returned None"
                )
                logger.error(f"Failed to delete project {project_id}: {error_msg}")
                return DeleteResponse(
                    success=False,
                    deleted=False,
                    error=error_msg,
                    message="Failed to delete project",
                    timestamp=datetime.now(UTC).isoformat(),
                )

        except Exception as e:
            logger.error(f"Error deleting project {project_id} for user {user_id}: {e}")
            return DeleteResponse(
                success=False,
                deleted=False,
                error=str(e),
                message="Failed to delete project",
                timestamp=datetime.now(UTC).isoformat(),
            )

    async def get_project_health(
        self, project_id: str, user_id: str, session
    ) -> ApiResponse:
        """
        Get project health status.

        Args:
            project_id: Project identifier
            user_id: Authenticated user ID
            session: Database session

        Returns:
            ApiResponse with project health data
        """
        try:
            # Create project facade with proper user context
            facade = ProjectApplicationFacade(user_id=user_id)

            # First check if project exists
            existing_project = await facade.get_project(project_id)
            if not existing_project:
                return ApiResponse(
                    success=False,
                    error="Project not found",
                    message="Project not found or access denied",
                    timestamp=datetime.now(UTC).isoformat(),
                )

            # Delegate to facade for health check
            health_result = await facade.project_health_check(project_id)

            logger.info(f"Retrieved project health for {project_id} by user {user_id}")

            return ApiResponse(
                success=True,
                data=health_result,
                message="Project health retrieved successfully",
                timestamp=datetime.now(UTC).isoformat(),
            )

        except Exception as e:
            logger.error(
                f"Error getting project health {project_id} for user {user_id}: {e}"
            )
            return ApiResponse(
                success=False,
                error=str(e),
                message="Failed to get project health",
                timestamp=datetime.now(UTC).isoformat(),
            )
