"""Rule Application Service

DDD application service for rule management operations.
"""

from __future__ import annotations

from typing import Any

from fastmcp.task_management.application.use_cases.create_rule import CreateRuleUseCase
from fastmcp.task_management.application.use_cases.delete_rule import DeleteRuleUseCase
from fastmcp.task_management.application.use_cases.get_rule import GetRuleUseCase
from fastmcp.task_management.application.use_cases.list_rules import ListRulesUseCase
from fastmcp.task_management.application.use_cases.update_rule import UpdateRuleUseCase
from fastmcp.task_management.application.use_cases.validate_rule import (
    ValidateRuleUseCase,
)

from ...domain.repositories.rule_repository import RuleRepository
from ...domain.value_objects import RuleFormat, RuleType


class RuleApplicationService:
    """Application service for rule management operations"""

    def __init__(self, rule_repository: RuleRepository, user_id: str | None = None):
        self._rule_repository = rule_repository
        self._user_id = user_id  # Store user context

        # Initialize use cases with user-scoped repository
        repo = self._get_user_scoped_repository(rule_repository)
        self._create_rule_use_case = CreateRuleUseCase(repo)
        self._get_rule_use_case = GetRuleUseCase(repo)
        self._list_rules_use_case = ListRulesUseCase(repo)
        self._update_rule_use_case = UpdateRuleUseCase(repo)
        self._delete_rule_use_case = DeleteRuleUseCase(repo)
        self._validate_rule_use_case = ValidateRuleUseCase(repo)

    def _get_user_scoped_repository(self, repository: Any) -> Any:
        """Get a user-scoped version of the repository if it supports user context."""
        if not repository:
            return repository
        if hasattr(repository, "with_user") and self._user_id:
            return repository.with_user(self._user_id)
        elif hasattr(repository, "user_id"):
            if self._user_id and repository.user_id != self._user_id:
                repo_class = type(repository)
                if hasattr(repository, "session"):
                    return repo_class(repository.session, user_id=self._user_id)
        return repository

    def with_user(self, user_id: str) -> RuleApplicationService:
        """Create a new service instance scoped to a specific user."""
        return RuleApplicationService(self._rule_repository, user_id)

    async def create_rule(
        self,
        rule_path: str,
        content: str,
        rule_type: RuleType,
        rule_format: RuleFormat,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new rule"""
        return await self._create_rule_use_case.execute(
            rule_path=rule_path,
            content=content,
            rule_type=rule_type,
            rule_format=rule_format,
            metadata=metadata,
        )

    async def get_rule(self, rule_path: str) -> dict[str, Any]:
        """Get a rule by path"""
        return await self._get_rule_use_case.execute(rule_path)

    async def list_rules(
        self, filters: dict[str, Any] | None = None, metadata_only: bool = False
    ) -> dict[str, Any]:
        """List rules with optional filters"""
        return await self._list_rules_use_case.execute(filters, metadata_only)

    async def update_rule(
        self,
        rule_path: str,
        content: str | None = None,
        metadata_updates: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Update an existing rule"""
        return await self._update_rule_use_case.execute(
            rule_path=rule_path, content=content, metadata_updates=metadata_updates
        )

    async def delete_rule(self, rule_path: str, force: bool = False) -> dict[str, Any]:
        """Delete a rule"""
        return await self._delete_rule_use_case.execute(rule_path, force)

    async def validate_rule(self, rule_path: str | None = None) -> dict[str, Any]:
        """Validate a rule or all rules"""
        return await self._validate_rule_use_case.execute(rule_path)

    async def backup_rules(self, backup_path: str) -> dict[str, Any]:
        """Backup all rules"""
        try:
            repo = self._get_user_scoped_repository(self._rule_repository)
            success = await repo.backup_rules(backup_path)
            if success:
                return {
                    "success": True,
                    "message": f"Rules backed up successfully to {backup_path}",
                    "backup_path": backup_path,
                }
            else:
                return {"success": False, "error": "Failed to backup rules"}
        except Exception as e:
            return {"success": False, "error": f"Failed to backup rules: {str(e)}"}

    async def restore_rules(self, backup_path: str) -> dict[str, Any]:
        """Restore rules from backup"""
        try:
            repo = self._get_user_scoped_repository(self._rule_repository)
            success = await repo.restore_rules(backup_path)
            if success:
                return {
                    "success": True,
                    "message": f"Rules restored successfully from {backup_path}",
                    "backup_path": backup_path,
                }
            else:
                return {"success": False, "error": "Failed to restore rules"}
        except Exception as e:
            return {"success": False, "error": f"Failed to restore rules: {str(e)}"}

    async def cleanup_obsolete_rules(self) -> dict[str, Any]:
        """Clean up obsolete rules"""
        try:
            repo = self._get_user_scoped_repository(self._rule_repository)
            cleaned_paths = await repo.cleanup_obsolete_rules()
            return {
                "success": True,
                "message": f"Cleaned up {len(cleaned_paths)} obsolete rules",
                "cleaned_paths": cleaned_paths,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to cleanup obsolete rules: {str(e)}",
            }

    async def get_rule_statistics(self) -> dict[str, Any]:
        """Get statistics about rules"""
        try:
            repo = self._get_user_scoped_repository(self._rule_repository)
            stats = await repo.get_rule_statistics()
            return {"success": True, "statistics": stats}
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get rule statistics: {str(e)}",
            }

    async def get_rule_dependencies(self, rule_path: str) -> dict[str, Any]:
        """Get dependencies for a rule"""
        try:
            repo = self._get_user_scoped_repository(self._rule_repository)
            dependencies = await repo.get_rule_dependencies(rule_path)
            return {
                "success": True,
                "rule_path": rule_path,
                "dependencies": dependencies,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get rule dependencies: {str(e)}",
            }

    async def get_dependent_rules(self, rule_path: str) -> dict[str, Any]:
        """Get rules that depend on the specified rule"""
        try:
            repo = self._get_user_scoped_repository(self._rule_repository)
            dependent_rules = await repo.get_dependent_rules(rule_path)
            return {
                "success": True,
                "rule_path": rule_path,
                "dependent_rules": dependent_rules,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get dependent rules: {str(e)}",
            }

    async def get_rules_by_type(self, rule_type: str) -> dict[str, Any]:
        """Get rules by type"""
        try:
            repo = self._get_user_scoped_repository(self._rule_repository)
            rules = await repo.get_rules_by_type(rule_type)
            return {
                "success": True,
                "rule_type": rule_type,
                "rules": [
                    {
                        "path": rule.metadata.path,
                        "type": rule.metadata.type.value,
                        "format": rule.metadata.format.value,
                        "description": rule.metadata.description,
                        "tags": rule.metadata.tags,
                    }
                    for rule in rules
                ],
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to get rules by type: {str(e)}"}

    async def get_rules_by_tag(self, tag: str) -> dict[str, Any]:
        """Get rules by tag"""
        try:
            repo = self._get_user_scoped_repository(self._rule_repository)
            rules = await repo.get_rules_by_tag(tag)
            return {
                "success": True,
                "tag": tag,
                "rules": [
                    {
                        "path": rule.metadata.path,
                        "type": rule.metadata.type.value,
                        "format": rule.metadata.format.value,
                        "description": rule.metadata.description,
                        "tags": rule.metadata.tags,
                    }
                    for rule in rules
                ],
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to get rules by tag: {str(e)}"}
