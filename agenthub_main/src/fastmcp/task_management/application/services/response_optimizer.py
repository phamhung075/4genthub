"""Response Optimizer Service for MCP Response Optimization

This module implements the ResponseOptimizer class to reduce response redundancy
and improve AI parsing efficiency by removing duplicate fields and optimizing
response structure.

Based on MCP Response Optimization Recommendations:
- Target: 60% reduction in response size
- Remove duplicate fields (operation_id, timestamp, operation name)
- Flatten nested confirmation objects
- Remove null/empty fields
"""

import logging
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from copy import deepcopy
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ResponseProfile(Enum):
    """Response profile levels for different verbosity needs"""
    MINIMAL = "minimal"      # Just success + data (smallest payload)
    STANDARD = "standard"     # Success + data + meta (default)
    DETAILED = "detailed"     # Full response with hints (for AI agents)
    DEBUG = "debug"          # Everything including traces (development)


class ResponseOptimizer:
    """
    Optimizes MCP responses by removing redundancy and compressing structure.
    
    This class addresses the issues identified in the optimization analysis:
    - Duplicate fields at multiple levels
    - Nested confirmation objects
    - Redundant metadata
    - Verbose workflow guidance
    """
    
    # High-frequency operations that should use MINIMAL profile
    HIGH_FREQUENCY_OPS = [
        "list", "get_status", "health_check", "ping", 
        "get_metrics", "get_statistics", "list_agents"
    ]
    
    # AI agent indicators in request headers or parameters
    AI_AGENT_INDICATORS = [
        "coding-agent", "@test-orchestrator-agent", "debugger-agent",
        "system-architect-agent", "documentation-agent", "ai-agent",
        "agent", "autonomous", "orchestrator"
    ]
    
    # Development/debug indicators
    DEBUG_INDICATORS = [
        "debug", "trace", "verbose", "development", "test"
    ]
    
    def __init__(self):
        """Initialize the ResponseOptimizer"""
        self.metrics = {
            "total_optimized": 0,
            "total_bytes_saved": 0,
            "average_compression_ratio": 0.0,
            "profile_usage": {
                "minimal": 0,
                "standard": 0,
                "detailed": 0,
                "debug": 0
            }
        }
        
    def optimize_response(
        self, 
        response: Dict[str, Any],
        profile: Optional[ResponseProfile] = None,
        request_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main optimization method that coordinates all optimization steps.
        
        Args:
            response: The original response to optimize
            profile: The response profile to use (auto-selected if None)
            request_context: Optional context for auto-selecting profile
            
        Returns:
            Optimized response with reduced size and cleaner structure
        """
        # Auto-select profile if not provided
        if profile is None:
            profile = self.auto_select_profile(response, request_context)
            logger.debug(f"Auto-selected profile: {profile.value}")
        
        # Track original size for metrics
        original_size = len(str(response))
        
        # Create a deep copy to avoid modifying the original
        optimized = deepcopy(response)
        
        # Step 1: Remove duplicate fields
        optimized = self.remove_duplicates(optimized)
        
        # Step 2: Flatten nested structures
        optimized = self.flatten_structure(optimized)
        
        # Step 3: Remove null/empty fields
        optimized = self.remove_nulls(optimized)
        
        # Step 4: Apply profile-based filtering
        optimized = self.apply_profile(optimized, profile)
        
        # Step 5: Merge and consolidate metadata
        optimized = self.merge_metadata(optimized)
        
        # Update metrics
        optimized_size = len(str(optimized))
        self._update_metrics(original_size, optimized_size, profile)
        
        logger.debug(f"Response optimized with {profile.value} profile: {original_size} -> {optimized_size} bytes "
                    f"({self._calculate_reduction_percentage(original_size, optimized_size):.1f}% reduction)")
        
        return optimized
    
    def auto_select_profile(
        self,
        response: Dict[str, Any],
        request_context: Optional[Dict[str, Any]] = None
    ) -> ResponseProfile:
        """
        Automatically select the appropriate response profile based on context.
        
        Args:
            response: The response being optimized
            request_context: Optional request context with headers, params, etc.
            
        Returns:
            The selected ResponseProfile
        """
        if request_context is None:
            request_context = {}
        
        # Check for explicit profile in request
        if "profile" in request_context:
            profile_str = request_context["profile"].lower()
            for profile in ResponseProfile:
                if profile.value == profile_str:
                    return profile
        
        # Check for explicit DEBUG request first (highest priority)
        headers = request_context.get("headers", {})
        params = request_context.get("params", {})
        operation = response.get("operation", "").lower()

        # Explicit debug flag takes precedence
        if request_context.get("debug", False):
            return ResponseProfile.DEBUG

        # Check for AI agent requests (prioritize specific AI agent indicators)
        assignees = response.get("data", {}).get("assignees", [])
        user_agent = headers.get("User-Agent", "").lower()

        for indicator in self.AI_AGENT_INDICATORS:
            if (indicator in str(assignees).lower() or
                indicator in user_agent or
                indicator in str(params).lower()):
                return ResponseProfile.DETAILED

        # Check for other DEBUG indicators (headers/params only, not explicit flag)
        for indicator in self.DEBUG_INDICATORS:
            if (indicator in str(headers).lower() or
                indicator in str(params).lower()):
                return ResponseProfile.DEBUG
        
        # Check for high-frequency operations (use MINIMAL profile)
        for op in self.HIGH_FREQUENCY_OPS:
            if op in operation:
                return ResponseProfile.MINIMAL
        
        # Check response size - use MINIMAL for large list responses
        if "data" in response:
            data = response["data"]
            if isinstance(data, dict):
                # Check for list operations with many items
                for key in ["tasks", "items", "results", "contexts", "agents"]:
                    if key in data and isinstance(data[key], list) and len(data[key]) > 10:
                        return ResponseProfile.MINIMAL
        
        # Default to STANDARD profile
        return ResponseProfile.STANDARD
    
    def remove_duplicates(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove duplicate fields that appear at multiple levels.
        
        Addresses issues like:
        - operation_id at root AND in confirmation.operation_details
        - timestamp at root AND in confirmation.operation_details
        - operation name at root AND in confirmation.operation_details
        """
        # If confirmation.operation_details exists and duplicates root fields, remove them
        if "confirmation" in response and "operation_details" in response.get("confirmation", {}):
            operation_details = response["confirmation"]["operation_details"]
            
            # Remove duplicates from operation_details
            fields_to_check = ["operation", "operation_id", "timestamp"]
            for field in fields_to_check:
                if field in response and field in operation_details:
                    if response[field] == operation_details[field]:
                        # Remove from operation_details since it's already at root
                        del operation_details[field]
            
            # If operation_details is now empty, remove it
            if not operation_details:
                del response["confirmation"]["operation_details"]
        
        # Remove redundant success indicators
        if "status" in response and "success" in response:
            # If status == "success", success is redundant
            if response["status"] == "success" and response["success"] is True:
                del response["status"]  # Keep success for backward compatibility
            elif response["status"] == "failure" and response["success"] is False:
                del response["status"]  # Keep success for backward compatibility
        
        # Remove operation_completed if it matches success
        if "confirmation" in response and "operation_completed" in response.get("confirmation", {}):
            if response.get("success") == response["confirmation"]["operation_completed"]:
                del response["confirmation"]["operation_completed"]
        
        return response
    
    def flatten_structure(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten deeply nested structures to improve readability and reduce size.
        
        Transforms:
        - Nested confirmation objects into flat structure
        - Single-item arrays into scalar values
        """
        # Flatten confirmation if it only contains basic fields
        if "confirmation" in response:
            confirmation = response["confirmation"]
            
            # If confirmation only has data_persisted and empty partial_failures, flatten it
            if (len(confirmation) <= 3 and 
                "data_persisted" in confirmation and
                confirmation.get("partial_failures", []) == []):
                
                # Move data_persisted to meta
                if "meta" not in response:
                    response["meta"] = {}
                response["meta"]["persisted"] = confirmation.get("data_persisted", False)
                
                # Remove the confirmation object
                del response["confirmation"]
        
        # Flatten single-item arrays throughout the response
        response = self._flatten_single_arrays(response)
        
        return response
    
    def remove_nulls(self, data: Union[Dict, List, Any]) -> Union[Dict, List, Any]:
        """
        Recursively remove null, None, empty strings, and empty collections.
        
        Args:
            data: The data structure to clean
            
        Returns:
            Cleaned data structure with nulls removed
        """
        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                # Special case: preserve 'data' field even if empty (required field)
                if key == "data":
                    cleaned[key] = self.remove_nulls(value) if value else {}
                    continue
                
                # Special case: preserve 'projects' field even if empty (required for list operations)
                if key == "projects":
                    cleaned[key] = self.remove_nulls(value) if value else []
                    continue

                # Special case: preserve 'updated_data' field even if empty (required for update operations)
                if key == "updated_data":
                    cleaned[key] = self.remove_nulls(value) if value else {}
                    continue
                    
                # Recursively clean the value
                cleaned_value = self.remove_nulls(value)
                
                # Only include if not null/empty
                if cleaned_value is not None:
                    # Skip empty strings, lists, and dicts
                    if isinstance(cleaned_value, str) and cleaned_value == "":
                        continue
                    if isinstance(cleaned_value, (list, dict)) and len(cleaned_value) == 0:
                        continue
                    cleaned[key] = cleaned_value
            return cleaned
        
        elif isinstance(data, list):
            # Remove None values from lists
            cleaned = [self.remove_nulls(item) for item in data if item is not None]
            return cleaned
        
        else:
            return data
    
    def apply_profile(self, response: Dict[str, Any], profile: ResponseProfile) -> Dict[str, Any]:
        """
        Apply response profile to filter fields based on verbosity level.
        
        Args:
            response: The response to filter
            profile: The profile to apply
            
        Returns:
            Filtered response based on profile
        """
        if profile == ResponseProfile.MINIMAL:
            # Only keep essential fields
            minimal_fields = ["success", "operation", "data", "error"]
            filtered = {k: v for k, v in response.items() if k in minimal_fields}
            # Ensure data field is preserved even if empty
            if "data" in response and "data" not in filtered:
                filtered["data"] = response["data"]
            return filtered
        
        elif profile == ResponseProfile.STANDARD:
            # Keep standard fields plus meta
            standard_fields = ["success", "operation", "data", "meta", "operation_id", "timestamp", "error"]
            filtered = {k: v for k, v in response.items() if k in standard_fields}
            
            # Ensure meta exists if we have metadata
            if "operation_id" in response or "timestamp" in response:
                if "meta" not in filtered:
                    filtered["meta"] = {}
                if "operation_id" in response:
                    filtered["meta"]["id"] = response["operation_id"]
                    del filtered["operation_id"]
                if "timestamp" in response:
                    filtered["meta"]["timestamp"] = response["timestamp"]
                    del filtered["timestamp"]
            
            return filtered
        
        elif profile == ResponseProfile.DETAILED:
            # Include workflow guidance and hints
            excluded_fields = ["confirmation"]  # Still exclude redundant confirmation
            filtered = {k: v for k, v in response.items() if k not in excluded_fields}
            
            # Simplify workflow_guidance if present
            if "workflow_guidance" in filtered:
                filtered["hints"] = self._simplify_workflow_guidance(filtered["workflow_guidance"])
                del filtered["workflow_guidance"]
            
            return filtered
        
        else:  # DEBUG profile
            # Return everything for debugging, plus add debug info
            debug_response = response.copy()
            
            # Add debug metadata if not present
            if "debug_info" not in debug_response:
                debug_response["debug_info"] = {
                    "profile_used": "debug",
                    "optimization_steps": [
                        "duplicates_removed",
                        "structure_flattened", 
                        "nulls_removed",
                        "metadata_merged"
                    ],
                    "original_size_estimate": len(str(response)),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            return debug_response
    
    def merge_metadata(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Consolidate duplicate metadata into a single location.
        
        Merges scattered metadata fields into a unified 'meta' object.
        """
        # Create meta object if it doesn't exist
        if "meta" not in response:
            response["meta"] = {}
        
        # Move top-level metadata fields to meta
        metadata_fields = ["operation_id", "timestamp", "operation"]
        for field in metadata_fields:
            if field in response and field not in ["data", "success", "error"]:
                if field == "operation_id":
                    response["meta"]["id"] = response[field]
                else:
                    response["meta"][field] = response[field]
                del response[field]
        
        # If confirmation exists and has useful data, merge it
        if "confirmation" in response:
            confirmation = response["confirmation"]
            if "data_persisted" in confirmation:
                response["meta"]["persisted"] = confirmation["data_persisted"]
            if "partial_failures" in confirmation and confirmation["partial_failures"]:
                response["meta"]["partial_failures"] = confirmation["partial_failures"]
            del response["confirmation"]
        
        # Clean up empty meta
        if not response.get("meta"):
            del response["meta"]
        
        return response
    
    def _flatten_single_arrays(self, data: Union[Dict, List, Any]) -> Union[Dict, List, Any]:
        """
        Recursively flatten single-item arrays to scalar values.
        
        Args:
            data: The data structure to process
            
        Returns:
            Data with single-item arrays flattened
        """
        if isinstance(data, dict):
            flattened = {}
            for key, value in data.items():
                if isinstance(value, list) and len(value) == 1:
                    # Flatten single-item array to scalar
                    flattened[key] = self._flatten_single_arrays(value[0])
                else:
                    flattened[key] = self._flatten_single_arrays(value)
            return flattened
        
        elif isinstance(data, list):
            return [self._flatten_single_arrays(item) for item in data]
        
        else:
            return data
    
    def _simplify_workflow_guidance(self, guidance: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simplify verbose workflow guidance into concise hints.
        
        Args:
            guidance: The original workflow guidance
            
        Returns:
            Simplified hints structure
        """
        hints = {}
        
        # Extract next action
        if "next_steps" in guidance:
            next_steps = guidance["next_steps"]
            if isinstance(next_steps, dict):
                if "recommendations" in next_steps and next_steps["recommendations"]:
                    hints["next"] = next_steps["recommendations"][0] if isinstance(next_steps["recommendations"], list) else str(next_steps["recommendations"])
                if "required_actions" in next_steps and next_steps["required_actions"]:
                    required = next_steps["required_actions"]
                    if isinstance(required, str):
                        hints["required"] = [required]  # Convert string back to array
                    elif isinstance(required, list):
                        hints["required"] = required[:3]  # Max 3 required actions
                    else:
                        hints["required"] = [str(required)]
            elif isinstance(next_steps, list) and next_steps:
                hints["next"] = next_steps[0]
        
        # Extract tips
        if "optional_actions" in guidance:
            hints["tips"] = guidance["optional_actions"][:2]  # Max 2 tips
        
        # Extract confidence if present
        if "autonomous_guidance" in guidance:
            auto_guidance = guidance["autonomous_guidance"]
            if "confidence" in auto_guidance:
                hints["confidence"] = auto_guidance["confidence"]
        
        return hints
    
    def _calculate_reduction_percentage(self, original: int, optimized: int) -> float:
        """Calculate the percentage reduction in size"""
        if original == 0:
            return 0.0
        return ((original - optimized) / original) * 100
    
    def _update_metrics(self, original_size: int, optimized_size: int, profile: ResponseProfile):
        """Update internal metrics for monitoring"""
        self.metrics["total_optimized"] += 1
        self.metrics["total_bytes_saved"] += (original_size - optimized_size)
        
        # Track profile usage
        self.metrics["profile_usage"][profile.value] += 1
        
        # Update average compression ratio
        reduction = self._calculate_reduction_percentage(original_size, optimized_size)
        current_avg = self.metrics["average_compression_ratio"]
        count = self.metrics["total_optimized"]
        self.metrics["average_compression_ratio"] = (
            (current_avg * (count - 1) + reduction) / count
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get optimization metrics for monitoring.
        
        Returns:
            Dictionary containing optimization statistics
        """
        return {
            "total_responses_optimized": self.metrics["total_optimized"],
            "total_bytes_saved": self.metrics["total_bytes_saved"],
            "average_compression_ratio": f"{self.metrics['average_compression_ratio']:.1f}%",
            "target_compression": "60%",
            "target_achieved": self.metrics["average_compression_ratio"] >= 60,
            "profile_usage": self.metrics["profile_usage"],
            "most_used_profile": max(self.metrics["profile_usage"], key=self.metrics["profile_usage"].get) if self.metrics["total_optimized"] > 0 else None
        }