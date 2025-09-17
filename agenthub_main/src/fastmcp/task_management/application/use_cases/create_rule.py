"""Create Rule Use Case

DDD use case for creating rules with proper validation and business logic.
"""

from typing import Dict, Any, Optional
from ...domain.entities.rule_entity import RuleContent, RuleMetadata
from ...domain.repositories.rule_repository import RuleRepository
from ...domain.enums.rule_enums import RuleFormat, RuleType


class CreateRuleUseCase:
    """Use case for creating new rules"""
    
    def __init__(self, rule_repository: RuleRepository):
        self._rule_repository = rule_repository
    
    async def execute(
        self,
        rule_path: str,
        content: str,
        rule_type: RuleType,
        rule_format: RuleFormat,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new rule with validation"""
        try:
            # Check if rule already exists
            if await self._rule_repository.rule_exists(rule_path):
                return {
                    "success": False,
                    "error": f"Rule already exists at path: {rule_path}"
                }
            
            # Create rule metadata
            rule_metadata = RuleMetadata(
                path=rule_path,
                format=rule_format,
                type=rule_type,
                size=len(content),
                modified=0.0,  # Will be set by repository
                checksum="",   # Will be calculated by repository
                dependencies=[],
                version=metadata.get("version", "1.0") if metadata else "1.0",
                author=metadata.get("author", "rule_creator") if metadata else "rule_creator",
                description=metadata.get("description", "") if metadata else "",
                tags=metadata.get("tags", []) if metadata else []
            )
            
            # Create rule content
            rule_content = RuleContent(
                metadata=rule_metadata,
                raw_content=content,
                parsed_content={},
                sections={},
                references=[],
                variables={}
            )
            
            # Save the rule
            success = await self._rule_repository.save_rule(rule_content)
            
            if success:
                return {
                    "success": True,
                    "message": f"Rule created successfully at {rule_path}",
                    "rule_path": rule_path,
                    "rule_type": rule_type.value,
                    "rule_format": rule_format.value
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to save rule to repository"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create rule: {str(e)}"
            }