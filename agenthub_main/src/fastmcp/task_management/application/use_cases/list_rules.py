"""List Rules Use Case

DDD use case for listing rules with filtering and pagination.
"""

from typing import Dict, Any, Optional, List
from ...domain.entities.rule_entity import RuleContent
from ...domain.repositories.rule_repository import RuleRepository


class ListRulesUseCase:
    """Use case for listing rules with filters"""
    
    def __init__(self, rule_repository: RuleRepository):
        self._rule_repository = rule_repository
    
    async def execute(
        self,
        filters: Optional[Dict[str, Any]] = None,
        metadata_only: bool = False
    ) -> Dict[str, Any]:
        """List rules with optional filters"""
        try:
            if metadata_only:
                # Get only metadata for performance
                metadata_list = await self._rule_repository.list_rule_metadata(filters)
                
                rules = []
                for metadata in metadata_list:
                    rules.append({
                        "path": metadata.path,
                        "type": metadata.type.value,
                        "format": metadata.format.value,
                        "size": metadata.size,
                        "version": metadata.version,
                        "author": metadata.author,
                        "description": metadata.description,
                        "tags": metadata.tags,
                        "dependencies": metadata.dependencies,
                        "modified": metadata.modified,
                        "checksum": metadata.checksum
                    })
            else:
                # Get full rule content
                rule_list = await self._rule_repository.list_rules(filters)
                
                rules = []
                for rule in rule_list:
                    rules.append({
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
                        "references": rule.references,
                        "modified": rule.metadata.modified,
                        "checksum": rule.metadata.checksum
                    })
            
            return {
                "success": True,
                "rules": rules,
                "count": len(rules),
                "filters_applied": filters or {},
                "metadata_only": metadata_only
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to list rules: {str(e)}"
            }