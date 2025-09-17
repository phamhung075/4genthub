"""
Validation Factory for Task MCP Controller

Coordinates validation components for task operations.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple

from ..validators.parameter_validator import ParameterValidator
from ..validators.context_validator import ContextValidator
from ..validators.business_validator import BusinessValidator
from ....utils.response_formatter import StandardResponseFormatter

logger = logging.getLogger(__name__)


class ValidationFactory:
    """Factory for coordinating task validation components."""
    
    def __init__(self, response_formatter: StandardResponseFormatter):
        self._response_formatter = response_formatter
        
        # Initialize validators
        self._parameter_validator = ParameterValidator(response_formatter)
        self._context_validator = ContextValidator(response_formatter)
        self._business_validator = BusinessValidator(response_formatter)
        
        logger.info("ValidationFactory initialized with all validators")
    
    def validate_create_request(self, title: Optional[str], git_branch_id: Optional[str],
                               description: Optional[str] = None, status: Optional[str] = None,
                               priority: Optional[str] = None, due_date: Optional[str] = None,
                               assignees: Optional[List[str]] = None, 
                               labels: Optional[List[str]] = None,
                               dependencies: Optional[List[str]] = None,
                               context_data: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Comprehensive validation for task creation request.
        
        Returns:
            Tuple of (is_valid, error_response)
        """
        
        # Step 1: Parameter validation
        param_valid, param_error = self._parameter_validator.validate_create_task_params(
            title=title,
            git_branch_id=git_branch_id,
            description=description,
            status=status,
            priority=priority,
            due_date=due_date,
            assignees=assignees,
            labels=labels,
            dependencies=dependencies
        )
        
        if not param_valid:
            return False, param_error
        
        # Step 2: Context validation
        context_valid, context_error = self._context_validator.validate_context_requirements(
            operation="create",
            git_branch_id=git_branch_id
        )
        
        if not context_valid:
            return False, context_error
        
        # Validate context data if provided
        if context_data:
            context_data_valid, context_data_error = self._context_validator.validate_context_data(context_data)
            if not context_data_valid:
                return False, context_data_error
        
        # Step 3: Business rules validation
        business_valid, business_error = self._business_validator.validate_task_creation_rules(
            title=title,
            git_branch_id=git_branch_id,
            priority=priority,
            due_date=due_date,
            dependencies=dependencies
        )
        
        if not business_valid:
            return False, business_error
        
        return True, None
    
    def validate_update_request(self, task_id: Optional[str], 
                               current_task_data: Optional[Dict[str, Any]] = None,
                               **update_params) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Comprehensive validation for task update request.
        """
        
        # Step 1: Parameter validation
        # Remove task_id from update_params to avoid duplicate parameter error
        update_params_filtered = {k: v for k, v in update_params.items() if k != 'task_id'}
        param_valid, param_error = self._parameter_validator.validate_update_task_params(
            task_id=task_id,
            **update_params_filtered
        )
        
        if not param_valid:
            return False, param_error
        
        # Step 2: Context validation for context-related updates
        # Only validate context if explicitly requested or context data is provided
        if update_params.get('include_context') is True or 'context_data' in update_params:
            context_valid, context_error = self._context_validator.validate_context_requirements(
                operation="update",
                task_id=task_id,
                git_branch_id=update_params.get('git_branch_id'),
                include_context=update_params.get('include_context')
            )
            
            if not context_valid:
                return False, context_error
        
        # Step 3: Business rules validation
        business_valid, business_error = self._business_validator.validate_task_update_rules(
            task_id=task_id,
            current_task_data=current_task_data,
            status=update_params.get('status'),
            priority=update_params.get('priority'),
            due_date=update_params.get('due_date'),
            dependencies=update_params.get('dependencies'),
            completion_summary=update_params.get('completion_summary')
        )
        
        if not business_valid:
            return False, business_error
        
        return True, None
    
    def validate_search_request(self, operation: str, query: Optional[str] = None,
                               **search_params) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Comprehensive validation for search/list requests.
        """
        
        # Parameter validation for search operations
        param_valid, param_error = self._parameter_validator.validate_search_params(
            query=query if operation == 'search' else None,
            **search_params
        )
        
        if not param_valid:
            return False, param_error
        
        return True, None
    
    def validate_completion_request(self, task_id: str, task_data: Optional[Dict[str, Any]] = None,
                                  completion_summary: Optional[str] = None,
                                  testing_notes: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Comprehensive validation for task completion.
        """
        
        if not task_data:
            return True, None  # Cannot validate without task data
        
        # Business rules validation for completion
        completion_valid, completion_error = self._business_validator.validate_completion_requirements(
            task_data=task_data,
            completion_summary=completion_summary,
            testing_notes=testing_notes
        )
        
        if not completion_valid:
            return False, completion_error
        
        return True, None
    
    def validate_deletion_request(self, task_id: str, 
                                current_task_data: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Comprehensive validation for task deletion.
        """
        
        # Business rules validation for deletion
        deletion_valid, deletion_error = self._business_validator.validate_task_deletion_rules(
            task_id=task_id,
            current_task_data=current_task_data
        )
        
        if not deletion_valid:
            return False, deletion_error
        
        return True, None
    
    def get_parameter_validator(self) -> ParameterValidator:
        """Get parameter validator instance."""
        return self._parameter_validator
    
    def get_context_validator(self) -> ContextValidator:
        """Get context validator instance."""
        return self._context_validator
    
    def get_business_validator(self) -> BusinessValidator:
        """Get business validator instance."""
        return self._business_validator