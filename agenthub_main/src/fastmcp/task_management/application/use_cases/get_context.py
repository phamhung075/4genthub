"""Get Context Use Case"""

from ...application.dtos.context import (
    GetContextRequest,
    ContextResponse
)
from ...domain.repositories.context_repository import ContextRepository


class GetContextUseCase:
    """Use case for getting a context"""
    
    def __init__(self, context_repository: ContextRepository):
        self._context_repository = context_repository
    
    def execute(self, request: GetContextRequest) -> ContextResponse:
        """Execute the get context use case"""
        try:
            # Get the context (using only task_id following clean relationship chain)
            context = self._context_repository.get_context(request.task_id)
            
            if not context:
                return ContextResponse.error_response(
                    f"Context not found for task {request.task_id}"
                )
            
            return ContextResponse.success_response(
                context=context,
                message="Context retrieved successfully"
            )
            
        except Exception as e:
            import logging
            logging.error(f"Failed to get context: {e}")
            return ContextResponse.error_response(
                f"Failed to get context: {str(e)}"
            )