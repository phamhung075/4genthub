"""Create Context Use Case"""

from typing import Dict, Any

from ...application.dtos.context import (
    CreateContextRequest,
    CreateContextResponse
)
from ...domain.entities.context import (
    TaskContext,
    ContextMetadata,
    ContextObjective,
    ContextSchema
)
from ...domain.repositories.context_repository import ContextRepository
from ...domain.value_objects import TaskStatus, Priority
from ...domain.value_objects.task_status import TaskStatusEnum
from ...domain.value_objects.priority import PriorityLevel


class CreateContextUseCase:
    """Use case for creating a new context"""
    
    def __init__(self, context_repository: ContextRepository):
        self._context_repository = context_repository
    
    def execute(self, request: CreateContextRequest) -> CreateContextResponse:
        """Execute the create context use case"""
        try:
            # Check if context already exists (using only task_id following clean relationship chain)
            if self._context_repository.context_exists(request.task_id):
                return CreateContextResponse.error_response(
                    f"Context already exists for task {request.task_id}"
                )
            
            # Create domain value objects
            status = TaskStatus(request.status or TaskStatusEnum.TODO.value)
            priority = Priority(request.priority or PriorityLevel.MEDIUM.label)
            
            # Create context metadata (using only task_id following clean relationship chain)
            # Timestamps handled automatically by BaseTimestampEntity
            metadata = ContextMetadata(
                task_id=request.task_id,  # Only task_id needed - other context derived from task relationships
                status=status,
                priority=priority,
                assignees=request.assignees or [],
                labels=request.labels or []
            )
            
            # Create context objective
            objective = ContextObjective(
                title=request.title,
                description=request.description,
                estimated_effort=request.estimated_effort,
                due_date=request.due_date
            )
            
            # Create context entity
            context = TaskContext(
                metadata=metadata,
                objective=objective
            )
            
            # Merge additional data if provided
            if request.data:
                context_dict = context.to_dict()
                context_dict.update(request.data)
                context = TaskContext.from_dict(context_dict)
            
            # Save the context
            result = self._context_repository.create_context(context)
            
            return CreateContextResponse.success_response(
                context=context,
                data=result,
                message="Context created successfully"
            )
            
        except ValueError as e:
            return CreateContextResponse.error_response(
                f"Validation error: {str(e)}"
            )
        except Exception as e:
            import logging
            logging.error(f"Failed to create context: {e}")
            return CreateContextResponse.error_response(
                f"Failed to create context: {str(e)}"
            )