"""
Response Factory for Task MCP Controller

Coordinates response formatting and enrichment for task operations.
"""

import logging
from typing import Dict, Any, Optional

from ....utils.response_formatter import StandardResponseFormatter, ResponseStatus, ErrorCodes

logger = logging.getLogger(__name__)


class ResponseFactory:
    """Factory for creating and formatting task operation responses."""
    
    def __init__(self, response_formatter: StandardResponseFormatter):
        self._response_formatter = response_formatter
        logger.info("ResponseFactory initialized")
    
    def create_success_response(self, operation: str, data: Dict[str, Any],
                              workflow_guidance: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create standardized success response."""
        return self._response_formatter.create_success_response(
            operation=operation,
            data=data,
            workflow_guidance=workflow_guidance
        )
    
    def create_error_response(self, operation: str, error: str, 
                            error_code: str = ErrorCodes.OPERATION_FAILED,
                            metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create standardized error response."""
        return self._response_formatter.create_error_response(
            operation=operation,
            error=error,
            error_code=error_code,
            metadata=metadata
        )
    
    def standardize_facade_response(self, facade_response: Dict[str, Any], 
                                  operation: str) -> Dict[str, Any]:
        """
        Convert facade response to standardized format.
        
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
            
            # Extract workflow guidance if present
            workflow_guidance = None
            if "workflow_guidance" in data:
                workflow_guidance = data.pop("workflow_guidance")
            
            return self.create_success_response(
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
            
            return self.create_error_response(
                operation=operation,
                error=error_message,
                error_code=error_code,
                metadata=metadata if metadata else None
            )
    
    def enrich_response_with_metadata(self, response: Dict[str, Any], 
                                    metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Add metadata to existing response."""
        enriched_response = response.copy()
        
        if 'metadata' in enriched_response:
            enriched_response['metadata'].update(metadata)
        else:
            enriched_response['metadata'] = metadata
        
        return enriched_response
    
    def add_pagination_metadata(self, response: Dict[str, Any], 
                              total: int, limit: int, offset: int) -> Dict[str, Any]:
        """Add pagination metadata to list responses."""
        pagination_metadata = {
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": total > (offset + limit)
            }
        }
        
        return self.enrich_response_with_metadata(response, pagination_metadata)
    
    def add_operation_metadata(self, response: Dict[str, Any], 
                             operation: str, timestamp: Optional[str] = None) -> Dict[str, Any]:
        """Add operation metadata to response."""
        operation_metadata = {
            "operation_info": {
                "operation": operation,
                "timestamp": timestamp or self._response_formatter._get_timestamp()
            }
        }
        
        return self.enrich_response_with_metadata(response, operation_metadata)
    
    def create_validation_error_response(self, field: str, expected: str, 
                                       hint: str, operation: str = "validation") -> Dict[str, Any]:
        """Create standardized validation error response."""
        return self.create_error_response(
            operation=operation,
            error=f"Invalid field: {field}. Expected: {expected}",
            error_code=ErrorCodes.VALIDATION_ERROR,
            metadata={"field": field, "hint": hint}
        )
    
    def create_business_rule_error_response(self, rule_name: str, message: str, 
                                          hint: str, operation: str = "business_validation") -> Dict[str, Any]:
        """Create standardized business rule error response."""
        return self.create_error_response(
            operation=operation,
            error=f"Business rule violation ({rule_name}): {message}",
            error_code=ErrorCodes.BUSINESS_RULE_VIOLATION,
            metadata={"rule": rule_name, "hint": hint}
        )