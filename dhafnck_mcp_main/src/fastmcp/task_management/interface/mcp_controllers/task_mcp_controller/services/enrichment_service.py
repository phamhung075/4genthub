"""
Enrichment Service for Task MCP Controller

Handles response enrichment with additional metadata and visual indicators.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class EnrichmentService:
    """Service for enriching task responses with additional information."""
    
    def __init__(self):
        logger.info("EnrichmentService initialized")
    
    def enrich_task_data(self, task_data: Dict[str, Any], 
                        include_visual_indicators: bool = True,
                        include_workflow_hints: bool = True) -> Dict[str, Any]:
        """
        Enrich task data with additional metadata and indicators.
        
        Args:
            task_data: Original task data
            include_visual_indicators: Whether to include visual indicators
            include_workflow_hints: Whether to include workflow hints
            
        Returns:
            Enriched task data
        """
        enriched_data = task_data.copy()
        
        try:
            # Add visual indicators
            if include_visual_indicators:
                visual_indicators = self._generate_visual_indicators(task_data)
                enriched_data["visual_indicators"] = visual_indicators
            
            # Add workflow hints
            if include_workflow_hints:
                workflow_hints = self._generate_workflow_hints(task_data)
                if workflow_hints:
                    enriched_data["workflow_hints"] = workflow_hints
            
            # Add computed fields
            enriched_data["computed_fields"] = self._compute_additional_fields(task_data)
            
            # Add enrichment metadata
            enriched_data["enrichment_metadata"] = {
                "enriched_at": datetime.now(timezone.utc).isoformat(),
                "enrichment_version": "1.0",
                "features_applied": []
            }
            
            if include_visual_indicators:
                enriched_data["enrichment_metadata"]["features_applied"].append("visual_indicators")
            if include_workflow_hints:
                enriched_data["enrichment_metadata"]["features_applied"].append("workflow_hints")
            
        except Exception as e:
            logger.error(f"Error enriching task data: {str(e)}")
            # Return original data if enrichment fails
            return task_data
        
        return enriched_data
    
    def _generate_visual_indicators(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate visual indicators for the task."""
        status = task_data.get("status", "pending")
        priority = task_data.get("priority", "medium")
        
        # Status indicators
        status_indicators = {
            "pending": {"emoji": "🟡", "color": "#fbbf24", "label": "Pending"},
            "in_progress": {"emoji": "🔵", "color": "#3b82f6", "label": "In Progress"},
            "completed": {"emoji": "🟢", "color": "#10b981", "label": "Completed"},
            "blocked": {"emoji": "🔴", "color": "#ef4444", "label": "Blocked"},
            "cancelled": {"emoji": "⚫", "color": "#6b7280", "label": "Cancelled"}
        }
        
        # Priority indicators
        priority_indicators = {
            "critical": {"emoji": "🚨", "color": "#dc2626", "label": "Critical"},
            "high": {"emoji": "⚡", "color": "#ea580c", "label": "High"},
            "medium": {"emoji": "📋", "color": "#0891b2", "label": "Medium"},
            "low": {"emoji": "📝", "color": "#65a30d", "label": "Low"}
        }
        
        return {
            "status": status_indicators.get(status.lower(), status_indicators["pending"]),
            "priority": priority_indicators.get(priority.lower(), priority_indicators["medium"]),
            "completion_percentage": self._calculate_completion_percentage(task_data)
        }
    
    def _generate_workflow_hints(self, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate workflow hints based on task state."""
        status = task_data.get("status", "pending")
        priority = task_data.get("priority", "medium")
        due_date = task_data.get("due_date")
        
        hints = []
        
        # Status-based hints
        if status == "pending":
            hints.append("Task is ready to start. Consider updating status to 'in_progress'.")
        elif status == "in_progress":
            hints.append("Task is active. Update progress regularly and complete when done.")
        elif status == "blocked":
            hints.append("Task is blocked. Identify and resolve blocking issues.")
        
        # Priority-based hints
        if priority in ["high", "critical"]:
            hints.append("High priority task - consider working on this soon.")
        
        # Due date hints
        if due_date:
            try:
                due_datetime = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                days_until_due = (due_datetime - now).days
                
                if days_until_due < 0:
                    hints.append("⚠️ Task is overdue!")
                elif days_until_due <= 1:
                    hints.append("📅 Task is due soon!")
                elif days_until_due <= 7:
                    hints.append("📅 Task is due within a week.")
            except ValueError:
                pass
        
        return {"hints": hints} if hints else None
    
    def _compute_additional_fields(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compute additional fields based on task data."""
        computed = {}
        
        # Compute age of task
        created_at = task_data.get("created_at")
        if created_at:
            try:
                created_datetime = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                age_days = (now - created_datetime).days
                computed["age_days"] = age_days
                
                if age_days == 0:
                    computed["age_description"] = "Created today"
                elif age_days == 1:
                    computed["age_description"] = "Created yesterday"
                elif age_days < 7:
                    computed["age_description"] = f"Created {age_days} days ago"
                elif age_days < 30:
                    computed["age_description"] = f"Created {age_days // 7} weeks ago"
                else:
                    computed["age_description"] = f"Created {age_days // 30} months ago"
            except ValueError:
                pass
        
        # Compute complexity score based on various factors
        complexity_score = 0
        
        description_length = len(task_data.get("description", ""))
        if description_length > 500:
            complexity_score += 2
        elif description_length > 100:
            complexity_score += 1
        
        assignees_count = len(task_data.get("assignees", []))
        if assignees_count > 3:
            complexity_score += 2
        elif assignees_count > 1:
            complexity_score += 1
        
        dependencies_count = len(task_data.get("dependencies", []))
        complexity_score += min(dependencies_count, 3)
        
        labels_count = len(task_data.get("labels", []))
        if labels_count > 5:
            complexity_score += 1
        
        computed["complexity_score"] = complexity_score
        if complexity_score <= 2:
            computed["complexity_description"] = "Simple"
        elif complexity_score <= 4:
            computed["complexity_description"] = "Moderate"
        elif complexity_score <= 6:
            computed["complexity_description"] = "Complex"
        else:
            computed["complexity_description"] = "Very Complex"
        
        return computed
    
    def _calculate_completion_percentage(self, task_data: Dict[str, Any]) -> int:
        """Calculate rough completion percentage based on task data."""
        status = task_data.get("status", "pending").lower()
        
        # Simple status-based percentage
        if status == "completed":
            return 100
        elif status == "in_progress":
            return 50  # Could be enhanced with more detailed tracking
        elif status == "blocked":
            return 25
        else:  # pending, cancelled
            return 0