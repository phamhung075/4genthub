"""
Subtask Workflow Guidance Module

Provides intelligent workflow guidance for subtask operations based on DDD principles.
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SubtaskWorkflowGuidance:
    """Provides workflow guidance for subtask operations."""
    
    def generate_guidance(self, action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate workflow guidance based on action and context.
        
        Args:
            action: The subtask action being performed
            context: Context including task_id and response data
            
        Returns:
            Dict containing workflow guidance with hints, next actions, and rules
        """
        try:
            guidance = {
                "hints": [],
                "next_actions": [],
                "rules": [],
                "recommendations": []
            }
            
            # Provide action-specific guidance
            if action == "create":
                guidance["hints"].append("Subtask created successfully. Remember to update progress regularly.")
                guidance["next_actions"].append({"action": "update", "description": "Update progress as you work"})
                guidance["rules"].append("Always provide completion_summary when completing subtasks")
                
            elif action == "update":
                response = context.get("response", {})
                if response.get("subtask", {}).get("progress_percentage", 0) >= 75:
                    guidance["hints"].append("Subtask is nearing completion. Prepare completion summary.")
                guidance["next_actions"].append({"action": "complete", "description": "Complete when finished"})
                
            elif action == "complete":
                guidance["hints"].append("Subtask completed! Parent task progress has been updated.")
                guidance["next_actions"].append({"action": "list", "description": "Check overall progress"})
                guidance["recommendations"].append("Review parent task to see if it's ready for completion")
                
            elif action == "list":
                response = context.get("response", {})
                subtasks = response.get("subtasks", [])
                completed = sum(1 for s in subtasks if s.get("status") == "done")
                total = len(subtasks)
                
                if completed == total and total > 0:
                    guidance["hints"].append(f"All {total} subtasks complete! Parent task ready for completion.")
                    guidance["recommendations"].append("Consider completing the parent task")
                elif completed > 0:
                    guidance["hints"].append(f"Progress: {completed}/{total} subtasks completed")
                    
            elif action == "delete":
                guidance["hints"].append("Subtask deleted. Parent task progress recalculated.")
                guidance["next_actions"].append({"action": "list", "description": "View remaining subtasks"})
                
            return guidance
            
        except Exception as e:
            logger.warning(f"Failed to generate workflow guidance: {e}")
            # Return minimal guidance on error
            return {
                "hints": ["Continue with your workflow"],
                "next_actions": [],
                "rules": [],
                "recommendations": []
            }


class SubtaskWorkflowFactory:
    """Factory for creating SubtaskWorkflowGuidance instances."""
    
    @staticmethod
    def create() -> SubtaskWorkflowGuidance:
        """
        Create and return a SubtaskWorkflowGuidance instance.
        
        Returns:
            SubtaskWorkflowGuidance: Configured workflow guidance instance
        """
        return SubtaskWorkflowGuidance()