"""Git Branch MCP Controller

This controller handles git branch management operations following DDD principles.
It delegates business logic to the git branch facade and handles MCP-specific concerns.
"""

import logging
from typing import Dict, Any, Optional, Annotated
from pydantic import Field  # type: ignore
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

from .desc import description_loader
from ...application.factories.git_branch_facade_factory import GitBranchFacadeFactory
from ...application.facades.git_branch_application_facade import GitBranchApplicationFacade
from .workflow_guidance.git_branch.git_branch_workflow_factory import GitBranchWorkflowFactory
from .auth_helper import get_authenticated_user_id, log_authentication_details

logger = logging.getLogger(__name__)

# Import user context utilities - REQUIRED for authentication
try:
    from fastmcp.auth.middleware.request_context_middleware import get_current_user_id
    from fastmcp.auth.mcp_integration.thread_context_manager import ContextPropagationMixin
except ImportError:
    # Use auth_helper which is already imported
    get_current_user_id = get_authenticated_user_id
    # Fallback mixin if thread context manager is not available
    class ContextPropagationMixin:
        def _run_async_with_context(self, async_func, *args, **kwargs):
            import asyncio
            import threading
            result = None
            exception = None
            def run_in_new_loop():
                nonlocal result, exception
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        result = new_loop.run_until_complete(async_func(*args, **kwargs))
                    finally:
                        new_loop.close()
                        asyncio.set_event_loop(None)
                except Exception as e:
                    exception = e
            thread = threading.Thread(target=run_in_new_loop)
            thread.start()
            thread.join()
            if exception:
                raise exception
            return result


class GitBranchMCPController(ContextPropagationMixin):
    """
    MCP controller for git branch management operations.
    
    This controller follows DDD principles by:
    - Handling MCP-specific concerns (parameter validation, response formatting)
    - Delegating business logic to the git branch application facade
    - Maintaining clean separation between interface and business logic
    - Proper authentication context propagation across threads
    """
    
    def __init__(self, git_branch_facade_factory: GitBranchFacadeFactory):
        """
        Initialize the git branch MCP controller with factory pattern.
        
        Args:
            git_branch_facade_factory: Factory for creating git branch application facades
        """
        self._git_branch_facade_factory = git_branch_facade_factory
        self._workflow_guidance = GitBranchWorkflowFactory.create()
        logger.info("GitBranchMCPController initialized with factory pattern and workflow guidance")
    
    def register_tools(self, mcp: "FastMCP"):
        """Register git branch management MCP tools"""
        
        # Get tool descriptions
        manage_git_branch_desc = self._get_git_branch_management_descriptions().get("manage_git_branch", {})
        
        @mcp.tool(name="manage_git_branch", description=manage_git_branch_desc["description"])
        def manage_git_branch(
            action: Annotated[str, Field(description=manage_git_branch_desc["parameters"].get("action", "Git branch management action"))],
            project_id: Annotated[Optional[str], Field(description=manage_git_branch_desc["parameters"].get("project_id", "Project identifier"))] = None,
            git_branch_name: Annotated[Optional[str], Field(description="Git branch name identifier (can be used for assignment operations)")] = None,
            git_branch_id: Annotated[Optional[str], Field(description="Git branch UUID for lookup (can be used for assignment operations)")] = None,
            git_branch_description: Annotated[Optional[str], Field(description="Git branch description")] = None,
            agent_id: Annotated[Optional[str], Field(description=manage_git_branch_desc["parameters"].get("agent_id", "Agent identifier"))] = None,
            user_id: Annotated[Optional[str], Field(description=manage_git_branch_desc["parameters"].get("user_id", "User identifier for access control and audit"))] = None
        ) -> Dict[str, Any]:
            """Manage git branch operations including create, get, list, update, and delete."""
            return self.manage_git_branch(
                action=action,
                project_id=project_id,
                git_branch_name=git_branch_name,
                git_branch_id=git_branch_id,
                git_branch_description=git_branch_description,
                agent_id=agent_id,
                user_id=user_id
            )
    
    def _get_facade_for_request(self, project_id: str, user_id: str = None) -> GitBranchApplicationFacade:
        """
        Get a GitBranchApplicationFacade with the appropriate context.
        
        Args:
            project_id: Project identifier
            user_id: User identifier (optional, will be retrieved from context if not provided)
            
        Returns:
            GitBranchApplicationFacade instance
        """
        # Get authenticated user ID using helper function (handles compatibility mode)
        log_authentication_details()  # For debugging
        user_id = get_authenticated_user_id(user_id, "Git branch facade creation")
        
        # Create facade with user context
        return self._git_branch_facade_factory.create_git_branch_facade(
            project_id=project_id, 
            user_id=user_id
        )
    
    def manage_git_branch(
        self,
        action: str,
        project_id: Optional[str] = None,
        git_branch_name: Optional[str] = None,
        git_branch_id: Optional[str] = None,
        git_branch_description: Optional[str] = None,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Manage git branch operations by routing to appropriate handlers.
        """
        print(f"DEBUG: manage_git_branch called with action={action}, project_id={project_id}")
        logger.info(f"Managing git branch with action: {action} for project: {project_id}")
        
        # All actions require project_id
        if not project_id:
            return self._create_missing_field_error("project_id", action)
        
        # Route to appropriate handler based on action
        if action in ["create", "update", "get", "delete", "list"]:
            return self.handle_crud_operations(
                action, project_id, git_branch_name, git_branch_id, 
                git_branch_description, user_id
            )
        elif action in ["assign_agent", "unassign_agent"]:
            return self.handle_agent_operations(
                action, project_id, git_branch_name, git_branch_id, agent_id, user_id
            )
        elif action in ["get_statistics", "archive", "restore"]:
            return self.handle_advanced_operations(
                action, project_id, git_branch_id, user_id
            )
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "error_code": "UNKNOWN_ACTION",
                "valid_actions": [
                    "create", "get", "list", "update", "delete",
                    "assign_agent", "unassign_agent", "get_statistics",
                    "archive", "restore"
                ],
                "hint": "Check the action parameter for typos"
            }
    
    def handle_crud_operations(
        self,
        action: str,
        project_id: str,
        git_branch_name: Optional[str] = None,
        git_branch_id: Optional[str] = None,
        git_branch_description: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle core CRUD operations by converting MCP parameters 
        and delegating to the application facade.
        """
        try:
            # Get facade for this request
            print(f"DEBUG: About to call _get_facade_for_request with project_id={project_id}, user_id={user_id}")
            facade = self._get_facade_for_request(project_id, user_id)
            print(f"DEBUG: Successfully created facade: {facade}")
            
            if action == "create":
                if not git_branch_name:
                    return self._create_missing_field_error("git_branch_name", "create")
                return self._handle_create_git_branch(
                    facade, project_id, git_branch_name, git_branch_description or ""
                )
                
            elif action == "update":
                if not git_branch_id:
                    return self._create_missing_field_error("git_branch_id", "update")
                return self._handle_update_git_branch(
                    facade, git_branch_id, git_branch_name, git_branch_description
                )
                
            elif action == "get":
                if not git_branch_id:
                    return self._create_missing_field_error("git_branch_id", "get")
                return self._handle_get_git_branch(facade, git_branch_id)
                
            elif action == "delete":
                if not git_branch_id:
                    return self._create_missing_field_error("git_branch_id", "delete")
                return self._handle_delete_git_branch(facade, git_branch_id)
                
            elif action == "list":
                return self._handle_list_git_branchs(facade, project_id)
                
            else:
                return self._create_invalid_action_error(action)

        except Exception as e:
            logger.error(f"Error in CRUD operation '{action}': {e}")
            return {
                "success": False,
                "error": f"Operation failed: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "details": str(e)
            }
    
    def handle_agent_operations(
        self,
        action: str,
        project_id: str,
        git_branch_name: Optional[str] = None,
        git_branch_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle agent-related operations by converting MCP parameters 
        and delegating to the application facade.
        """
        try:
            # Get facade for this request
            facade = self._get_facade_for_request(project_id, user_id)
            
            # Validate required fields - now accepts either git_branch_id or git_branch_name
            if not git_branch_id and not git_branch_name:
                return {
                    "success": False,
                    "error": "Missing required field: git_branch_id or git_branch_name",
                    "error_code": "MISSING_FIELD",
                    "hint": "Include either 'git_branch_id' (UUID) or 'git_branch_name' (branch name) in your request"
                }
            
            if not agent_id:
                return self._create_missing_field_error("agent_id", action)
            
            if action == "assign_agent":
                return self._handle_assign_agent(facade, project_id, git_branch_id, git_branch_name, agent_id, user_id)
            elif action == "unassign_agent":
                return self._handle_unassign_agent(facade, project_id, git_branch_id, git_branch_name, agent_id, user_id)
            else:
                return self._create_invalid_action_error(action)

        except Exception as e:
            logger.error(f"Error in agent operation '{action}': {e}")
            return {
                "success": False,
                "error": f"Operation failed: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "details": str(e)
            }
    
    def handle_advanced_operations(
        self,
        action: str,
        project_id: str,
        git_branch_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle advanced operations by converting MCP parameters 
        and delegating to the application facade.
        """
        try:
            # Get facade for this request
            facade = self._get_facade_for_request(project_id, user_id)
            
            # All advanced operations require git_branch_id
            if not git_branch_id:
                return self._create_missing_field_error("git_branch_id", action)
            
            if action == "get_statistics":
                return self._handle_get_statistics(facade, project_id, git_branch_id)
            elif action == "archive":
                return self._handle_archive_git_branch(facade, git_branch_id)
            elif action == "restore":
                return self._handle_restore_git_branch(facade, git_branch_id)
            else:
                return self._create_invalid_action_error(action)

        except Exception as e:
            logger.error(f"Error in advanced operation '{action}': {e}")
            return {
                "success": False,
                "error": f"Operation failed: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "details": str(e)
            }

    # Private helper methods for converting MCP parameters and delegating to facade
    
    def _handle_create_git_branch(self, facade: GitBranchApplicationFacade, project_id: str, 
                                 git_branch_name: str, git_branch_description: str) -> Dict[str, Any]:
        """Convert MCP create parameters and delegate to facade."""
        response = facade.create_git_branch(project_id, git_branch_name, git_branch_description)
        return self._enhance_response_with_workflow_guidance(response, "create", project_id)
    
    def _handle_update_git_branch(self, facade: GitBranchApplicationFacade, git_branch_id: str, 
                                 git_branch_name: Optional[str] = None,
                                 git_branch_description: Optional[str] = None) -> Dict[str, Any]:
        """Convert MCP update parameters and delegate to facade."""
        response = facade.update_git_branch(git_branch_id, git_branch_name, git_branch_description)
        return self._enhance_response_with_workflow_guidance(response, "update", git_branch_id=git_branch_id)
    
    def _handle_get_git_branch(self, facade: GitBranchApplicationFacade, 
                              git_branch_id: str) -> Dict[str, Any]:
        """Handle get git branch request with enhanced context inclusion."""
        response = facade.get_git_branch_by_id(git_branch_id)
        
        # Extract project_id from response if available
        project_id = None
        if response.get("success") and response.get("git_branch"):
            project_id = response["git_branch"].get("project_id")
            
            # Include project + branch context
            response = self._include_project_branch_context(response, project_id, git_branch_id)
            
        return self._enhance_response_with_workflow_guidance(response, "get", project_id, git_branch_id)
    
    def _handle_delete_git_branch(self, facade: GitBranchApplicationFacade, 
                                 git_branch_id: str) -> Dict[str, Any]:
        """Handle delete git branch request."""
        response = facade.delete_git_branch(git_branch_id)
        return self._enhance_response_with_workflow_guidance(response, "delete", git_branch_id=git_branch_id)
    
    def _handle_list_git_branchs(self, facade: GitBranchApplicationFacade, 
                                 project_id: str) -> Dict[str, Any]:
        """Convert MCP list parameters and delegate to facade."""
        response = facade.list_git_branchs(project_id)
        return self._enhance_response_with_workflow_guidance(response, "list", project_id)
    
    def _handle_assign_agent(self, facade: GitBranchApplicationFacade, project_id: str, git_branch_id: Optional[str], 
                            git_branch_name: Optional[str], agent_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle assign agent to git branch request."""
        try:
            # Get the agent facade to handle agent operations
            from ...application.factories.agent_facade_factory import AgentFacadeFactory
            factory = AgentFacadeFactory()
            agent_facade = factory.create_agent_facade(project_id=project_id, user_id=user_id)
            
            # Resolve git_branch_id if only git_branch_name is provided
            resolved_git_branch_id = git_branch_id
            if not resolved_git_branch_id and git_branch_name:
                logger.info(f"Resolving branch name '{git_branch_name}' to ID for project '{project_id}'")
                resolved_git_branch_id = self._resolve_branch_name_to_id(project_id, git_branch_name)
                logger.info(f"Resolved branch ID: {resolved_git_branch_id}")
                if not resolved_git_branch_id:
                    response = {
                        "success": False,
                        "error": f"Git branch not found: {git_branch_name}",
                        "error_code": "BRANCH_NOT_FOUND",
                        "action": "assign_agent",
                        "git_branch_name": git_branch_name,
                        "agent_id": agent_id
                    }
                    return self._enhance_response_with_workflow_guidance(response, "assign_agent", project_id=project_id)
            
            # Resolve agent_id with database lookup (supports @prefix, no prefix, and UUID formats)
            resolved_agent_id = self._resolve_agent_identifier_with_lookup(project_id, agent_id, agent_facade)
            logger.info(f"Resolved agent ID: {resolved_agent_id} from input: {agent_id}")
            
            # Use the resolved git_branch_id to assign agent
            logger.debug(f"[CONTROLLER] About to call agent_facade.assign_agent with project_id={project_id}, agent_id={resolved_agent_id}, git_branch_id={resolved_git_branch_id}")
            logger.debug(f"[CONTROLLER] Type of resolved_git_branch_id: {type(resolved_git_branch_id)}")
            
            if resolved_git_branch_id:
                response = agent_facade.assign_agent(project_id, resolved_agent_id, resolved_git_branch_id)
            else:
                response = {
                    "success": False,
                    "error": "Either git_branch_id or git_branch_name is required for agent assignment",
                    "error_code": "MISSING_IDENTIFIER"
                }
            
            # Get the actual branch name from the database if not provided
            actual_branch_name = git_branch_name
            if not actual_branch_name and resolved_git_branch_id:
                actual_branch_name = self._resolve_branch_id_to_name(project_id, resolved_git_branch_id)
            
            # Add action and git_branch info to response
            response["action"] = "assign_agent"
            response["git_branch_id"] = resolved_git_branch_id
            response["git_branch_name"] = actual_branch_name
            response["agent_id"] = resolved_agent_id
            response["original_agent_id"] = agent_id  # Track what user originally provided
            
        except Exception as e:
            response = {
                "success": False,
                "error": f"Failed to assign agent: {str(e)}",
                "action": "assign_agent",
                "git_branch_id": git_branch_id,
                "git_branch_name": git_branch_name,
                "agent_id": agent_id
            }
        
        return self._enhance_response_with_workflow_guidance(response, "assign_agent", git_branch_id=resolved_git_branch_id if 'resolved_git_branch_id' in locals() else git_branch_id)
    
    def _handle_unassign_agent(self, facade: GitBranchApplicationFacade, project_id: str, git_branch_id: Optional[str], 
                              git_branch_name: Optional[str], agent_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle unassign agent from git branch request."""
        try:
            # Get the agent facade to handle agent operations
            from ...application.factories.agent_facade_factory import AgentFacadeFactory
            factory = AgentFacadeFactory()
            agent_facade = factory.create_agent_facade(project_id=project_id, user_id=user_id)
            
            # Resolve git_branch_id if only git_branch_name is provided
            resolved_git_branch_id = git_branch_id
            if not resolved_git_branch_id and git_branch_name:
                resolved_git_branch_id = self._resolve_branch_name_to_id(project_id, git_branch_name)
                if not resolved_git_branch_id:
                    response = {
                        "success": False,
                        "error": f"Git branch not found: {git_branch_name}",
                        "error_code": "BRANCH_NOT_FOUND",
                        "action": "unassign_agent",
                        "git_branch_name": git_branch_name,
                        "agent_id": agent_id
                    }
                    return self._enhance_response_with_workflow_guidance(response, "unassign_agent", project_id=project_id)
            
            # Resolve agent_id with database lookup (supports @prefix, no prefix, and UUID formats)  
            resolved_agent_id = self._resolve_agent_identifier_with_lookup(project_id, agent_id, agent_facade)
            logger.info(f"Resolved agent ID: {resolved_agent_id} from input: {agent_id}")
            
            # Use the resolved git_branch_id to unassign agent
            if resolved_git_branch_id:
                response = agent_facade.unassign_agent(project_id, resolved_agent_id, resolved_git_branch_id)
            else:
                response = {
                    "success": False,
                    "error": "Either git_branch_id or git_branch_name is required for agent unassignment",
                    "error_code": "MISSING_IDENTIFIER"
                }
            
            # Get the actual branch name from the database if not provided
            actual_branch_name = git_branch_name
            if not actual_branch_name and resolved_git_branch_id:
                actual_branch_name = self._resolve_branch_id_to_name(project_id, resolved_git_branch_id)
            
            # Add action and git_branch info to response
            response["action"] = "unassign_agent"
            response["git_branch_id"] = resolved_git_branch_id
            response["git_branch_name"] = actual_branch_name
            response["agent_id"] = resolved_agent_id
            response["original_agent_id"] = agent_id  # Track what user originally provided
            
        except Exception as e:
            response = {
                "success": False,
                "error": f"Failed to unassign agent: {str(e)}",
                "action": "unassign_agent",
                "git_branch_id": git_branch_id,
                "git_branch_name": git_branch_name,
                "agent_id": agent_id
            }
        
        return self._enhance_response_with_workflow_guidance(response, "unassign_agent", git_branch_id=resolved_git_branch_id if 'resolved_git_branch_id' in locals() else git_branch_id)
    
    def _handle_get_statistics(self, facade: GitBranchApplicationFacade, 
                              project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Handle get statistics for git branch request."""
        try:
            # Get the project_id from facade context or find it from the branch
            # Since we need the repository directly, let's use it
            # Use facade methods instead of direct repository access
            # The facade already has methods to get branch data and statistics
            
            # Get branch statistics using facade
            try:
                # First get the branch to ensure it exists
                branch_data = facade.get_git_branch_by_id(git_branch_id)
                if branch_data and 'git_branch' in branch_data:
                    # Return statistics based on branch data
                    branch = branch_data['git_branch']
                    return {
                        "git_branch_id": git_branch_id,
                        "project_id": project_id,
                        "name": branch.get('name'),
                        "task_count": branch.get('task_count', 0),
                        "completed_tasks": branch.get('completed_tasks', 0),
                        "in_progress_tasks": branch.get('in_progress_tasks', 0),
                        "todo_tasks": branch.get('todo_tasks', 0)
                    }
                else:
                    return {"error": f"Branch {git_branch_id} not found in project {project_id}"}
            except Exception as e:
                return {"error": f"Failed to get statistics: {e}"}
            
            result = self._run_async_with_context(_get_statistics_async)
                
            if result and "error" not in result:
                response = {
                    "success": True,
                    "action": "get_statistics",
                    "git_branch_id": git_branch_id,
                    "statistics": {
                        "branch_name": result["branch_name"],
                        "status": result["status"],
                        "priority": result["priority"],
                        "assigned_agent_id": result["assigned_agent_id"],
                        "total_tasks": result["task_count"],
                        "completed_tasks": result["completed_task_count"],
                        "in_progress_tasks": result["task_count"] - result["completed_task_count"],
                        "progress_percentage": result["progress_percentage"],
                        "created_at": result["created_at"],
                        "updated_at": result["updated_at"]
                    }
                }
                return self._enhance_response_with_workflow_guidance(response, "get_statistics", project_id, git_branch_id)
            else:
                return {
                    "success": False,
                    "error": result["error"] if "error" in result else "Failed to get branch statistics",
                    "git_branch_id": git_branch_id
                }
                
        except Exception as e:
            logger.error(f"Error getting branch statistics: {e}")
            return {
                "success": False,
                "error": f"Failed to get branch statistics: {str(e)}",
                "git_branch_id": git_branch_id
            }
    
    def _handle_archive_git_branch(self, facade: GitBranchApplicationFacade, 
                                  git_branch_id: str) -> Dict[str, Any]:
        """Handle archive git branch request."""
        # For now, return a placeholder response since archive isn't fully implemented
        response = {
            "success": True,
            "message": f"Archive functionality not yet implemented",
            "action": "archive",
            "git_branch_id": git_branch_id
        }
        return self._enhance_response_with_workflow_guidance(response, "archive", git_branch_id=git_branch_id)
    
    def _handle_restore_git_branch(self, facade: GitBranchApplicationFacade, 
                                  git_branch_id: str) -> Dict[str, Any]:
        """Handle restore git branch request."""
        # For now, return a placeholder response since restore isn't fully implemented
        response = {
            "success": True,
            "message": f"Restore functionality not yet implemented",
            "action": "restore",
            "git_branch_id": git_branch_id
        }
        return self._enhance_response_with_workflow_guidance(response, "restore", git_branch_id=git_branch_id)

    def _resolve_branch_name_to_id(self, project_id: str, git_branch_name: str) -> Optional[str]:
        """
        Helper method to resolve a git branch name to its ID within a project.
        
        Args:
            project_id: The project ID
            git_branch_name: The branch name to resolve
            
        Returns:
            The branch ID if found, None otherwise
        """
        try:
            # Use the git branch repository directly to find the branch by name
            # Use facade to list branches and find by name
            branches_data = self._facade.list_git_branches(project_id)
            if branches_data and 'git_branches' in branches_data:
                for branch in branches_data['git_branches']:
                    if branch.get('name') == git_branch_name:
                        return branch.get('id')
            return None
            
        except Exception as e:
            logger.error(f"Error in _resolve_branch_name_to_id: {e}")
            return None

    def _resolve_branch_id_to_name(self, project_id: str, git_branch_id: str) -> Optional[str]:
        """
        Helper method to resolve a git branch ID to its name within a project.
        
        Args:
            project_id: The project ID
            git_branch_id: The branch ID to resolve
            
        Returns:
            The branch name if found, None otherwise
        """
        try:
            # Use the git branch repository directly to find the branch by ID
            # Use facade to get branch by ID
            branch_data = self._facade.get_git_branch_by_id(git_branch_id)
            if branch_data and 'git_branch' in branch_data:
                return branch_data['git_branch'].get('name')
            return None
            
        except Exception as e:
            logger.error(f"Error in _resolve_branch_id_to_name: {e}")
            return None

    def _resolve_agent_identifier_with_lookup(self, project_id: str, agent_identifier: str, agent_facade) -> str:
        """
        Resolve agent identifier with database lookup and UUID generation for auto-registration.
        
        This method:
        1. Normalizes the agent identifier format
        2. Looks up existing agents by name
        3. Generates UUIDs for new agents
        4. Returns the appropriate format for auto-registration
        
        Args:
            project_id: The project ID
            agent_identifier: The agent identifier to resolve
            agent_facade: Agent facade for database operations
            
        Returns:
            Either a UUID (for existing agents) or "UUID:name" format (for auto-registration)
        """
        try:
            # First normalize the agent identifier
            normalized_agent = self._resolve_agent_identifier(project_id, agent_identifier)
            
            # Check if it's already a UUID
            import uuid
            import re
            uuid_pattern = re.compile(
                r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', 
                re.IGNORECASE
            )
            
            if uuid_pattern.match(normalized_agent):
                logger.info(f"Agent identifier '{normalized_agent}' is already a UUID")
                return normalized_agent
            
            # Extract clean agent name (remove @ if present)
            clean_name = normalized_agent.lstrip('@')
            
            # Try to find existing agent by name using agent facade
            try:
                # This would typically be done through agent repository, but agent facade doesn't expose find_by_name
                # For now, we'll generate UUID and use auto-registration format
                logger.info(f"Agent '{clean_name}' not found, generating UUID for auto-registration")
                
                # Generate a UUID for the new agent
                generated_uuid = str(uuid.uuid4())
                logger.info(f"Agent '{clean_name}' not found, generated UUID for auto-registration: {generated_uuid}")
                
                # Return UUID:name format for auto-registration
                return f"{generated_uuid}:{clean_name}"
                
            except Exception as lookup_error:
                logger.warning(f"Error looking up agent '{clean_name}': {lookup_error}")
                # Fallback: generate UUID anyway
                generated_uuid = str(uuid.uuid4())
                logger.info(f"Agent '{clean_name}' lookup failed, generated UUID for auto-registration: {generated_uuid}")
                return f"{generated_uuid}:{clean_name}"
            
        except Exception as e:
            logger.error(f"Error resolving agent identifier '{agent_identifier}': {e}")
            # Fallback: generate UUID
            import uuid
            generated_uuid = str(uuid.uuid4())
            clean_name = agent_identifier.lstrip('@')
            logger.info(f"Fallback: generated UUID for agent '{clean_name}': {generated_uuid}")
            return f"{generated_uuid}:{clean_name}"

    def _resolve_agent_identifier(self, project_id: str, agent_identifier: str) -> str:
        """
        Helper method to resolve agent identifier following expected behavior.
        
        Supports multiple input formats:
        1. UUID: "2d3727cf-6915-4b54-be8d-4a5a0311ca03" -> returns as-is
        2. Agent name with @: "@coding_agent" -> returns as-is (preserved)
        3. Agent name without @: "coding_agent" -> adds @ prefix and returns "@coding_agent"
        
        Args:
            project_id: The project ID (for potential future agent lookup)
            agent_identifier: The agent identifier to resolve
            
        Returns:
            The resolved agent identifier
        """
        try:
            import uuid
            import re
            
            # Check if it's already a valid UUID
            uuid_pattern = re.compile(
                r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', 
                re.IGNORECASE
            )
            
            if uuid_pattern.match(agent_identifier):
                logger.info(f"Agent identifier '{agent_identifier}' is already a valid UUID")
                return agent_identifier
            
            # If it already has @ prefix, preserve it as-is
            if agent_identifier.startswith('@'):
                logger.info(f"Agent identifier '{agent_identifier}' is @-prefixed, preserving as-is")
                return agent_identifier
            
            # If it doesn't have @ prefix, add it
            resolved_agent = f"@{agent_identifier}"
            logger.info(f"Agent identifier '{agent_identifier}' converted to '{resolved_agent}'")
            return resolved_agent
            
        except Exception as e:
            logger.error(f"Error resolving agent identifier '{agent_identifier}': {e}")
            # Fall back to adding @ prefix if agent_identifier doesn't already have it
            if not agent_identifier.startswith('@'):
                return f"@{agent_identifier}"
            return agent_identifier

    def _get_git_branch_management_descriptions(self) -> Dict[str, Any]:
        """
        Flatten git branch descriptions for robust access, similar to task controller.
        """
        all_desc = description_loader.get_all_descriptions()
        flat = {}
        # Look for 'manage_git_branch' in any subdict
        for sub in all_desc.values():
            if isinstance(sub, dict) and "manage_git_branch" in sub:
                flat["manage_git_branch"] = sub["manage_git_branch"]
        return flat
    
    def _create_missing_field_error(self, field: str, action: str) -> Dict[str, Any]:
        """Create standardized missing field error response."""
        return {
            "success": False,
            "error": f"Missing required field: {field}",
            "error_code": "MISSING_FIELD",
            "field": field,
            "action": action,
            "expected": f"A valid {field} value",
            "hint": f"Include '{field}' in your request for action '{action}'"
        }
    
    def _create_invalid_action_error(self, action: str) -> Dict[str, Any]:
        """Create standardized invalid action error response."""
        return {
            "success": False,
            "error": f"Invalid action: {action}",
            "error_code": "INVALID_ACTION",
            "field": "action",
            "valid_actions": [
                "create", "get", "list", "update", "delete",
                "assign_agent", "unassign_agent", "get_statistics",
                "archive", "restore"
            ],
            "hint": "Check the action parameter for valid values"
        }
    
    def _include_project_branch_context(self, response: Dict[str, Any], project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Include project + branch context in the response."""
        try:
            # Get hierarchical context facade
            from ...application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory
            context_factory = UnifiedContextFacadeFactory()
            context_facade = context_factory.create_facade()
            
            # Get project context
            project_context = context_facade.get_context("project", project_id, include_inherited=True)
            if project_context.get("success"):
                response["project_context"] = project_context.get("context", {})
                logger.info(f"Added project context for project {project_id}")
            else:
                logger.warning(f"Failed to get project context for {project_id}: {project_context.get('error', 'Unknown error')}")
            
            # Get branch context (if it exists)
            branch_context = context_facade.get_context("task", git_branch_id, include_inherited=True)
            if branch_context.get("success"):
                response["branch_context"] = branch_context.get("context", {})
                logger.info(f"Added branch context for branch {git_branch_id}")
            else:
                logger.debug(f"No branch context found for {git_branch_id}: {branch_context.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error including project + branch context: {e}")
        
        return response
    
    def _enhance_response_with_workflow_guidance(self, response: Dict[str, Any], action: str, 
                                               project_id: Optional[str] = None,
                                               git_branch_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Enhance response with workflow guidance if operation was successful.
        
        Args:
            response: The original response
            action: The action performed
            project_id: Project ID if available
            git_branch_id: Git branch ID if available
            
        Returns:
            Enhanced response with workflow guidance
        """
        if response.get("success", False):
            # Build context for workflow guidance
            guidance_context = {}
            if project_id:
                guidance_context["project_id"] = project_id
            if git_branch_id:
                guidance_context["git_branch_id"] = git_branch_id
            
            # Extract created branch ID from response if available
            if action == "create" and response.get("git_branch"):
                guidance_context["git_branch_id"] = response["git_branch"].get("id")
            
            # Generate and add workflow guidance
            workflow_guidance = self._workflow_guidance.generate_guidance(action, guidance_context)
            response["workflow_guidance"] = workflow_guidance
            
        return response