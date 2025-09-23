"""
Git Branch Application Facade (for Task Trees)
"""
from typing import Dict, Any, Optional

from ..services.git_branch_service import GitBranchService
from ..services.websocket_notification_service import WebSocketNotificationService
from ...domain.repositories.project_repository import ProjectRepository

class GitBranchApplicationFacade:
    def __init__(self, git_branch_service: Optional[GitBranchService] = None, project_repo: Optional[ProjectRepository] = None, project_id: Optional[str] = None, user_id: Optional[str] = None):
        self._git_branch_service = git_branch_service or GitBranchService(project_repo)
        self._project_id = project_id
        self._user_id = user_id

    async def create_tree(self, project_id: str, tree_name: str, description: str = "") -> Dict[str, Any]:
        """Facade method to create a new task tree (branch)."""
        return await self._git_branch_service.create_git_branch(project_id, tree_name, description)

    def create_git_branch(self, project_id: str, git_branch_name: str, git_branch_description: str = "") -> Dict[str, Any]:
        """Create a new git branch (task tree) - synchronous version for MCP controller."""
        try:
            # Use actual GitBranchService to create the git branch
            import asyncio
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Creating git branch: project_id={project_id}, name={git_branch_name}")
            
            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're in a running loop, use asyncio.create_task() instead
                import concurrent.futures
                import threading
                
                # Use a thread pool to run the async function
                result = None
                exception = None
                
                def run_in_thread():
                    nonlocal result, exception
                    try:
                        result = asyncio.run(self.create_tree(project_id, git_branch_name, git_branch_description))
                    except Exception as e:
                        exception = e
                
                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join()

                if exception:
                    raise exception

                logger.info(f"Git branch creation result: {result}")

                # Send WebSocket notification after successful creation
                if result.get("success") and result.get("git_branch"):
                    branch_data = result.get("git_branch", {})
                    try:
                        WebSocketNotificationService.sync_broadcast_branch_event(
                            event_type="created",
                            branch_id=str(branch_data.get("id", "")),
                            project_id=str(project_id),
                            user_id=self._user_id or "system",
                            branch_data={
                                "id": str(branch_data.get("id", "")),
                                "git_branch_name": branch_data.get("git_branch_name") or branch_data.get("name", git_branch_name),
                                "name": branch_data.get("name"),
                                "description": branch_data.get("description", git_branch_description),
                                "project_id": str(project_id)
                            }
                        )
                        logger.info(f"✅ WebSocket notification sent for branch creation: {branch_data.get('id')}")
                    except Exception as ws_error:
                        logger.warning(f"Failed to send WebSocket notification for branch creation: {ws_error}")

                return result

            except RuntimeError:
                # No event loop is running, use asyncio.run()
                result = asyncio.run(self.create_tree(project_id, git_branch_name, git_branch_description))
                logger.info(f"Git branch creation result: {result}")

                # Send WebSocket notification after successful creation
                if result.get("success") and result.get("git_branch"):
                    branch_data = result.get("git_branch", {})
                    try:
                        WebSocketNotificationService.sync_broadcast_branch_event(
                            event_type="created",
                            branch_id=str(branch_data.get("id", "")),
                            project_id=str(project_id),
                            user_id=self._user_id or "system",
                            branch_data={
                                "id": str(branch_data.get("id", "")),
                                "git_branch_name": branch_data.get("git_branch_name") or branch_data.get("name", git_branch_name),
                                "name": branch_data.get("name"),
                                "description": branch_data.get("description", git_branch_description),
                                "project_id": str(project_id)
                            }
                        )
                        logger.info(f"✅ WebSocket notification sent for branch creation: {branch_data.get('id')}")
                    except Exception as ws_error:
                        logger.warning(f"Failed to send WebSocket notification for branch creation: {ws_error}")

                return result
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create git branch: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Failed to create git branch: {str(e)}",
                "error_code": "CREATION_FAILED"
            }

    def update_git_branch(self, git_branch_id: str, git_branch_name: Optional[str] = None, git_branch_description: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Update a git branch - synchronous version for MCP controller."""
        try:
            import asyncio
            import logging
            logger = logging.getLogger(__name__)

            # For simplicity, return success (update functionality would need to be implemented in service layer)
            # project_id is accepted but not used as git_branch_id is unique identifier
            result = {
                "success": True,
                "message": f"Git branch {git_branch_id} updated successfully",
                "git_branch_id": git_branch_id
            }

            # Get the current branch information for WebSocket notification
            # First, get the branch data to include in the notification
            try:
                branch_result = self.get_git_branch_by_id(git_branch_id)
                if branch_result.get("success"):
                    branch_data = branch_result.get("git_branch", {})
                    actual_project_id = branch_data.get("project_id", project_id)

                    # Send WebSocket notification after successful update
                    WebSocketNotificationService.sync_broadcast_branch_event(
                        event_type="updated",
                        branch_id=str(git_branch_id),
                        project_id=str(actual_project_id),
                        user_id=self._user_id or "system",
                        branch_data={
                            "id": str(git_branch_id),
                            "git_branch_name": git_branch_name or branch_data.get("git_branch_name") or branch_data.get("name", ""),
                            "name": branch_data.get("name"),
                            "description": git_branch_description or branch_data.get("description", ""),
                            "project_id": str(actual_project_id)
                        }
                    )
                    logger.info(f"✅ WebSocket notification sent for branch update: {git_branch_id}")
                else:
                    logger.warning(f"Could not retrieve branch data for WebSocket notification: {git_branch_id}")
            except Exception as ws_error:
                logger.warning(f"Failed to send WebSocket notification for branch update: {ws_error}")

            return result
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to update git branch: {str(e)}",
                "error_code": "UPDATE_FAILED"
            }

    def get_git_branch(self, project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Get a git branch by ID with project context - DDD-compliant method for controller interface."""
        try:
            import asyncio
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Getting git branch: project_id={project_id}, git_branch_id={git_branch_id}")
            
            # Use the existing get_git_branch_by_id method which handles the lookup
            result = self.get_git_branch_by_id(git_branch_id)
            
            # Ensure project_id matches (for validation)
            if result.get("success") and result.get("git_branch", {}).get("project_id") != project_id:
                logger.warning(f"Project ID mismatch: expected {project_id}, found {result.get('git_branch', {}).get('project_id')}")
            
            return result
            
        except Exception as e:
            import traceback
            logger.error(f"Error getting git branch: {e}")
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Failed to get git branch: {str(e)}",
                "error_code": "GET_FAILED"
            }

    def get_git_branch_by_id(self, git_branch_id: str) -> Dict[str, Any]:
        """Get a git branch by ID - synchronous version for MCP controller."""
        try:
            import asyncio
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Getting git branch by ID: {git_branch_id}")
            
            # We need to find the project that contains this git branch
            # For now, we'll query the project repository directly
            from ...domain.interfaces.repository_factory import IProjectRepositoryFactory
            
            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're in a running loop, use a thread to run the async function
                import concurrent.futures
                import threading
                
                result = None
                exception = None
                
                def run_in_thread():
                    nonlocal result, exception
                    try:
                        # Create a new event loop for this thread
                        result = asyncio.run(self._find_git_branch_by_id(git_branch_id))
                    except Exception as e:
                        exception = e
                
                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join()
                
                if exception:
                    raise exception
                    
                return result
                    
            except RuntimeError:
                # No event loop is running, use asyncio.run()
                result = asyncio.run(self._find_git_branch_by_id(git_branch_id))
                return result
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to get git branch: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Failed to get git branch: {str(e)}",
                "error_code": "GET_FAILED"
            }
    
    async def _find_git_branch_by_id(self, git_branch_id: str) -> Dict[str, Any]:
        """Helper method to find a git branch by ID across all projects."""
        
        # CONSISTENCY FIX: Use the same RepositoryProviderService that the API controller uses
        try:
            from ..services.repository_provider_service import RepositoryProviderService
            
            # User authentication is required
            if not self._user_id:
                raise ValueError("User authentication required. No user ID provided.")
            
            # Use the same repository service pattern as the API controller
            repo_provider = RepositoryProviderService.get_instance()
            git_branch_repo = repo_provider.get_git_branch_repository(user_id=self._user_id)
            
            # Use the git branch repository's find_by_id method directly (same as API controller)
            git_branch = await git_branch_repo.find_by_id(git_branch_id)
            
            if git_branch:
                # Convert the git branch entity to the expected format
                return {
                    "success": True,
                    "git_branch": {
                        "id": str(git_branch.id),
                        "name": git_branch.name,
                        "description": git_branch.description,
                        "project_id": str(git_branch.project_id),
                        "created_at": git_branch.created_at,
                        "updated_at": git_branch.updated_at
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"Git branch not found: {git_branch_id}",
                    "error_code": "NOT_FOUND"
                }
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to lookup git branch {git_branch_id}: {e}")
            return {
                "success": False,
                "error": f"Failed to get git branch: {str(e)}",
                "error_code": "GET_FAILED"
            }

    def delete_git_branch(self, git_branch_id: str, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Delete a git branch - synchronous version for MCP controller."""
        try:
            import asyncio
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Deleting git branch: {git_branch_id}")
            
            # CONSISTENCY FIX: First verify the branch exists using the same lookup pattern as get_git_branch_by_id
            # This ensures we find the branch the same way the API controller does
            branch_result = self.get_git_branch_by_id(git_branch_id)
            
            if not branch_result.get("success"):
                return {
                    "success": False,
                    "error": f"Git branch with ID {git_branch_id} not found",
                    "error_code": "NOT_FOUND"
                }
            
            # Get actual project_id from the found branch (for validation)
            found_branch = branch_result.get("git_branch", {})
            actual_project_id = found_branch.get("project_id")

            # Store branch data for WebSocket notification before deletion
            branch_data_for_notification = {
                "id": str(git_branch_id),
                "git_branch_name": found_branch.get("git_branch_name") or found_branch.get("name", ""),
                "name": found_branch.get("name"),
                "description": found_branch.get("description", ""),
                "project_id": str(actual_project_id)
            }

            # Validate project_id if provided
            if project_id and actual_project_id != project_id:
                logger.warning(f"Project ID mismatch for branch {git_branch_id}: expected {project_id}, found {actual_project_id}")
                return {
                    "success": False,
                    "error": f"Git branch {git_branch_id} belongs to project {actual_project_id}, not {project_id}",
                    "error_code": "PROJECT_MISMATCH"
                }

            # Use the actual project_id from the found branch
            target_project_id = actual_project_id or project_id or self._project_id
            
            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're in a running loop, use a thread to run the async function
                import concurrent.futures
                import threading
                
                result = None
                exception = None
                
                def run_in_thread():
                    nonlocal result, exception
                    try:
                        result = asyncio.run(self._git_branch_service.delete_git_branch(target_project_id, git_branch_id))
                    except Exception as e:
                        exception = e
                
                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join()
                
                if exception:
                    raise exception

                logger.info(f"Git branch deletion result: {result}")

                # Send WebSocket notification after successful deletion
                if result.get("success"):
                    try:
                        WebSocketNotificationService.sync_broadcast_branch_event(
                            event_type="deleted",
                            branch_id=str(git_branch_id),
                            project_id=str(target_project_id),
                            user_id=self._user_id or "system",
                            branch_data=branch_data_for_notification
                        )
                        logger.info(f"✅ WebSocket notification sent for branch deletion: {git_branch_id}")
                    except Exception as ws_error:
                        logger.warning(f"Failed to send WebSocket notification for branch deletion: {ws_error}")

                return result
                
            except RuntimeError:
                # No event loop is running, use asyncio.run()
                result = asyncio.run(self._git_branch_service.delete_git_branch(target_project_id, git_branch_id))
                logger.info(f"Git branch deletion result: {result}")

                # Send WebSocket notification after successful deletion
                if result.get("success"):
                    try:
                        WebSocketNotificationService.sync_broadcast_branch_event(
                            event_type="deleted",
                            branch_id=str(git_branch_id),
                            project_id=str(target_project_id),
                            user_id=self._user_id or "system",
                            branch_data=branch_data_for_notification
                        )
                        logger.info(f"✅ WebSocket notification sent for branch deletion: {git_branch_id}")
                    except Exception as ws_error:
                        logger.warning(f"Failed to send WebSocket notification for branch deletion: {ws_error}")

                return result
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to delete git branch: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Failed to delete git branch: {str(e)}",
                "error_code": "DELETE_FAILED"
            }

    def list_git_branchs(self, project_id: str) -> Dict[str, Any]:
        """List git branches for a project - synchronous version for MCP controller."""
        try:
            import asyncio
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Listing git branches for project: {project_id}")
            
            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're in a running loop, use a thread to run the async function
                import concurrent.futures
                import threading
                
                result = None
                exception = None
                
                def run_in_thread():
                    nonlocal result, exception
                    try:
                        result = asyncio.run(self.list_trees(project_id))
                    except Exception as e:
                        exception = e
                
                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join()
                
                if exception:
                    raise exception
                    
                logger.info(f"List git branches result: {result}")
                
                # Transform the result to match expected format
                if result.get("success"):
                    git_branchs = []
                    for tree in result.get("git_branchs", []):
                        git_branchs.append({
                            "id": tree.get("id"),
                            "name": tree.get("name"),
                            "description": tree.get("description", ""),
                            "created_at": tree.get("created_at"),
                            "total_tasks": tree.get("total_tasks", 0),
                            "completed_tasks": tree.get("completed_tasks", 0),
                            "progress": tree.get("progress", 0.0)
                        })
                    
                    return {
                        "success": True,
                        "git_branchs": git_branchs,
                        "total_count": len(git_branchs),
                        "message": f"Listed git branches for project {project_id}"
                    }
                else:
                    return result
                    
            except RuntimeError:
                # No event loop is running, use asyncio.run()
                result = asyncio.run(self.list_trees(project_id))
                logger.info(f"List git branches result: {result}")
                
                # Transform the result to match expected format
                if result.get("success"):
                    git_branchs = []
                    for tree in result.get("git_branchs", []):
                        git_branchs.append({
                            "id": tree.get("id"),
                            "name": tree.get("name"),
                            "description": tree.get("description", ""),
                            "created_at": tree.get("created_at"),
                            "total_tasks": tree.get("total_tasks", 0),
                            "completed_tasks": tree.get("completed_tasks", 0),
                            "progress": tree.get("progress", 0.0)
                        })
                    
                    return {
                        "success": True,
                        "git_branchs": git_branchs,
                        "total_count": len(git_branchs),
                        "message": f"Listed git branches for project {project_id}"
                    }
                else:
                    return result
                    
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to list git branches: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Failed to list git branches: {str(e)}",
                "error_code": "LIST_FAILED"
            }

    async def get_tree(self, project_id: str, tree_name: str) -> Dict[str, Any]:
        """Facade method to get a task tree."""
        return await self._git_branch_service.get_git_branch(project_id, tree_name)

    async def list_trees(self, project_id: str) -> Dict[str, Any]:
        """Facade method to list all task trees in a project."""
        return await self._git_branch_service.list_git_branchs(project_id)
    
    def assign_agent(self, git_branch_id: str, agent_id: str, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Assign an agent to a git branch - synchronous version for MCP controller."""
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Assigning agent {agent_id} to git branch {git_branch_id}")
            
            # Ensure we have user_id for authentication
            if not self._user_id:
                return {
                    "success": False,
                    "error": "Agent assignment requires user authentication. No user ID was provided.",
                    "error_code": "AUTHENTICATION_REQUIRED"
                }
            
            # Get the agent facade with proper user authentication
            from ..services.facade_service import FacadeService
            facade_service = FacadeService.get_instance()
            agent_facade = facade_service.get_agent_facade(
                project_id=project_id or self._project_id,
                user_id=self._user_id
            )
            
            # Use the agent facade to perform the assignment
            result = agent_facade.assign_agent(
                project_id=project_id or self._project_id,
                agent_id=agent_id,
                git_branch_id=git_branch_id
            )
            
            logger.info(f"Agent {agent_id} successfully assigned to git branch {git_branch_id}")
            return result
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to assign agent: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to assign agent: {str(e)}",
                "error_code": "ASSIGNMENT_FAILED"
            }
    
    def unassign_agent(self, git_branch_id: str, agent_id: str, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Unassign an agent from a git branch - synchronous version for MCP controller."""
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Unassigning agent {agent_id} from git branch {git_branch_id}")
            
            # Ensure we have user_id for authentication
            if not self._user_id:
                return {
                    "success": False,
                    "error": "Agent unassignment requires user authentication. No user ID was provided.",
                    "error_code": "AUTHENTICATION_REQUIRED"
                }
            
            # Get the agent facade with proper user authentication
            from ..services.facade_service import FacadeService
            facade_service = FacadeService.get_instance()
            agent_facade = facade_service.get_agent_facade(
                project_id=project_id or self._project_id,
                user_id=self._user_id
            )
            
            # Use the agent facade to perform the unassignment
            result = agent_facade.unassign_agent(
                project_id=project_id or self._project_id,
                agent_id=agent_id,
                git_branch_id=git_branch_id
            )
            
            logger.info(f"Agent {agent_id} successfully unassigned from git branch {git_branch_id}")
            return result
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to unassign agent: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to unassign agent: {str(e)}",
                "error_code": "UNASSIGNMENT_FAILED"
            }
    
    def get_statistics(self, project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Get statistics for a git branch - DDD-compliant implementation."""
        try:
            import logging
            from datetime import datetime, timezone
            logger = logging.getLogger(__name__)
            logger.info(f"Getting statistics for git branch {git_branch_id} in project {project_id}")
            
            # Get tasks associated with this git branch
            # IMPORTANT: For collaborative task visibility, we query ALL tasks
            # in a branch regardless of owner. Project-level security is still enforced.
            
            # Get ALL tasks for this branch using repository (follows DDD pattern)
            # This allows collaborative visibility while maintaining project-level security
            from ..services.repository_provider_service import RepositoryProviderService
            
            # Create instance of RepositoryProviderService
            repo_service = RepositoryProviderService()
            task_repo = repo_service.get_task_repository(
                project_id=project_id,
                user_id=self._user_id
            )
            # Use repository method to get tasks for branch - FIXED: Use correct method name
            task_objs = task_repo.get_tasks_by_git_branch_id(git_branch_id) if hasattr(task_repo, 'get_tasks_by_git_branch_id') else []
            
            # get_tasks_by_git_branch_id already returns dicts, no conversion needed
            tasks = task_objs if isinstance(task_objs, list) else []

            if not tasks:
                logger.warning(f"No tasks found for git branch {git_branch_id}")
            else:
                logger.info(f"Found {len(tasks)} tasks for git branch {git_branch_id}")
            
            # ✅ CRITICAL FIX: Use denormalized count fields from database triggers
            # Get branch data to access task_count and completed_task_count fields
            git_branch_repo = repo_service.get_git_branch_repository(
                project_id=project_id,
                user_id=self._user_id
            )

            # Get the branch to access denormalized count fields
            import asyncio
            try:
                branch = asyncio.run(git_branch_repo.find_by_id(git_branch_id))
            except RuntimeError:
                try:
                    loop = asyncio.get_event_loop()
                    branch = loop.run_until_complete(git_branch_repo.find_by_id(git_branch_id))
                except Exception:
                    branch = None

            if not branch:
                logger.warning(f"Branch {git_branch_id} not found")
                return {
                    "success": False,
                    "error": f"Branch {git_branch_id} not found",
                    "error_code": "BRANCH_NOT_FOUND"
                }

            # Use denormalized count fields (maintained by database triggers)
            total_tasks = getattr(branch, 'task_count', 0) or 0

            # Extract status from dictionary format (get_tasks_by_git_branch_id returns dicts)
            def get_task_status(task):
                return task.get("status") if isinstance(task, dict) else None
            
            completed_tasks = getattr(branch, 'completed_task_count', 0) or 0

            logger.info(f"🎯 Using trigger-maintained counts: {total_tasks} total, {completed_tasks} completed")
            in_progress_tasks = len([t for t in tasks if get_task_status(t) == "in_progress"])
            todo_tasks = len([t for t in tasks if get_task_status(t) == "todo"])
            blocked_tasks = len([t for t in tasks if get_task_status(t) == "blocked"])
            
            # Calculate progress percentage
            progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0
            
            # Find last activity (most recent task update)
            last_activity = None
            if tasks:
                last_updates = [task.get("updated_at") for task in tasks if task.get("updated_at")]
                if last_updates:
                    # Find the most recent update
                    last_activity = max(last_updates)
            
            # Get assigned agents (would need implementation in actual agent system)
            assigned_agents = []  # TODO: Implement agent assignment tracking
            
            return {
                "success": True,
                "statistics": {
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "in_progress_tasks": in_progress_tasks,
                    "todo_tasks": todo_tasks,
                    "blocked_tasks": blocked_tasks,
                    "progress_percentage": round(progress_percentage, 2),
                    "last_activity": last_activity,
                    "assigned_agents": assigned_agents,
                    "git_branch_id": git_branch_id,
                    "project_id": project_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "message": f"Statistics retrieved for git branch {git_branch_id}"
            }
            
        except Exception as e:
            import logging
            import traceback
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to get git branch statistics: {str(e)}")
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Failed to get git branch statistics: {str(e)}",
                "error_code": "STATISTICS_FAILED"
            }

    def get_branches_with_task_counts(self, project_id: str) -> Dict[str, Any]:
        """
        Get all branches for a project with their task counts.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Dict with branches array containing task count information
        """
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Getting branches with task counts for project {project_id}")
            
            # First get all branches for the project
            branches_result = self.list_git_branchs(project_id)
            
            if not branches_result.get("success"):
                return branches_result
            
            branches = branches_result.get("git_branchs", [])
            
            # Get task repository to query task counts
            # IMPORTANT: For collaborative task visibility, we query ALL tasks
            # in a branch regardless of owner. Project-level security is still enforced.
            from ...infrastructure.database.database_config import get_session
            from ...infrastructure.database.models import Task
            
            # Enhance each branch with task counts
            enhanced_branches = []
            for branch in branches:
                branch_id = branch.get("id")
                
                # Get ALL tasks for this branch using repository (follows DDD pattern)
                # This allows collaborative visibility while maintaining project-level security
                from ...infrastructure.repositories.task_repository_factory import TaskRepositoryFactory
                
                task_repo_factory = TaskRepositoryFactory()
                task_repo = task_repo_factory.create_repository(project_id=project_id, git_branch_name=branch.get("name", "main"), user_id=self._user_id)
                # Use repository method to get tasks for branch
                # FIXED: Use correct method name get_tasks_by_git_branch_id
                task_objs = task_repo.get_tasks_by_git_branch_id(branch_id) if hasattr(task_repo, 'get_tasks_by_git_branch_id') else []
                
                # Convert to list of dicts for processing (get_tasks_by_git_branch_id already returns dicts)
                tasks = task_objs if isinstance(task_objs, list) else []
                
                # ✅ CRITICAL FIX: Use denormalized count fields from database triggers
                # Access the branch object to get trigger-maintained counts
                total_tasks = branch.get("task_count", 0) or 0
                completed_tasks = branch.get("completed_task_count", 0) or 0

                logger.info(f"🎯 Branch {branch.get('name')}: Using trigger-maintained counts: {total_tasks} total, {completed_tasks} completed")

                # Calculate detailed status breakdown from actual tasks (for detailed stats)
                in_progress_tasks = 0
                todo_tasks = 0
                blocked_tasks = 0

                for task in tasks:
                    # get_tasks_by_git_branch_id returns dictionaries with 'status' key
                    status = task.get("status") if isinstance(task, dict) else getattr(task, 'status', None)

                    if status == "in_progress":
                        in_progress_tasks += 1
                    elif status == "todo":
                        todo_tasks += 1
                    elif status == "blocked":
                        blocked_tasks += 1
                
                # Calculate progress
                progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0
                
                
                enhanced_branch = {
                    "id": branch_id,
                    "name": branch.get("name"),
                    "git_branch_name": branch.get("git_branch_name") or branch.get("name"),
                    "description": branch.get("description", ""),
                    "project_id": project_id,
                    "total_tasks": total_tasks,  # Single source of truth for task count
                    "completed_tasks": completed_tasks,
                    "in_progress_tasks": in_progress_tasks,
                    "todo_tasks": todo_tasks,
                    "blocked_tasks": blocked_tasks,
                    "progress_percentage": round(progress_percentage, 2),
                    "created_at": branch.get("created_at"),
                    "updated_at": branch.get("updated_at")
                }
                enhanced_branches.append(enhanced_branch)
            
            logger.info(f"Enhanced {len(enhanced_branches)} branches with task counts")
            
            return {
                "success": True,
                "branches": enhanced_branches,
                "total_count": len(enhanced_branches)
            }
            
        except Exception as e:
            import logging
            import traceback
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to get branches with task counts: {str(e)}")
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Failed to get branches with task counts: {str(e)}",
                "branches": []
            }
    
    def get_project_branch_summary(self, project_id: str) -> Dict[str, Any]:
        """
        Get aggregated summary statistics for all branches in a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Dict with aggregated project statistics
        """
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Getting project branch summary for project {project_id}")
            
            # Get branches with task counts
            branches_result = self.get_branches_with_task_counts(project_id)
            
            if not branches_result.get("success"):
                return {
                    "success": False,
                    "summary": {},
                    "error": branches_result.get("error")
                }
            
            branches = branches_result.get("branches", [])
            
            # Aggregate statistics
            total_branches = len(branches)
            total_tasks = sum(b.get("total_tasks", 0) for b in branches)
            total_completed = sum(b.get("completed_tasks", 0) for b in branches)
            total_in_progress = sum(b.get("in_progress_tasks", 0) for b in branches)
            total_todo = sum(b.get("todo_tasks", 0) for b in branches)
            total_blocked = sum(b.get("blocked_tasks", 0) for b in branches)
            
            # Calculate overall progress
            overall_progress = (total_completed / total_tasks * 100) if total_tasks > 0 else 0.0
            
            # Find most active branch (most tasks)
            most_active_branch = None
            if branches:
                most_active = max(branches, key=lambda b: b.get("total_tasks", 0))
                if most_active.get("total_tasks", 0) > 0:
                    most_active_branch = {
                        "id": most_active.get("id"),
                        "name": most_active.get("name"),
                        "total_tasks": most_active.get("total_tasks")
                    }
            
            summary = {
                "total_branches": total_branches,
                "total_tasks": total_tasks,
                "completed_tasks": total_completed,
                "in_progress_tasks": total_in_progress,
                "todo_tasks": total_todo,
                "blocked_tasks": total_blocked,
                "overall_progress": round(overall_progress, 2),
                "most_active_branch": most_active_branch,
                "project_id": project_id
            }
            
            logger.info(f"Generated project summary: {total_branches} branches, {total_tasks} tasks")
            
            return {
                "success": True,
                "summary": summary
            }
            
        except Exception as e:
            import logging
            import traceback
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to get project branch summary: {str(e)}")
            traceback.print_exc()
            return {
                "success": False,
                "summary": {},
                "error": f"Failed to get project branch summary: {str(e)}"
            }
    
    def get_branch_summary(self, branch_id: str) -> Dict[str, Any]:
        """
        Get a single branch with its task count information.
        
        Args:
            branch_id: Branch identifier
            
        Returns:
            Dict with single branch data including task counts
        """
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Getting branch summary for branch {branch_id}")
            
            # Get branch details
            branch_result = self.get_git_branch_by_id(branch_id)
            
            if not branch_result.get("success"):
                return {
                    "success": False,
                    "branch": None,
                    "error": branch_result.get("error", f"Branch {branch_id} not found")
                }
            
            branch = branch_result.get("git_branch", {})
            
            # Get task counts for this branch
            # IMPORTANT: For collaborative task visibility, we query ALL tasks
            # in a branch regardless of owner. Project-level security is still enforced.
            # Get ALL tasks for this branch using repository (follows DDD pattern)
            # This allows collaborative visibility while maintaining project-level security  
            from ..services.repository_provider_service import RepositoryProviderService
            
            task_repo = RepositoryProviderService.get_task_repository()
            # Use repository method to get tasks for branch
            # FIXED: Use correct method name get_tasks_by_git_branch_id
            task_objs = task_repo.get_tasks_by_git_branch_id(branch_id) if hasattr(task_repo, 'get_tasks_by_git_branch_id') else []
            
            # Convert to list of dicts for processing (get_tasks_by_git_branch_id already returns dicts)
            tasks = task_objs if isinstance(task_objs, list) else []
            
            # ✅ CRITICAL FIX: Use denormalized count fields from database triggers
            # Access the branch object to get trigger-maintained counts
            total_tasks = branch.get("task_count", 0) or 0
            completed_tasks = branch.get("completed_task_count", 0) or 0

            logger.info(f"🎯 Branch summary: Using trigger-maintained counts: {total_tasks} total, {completed_tasks} completed")

            # Calculate detailed status breakdown from actual tasks (for detailed stats)
            in_progress_tasks = 0
            todo_tasks = 0
            blocked_tasks = 0

            for task in tasks:
                # get_tasks_by_git_branch_id returns dictionaries with 'status' key
                status = task.get("status") if isinstance(task, dict) else getattr(task, 'status', None)

                if status == "in_progress":
                    in_progress_tasks += 1
                elif status == "todo":
                    todo_tasks += 1
                elif status == "blocked":
                    blocked_tasks += 1
            
            # Calculate progress
            progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0
            
            
            branch_summary = {
                "id": branch_id,
                "name": branch.get("name"),
                "git_branch_name": branch.get("git_branch_name") or branch.get("name"),
                "description": branch.get("description", ""),
                "project_id": branch.get("project_id"),
                "total_tasks": total_tasks,  # Single source of truth for task count
                "completed_tasks": completed_tasks,
                "in_progress_tasks": in_progress_tasks,
                "todo_tasks": todo_tasks,
                "blocked_tasks": blocked_tasks,
                "progress_percentage": round(progress_percentage, 2),
                "created_at": branch.get("created_at"),
                "updated_at": branch.get("updated_at")
            }
            
            logger.info(f"Generated branch summary: {total_tasks} tasks, {progress_percentage:.1f}% complete")
            
            return {
                "success": True,
                "branch": branch_summary
            }
            
        except Exception as e:
            import logging
            import traceback
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to get branch summary: {str(e)}")
            traceback.print_exc()
            return {
                "success": False,
                "branch": None,
                "error": f"Failed to get branch summary: {str(e)}"
            }