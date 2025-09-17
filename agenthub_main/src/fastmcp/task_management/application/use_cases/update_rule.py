"""Update Rule Use Case

DDD use case for updating rules with proper validation and business logic.
"""

from typing import Dict, Any, Optional
from ...domain.entities.rule_entity import RuleContent
from ...domain.repositories.rule_repository import RuleRepository


class UpdateRuleUseCase:
    """Use case for updating existing rules"""
    
    def __init__(self, rule_repository: RuleRepository):
        self._rule_repository = rule_repository
    
    async def execute(
        self,
        rule_path: str,
        content: Optional[str] = None,
        metadata_updates: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update an existing rule"""
        try:
            # Check if rule exists
            existing_rule = await self._rule_repository.get_rule(rule_path)
            if not existing_rule:
                return {
                    "success": False,
                    "error": f"Rule not found at path: {rule_path}"
                }
            
            # Update content if provided
            if content is not None:
                existing_rule.raw_content = content
                existing_rule.metadata.size = len(content)
            
            # Update metadata if provided
            if metadata_updates:
                if "version" in metadata_updates:
                    existing_rule.metadata.version = metadata_updates["version"]
                if "author" in metadata_updates:
                    existing_rule.metadata.author = metadata_updates["author"]
                if "description" in metadata_updates:
                    existing_rule.metadata.description = metadata_updates["description"]
                if "tags" in metadata_updates:
                    existing_rule.metadata.tags = metadata_updates["tags"]
                if "dependencies" in metadata_updates:
                    existing_rule.metadata.dependencies = metadata_updates["dependencies"]
                if "sections" in metadata_updates:
                    existing_rule.sections = metadata_updates["sections"]
                if "variables" in metadata_updates:
                    existing_rule.variables = metadata_updates["variables"]
                if "references" in metadata_updates:
                    existing_rule.references = metadata_updates["references"]
            
            # Save the updated rule
            success = await self._rule_repository.save_rule(existing_rule)
            
            if success:
                return {
                    "success": True,
                    "message": f"Rule updated successfully at {rule_path}",
                    "rule_path": rule_path,
                    "updates_applied": {
                        "content_updated": content is not None,
                        "metadata_updated": metadata_updates is not None
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to save updated rule to repository"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to update rule: {str(e)}"
            }