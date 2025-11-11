"""
Project Application Facade
"""

from __future__ import annotations

from typing import Any

from ...infrastructure.repositories.project_repository_factory import (
    GlobalRepositoryManager,
)
from ..services.project_management_service import ProjectManagementService


class ProjectApplicationFacade:
    def __init__(
        self,
        project_service: ProjectManagementService | None = None,
        user_id: str | None = None,
    ):
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
                self._project_service = ProjectManagementService(
                    GlobalRepositoryManager.get_default(), user_id
                )

    def with_user(self, user_id: str) -> ProjectApplicationFacade:
        """Create a new facade instance scoped to a specific user."""
        return ProjectApplicationFacade(
            self._project_service.with_user(user_id), user_id
        )

    async def manage_project(
        self,
        action: str,
        project_id: str | None = None,
        name: str | None = None,
        description: str | None = None,
        user_id: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Facade method to route project management actions to the service layer."""

        if action == "create":
            if not name:
                return {"success": False, "error": "Missing required field: name"}

            # Use user-scoped service - prioritize parameter user_id, fallback to instance user_id
            effective_user_id = user_id or self._user_id
            if not effective_user_id:
                return {"success": False, "error": "User authentication required"}

            # Validate project name using domain service
            try:
                from ...domain.services.project_name_validator import (
                    ProjectNameValidator,
                )
                from ...infrastructure.repositories.project_repository_factory import (
                    GlobalRepositoryManager,
                )

                # Get user-scoped repository for validation
                project_repo = GlobalRepositoryManager.get_for_user(effective_user_id)
                validator = ProjectNameValidator(project_repo)

                # Validate project name (includes format and uniqueness checks)
                await validator.validate_project_name(name, effective_user_id)

            except Exception as e:
                # Build enhanced error response
                error_msg = str(e)
                error_response = {"success": False, "error": error_msg}

                # Add helpful hints for duplicate project names
                if "already exists" in error_msg.lower():
                    error_response["error_code"] = "DUPLICATE_PROJECT_NAME"
                    error_response["hint"] = (
                        "Use manage_project(action='list') to see all existing projects"
                    )
                    error_response["suggested_actions"] = [
                        {"action": "list", "description": "View all existing projects"},
                        {
                            "action": "get",
                            "name": name,
                            "description": f"Get details of existing project '{name}'",
                        },
                    ]

                return error_response

            # If validation passes, proceed with creation
            service = (
                self._project_service.with_user(effective_user_id)
                if effective_user_id
                else self._project_service
            )
            return await service.create_project(name, description or "")

        elif action == "get":
            if project_id:
                return await self._project_service.get_project(project_id)
            elif name:
                return await self._project_service.get_project_by_name(name)
            else:
                return {
                    "success": False,
                    "error": "Missing required field: project_id or name",
                }

        elif action == "list":
            # Use user-scoped service - prioritize parameter user_id, fallback to instance user_id
            effective_user_id = user_id or self._user_id
            service = (
                self._project_service.with_user(effective_user_id)
                if effective_user_id
                else self._project_service
            )
            # Always include branches to optimize frontend performance
            return await service.list_projects(include_branches=True)

        elif action == "update":
            if not project_id:
                return {"success": False, "error": "Missing required field: project_id"}

            # If name is being updated, validate it
            if name is not None:
                effective_user_id = user_id or self._user_id
                if not effective_user_id:
                    return {"success": False, "error": "User authentication required"}

                try:
                    from ...domain.services.project_name_validator import (
                        ProjectNameValidator,
                    )
                    from ...infrastructure.repositories.project_repository_factory import (
                        GlobalRepositoryManager,
                    )

                    # Get user-scoped repository for validation
                    project_repo = GlobalRepositoryManager.get_for_user(
                        effective_user_id
                    )
                    validator = ProjectNameValidator(project_repo)

                    # Validate project name (include project_id to exclude current project)
                    await validator.validate_project_name(
                        name, effective_user_id, project_id
                    )

                except Exception as e:
                    # Build enhanced error response
                    error_msg = str(e)
                    error_response = {"success": False, "error": error_msg}

                    # Add helpful hints for duplicate project names
                    if "already exists" in error_msg.lower():
                        error_response["error_code"] = "DUPLICATE_PROJECT_NAME"
                        error_response["hint"] = (
                            "Use manage_project(action='list') to see all existing projects"
                        )
                        error_response["suggested_actions"] = [
                            {
                                "action": "list",
                                "description": "View all existing projects",
                            },
                            {
                                "action": "get",
                                "name": name,
                                "description": f"Get details of existing project '{name}'",
                            },
                        ]

                    return error_response

            return await self._project_service.update_project(
                project_id, name, description
            )

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
            # Use user-scoped service like CREATE and LIST
            effective_user_id = user_id or self._user_id
            service = (
                self._project_service.with_user(effective_user_id)
                if effective_user_id
                else self._project_service
            )
            return await service.delete_project(project_id, force)

        else:
            return {"success": False, "error": f"Invalid action: {action}"}

    async def create_project(self, name: str, description: str = "") -> dict[str, Any]:
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

    async def get_project(self, project_id: str) -> dict[str, Any]:
        """
        Get project details by ID.

        Args:
            project_id: Project identifier

        Returns:
            Response with project details
        """
        return await self.manage_project("get", project_id=project_id)

    async def get_project_by_name(self, name: str) -> dict[str, Any]:
        """
        Get project details by name.

        Args:
            name: Project name

        Returns:
            Response with project details
        """
        return await self.manage_project("get", name=name)

    async def list_projects(self) -> dict[str, Any]:
        """
        List all projects.

        Returns:
            Response with project list
        """
        return await self.manage_project("list")

    async def update_project(
        self, project_id: str, name: str | None = None, description: str | None = None
    ) -> dict[str, Any]:
        """
        Update an existing project.

        Args:
            project_id: Project identifier
            name: New project name (optional)
            description: New project description (optional)

        Returns:
            Response with updated project details
        """
        return await self.manage_project(
            "update", project_id=project_id, name=name, description=description
        )

    async def delete_project(
        self, project_id: str, force: bool = False
    ) -> dict[str, Any]:
        """
        Delete a project.

        Args:
            project_id: Project identifier
            force: Force deletion even if project has dependencies

        Returns:
            Response confirming deletion
        """
        return await self.manage_project("delete", project_id=project_id, force=force)

    async def project_health_check(
        self, project_id: str, user_id: str | None = None
    ) -> dict[str, Any]:
        """
        Perform a health check on a project.

        Args:
            project_id: Project identifier
            user_id: User identifier (optional)

        Returns:
            Response with health check results
        """
        return await self.manage_project(
            "project_health_check", project_id=project_id, user_id=user_id
        )

    async def cleanup_obsolete(
        self, project_id: str, force: bool = False, user_id: str | None = None
    ) -> dict[str, Any]:
        """
        Clean up obsolete project data.

        Args:
            project_id: Project identifier
            force: Force cleanup operation
            user_id: User identifier (optional)

        Returns:
            Response with cleanup results
        """
        return await self.manage_project(
            "cleanup_obsolete", project_id=project_id, force=force, user_id=user_id
        )

    async def validate_integrity(
        self, project_id: str, force: bool = False, user_id: str | None = None
    ) -> dict[str, Any]:
        """
        Validate project data integrity.

        Args:
            project_id: Project identifier
            force: Force validation operation
            user_id: User identifier (optional)

        Returns:
            Response with validation results
        """
        return await self.manage_project(
            "validate_integrity", project_id=project_id, force=force, user_id=user_id
        )

    async def rebalance_agents(
        self, project_id: str, force: bool = False, user_id: str | None = None
    ) -> dict[str, Any]:
        """
        Rebalance agents across the project.

        Args:
            project_id: Project identifier
            force: Force rebalancing operation
            user_id: User identifier (optional)

        Returns:
            Response with rebalancing results
        """
        return await self.manage_project(
            "rebalance_agents", project_id=project_id, force=force, user_id=user_id
        )
