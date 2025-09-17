"""Delete Rule Use Case

DDD use case for deleting rules with proper validation and dependency checks.
"""

from typing import Dict, Any
from ...domain.repositories.rule_repository import RuleRepository


class DeleteRuleUseCase:
    """Use case for deleting rules"""
    
    def __init__(self, rule_repository: RuleRepository):
        self._rule_repository = rule_repository
    
    async def execute(self, rule_path: str, force: bool = False) -> Dict[str, Any]:
        """Delete a rule with dependency checks"""
        try:
            # Check if rule exists
            if not await self._rule_repository.rule_exists(rule_path):
                return {
                    "success": False,
                    "error": f"Rule not found at path: {rule_path}"
                }
            
            # Check for dependent rules unless force is True
            if not force:
                dependent_rules = await self._rule_repository.get_dependent_rules(rule_path)
                if dependent_rules:
                    return {
                        "success": False,
                        "error": f"Cannot delete rule: {len(dependent_rules)} dependent rules found",
                        "dependent_rules": dependent_rules,
                        "suggestion": "Use force=True to delete anyway or remove dependencies first"
                    }
            
            # Delete the rule
            success = await self._rule_repository.delete_rule(rule_path)
            
            if success:
                return {
                    "success": True,
                    "message": f"Rule deleted successfully from {rule_path}",
                    "rule_path": rule_path,
                    "forced": force
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to delete rule from repository"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to delete rule: {str(e)}"
            }