"""Update Project Use Case"""

from __future__ import annotations

from typing import Any

from ...domain.repositories.project_repository import ProjectRepository


class UpdateProjectUseCase:
    """Use case for updating a project"""

    def __init__(self, project_repository: ProjectRepository):
        self._project_repository = project_repository

    async def execute(
        self, project_id: str, name: str | None = None, description: str | None = None
    ) -> dict[str, Any]:
        """Execute the update project use case"""

        project = await self._project_repository.find_by_id(project_id)

        if not project:
            return {
                "success": False,
                "error": f"Project with ID '{project_id}' not found",
            }

        updated_fields = []

        if name is not None:
            project.name = name
            updated_fields.append("name")

        if description is not None:
            project.description = description
            updated_fields.append("description")

        if not updated_fields:
            return {
                "success": False,
                "error": "No fields to update. Provide name and/or description.",
            }

        # Update timestamp using entity's touch() method
        project.touch("project_updated")

        # Save to repository
        await self._project_repository.update(project)

        # Broadcast WebSocket notification for real-time frontend updates
        try:
            from ..services.websocket_notification_service import (
                WebSocketNotificationService,
            )

            # Get user_id for WebSocket broadcast
            user_id = None
            if hasattr(self._project_repository, "user_id"):
                user_context = getattr(self._project_repository, "user_id", None)
                if user_context is not None:
                    if hasattr(user_context, "user_id"):
                        user_id = user_context.user_id
                    elif hasattr(user_context, "id"):
                        user_id = user_context.id
                    elif isinstance(user_context, str):
                        user_id = user_context

            if user_id:
                WebSocketNotificationService.sync_broadcast_project_event(
                    event_type="updated",
                    project_id=project.id,
                    user_id=user_id,
                    project_data={
                        "id": project.id,
                        "name": project.name,
                        "description": project.description,
                        "updated_at": project.updated_at.isoformat(),
                        "updated_fields": updated_fields,
                    },
                )
                import logging

                logger = logging.getLogger(__name__)
                logger.info(
                    f"✅ Broadcasted WebSocket notification for project update: {project.id}"
                )
        except Exception as ws_error:
            # Log WebSocket errors but don't fail project update
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                f"Failed to broadcast WebSocket notification for project {project.id}: {ws_error}"
            )

        return {
            "success": True,
            "project": {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat(),
            },
            "updated_fields": updated_fields,
            "message": f"Project '{project_id}' updated successfully",
        }
