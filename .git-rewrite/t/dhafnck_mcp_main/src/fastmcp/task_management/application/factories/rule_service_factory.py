"""Rule Service Factory

Factory for creating rule management services with proper dependency injection following DDD patterns.
"""

from typing import Optional
from ..services.rule_application_service import RuleApplicationService
from ...domain.repositories.rule_repository import RuleRepository


class RuleServiceFactory:
    """Factory for creating rule management services"""
    
    def __init__(self, rule_repository: Optional[RuleRepository] = None):
        self._rule_repository = rule_repository
    
    def create_rule_application_service(self) -> RuleApplicationService:
        """Create a DDD-compliant rule application service"""
        if not self._rule_repository:
            raise ValueError("RuleRepository is required for creating RuleApplicationService")
        
        return RuleApplicationService(
            rule_repository=self._rule_repository
        )
    
    def set_rule_repository(self, rule_repository: RuleRepository) -> None:
        """Set the rule repository"""
        self._rule_repository = rule_repository
    
    def get_rule_repository(self) -> Optional[RuleRepository]:
        """Get the current rule repository"""
        return self._rule_repository