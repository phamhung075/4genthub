"""
Context Operation Handler

Handles all unified context management operations including CRUD, delegation, insights, and list operations.
"""

import logging
from typing import Dict, Any, Optional, Union
from ....utils.response_formatter import StandardResponseFormatter, ResponseStatus, ErrorCodes
from .....application.facades.unified_context_facade import UnifiedContextFacade
from ...auth_helper import get_authenticated_user_id

logger = logging.getLogger(__name__)


class ContextOperationHandler:
    """Handler for all unified context operations."""
    
    def __init__(self, response_formatter: StandardResponseFormatter):
        self._response_formatter = response_formatter
    
    def handle_context_operation(self, facade: UnifiedContextFacade, action: str, **kwargs) -> Dict[str, Any]:
        """Handle any context operation by routing to the facade."""
        
        try:
            # Get authenticated user_id
            user_id = kwargs.get('user_id') or get_authenticated_user_id()
            
            # Extract and prepare parameters
            level = kwargs.get('level', 'task')
            context_id = kwargs.get('context_id')
            data = kwargs.get('data')
            project_id = kwargs.get('project_id')
            git_branch_id = kwargs.get('git_branch_id')
            force_refresh = kwargs.get('force_refresh', False)
            include_inherited = kwargs.get('include_inherited', False)
            propagate_changes = kwargs.get('propagate_changes', True)
            delegate_to = kwargs.get('delegate_to')
            delegate_data = kwargs.get('delegate_data')
            delegation_reason = kwargs.get('delegation_reason')
            content = kwargs.get('content')
            category = kwargs.get('category')
            importance = kwargs.get('importance')
            agent = kwargs.get('agent')
            filters = kwargs.get('filters')
            
            # Route to appropriate facade method based on action
            if action == "create":
                # For task level contexts, normalize git_branch_id parameter to branch_id in data
                if level == "task" and git_branch_id and data:
                    # Normalize git_branch_id to branch_id for TaskContext entity consistency
                    if "branch_id" not in data:
                        # TaskContext domain entity expects 'branch_id' field
                        data["branch_id"] = git_branch_id
                    
                    # Also ensure parent references are set for 4-tier hierarchy
                    if "parent_branch_id" not in data:
                        data["parent_branch_id"] = git_branch_id
                    if "parent_branch_context_id" not in data:
                        data["parent_branch_context_id"] = git_branch_id
                
                result = facade.create_context(
                    level=level,
                    context_id=context_id,
                    data=data,
                    user_id=user_id
                )
            elif action == "get":
                result = facade.get_context(
                    level=level,
                    context_id=context_id,
                    include_inherited=include_inherited,
                    force_refresh=force_refresh,
                    user_id=user_id
                )
            elif action == "update":
                result = facade.update_context(
                    level=level,
                    context_id=context_id,
                    data=data,
                    propagate_changes=propagate_changes
                )
            elif action == "delete":
                result = facade.delete_context(
                    level=level,
                    context_id=context_id
                )
            elif action == "resolve":
                result = facade.resolve_context(
                    level=level,
                    context_id=context_id,
                    force_refresh=force_refresh
                )
            elif action == "delegate":
                result = facade.delegate_context(
                    level=level,
                    context_id=context_id,
                    delegate_to=delegate_to,
                    data=delegate_data,
                    delegation_reason=delegation_reason
                )
            elif action == "add_insight":
                result = facade.add_insight(
                    level=level,
                    context_id=context_id,
                    content=content,
                    category=category,
                    importance=importance,
                    agent=agent
                )
            elif action == "add_progress":
                result = facade.add_progress(
                    level=level,
                    context_id=context_id,
                    content=content,
                    agent=agent
                )
            elif action == "list":
                result = facade.list_contexts(
                    level=level,
                    filters=filters
                )
            else:
                valid_actions = [
                    "create", "get", "update", "delete", "resolve",
                    "delegate", "add_insight", "add_progress", "list"
                ]
                return self._response_formatter.create_error_response(
                    operation=f"manage_context.{action}",
                    error=f"Unknown action: {action}. Valid actions: {', '.join(valid_actions)}",
                    error_code=ErrorCodes.OPERATION_FAILED,
                    metadata={
                        "valid_actions": valid_actions
                    }
                )
            
            # Standardize the facade response using the formatter
            return self._standardize_facade_response(result, action)
            
        except ValueError as e:
            logger.error(f"Validation error in context operation '{action}': {e}")
            return self._response_formatter.create_error_response(
                operation=f"manage_context.{action}",
                error=str(e),
                error_code=ErrorCodes.VALIDATION_ERROR,
                metadata={"action": action, "level": kwargs.get('level', 'task')}
            )
        except Exception as e:
            logger.error(f"Error in context operation '{action}': {e}")
            return self._response_formatter.create_error_response(
                operation=f"manage_context.{action}",
                error=f"Operation failed: {str(e)}",
                error_code=ErrorCodes.INTERNAL_ERROR,
                metadata={"action": action, "level": kwargs.get('level', 'task')}
            )
    
    def _standardize_facade_response(self, facade_response: Dict[str, Any], operation: str) -> Dict[str, Any]:
        """Convert facade response to standardized format."""
        logger.info(f"DEBUG: _standardize_facade_response - operation: {operation}, facade_response keys: {facade_response.keys()}")
        if "context" in facade_response:
            logger.info(f"DEBUG: facade_response has context with keys: {facade_response['context'].keys() if isinstance(facade_response['context'], dict) else 'not a dict'}")
        
        return StandardResponseFormatter.format_context_response(
            facade_response,
            operation=operation,
            standardize_field_names=True
        )