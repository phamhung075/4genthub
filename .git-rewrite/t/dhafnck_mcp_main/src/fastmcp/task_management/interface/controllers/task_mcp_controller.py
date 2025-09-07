"""Task MCP Controller

This controller handles MCP tool registration for task management operations,
following DDD principles by delegating business logic to application services.
Enhanced with workflow hints and context enforcement for better AI guidance.
"""

import logging
import asyncio
import uuid
import re
from typing import Dict, Any, Optional, List, Annotated, Union
from datetime import datetime, timezone
from datetime import datetime
from pydantic import Field # type: ignore

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

from .desc import description_loader
from .workflow_hint_enhancer import WorkflowHintEnhancer
from .workflow_guidance.task import TaskWorkflowFactory
from ..utils.error_handler import UserFriendlyErrorHandler
from ..utils.response_formatter import StandardResponseFormatter, ResponseStatus, ErrorCodes

from ...application.dtos.task.create_task_request import CreateTaskRequest
from ...application.dtos.task.list_tasks_request import ListTasksRequest
from ...application.dtos.task.search_tasks_request import SearchTasksRequest
from ...application.dtos.task.update_task_request import UpdateTaskRequest
from ...application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory

from ...application.facades.task_application_facade import TaskApplicationFacade
from ...application.facades.unified_context_facade import UnifiedContextFacade
from ...application.factories.task_facade_factory import TaskFacadeFactory
from ...application.services.context_validation_service import ContextValidationService
from ...application.services.progress_tracking_service import ProgressTrackingService
from ...application.services.hint_generation_service import HintGenerationService
from ...application.services.workflow_analysis_service import WorkflowAnalysisService
from ...application.services.agent_coordination_service import AgentCoordinationService
from ...application.services.parameter_enforcement_service import (
    ParameterEnforcementService, 
    EnforcementLevel,
    EnforcementResult
)
from ...application.services.progressive_enforcement_service import ProgressiveEnforcementService
from ...application.services.response_enrichment_service import (
    ResponseEnrichmentService,
    ContextState,
    ContextStalnessLevel
)
from ...domain.constants import validate_user_id
from ...domain.exceptions.authentication_exceptions import (
    UserAuthenticationRequiredError,
    DefaultUserProhibitedError
)
from ....config.auth_config import AuthConfig
from .auth_helper import get_authenticated_user_id, log_authentication_details

logger = logging.getLogger(__name__)

# Import user context utilities - REQUIRED for authentication
try:
    from fastmcp.auth.middleware.request_context_middleware import get_current_user_id
    from fastmcp.auth.mcp_integration.thread_context_manager import ContextPropagationMixin
except ImportError:
    # Try alternative import path for RequestContextMiddleware
    try:
        from .auth_helper import get_authenticated_user_id as get_current_user_id
    except ImportError:
        # Authentication is required - no fallbacks allowed
        from ...domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError
        def get_current_user_id():
            raise UserAuthenticationRequiredError("User context middleware not available")
    
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
from ...domain.value_objects.progress import ProgressType
from ...domain.value_objects.hints import HintType


class TaskMCPController(ContextPropagationMixin):
    """
    MCP Controller for task management operations.
    
    Handles only MCP protocol concerns and delegates business operations
    to the TaskApplicationFacade following proper DDD layer separation.
    Enhanced with workflow hints, context enforcement, and proper authentication
    context propagation across threads.
    """
    
    def __init__(self, 
                 task_facade_factory: TaskFacadeFactory,
                 context_facade_factory: Optional[UnifiedContextFacadeFactory] = None,
                 project_manager=None, 
                 repository_factory=None,
                 progress_service: Optional[ProgressTrackingService] = None,
                 hint_service: Optional[HintGenerationService] = None,
                 workflow_service: Optional[WorkflowAnalysisService] = None,
                 coordination_service: Optional[AgentCoordinationService] = None):
        """
        Initialize controller with task application facade factory and optional services.
        
        Args:
            task_facade_factory: Factory for creating task application facades
            context_facade_factory: Factory for creating context application facades
            project_manager: Optional project manager instance
            repository_factory: Optional repository factory instance
            progress_service: Optional progress tracking service
            hint_service: Optional hint generation service
            workflow_service: Optional workflow analysis service
            coordination_service: Optional agent coordination service
        """
        self._task_facade_factory = task_facade_factory
        self._context_facade_factory = context_facade_factory or UnifiedContextFacadeFactory()
        self._project_manager = project_manager
        self._repository_factory = repository_factory
        
        # Enhanced services
        self._workflow_hint_enhancer = WorkflowHintEnhancer()
        self._workflow_guidance = TaskWorkflowFactory.create()
        self._validation_service = ContextValidationService()
        self._progress_service = progress_service
        self._hint_service = hint_service
        self._workflow_service = workflow_service
        self._coordination_service = coordination_service
        
        # Phase 2: Initialize enforcement services
        # Start with WARNING level for gradual adoption
        self._enforcement_service = ParameterEnforcementService(EnforcementLevel.WARNING)
        self._progressive_enforcement = ProgressiveEnforcementService(
            enforcement_service=self._enforcement_service,
            default_level=EnforcementLevel.WARNING
        )
        
        # Phase 3: Initialize response enrichment service
        self._response_enrichment = ResponseEnrichmentService()
        
        logger.info("TaskMCPController initialized with enhanced workflow hints, context enforcement, parameter enforcement, and response enrichment")
        
        # Store last known git_branch_id for context operations
        self._last_git_branch_id = None
    
    def _standardize_facade_response(self, facade_response: Dict[str, Any], operation: str) -> Dict[str, Any]:
        """
        Convert facade response to standardized format using StandardResponseFormatter.
        
        Args:
            facade_response: Response from facade method
            operation: Operation name for tracking
            
        Returns:
            Standardized response using StandardResponseFormatter
        """
        if facade_response.get("success", False):
            # Extract data from facade response
            data = {}
            for key, value in facade_response.items():
                if key not in ["success", "action", "error", "error_code"]:
                    data[key] = value
            
            # Add workflow guidance if present
            workflow_guidance = None
            if "workflow_guidance" in data:
                workflow_guidance = data.pop("workflow_guidance")
            
            return StandardResponseFormatter.create_success_response(
                operation=operation,
                data=data,
                workflow_guidance=workflow_guidance
            )
        else:
            # Handle error response
            error_message = facade_response.get("error", "Unknown error occurred")
            error_code = facade_response.get("error_code", ErrorCodes.OPERATION_FAILED)
            
            # Extract metadata
            metadata = {}
            for key, value in facade_response.items():
                if key not in ["success", "action", "error", "error_code"]:
                    metadata[key] = value
            
            return StandardResponseFormatter.create_error_response(
                operation=operation,
                error=error_message,
                error_code=error_code,
                metadata=metadata if metadata else None
            )
    
    def _enrich_task_response(
        self,
        response: Dict[str, Any],
        action: str,
        task_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Enrich task response with context intelligence and visual indicators.
        
        Args:
            response: The response from the facade
            action: The action that was performed
            task_data: Optional task data from the response
            
        Returns:
            Enriched response with visual indicators and contextual guidance
        """
        if not response.get("success") or not task_data:
            return response
        
        try:
            # Get context state if possible
            context_state = None
            task_id = task_data.get("id")
            if task_id and self._context_facade_factory:
                try:
                    context_facade = self._context_facade_factory.create()
                    context_result = context_facade.get_context(
                        level="task",
                        context_id=task_id
                    )
                    
                    if context_result.get("success") and context_result.get("context"):
                        context_data = context_result["context"]
                        context_state = self._response_enrichment.get_context_state(
                            task_id=task_id,
                            context_data=context_data
                        )
                except Exception as e:
                    logger.debug(f"Could not get context state for task {task_id}: {e}")
            
            # Enrich the response
            enrichment = self._response_enrichment.enrich_task_response(
                task_data=task_data,
                action=action,
                context_state=context_state
            )
            
            # Add enrichment to response
            if "workflow_guidance" not in response:
                response["workflow_guidance"] = {}
            
            # Add visual indicators
            if enrichment.visual_indicators:
                response["workflow_guidance"]["visual_indicators"] = enrichment.visual_indicators
            
            # Add context hints
            if enrichment.context_hints:
                if "hints" not in response["workflow_guidance"]:
                    response["workflow_guidance"]["hints"] = []
                response["workflow_guidance"]["hints"].extend(enrichment.context_hints)
            
            # Add actionable suggestions
            if enrichment.actionable_suggestions:
                response["workflow_guidance"]["actionable_suggestions"] = enrichment.actionable_suggestions
            
            # Add template examples
            if enrichment.template_examples:
                response["workflow_guidance"]["template_examples"] = enrichment.template_examples
            
            # Add warnings
            if enrichment.warnings:
                if "warnings" not in response["workflow_guidance"]:
                    response["workflow_guidance"]["warnings"] = []
                response["workflow_guidance"]["warnings"].extend(enrichment.warnings)
            
            # Add metadata
            response["workflow_guidance"]["enrichment_metadata"] = enrichment.metadata
            
        except Exception as e:
            logger.warning(f"Failed to enrich response for action {action}: {e}")
        
        return response
    
    def register_tools(self, mcp: "FastMCP"):
        """Register task management tools with FastMCP."""
        
        # Get tool descriptions
        manage_task_desc = self._get_task_management_descriptions().get("manage_task", {})
        
        @mcp.tool(name="manage_task", description=manage_task_desc["description"])
        def manage_task(
            action: Annotated[str, Field(description=manage_task_desc["parameters"].get("action", "Task management action"))],
            git_branch_id: Annotated[Optional[str], Field(description="Git branch UUID identifier - contains all context (project_id, git_branch_name, user_id). Required for 'create' action, optional for others when task_id is provided")] = None,
            task_id: Annotated[Optional[str], Field(description=manage_task_desc["parameters"].get("task_id", "Task identifier"))] = None,
            title: Annotated[Optional[str], Field(description=manage_task_desc["parameters"].get("title", "Task title"))] = None,
            description: Annotated[Optional[str], Field(description=manage_task_desc["parameters"].get("description", "Task description"))] = None,
            status: Annotated[Optional[str], Field(description=manage_task_desc["parameters"].get("status", "Task status"))] = None,
            priority: Annotated[Optional[str], Field(description=manage_task_desc["parameters"].get("priority", "Task priority"))] = None,
            details: Annotated[Optional[str], Field(description=manage_task_desc["parameters"].get("details", "Task details"))] = None,
            estimated_effort: Annotated[Optional[str], Field(description=manage_task_desc["parameters"].get("estimated_effort", "Estimated effort"))] = None,
            assignees: Annotated[Optional[Union[List[str], str]], Field(description=manage_task_desc["parameters"].get("assignees", "Task assignees"))] = None,
            labels: Annotated[Optional[Union[List[str], str]], Field(description=manage_task_desc["parameters"].get("labels", "Task labels"))] = None,
            due_date: Annotated[Optional[str], Field(description=manage_task_desc["parameters"].get("due_date", "Due date"))] = None,
            context_id: Annotated[Optional[str], Field(description=manage_task_desc["parameters"].get("context_id", "Context ID for task completion validation"))] = None,
            force_full_generation: Annotated[Union[bool, str], Field(description=manage_task_desc["parameters"].get("force_full_generation", "Force full generation"))] = False,
            include_context: Annotated[Union[bool, str], Field(description=manage_task_desc["parameters"].get("include_context", "Whether to include full context data in task responses. Default: False for tests/backward compatibility"))] = False,
            limit: Annotated[Optional[Union[int, str]], Field(description=manage_task_desc["parameters"].get("limit", "Result limit"))] = None,
            query: Annotated[Optional[str], Field(description=manage_task_desc["parameters"].get("query", "Search query or dependency_id for add/remove_dependency (deprecated, use dependency_id instead)"))] = None,
            dependency_id: Annotated[Optional[str], Field(description=manage_task_desc["parameters"].get("dependency_id", "Dependency task ID for add/remove_dependency actions (flattened from dependency_data)"))] = None,
            dependencies: Annotated[Optional[Union[List[str], str]], Field(description="List of task IDs this task depends on (for create action)")] = None,
            # Enhanced completion parameters (merged from complete_task_with_update)
            completion_summary: Annotated[Optional[str], Field(description=manage_task_desc["parameters"].get("completion_summary", "Summary of what was accomplished (for complete action)"))] = None,
            testing_notes: Annotated[Optional[str], Field(description=manage_task_desc["parameters"].get("testing_notes", "Description of testing performed (for complete action)"))] = None,
            user_id: Annotated[Optional[str], Field(description="User identifier for authentication. Optional, defaults to authenticated user context")] = None
        ) -> Dict[str, Any]:
            # Parse labels, assignees, and dependencies if they come as strings
            parsed_labels = self._parse_string_list(labels, "labels") if labels is not None else None
            parsed_assignees = self._parse_string_list(assignees, "assignees") if assignees is not None else None
            parsed_dependencies = self._parse_string_list(dependencies, "dependencies") if dependencies is not None else None
            
            # Coerce limit to int if it's a string
            coerced_limit = None
            if limit is not None:
                if isinstance(limit, str):
                    try:
                        coerced_limit = int(limit)
                    except ValueError:
                        return StandardResponseFormatter.create_validation_error_response(
                            operation="manage_task",
                            field="limit",
                            expected="An integer or string representation of an integer",
                            actual=str(limit),
                            hint="Use a valid integer like 5 or '5'"
                        )
                elif isinstance(limit, (int, float)):
                    # Reject floats
                    if isinstance(limit, float) and not limit.is_integer():
                        return StandardResponseFormatter.create_validation_error_response(
                            operation="manage_task",
                            field="limit",
                            expected="An integer value, not a float",
                            actual=str(limit),
                            hint="Use a whole number like 5, not 5.5"
                        )
                    coerced_limit = int(limit)
                else:
                    # Invalid type (list, dict, etc.)
                    return StandardResponseFormatter.create_validation_error_response(
                        operation="manage_task",
                        field="limit",
                        expected="An integer or string representation of an integer",
                        actual=f"{type(limit).__name__}: {limit}",
                        hint="Use a valid integer like 5 or '5'"
                    )
                
                # Validate limit range (1-100)
                if coerced_limit is not None:
                    if coerced_limit < 1 or coerced_limit > 100:
                        return StandardResponseFormatter.create_validation_error_response(
                            operation="manage_task",
                            field="limit",
                            expected="An integer between 1 and 100",
                            actual=str(coerced_limit),
                            hint="Use a value between 1 and 100 for the limit parameter"
                        )
            
            # Coerce boolean parameters
            coerced_force_full_generation = self._coerce_to_bool(force_full_generation, "force_full_generation")
            coerced_include_context = self._coerce_to_bool(include_context, "include_context")
            
            return self._handle_task_management(
                action=action,
                git_branch_id=git_branch_id,
                task_id=task_id,
                title=title,
                description=description,
                status=status,
                priority=priority,
                details=details,
                estimated_effort=estimated_effort,
                assignees=parsed_assignees,  # Use parsed assignees
                labels=parsed_labels,  # Use parsed labels
                due_date=due_date,
                context_id=context_id,
                force_full_generation=coerced_force_full_generation,
                include_context=coerced_include_context,
                limit=coerced_limit,  # Use coerced limit
                query=query,
                dependency_id=dependency_id,
                dependencies=parsed_dependencies,
                completion_summary=completion_summary,
                testing_notes=testing_notes,
                user_id=user_id
            )
        
        # NOTE: Context enforcing functionality is integrated into the main manage_task tool
        # No separate tools needed - use manage_task with appropriate actions
    
    # Public API method for direct access (tests, etc.)
    def manage_task(self, *args, **kwargs):
        """Public API method that delegates to the internal handler."""
        return self._handle_task_management(*args, **kwargs)
    
    def _get_facade_for_request(self, task_id: Optional[str] = None, git_branch_id: Optional[str] = None, user_id: Optional[str] = None) -> TaskApplicationFacade:
        """
        Get a TaskApplicationFacade with the appropriate context.
        If a mock facade is present, it will be used for testing purposes.
        Otherwise, a new facade is created based on the provided context.
        """
        # Prioritize mock facade for testing
        if hasattr(self, '_task_facade') and self._task_facade is not None:
             return self._task_facade

        # Derive context from provided identifiers (only project_id and git_branch_name)
        project_id, git_branch_name, derived_user_id = self._derive_context_from_identifiers(task_id, git_branch_id, user_id)
        
        # Use provided user_id if available, otherwise use derived user_id
        effective_user_id = user_id or derived_user_id
        
        logger.debug(f"Derived context for task_id={task_id}, git_branch_id={git_branch_id}: project_id={project_id}, git_branch_name={git_branch_name}, provided_user_id={user_id}, effective_user_id={effective_user_id}")
        
        # Use resolved git_branch_id if available
        effective_git_branch_id = git_branch_id or getattr(self, '_resolved_git_branch_id', None)
        return self._get_task_facade(project_id, git_branch_name, effective_user_id, effective_git_branch_id)


    def handle_crud_operations(self, facade: TaskApplicationFacade, action: str, git_branch_id: Optional[str] = None,
                              task_id: Optional[str] = None, title: Optional[str] = None, 
                              description: Optional[str] = None, status: Optional[str] = None, 
                              priority: Optional[str] = None, details: Optional[str] = None, 
                              estimated_effort: Optional[str] = None, 
                              assignees: Optional[List[str]] = None, 
                              labels: Optional[List[str]] = None, 
                              due_date: Optional[str] = None, 
                              context_id: Optional[str] = None,
                              force_full_generation: bool = False,
                              include_context: bool = False,
                              dependencies: Optional[List[str]] = None,
                              completion_summary: Optional[str] = None,
                              testing_notes: Optional[str] = None,
                              # Phase 1: Context tracking parameters  
                              work_notes: Optional[str] = None,
                              progress_made: Optional[str] = None,
                              files_modified: Optional[List[str]] = None,
                              decisions_made: Optional[List[str]] = None,
                              blockers_encountered: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Handle core task operations by converting MCP parameters to DTOs
        and delegating to the application facade.
        """
        
        # Pre-validate parameter formats with helpful error messages
        validation_result = self._validate_parameters(
            action=action, labels=labels, assignees=assignees
        )
        if not validation_result["valid"]:
            return validation_result
        
        # Extract the new context tracking parameters from method parameters
        # (These are now part of the method signature)
        
        try:
            # Use provided facade if available, otherwise create one
            if facade is None:
                facade = self._get_facade_for_request(git_branch_id=git_branch_id)
            
            if action == "create":
                if not title:
                    return StandardResponseFormatter.create_validation_error_response(
                        operation="create_task",
                        field="title",
                        expected="A non-empty string for the task title",
                        hint="Include 'title' in your request body"
                    )
                
                return self._handle_create_task(
                    facade, git_branch_id, title, description, status, priority, 
                    details, estimated_effort, assignees, labels, due_date, dependencies
                )
            elif action == "update":
                if not task_id:
                    return StandardResponseFormatter.create_validation_error_response(
                        operation="update_task",
                        field="task_id",
                        expected="A valid task_id string",
                        hint="Include 'task_id' in your request body"
                    )
                
                # Phase 2: Enforce parameter requirements
                provided_params = {
                    "work_notes": work_notes,
                    "progress_made": progress_made,
                    "files_modified": files_modified,
                    "decisions_made": decisions_made,
                    "blockers_encountered": blockers_encountered,
                    "details": details,
                    "description": description,
                    "status": status
                }
                # Filter out None values
                provided_params = {k: v for k, v in provided_params.items() if v is not None}
                
                # Get agent ID (could be from headers, session, or a parameter)
                agent_id = "default_agent"  # TODO: Extract from request context
                
                # Enforce with progressive enforcement
                enforcement_result = self._progressive_enforcement.enforce_with_progression(
                    action="update",
                    provided_params=provided_params,
                    agent_id=agent_id
                )
                
                # If enforcement blocks the operation, return with helpful guidance
                if not enforcement_result.allowed:
                    return {
                        "success": False,
                        "error": enforcement_result.message,
                        "enforcement_level": enforcement_result.level.value,
                        "missing_required": enforcement_result.missing_required,
                        "missing_recommended": enforcement_result.missing_recommended,
                        "hints": enforcement_result.hints,
                        "examples": enforcement_result.examples,
                        "workflow_guidance": {
                            "hint": "📝 Context parameters are required for task updates",
                            "why": "This helps maintain project context and track work progress",
                            "next_actions": [
                                {
                                    "action": "update with context",
                                    "example": enforcement_result.examples.get("example_command", {})
                                }
                            ]
                        }
                    }
                
                # Add enforcement hints to response if there were warnings
                enforcement_hints = []
                if enforcement_result.missing_required:
                    enforcement_hints.extend(enforcement_result.hints)
                
                # Phase 1: Handle context tracking parameters if provided
                if any([work_notes, progress_made, files_modified, decisions_made, blockers_encountered]):
                    # Update task context with provided information
                    context_update = {}
                    if work_notes:
                        context_update["work_notes"] = work_notes
                    if progress_made:
                        context_update["progress_made"] = progress_made
                    if files_modified:
                        context_update["files_modified"] = files_modified
                    if decisions_made:
                        context_update["decisions_made"] = decisions_made
                    if blockers_encountered:
                        context_update["blockers_encountered"] = blockers_encountered
                    
                    # Update context through facade if available
                    if self._context_facade_factory:
                        try:
                            context_facade = self._context_facade_factory.create()
                            context_result = context_facade.update_context(
                                level="task",
                                context_id=task_id,
                                data=context_update,
                                propagate_changes=True
                            )
                            if not context_result.get("success"):
                                logger.warning(f"Failed to update context for task {task_id}: {context_result.get('error')}")
                        except Exception as e:
                            logger.warning(f"Error updating context for task {task_id}: {e}")
                
                # Check if this is a progress report (when details contains progress info)
                if details and ("progress:" in details.lower() or "completed:" in details.lower() or "implemented:" in details.lower()):
                    # Extract progress percentage if status is changing to in_progress
                    percentage = None
                    if status == "in_progress" and estimated_effort:
                        # Try to parse percentage from estimated_effort if it looks like "40%" or "40"
                        try:
                            percentage = int(estimated_effort.strip('%'))
                        except:
                            pass
                    
                    # Use report_progress for better tracking
                    result = self.report_progress(
                        task_id=task_id,
                        progress_type="update",
                        description=details or description or "Progress update",
                        percentage=percentage
                    )
                else:
                    # Regular update
                    result = self._handle_update_task(
                        facade, task_id, title, description, status, priority, 
                        details, estimated_effort, assignees, labels, due_date, context_id
                    )
                
                # Add enforcement hints if there were warnings
                if enforcement_hints and result.get("success"):
                    if "workflow_guidance" not in result:
                        result["workflow_guidance"] = {}
                    if "hints" not in result["workflow_guidance"]:
                        result["workflow_guidance"]["hints"] = []
                    result["workflow_guidance"]["hints"].extend(enforcement_hints)
                
                # Add vision alignment info if requested
                if result.get("success") and include_context:
                    vision_result = self.get_vision_alignment(task_id)
                    if vision_result.get("success"):
                        result["vision_alignment"] = vision_result.get("vision_alignment")
                
                # Phase 3: Enrich response with context intelligence and visual indicators
                if result.get("success") and result.get("data", {}).get("task"):
                    result = self._enrich_task_response(
                        response=result,
                        action="update",
                        task_data=result["data"]["task"]
                    )
                
                return result
            elif action == "get":
                # Always load context for get to provide better AI assistance
                result = self._handle_get_task(facade, task_id, True, True)  # Force include_context=True, include_dependencies=True
                
                # Add workflow hints (now always included)
                if result.get("success") and task_id:
                    hints_result = self.get_workflow_hints(task_id, include_agent_suggestions=True)
                    if hints_result.get("success"):
                        result["workflow_hints"] = hints_result.get("hints", {})
                
                return result
            elif action == "delete":
                if not task_id:
                    return StandardResponseFormatter.create_validation_error_response(
                        operation="delete_task",
                        field="task_id",
                        expected="A valid task_id string",
                        hint="Include 'task_id' in your request body"
                    )
                return self._handle_delete_task(facade, task_id)
            elif action == "complete":
                if not task_id:
                    return StandardResponseFormatter.create_validation_error_response(
                        operation="complete_task",
                        field="task_id",
                        expected="A valid task_id string",
                        hint="Include 'task_id' in your request body"
                    )
                
                # Regular completion without mandatory context enforcement
                # Use completion_summary if provided, otherwise fall back to description
                if completion_summary or description:
                    # Use the regular facade completion method (context is optional)
                    result = facade.complete_task(
                        task_id=task_id,
                        completion_summary=completion_summary or description,
                        testing_notes=testing_notes or details  # Use testing_notes or details field
                    )
                else:
                    # Regular completion - but encourage context update with rich guidance
                    return {
                        "success": False,
                        "error": "Task completion requires completion_summary parameter",
                        "reason": "A completion summary is required to track what was accomplished",
                        "solution": "Use the 'complete' action with 'completion_summary' parameter",
                        "workflow_guidance": {
                            "hint": "📝 Tasks must be completed with a summary of what was accomplished",
                            "why": "This helps maintain project context and enables better AI collaboration",
                            "next_actions": [
                                {
                                    "action": "complete with summary",
                                    "description": "Complete the task with details",
                                    "example": {
                                        "action": "complete",
                                        "task_id": task_id,
                                        "completion_summary": "Feature implemented successfully with all tests passing",
                                        "testing_notes": "Added unit tests and integration tests"
                                    }
                                },
                                {
                                    "action": "update progress first",
                                    "description": "Update task progress before completing",
                                    "example": {
                                        "action": "update",
                                        "task_id": task_id,
                                        "details": "Describe current progress",
                                        "status": "in_progress"
                                    }
                                }
                            ]
                        }
                    }
                
                # Always enhance with comprehensive workflow guidance for successful completions
                # For failed completions, pass through the detailed error from the use case
                if result.get("success"):
                    result = self._enhance_with_workflow_hints(
                        result, "complete", {
                            "task_id": task_id,
                            "completion_summary": completion_summary,
                            "testing_notes": testing_notes
                        }
                    )
                    
                    # Phase 3: Enrich response with context intelligence and visual indicators
                    if result.get("data", {}).get("task"):
                        result = self._enrich_task_response(
                            response=result,
                            action="complete",
                            task_data=result["data"]["task"]
                        )
                else:
                    # For failures, ensure we include task_id and action in the error response
                    if "task_id" not in result:
                        result["task_id"] = task_id
                    if "action" not in result:
                        result["action"] = "complete"
                    
                    # Log the detailed error for debugging
                    logger.error(f"Task completion failed for {task_id}: {result.get('message', result.get('error', 'Unknown error'))}")
                
                return result
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "error_code": "UNKNOWN_ACTION",
                    "field": "action",
                    "expected": "One of: create, update, get, delete, complete, list, search, next, add_dependency, remove_dependency",
                    "hint": "Check the 'action' parameter for typos"
                }
                
        except Exception as e:
            return UserFriendlyErrorHandler.handle_error(
                e, 
                f"task {action} operation",
                {"action": action}
            )
    
    def handle_list_search_next(self, action: str, git_branch_id: Optional[str] = None,
                               status: Optional[str] = None, priority: Optional[str] = None, 
                               assignees: Optional[List[str]] = None, 
                               labels: Optional[List[str]] = None, 
                               limit: Optional[int] = None, 
                               query: Optional[str] = None,
                               include_context: bool = False) -> Dict[str, Any]:
        """
        Handle list, search, and next operations by converting MCP parameters 
        to DTOs and delegating to the application facade.
        """
        
        try:
            facade = self._get_facade_for_request(git_branch_id)
            
            if action == "list":
                return self._handle_list_tasks(
                    facade, status, priority, assignees, labels, limit, git_branch_id, include_context
                )
            elif action == "search":
                return self._handle_search_tasks(facade, query, limit, git_branch_id, include_context)
            elif action == "next":
                # Always load context for next to provide better AI assistance
                result = self._handle_next_task(facade, git_branch_id, True)  # Force include_context=True
                
                # Add workflow hints for next task (now always included)
                if result.get("success") and result.get("task"):
                    task_id = result["task"].get("id")
                    if task_id:
                        hints_result = self.get_workflow_hints(task_id, include_agent_suggestions=True)
                        if hints_result.get("success"):
                            result["workflow_hints"] = hints_result.get("hints", {})
                        
                        # Add AI reminders for next task
                        task = result["task"]
                        task["ai_reminders"] = {
                            "important": "📋 This is your next recommended task!",
                            "start_guidance": {
                                "step_1": "Review the task requirements",
                                "step_2": "Update status to 'in_progress' when starting",
                                "step_3": "Create or update context to track progress"
                            },
                            "quick_start": {
                                "action": "update",
                                "task_id": task_id,
                                "status": "in_progress",
                                "details": "Starting work on this task"
                            }
                        }
                        result["task"] = task
                
                return result
            else:
                return {"success": False, "error": f"Invalid action: {action}"}
                
        except Exception as e:
            return UserFriendlyErrorHandler.handle_error(
                e, 
                f"task {action} operation",
                {"action": action}
            )
    
    # Private helper methods for converting MCP parameters to DTOs
    
    def _handle_create_task(self, facade: TaskApplicationFacade, git_branch_id: Optional[str], 
                           title: Optional[str], description: Optional[str], status: Optional[str], 
                           priority: Optional[str], details: Optional[str], 
                           estimated_effort: Optional[str], assignees: Optional[List[str]], 
                           labels: Optional[List[str]], due_date: Optional[str],
                           dependencies: Optional[List[str]] = None) -> Dict[str, Any]:
        """Convert MCP create parameters to DTO and delegate to facade."""
        if not title:
            return self._create_standardized_error(
                operation="create_task",
                field="title",
                expected="A valid title string",
                hint="Include 'title' in your request body"
            )
        
        if not git_branch_id:
            return self._create_standardized_error(
                operation="create_task",
                field="git_branch_id",
                expected="A valid git_branch_id string",
                hint="Include 'git_branch_id' in your request body"
            )
        
        request = CreateTaskRequest(
            title=title,
            description=description or f"Description for {title}",
            git_branch_id=git_branch_id,
            status=status,
            priority=priority,
            details=details or "",
            estimated_effort=estimated_effort,
            assignees=assignees or [],
            labels=labels or [],
            due_date=due_date,
            dependencies=dependencies or []
            # context_id automatically set to task_id in CreateTaskUseCase
        )
        
        # Store git_branch_id for context operations
        self._last_git_branch_id = git_branch_id
        
        result = facade.create_task(request)
        
        # Ensure result is a dictionary before accessing it
        if not isinstance(result, dict):
            logger.error(f"create_task returned non-dict result: {type(result)}")
            return self._response_formatter.create_error_response(
                operation="create",
                error="Internal error: Invalid response format from task creation",
                error_code=ErrorCodes.INTERNAL_ERROR
            )
        
        if result.get("success"):
            # Automatically create context for the new task
            task_data = result.get("task", {})
            task_id = task_data.get("id")
            
            if task_id and self._context_facade_factory:
                logger.info(f"Attempting to create context for task {task_id}")
                try:
                    # Create context facade
                    context_facade = self._context_facade_factory.create_facade(
                        git_branch_id=self._last_git_branch_id
                    )
                    
                    # Create the context using synchronous method
                    # The create_context method is NOT async, so we call it directly
                    context_result = context_facade.create_context(
                        level="task",
                        context_id=task_id,
                        data={
                            "title": title,
                            "description": description or f"Description for {title}",
                            "status": status,
                            "priority": priority,
                            "assignees": assignees,
                            "labels": labels,
                            "estimated_effort": estimated_effort,
                            "due_date": due_date
                        }
                    )
                    
                    logger.info(f"Context creation result: {context_result}")
                    
                    if context_result.get("success"):
                        # Update task with context_id
                        update_request = UpdateTaskRequest(
                            task_id=task_id,
                            context_id=task_id  # Context ID is same as task ID
                        )
                        update_result = facade.update_task(task_id, update_request)
                        
                        # Add context data to response
                        result["task"]["context_id"] = task_id
                        result["task"]["context_data"] = context_result.get("context", {})
                        result["task"]["context_available"] = True
                        
                        logger.info(f"Context automatically created for task {task_id}")
                    else:
                        logger.warning(f"Failed to create context for task {task_id}: {context_result.get('error')}")
                        
                except Exception as e:
                    logger.error(f"Error creating context for task {task_id}: {e}")
                    # Don't fail the task creation if context creation fails
                    
        # Enhance response with comprehensive workflow guidance
        if result.get("success"):
            result = self._enhance_with_workflow_hints(
                result, "create", {
                    "git_branch_id": git_branch_id,
                    "title": title,
                    "task_id": result.get("task", {}).get("id")
                }
            )
            
            # Phase 3: Enrich response with context intelligence and visual indicators
            if result.get("task"):
                enriched_result = self._enrich_task_response(
                    response={"success": True, "data": {"task": result["task"]}},
                    action="create",
                    task_data=result["task"]
                )
                # Merge enrichment back into result
                if enriched_result.get("workflow_guidance"):
                    if "workflow_guidance" not in result:
                        result["workflow_guidance"] = {}
                    result["workflow_guidance"].update(enriched_result["workflow_guidance"])
        
        # Convert to standardized response format
        return self._standardize_response(
            result,
            operation="create_task",
            metadata={
                "git_branch_id": git_branch_id,
                "title": title
            }
        )
    
    def _handle_update_task(self, facade: TaskApplicationFacade, task_id: Optional[str], title: Optional[str], 
                           description: Optional[str], status: Optional[str], 
                           priority: Optional[str], details: Optional[str], 
                           estimated_effort: Optional[str], assignees: Optional[List[str]], 
                           labels: Optional[List[str]], due_date: Optional[str],
                           context_id: Optional[str] = None) -> Dict[str, Any]:
        """Convert MCP update parameters to DTO and delegate to facade."""
        if not task_id:
            return self._create_standardized_error(
                operation="update_task",
                field="task_id",
                expected="A valid task_id uuid",
                hint="Include 'task_id' in your request body"
            )
        
        request = UpdateTaskRequest(
            task_id=task_id,
            title=title,
            description=description,
            status=status,
            priority=priority,
            details=details,
            estimated_effort=estimated_effort,
            assignees=assignees,
            labels=labels,
            due_date=due_date,
            context_id=context_id
        )
        
        result = facade.update_task(task_id, request)
        
        # Ensure result is a dictionary before accessing it
        if not isinstance(result, dict):
            logger.error(f"update_task returned non-dict result: {type(result)}")
            return self._response_formatter.create_error_response(
                operation="update",
                error="Internal error: Invalid response format from task update",
                error_code=ErrorCodes.INTERNAL_ERROR
            )
        
        # Enhance response with comprehensive workflow guidance
        if result.get("success"):
            result = self._enhance_with_workflow_hints(
                result, "update", {
                    "task_id": task_id,
                    "status": status,
                    "details": details
                }
            )
        
        # Convert to standardized response format
        return self._standardize_response(
            result,
            operation="update_task",
            metadata={
                "task_id": task_id,
                "updated_fields": [f for f in ["title", "description", "status", "priority", "details", 
                                              "estimated_effort", "assignees", "labels", "due_date"] 
                                 if locals().get(f) is not None]
            }
        )
    
    def _handle_get_task(
        self,
        facade: TaskApplicationFacade,
        task_id: Optional[str],
        include_context: bool = False,
        include_dependencies: bool = True,
    ) -> Dict[str, Any]:
        """Handle get task request synchronously (backward-compatible)."""
        if not task_id:
            return {
                "success": False, 
                "error": "task_id is required for get",
                "error_code": "MISSING_FIELD",
                "field": "task_id",
                "expected": "A valid task_id uuid",
                "hint": "Include 'task_id' in your request body"
            }

        try:
            # Direct synchronous call to facade (which is also synchronous)
            result = facade.get_task(task_id, include_context, include_dependencies)
            
            # Ensure result is a dictionary before accessing it
            if not isinstance(result, dict):
                logger.error(f"get_task returned non-dict result: {type(result)}")
                return self._response_formatter.create_error_response(
                    operation="get",
                    error="Internal error: Invalid response format from task retrieval",
                    error_code=ErrorCodes.INTERNAL_ERROR
                )
            
            if result.get("success") and result.get("task"):
                task = result["task"]
                
                # Add AI reminders and templates
                task["ai_reminders"] = {
                    "important": "📝 Remember to update progress and context!",
                    "update_example": {
                        "tool": "manage_task",
                        "params": {
                            "action": "update",
                            "task_id": task["id"],
                            "details": "Describe what you've done",
                            "status": "in_progress"
                        }
                    },
                    "completion_example": {
                        "tool": "manage_task",
                        "params": {
                            "action": "complete",
                            "task_id": task["id"],
                            "completion_summary": "Brief summary of what was accomplished",
                            "testing_notes": "Description of tests performed"
                        }
                    }
                }
                
                # Check task status and provide appropriate guidance
                if task.get("status") == "todo":
                    task["ai_reminders"]["next_step"] = "Start by updating status to 'in_progress'"
                elif task.get("status") == "in_progress":
                    task["ai_reminders"]["next_step"] = "Remember to track your progress with updates"
                
                # Check if context exists
                if not task.get("context_id"):
                    task["ai_reminders"]["warning"] = "⚠️ No context created yet - create one before completing!"
                
                result["task"] = task
            
            # Enhance response with comprehensive workflow guidance
            if result.get("success"):
                result = self._enhance_with_workflow_hints(
                    result, "get", {
                        "task_id": task_id,
                        "include_context": include_context
                    }
                )
            
            return result
        except Exception as e:
            return UserFriendlyErrorHandler.handle_error(
                e, 
                "task retrieval",
                {"task_id": task_id}
            )
    
    def _handle_delete_task(self, facade: TaskApplicationFacade, task_id: Optional[str]) -> Dict[str, Any]:
        """Handle delete task request."""
        if not task_id:
            return {"success": False, "error": "task_id is required for delete"}
        
        return facade.delete_task(task_id)
    
    def _handle_complete_task(self, facade: TaskApplicationFacade, task_id: Optional[str], 
                            completion_summary: Optional[str] = None,
                            testing_notes: Optional[str] = None) -> Dict[str, Any]:
        """Handle complete task request."""
        if not task_id:
            return {
                "success": False, 
                "error": "task_id is required for complete",
                "error_code": "MISSING_FIELD",
                "field": "task_id",
                "expected": "A valid task_id uuid",
                "hint": "Include 'task_id' in your request body"
            }
        
        return facade.complete_task(task_id, completion_summary, testing_notes)
    
    def _handle_list_tasks(self, facade: TaskApplicationFacade, status: Optional[str], priority: Optional[str], 
                          assignees: Optional[List[str]], labels: Optional[List[str]], 
                          limit: Optional[int], git_branch_id: Optional[str] = None, 
                          include_context: bool = False) -> Dict[str, Any]:
        """Convert MCP list parameters to DTO and delegate to facade."""

        # Enhanced debug logging for MCP task listing
        logger.debug("=" * 80)
        logger.debug(f"🔍 MCP TASK LIST REQUEST")
        logger.debug(f"🎯 Parameters: status={status}, priority={priority}, limit={limit}")
        logger.debug(f"🌿 Git branch ID: {git_branch_id}")
        logger.debug(f"👤 Assignees: {assignees}")
        logger.debug(f"🏷️ Labels: {labels}")
        logger.debug(f"📖 Include context: {include_context}")
        logger.debug(f"🏭 Facade type: {type(facade)}")

        # git_branch_id is optional – when omitted we list tasks across all branches for the user/project.
        
        logger.debug("📋 Building ListTasksRequest...")
        request = ListTasksRequest(
            git_branch_id=git_branch_id,
            status=status,
            priority=priority,
            assignees=assignees,
            labels=labels,
            limit=limit
        )
        logger.debug(f"✅ ListTasksRequest created: {request}")
        
        # Use minimal=True for optimized performance (only essential fields) unless context is requested
        minimal = not include_context  # If context is requested, don't use minimal mode
        logger.debug(f"⚡ Performance mode: minimal={minimal} (include_context={include_context})")
        
        logger.debug("🔍 Calling facade.list_tasks...")
        result = facade.list_tasks(request, include_dependencies=True, minimal=minimal, include_context=include_context)
        logger.debug(f"✅ Facade returned: {type(result)}, success={result.get('success') if isinstance(result, dict) else 'N/A'}")
        
        # Ensure result is a dictionary before accessing it
        if not isinstance(result, dict):
            logger.error("=" * 80)
            logger.error(f"❌ MCP TASK LIST ERROR: list_tasks returned non-dict result: {type(result)}")
            logger.error(f"❌ Result value: {result}")
            logger.error("=" * 80)
            return self._response_formatter.create_error_response(
                operation="list",
                error="Internal error: Invalid response format from task listing",
                error_code=ErrorCodes.INTERNAL_ERROR
            )
        
        logger.debug(f"🔍 Result validation passed. Success: {result.get('success')}")
        if result.get("success") and result.get("tasks"):
            tasks = result["tasks"]
            logger.debug(f"📋 Tasks found: {len(tasks)} tasks")
            
            # Log first few tasks for debugging
            if tasks:
                logger.debug("📝 First task details:")
                for i, task in enumerate(tasks[:3]):  # Log first 3 tasks
                    if isinstance(task, dict):
                        logger.debug(f"   Task {i+1}: ID={task.get('id', 'N/A')}, Title={task.get('title', 'N/A')}, Status={task.get('status', 'N/A')}")
                    else:
                        logger.debug(f"   Task {i+1}: {type(task)} - {task}")
                if len(tasks) > 3:
                    logger.debug(f"   ... and {len(tasks) - 3} more tasks")
        else:
            logger.debug(f"📝 No tasks found or operation failed. Success: {result.get('success')}, Tasks key present: {'tasks' in result}")
            if result.get("error"):
                logger.debug(f"🚨 Error in result: {result.get('error')}")
        
        if result.get("success") and result.get("tasks"):
            tasks = result["tasks"]
            
            # Add helpful summary
            result["summary"] = {
                "total_tasks": len(tasks),
                "by_status": {},
                "by_priority": {},
                "recommendations": []
            }
            
            # Count tasks by status and priority
            for task in tasks:
                status = task.get("status", "unknown")
                priority = task.get("priority", "unknown")
                
                result["summary"]["by_status"][status] = result["summary"]["by_status"].get(status, 0) + 1
                result["summary"]["by_priority"][priority] = result["summary"]["by_priority"].get(priority, 0) + 1
            
            # Add recommendations based on task list
            if result["summary"]["by_status"].get("todo", 0) > 0:
                result["summary"]["recommendations"].append({
                    "action": "Start a new task",
                    "reason": f"You have {result['summary']['by_status']['todo']} tasks waiting to be started",
                    "command": {"action": "next", "git_branch_id": git_branch_id}
                })
            
            if result["summary"]["by_status"].get("in_progress", 0) > 3:
                result["summary"]["recommendations"].append({
                    "action": "Complete in-progress tasks",
                    "reason": "You have many tasks in progress - consider completing some before starting new ones",
                    "tip": "Focus on finishing existing work to maintain momentum"
                })
        
        # Skip heavy workflow enhancement for list operations to improve performance
        # The _enhance_with_workflow_hints adds massive amounts of data (autonomous_rules,
        # decision_matrix, conflict_resolution, etc.) that is not needed for list operations
        # if result.get("success"):
        #     result = self._enhance_with_workflow_hints(
        #         result, "list", {
        #             "git_branch_id": git_branch_id
        #         }
        #     )
        
        return result
    
    def _handle_search_tasks(self, facade: TaskApplicationFacade, query: Optional[str], 
                            limit: Optional[int], git_branch_id: Optional[str] = None, 
                            include_context: bool = False) -> Dict[str, Any]:
        """Convert MCP search parameters to DTO and delegate to facade."""
        if not query:
            return {
                "success": False, 
                "error": "query is required for search",
                "error_code": "MISSING_FIELD",
                "field": "query",
                "expected": "A valid query string",
                "hint": "Include 'query' in your request body"
            }
        
        request = SearchTasksRequest(
            git_branch_id=git_branch_id,
            query=query,
            limit=limit
        )
        
        result = facade.search_tasks(request, include_context=include_context)
        
        # Ensure result is a dictionary before accessing it
        if not isinstance(result, dict):
            logger.error(f"search_tasks returned non-dict result: {type(result)}")
            return self._response_formatter.create_error_response(
                operation="search",
                error="Internal error: Invalid response format from task search",
                error_code=ErrorCodes.INTERNAL_ERROR
            )
        
        # Skip heavy workflow enhancement for search operations to improve performance
        # Search results don't need the full autonomous guidance system
        # if result.get("success"):
        #     result = self._enhance_with_workflow_hints(
        #         result, "search", {
        #             "query": query,
        #             "git_branch_id": git_branch_id
        #         }
        #     )
        
        return result
    
    def _handle_next_task(self, facade: TaskApplicationFacade, git_branch_id: Optional[str] = None, include_context: bool = False) -> Dict[str, Any]:
        """Handle next task request with optional context inclusion."""
        try:
            # Derive context parameters from git_branch_id
            project_id, git_branch_name, user_id = self._derive_context_from_identifiers(git_branch_id=git_branch_id, user_id=None)
            
            # Since MCP tools are synchronous, we need to run the async method in sync context
            async def _run_async(facade, include_context, user_id, project_id, git_branch_id):
                return await facade.get_next_task(
                    include_context=include_context,
                    user_id=user_id,
                    project_id=project_id,
                    git_branch_id=git_branch_id,  # Fixed: Pass git_branch_id instead of git_branch_name
                    assignee=None,  # Pass None explicitly to avoid NoneType errors
                    labels=None     # Pass None explicitly to avoid NoneType errors
                )
            
            # Use the context-aware threading approach to preserve authentication
            result = self._run_async_with_context(_run_async, facade, include_context, user_id, project_id, git_branch_id)
            
            # Enhance response with comprehensive workflow guidance
            if result.get("success"):
                result = self._enhance_with_workflow_hints(
                    result, "next", {
                        "git_branch_id": git_branch_id,
                        "include_context": include_context
                    }
                )
                
                # Include project + branch + task context for next task
                if result.get("task"):
                    result = self._include_project_branch_task_context(
                        result, project_id, git_branch_id, result["task"].get("id")
                    )
            
            return result
        except Exception as e:
            return UserFriendlyErrorHandler.handle_error(
                e, 
                "next task retrieval",
                {"git_branch_id": git_branch_id}
            )
    
    def _handle_task_management(self, 
                   action: str,
                   git_branch_id: Optional[str] = None,
                   task_id: Optional[str] = None,
                   title: Optional[str] = None,
                   description: Optional[str] = None,
                   status: Optional[str] = None,
                   priority: Optional[str] = None,
                   details: Optional[str] = None,
                   estimated_effort: Optional[str] = None,
                   assignees: Optional[List[str]] = None,
                   labels: Optional[List[str]] = None,
                   due_date: Optional[str] = None,
                   context_id: Optional[str] = None,
                   force_full_generation: bool = False,
                   include_context: bool = False,
                   limit: Optional[int] = None,
                   query: Optional[str] = None,
                   dependency_id: Optional[str] = None,
                   dependencies: Optional[List[str]] = None,
                   completion_summary: Optional[str] = None,
                   testing_notes: Optional[str] = None,
                   # Phase 1: Enhanced context tracking parameters
                   work_notes: Optional[str] = None,
                   progress_made: Optional[str] = None,
                   files_modified: Optional[List[str]] = None,
                   decisions_made: Optional[List[str]] = None,
                   blockers_encountered: Optional[List[str]] = None,
                   user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Manage task operations by routing to appropriate handlers.
        For add_dependency/remove_dependency, use dependency_id parameter.
        """
        # --- Validation ---
        # git_branch_id is required for create (to associate the task with a branch) and for
        # next (to compute next task within a branch). It is optional for list/search so
        # that callers can retrieve tasks across branches without specifying one.
        if action in ["create", "next"] and not git_branch_id:
            return {
                "success": False,
                "error": f"Missing required field: git_branch_id for action '{action}'",
                "error_code": "MISSING_FIELD",
                "field": "git_branch_id"
            }

        if action in ["update", "get", "delete", "complete", "add_dependency", "remove_dependency"] and not task_id:
            return {
                "success": False,
                "error": f"Missing required field: task_id for action '{action}'",
                "error_code": "MISSING_FIELD",
                "field": "task_id"
            }

        # Validate UUID format for git_branch_id if provided
        if git_branch_id:
            if not self._is_valid_uuid(git_branch_id):
                return {
                    "success": False,
                    "error": f"Invalid git_branch_id format: '{git_branch_id}'. Expected UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                    "error_code": "INVALID_FORMAT",
                    "field": "git_branch_id",
                    "expected_format": "UUID (e.g., 550e8400-e29b-41d4-a716-446655440000)",
                    "hint": "Use a valid UUID for git_branch_id. Get UUIDs from git branch creation or list operations."
                }

        # Validate UUID format for task_id if provided
        if task_id:
            if not self._is_valid_uuid(task_id):
                return {
                    "success": False,
                    "error": f"Invalid task_id format: '{task_id}'. Expected UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                    "error_code": "INVALID_FORMAT", 
                    "field": "task_id",
                    "expected_format": "UUID (e.g., 550e8400-e29b-41d4-a716-446655440000)",
                    "hint": "Use a valid UUID for task_id. Get UUIDs from task creation or list operations."
                }

        logger.info(f"Managing task with action: {action}")
        
        facade = self._get_facade_for_request(task_id=task_id, git_branch_id=git_branch_id, user_id=user_id)

        if action in ["create", "update", "get", "delete", "complete"]:
            return self.handle_crud_operations(
                facade=facade,
                action=action, 
                task_id=task_id, 
                title=title,
                description=description, 
                status=status, 
                priority=priority, 
                details=details, 
                estimated_effort=estimated_effort,
                assignees=assignees, 
                labels=labels, 
                due_date=due_date, 
                context_id=context_id, 
                force_full_generation=force_full_generation,
                include_context=include_context, 
                git_branch_id=git_branch_id,
                dependencies=dependencies,
                completion_summary=completion_summary,
                testing_notes=testing_notes,
                # Phase 1: Pass context tracking parameters
                work_notes=work_notes,
                progress_made=progress_made,
                files_modified=files_modified,
                decisions_made=decisions_made,
                blockers_encountered=blockers_encountered
            )
        elif action in ["list", "search", "next"]:
            return self.handle_list_search_next(
                action=action, 
                status=status, 
                priority=priority,
                assignees=assignees, 
                labels=labels, 
                limit=limit, 
                query=query, 
                include_context=include_context,
                git_branch_id=git_branch_id
            )
        elif action in ["add_dependency", "remove_dependency"]:
            return self.handle_dependency_operations(
                facade=facade,
                action=action, 
                task_id=task_id, 
                dependency_id=dependency_id
            )
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "error_code": "UNKNOWN_ACTION",
            }

    def handle_dependency_operations(self, action: str, git_branch_id: str, task_id: str = None, dependency_id: str = None) -> dict:
        """Handle dependency operations with parameter validation before delegation."""
        try:
            # Validate task_id
            if not task_id:
                return {
                    "success": False,
                    "error": "Missing required field: task_id",
                    "error_code": "MISSING_FIELD",
                    "field": "task_id",
                    "expected": "A valid task ID string",
                    "hint": "Include 'task_id' in your request body"
                }
            
            # Get facade
            facade = self._get_facade_for_request(git_branch_id)
            
            if action == "add_dependency":
                if not dependency_id:
                    return {
                        "success": False,
                        "error": "Missing required field: dependency_id",
                        "error_code": "MISSING_FIELD",
                        "field": "dependency_id",
                        "expected": "A valid dependency task ID string",
                        "hint": "Include 'dependency_id' in your request body"
                    }
                return facade.add_dependency(task_id, dependency_id)
            elif action == "remove_dependency":
                if not dependency_id:
                    return {
                        "success": False,
                        "error": "Missing required field: dependency_id",
                        "error_code": "MISSING_FIELD",
                        "field": "dependency_id",
                        "expected": "A valid dependency task ID string",
                        "hint": "Include 'dependency_id' in your request body"
                    }
                return facade.remove_dependency(task_id, dependency_id)
            else:
                return {
                    "success": False,
                    "error": f"Unknown dependency action: {action}",
                    "error_code": "UNKNOWN_ACTION",
                    "field": "action",
                    "expected": "One of: add_dependency, remove_dependency",
                    "hint": "Check the 'action' parameter for typos"
                }
                
        except Exception as e:
            logger.error(f"Error in dependency operation '{action}': {e}")
            return {"success": False, "error": f"Dependency operation failed: {str(e)}"}
    
    def _get_task_management_descriptions(self) -> Dict[str, Any]:
        """
        Flatten task descriptions for robust access, similar to other controllers.
        """
        all_desc = description_loader.get_all_descriptions()
        flat = {}
        # Look for 'manage_task' in any subdict (e.g., all_desc['task']['manage_task'])
        for sub in all_desc.values():
            if isinstance(sub, dict) and "manage_task" in sub:
                flat["manage_task"] = sub["manage_task"]
        return flat
    
    def _derive_context_from_identifiers(self, task_id: Optional[str] = None, git_branch_id: Optional[str] = None, user_id: Optional[str] = None) -> tuple:
        """
        Derive project_id, git_branch_name, and user_id from task_id or git_branch_id.
        
        Args:
            task_id: Task identifier to derive context from
            git_branch_id: Git branch identifier to derive context from
            
        Returns:
            Tuple of (project_id, git_branch_name, user_id)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Get authenticated user ID using helper function (if not provided)
        if user_id is None:
            log_authentication_details()  # For debugging
            user_id = get_authenticated_user_id(None, "Task context resolution")
        else:
            logger.debug(f"Using provided user_id: {user_id}")
        
        # For git_branch_id, look up the actual project_id
        if git_branch_id:
            logger.debug(f"Looking up project_id for git_branch_id {git_branch_id}")
            try:
                # Use GitBranchApplicationFacade with proper factory pattern
                from ...application.facades.git_branch_application_facade import GitBranchApplicationFacade
                from ...infrastructure.repositories.repository_factory import RepositoryFactory
                
                git_branch_facade = GitBranchApplicationFacade(
                    git_branch_repository=RepositoryFactory.get_git_branch_repository()
                )
                
                try:
                    git_branch_data = git_branch_facade.get_git_branch_by_id(git_branch_id)
                    if git_branch_data and 'git_branch' in git_branch_data:
                        branch = git_branch_data['git_branch']
                        actual_project_id = branch.get('project_id')
                        git_branch_name = branch.get('name')
                        logger.debug(f"Found project_id {actual_project_id} and branch name '{git_branch_name}' for git_branch_id {git_branch_id}")
                        return (actual_project_id, git_branch_name, user_id)
                except Exception:
                    logger.warning(f"Git branch {git_branch_id} not found")
            except Exception as e:
                logger.warning(f"Failed to look up project_id for git_branch_id {git_branch_id}: {e}")
            
            # Fallback for git_branch_id case
            logger.debug(f"Using default context for git_branch_id {git_branch_id}")
            return ("default_project", "main", user_id)
        
        # For task_id, look up the git_branch_id and derive context
        if task_id:
            logger.debug(f"Deriving context for task_id {task_id}")
            try:
                # Use TaskApplicationFacade instead of direct database access
                task_data = self._task_facade.get_task(task_id, include_context=False)
                if task_data and 'task' in task_data:
                    found_git_branch_id = task_data['task'].get('git_branch_id')
                    if found_git_branch_id:
                        logger.debug(f"Found git_branch_id {found_git_branch_id} for task {task_id}")
                        # Store the git_branch_id for later use
                        self._resolved_git_branch_id = found_git_branch_id
                        
                        # Now look up the actual project_id for this git_branch_id
                        branch_result = session.execute(
                            text('SELECT project_id, name FROM project_git_branchs WHERE id = :git_branch_id'),
                            {'git_branch_id': found_git_branch_id}
                        ).fetchone()
                        
                        if branch_result:
                            actual_project_id, git_branch_name = branch_result
                            logger.debug(f"Found project_id {actual_project_id} and branch name '{git_branch_name}' for git_branch_id {found_git_branch_id}")
                            return (actual_project_id, git_branch_name, user_id)
                        else:
                            logger.warning(f"Git branch {found_git_branch_id} not found in project_git_branchs table")
                            return ("default_project", "main", user_id)
                    else:
                        logger.warning(f"Task {task_id} not found or has no git_branch_id")
            except Exception as e:
                logger.warning(f"Failed to derive context from task_id {task_id}: {e}")
        
        # Default fallback
        logger.debug("Using default context for task facade")
        return ("default_project", "main", user_id)

    def _get_task_facade(self, project_id: str, git_branch_name: str, user_id: str, git_branch_id: Optional[str] = None) -> TaskApplicationFacade:
        """Get a context-aware task facade."""
        # If git_branch_id is provided, create a facade with it
        if git_branch_id:
            return self._task_facade_factory.create_task_facade_with_git_branch_id(project_id, git_branch_name, user_id, git_branch_id)
        else:
            return self._task_facade_factory.create_task_facade(project_id, git_branch_name, user_id)
    
    # Context Enforcing Methods
    
    def complete_task_with_context(self, 
                                  task_id: str,
                                  completion_summary: str,
                                  testing_notes: Optional[str] = None,
                                  next_recommendations: Optional[str] = None) -> Dict[str, Any]:
        """Complete a task with mandatory context update.
        
        This method enforces the Vision System requirement that all task completions
        MUST include a completion_summary describing what was accomplished.
        """
        try:
            if not completion_summary:
                return {
                    "success": False,
                    "error": "Missing required field: completion_summary",
                    "error_code": "MISSING_FIELD",
                    "field": "completion_summary",
                    "expected": "A detailed summary of what was accomplished",
                    "hint": "Describe what you completed, how you did it, and any important details"
                }
            
            # Get facade for the task
            facade = self._get_facade_for_request(task_id=task_id)
            
            # First update the task context with completion details
            if self._context_facade_factory:
                # Get task details to extract project and branch info
                task_result = facade.get_task(task_id)
                if task_result.get("success"):
                    task = task_result.get("task", {})
                    # Derive context from task
                    project_id, git_branch_name, user_id = self._derive_context_from_identifiers(
                        task_id=task_id, 
                        git_branch_id=task.get("git_branch_id"),
                        user_id=None
                    )
                    
                    # Validate user_id before creating context facade
                    validated_user_id = user_id
                    if not validated_user_id:
                        # NO FALLBACKS ALLOWED - user authentication is required
                        raise UserAuthenticationRequiredError("Task context facade creation")
                    
                    validated_user_id = validate_user_id(validated_user_id, "Task context facade creation")
                    
                    context_facade = self._context_facade_factory.create_facade(
                        user_id=validated_user_id,
                        project_id=project_id or "default_project",
                        git_branch_id=task.get("git_branch_id")
                    )
                    
                    # Build context update data
                    context_data = {
                        "completion_summary": completion_summary,
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                        "status": "done"
                    }
                    
                    if testing_notes:
                        context_data["testing_notes"] = testing_notes
                    
                    if next_recommendations:
                        context_data["next_recommendations"] = next_recommendations
                    
                    # Update context using the facade with all required parameters
                    import asyncio
                    import threading
                    
                    async def _update_context_async(context_facade, task_id, user_id, project_id, git_branch_name, context_data):
                        # Validate user_id for context update
                        validated_user_id = user_id
                        if not validated_user_id:
                            # NO FALLBACKS ALLOWED - user authentication is required
                            raise UserAuthenticationRequiredError("Task context update")
                        
                        validated_user_id = validate_user_id(validated_user_id, "Task context update")
                        
                        return await context_facade.update_context(
                            task_id, 
                            validated_user_id,
                            project_id or "default_project",
                            git_branch_name or "main",
                            context_data
                        )
                    
                    # Run async update with proper context preservation
                    try:
                        result = self._run_async_with_context(_update_context_async, context_facade, task_id, user_id, project_id, git_branch_name, context_data)
                    except Exception as exception:
                        logger.warning(f"Failed to update context for task {task_id}: {exception}")
                    
                    if result and not result.get("success"):
                        logger.warning(f"Failed to update context for task {task_id}: {result.get('error')}")
                else:
                    logger.warning(f"Could not retrieve task {task_id} to update context")
            
            # Complete the task with Vision System parameters
            result = facade.complete_task(
                task_id,
                completion_summary=completion_summary,
                testing_notes=testing_notes
            )
            
            # Ensure result is a dictionary before accessing it
            if not isinstance(result, dict):
                logger.error(f"complete_task returned non-dict result: {type(result)}")
                return self._response_formatter.create_error_response(
                    operation="complete",
                    error="Internal error: Invalid response format from task completion",
                    error_code=ErrorCodes.INTERNAL_ERROR
                )
            
            if result.get("success"):
                # Add completion details to response
                result["completion_details"] = {
                    "summary": completion_summary,
                    "testing_notes": testing_notes,
                    "next_recommendations": next_recommendations,
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }
                
                # Add helpful next action suggestions
                result["next_action_suggestions"] = [
                    {
                        "action": "next",
                        "description": "Get next task to work on",
                        "example": {"action": "next", "git_branch_id": result.get("task", {}).get("git_branch_id")}
                    },
                    {
                        "action": "list",
                        "description": "See remaining tasks",
                        "example": {"action": "list", "status": "todo", "git_branch_id": result.get("task", {}).get("git_branch_id")}
                    },
                    {
                        "action": "create",
                        "description": "Create a follow-up task",
                        "example": {
                            "action": "create",
                            "git_branch_id": result.get("task", {}).get("git_branch_id"),
                            "title": "Follow-up task title",
                            "description": "Task description"
                        }
                    }
                ]
                
                result["context_updated"] = True
                result["workflow_status"] = "✅ Task completed successfully with context"
                
                # Enhance with comprehensive workflow guidance
                if result.get("success"):
                    result = self._enhance_with_workflow_hints(
                        result, "complete", {
                            "task_id": task_id
                        }
                    )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in complete_task_with_context: {e}")
            return {
                "success": False,
                "error": f"Failed to complete task: {str(e)}",
                "error_code": "INTERNAL_ERROR"
            }
    
    def report_progress(self,
                       task_id: str,
                       progress_type: str,
                       description: str,
                       percentage: Optional[int] = None,
                       details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Report progress on a task with automatic context tracking.
        
        Parameters:
        - task_id: ID of the task
        - progress_type: Type of progress (analysis, design, implementation, testing, etc.)
        - description: What was accomplished
        - percentage: Optional completion percentage (0-100)
        - details: Optional additional details
        """
        try:
            # Validate inputs
            if not all([task_id, progress_type, description]):
                return {
                    "success": False,
                    "error": "Missing required fields: task_id, progress_type, and description are required",
                    "error_code": "MISSING_FIELD"
                }
            
            # Get facade
            facade = self._get_facade_for_request(task_id=task_id)
            
            # Build update data
            update_data = {
                "status": "in_progress",
                "details": f"[{progress_type}] {description}"
            }
            
            if percentage is not None:
                update_data["completion_percentage"] = max(0, min(100, percentage))
            
            # Update task
            from ...application.dtos.task.update_task_request import UpdateTaskRequest
            request = UpdateTaskRequest(
                task_id=task_id,
                status="in_progress",
                details=update_data["details"]
            )
            
            result = facade.update_task(task_id, request)
            
            if result.get("success"):
                # Add progress details to response
                result["progress_details"] = {
                    "type": progress_type,
                    "description": description,
                    "percentage": percentage,
                    "reported_at": datetime.now(timezone.utc).isoformat()
                }
                
                # Add progress tracking if service available
                if self._progress_service:
                    from ...domain.value_objects.progress import ProgressType
                    try:
                        progress_type_enum = ProgressType(progress_type.lower())
                        self._progress_service.track_progress(
                            task_id, progress_type_enum, description, percentage, details
                        )
                    except ValueError:
                        logger.warning(f"Unknown progress type: {progress_type}")
                
                # Enhance with comprehensive workflow guidance
                if result.get("success"):
                    result = self._enhance_with_workflow_hints(
                        result, "update", {
                            "task_id": task_id,
                            "progress_type": progress_type
                        }
                    )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in report_progress: {e}")
            return {
                "success": False,
                "error": f"Failed to report progress: {str(e)}",
                "error_code": "INTERNAL_ERROR"
            }
    
    def get_workflow_hints(self,
                          task_id: str,
                          include_agent_suggestions: bool = False) -> Dict[str, Any]:
        """Get intelligent workflow hints for a task.
        
        Parameters:
        - task_id: ID of the task
        - include_agent_suggestions: Include agent assignment suggestions
        """
        try:
            # Get task details
            facade = self._get_facade_for_request(task_id=task_id)
            task_result = facade.get_task(task_id, include_context=True)
            
            if not task_result.get("success"):
                return task_result
            
            task = task_result.get("task", {})
            
            # Generate hints using hint service if available
            hints = {
                "task_id": task_id,
                "current_status": task.get("status"),
                "completion_percentage": task.get("completion_percentage", 0),
                "workflow_hints": [],
                "next_actions": [],
                "warnings": []
            }
            
            if self._hint_service:
                from ...domain.value_objects.hints import HintType
                
                # Get various types of hints
                for hint_type in [HintType.NEXT_ACTION, HintType.BEST_PRACTICE, HintType.WARNING]:
                    service_hints = self._hint_service.generate_hints(task_id, hint_type)
                    if hint_type == HintType.NEXT_ACTION:
                        hints["next_actions"].extend(service_hints)
                    elif hint_type == HintType.WARNING:
                        hints["warnings"].extend(service_hints)
                    else:
                        hints["workflow_hints"].extend(service_hints)
            
            # Use workflow analysis service if available
            if self._workflow_service:
                workflow_state = self._workflow_service.analyze_workflow_state(task_id)
                hints["workflow_analysis"] = workflow_state
            
            # Add agent suggestions if requested
            if include_agent_suggestions and self._coordination_service:
                suggestions = self._coordination_service.suggest_agents_for_task(task_id)
                hints["agent_suggestions"] = suggestions
            
            # Enhance with comprehensive workflow guidance
            enhanced_result = self._enhance_with_workflow_hints(
                {"success": True, "task": task, "hints": hints},
                "get",
                {"task_id": task_id}
            )
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error in get_workflow_hints: {e}")
            return {
                "success": False,
                "error": f"Failed to get workflow hints: {str(e)}",
                "error_code": "INTERNAL_ERROR"
            }
    
    def get_vision_alignment(self, task_id: str) -> Dict[str, Any]:
        """Get vision alignment information for a task."""
        try:
            # Simple implementation for now
            facade = self._get_facade_for_request(task_id=task_id)
            task_result = facade.get_task(task_id, include_context=True)
            
            if not task_result.get("success"):
                return task_result
            
            task = task_result.get("task", {})
            
            # Basic vision alignment response
            return {
                "success": True,
                "task_id": task_id,
                "vision_alignment": {
                    "score": 0.8,  # Placeholder
                    "aligned_objectives": [
                        "Code quality improvement",
                        "Feature completeness"
                    ],
                    "recommendations": [
                        "Consider impact on overall architecture",
                        "Ensure documentation is updated"
                    ],
                    "strategic_importance": task.get("priority", "medium")
                }
            }
        except Exception as e:
            logger.error(f"Error in get_vision_alignment: {e}")
            return {
                "success": False,
                "error": f"Failed to get vision alignment: {str(e)}",
                "error_code": "INTERNAL_ERROR"
            }
    
    def _include_project_branch_task_context(self, response: Dict[str, Any], project_id: str, git_branch_id: str, task_id: str) -> Dict[str, Any]:
        """Include project + branch + task context in the response."""
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
            if git_branch_id:
                branch_context = context_facade.get_context("task", git_branch_id, include_inherited=True)
                if branch_context.get("success"):
                    response["branch_context"] = branch_context.get("context", {})
                    logger.info(f"Added branch context for branch {git_branch_id}")
                else:
                    logger.debug(f"No branch context found for {git_branch_id}: {branch_context.get('error', 'Unknown error')}")
            
            # Get task context
            if task_id:
                task_context = context_facade.get_context("task", task_id, include_inherited=True)
                if task_context.get("success"):
                    response["task_context"] = task_context.get("context", {})
                    logger.info(f"Added task context for task {task_id}")
                else:
                    logger.debug(f"No task context found for {task_id}: {task_context.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error including project + branch + task context: {e}")
        
        return response
    
    def _enhance_with_workflow_hints(self, response: Dict[str, Any], action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance response with comprehensive workflow guidance using factory.
        """
        return self._workflow_guidance.enhance_response(response, action, context)
    
    def _validate_parameters(self, action: str, labels: Optional[List[str]] = None, 
                           assignees: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Validate parameter formats with helpful error messages.
        Now that we have parsers, we're more lenient with input formats.
        """
        # Since we now have parsers that handle various formats, we don't need strict validation
        # The parsers will handle string, list, JSON, and comma-separated formats
        
        # Just validate that after parsing we have proper lists
        if labels is not None and not isinstance(labels, list):
            # This should not happen if parsers are used correctly
            logger.error(f"Labels validation failed after parsing: {type(labels).__name__}")
            
        if assignees is not None and not isinstance(assignees, list):
            # This should not happen if parsers are used correctly  
            logger.error(f"Assignees validation failed after parsing: {type(assignees).__name__}")
        
        # All validation passed
        return {"valid": True}
    
    def _parse_labels(self, labels: Any) -> Optional[List[str]]:
        """
        Parse labels parameter that might come in various formats.
        
        Handles:
        - List[str]: ["label1", "label2"] - already correct format
        - JSON string: '["label1", "label2"]' - parse as JSON
        - Comma-separated string: "label1,label2,label3" - split by comma
        - Single label string: "label1" - wrap in list
        - None or empty - return None
        
        Returns:
            List[str] if valid labels found, None otherwise
        """
        if labels is None:
            return None
            
        # If already a list, validate each item is a string
        if isinstance(labels, list):
            # Ensure all items are strings
            parsed_labels = []
            for label in labels:
                if isinstance(label, str):
                    parsed_labels.append(label.strip())
                else:
                    logger.warning(f"Skipping non-string label: {label}")
            return parsed_labels if parsed_labels else None
            
        # If it's a string, try to parse it
        if isinstance(labels, str):
            labels = labels.strip()
            if not labels:
                return None
                
            # Try parsing as JSON array first
            if labels.startswith('[') and labels.endswith(']'):
                try:
                    import json
                    parsed = json.loads(labels)
                    if isinstance(parsed, list):
                        # Validate all items are strings
                        parsed_labels = []
                        for item in parsed:
                            if isinstance(item, str):
                                parsed_labels.append(item.strip())
                        return parsed_labels if parsed_labels else None
                except json.JSONDecodeError:
                    logger.debug(f"Failed to parse labels as JSON: {labels}")
            
            # Try comma-separated format
            if ',' in labels:
                parsed_labels = [label.strip() for label in labels.split(',') if label.strip()]
                return parsed_labels if parsed_labels else None
            
            # Single label
            return [labels]
        
        # Unknown format
        logger.warning(f"Unable to parse labels parameter of type {type(labels)}: {labels}")
        return None
    
    def _coerce_to_bool(self, value: Union[bool, str], param_name: str) -> bool:
        """
        Coerce a value to boolean, handling string representations.
        
        Args:
            value: The value to coerce (bool or string)
            param_name: Parameter name for error messages
            
        Returns:
            Boolean value
        """
        if isinstance(value, bool):
            return value
            
        if isinstance(value, str):
            value_lower = value.lower().strip()
            if value_lower in ('true', '1', 'yes', 'on', 'enabled'):
                return True
            elif value_lower in ('false', '0', 'no', 'off', 'disabled'):
                return False
            else:
                # For invalid strings, log warning and use default
                logger.warning(f"Invalid boolean value '{value}' for {param_name}, using False")
                return False
        
        # For other types, use Python's truthiness
        return bool(value)
    
    def _parse_string_list(self, param: Any, param_name: str = "parameter") -> Optional[List[str]]:
        """
        Generic parser for string list parameters that might come in various formats.
        Works for labels, assignees, or any other string list parameter.
        
        Handles:
        - List[str]: ["item1", "item2"] - already correct format
        - JSON string: '["item1", "item2"]' - parse as JSON
        - Comma-separated string: "item1,item2,item3" - split by comma
        - Single item string: "item1" - wrap in list
        - None or empty - return None
        
        Returns:
            List[str] if valid items found, None otherwise
        """
        if param is None:
            return None
            
        # If already a list, validate each item is a string
        if isinstance(param, list):
            # Ensure all items are strings
            parsed_items = []
            for item in param:
                if isinstance(item, str):
                    parsed_items.append(item.strip())
                else:
                    logger.warning(f"Skipping non-string {param_name}: {item}")
            return parsed_items if parsed_items else None
            
        # If it's a string, try to parse it
        if isinstance(param, str):
            param = param.strip()
            if not param:
                return None
                
            # Try parsing as JSON array first
            if param.startswith('[') and param.endswith(']'):
                try:
                    import json
                    parsed = json.loads(param)
                    if isinstance(parsed, list):
                        # Validate all items are strings
                        parsed_items = []
                        for item in parsed:
                            if isinstance(item, str):
                                parsed_items.append(item.strip())
                        return parsed_items if parsed_items else None
                except json.JSONDecodeError:
                    logger.debug(f"Failed to parse {param_name} as JSON: {param}")
            
            # Try comma-separated format
            if ',' in param:
                parsed_items = [item.strip() for item in param.split(',') if item.strip()]
                return parsed_items if parsed_items else None
            
            # Single item
            return [param]
        
        # Unknown format
        logger.warning(f"Unable to parse {param_name} parameter of type {type(param)}: {param}")
        return None
    
    def _standardize_response(
        self, 
        result: Dict[str, Any], 
        operation: str,
        workflow_guidance: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Convert legacy response format to standardized format.
        
        Args:
            result: The original response from facade
            operation: The operation performed (e.g., "create_task", "update_task")
            workflow_guidance: Workflow guidance to include
            metadata: Additional metadata
            
        Returns:
            Standardized response following the new format
        """
        # Check if this is already a standardized response
        if "operation_id" in result and "confirmation" in result:
            return result
            
        # Handle error responses
        if not result.get("success", False):
            error_code = result.get("error_code", ErrorCodes.OPERATION_FAILED)
            
            # Check for validation errors
            if "field" in result or "parameter" in result:
                return StandardResponseFormatter.create_validation_error_response(
                    operation=operation,
                    field=result.get("field") or result.get("parameter", "unknown"),
                    expected=result.get("expected", "valid value"),
                    hint=result.get("hint")
                )
            
            # Standard error response
            return StandardResponseFormatter.create_error_response(
                operation=operation,
                error=result.get("error", "Operation failed"),
                error_code=error_code,
                metadata=metadata
            )
        
        # Handle success responses
        # Extract the main data object (task, context, etc.)
        data = None
        if "task" in result:
            data = {"task": result["task"]}
        elif "tasks" in result:
            data = {"tasks": result["tasks"]}
        elif "context" in result:
            data = {"context": result["context"]}
        else:
            # Include all non-standard fields as data
            data = {k: v for k, v in result.items() 
                   if k not in ["success", "error", "workflow_guidance"]}
        
        # Check for partial failures (e.g., context update failures)
        partial_failures = []
        if "context_update_error" in result:
            partial_failures.append({
                "operation": "context_update",
                "error": result["context_update_error"],
                "impact": "Context may be out of sync"
            })
        
        # Create standardized response
        if partial_failures:
            return StandardResponseFormatter.create_partial_success_response(
                operation=operation,
                data=data,
                partial_failures=partial_failures,
                metadata=metadata,
                workflow_guidance=workflow_guidance or result.get("workflow_guidance")
            )
        else:
            return StandardResponseFormatter.create_success_response(
                operation=operation,
                data=data,
                metadata=metadata,
                workflow_guidance=workflow_guidance or result.get("workflow_guidance")
            )
    
    def _create_standardized_error(
        self,
        operation: str,
        field: str,
        expected: str,
        hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a standardized validation error response."""
        return StandardResponseFormatter.create_validation_error_response(
            operation=operation,
            field=field,
            expected=expected,
            hint=hint
        )
    
    def _is_valid_uuid(self, uuid_string: str) -> bool:
        """
        Validate if a string is a valid UUID format.
        
        Accepts both formats:
        - Standard UUID with hyphens: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        - Hex format without hyphens: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx (32 chars)
        
        Args:
            uuid_string: String to validate
            
        Returns:
            True if valid UUID format, False otherwise
        """
        if not uuid_string or not isinstance(uuid_string, str):
            return False
            
        uuid_string = uuid_string.strip()
        
        # Try to parse as UUID - this handles both formats
        try:
            uuid.UUID(uuid_string)
            return True
        except (ValueError, TypeError):
            # Check if it's a 32-character hex string (UUID without hyphens)
            if len(uuid_string) == 32 and re.match(r'^[0-9a-fA-F]{32}$', uuid_string):
                return True
            return False

    def handle_search_operations(self, action: str, 
                               query: Optional[str] = None, limit: Optional[int] = None,
                               git_branch_id: Optional[str] = None, 
                               include_context: bool = False) -> Dict[str, Any]:
        """Handle search-related operations."""
        try:
            if action == "search":
                # Validate query parameter before authentication
                if not query:
                    return self._create_missing_field_error("query", "search")
                
                # Get facade after parameter validation
                facade = self._get_facade_for_request(git_branch_id)
                return self._handle_search_tasks(facade, query, limit, git_branch_id, include_context)
            else:
                return {"success": False, "error": f"Unknown search operation: {action}"}
        except Exception as e:
            return UserFriendlyErrorHandler.handle_error(
                e, 
                f"search {action} operation",
                {"action": action, "query": query}
            )

    def handle_recommendation_operations(self, action: str,
                                       git_branch_id: Optional[str] = None,
                                       include_context: bool = False) -> Dict[str, Any]:
        """Handle recommendation-related operations."""
        try:
            facade = self._get_facade_for_request(git_branch_id)
            
            if action == "next":
                return self._handle_next_task(facade, git_branch_id, include_context)
            else:
                return {"success": False, "error": f"Unknown recommendation operation: {action}"}
        except Exception as e:
            return UserFriendlyErrorHandler.handle_error(
                e, 
                f"recommendation {action} operation",
                {"action": action, "git_branch_id": git_branch_id}
            )

    def _create_missing_field_error(self, field: str, action: str) -> Dict[str, Any]:
        """Create a standardized missing field error response."""
        return StandardResponseFormatter.create_validation_error_response(
            operation=action,
            field=field,
            expected=f"A valid {field} parameter",
            hint=f"Missing required field: {field}"
        )

    def _create_invalid_action_error(self, action: str) -> Dict[str, Any]:
        """Create a standardized invalid action error response."""
        valid_actions = ["create", "get", "update", "delete", "complete", "list", "search", "next", "add_dependency", "remove_dependency"]
        return StandardResponseFormatter.create_validation_error_response(
            operation="unknown_action",
            field="action",
            expected=f"One of: {', '.join(valid_actions)}",
            hint=f"Invalid action: {action}"
        )
