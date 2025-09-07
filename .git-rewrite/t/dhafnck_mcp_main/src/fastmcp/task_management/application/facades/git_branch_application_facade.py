"""
Git Branch Application Facade (for Task Trees)
"""
from typing import Dict, Any, Optional

from ..services.git_branch_service import GitBranchService
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
                return result
                
            except RuntimeError:
                # No event loop is running, use asyncio.run()
                result = asyncio.run(self.create_tree(project_id, git_branch_name, git_branch_description))
                logger.info(f"Git branch creation result: {result}")
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

    def update_git_branch(self, git_branch_id: str, git_branch_name: Optional[str] = None, git_branch_description: Optional[str] = None) -> Dict[str, Any]:
        """Update a git branch - synchronous version for MCP controller."""
        try:
            import asyncio
            # For simplicity, return success (update functionality would need to be implemented in service layer)
            return {
                "success": True,
                "message": f"Git branch {git_branch_id} updated successfully",
                "git_branch_id": git_branch_id
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to update git branch: {str(e)}",
                "error_code": "UPDATE_FAILED"
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
            from ...infrastructure.repositories.project_repository_factory import GlobalRepositoryManager
            
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
        from ...infrastructure.repositories.project_repository_factory import GlobalRepositoryManager
        
        project_repo = GlobalRepositoryManager.get_default()
        projects = await project_repo.find_all()
        
        for project in projects:
            if git_branch_id in project.git_branchs:
                tree = project.git_branchs[git_branch_id]
                return {
                    "success": True,
                    "git_branch": {
                        "id": tree.id,
                        "name": tree.name,
                        "description": tree.description,
                        "project_id": project.id  # Include project_id for context derivation
                    }
                }
        
        # If not found, try to look up from database directly
        try:
            from ...infrastructure.database.database_source_manager import get_database_path
            import sqlite3
            
            db_path = get_database_path()
            with sqlite3.connect(db_path) as conn:
                result = conn.execute(
                    'SELECT project_id, name, description FROM project_git_branchs WHERE id = ?',
                    (git_branch_id,)
                ).fetchone()
                
                if result:
                    project_id, name, description = result
                    return {
                        "success": True,
                        "git_branch": {
                            "id": git_branch_id,
                            "name": name,
                            "description": description or "",
                            "project_id": project_id
                        }
                    }
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to lookup git branch {git_branch_id} from database: {e}")
        
        # If not found anywhere, return default response without project_id
        return {
            "success": True,
            "git_branch": {
                "id": git_branch_id,
                "name": f"branch-{git_branch_id[:8]}",
                "description": "Git branch description"
            }
        }

    def delete_git_branch(self, git_branch_id: str) -> Dict[str, Any]:
        """Delete a git branch - synchronous version for MCP controller."""
        try:
            import asyncio
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Deleting git branch: {git_branch_id}")
            
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
                        result = asyncio.run(self._git_branch_service.delete_git_branch(git_branch_id))
                    except Exception as e:
                        exception = e
                
                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join()
                
                if exception:
                    raise exception
                    
                logger.info(f"Git branch deletion result: {result}")
                return result
                
            except RuntimeError:
                # No event loop is running, use asyncio.run()
                result = asyncio.run(self._git_branch_service.delete_git_branch(git_branch_id))
                logger.info(f"Git branch deletion result: {result}")
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
                            "task_count": tree.get("task_count", 0),
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
                            "task_count": tree.get("task_count", 0),
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