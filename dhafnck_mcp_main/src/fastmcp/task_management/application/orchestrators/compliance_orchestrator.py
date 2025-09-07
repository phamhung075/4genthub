"""Compliance Orchestrator - Temporary compatibility fix."""

from typing import Optional
from ..services.orchestrator import OrchestratorService


class ComplianceOrchestrator(OrchestratorService):
    """
    Compliance orchestrator that extends the base orchestrator service.
    This is a temporary compatibility fix to resolve import issues.
    """
    
    def __init__(self, user_id: Optional[str] = None):
        super().__init__(user_id)
    
    def with_user(self, user_id: str) -> 'ComplianceOrchestrator':
        """Create a new compliance orchestrator instance scoped to a specific user."""
        return ComplianceOrchestrator(user_id)