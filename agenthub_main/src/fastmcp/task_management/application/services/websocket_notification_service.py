"""
WebSocket Notification Service for broadcasting data changes to connected clients
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import hashlib
import time

logger = logging.getLogger(__name__)

# Global deduplication cache to prevent duplicate notifications
_notification_cache = {}
_cache_ttl = 5  # 5 seconds TTL for deduplication


def _is_duplicate_notification(event_type: str, entity_type: str, entity_id: str, user_id: str) -> bool:
    """
    Check if this notification is a duplicate based on recent cache.
    Returns True if this is a duplicate that should be skipped.
    """
    global _notification_cache

    # Create a unique key for this notification
    notification_key = f"{event_type}:{entity_type}:{entity_id}:{user_id}"
    current_time = time.time()

    # Clean expired entries from cache
    expired_keys = [k for k, timestamp in _notification_cache.items() if current_time - timestamp > _cache_ttl]
    for key in expired_keys:
        del _notification_cache[key]

    # Check if this notification was recently sent
    if notification_key in _notification_cache:
        time_since_last = current_time - _notification_cache[notification_key]
        if time_since_last < _cache_ttl:
            logger.warning(f"🚫 DUPLICATE NOTIFICATION BLOCKED: {notification_key} (last sent {time_since_last:.2f}s ago)")
            return True

    # Record this notification
    _notification_cache[notification_key] = current_time
    logger.info(f"✅ NOTIFICATION ALLOWED: {notification_key}")
    return False


class WebSocketNotificationService:
    """
    Service for broadcasting data changes via WebSocket.
    This service acts as a bridge between the application layer and WebSocket infrastructure.
    """

    @staticmethod
    def _get_task_context(task_id: str, user_id: str = None) -> Dict[str, Any]:
        """
        Fetch task context including task title and parent branch information.

        Args:
            task_id: ID of the task
            user_id: User ID for multi-tenant filtering

        Returns:
            Dict containing task_title, parent_branch_id, parent_branch_title
        """
        try:
            from ...infrastructure.database.database_config import get_session
            from ...infrastructure.database.models import Task, ProjectGitBranch

            with get_session() as session:
                # Query with proper relationships
                query = session.query(Task, ProjectGitBranch).join(
                    ProjectGitBranch, Task.git_branch_id == ProjectGitBranch.id
                ).filter(Task.id == task_id)

                # Add user filtering if provided
                if user_id:
                    query = query.filter(Task.user_id == user_id)

                result = query.first()

                if result:
                    task, branch = result
                    return {
                        "task_title": task.title,
                        "parent_branch_id": branch.id,
                        "parent_branch_title": branch.name,
                        "task_user_id": task.user_id  # Include task owner's user_id for proper authorization
                    }
                else:
                    logger.warning(f"Task {task_id} not found for context lookup")
                    return {
                        "task_title": f"Task {task_id[:8]}",
                        "parent_branch_id": None,
                        "parent_branch_title": "Unknown Branch",
                        "task_user_id": None  # No user_id available if task not found
                    }

        except Exception as e:
            logger.error(f"Failed to get task context for {task_id}: {e}")
            return {
                "task_title": f"Task {task_id[:8]}",
                "parent_branch_id": None,
                "parent_branch_title": "Unknown Branch",
                "task_user_id": None  # No user_id available on error
            }

    @staticmethod
    def _get_subtask_context(subtask_id: str, task_id: str, user_id: str = None) -> Dict[str, Any]:
        """
        Fetch subtask context including subtask title and parent task information.

        Args:
            subtask_id: ID of the subtask
            task_id: ID of the parent task
            user_id: User ID for multi-tenant filtering

        Returns:
            Dict containing subtask_title, parent_task_id, parent_task_title
        """
        try:
            from ...infrastructure.database.database_config import get_session
            from ...infrastructure.database.models import Subtask, Task

            with get_session() as session:
                # Query with proper relationships
                query = session.query(Subtask, Task).join(
                    Task, Subtask.task_id == Task.id
                ).filter(
                    Subtask.id == subtask_id,
                    Subtask.task_id == task_id
                )

                # Add user filtering if provided
                if user_id:
                    query = query.filter(Subtask.user_id == user_id)

                result = query.first()

                if result:
                    subtask, task = result
                    return {
                        "subtask_title": subtask.title,
                        "parent_task_id": task.id,
                        "parent_task_title": task.title
                    }
                else:
                    logger.warning(f"Subtask {subtask_id} not found for context lookup")
                    return {
                        "subtask_title": f"Subtask {subtask_id[:8]}",
                        "parent_task_id": task_id,
                        "parent_task_title": f"Task {task_id[:8]}"
                    }

        except Exception as e:
            logger.error(f"Failed to get subtask context for {subtask_id}: {e}")
            return {
                "subtask_title": f"Subtask {subtask_id[:8]}",
                "parent_task_id": task_id,
                "parent_task_title": f"Task {task_id[:8]}"
            }

    @staticmethod
    def _get_branch_context(branch_id: str, user_id: str = None) -> Dict[str, Any]:
        """
        Fetch branch context including branch title.

        Args:
            branch_id: ID of the branch
            user_id: User ID for multi-tenant filtering

        Returns:
            Dict containing branch_title
        """
        try:
            from ...infrastructure.database.database_config import get_session
            from ...infrastructure.database.models import ProjectGitBranch

            with get_session() as session:
                query = session.query(ProjectGitBranch).filter(ProjectGitBranch.id == branch_id)

                # Add user filtering if provided
                if user_id:
                    query = query.filter(ProjectGitBranch.user_id == user_id)

                branch = query.first()

                if branch:
                    return {
                        "branch_title": branch.name
                    }
                else:
                    logger.warning(f"Branch {branch_id} not found for context lookup")
                    return {
                        "branch_title": f"Branch {branch_id[:8]}"
                    }

        except Exception as e:
            logger.error(f"Failed to get branch context for {branch_id}: {e}")
            return {
                "branch_title": f"Branch {branch_id[:8]}"
            }

    @staticmethod
    def _get_branch_cascade_data(branch_id: str, user_id: str = None) -> Dict[str, Any]:
        """
        Fetch branch cascade data with current task counts for WebSocket updates.
        Uses the same trigger-maintained counts as the bulk API for consistency.

        Args:
            branch_id: ID of the branch
            user_id: User ID for multi-tenant filtering

        Returns:
            Dict containing branch cascade data with task_count, completed_tasks, etc.
        """
        try:
            from ...infrastructure.database.database_config import get_session
            from sqlalchemy import text

            with get_session() as session:
                # Use the same query approach as bulk API for consistency
                query = text("""
                    SELECT
                        b.id as branch_id,
                        b.project_id,
                        b.name as branch_name,
                        b.status as branch_status,
                        b.priority as branch_priority,
                        COALESCE(b.task_count, 0) as task_count,
                        COALESCE(b.completed_task_count, 0) as completed_tasks,
                        COALESCE(b.task_count, 0) - COALESCE(b.completed_task_count, 0) as todo_tasks,
                        CASE
                            WHEN COALESCE(b.task_count, 0) = 0 THEN 0
                            ELSE ROUND((COALESCE(b.completed_task_count, 0)::numeric / b.task_count::numeric) * 100, 2)
                        END as progress_percentage,
                        b.updated_at as last_activity
                    FROM project_git_branchs b
                    WHERE b.id = :branch_id
                """)

                params = {"branch_id": branch_id}

                # Add user filtering if provided
                if user_id:
                    query = text("""
                        SELECT
                            b.id as branch_id,
                            b.project_id,
                            b.name as branch_name,
                            b.status as branch_status,
                            b.priority as branch_priority,
                            COALESCE(b.task_count, 0) as task_count,
                            COALESCE(b.completed_task_count, 0) as completed_tasks,
                            COALESCE(b.task_count, 0) - COALESCE(b.completed_task_count, 0) as todo_tasks,
                            CASE
                                WHEN COALESCE(b.task_count, 0) = 0 THEN 0
                                ELSE ROUND((COALESCE(b.completed_task_count, 0)::numeric / b.task_count::numeric) * 100, 2)
                            END as progress_percentage,
                            b.updated_at as last_activity
                        FROM project_git_branchs b
                        WHERE b.id = :branch_id AND b.user_id = :user_id
                    """)
                    params["user_id"] = user_id

                result = session.execute(query, params).fetchone()

                if result:
                    return {
                        "id": result[0],
                        "project_id": result[1],
                        "name": result[2],
                        "status": result[3],
                        "priority": result[4],
                        "task_count": result[5] or 0,
                        "completed_tasks": result[6] or 0,
                        "todo_tasks": result[7] or 0,
                        "progress_percentage": float(result[8] or 0),
                        "last_activity": result[9].isoformat() if result[9] else None
                    }
                else:
                    logger.warning(f"Branch {branch_id} not found for cascade data lookup")
                    return None

        except Exception as e:
            logger.error(f"Failed to get branch cascade data for {branch_id}: {e}")
            return None

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
        logger.info(f"📡 🚨 DELETE DEBUG: broadcast_task_event called - event: {event_type}, task_id: {task_id}, user: {user_id}")

        # Special detailed logging for DELETE operations
        if event_type.lower() in ['delete', 'deleted']:
            logger.warning(f"🗑️ BACKEND DELETE EVENT BROADCAST:")
            logger.warning(f"   Event Type: {event_type}")
            logger.warning(f"   Task ID: {task_id}")
            logger.warning(f"   User ID: {user_id}")
            logger.warning(f"   Task Data: {task_data}")
            logger.warning(f"   Git Branch ID: {git_branch_id}")
            logger.warning(f"   Project ID: {project_id}")
            logger.warning(f"   About to check for duplicate notification...")

        # DUPLICATE DETECTION: Check if this is a duplicate notification
        if _is_duplicate_notification(event_type, "task", task_id, user_id):
            if event_type.lower() in ['delete', 'deleted']:
                logger.warning(f"🚫 🗑️ DELETE DUPLICATE BLOCKED: {event_type} for task {task_id}")
            else:
                logger.info(f"🚫 Skipping duplicate task notification: {event_type} for task {task_id}")
            return  # Skip this notification

        # Special logging for DELETE continuing after duplicate check
        if event_type.lower() in ['delete', 'deleted']:
            logger.warning(f"✅ DELETE NOT DUPLICATE - proceeding with broadcast")

        try:
            # Try direct import first (for when running in same process)
            from fastmcp.server.routes.websocket_routes import broadcast_data_change
            logger.info("✅ Using direct WebSocket broadcast (same process)")

            # Get enhanced task context (title and parent branch info)
            task_context = WebSocketNotificationService._get_task_context(task_id, user_id)

            # Prepare enhanced metadata with titles and parent context
            metadata = {}
            if git_branch_id:
                metadata["git_branch_id"] = git_branch_id
            if project_id:
                metadata["project_id"] = project_id
            metadata["timestamp"] = datetime.now(timezone.utc).isoformat()

            # Enhanced payload with titles and parent context
            metadata["task_title"] = task_context["task_title"]
            metadata["parent_branch_id"] = task_context["parent_branch_id"]
            metadata["parent_branch_title"] = task_context["parent_branch_title"]

            # Send notification
            await broadcast_data_change(
                event_type=event_type,
                entity_type="task",
                entity_id=task_id,
                user_id=user_id,
                data=task_data,
                metadata=metadata
            )

            # Enhanced success logging for DELETE operations
            if event_type.lower() in ['delete', 'deleted']:
                logger.warning(f"✅ 🗑️ DELETE SUCCESSFULLY BROADCASTED: task {event_type} event for {task_id}")
                logger.warning(f"   Payload sent to broadcast_data_change: entity_type=task, event_type={event_type}, entity_id={task_id}")
            else:
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

                # Get enhanced task context (title and parent branch info)
                task_context = WebSocketNotificationService._get_task_context(task_id, user_id)

                # Prepare enhanced metadata with titles and parent context
                metadata = {}
                if git_branch_id:
                    metadata["git_branch_id"] = git_branch_id
                if project_id:
                    metadata["project_id"] = project_id
                metadata["timestamp"] = datetime.now(timezone.utc).isoformat()

                # Enhanced payload with titles and parent context
                metadata["task_title"] = task_context["task_title"]
                metadata["parent_branch_id"] = task_context["parent_branch_id"]
                metadata["parent_branch_title"] = task_context["parent_branch_title"]

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

            # Get enhanced subtask context (subtask title and parent task info)
            subtask_context = WebSocketNotificationService._get_subtask_context(subtask_id, task_id, user_id)

            metadata = {
                "parent_task_id": task_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                # Enhanced payload with titles and parent context
                "subtask_title": subtask_context["subtask_title"],
                "parent_task_title": subtask_context["parent_task_title"]
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
                "timestamp": datetime.now(timezone.utc).isoformat()
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

            # Get enhanced branch context (branch title)
            branch_context = WebSocketNotificationService._get_branch_context(branch_id, user_id)

            metadata = {
                "project_id": project_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                # Enhanced payload with branch title
                "branch_title": branch_context["branch_title"]
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
            metadata["timestamp"] = datetime.now(timezone.utc).isoformat()

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
        print(f"🚀 BACKEND DELETE DEBUG: sync_broadcast_task_event called")
        print(f"🚀 BACKEND DELETE DEBUG: This is EVENT 1 of 2 - TASK DELETION")

        # Extract arguments
        event_type = kwargs.get('event_type', args[0] if args else 'unknown')
        task_id = kwargs.get('task_id', args[1] if len(args) > 1 else 'unknown')
        user_id = kwargs.get('user_id', args[2] if len(args) > 2 else 'system')
        task_data = kwargs.get('task_data', args[3] if len(args) > 3 else None)
        git_branch_id = kwargs.get('git_branch_id', args[4] if len(args) > 4 else None)
        project_id = kwargs.get('project_id', args[5] if len(args) > 5 else None)
        pre_fetched_context = kwargs.get('pre_fetched_context', None)

        # DUPLICATE DETECTION: Check if this is a duplicate notification
        if _is_duplicate_notification(event_type, "task", task_id, user_id):
            logger.info(f"🚫 Skipping duplicate task notification: {event_type} for task {task_id}")
            return  # Skip this notification

        # Get enhanced task context (title and parent branch info)
        # CRITICAL FIX: Use pre-fetched context for deletion events to avoid querying deleted task
        if pre_fetched_context:
            logger.info(f"✅ Using pre-fetched context for {event_type} event: {pre_fetched_context}")
            task_context = pre_fetched_context
        else:
            logger.info(f"🔍 Fetching task context from database for {event_type} event")
            task_context = WebSocketNotificationService._get_task_context(task_id, user_id)

        # Prepare enhanced metadata with titles and parent context
        metadata = {}
        if git_branch_id:
            metadata["git_branch_id"] = git_branch_id
        if project_id:
            metadata["project_id"] = project_id
        metadata["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Enhanced payload with titles and parent context
        metadata["task_title"] = task_context["task_title"]
        metadata["parent_branch_id"] = task_context["parent_branch_id"]
        metadata["parent_branch_title"] = task_context["parent_branch_title"]

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
                    return  # Exit here - broadcast scheduled successfully
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
                    return  # Exit here - broadcast completed successfully
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
                    return  # Exit here - broadcast completed successfully
                finally:
                    new_loop.close()

        except (ImportError, RuntimeError) as direct_error:
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

    @staticmethod
    def sync_broadcast_branch_event(*args, **kwargs):
        """Synchronous wrapper for broadcast_branch_event - tries direct WebSocket first, then HTTP fallback"""
        logger.info(f"🔔 sync_broadcast_branch_event called from MCP server")
        print(f"🚀 BACKEND DELETE DEBUG: sync_broadcast_branch_event called")
        print(f"🚀 BACKEND DELETE DEBUG: This is EVENT 2 of 2 - BRANCH UPDATE")

        # Extract arguments
        event_type = kwargs.get('event_type', args[0] if args else 'unknown')
        branch_id = kwargs.get('branch_id', args[1] if len(args) > 1 else 'unknown')
        project_id = kwargs.get('project_id', args[2] if len(args) > 2 else 'unknown')
        user_id = kwargs.get('user_id', args[3] if len(args) > 3 else 'system')
        branch_data = kwargs.get('branch_data', args[4] if len(args) > 4 else None)

        # Get enhanced branch context (branch title)
        branch_context = WebSocketNotificationService._get_branch_context(branch_id, user_id)

        # Prepare enhanced metadata with branch title
        metadata = {
            "project_id": project_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            # Enhanced payload with branch title
            "branch_title": branch_context["branch_title"]
        }

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
                        entity_type="branch",
                        entity_id=branch_id,
                        user_id=user_id,
                        data=branch_data,
                        metadata=metadata
                    ))
                    logger.info(f"✅ Successfully scheduled WebSocket broadcast for branch {event_type}")
                    return  # Exit here - broadcast scheduled successfully
                else:
                    # If no running loop, run until complete
                    loop.run_until_complete(broadcast_data_change(
                        event_type=event_type,
                        entity_type="branch",
                        entity_id=branch_id,
                        user_id=user_id,
                        data=branch_data,
                        metadata=metadata
                    ))
                    logger.info(f"✅ Successfully completed WebSocket broadcast for branch {event_type}")
                    return  # Exit here - broadcast completed successfully
            except RuntimeError:
                # If we can't use the current loop, create a new one
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    new_loop.run_until_complete(broadcast_data_change(
                        event_type=event_type,
                        entity_type="branch",
                        entity_id=branch_id,
                        user_id=user_id,
                        data=branch_data,
                        metadata=metadata
                    ))
                    logger.info(f"✅ Successfully completed WebSocket broadcast for branch {event_type}")
                    return  # Exit here - broadcast completed successfully
                finally:
                    new_loop.close()

        except (ImportError, RuntimeError) as direct_error:
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
                "entity_type": "branch",
                "entity_id": branch_id,
                "user_id": user_id,
                "data": branch_data,
                "metadata": metadata
            }

            logger.info(f"📡 Sending HTTP broadcast to {broadcast_url}")
            response = requests.post(broadcast_url, json=payload, timeout=2)

            if response.status_code == 200:
                logger.info(f"✅ Successfully sent HTTP broadcast for branch {event_type}")
            else:
                logger.error(f"HTTP broadcast failed with status {response.status_code}")

        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not send HTTP broadcast (API server may be down): {e}")
        except Exception as e:
            logger.error(f"Failed to sync broadcast branch event: {e}")

    @staticmethod
    def sync_broadcast_subtask_event(*args, **kwargs):
        """Synchronous wrapper for broadcast_subtask_event - tries direct WebSocket first, then HTTP fallback"""
        logger.info(f"🔔 sync_broadcast_subtask_event called from MCP server")

        # Extract arguments
        event_type = kwargs.get('event_type', args[0] if args else 'unknown')
        subtask_id = kwargs.get('subtask_id', args[1] if len(args) > 1 else 'unknown')
        task_id = kwargs.get('task_id', args[2] if len(args) > 2 else 'unknown')
        user_id = kwargs.get('user_id', args[3] if len(args) > 3 else 'system')
        subtask_data = kwargs.get('subtask_data', args[4] if len(args) > 4 else None)

        # Get enhanced subtask context (subtask title and parent task info)
        subtask_context = WebSocketNotificationService._get_subtask_context(subtask_id, task_id, user_id)

        # Prepare enhanced metadata with titles and parent context
        metadata = {
            "parent_task_id": task_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            # Enhanced payload with titles and parent context
            "subtask_title": subtask_context["subtask_title"],
            "parent_task_title": subtask_context["parent_task_title"]
        }

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
                        entity_type="subtask",
                        entity_id=subtask_id,
                        user_id=user_id,
                        data=subtask_data,
                        metadata=metadata
                    ))
                    logger.info(f"✅ Successfully scheduled WebSocket broadcast for subtask {event_type}")
                    return  # Exit here - broadcast scheduled successfully
                else:
                    # If no running loop, run until complete
                    loop.run_until_complete(broadcast_data_change(
                        event_type=event_type,
                        entity_type="subtask",
                        entity_id=subtask_id,
                        user_id=user_id,
                        data=subtask_data,
                        metadata=metadata
                    ))
                    logger.info(f"✅ Successfully completed WebSocket broadcast for subtask {event_type}")
                    return  # Exit here - broadcast completed successfully

            except RuntimeError:
                # No event loop in current thread, create new one
                import asyncio
                asyncio.run(broadcast_data_change(
                    event_type=event_type,
                    entity_type="subtask",
                    entity_id=subtask_id,
                    user_id=user_id,
                    data=subtask_data,
                    metadata=metadata
                ))
                logger.info(f"✅ Successfully created new loop and broadcast subtask {event_type}")
                return  # Exit here - broadcast completed successfully

        except ImportError:
            logger.warning("WebSocket routes not available, falling back to HTTP broadcast")
        except Exception as e:
            logger.warning(f"Direct WebSocket broadcast failed: {e}, falling back to HTTP")

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
                "entity_type": "subtask",
                "entity_id": subtask_id,
                "user_id": user_id,
                "data": subtask_data,
                "metadata": metadata
            }

            logger.info(f"📡 Sending HTTP broadcast to {broadcast_url}")
            response = requests.post(broadcast_url, json=payload, timeout=2)

            if response.status_code == 200:
                logger.info(f"✅ Successfully sent HTTP broadcast for subtask {event_type}")
            else:
                logger.error(f"HTTP broadcast failed with status {response.status_code}")

        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not send HTTP broadcast (API server may be down): {e}")
        except Exception as e:
            logger.error(f"Failed to sync broadcast subtask event: {e}")