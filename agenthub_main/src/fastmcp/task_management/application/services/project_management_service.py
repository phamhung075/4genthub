"""Project Management Service

Application service for project lifecycle and multi-agent coordination.
Now uses SQLite database instead of JSON files for better data integrity and performance.
"""

from __future__ import annotations

import logging
from typing import Any

from ...domain.repositories.project_repository import ProjectRepository
from ...domain.websocket_protocol import (
    ProjectCreatePayload,
    ProjectDeletePayload,
    ProjectUpdatePayload,
)
from ...infrastructure.repositories.project_repository_factory import (
    GlobalRepositoryManager,
)
from ..services.websocket_notification_service import WebSocketNotificationService
from ..use_cases.cleanup_obsolete_use_case import CleanupObsoleteUseCase
from ..use_cases.create_project import CreateProjectUseCase
from ..use_cases.get_project import GetProjectUseCase
from ..use_cases.list_projects import ListProjectsUseCase

# from ..use_cases.delete_project import DeleteProjectUseCase  # Not used, commented out
from ..use_cases.project_health_check import ProjectHealthCheckUseCase
from ..use_cases.rebalance_agents_use_case import RebalanceAgentsUseCase
from ..use_cases.update_project import UpdateProjectUseCase
from ..use_cases.validate_integrity_use_case import ValidateIntegrityUseCase

logger = logging.getLogger(__name__)


class ProjectManagementService:
    """Application service for project lifecycle and multi-agent coordination using SQLite database"""

    def __init__(
        self, project_repo: ProjectRepository | None = None, user_id: str | None = None
    ):
        """
        Initialize ProjectManagementService with SQLite repository

        Args:
            project_repo: Optional project repository (for testing/dependency injection)
            user_id: User context for user-scoped project management
        """
        # Use provided repository or get default repository
        self._project_repo = project_repo or GlobalRepositoryManager.get_default()
        self._user_id = user_id  # Store user context

        # Determine repository type for logging
        repo_type = "unknown"
        if self._project_repo:
            repo_class_name = self._project_repo.__class__.__name__
            if "ORM" in repo_class_name:
                repo_type = "PostgreSQL/ORM"
            elif "SQLite" in repo_class_name:
                repo_type = "SQLite"
            elif "Mock" in repo_class_name:
                repo_type = "Mock"
            else:
                repo_type = repo_class_name

        logger.info(f"ProjectManagementService initialized with {repo_type} repository")

    def _get_user_scoped_repository(self) -> ProjectRepository:
        """Get a user-scoped version of the repository if it supports user context."""
        if hasattr(self._project_repo, "with_user") and self._user_id:
            # Repository supports user scoping
            return self._project_repo.with_user(self._user_id)
        elif hasattr(self._project_repo, "user_id"):
            # Repository has user_id property, set it if needed
            if self._user_id and self._project_repo.user_id != self._user_id:
                # Create new instance with user_id
                repo_class = type(self._project_repo)
                if hasattr(self._project_repo, "session"):
                    return repo_class(self._project_repo.session, user_id=self._user_id)
        return self._project_repo

    def with_user(self, user_id: str) -> ProjectManagementService:
        """Create a new service instance scoped to a specific user."""
        return ProjectManagementService(self._project_repo, user_id)

    async def create_project(self, name: str, description: str = "") -> dict[str, Any]:
        """Create a new project with auto-generated UUID"""
        try:
            logger.info(
                f"🔵 create_project called - name: {name}, user_id: {self._user_id}"
            )

            # Use user-scoped repository instead of the default one
            user_scoped_repo = self._get_user_scoped_repository()
            use_case = CreateProjectUseCase(user_scoped_repo)
            # Pass `None` for project_id so the use-case auto-generates one.
            result = await use_case.execute(None, name, description)

            logger.info(
                f"🔵 Use case result - success: {result.get('success')}, project_id: {result.get('project', {}).get('id')}"
            )

            # CRITICAL FIX: Ensure WebSocket broadcast is sent with correct user_id
            # The use case tries to extract user_id from repository, but this may fail
            # As a safety net, if we have user_id in service, always broadcast
            if result.get("success") and self._user_id:
                logger.info(f"🔵 Entering broadcast block - user_id: {self._user_id}")
                try:
                    raw_project_data = result.get("project", {})

                    logger.info(
                        f"🔵 About to call sync_broadcast_project_event - project_id: {raw_project_data.get('id')}, user_id: {self._user_id}"
                    )

                    # ✅ TYPE-SAFE PAYLOAD: Using Pydantic model for runtime validation
                    # This prevents "missing ID" bugs by enforcing required fields
                    try:
                        payload = ProjectCreatePayload(
                            id=raw_project_data.get("id"),
                            name=raw_project_data.get("name"),
                            description=raw_project_data.get("description"),
                            created_at=raw_project_data.get("created_at"),
                            updated_at=raw_project_data.get("updated_at"),
                        )
                        project_data = payload.model_dump()
                        logger.info(
                            f"✅ Project create payload validated: {project_data}"
                        )
                    except Exception as validation_error:
                        logger.error(
                            f"❌ Project create payload validation failed: {validation_error}"
                        )
                        # Fallback to dict (maintains backward compatibility during migration)
                        project_data = raw_project_data

                    # Always broadcast from service layer to ensure frontend updates
                    # This guarantees user_id is correct even if use case extraction failed
                    WebSocketNotificationService.sync_broadcast_project_event(
                        event_type="created",
                        project_id=project_data.get("id"),
                        user_id=self._user_id,
                        project_data=project_data,
                    )
                    logger.info(
                        f"✅ Service layer WebSocket broadcast COMPLETED for project: {project_data.get('id')}"
                    )
                except Exception as ws_error:
                    logger.error(
                        f"❌ Service layer WebSocket broadcast EXCEPTION: {ws_error}",
                        exc_info=True,
                    )
            else:
                logger.warning(
                    f"⚠️  Broadcast skipped - success: {result.get('success')}, user_id: {self._user_id}"
                )

            return result
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            return {"success": False, "error": str(e)}

    async def get_project(self, project_id: str) -> dict[str, Any]:
        """Get project details by UUID"""
        try:
            user_scoped_repo = self._get_user_scoped_repository()
            use_case = GetProjectUseCase(user_scoped_repo)
            return await use_case.execute(project_id)
        except Exception as e:
            logger.error(f"Failed to get project {project_id}: {e}")
            return {"success": False, "error": str(e)}

    async def get_project_by_name(self, name: str) -> dict[str, Any]:
        """Get project details by name"""
        try:
            # Use user-scoped repository for all operations
            user_scoped_repo = self._get_user_scoped_repository()
            project = await user_scoped_repo.find_by_name(name)
            if not project:
                return {
                    "success": False,
                    "error": f"Project with name '{name}' not found",
                }

            use_case = GetProjectUseCase(user_scoped_repo)
            return await use_case.execute(project.id)

        except Exception as e:
            logger.error(f"Failed to get project by name '{name}': {e}")
            return {"success": False, "error": str(e)}

    async def list_projects(self, include_branches: bool = True) -> dict[str, Any]:
        """
        List all projects

        Args:
            include_branches: Whether to include git branch data in the response.
                            Defaults to True for optimal performance.
        """
        try:
            user_scoped_repo = self._get_user_scoped_repository()
            use_case = ListProjectsUseCase(user_scoped_repo)
            return await use_case.execute(include_branches=include_branches)
        except Exception as e:
            logger.error(f"Failed to list projects: {e}")
            return {"success": False, "error": str(e)}

    async def update_project(
        self, project_id: str, name: str = None, description: str = None
    ) -> dict[str, Any]:
        """Update an existing project"""
        try:
            user_scoped_repo = self._get_user_scoped_repository()
            use_case = UpdateProjectUseCase(user_scoped_repo)
            result = await use_case.execute(project_id, name, description)

            # CRITICAL FIX: Ensure WebSocket broadcast for updates
            if result.get("success") and self._user_id:
                try:
                    raw_project_data = result.get("project", {})

                    # ✅ TYPE-SAFE PAYLOAD: Using Pydantic model for runtime validation
                    try:
                        payload = ProjectUpdatePayload(
                            id=raw_project_data.get("id") or project_id,
                            name=raw_project_data.get("name"),
                            description=raw_project_data.get("description"),
                            updated_at=raw_project_data.get("updated_at"),
                        )
                        project_data = payload.model_dump()
                        logger.info(
                            f"✅ Project update payload validated: {project_data}"
                        )
                    except Exception as validation_error:
                        logger.error(
                            f"❌ Project update payload validation failed: {validation_error}"
                        )
                        # Fallback to dict (maintains backward compatibility during migration)
                        project_data = raw_project_data

                    WebSocketNotificationService.sync_broadcast_project_event(
                        event_type="updated",
                        project_id=project_id,
                        user_id=self._user_id,
                        project_data=project_data,
                    )
                    logger.info(
                        f"✅ Service layer WebSocket broadcast for updated project: {project_id}"
                    )
                except Exception as ws_error:
                    logger.warning(
                        f"Service layer WebSocket broadcast failed: {ws_error}"
                    )

            return result
        except Exception as e:
            logger.error(f"Failed to update project {project_id}: {e}")
            return {"success": False, "error": str(e)}

    async def project_health_check(self, project_id: str = None) -> dict[str, Any]:
        """Perform health check on project(s)"""
        try:
            user_scoped_repo = self._get_user_scoped_repository()
            use_case = ProjectHealthCheckUseCase(user_scoped_repo)
            return await use_case.execute(project_id)
        except Exception as e:
            logger.error(f"Failed to perform health check: {e}")
            return {"success": False, "error": str(e)}

    async def cleanup_obsolete(self, project_id: str = None) -> dict[str, Any]:
        """Clean up obsolete project data"""
        try:
            user_scoped_repo = self._get_user_scoped_repository()
            use_case = CleanupObsoleteUseCase(user_scoped_repo)
            return await use_case.execute(project_id)
        except Exception as e:
            logger.error(f"Failed to cleanup obsolete data: {e}")
            return {"success": False, "error": str(e)}

    async def validate_integrity(self, project_id: str = None) -> dict[str, Any]:
        """Validate integrity of project data"""
        try:
            user_scoped_repo = self._get_user_scoped_repository()
            use_case = ValidateIntegrityUseCase(user_scoped_repo)
            return await use_case.execute(project_id)
        except Exception as e:
            logger.error(f"Failed to validate integrity: {e}")
            return {"success": False, "error": str(e)}

    async def rebalance_agents(self, project_id: str = None) -> dict[str, Any]:
        """Rebalance agent assignments across task trees"""
        try:
            user_scoped_repo = self._get_user_scoped_repository()
            use_case = RebalanceAgentsUseCase(user_scoped_repo)
            return await use_case.execute(project_id)
        except Exception as e:
            logger.error(f"Failed to rebalance agents: {e}")
            return {"success": False, "error": str(e)}

    async def delete_project(
        self, project_id: str, force: bool = False
    ) -> dict[str, Any]:
        """
        Delete a project with cascade deletion of all related data.
        Only allow deletion if project has only 'main' branch with 0 tasks (unless force=True).

        Args:
            project_id: The ID of the project to delete
            force: If True, skip safety checks and force deletion

        Returns:
            Dictionary with deletion results and statistics
        """
        try:
            # Get project to validate it exists
            user_scoped_repo = self._get_user_scoped_repository()
            project = await user_scoped_repo.find_by_id(project_id)
            if not project:
                return {"success": False, "error": f"Project {project_id} not found"}

            # Validate deletion safety if not forced
            if not force:
                # Get branches for this project using RepositoryFactory
                from ...infrastructure.repositories.repository_factory import (
                    RepositoryFactory,
                )

                # Create repository with user_id using factory pattern
                git_branch_repo = RepositoryFactory.get_git_branch_repository(
                    user_id=self._user_id
                )

                # Get all branches for this project - method is find_all_by_project
                branches = await git_branch_repo.find_all_by_project(project_id)
                logger.info(
                    f"[DEBUG] Found {len(branches) if branches else 0} branches for project {project_id}"
                )

                if branches:
                    logger.info(
                        f"Project deletion validation for {project_id}: Found {len(branches)} branches"
                    )
                    for branch in branches:
                        # Branch is an entity object, access attributes directly
                        branch_name = (
                            branch.name
                            if hasattr(branch, "name")
                            else branch.get("name", "unknown")
                        )
                        branch_id = (
                            branch.id
                            if hasattr(branch, "id")
                            else branch.get("id", "unknown")
                        )
                        # Get task count - might need to query separately
                        task_count = 0  # Will be determined below
                        logger.info(f"  Branch: {branch_name} (id={branch_id})")

                    # Check if project has only one branch and it's 'main'
                    if len(branches) > 1:
                        branch_names = [
                            b.name if hasattr(b, "name") else b.get("name")
                            for b in branches
                        ]
                        return {
                            "success": False,
                            "error": f"Cannot delete project with multiple branches ({len(branches)} branches: {', '.join(branch_names)}). "
                            f"Delete other branches first, or use force=True",
                        }

                    if len(branches) == 1:
                        main_branch = branches[0]
                        branch_name = (
                            main_branch.name
                            if hasattr(main_branch, "name")
                            else main_branch.get("name")
                        )
                        if branch_name != "main":
                            return {
                                "success": False,
                                "error": f"Cannot delete project with non-main branch '{branch_name}'. "
                                f"Project must have only 'main' branch, or use force=True",
                            }

                        # Check if main branch has any tasks
                        # Query task count for the branch
                        from ...infrastructure.database.database_config import (
                            get_session,
                        )
                        from ...infrastructure.database.models import Task

                        branch_id = (
                            main_branch.id
                            if hasattr(main_branch, "id")
                            else main_branch.get("id")
                        )

                        # Get a database session to query tasks
                        db_session = get_session()
                        try:
                            task_count = (
                                db_session.query(Task)
                                .filter(Task.git_branch_id == branch_id)
                                .count()
                            )
                            logger.info(
                                f"[DEBUG] Branch {branch_id} has {task_count} tasks"
                            )
                        finally:
                            db_session.close()

                        if task_count > 0:
                            return {
                                "success": False,
                                "error": f"Cannot delete project with {task_count} tasks in main branch. "
                                f"Delete all tasks first, or use force=True",
                            }

                        # If we get here, validation passed - project has only main branch with 0 tasks
                        logger.info(
                            f"Project {project_id} validation passed: main branch with {task_count} tasks"
                        )

            # Now proceed with deletion
            # Delete all branches (which will cascade delete tasks)
            logger.info(f"[DEBUG] Starting deletion process for project {project_id}")

            # Get branches using RepositoryFactory
            from ...infrastructure.repositories.repository_factory import (
                RepositoryFactory,
            )

            # Create repository with user_id using factory pattern
            git_branch_repo = RepositoryFactory.get_git_branch_repository(
                user_id=self._user_id
            )

            # Get all branches for this project - method is find_all_by_project
            branches = await git_branch_repo.find_all_by_project(project_id)
            logger.info(
                f"[DEBUG] Found {len(branches) if branches else 0} branches to delete for project {project_id}"
            )

            # Delete each branch (which will cascade delete tasks through the repository)
            if branches:
                for branch in branches:
                    branch_id = branch.id if hasattr(branch, "id") else branch.get("id")
                    if branch_id:
                        logger.info(
                            f"[DEBUG] Deleting branch {branch_id} for project {project_id}"
                        )
                        deleted = await git_branch_repo.delete_branch(branch_id)
                        logger.info(
                            f"[DEBUG] Branch {branch_id} deletion result: {deleted}"
                        )

            # Delete the project itself using user-scoped repository
            logger.info(
                f"[DEBUG] Attempting to delete project {project_id} from repository"
            )
            logger.info(
                f"[DEBUG] Project name: {project.name}, User ID: {self._user_id}"
            )

            deleted = await user_scoped_repo.delete(project_id)
            logger.info(f"[DEBUG] Delete operation returned: {deleted}")

            # Double-check the project is really deleted
            verify_project = await user_scoped_repo.find_by_id(project_id)
            logger.info(
                f"[DEBUG] Verification after delete - project found: {verify_project is not None}"
            )

            if deleted and verify_project is None:
                logger.info(
                    f"[DEBUG] Successfully deleted project {project_id} - verified gone from database"
                )

                # CRITICAL FIX: Service layer WebSocket broadcast (sync to ensure completion)
                # This is the safety net that ensures broadcast happens even if use case fails
                #
                # TYPE-SAFE PAYLOAD: Using Pydantic model for compile-time + runtime validation
                # This prevents "missing ID" bugs by enforcing required fields
                try:
                    logger.info(
                        f"🔵 [DELETE] About to call sync_broadcast_project_event - project_id: {project_id}, user_id: {self._user_id}"
                    )

                    # ✅ NEW: Type-safe payload construction with Pydantic validation
                    # Pydantic will raise ValidationError if required fields are missing
                    try:
                        payload = ProjectDeletePayload(id=project_id, name=project.name)
                        project_data = payload.model_dump()
                        logger.info(
                            f"✅ Project delete payload validated: {project_data}"
                        )
                    except Exception as validation_error:
                        logger.error(
                            f"❌ Project delete payload validation failed: {validation_error}"
                        )
                        # Fallback to dict (maintains backward compatibility during migration)
                        project_data = {"id": project_id, "name": project.name}

                    WebSocketNotificationService.sync_broadcast_project_event(
                        event_type="deleted",
                        project_id=project_id,
                        user_id=self._user_id,
                        project_data=project_data,
                    )
                    logger.info(
                        f"✅ [DELETE] Service layer WebSocket broadcast COMPLETED for project: {project_id}"
                    )
                except Exception as ws_error:
                    logger.error(
                        f"❌ [DELETE] Service layer WebSocket broadcast EXCEPTION: {ws_error}",
                        exc_info=True,
                    )

                return {
                    "success": True,
                    "message": f"Project '{project.name}' deleted successfully",
                    "project_id": project_id,
                }
            elif deleted and verify_project is not None:
                logger.error(
                    "[DEBUG] Delete returned True but project still exists in database!"
                )
                return {
                    "success": False,
                    "error": f"Failed to delete project {project_id} - project still exists after deletion",
                }
            else:
                logger.error(
                    f"[DEBUG] Repository delete returned False for project {project_id}"
                )
                return {
                    "success": False,
                    "error": f"Failed to delete project {project_id} - repository returned False",
                }

        except Exception as e:
            logger.error(f"Failed to delete project: {e}")
            return {"success": False, "error": str(e)}
