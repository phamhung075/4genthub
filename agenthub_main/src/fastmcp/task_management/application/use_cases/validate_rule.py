"""Validate Rule Use Case

DDD use case for validating rules and rule hierarchies.
"""

from typing import Dict, Any, List, Optional
from ...domain.repositories.rule_repository import RuleRepository


class ValidateRuleUseCase:
    """Use case for validating rules"""
    
    def __init__(self, rule_repository: RuleRepository):
        self._rule_repository = rule_repository
    
    async def execute(self, rule_path: Optional[str] = None) -> Dict[str, Any]:
        """Validate a specific rule or all rules"""
        try:
            if rule_path:
                # Validate specific rule
                return await self._validate_single_rule(rule_path)
            else:
                # Validate all rules
                return await self._validate_all_rules()
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to validate rules: {str(e)}"
            }
    
    async def _validate_single_rule(self, rule_path: str) -> Dict[str, Any]:
        """Validate a single rule"""
        # Check if rule exists
        if not await self._rule_repository.rule_exists(rule_path):
            return {
                "success": False,
                "error": f"Rule not found at path: {rule_path}"
            }
        
        # Get rule content
        rule = await self._rule_repository.get_rule(rule_path)
        if not rule:
            return {
                "success": False,
                "error": f"Failed to retrieve rule content for: {rule_path}"
            }
        
        validation_results = []
        
        # Validate dependencies
        for dependency in rule.metadata.dependencies:
            if not await self._rule_repository.rule_exists(dependency):
                validation_results.append({
                    "type": "dependency_error",
                    "message": f"Dependency not found: {dependency}"
                })
        
        # Validate references
        for reference in rule.references:
            if not await self._rule_repository.rule_exists(reference):
                validation_results.append({
                    "type": "reference_error",
                    "message": f"Reference not found: {reference}"
                })
        
        # Check for circular dependencies
        if await self._has_circular_dependency(rule_path):
            validation_results.append({
                "type": "circular_dependency",
                "message": f"Circular dependency detected for rule: {rule_path}"
            })
        
        return {
            "success": True,
            "rule_path": rule_path,
            "is_valid": len(validation_results) == 0,
            "validation_results": validation_results
        }
    
    async def _validate_all_rules(self) -> Dict[str, Any]:
        """Validate all rules in the repository"""
        integrity_results = await self._rule_repository.validate_rule_integrity()
        
        return {
            "success": True,
            "validation_type": "all_rules",
            "integrity_results": integrity_results
        }
    
    async def _has_circular_dependency(self, rule_path: str, visited: set = None) -> bool:
        """Check for circular dependencies recursively"""
        if visited is None:
            visited = set()
        
        if rule_path in visited:
            return True
        
        visited.add(rule_path)
        
        # Get rule dependencies
        dependencies = await self._rule_repository.get_rule_dependencies(rule_path)
        
        for dependency in dependencies:
            if await self._has_circular_dependency(dependency, visited.copy()):
                return True
        
        return False