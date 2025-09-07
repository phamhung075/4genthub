"""Add Context Progress Use Case"""

from datetime import datetime, timezone

from ...application.dtos.context import (
    AddProgressRequest,
    AddProgressResponse
)
from ...domain.entities.context import ContextProgressAction
from ...domain.repositories.context_repository import ContextRepository


class AddContextProgressUseCase:
    """Use case for adding progress to a context"""
    
    def __init__(self, context_repository: ContextRepository):
        self._context_repository = context_repository
    
    def execute(self, request: AddProgressRequest) -> AddProgressResponse:
        """Execute the add context progress use case"""
        try:
            # Check if context exists (using only task_id following clean relationship chain)
            if not self._context_repository.context_exists(request.task_id):
                return AddProgressResponse.error_response(
                    f"Context not found for task {request.task_id}"
                )
            
            # Create progress action
            progress = ContextProgressAction(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action=request.content,
                agent=request.agent,
                details="",
                status="completed"
            )
            
            # Add progress to context (using only task_id following clean relationship chain)
            result = self._context_repository.add_progress(request.task_id, progress)
            
            return AddProgressResponse.success_response(
                data=result,
                message="Progress added successfully"
            )
            
        except Exception as e:
            import logging
            logging.error(f"Failed to add progress: {e}")
            return AddProgressResponse.error_response(
                f"Failed to add progress: {str(e)}"
            )