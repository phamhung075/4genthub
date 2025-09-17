"""Standardized Response Formatter for MCP Controllers

This module provides a consistent response format across all MCP controllers
to address API response inconsistencies and operation success confirmation issues.
"""

import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timezone
import uuid
from enum import Enum
import os

# Import ResponseOptimizer for response optimization
try:
    from fastmcp.task_management.application.services.response_optimizer import (
        ResponseOptimizer, ResponseProfile
    )
    OPTIMIZER_AVAILABLE = True
except ImportError:
    OPTIMIZER_AVAILABLE = False
    ResponseProfile = None

logger = logging.getLogger(__name__)


class ResponseStatus(Enum):
    """Response status types"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"


class StandardResponseFormatter:
    """Provides standardized response formatting for all MCP operations"""
    
    _instance = None
    
    def __init__(self):
        """Initialize the formatter with optional optimizer"""
        self.optimizer = ResponseOptimizer() if OPTIMIZER_AVAILABLE else None
        self.optimization_enabled = (
            OPTIMIZER_AVAILABLE and 
            os.getenv('ENABLE_RESPONSE_OPTIMIZATION', 'true').lower() in ['true', '1', 'yes', 'on']
        )
        self.legacy_mode = False
        
        if self.optimization_enabled:
            logger.info("Response optimization is ENABLED")
        else:
            logger.info("Response optimization is DISABLED")
    
    @classmethod
    def get_instance(cls):
        """Get singleton instance for backward compatibility"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def create_response(
        self,
        status: ResponseStatus,
        operation: str,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        error_code: Optional[str] = None,
        partial_failures: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        workflow_guidance: Optional[Dict[str, Any]] = None,
        request_context: Optional[Dict[str, Any]] = None,
        profile: Optional[ResponseProfile] = None
    ) -> Dict[str, Any]:
        """
        Create a standardized response format
        
        Args:
            status: The operation status (success, partial_success, failure)
            operation: The operation that was performed
            data: The main data payload (e.g., task, context, etc.)
            error: Error message if any
            error_code: Standardized error code
            partial_failures: List of partial failures for partial_success status
            metadata: Additional metadata about the operation
            workflow_guidance: Workflow guidance data if applicable
            
        Returns:
            Standardized response dictionary
        """
        # Generate operation ID for tracking
        operation_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        response = {
            # Core response structure
            "status": status.value,
            "success": status != ResponseStatus.FAILURE,  # True for success and partial_success
            "operation": operation,
            "operation_id": operation_id,
            "timestamp": timestamp,
            
            # Confirmation details
            "confirmation": {
                "operation_completed": status != ResponseStatus.FAILURE,
                "data_persisted": status != ResponseStatus.FAILURE and data is not None,
                "partial_failures": partial_failures or [],
                "operation_details": {
                    "operation": operation,
                    "operation_id": operation_id,
                    "timestamp": timestamp
                }
            }
        }
        
        # Add data if present
        if data is not None:
            response["data"] = data
            
        # Add error information if present
        if error:
            response["error"] = {
                "message": error,
                "code": error_code or "UNKNOWN_ERROR",
                "operation": operation,
                "timestamp": timestamp
            }
            
        # Add metadata if present
        if metadata:
            response["metadata"] = metadata
            
        # Add workflow guidance if present
        if workflow_guidance:
            response["workflow_guidance"] = workflow_guidance
            
        # Log the operation
        logger.info(f"Operation {operation} completed with status {status.value} (ID: {operation_id})")
        
        # Apply response optimization if enabled
        if self.optimization_enabled and self.optimizer:
            # Check for legacy mode request
            if request_context and request_context.get('headers', {}).get('X-Response-Format') == 'legacy':
                logger.debug("Legacy format requested via header")
                return response
            
            # Apply optimization with auto-selected or specified profile
            try:
                optimized = self.optimizer.optimize_response(
                    response, 
                    profile=profile,
                    request_context=request_context
                )
                logger.debug(f"Response optimized: {len(str(response))} -> {len(str(optimized))} bytes")
                return optimized
            except Exception as e:
                logger.warning(f"Response optimization failed, returning unoptimized: {e}")
                return response
        
        return response
    
    def create_success_response(
        self,
        operation: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        workflow_guidance: Optional[Dict[str, Any]] = None,
        request_context: Optional[Dict[str, Any]] = None,
        profile: Optional[ResponseProfile] = None
    ) -> Dict[str, Any]:
        """Create a success response"""
        return self.create_response(
            status=ResponseStatus.SUCCESS,
            operation=operation,
            data=data,
            metadata=metadata,
            workflow_guidance=workflow_guidance,
            request_context=request_context,
            profile=profile
        )
    
    def create_error_response(
        self,
        operation: str,
        error: str,
        error_code: str = "UNKNOWN_ERROR",
        metadata: Optional[Dict[str, Any]] = None,
        request_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create an error response"""
        return self.create_response(
            status=ResponseStatus.FAILURE,
            operation=operation,
            error=error,
            error_code=error_code,
            metadata=metadata,
            request_context=request_context
        )
    
    def create_partial_success_response(
        self,
        operation: str,
        data: Dict[str, Any],
        partial_failures: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
        workflow_guidance: Optional[Dict[str, Any]] = None,
        request_context: Optional[Dict[str, Any]] = None,
        profile: Optional[ResponseProfile] = None
    ) -> Dict[str, Any]:
        """Create a partial success response"""
        return self.create_response(
            status=ResponseStatus.PARTIAL_SUCCESS,
            operation=operation,
            data=data,
            partial_failures=partial_failures,
            metadata=metadata,
            workflow_guidance=workflow_guidance,
            request_context=request_context,
            profile=profile
        )
    
    def create_validation_error_response(
        self,
        operation: str,
        field: str,
        expected: str,
        actual: Optional[str] = None,
        hint: Optional[str] = None,
        request_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a validation error response with helpful details"""
        error_details = {
            "field": field,
            "expected": expected,
            "hint": hint or f"Please provide a valid {field}"
        }
        
        if actual:
            error_details["actual"] = actual
            
        return self.create_response(
            status=ResponseStatus.FAILURE,
            operation=operation,
            error=f"Validation failed for field: {field}",
            error_code="VALIDATION_ERROR",
            metadata={"validation_details": error_details},
            request_context=request_context
        )
    
    @staticmethod
    def verify_success(response: Dict[str, Any]) -> bool:
        """
        Verify if an operation was truly successful
        
        This addresses the issue of not trusting the success field alone
        
        Args:
            response: The response to verify
            
        Returns:
            True if the operation was successful, False otherwise
        """
        # Check multiple indicators as recommended in 4genthub.mdc
        return (
            response.get("status") == ResponseStatus.SUCCESS.value and
            response.get("success", False) and
            "error" not in response and
            response.get("confirmation", {}).get("operation_completed", False) and
            response.get("confirmation", {}).get("data_persisted", False) and
            len(response.get("confirmation", {}).get("partial_failures", [])) == 0
        )
    
    @staticmethod
    def extract_data(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Safely extract data from a standardized response
        
        Args:
            response: The response to extract data from
            
        Returns:
            The data payload or None if not present
        """
        if StandardResponseFormatter.verify_success(response):
            return response.get("data")
        return None
    
    @staticmethod
    def get_operation_id(response: Dict[str, Any]) -> Optional[str]:
        """Get the operation ID from a response for tracking"""
        return response.get("operation_id")
    
    @staticmethod
    def has_partial_failures(response: Dict[str, Any]) -> bool:
        """Check if a response has partial failures"""
        return (
            response.get("status") == ResponseStatus.PARTIAL_SUCCESS.value or
            len(response.get("confirmation", {}).get("partial_failures", [])) > 0
        )
    
    def format_success(
        self,
        data: Dict[str, Any], 
        operation: str,
        metadata: Optional[Dict[str, Any]] = None,
        request_context: Optional[Dict[str, Any]] = None,
        profile: Optional[ResponseProfile] = None
    ) -> Dict[str, Any]:
        """
        Format a raw data response into standardized success format.
        
        This method handles converting facade/service responses into the standard format.
        
        Args:
            data: Raw response data from facade/service
            operation: The operation that was performed
            metadata: Additional metadata
            
        Returns:
            Standardized success response
        """
        # If already standardized, return as-is
        if "status" in data and "operation_id" in data:
            return data
            
        # If it's a simple success/error response, extract relevant data
        if data.get("success") is True:
            # Extract the main data payload
            main_data = {}
            operation_info = {}
            
            # Standard fields to move to operation_info
            operation_fields = {"level", "context_id", "source_level", "target_level", "propagated", "inherited", "created", "count"}
            
            for key, value in data.items():
                if key in ["success", "error"]:
                    continue  # Skip these, they'll be replaced by standard format
                elif key in operation_fields:
                    operation_info[key] = value
                else:
                    main_data[key] = value
            
            # Add operation info to metadata
            if not metadata:
                metadata = {}
            metadata["operation_details"] = operation_info
            
            return self.create_success_response(
                operation=operation,
                data=main_data,
                metadata=metadata,
                request_context=request_context,
                profile=profile
            )
        
        # If it's an error response
        elif data.get("success") is False:
            error_message = data.get("error", "Unknown error occurred")
            return self.create_error_response(
                operation=operation,
                error=error_message,
                metadata=metadata,
                request_context=request_context
            )
        
        # If it's raw data without success field, treat as success
        else:
            return self.create_success_response(
                operation=operation,
                data=data,
                metadata=metadata,
                request_context=request_context,
                profile=profile
            )
    
    def format_context_response(
        self,
        data: Dict[str, Any], 
        operation: str,
        standardize_field_names: bool = True,
        request_context: Optional[Dict[str, Any]] = None,
        profile: Optional[ResponseProfile] = None
    ) -> Dict[str, Any]:
        """
        Format context operation responses with consistent field names.
        
        Args:
            data: Raw context response data
            operation: The context operation performed
            standardize_field_names: Whether to standardize field names
            
        Returns:
            Standardized context response
        """
        if not standardize_field_names:
            return self.format_success(data, operation, request_context=request_context, profile=profile)
        
        # Standardize context data field names
        standardized_data = {}
        metadata = {}
        
        if data.get("success") is True:
            logger.info(f"DEBUG format_context_response: operation={operation}, data keys={data.keys()}")
            # Handle different context operations
            if operation in ['create', 'get', 'update'] or operation.endswith('.create') or operation.endswith('.get') or operation.endswith('.update'):
                # Single context operations - return context data directly in data field
                if "context" in data and data["context"]:
                    # Return the actual context data in the data field
                    standardized_data = data["context"]
                    logger.info(f"DEBUG format_context_response: found context, standardized_data={standardized_data}")
                else:
                    # If no context, return empty dict
                    standardized_data = {}
                    logger.info(f"DEBUG format_context_response: no context found, returning empty dict")
                
            elif operation in ['list'] or operation.endswith('.list'):
                # List operations - standardize to "contexts"
                if "contexts" in data:
                    standardized_data["contexts"] = data["contexts"]
                elif "context" in data:
                    # Handle case where single context is returned instead of list
                    standardized_data["contexts"] = [data["context"]]
                    
            elif operation in ['delegate'] or operation.endswith('.delegate'):
                # Delegation operations - keep delegation info
                if "delegation" in data:
                    standardized_data["delegation_result"] = data["delegation"]
                    
            elif operation in ['resolve'] or operation.endswith('.resolve'):
                # Resolve operations - standardize to "resolved_context"
                if "context" in data:
                    standardized_data["resolved_context"] = data["context"]
                elif "resolved" in data:
                    standardized_data["resolved_context"] = data["resolved"]
            
            # Add operation metadata
            metadata["context_operation"] = {
                "level": data.get("level"),
                "context_id": data.get("context_id"),
                "source_level": data.get("source_level"),
                "target_level": data.get("target_level"),
                "inherited": data.get("inherited", False),
                "propagated": data.get("propagated", False),
                "created": data.get("created", False),
                "count": data.get("count")
            }
            
            # Remove None values from metadata
            metadata["context_operation"] = {k: v for k, v in metadata["context_operation"].items() if v is not None}
            
            return self.create_success_response(
                operation=operation,
                data=standardized_data,
                metadata=metadata,
                request_context=request_context,
                profile=profile
            )
        
        # Handle error cases
        return self.format_success(data, operation, request_context=request_context, profile=profile)


class ErrorCodes:
    """Standardized error codes for consistent error handling"""
    
    # Validation errors
    MISSING_FIELD = "MISSING_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    
    # Operation errors
    NOT_FOUND = "NOT_FOUND"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    INVALID_OPERATION = "INVALID_OPERATION"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    OPERATION_FAILED = "OPERATION_FAILED"
    UNAUTHORIZED = "UNAUTHORIZED"
    
    # System errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    CONTEXT_ERROR = "CONTEXT_ERROR"
    
    # Business logic errors
    INVALID_STATE = "INVALID_STATE"
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"
    CONSTRAINT_VIOLATION = "CONSTRAINT_VIOLATION"