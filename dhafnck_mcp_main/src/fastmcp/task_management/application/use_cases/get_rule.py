"""Get Rule Use Case

DDD use case for retrieving rules with proper domain logic.
"""

from typing import Dict, Any, Optional
from ...domain.entities.rule_entity import RuleContent
from ...domain.repositories.rule_repository import RuleRepository


class GetRuleUseCase:
    """Use case for retrieving rules"""
    
    def __init__(self, rule_repository: RuleRepository):
        self._rule_repository = rule_repository
    
    async def execute(self, rule_path: str) -> Dict[str, Any]:
        """Get a rule by its path"""
        try:
            rule = await self._rule_repository.get_rule(rule_path)
            
            if not rule:
                return {
                    "success": False,
                    "error": f"Rule not found at path: {rule_path}"
                }
            
            return {
                "success": True,
                "rule": {
                    "path": rule.metadata.path,
                    "type": rule.metadata.type.value,
                    "format": rule.metadata.format.value,
                    "content": rule.raw_content,
                    "size": rule.metadata.size,
                    "version": rule.metadata.version,
                    "author": rule.metadata.author,
                    "description": rule.metadata.description,
                    "tags": rule.metadata.tags,
                    "dependencies": rule.metadata.dependencies,
                    "sections": rule.sections,
                    "variables": rule.variables,
                    "references": rule.references
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to retrieve rule: {str(e)}"
            }