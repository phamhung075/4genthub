from ...domain.value_objects.priority import PriorityLevel
from typing import Optional


class OrchestratorService:
    """Basic orchestrator service placeholder."""
    
    def __init__(self, user_id: Optional[str] = None):
        self._user_id = user_id  # Store user context
    
    def with_user(self, user_id: str) -> 'OrchestratorService':
        """Create a new service instance scoped to a specific user."""
        return OrchestratorService(user_id)
    
    def _get_user_scoped_repository(self, repository):
        """Get user-scoped repository if user_id is available."""
        if self._user_id and hasattr(repository, 'with_user'):
            return repository.with_user(self._user_id)
        return repository