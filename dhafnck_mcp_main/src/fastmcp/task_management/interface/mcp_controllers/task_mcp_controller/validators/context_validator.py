"""
Context Validator for Task MCP Controller

Validates context-related parameters and operations.
"""

import logging
from typing import Dict, Any, Optional, Tuple

from ....utils.response_formatter import StandardResponseFormatter, ErrorCodes

logger = logging.getLogger(__name__)


class ContextValidator:
    """Validates context-related operations for tasks."""
    
    def __init__(self, response_formatter: StandardResponseFormatter):
        self._response_formatter = response_formatter
    
    def validate_context_requirements(self, operation: str, task_id: Optional[str] = None,
                                    git_branch_id: Optional[str] = None,
                                    include_context: Optional[bool] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate context requirements for operations."""
        
        # For operations that require context, validate context parameters
        context_required_operations = {"create", "update", "complete"}
        
        if operation in context_required_operations:
            if not git_branch_id:
                return False, self._create_context_error(
                    "git_branch_id", 
                    "Context operations require git_branch_id",
                    "Include git_branch_id to enable context management"
                )
        
        # Validate context inclusion requests
        if include_context is True:
            if not task_id:
                return False, self._create_context_error(
                    "task_id",
                    "Context inclusion requires task_id",
                    "Provide task_id when requesting context inclusion"
                )
        
        return True, None
    
    def validate_context_data(self, context_data: Optional[Dict[str, Any]]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate context data structure."""
        
        if context_data is None:
            return True, None  # Context data is optional
        
        if not isinstance(context_data, dict):
            return False, self._create_context_error(
                "context_data",
                "Context data must be a dictionary",
                "Provide context data as a JSON object"
            )
        
        # Validate context data doesn't contain reserved fields
        reserved_fields = {"id", "created_at", "updated_at", "level", "context_id"}
        
        for field in reserved_fields:
            if field in context_data:
                return False, self._create_context_error(
                    f"context_data.{field}",
                    f"Field '{field}' is reserved and cannot be set directly",
                    f"Remove '{field}' from context data"
                )
        
        return True, None
    
    def validate_context_inheritance(self, parent_context_id: Optional[str],
                                   child_context_id: Optional[str]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate context inheritance relationships."""
        
        if parent_context_id and child_context_id:
            if parent_context_id == child_context_id:
                return False, self._create_context_error(
                    "context_inheritance",
                    "Context cannot inherit from itself",
                    "Use different IDs for parent and child contexts"
                )
        
        return True, None
    
    def _create_context_error(self, field: str, message: str, hint: str) -> Dict[str, Any]:
        """Create standardized context validation error."""
        return self._response_formatter.create_error_response(
            operation="validate_context",
            error=f"Context validation failed: {message}",
            error_code=ErrorCodes.VALIDATION_ERROR,
            metadata={"field": field, "hint": hint}
        )