"""Validate Dependencies Use Case"""

from typing import Union, Dict, Any
import logging

from ...domain.repositories.task_repository import TaskRepository
from ...domain.value_objects.task_id import TaskId
from ...domain.services.dependency_validation_service import DependencyValidationService
from ...domain.exceptions import TaskNotFoundError

logger = logging.getLogger(__name__)


class ValidateDependenciesUseCase:
    """Use case for validating task dependencies and dependency chains"""
    
    def __init__(self, task_repository: TaskRepository):
        self._task_repository = task_repository
        self._validation_service = DependencyValidationService(task_repository)
    
    def validate_task_dependencies(self, task_id: Union[str, int]) -> Dict[str, Any]:
        """
        Validate all dependencies for a specific task.
        
        Args:
            task_id: ID of the task to validate
            
        Returns:
            Dictionary with validation results
        """
        try:
            # Convert to domain value object
            domain_task_id = TaskId.from_string(str(task_id))
            
            # Validate the dependency chain
            validation_result = self._validation_service.validate_dependency_chain(domain_task_id)
            
            # Add use case specific information
            validation_result.update({
                "use_case": "validate_dependencies",
                "requested_task_id": str(task_id)
            })
            
            # If there are issues, provide actionable recommendations
            if validation_result.get("issues") or validation_result.get("errors"):
                validation_result["recommendations"] = self._generate_recommendations(validation_result)
            
            return validation_result
            
        except TaskNotFoundError as e:
            return {
                "valid": False,
                "error": str(e),
                "task_id": str(task_id)
            }
        except Exception as e:
            logger.error(f"Error validating dependencies for task {task_id}: {e}")
            return {
                "valid": False,
                "error": f"Validation failed: {str(e)}",
                "task_id": str(task_id)
            }
    
    def get_dependency_chain_analysis(self, task_id: Union[str, int]) -> Dict[str, Any]:
        """
        Get comprehensive dependency chain analysis for a task.
        
        Args:
            task_id: ID of the task to analyze
            
        Returns:
            Dictionary with dependency chain analysis
        """
        try:
            # Convert to domain value object
            domain_task_id = TaskId.from_string(str(task_id))
            
            # Get dependency chain status
            chain_status = self._validation_service.get_dependency_chain_status(domain_task_id)
            
            # Add analysis insights
            if "error" not in chain_status:
                chain_status["insights"] = self._generate_chain_insights(chain_status)
                chain_status["next_actions"] = self._suggest_next_actions(chain_status)
            
            return chain_status
            
        except Exception as e:
            logger.error(f"Error analyzing dependency chain for task {task_id}: {e}")
            return {
                "error": f"Analysis failed: {str(e)}",
                "task_id": str(task_id)
            }
    
    def validate_multiple_tasks(self, task_ids: list) -> Dict[str, Any]:
        """
        Validate dependencies for multiple tasks.
        
        Args:
            task_ids: List of task IDs to validate
            
        Returns:
            Dictionary with validation results for all tasks
        """
        results = {
            "overall_valid": True,
            "task_results": {},
            "summary": {
                "total_tasks": len(task_ids),
                "valid_tasks": 0,
                "invalid_tasks": 0,
                "tasks_with_issues": 0
            }
        }
        
        for task_id in task_ids:
            task_result = self.validate_task_dependencies(task_id)
            results["task_results"][str(task_id)] = task_result
            
            # Update summary
            if task_result.get("valid", False):
                results["summary"]["valid_tasks"] += 1
            else:
                results["summary"]["invalid_tasks"] += 1
                results["overall_valid"] = False
            
            if task_result.get("issues") or task_result.get("errors"):
                results["summary"]["tasks_with_issues"] += 1
        
        # Add overall recommendations
        if not results["overall_valid"]:
            results["overall_recommendations"] = self._generate_overall_recommendations(results)
        
        return results
    
    def _generate_recommendations(self, validation_result: Dict[str, Any]) -> list:
        """
        Generate actionable recommendations based on validation results.
        
        Args:
            validation_result: The validation result
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        errors = validation_result.get("errors", [])
        issues = validation_result.get("issues", [])
        
        # Handle errors first
        for error in errors:
            if "Circular dependency" in error:
                recommendations.append({
                    "type": "error_fix",
                    "priority": "high",
                    "action": "Break circular dependency chain",
                    "details": error,
                    "suggested_command": "Remove one of the dependencies to break the cycle"
                })
            elif "no longer exists" in error:
                recommendations.append({
                    "type": "error_fix",
                    "priority": "high",
                    "action": "Remove orphaned dependency",
                    "details": error,
                    "suggested_command": "Use remove_dependency to clean up missing dependencies"
                })
        
        # Handle issues
        for issue in issues:
            issue_type = issue.get("type", "unknown")
            
            if issue_type == "cancelled_dependency":
                recommendations.append({
                    "type": "dependency_cleanup",
                    "priority": "medium",
                    "action": "Review cancelled dependency",
                    "details": issue.get("message", ""),
                    "suggested_command": f"Consider removing dependency {issue.get('dependency_id', '')} or finding alternative"
                })
            elif issue_type == "blocked_dependency":
                recommendations.append({
                    "type": "dependency_unblock",
                    "priority": "high",
                    "action": "Unblock dependency",
                    "details": issue.get("message", ""),
                    "suggested_command": f"Work on unblocking task {issue.get('dependency_id', '')} first"
                })
        
        return recommendations
    
    def _generate_chain_insights(self, chain_status: Dict[str, Any]) -> list:
        """
        Generate insights about the dependency chain.
        
        Args:
            chain_status: The dependency chain status
            
        Returns:
            List of insights
        """
        insights = []
        
        stats = chain_status.get("chain_statistics", {})
        total_deps = stats.get("total_dependencies", 0)
        completed_deps = stats.get("completed_dependencies", 0)
        completion_pct = stats.get("completion_percentage", 0)
        
        if total_deps == 0:
            insights.append({
                "type": "no_dependencies",
                "message": "Task has no dependencies and can be started immediately"
            })
        elif completion_pct == 100:
            insights.append({
                "type": "ready_to_start",
                "message": "All dependencies are completed - task is ready to start"
            })
        elif completion_pct > 75:
            insights.append({
                "type": "nearly_ready",
                "message": f"Most dependencies are complete ({completed_deps}/{total_deps}) - task should be ready soon"
            })
        elif completion_pct > 25:
            insights.append({
                "type": "partial_progress",
                "message": f"Some dependencies are complete ({completed_deps}/{total_deps}) - moderate progress"
            })
        else:
            insights.append({
                "type": "early_stage",
                "message": f"Most dependencies are still pending ({total_deps - completed_deps}/{total_deps}) - task is in early stage"
            })
        
        return insights
    
    def _suggest_next_actions(self, chain_status: Dict[str, Any]) -> list:
        """
        Suggest next actions based on dependency chain status.
        
        Args:
            chain_status: The dependency chain status
            
        Returns:
            List of suggested actions
        """
        actions = []
        
        if chain_status.get("can_proceed", False):
            actions.append({
                "action": "start_task",
                "priority": "high",
                "description": "All dependencies are satisfied - task can be started",
                "command": f"Start working on task {chain_status.get('task_id', '')}"
            })
        else:
            # Find the next dependency to work on
            dependency_chain = chain_status.get("dependency_chain", [])
            for dep in dependency_chain:
                if not dep.get("is_completed", False) and dep.get("status") != "blocked":
                    actions.append({
                        "action": "work_on_dependency",
                        "priority": "high",
                        "description": f"Work on dependency: {dep.get('title', 'Unknown')}",
                        "command": f"Start working on task {dep.get('dependency_id', '')}"
                    })
                    break
        
        return actions
    
    def _generate_overall_recommendations(self, results: Dict[str, Any]) -> list:
        """
        Generate overall recommendations for multiple task validation.
        
        Args:
            results: The overall validation results
            
        Returns:
            List of overall recommendations
        """
        recommendations = []
        
        invalid_count = results["summary"]["invalid_tasks"]
        issues_count = results["summary"]["tasks_with_issues"]
        
        if invalid_count > 0:
            recommendations.append({
                "type": "dependency_cleanup",
                "priority": "high",
                "action": f"Fix {invalid_count} tasks with invalid dependencies",
                "description": "Review and fix dependency issues before proceeding"
            })
        
        if issues_count > 0:
            recommendations.append({
                "type": "dependency_review",
                "priority": "medium", 
                "action": f"Review {issues_count} tasks with dependency issues",
                "description": "Address warnings and optimize dependency chains"
            })
        
        return recommendations