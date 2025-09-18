"""
WebSocket Notification Service for broadcasting data changes to connected clients
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class WebSocketNotificationService:
    """
    Service for broadcasting data changes via WebSocket.
    This service acts as a bridge between the application layer and WebSocket infrastructure.
    """

    @staticmethod
    async def broadcast_task_event(
        event_type: str,
        task_id: str,
        user_id: str,
        task_data: Optional[Dict[str, Any]] = None,
        git_branch_id: Optional[str] = None,
        project_id: Optional[str] = None
    ):
        """
        Broadcast task-related events to WebSocket clients.

        Args:
            event_type: Type of event (created, updated, deleted, completed, etc.)
            task_id: ID of the task
            user_id: User who triggered the change
            task_data: Optional task data
            git_branch_id: Optional branch ID for filtering
            project_id: Optional project ID for filtering
        """
        logger.info(f"📡 broadcast_task_event called - event: {event_type}, task_id: {task_id}, user: {user_id}")

        try:
            # Try direct import first (for when running in same process)
            from fastmcp.server.routes.websocket_routes import broadcast_data_change
            logger.info("✅ Using direct WebSocket broadcast (same process)")

            # Prepare metadata
            metadata = {}
            if git_branch_id:
                metadata["git_branch_id"] = git_branch_id
            if project_id:
                metadata["project_id"] = project_id
            metadata["timestamp"] = datetime.utcnow().isoformat()

            # Send notification
            await broadcast_data_change(
                event_type=event_type,
                entity_type="task",
                entity_id=task_id,
                user_id=user_id,
                data=task_data,
                metadata=metadata
            )
            logger.info(f"✅ Successfully broadcasted task {event_type} event for {task_id}")

        except (ImportError, RuntimeError) as e:
            # Fallback to HTTP broadcast for cross-process communication
            logger.info("📡 Using HTTP broadcast (cross-process)")
            try:
                import aiohttp
                import os

                # Get API server URL from environment
                api_url = os.getenv("AUTH_API_URL", "http://localhost:8001")
                broadcast_url = f"{api_url}/api/v2/broadcast/notify"

                # Prepare metadata
                metadata = {}
                if git_branch_id:
                    metadata["git_branch_id"] = git_branch_id
                if project_id:
                    metadata["project_id"] = project_id
                metadata["timestamp"] = datetime.utcnow().isoformat()

                # Send HTTP request to broadcast endpoint
                async with aiohttp.ClientSession() as session:
                    payload = {
                        "event_type": event_type,
                        "entity_type": "task",
                        "entity_id": task_id,
                        "user_id": user_id,
                        "data": task_data,
                        "metadata": metadata
                    }
                    async with session.post(broadcast_url, json=payload) as resp:
                        if resp.status == 200:
                            logger.info(f"✅ Successfully sent HTTP broadcast for task {event_type}")
                        else:
                            logger.error(f"HTTP broadcast failed with status {resp.status}")

            except Exception as http_error:
                logger.error(f"Failed to send HTTP broadcast: {http_error}")

        except Exception as e:
            # Don't let notification failures break the main operation
            logger.error(f"Failed to broadcast task event: {e}")

    @staticmethod
    async def broadcast_subtask_event(
        event_type: str,
        subtask_id: str,
        task_id: str,
        user_id: str,
        subtask_data: Optional[Dict[str, Any]] = None
    ):
        """
        Broadcast subtask-related events to WebSocket clients.

        Args:
            event_type: Type of event (created, updated, deleted, completed, etc.)
            subtask_id: ID of the subtask
            task_id: ID of the parent task
            user_id: User who triggered the change
            subtask_data: Optional subtask data
        """
        try:
            from fastmcp.server.routes.websocket_routes import broadcast_data_change

            metadata = {
                "parent_task_id": task_id,
                "timestamp": datetime.utcnow().isoformat()
            }

            await broadcast_data_change(
                event_type=event_type,
                entity_type="subtask",
                entity_id=subtask_id,
                user_id=user_id,
                data=subtask_data,
                metadata=metadata
            )

            logger.debug(f"Broadcasted subtask {event_type} event for {subtask_id}")

        except ImportError:
            logger.warning("WebSocket routes not available, skipping broadcast")
        except Exception as e:
            logger.error(f"Failed to broadcast subtask event: {e}")

    @staticmethod
    async def broadcast_project_event(
        event_type: str,
        project_id: str,
        user_id: str,
        project_data: Optional[Dict[str, Any]] = None
    ):
        """
        Broadcast project-related events to WebSocket clients.

        Args:
            event_type: Type of event (created, updated, deleted, etc.)
            project_id: ID of the project
            user_id: User who triggered the change
            project_data: Optional project data
        """
        try:
            from fastmcp.server.routes.websocket_routes import broadcast_data_change

            metadata = {
                "timestamp": datetime.utcnow().isoformat()
            }

            await broadcast_data_change(
                event_type=event_type,
                entity_type="project",
                entity_id=project_id,
                user_id=user_id,
                data=project_data,
                metadata=metadata
            )

            logger.debug(f"Broadcasted project {event_type} event for {project_id}")

        except ImportError:
            logger.warning("WebSocket routes not available, skipping broadcast")
        except Exception as e:
            logger.error(f"Failed to broadcast project event: {e}")

    @staticmethod
    async def broadcast_branch_event(
        event_type: str,
        branch_id: str,
        project_id: str,
        user_id: str,
        branch_data: Optional[Dict[str, Any]] = None
    ):
        """
        Broadcast branch-related events to WebSocket clients.

        Args:
            event_type: Type of event (created, updated, deleted, etc.)
            branch_id: ID of the branch
            project_id: ID of the project
            user_id: User who triggered the change
            branch_data: Optional branch data
        """
        try:
            from fastmcp.server.routes.websocket_routes import broadcast_data_change

            metadata = {
                "project_id": project_id,
                "timestamp": datetime.utcnow().isoformat()
            }

            await broadcast_data_change(
                event_type=event_type,
                entity_type="branch",
                entity_id=branch_id,
                user_id=user_id,
                data=branch_data,
                metadata=metadata
            )

            logger.debug(f"Broadcasted branch {event_type} event for {branch_id}")

        except ImportError:
            logger.warning("WebSocket routes not available, skipping broadcast")
        except Exception as e:
            logger.error(f"Failed to broadcast branch event: {e}")

    @staticmethod
    async def broadcast_context_event(
        event_type: str,
        context_id: str,
        level: str,
        user_id: str,
        context_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Broadcast context-related events to WebSocket clients.

        Args:
            event_type: Type of event (created, updated, deleted, delegated, etc.)
            context_id: ID of the context
            level: Context level (global, project, branch, task)
            user_id: User who triggered the change
            context_data: Optional context data
            metadata: Optional additional metadata
        """
        try:
            from fastmcp.server.routes.websocket_routes import broadcast_data_change

            if metadata is None:
                metadata = {}
            metadata["context_level"] = level
            metadata["timestamp"] = datetime.utcnow().isoformat()

            await broadcast_data_change(
                event_type=event_type,
                entity_type="context",
                entity_id=context_id,
                user_id=user_id,
                data=context_data,
                metadata=metadata
            )

            logger.debug(f"Broadcasted context {event_type} event for {context_id} at level {level}")

        except ImportError:
            logger.warning("WebSocket routes not available, skipping broadcast")
        except Exception as e:
            logger.error(f"Failed to broadcast context event: {e}")

    @staticmethod
    def sync_broadcast_task_event(*args, **kwargs):
        """Synchronous wrapper for broadcast_task_event - tries direct WebSocket first, then HTTP fallback"""
        logger.info(f"🔔 sync_broadcast_task_event called from MCP server")

        # Extract arguments
        event_type = kwargs.get('event_type', args[0] if args else 'unknown')
        task_id = kwargs.get('task_id', args[1] if len(args) > 1 else 'unknown')
        user_id = kwargs.get('user_id', args[2] if len(args) > 2 else 'system')
        task_data = kwargs.get('task_data', args[3] if len(args) > 3 else None)
        git_branch_id = kwargs.get('git_branch_id', args[4] if len(args) > 4 else None)
        project_id = kwargs.get('project_id', args[5] if len(args) > 5 else None)

        # Prepare metadata
        metadata = {}
        if git_branch_id:
            metadata["git_branch_id"] = git_branch_id
        if project_id:
            metadata["project_id"] = project_id
        metadata["timestamp"] = datetime.utcnow().isoformat()

        # Try direct WebSocket broadcast first (same process)
        try:
            from fastmcp.server.routes.websocket_routes import broadcast_data_change
            logger.info("✅ Using direct WebSocket broadcast (same process)")

            # Create a task to run the async broadcast
            import asyncio
            try:
                # Get the current event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If there's already a running loop, create a task
                    asyncio.create_task(broadcast_data_change(
                        event_type=event_type,
                        entity_type="task",
                        entity_id=task_id,
                        user_id=user_id,
                        data=task_data,
                        metadata=metadata
                    ))
                    logger.info(f"✅ Successfully scheduled WebSocket broadcast for task {event_type}")
                    return
                else:
                    # If no running loop, run until complete
                    loop.run_until_complete(broadcast_data_change(
                        event_type=event_type,
                        entity_type="task",
                        entity_id=task_id,
                        user_id=user_id,
                        data=task_data,
                        metadata=metadata
                    ))
                    logger.info(f"✅ Successfully completed WebSocket broadcast for task {event_type}")
                    return
            except RuntimeError:
                # If we can't use the current loop, create a new one
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    new_loop.run_until_complete(broadcast_data_change(
                        event_type=event_type,
                        entity_type="task",
                        entity_id=task_id,
                        user_id=user_id,
                        data=task_data,
                        metadata=metadata
                    ))
                    logger.info(f"✅ Successfully completed WebSocket broadcast for task {event_type}")
                    return
                finally:
                    new_loop.close()

        except Exception as direct_error:
            logger.warning(f"Direct WebSocket broadcast failed: {direct_error}, trying HTTP fallback")

        # Fallback to HTTP broadcast for cross-process communication
        try:
            import requests
            import os

            # MCP server runs on port 8000
            api_url = os.getenv("AUTH_API_URL", "http://localhost:8000")
            broadcast_url = f"{api_url}/api/v2/broadcast/notify"

            # Send HTTP request
            payload = {
                "event_type": event_type,
                "entity_type": "task",
                "entity_id": task_id,
                "user_id": user_id,
                "data": task_data,
                "metadata": metadata
            }

            logger.info(f"📡 Sending HTTP broadcast to {broadcast_url}")
            response = requests.post(broadcast_url, json=payload, timeout=2)

            if response.status_code == 200:
                logger.info(f"✅ Successfully sent HTTP broadcast for task {event_type}")
            else:
                logger.error(f"HTTP broadcast failed with status {response.status_code}")

        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not send HTTP broadcast (API server may be down): {e}")
        except Exception as e:
            logger.error(f"Failed to sync broadcast task event: {e}")

    @staticmethod
    def sync_broadcast_project_event(*args, **kwargs):
        """Synchronous wrapper for broadcast_project_event"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    WebSocketNotificationService.broadcast_project_event(*args, **kwargs)
                )
            else:
                loop.run_until_complete(
                    WebSocketNotificationService.broadcast_project_event(*args, **kwargs)
                )
        except Exception as e:
            logger.error(f"Failed to sync broadcast project event: {e}")