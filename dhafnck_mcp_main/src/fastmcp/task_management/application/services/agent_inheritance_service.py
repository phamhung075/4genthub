"""Agent Inheritance Service

Handles agent assignment inheritance logic between tasks and subtasks.
"""

import logging
from typing import List, Optional
from ...domain.entities.task import Task
from ...domain.entities.subtask import Subtask
from ...domain.repositories.task_repository import TaskRepository
from ...domain.repositories.subtask_repository import SubtaskRepository
from ...domain.value_objects.task_id import TaskId
from ...domain.enums.agent_roles import AgentRole

logger = logging.getLogger(__name__)


class AgentInheritanceService:
    """Service for handling agent inheritance between tasks and subtasks."""
    
    def __init__(self, task_repository: TaskRepository, subtask_repository: SubtaskRepository):
        self._task_repository = task_repository
        self._subtask_repository = subtask_repository
    
    def apply_agent_inheritance(self, subtask: Subtask, parent_task: Optional[Task] = None) -> Subtask:
        """Apply agent inheritance logic to a subtask.
        
        If the subtask has no assignees, it inherits assignees from its parent task.
        
        Args:
            subtask: The subtask to apply inheritance to
            parent_task: Optional parent task (will be fetched if not provided)
            
        Returns:
            Subtask: The subtask with inheritance applied
        """
        if subtask.should_inherit_assignees():
            # Get parent task if not provided
            if not parent_task:
                parent_task = self._task_repository.find_by_id(subtask.parent_task_id)
            
            if parent_task:
                parent_assignees = parent_task.get_inherited_assignees_for_subtasks()
                if parent_assignees:
                    logger.info(f"Applying agent inheritance: subtask {subtask.id} inheriting {len(parent_assignees)} assignees from parent task {parent_task.id}")
                    subtask.inherit_assignees_from_parent(parent_assignees)
                else:
                    logger.info(f"No assignees to inherit: parent task {parent_task.id} has no assignees")
            else:
                logger.warning(f"Cannot apply inheritance: parent task {subtask.parent_task_id} not found")
        else:
            logger.debug(f"Subtask {subtask.id} already has assignees, no inheritance needed")
        
        return subtask
    
    def apply_inheritance_to_all_subtasks(self, task_id: TaskId) -> List[Subtask]:
        """Apply agent inheritance to all subtasks of a task.
        
        This is useful when a task's assignees are updated and all subtasks
        without explicit assignees should inherit the new assignees.
        
        Args:
            task_id: ID of the parent task
            
        Returns:
            List[Subtask]: List of subtasks that were updated
        """
        # Get parent task
        parent_task = self._task_repository.find_by_id(task_id)
        if not parent_task:
            logger.error(f"Parent task {task_id} not found for inheritance update")
            return []
        
        # Get all subtasks
        subtasks = self._subtask_repository.find_by_parent_task_id(task_id)
        updated_subtasks = []
        
        for subtask in subtasks:
            if subtask.should_inherit_assignees():
                original_assignees = subtask.assignees.copy()
                self.apply_agent_inheritance(subtask, parent_task)
                
                # Save if changed
                if subtask.assignees != original_assignees:
                    self._subtask_repository.save(subtask)
                    updated_subtasks.append(subtask)
                    logger.info(f"Updated subtask {subtask.id} with inherited assignees: {subtask.assignees}")
        
        logger.info(f"Applied inheritance to {len(updated_subtasks)} subtasks for task {task_id}")
        return updated_subtasks
    
    def validate_agent_assignments(self, assignees: List[str]) -> List[str]:
        """Validate agent assignments using domain validation.
        
        Args:
            assignees: List of assignee strings
            
        Returns:
            List[str]: Validated and normalized assignees
            
        Raises:
            ValueError: If any assignees are invalid
        """
        # Use Task entity's validation method for consistency
        dummy_task = Task(title="dummy", description="dummy")  # Temporary task for validation
        return dummy_task.validate_assignee_list(assignees)
    
    def get_inheritance_summary(self, task_id: TaskId) -> dict:
        """Get summary of agent inheritance for a task and its subtasks.
        
        Args:
            task_id: ID of the parent task
            
        Returns:
            dict: Summary of inheritance status
        """
        parent_task = self._task_repository.find_by_id(task_id)
        if not parent_task:
            return {"error": f"Task {task_id} not found"}
        
        subtasks = self._subtask_repository.find_by_parent_task_id(task_id)
        
        summary = {
            "task_id": str(task_id),
            "parent_assignees": parent_task.assignees,
            "parent_assignee_count": len(parent_task.assignees),
            "total_subtasks": len(subtasks),
            "subtasks_with_assignees": 0,
            "subtasks_inheriting": 0,
            "subtask_details": []
        }
        
        for subtask in subtasks:
            subtask_info = {
                "id": str(subtask.id),
                "title": subtask.title,
                "has_assignees": subtask.has_assignees(),
                "should_inherit": subtask.should_inherit_assignees(),
                "current_assignees": subtask.assignees,
                "assignee_count": len(subtask.assignees)
            }
            
            if subtask.has_assignees():
                summary["subtasks_with_assignees"] += 1
            if subtask.should_inherit_assignees():
                summary["subtasks_inheriting"] += 1
            
            summary["subtask_details"].append(subtask_info)
        
        return summary