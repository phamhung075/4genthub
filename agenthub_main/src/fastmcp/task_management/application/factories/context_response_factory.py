"""Context Response Factory - Standardizes context data format across all task actions"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ContextResponseFactory:
    """Factory to create standardized context response format"""
    
    @staticmethod
    def create_unified_context(context_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Create a unified context format from various context data sources.
        
        Args:
            context_data: Raw context data from various sources
            
        Returns:
            Standardized context format or None if no valid context
        """
        if not context_data:
            return None
            
        try:
            # Handle different context data formats and extract the core context
            unified_context = None
            
            # Case 1: Direct template_context (from create action)
            if "template_context" in context_data:
                unified_context = context_data["template_context"]
            
            # Case 1b: Context has success and template_context (nested from create action)
            elif "success" in context_data and "template_context" in context_data:
                unified_context = context_data["template_context"]
                
            # Case 2: Nested context structure (from next action)
            elif "context" in context_data and isinstance(context_data["context"], dict):
                nested_context = context_data["context"]
                if "template_context" in nested_context:
                    unified_context = nested_context["template_context"]
                elif "task_data" in nested_context:
                    # Handle unified context format with task_data
                    unified_context = ContextResponseFactory._convert_task_data_to_template(nested_context)
                    
            # Case 3: Context data is already the template_context
            elif "metadata" in context_data and "task_id" in context_data.get("metadata", {}):
                unified_context = context_data
                
            # Case 4: Handle task_data structure from unified context system
            elif "task_data" in context_data:
                # Convert task_data structure to template_context format
                unified_context = ContextResponseFactory._convert_task_data_to_template(context_data)
                
            # Case 5: Look for any nested structure with template_context
            else:
                for key, value in context_data.items():
                    if isinstance(value, dict):
                        if "template_context" in value:
                            unified_context = value["template_context"]
                            break
                        elif "task_data" in value:
                            unified_context = ContextResponseFactory._convert_task_data_to_template(value)
                            break
                        
            if unified_context:
                # Ensure required structure exists
                return ContextResponseFactory._ensure_complete_structure(unified_context)
                
            logger.warning("No valid context found in context_data")
            return None
            
        except Exception as e:
            logger.error(f"Error creating unified context: {e}")
            return None
    
    @staticmethod
    def _convert_task_data_to_template(context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert task_data structure from unified context to template_context format.
        
        Args:
            context_data: Context with task_data structure
            
        Returns:
            Template context format
        """
        # Extract task_data
        task_data = context_data.get("task_data", {})
        
        # Build template_context structure from task_data
        template_context = {
            "metadata": {
                "task_id": context_data.get("id", ""),
                "status": task_data.get("status", "todo"),
                "priority": task_data.get("priority", "medium"),
                "assignees": task_data.get("assignees", []),
                "labels": task_data.get("labels", []),
                "created_at": task_data.get("created_at"),
                "updated_at": task_data.get("updated_at"),
                "version": 1
            },
            "objective": {
                "title": task_data.get("title", ""),
                "description": task_data.get("description", ""),
                "estimated_effort": task_data.get("estimated_effort", ""),
                "due_date": task_data.get("due_date")
            },
            "progress": context_data.get("progress", {}) if isinstance(context_data.get("progress"), dict) else {
                "completion_percentage": context_data.get("progress", 0) if isinstance(context_data.get("progress"), (int, float)) else 0
            }
        }
        
        # Add other fields from context_data
        if "insights" in context_data:
            template_context["notes"] = {"agent_insights": context_data["insights"]}
        if "next_steps" in context_data:
            template_context["progress"]["next_steps"] = context_data["next_steps"]
            
        return template_context
    
    @staticmethod
    def _ensure_complete_structure(context: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure the context has all required sections with default values"""
        
        # Default structure template
        default_structure = {
            "metadata": {},
            "objective": {
                "title": "",
                "description": "",
                "estimated_effort": "",
                "due_date": None
            },
            "requirements": {
                "checklist": [],
                "custom_requirements": [],
                "completion_criteria": []
            },
            "technical": {
                "technologies": [],
                "frameworks": [],
                "database": "",
                "key_files": [],
                "key_directories": [],
                "architecture_notes": "",
                "patterns_used": []
            },
            "dependencies": {
                "task_dependencies": [],
                "external_dependencies": [],
                "blocked_by": []
            },
            "progress": {
                "completed_actions": [],
                "current_session_summary": "",
                "next_steps": [],
                "completion_percentage": 0.0,
                "time_spent_minutes": 0
            },
            "subtasks": {
                "items": [],
                "total_count": 0,
                "completed_count": 0,
                "progress_percentage": 0.0
            },
            "notes": {
                "agent_insights": [],
                "challenges_encountered": [],
                "solutions_applied": [],
                "decisions_made": [],
                "general_notes": ""
            },
            "custom_sections": []
        }
        
        # Merge with existing context, preserving existing values
        for section, default_values in default_structure.items():
            if section not in context:
                context[section] = default_values
            elif isinstance(default_values, dict):
                # Ensure subsections exist
                for subsection, default_value in default_values.items():
                    if subsection not in context[section]:
                        context[section][subsection] = default_value
                        
        return context
    
    @staticmethod
    def apply_to_task_response(task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply unified context format to a task response.
        
        Args:
            task_data: Task response data with context_data field
            
        Returns:
            Task response with standardized context_data
        """
        task_id = task_data.get("id", "")
        
        # If context_data is missing or null, try to fetch it directly
        if not task_data.get("context_data") and task_id:
            try:
                # Use FacadeService to maintain DDD boundaries
                from ..services.facade_service import FacadeService
                unified_facade = FacadeService.get_unified_context_facade()
                
                # Try to get context directly
                context_response = unified_facade.get_context(
                    level="task",
                    context_id=task_id,
                    include_inherited=True
                )
                
                if context_response.get("success") and context_response.get("context"):
                    task_data["context_data"] = context_response["context"]
                    logger.info(f"Manually fetched context for task {task_id}")
                else:
                    logger.debug(f"No context found for task {task_id} via manual fetch")
            except Exception as e:
                logger.warning(f"Failed to manually fetch context for task {task_id}: {e}")
        
        if "context_data" in task_data and task_data["context_data"]:
            unified_context = ContextResponseFactory.create_unified_context(task_data["context_data"])
            task_data["context_data"] = unified_context
            task_data["context_available"] = unified_context is not None
        else:
            # Ensure context_available field is always present
            task_data["context_available"] = False
            
        return task_data
    
    @staticmethod
    def apply_to_next_response(next_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply unified context format to a next task response.
        Simplifies the complex nested structure to a single context_data field.
        """
        if "task" in next_response:
            task_data = next_response["task"]
            
            # Extract context from context_info if it exists
            unified_context = None
            if "context_info" in task_data:
                context_info = task_data["context_info"] 
                unified_context = ContextResponseFactory.create_unified_context(context_info)
                
                # Apply unified context to the main task response
                task_data["context_data"] = unified_context
                task_data["context_available"] = unified_context is not None
                
                # Set context field to the context_id from metadata if available
                if unified_context and "metadata" in unified_context and "task_id" in unified_context["metadata"]:
                    task_data["context"] = unified_context["metadata"]["task_id"]
                elif "next_item" in task_data and "task" in task_data["next_item"] and "context_id" in task_data["next_item"]["task"]:
                    task_data["context"] = task_data["next_item"]["task"]["context_id"]
                
                # Remove redundant fields
                del task_data["context_info"]
            
            # Also apply to the nested task within next_item
            if "next_item" in task_data and "task" in task_data["next_item"]:
                nested_task = task_data["next_item"]["task"]
                if unified_context:
                    nested_task["context_data"] = unified_context
                    nested_task["context_available"] = True
                
        return next_response