"""
Context Hierarchy Validator

Validates context creation requirements and provides user-friendly guidance
for the 4-tier hierarchy: Global → Project → Branch → Task
"""

import logging
from typing import Dict, Any, Optional, Tuple, List
from ...domain.value_objects.context_enums import ContextLevel

logger = logging.getLogger(__name__)


class ContextHierarchyValidator:
    """Validates context hierarchy requirements and provides guidance."""
    
    def __init__(self, global_repo, project_repo, branch_repo, task_repo, user_id: Optional[str] = None):
        """Initialize with context repositories and optional user_id."""
        self.global_repo = global_repo
        self.project_repo = project_repo
        self.branch_repo = branch_repo
        self.task_repo = task_repo
        self.user_id = user_id
    
    def validate_hierarchy_requirements(
        self, 
        level: ContextLevel, 
        context_id: str,
        data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validate that parent contexts exist before creating a child context.
        
        Returns:
            Tuple of (is_valid, error_message, guidance)
        """
        if level == ContextLevel.GLOBAL:
            # Global context has no parent - always valid
            return True, None, None
        
        elif level == ContextLevel.PROJECT:
            # Project requires global context
            return self._validate_project_requirements(context_id)
        
        elif level == ContextLevel.BRANCH:
            # Branch requires project context
            return self._validate_branch_requirements(context_id, data)
        
        elif level == ContextLevel.TASK:
            # Task requires branch context
            return self._validate_task_requirements(context_id, data)
        
        return False, f"Unknown context level: {level}", None
    
    def _validate_project_requirements(self, project_id: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Validate project context requirements - more permissive approach."""
        # Check if global context exists
        try:
            from ...infrastructure.database.models import GLOBAL_SINGLETON_UUID
            
            # The global_repo passed to this validator is already user-scoped if needed
            # So we can directly use it to check for global context existence
            # First try the standard singleton ID
            global_context = self.global_repo.get(GLOBAL_SINGLETON_UUID)
            
            # If not found with singleton ID and we have a user_id, the user-scoped repo
            # will automatically handle the user filtering, so try listing contexts
            if not global_context:
                # List all global contexts - if repo is user-scoped, this will only return user contexts
                global_contexts = self.global_repo.list()
                if global_contexts and len(global_contexts) > 0:
                    global_context = global_contexts[0]  # Use the first one found
                    logger.debug(f"Found global context via list() method for user {self.user_id}")
            
            # If no global context found, allow creation with warning
            if not global_context:
                logger.warning(f"No global context found for user {self.user_id} during project context validation - allowing creation with auto-creation")
                # Return success with guidance but allow creation
                return True, None, {
                    "warning": "Global context will be auto-created",
                    "explanation": "The system will automatically create a global context if needed during project context creation.",
                    "auto_creation": True,
                    "recommended_action": "Consider creating global context explicitly for better control",
                    "command": 'manage_context(action="create", level="global", context_id="global", data={"autonomous_rules": {}, "security_policies": {}})'
                }
            
            logger.debug(f"Global context validation passed for user {self.user_id}")
            return True, None, None
            
        except Exception as e:
            logger.warning(f"Global context check error for user {self.user_id}: {e} - allowing permissive creation")
            # Be more permissive - allow creation with warning instead of blocking
            return True, None, {
                "warning": "Could not verify global context existence - allowing creation",
                "explanation": "The system will attempt to create necessary parent contexts automatically",
                "auto_creation": True
            }
    
    def _validate_branch_requirements(self, branch_id: str, data: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Validate branch context requirements."""
        # Handle None data gracefully
        if data is None:
            data = {}
        # Branch needs project_id in data
        project_id = data.get("project_id") or data.get("parent_project_id")
        
        # If project_id is not provided, try to auto-resolve it from git_branch_id
        if not project_id:
            try:
                # Use the branch repository to get the project_id from the existing git branch
                if hasattr(self, 'branch_repo') and self.branch_repo:
                    git_branch = self.branch_repo.get(branch_id)
                    if git_branch and hasattr(git_branch, 'project_id'):
                        project_id = git_branch.project_id
                        logger.info(f"Auto-resolved project_id '{project_id}' from git_branch_id '{branch_id}'")
                        # Add the resolved project_id to the data for consistency
                        data["project_id"] = project_id
            except Exception as e:
                logger.warning(f"Failed to auto-resolve project_id from git_branch_id '{branch_id}': {e}")
        
        # If still no project_id after auto-resolution attempt
        if not project_id:
            return False, "Branch context requires project_id", {
                "error": "Missing required field: project_id",
                "explanation": "Branch contexts must be associated with a project. Could not auto-resolve project_id from git_branch_id.",
                "required_fields": {
                    "project_id": "The ID of the parent project (auto-detection failed)"
                },
                "auto_resolution_failed": f"Attempted to resolve project_id from git_branch_id '{branch_id}' but the branch was not found or has no project_id.",
                "solutions": [
                    "Provide project_id explicitly in the data parameter",
                    "Ensure the git branch exists before creating its context",
                    "Create the git branch first using manage_git_branch"
                ],
                "example": f'manage_context(action="create", level="branch", context_id="{branch_id}", data={{"git_branch_name": "feature/branch"}})',
                "example_with_project": f'manage_context(action="create", level="branch", context_id="{branch_id}", data={{"project_id": "your-project-id", "git_branch_name": "feature/branch"}})'
            }
        
        # Check if project context exists - more permissive approach
        try:
            # The project_repo passed to this validator is already user-scoped if needed
            project_context = self.project_repo.get(project_id)
            if not project_context:
                logger.warning(f"Project context '{project_id}' not found - allowing branch creation with auto-creation")
                # Allow creation with warning and guidance
                return True, None, {
                    "warning": f"Parent project context '{project_id}' will be auto-created",
                    "explanation": "The system will automatically create the required project context during branch context creation",
                    "hierarchy": "Global → Project → Branch → Task",
                    "auto_creation": True,
                    "recommended_actions": [
                        {
                            "description": "Ensure global context exists",
                            "command": 'manage_context(action="get", level="global", context_id="global")'
                        },
                        {
                            "description": "Create project context explicitly for better control",
                            "command": f'manage_context(action="create", level="project", context_id="{project_id}", data={{"project_name": "Your Project"}})'
                        },
                        {
                            "step": 3,
                            "description": "Then create your branch context",
                            "command": f'manage_context(action="create", level="branch", context_id="{branch_id}", data={{"project_id": "{project_id}", "git_branch_name": "your-branch"}})'
                        }
                    ]
                }
            return True, None, None
        except Exception as e:
            logger.debug(f"Project context check error: {e}")
            return False, "Project context must exist first", {
                "error": f"Cannot verify project context: {project_id}",
                "suggestion": f"Create the project context first, then retry creating the branch context"
            }
    
    def _validate_task_requirements(self, task_id: str, data: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Validate task context requirements."""
        # Task needs branch_id (check common field names)
        branch_id = (data.get("branch_id") or 
                    data.get("parent_branch_id") or
                    data.get("git_branch_id"))
        
        if not branch_id:
            return False, "Missing required field: branch_id (or parent_branch_id or git_branch_id)", {
                "error": "Missing required field: branch_id (or parent_branch_id or git_branch_id)",
                "explanation": "Task contexts must be associated with a git branch (task tree)",
                "required_fields": {
                    "branch_id": "The ID of the parent git branch",
                    "alternative_names": ["parent_branch_id", "git_branch_id"]
                },
                "example": f'manage_context(action="create", level="task", context_id="{task_id}", data={{"branch_id": "your-branch-id", "task_data": {{"title": "Task Title"}}}})',
                "tip": "You can find branch IDs using: manage_git_branch(action=\"list\", project_id=\"your-project-id\")"
            }
        
        # Check if branch exists using repository (follows DDD pattern)
        try:
            # Use the branch repository that was injected via constructor
            branch_exists = False
            project_id = None
            
            # Use repository method instead of direct database access
            git_branch = self.branch_repo.get(branch_id) if hasattr(self, 'branch_repo') and self.branch_repo else None
            
            if git_branch:
                branch_exists = True
                project_id = git_branch.project_id if hasattr(git_branch, 'project_id') else None
                logger.debug(f"✅ Branch {branch_id} exists with project_id: {project_id}")
            else:
                logger.debug(f"⚠️ Branch {branch_id} not found via repository")
                    
            if not branch_exists:
                # Get project ID from the task if possible
                project_hint = ""
                if "project_id" in data:
                    project_hint = f", project_id=\"{data['project_id']}\""
                
                logger.warning(f"Branch '{branch_id}' not found in database - allowing task creation with auto-creation")
                # Allow task creation with warning and guidance
                return True, None, {
                    "warning": f"Parent branch context '{branch_id}' will be auto-created",
                    "explanation": "The system will automatically create the required branch context during task context creation if possible",
                    "hierarchy": "Global → Project → Branch → Task",
                    "auto_creation": True,
                    "context_creation_order": [
                        "1. Global context (auto-created)",
                        "2. Project context (auto-created)", 
                        "3. Branch context (auto-created)",
                        "4. Task context (current)"
                    ],
                    "recommended_actions": [
                        {
                            "description": "Create branch context explicitly for better control",
                            "command": f'manage_context(action="create", level="branch", context_id="{branch_id}", data={{"project_id": "your-project-id"{project_hint}}})'
                        },
                        {
                            "description": "Alternative: Create git branch first",
                            "command": f'manage_git_branch(action="create", project_id="your-project-id", git_branch_name="feature/branch")'
                        }
                    ],
                    "alternative": "If you're unsure of the branch_id, list available branches using manage_git_branch"
                }
            return True, None, None
        except Exception as e:
            logger.warning(f"Branch context check error: {e} - allowing permissive task creation")
            # Be more permissive - allow creation with warning instead of blocking
            return True, None, {
                "warning": f"Cannot verify branch context: {branch_id} - allowing creation",
                "explanation": "The system will attempt to create necessary parent contexts automatically",
                "auto_creation": True,
                "error_details": str(e)
            }
    
    def get_hierarchy_status(self) -> Dict[str, Any]:
        """Get the current status of the context hierarchy."""
        status = {
            "hierarchy_levels": ["global", "project", "branch", "task"],
            "current_state": {}
        }
        
        # Check global
        try:
            global_ctx = self.global_repo.get("global_singleton")
            status["current_state"]["global"] = {
                "exists": global_ctx is not None,
                "id": "global_singleton"
            }
        except:
            status["current_state"]["global"] = {"exists": False}
        
        # Get counts for other levels
        try:
            status["current_state"]["projects"] = {
                "count": len(self.project_repo.list()),
                "hint": "Use manage_project(action='list') for details"
            }
        except:
            status["current_state"]["projects"] = {"count": 0}
        
        try:
            status["current_state"]["branches"] = {
                "count": len(self.branch_repo.list()),
                "hint": "Use manage_git_branch(action='list') for details"
            }
        except:
            status["current_state"]["branches"] = {"count": 0}
        
        try:
            status["current_state"]["tasks"] = {
                "count": len(self.task_repo.list()),
                "hint": "Use manage_task(action='list') for details"
            }
        except:
            status["current_state"]["tasks"] = {"count": 0}
        
        return status