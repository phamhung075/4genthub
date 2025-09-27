"""Enhanced Progress Tracking Service for Vision System Phase 2.

This service provides comprehensive progress tracking capabilities including:
- Multi-type progress tracking (analysis, implementation, testing, etc.)
- Progress calculation and aggregation
- Progress history and timeline management
- Milestone tracking and notifications
- Integration with subtask progress
"""

import logging
from datetime import datetime, timezone
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID

from ...domain.entities.task import Task
from ...domain.entities.context import TaskContext
from ...domain.value_objects.task_id import TaskId
from ...domain.value_objects.progress import (
    ProgressType, ProgressStatus, ProgressSnapshot, 
    ProgressTimeline, ProgressCalculationStrategy, ProgressMetadata
)
from ...domain.events.progress_events import (
    ProgressUpdated, ProgressMilestoneReached, ProgressStalled,
    SubtaskProgressAggregated, ProgressBlocked, ProgressUnblocked
)
from ...domain.repositories.task_repository import TaskRepository
from ...domain.repositories.context_repository import ContextRepository
from ...infrastructure.event_bus import EventBus, get_event_bus

logger = logging.getLogger(__name__)


class ProgressTrackingService:
    """Service for tracking and managing task progress."""
    
    def __init__(self, 
                 task_repository: TaskRepository,
                 context_repository: ContextRepository,
                 event_bus: Optional[EventBus] = None,
                 user_id: Optional[str] = None):
        """Initialize progress tracking service."""
        self.task_repository = task_repository
        self.context_repository = context_repository
        self.event_bus = event_bus or get_event_bus()
        self._user_id = user_id  # Store user context
        
        # Configuration
        self.stall_threshold_hours = 24  # Consider progress stalled after 24 hours
        self.auto_calculate_interval = 300  # Auto-calculate every 5 minutes

    def _get_user_scoped_repository(self, repository: Any) -> Any:
        """Get a user-scoped version of the repository if it supports user context."""
        if not repository:
            return repository
        if hasattr(repository, 'with_user') and self._user_id:
            return repository.with_user(self._user_id)
        elif hasattr(repository, 'user_id'):
            if self._user_id and repository.user_id != self._user_id:
                repo_class = type(repository)
                if hasattr(repository, 'session'):
                    return repo_class(repository.session, user_id=self._user_id)
        return repository

    def with_user(self, user_id: str) -> 'ProgressTrackingService':
        """Create a new service instance scoped to a specific user."""
        return ProgressTrackingService(
            self.task_repository,
            self.context_repository,
            self.event_bus,
            user_id
        )
        
    async def update_progress(self,
                            task_id: str,
                            progress_type: ProgressType,
                            percentage: float,
                            description: Optional[str] = None,
                            metadata: Optional[Dict[str, Any]] = None,
                            agent_id: Optional[str] = None) -> Task:
        """
        Update progress for a specific task and progress type.
        
        Args:
            task_id: ID of the task
            progress_type: Type of progress being updated
            percentage: Progress percentage (0-100)
            description: Optional progress description
            metadata: Optional metadata (blockers, dependencies, etc.)
            agent_id: ID of the agent making the update
            
        Returns:
            Updated task entity
        """
        # Get task using user-scoped repository
        task_repo = self._get_user_scoped_repository(self.task_repository)
        task = await task_repo.get_by_id(TaskId(task_id))
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Update progress in domain entity
        task.update_progress(
            progress_type=progress_type,
            percentage=percentage,
            description=description,
            metadata=metadata,
            agent_id=agent_id
        )
        
        # Update context with progress information
        await self._update_context_progress(task, progress_type, percentage, description)
        
        # Check for stalled progress
        await self._check_stalled_progress(task)
        
        # Save updated task
        await self.task_repository.update(task)
        
        # Publish domain events
        for event in task.get_events():
            await self.event_bus.publish(event)
        
        # Trigger subtask aggregation if needed
        if task.subtasks:
            await self._aggregate_subtask_progress(task)
        
        return task
    
    async def batch_update_progress(self,
                                  updates: List[Dict[str, Any]]) -> List[Task]:
        """
        Update progress for multiple tasks in batch.
        
        Args:
            updates: List of progress updates, each containing:
                - task_id: Task ID
                - progress_type: Progress type
                - percentage: Progress percentage
                - description: Optional description
                - metadata: Optional metadata
                - agent_id: Optional agent ID
                
        Returns:
            List of updated tasks
        """
        updated_tasks = []
        
        for update in updates:
            try:
                task = await self.update_progress(**update)
                updated_tasks.append(task)
            except Exception as e:
                logger.error(f"Failed to update progress for task {update.get('task_id')}: {e}")
        
        return updated_tasks
    
    async def calculate_overall_progress(self,
                                       task_id: str,
                                       include_subtasks: bool = True,
                                       weights: Optional[Dict[str, float]] = None) -> float:
        """
        Calculate overall progress for a task.
        
        Args:
            task_id: Task ID
            include_subtasks: Whether to include subtask progress
            weights: Optional weights for different progress types
            
        Returns:
            Overall progress percentage (0-100)
        """
        task = await self.task_repository.get_by_id(TaskId(task_id))
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Get progress from different sources
        progress_values = {}
        
        # 1. Progress timeline (different types)
        if task.progress_timeline:
            for progress_type in ProgressType:
                type_progress = task.get_progress_by_type(progress_type)
                if type_progress > 0:
                    progress_values[progress_type.value] = type_progress
        
        # 2. Subtask progress
        if include_subtasks and task.subtasks:
            subtask_progress = task.calculate_progress_from_subtasks()
            progress_values["subtasks"] = subtask_progress
        
        # Calculate weighted average
        if not progress_values:
            return 0.0
        
        return ProgressCalculationStrategy.calculate_weighted_average(
            progress_values, weights
        )
    
    async def get_progress_timeline(self,
                                  task_id: str,
                                  hours: int = 24,
                                  progress_type: Optional[ProgressType] = None) -> List[ProgressSnapshot]:
        """
        Get progress timeline for a task.
        
        Args:
            task_id: Task ID
            hours: Number of hours to look back
            progress_type: Optional filter by progress type
            
        Returns:
            List of progress snapshots
        """
        task = await self.task_repository.get_by_id(TaskId(task_id))
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        if not task.progress_timeline:
            return []
        
        # Get snapshots from timeline
        if progress_type:
            snapshots = task.progress_timeline.get_snapshots_by_type(progress_type)
            # Filter by time
            cutoff = datetime.now(timezone.utc).timestamp() - (hours * 3600)
            return [s for s in snapshots if s.timestamp.timestamp() > cutoff]
        else:
            return task.progress_timeline.get_progress_trend(hours)
    
    async def set_progress_milestone(self,
                                   task_id: str,
                                   milestone_name: str,
                                   percentage: float) -> Task:
        """
        Set a progress milestone for a task.
        
        Args:
            task_id: Task ID
            milestone_name: Name of the milestone
            percentage: Progress percentage when milestone is reached
            
        Returns:
            Updated task
        """
        task = await self.task_repository.get_by_id(TaskId(task_id))
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Add milestone
        task.add_progress_milestone(milestone_name, percentage)
        
        # Save task
        await self.task_repository.update(task)
        
        return task
    
    async def check_milestones(self, task_id: str) -> List[str]:
        """
        Check which milestones have been reached for a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            List of reached milestone names
        """
        task = await self.task_repository.get_by_id(TaskId(task_id))
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        if not task.progress_timeline:
            return []
        
        reached_milestones = []
        for name, percentage in task.progress_timeline.milestones.items():
            if task.progress_timeline.is_milestone_reached(name):
                reached_milestones.append(name)
        
        return reached_milestones
    
    async def get_progress_summary(self, task_id: str) -> Dict[str, Any]:
        """
        Get comprehensive progress summary for a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Progress summary including overall progress, type breakdown, milestones, etc.
        """
        task = await self.task_repository.get_by_id(TaskId(task_id))
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        summary = {
            "task_id": task_id,
            "overall_progress": task.overall_progress,
            "progress_by_type": {},
            "subtask_progress": task.get_subtask_progress() if task.subtasks else None,
            "milestones": {},
            "recent_updates": [],
            "is_stalled": False,
            "blockers": []
        }
        
        if task.progress_timeline:
            # Progress by type
            for progress_type in ProgressType:
                progress = task.get_progress_by_type(progress_type)
                if progress > 0:
                    summary["progress_by_type"][progress_type.value] = progress
            
            # Milestones
            for name, percentage in task.progress_timeline.milestones.items():
                summary["milestones"][name] = {
                    "target": percentage,
                    "reached": task.progress_timeline.is_milestone_reached(name)
                }
            
            # Recent updates (last 24 hours)
            recent_snapshots = task.progress_timeline.get_progress_trend(24)
            summary["recent_updates"] = [s.to_dict() for s in recent_snapshots[-5:]]
            
            # Check if stalled
            if recent_snapshots:
                last_update = recent_snapshots[-1].timestamp
                hours_since_update = (datetime.now(timezone.utc) - last_update).total_seconds() / 3600
                summary["is_stalled"] = hours_since_update > self.stall_threshold_hours
            
            # Get blockers from latest snapshot
            latest = task.progress_timeline.get_latest_snapshot()
            if latest and latest.metadata:
                summary["blockers"] = latest.metadata.blockers
        
        return summary
    
    async def infer_progress_from_context(self, task_id: str) -> Optional[float]:
        """
        Infer progress based on context updates and insights.
        
        Args:
            task_id: Task ID
            
        Returns:
            Inferred progress percentage or None if cannot infer
        """
        # Get task and context
        task = await self.task_repository.get_by_id(TaskId(task_id))
        if not task or not task.context_id:
            return None
        
        context = await self.context_repository.get_by_id(task.context_id)
        if not context:
            return None
        
        # Analyze context for progress indicators
        progress_indicators = {
            "started": ["began", "started", "initiated", "commenced"],
            "in_progress": ["working on", "implementing", "developing", "coding"],
            "testing": ["testing", "verifying", "validating", "checking"],
            "near_completion": ["almost done", "nearly finished", "finalizing"],
            "completed": ["completed", "finished", "done", "accomplished"]
        }
        
        # Check recent insights and progress entries
        recent_text = ""
        if context.insights:
            recent_text += " ".join([i.get("content", "") for i in context.insights[-5:]])
        if context.progress:
            recent_text += " ".join([p.get("content", "") for p in context.progress[-5:]])
        
        recent_text = recent_text.lower()
        
        # Infer progress based on keywords
        if any(word in recent_text for word in progress_indicators["completed"]):
            return 100.0
        elif any(word in recent_text for word in progress_indicators["near_completion"]):
            return 85.0
        elif any(word in recent_text for word in progress_indicators["testing"]):
            return 70.0
        elif any(word in recent_text for word in progress_indicators["in_progress"]):
            return 50.0
        elif any(word in recent_text for word in progress_indicators["started"]):
            return 25.0
        
        return None
    
    async def suggest_progress_update(self, task_id: str) -> Dict[str, Any]:
        """
        Suggest a progress update based on task analysis.
        
        Args:
            task_id: Task ID
            
        Returns:
            Suggested progress update with type, percentage, and description
        """
        task = await self.task_repository.get_by_id(TaskId(task_id))
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        suggestion = {
            "task_id": task_id,
            "suggested_updates": []
        }
        
        # Analyze task to suggest progress types
        task_content = f"{task.title} {task.description}".lower()
        
        # Suggest based on task content
        if "design" in task_content or "architect" in task_content:
            suggestion["suggested_updates"].append({
                "progress_type": ProgressType.DESIGN,
                "percentage": 0.0,
                "description": "Start design phase"
            })
        
        if "implement" in task_content or "develop" in task_content or "code" in task_content:
            suggestion["suggested_updates"].append({
                "progress_type": ProgressType.IMPLEMENTATION,
                "percentage": 0.0,
                "description": "Begin implementation"
            })
        
        if "test" in task_content or "verify" in task_content:
            suggestion["suggested_updates"].append({
                "progress_type": ProgressType.TESTING,
                "percentage": 0.0,
                "description": "Start testing phase"
            })
        
        if "document" in task_content or "readme" in task_content:
            suggestion["suggested_updates"].append({
                "progress_type": ProgressType.DOCUMENTATION,
                "percentage": 0.0,
                "description": "Begin documentation"
            })
        
        # Default to general progress if no specific type found
        if not suggestion["suggested_updates"]:
            suggestion["suggested_updates"].append({
                "progress_type": ProgressType.GENERAL,
                "percentage": 0.0,
                "description": "Start task"
            })
        
        # Add inferred progress if available
        inferred_progress = await self.infer_progress_from_context(task_id)
        if inferred_progress is not None:
            suggestion["inferred_progress"] = inferred_progress
        
        return suggestion
    
    async def _update_context_progress(self,
                                     task: Task,
                                     progress_type: ProgressType,
                                     percentage: float,
                                     description: Optional[str]) -> None:
        """Update context with progress information."""
        if not task.context_id:
            return
        
        try:
            context = await self.context_repository.get_by_id(task.context_id)
            if context:
                # Add progress entry
                progress_entry = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "type": progress_type.value,
                    "percentage": percentage,
                    "description": description or f"Updated {progress_type.value} progress to {percentage}%"
                }
                
                if not hasattr(context, 'progress') or context.progress is None:
                    context.progress = []
                
                context.progress.append(progress_entry)
                
                # Save context
                await self.context_repository.update(context)
                
        except Exception as e:
            logger.error(f"Failed to update context progress: {e}")
    
    async def _check_stalled_progress(self, task: Task) -> None:
        """Check if task progress has stalled."""
        if not task.progress_timeline:
            return
        
        latest = task.progress_timeline.get_latest_snapshot()
        if not latest:
            return
        
        # Check time since last update
        # Ensure timestamp is timezone-aware
        timestamp = latest.timestamp
        if timestamp.tzinfo is None:
            # If naive, assume it's UTC
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        
        hours_since_update = (datetime.now(timezone.utc) - timestamp).total_seconds() / 3600
        
        if hours_since_update > self.stall_threshold_hours and latest.percentage < 100:
            # Emit stalled event
            stalled_event = ProgressStalled(
                task_id=task.id,
                last_update_timestamp=latest.timestamp,
                stall_duration_hours=hours_since_update,
                current_percentage=latest.percentage,
                blockers=latest.metadata.blockers if latest.metadata else []
            )
            await self.event_bus.publish(stalled_event)
    
    async def _aggregate_subtask_progress(self, parent_task: Task) -> None:
        """Aggregate progress from subtasks to parent."""
        if not parent_task.subtasks:
            return
        
        old_progress = parent_task.overall_progress
        
        # Get subtask progress details
        subtask_details = []
        for subtask in parent_task.subtasks:
            subtask_id = subtask.get("id")
            if subtask_id:
                try:
                    # Try to get full subtask entity if it exists
                    subtask_entity = await self.task_repository.get_by_id(TaskId(subtask_id))
                    if subtask_entity:
                        subtask_details.append({
                            "id": subtask_id,
                            "title": subtask_entity.title,
                            "progress": subtask_entity.overall_progress,
                            "status": subtask_entity.status.value
                        })
                except:
                    # Fallback to subtask dict data
                    status = subtask.get("status", "todo")
                    progress = 100.0 if status == "done" else 0.0
                    subtask_details.append({
                        "id": subtask_id,
                        "title": subtask.get("title", ""),
                        "progress": progress,
                        "status": status
                    })
        
        # Calculate new progress
        new_progress = ProgressCalculationStrategy.calculate_from_subtasks(subtask_details)
        
        # Emit aggregation event if progress changed
        if abs(new_progress - old_progress) > 0.1:  # Only if change > 0.1%
            event = SubtaskProgressAggregated(
                task_id=parent_task.id,
                parent_task_id=str(parent_task.id),
                subtask_count=len(subtask_details),
                old_parent_progress=old_progress,
                new_parent_progress=new_progress,
                subtask_progress_details=subtask_details
            )
            await self.event_bus.publish(event)