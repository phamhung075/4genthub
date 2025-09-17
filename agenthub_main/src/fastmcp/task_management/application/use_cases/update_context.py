"""Update Context Use Case"""

from datetime import datetime, timezone

from ...application.dtos.context import (
    UpdateContextRequest,
    UpdateContextResponse
)
from ...domain.repositories.context_repository import ContextRepository


class UpdateContextUseCase:
    """Use case for updating a context"""
    
    def __init__(self, context_repository: ContextRepository):
        self._context_repository = context_repository
    
    def execute(self, request: UpdateContextRequest) -> UpdateContextResponse:
        """Execute the update context use case"""
        try:
            # Check if context exists (using only task_id following clean relationship chain)
            if not self._context_repository.context_exists(request.task_id):
                return UpdateContextResponse.error_response(
                    f"Context not found for task {request.task_id}"
                )
            
            # Get existing context (using only task_id following clean relationship chain)
            context = self._context_repository.get_context(request.task_id)
            
            if not context:
                return UpdateContextResponse.error_response(
                    f"Context not found for task {request.task_id}"
                )
            
            # Update context data if provided
            if request.data:
                context_dict = context.to_dict()
                context_dict.update(request.data)
                context = context.from_dict(context_dict)
            
            # Update timestamp
            context.metadata.updated_at = datetime.now(timezone.utc)
            
            # Save the updated context
            result = self._context_repository.update_context(context)
            
            return UpdateContextResponse.success_response(
                context=context,
                data=result,
                message="Context updated successfully"
            )
            
        except Exception as e:
            import logging
            logging.error(f"Failed to update context: {e}")
            return UpdateContextResponse.error_response(
                f"Failed to update context: {str(e)}"
            )