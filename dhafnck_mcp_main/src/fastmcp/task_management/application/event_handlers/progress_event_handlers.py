"""Event handlers for progress tracking events in Vision System Phase 2.

These handlers process progress-related domain events and trigger appropriate
actions such as notifications, aggregations, and state updates.
"""

import logging
from datetime import datetime, timezone
from datetime import datetime
from typing import Optional, Dict, Any, List

from ...domain.events.progress_events import (
    ProgressUpdated, ProgressMilestoneReached, ProgressStalled,
    SubtaskProgressAggregated, ProgressBlocked, ProgressUnblocked,
    ProgressTypeCompleted, ProgressSnapshotCreated
)
from ...domain.repositories.task_repository import TaskRepository
from ...domain.repositories.context_repository import ContextRepository
from ...domain.interfaces.notification_service import NotificationService, get_notification_service
from ...domain.interfaces.event_store import EventStore, get_event_store

logger = logging.getLogger(__name__)


class ProgressUpdatedHandler:
    """Handler for ProgressUpdated events."""
    
    def __init__(self,
                 task_repository: TaskRepository,
                 context_repository: ContextRepository,
                 event_store: Optional[EventStore] = None):
        """Initialize the handler."""
        self.task_repository = task_repository
        self.context_repository = context_repository
        self.event_store = event_store
    
    async def handle(self, event: ProgressUpdated) -> None:
        """
        Handle progress updated event.
        
        Actions:
        1. Store event in event store
        2. Update task aggregate with latest progress
        3. Check for automatic milestone achievements
        4. Update related contexts
        """
        logger.info(f"Handling ProgressUpdated for task {event.task_id}: "
                   f"{event.progress_type.value} {event.old_percentage}% -> {event.new_percentage}%")
        
        try:
            # Store event if event store available
            if self.event_store:
                await self.event_store.append(event)
            
            # Get task to check for auto-milestones
            task = await self.task_repository.get_by_id(event.task_id)
            if task and task.progress_timeline:
                # Check if any milestones are automatically achieved
                for name, target in task.progress_timeline.milestones.items():
                    if (event.old_percentage < target <= event.new_percentage and
                        not task.progress_timeline.is_milestone_reached(name)):
                        logger.info(f"Auto-milestone '{name}' reached at {event.new_percentage}%")
            
            # Update context if significant progress (every 10%)
            if int(event.new_percentage / 10) > int(event.old_percentage / 10):
                await self._update_context_milestone(event)
                
        except Exception as e:
            logger.error(f"Error handling ProgressUpdated event: {e}")
    
    async def _update_context_milestone(self, event: ProgressUpdated) -> None:
        """Update context when significant progress milestones are reached."""
        task = await self.task_repository.get_by_id(event.task_id)
        if not task or not task.context_id:
            return
        
        try:
            context = await self.context_repository.get_by_id(task.context_id)
            if context:
                milestone_content = (
                    f"Progress milestone: {event.progress_type.value} reached "
                    f"{int(event.new_percentage / 10) * 10}%"
                )
                
                if not hasattr(context, 'insights') or context.insights is None:
                    context.insights = []
                
                context.insights.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "content": milestone_content,
                    "agent": event.agent_id or "progress_handler",
                    "category": "progress_milestone",
                    "importance": "medium"
                })
                
                await self.context_repository.update(context)
        except Exception as e:
            logger.error(f"Failed to update context milestone: {e}")


class ProgressMilestoneReachedHandler:
    """Handler for ProgressMilestoneReached events."""
    
    def __init__(self,
                 notification_service: Optional['NotificationService'] = None,
                 event_store: Optional['EventStore'] = None):
        """Initialize the handler."""
        self.notification_service = notification_service
        self.event_store = event_store
    
    async def handle(self, event: ProgressMilestoneReached) -> None:
        """
        Handle milestone reached event.
        
        Actions:
        1. Send notifications
        2. Log achievement
        3. Store event
        """
        logger.info(f"Milestone '{event.milestone_name}' reached for task {event.task_id} "
                   f"at {event.current_progress}%")
        
        try:
            # Store event
            if self.event_store:
                await self.event_store.append(event)
            
            # Send notification
            if self.notification_service:
                await self.notification_service.notify(
                    type="milestone_reached",
                    data={
                        "task_id": str(event.task_id),
                        "milestone": event.milestone_name,
                        "progress": event.current_progress
                    }
                )
        except Exception as e:
            logger.error(f"Error handling ProgressMilestoneReached event: {e}")


class ProgressStalledHandler:
    """Handler for ProgressStalled events."""
    
    def __init__(self,
                 task_repository: TaskRepository,
                 notification_service: Optional['NotificationService'] = None):
        """Initialize the handler."""
        self.task_repository = task_repository
        self.notification_service = notification_service
    
    async def handle(self, event: ProgressStalled) -> None:
        """
        Handle progress stalled event.
        
        Actions:
        1. Update task status if needed
        2. Send alerts
        3. Log stall information
        """
        logger.warning(f"Progress stalled for task {event.task_id} - "
                      f"No updates for {event.stall_duration_hours:.1f} hours")
        
        try:
            # Get task to check if action needed
            task = await self.task_repository.get_by_id(event.task_id)
            if not task:
                return
            
            # Send notification about stalled progress
            if self.notification_service:
                await self.notification_service.notify(
                    type="progress_stalled",
                    data={
                        "task_id": str(event.task_id),
                        "duration_hours": event.stall_duration_hours,
                        "current_progress": event.current_percentage,
                        "blockers": event.blockers
                    },
                    priority="high"
                )
            
            # Add to task context if blockers exist
            if event.blockers and task.context_id:
                await self._add_blocker_insight(task.context_id, event.blockers)
                
        except Exception as e:
            logger.error(f"Error handling ProgressStalled event: {e}")
    
    async def _add_blocker_insight(self, context_id: str, blockers: List[str]) -> None:
        """Add blocker information to context insights."""
        # Implementation would update context with blocker info
        pass


class SubtaskProgressAggregatedHandler:
    """Handler for SubtaskProgressAggregated events."""
    
    def __init__(self,
                 task_repository: TaskRepository,
                 context_repository: ContextRepository):
        """Initialize the handler."""
        self.task_repository = task_repository
        self.context_repository = context_repository
    
    async def handle(self, event: SubtaskProgressAggregated) -> None:
        """
        Handle subtask progress aggregation event.
        
        Actions:
        1. Update parent task progress
        2. Update context with aggregation info
        3. Check for cascade effects
        """
        logger.info(f"Subtask progress aggregated for parent {event.parent_task_id}: "
                   f"{event.old_parent_progress}% -> {event.new_parent_progress}%")
        
        try:
            # Get parent task
            parent_task = await self.task_repository.get_by_id(event.task_id)
            if not parent_task:
                return
            
            # Update overall progress if significant change
            if abs(event.new_parent_progress - parent_task.overall_progress) > 1.0:
                parent_task.overall_progress = event.new_parent_progress
                await self.task_repository.update(parent_task)
            
            # Check if parent has a parent (recursive aggregation)
            # This would be implemented based on task hierarchy structure
            
        except Exception as e:
            logger.error(f"Error handling SubtaskProgressAggregated event: {e}")


class ProgressTypeCompletedHandler:
    """Handler for ProgressTypeCompleted events."""
    
    def __init__(self,
                 task_repository: TaskRepository,
                 notification_service: Optional['NotificationService'] = None):
        """Initialize the handler."""
        self.task_repository = task_repository
        self.notification_service = notification_service
    
    async def handle(self, event: ProgressTypeCompleted) -> None:
        """
        Handle progress type completion event.
        
        Actions:
        1. Check if all progress types are complete
        2. Update task status if appropriate
        3. Send completion notifications
        """
        logger.info(f"Progress type {event.progress_type.value} completed for task {event.task_id}")
        
        try:
            # Get task to check overall completion
            task = await self.task_repository.get_by_id(event.task_id)
            if not task:
                return
            
            # Check if this was the last progress type to complete
            # This logic would depend on task requirements
            
            # Send notification
            if self.notification_service:
                await self.notification_service.notify(
                    type="progress_type_completed",
                    data={
                        "task_id": str(event.task_id),
                        "progress_type": event.progress_type.value,
                        "timestamp": event.completion_timestamp.isoformat()
                    }
                )
                
        except Exception as e:
            logger.error(f"Error handling ProgressTypeCompleted event: {e}")


class ProgressEventHandlerRegistry:
    """Registry for progress event handlers."""
    
    def __init__(self,
                 task_repository: TaskRepository,
                 context_repository: ContextRepository,
                 notification_service: Optional['NotificationService'] = None,
                 event_store: Optional['EventStore'] = None):
        """Initialize the registry with all handlers."""
        self.handlers = {
            ProgressUpdated: ProgressUpdatedHandler(
                task_repository, context_repository, event_store
            ),
            ProgressMilestoneReached: ProgressMilestoneReachedHandler(
                notification_service, event_store
            ),
            ProgressStalled: ProgressStalledHandler(
                task_repository, notification_service
            ),
            SubtaskProgressAggregated: SubtaskProgressAggregatedHandler(
                task_repository, context_repository
            ),
            ProgressTypeCompleted: ProgressTypeCompletedHandler(
                task_repository, notification_service
            )
        }
    
    async def handle_event(self, event: Any) -> None:
        """Route event to appropriate handler."""
        event_type = type(event)
        if event_type in self.handlers:
            handler = self.handlers[event_type]
            await handler.handle(event)
        else:
            logger.debug(f"No handler registered for event type: {event_type.__name__}")
    
    def register_handler(self, event_type: type, handler: Any) -> None:
        """Register a custom handler for an event type."""
        self.handlers[event_type] = handler