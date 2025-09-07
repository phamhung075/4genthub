"""List Contexts Use Case"""

from ...application.dtos.context import (
    ListContextsRequest,
    ListContextsResponse
)
from ...domain.repositories.context_repository import ContextRepository


class ListContextsUseCase:
    """Use case for listing contexts"""
    
    def __init__(self, context_repository: ContextRepository):
        self._context_repository = context_repository
    
    def execute(self, request: ListContextsRequest) -> ListContextsResponse:
        """Execute the list contexts use case"""
        try:
            # Get all contexts (repository method takes no parameters)
            contexts = self._context_repository.list_contexts()
            
            return ListContextsResponse.success_response(
                contexts=contexts,
                message=f"Retrieved {len(contexts)} contexts"
            )
            
        except Exception as e:
            import logging
            logging.error(f"Failed to list contexts: {e}")
            return ListContextsResponse.error_response(
                f"Failed to list contexts: {str(e)}"
            )