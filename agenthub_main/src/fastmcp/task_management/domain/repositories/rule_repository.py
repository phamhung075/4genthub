"""Rule Repository Interface

Domain repository interface for rule management following DDD patterns.
"""

from abc import ABC, abstractmethod
from typing import Any

from ..entities.rule_entity import RuleContent, RuleInheritance, RuleMetadata


class RuleRepository(ABC):
    """Abstract repository for rule management operations"""

    @abstractmethod
    async def save_rule(self, rule: RuleContent) -> bool:
        """Save a rule to the repository"""
        pass

    @abstractmethod
    async def get_rule(self, rule_path: str) -> RuleContent | None:
        """Get a rule by its path"""
        pass

    @abstractmethod
    async def get_rule_metadata(self, rule_path: str) -> RuleMetadata | None:
        """Get rule metadata by path"""
        pass

    @abstractmethod
    async def list_rules(
        self, filters: dict[str, Any] | None = None
    ) -> list[RuleContent]:
        """List all rules with optional filters"""
        pass

    @abstractmethod
    async def list_rule_metadata(
        self, filters: dict[str, Any] | None = None
    ) -> list[RuleMetadata]:
        """List rule metadata with optional filters"""
        pass

    @abstractmethod
    async def delete_rule(self, rule_path: str) -> bool:
        """Delete a rule by its path"""
        pass

    @abstractmethod
    async def rule_exists(self, rule_path: str) -> bool:
        """Check if a rule exists"""
        pass

    @abstractmethod
    async def get_rules_by_type(self, rule_type: str) -> list[RuleContent]:
        """Get rules by their type"""
        pass

    @abstractmethod
    async def get_rules_by_tag(self, tag: str) -> list[RuleContent]:
        """Get rules by a specific tag"""
        pass

    @abstractmethod
    async def get_rule_dependencies(self, rule_path: str) -> list[str]:
        """Get dependencies for a specific rule"""
        pass

    @abstractmethod
    async def get_dependent_rules(self, rule_path: str) -> list[str]:
        """Get rules that depend on the specified rule"""
        pass

    @abstractmethod
    async def save_rule_inheritance(self, inheritance: RuleInheritance) -> bool:
        """Save rule inheritance configuration"""
        pass

    @abstractmethod
    async def get_rule_inheritance(self, child_path: str) -> RuleInheritance | None:
        """Get rule inheritance configuration for a child rule"""
        pass

    @abstractmethod
    async def get_rule_hierarchy(self, rule_path: str) -> list[RuleInheritance]:
        """Get the complete inheritance hierarchy for a rule"""
        pass

    @abstractmethod
    async def backup_rules(self, backup_path: str) -> bool:
        """Create a backup of all rules"""
        pass

    @abstractmethod
    async def restore_rules(self, backup_path: str) -> bool:
        """Restore rules from a backup"""
        pass

    @abstractmethod
    async def validate_rule_integrity(self) -> dict[str, Any]:
        """Validate the integrity of all rules"""
        pass

    @abstractmethod
    async def cleanup_obsolete_rules(self) -> list[str]:
        """Clean up obsolete rules and return list of cleaned paths"""
        pass

    @abstractmethod
    async def get_rule_statistics(self) -> dict[str, Any]:
        """Get statistics about rules in the repository"""
        pass
