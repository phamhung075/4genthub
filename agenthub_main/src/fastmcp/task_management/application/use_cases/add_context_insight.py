"""Add Context Insight Use Case"""

from datetime import datetime, timezone

from ...application.dtos.context import (
    AddInsightRequest,
    AddInsightResponse
)
from ...domain.entities.context import ContextInsight
from ...domain.repositories.context_repository import ContextRepository


class AddContextInsightUseCase:
    """Use case for adding an insight to a context"""
    
    def __init__(self, context_repository: ContextRepository):
        self._context_repository = context_repository
    
    def execute(self, request: AddInsightRequest) -> AddInsightResponse:
        """Execute the add context insight use case"""
        try:
            # Check if context exists (using only task_id following clean relationship chain)
            if not self._context_repository.context_exists(request.task_id):
                return AddInsightResponse.error_response(
                    f"Context not found for task {request.task_id}"
                )
            
            # Create insight
            insight = ContextInsight(
                timestamp=datetime.now(timezone.utc).isoformat(),
                agent=request.agent,
                category=request.category,
                content=request.content,
                importance=request.importance
            )
            
            # Add insight to context (using only task_id following clean relationship chain)
            result = self._context_repository.add_insight(request.task_id, insight)
            
            return AddInsightResponse.success_response(
                data=result,
                message="Insight added successfully"
            )
            
        except Exception as e:
            import logging
            logging.error(f"Failed to add insight: {e}")
            return AddInsightResponse.error_response(
                f"Failed to add insight: {str(e)}"
            )