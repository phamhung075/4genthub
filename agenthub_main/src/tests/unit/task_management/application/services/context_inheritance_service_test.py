"""
Tests for Context Inheritance Service

Tests the logic for merging and inheriting contexts across the hierarchy:
Global → Project → Branch → Task with proper override and precedence rules.
"""

from unittest.mock import Mock

from fastmcp.task_management.application.services.context_inheritance_service import (
    ContextInheritanceService,
)


class TestContextInheritanceServiceInit:
    """Test ContextInheritanceService initialization"""

    def test_init_without_repository(self):
        """Test initialization without repository"""
        service = ContextInheritanceService()
        assert service.repository is None
        assert service._user_id is None

    def test_init_with_repository(self):
        """Test initialization with repository"""
        mock_repo = Mock()
        service = ContextInheritanceService(repository=mock_repo)
        assert service.repository == mock_repo

    def test_init_with_user_id(self):
        """Test initialization with user_id"""
        service = ContextInheritanceService(user_id="user123")
        assert service._user_id == "user123"

    def test_with_user_creates_new_instance(self):
        """Test with_user creates a new service instance"""
        service1 = ContextInheritanceService()
        service2 = service1.with_user("user456")

        assert service2._user_id == "user456"
        assert service1._user_id is None
        assert service1 is not service2


class TestGetUserScopedRepository:
    """Test _get_user_scoped_repository method"""

    def test_returns_none_for_none_repository(self):
        """Test returns None when repository is None"""
        service = ContextInheritanceService(user_id="user123")
        result = service._get_user_scoped_repository(None)
        assert result is None

    def test_with_user_method_exists(self):
        """Test repository with with_user method"""
        mock_repo = Mock()
        mock_repo.with_user = Mock(return_value="scoped_repo")

        service = ContextInheritanceService(user_id="user123")
        result = service._get_user_scoped_repository(mock_repo)

        assert result == "scoped_repo"
        mock_repo.with_user.assert_called_once_with("user123")

    def test_user_id_attribute_same_user(self):
        """Test repository with user_id attribute but same user"""
        mock_repo = Mock(spec=['user_id'])  # Only has user_id, not with_user
        mock_repo.user_id = "user123"

        service = ContextInheritanceService(user_id="user123")
        result = service._get_user_scoped_repository(mock_repo)

        # Should return repository as-is when user_id matches
        assert result == mock_repo


class TestProjectInheritance:
    """Test inherit_project_from_global method"""

    def test_basic_project_inheritance(self):
        """Test basic project inheritance from global context"""
        service = ContextInheritanceService()

        global_context = {
            "security_policies": {"mfa_required": False},
            "coding_standards": {"style": "PEP8"}
        }

        project_context = {
            "team_preferences": {"timezone": "UTC"},
            "technology_stack": {"backend": "Python"}
        }

        result = service.inherit_project_from_global(global_context, project_context)

        # Should have global data
        assert result["security_policies"]["mfa_required"] is False
        assert result["coding_standards"]["style"] == "PEP8"

        # Should have project data
        assert result["team_preferences"]["timezone"] == "UTC"
        assert result["technology_stack"]["backend"] == "Python"

        # Should have inheritance metadata
        assert "inheritance_metadata" in result
        assert result["inheritance_metadata"]["inherited_from"] == "global"

    def test_project_global_overrides(self):
        """Test project context with global overrides"""
        service = ContextInheritanceService()

        global_context = {
            "security_policies": {"mfa_required": False},
            "code_review": {"required": True}
        }

        project_context = {
            "team_preferences": {"timezone": "EST"},
            "global_overrides": {
                "security_policies.mfa_required": True
            }
        }

        result = service.inherit_project_from_global(global_context, project_context)

        # Override should be applied
        assert result["security_policies"]["mfa_required"] is True
        assert result["inheritance_metadata"]["project_overrides_applied"] == 1

    def test_project_delegation_rules(self):
        """Test project context with delegation rules"""
        service = ContextInheritanceService()

        global_context = {
            "delegation_rules": {
                "auto_delegate": {"enabled": True}
            }
        }

        project_context = {
            "delegation_rules": {
                "auto_delegate": {"max_depth": 3}
            }
        }

        result = service.inherit_project_from_global(global_context, project_context)

        # Delegation rules should be merged
        assert result["delegation_rules"]["auto_delegate"]["enabled"] is True
        assert result["delegation_rules"]["auto_delegate"]["max_depth"] == 3

    def test_project_arbitrary_fields(self):
        """Test project context with arbitrary fields"""
        service = ContextInheritanceService()

        global_context = {"base_field": "value"}
        project_context = {
            "custom_field": "custom_value",
            "another_field": {"nested": "data"}
        }

        result = service.inherit_project_from_global(global_context, project_context)

        # Arbitrary fields should be preserved
        assert result["custom_field"] == "custom_value"
        assert result["another_field"]["nested"] == "data"


class TestBranchInheritance:
    """Test inherit_branch_from_project method"""

    def test_basic_branch_inheritance(self):
        """Test basic branch inheritance from project context"""
        service = ContextInheritanceService()

        project_context = {
            "security_policies": {"mfa_required": True},
            "team_preferences": {"timezone": "UTC"}
        }

        branch_context = {
            "branch_workflow": {"ci_cd": "enabled"},
            "branch_standards": {"commit_format": "conventional"}
        }

        result = service.inherit_branch_from_project(project_context, branch_context)

        # Should have project data
        assert result["security_policies"]["mfa_required"] is True

        # Should have branch data
        assert result["branch_workflow"]["ci_cd"] == "enabled"
        assert result["branch_standards"]["commit_format"] == "conventional"

        # Should have inheritance metadata
        assert "inheritance_metadata" in result
        assert result["inheritance_metadata"]["inherited_from"] == "project"
        assert result["inheritance_metadata"]["inheritance_chain"] == ["global", "project", "branch"]

    def test_branch_local_overrides(self):
        """Test branch context with local overrides"""
        service = ContextInheritanceService()

        project_context = {
            "code_review": {"required": True, "min_approvals": 2}
        }

        branch_context = {
            "branch_workflow": {"feature_flags": True},
            "local_overrides": {
                "code_review.min_approvals": 1
            }
        }

        result = service.inherit_branch_from_project(project_context, branch_context)

        # Override should be applied
        assert result["code_review"]["min_approvals"] == 1
        assert result["inheritance_metadata"]["branch_overrides_applied"] == 1

    def test_branch_agent_assignments(self):
        """Test branch context with agent assignments"""
        service = ContextInheritanceService()

        project_context = {"base": "data"}
        branch_context = {
            "agent_assignments": {
                "coding-agent": ["task1", "task2"],
                "test-agent": ["task3"]
            }
        }

        result = service.inherit_branch_from_project(project_context, branch_context)

        # Agent assignments should be present
        assert "agent_assignments" in result
        assert result["agent_assignments"]["coding-agent"] == ["task1", "task2"]


class TestTaskInheritance:
    """Test inherit_task_from_branch method"""

    def test_basic_task_inheritance(self):
        """Test basic task inheritance from branch context"""
        service = ContextInheritanceService()

        branch_context = {
            "security_policies": {"mfa_required": True},
            "branch_workflow": {"ci_cd": "enabled"}
        }

        task_context = {
            "task_data": {
                "priority": "high",
                "deadline": "2025-12-31"
            }
        }

        result = service.inherit_task_from_branch(branch_context, task_context)

        # Should have branch data
        assert result["security_policies"]["mfa_required"] is True

        # Should have task data
        assert result["task_data"]["priority"] == "high"
        assert result["task_data"]["deadline"] == "2025-12-31"

        # Should have inheritance metadata
        assert "inheritance_metadata" in result
        assert result["inheritance_metadata"]["inherited_from"] == "branch"
        assert result["inheritance_metadata"]["inheritance_chain"] == ["global", "project", "branch", "task"]

    def test_task_local_overrides(self):
        """Test task context with local overrides"""
        service = ContextInheritanceService()

        branch_context = {
            "testing": {"coverage_threshold": 80}
        }

        task_context = {
            "task_data": {"type": "bug_fix"},
            "local_overrides": {
                "testing.coverage_threshold": 70
            }
        }

        result = service.inherit_task_from_branch(branch_context, task_context)

        # Override should be applied
        assert result["testing"]["coverage_threshold"] == 70
        assert result["inheritance_metadata"]["local_overrides_applied"] == 1

    def test_task_implementation_notes(self):
        """Test task context with implementation notes"""
        service = ContextInheritanceService()

        branch_context = {"base": "data"}
        task_context = {
            "implementation_notes": {
                "approach": "TDD",
                "considerations": ["performance", "security"]
            }
        }

        result = service.inherit_task_from_branch(branch_context, task_context)

        # Implementation notes should be present
        assert "implementation_notes" in result
        assert result["implementation_notes"]["approach"] == "TDD"

    def test_task_custom_inheritance_rules(self):
        """Test task context with custom inheritance rules"""
        service = ContextInheritanceService()

        branch_context = {
            "field1": "value1",
            "field2": "value2"
        }

        task_context = {
            "custom_inheritance_rules": {
                "exclude_keys": ["field1"],
                "force_values": {"field3": "forced"}
            }
        }

        result = service.inherit_task_from_branch(branch_context, task_context)

        # Custom rules should be applied
        assert "field1" not in result
        assert result["field3"] == "forced"
        assert result["inheritance_metadata"]["custom_rules_applied"] == 2

    def test_task_delegation_triggers(self):
        """Test task context with delegation triggers"""
        service = ContextInheritanceService()

        branch_context = {"base": "data"}
        task_context = {
            "delegation_triggers": {
                "on_completion": ["notify_team"],
                "on_error": ["escalate"]
            }
        }

        result = service.inherit_task_from_branch(branch_context, task_context)

        # Delegation triggers should be present
        assert "delegation_triggers" in result
        assert result["delegation_triggers"]["on_completion"] == ["notify_team"]


class TestDeepMerge:
    """Test _deep_merge utility method"""

    def test_merge_simple_dicts(self):
        """Test merging simple dictionaries"""
        service = ContextInheritanceService()

        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}

        result = service._deep_merge(base, override)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merge_nested_dicts(self):
        """Test merging nested dictionaries"""
        service = ContextInheritanceService()

        base = {
            "config": {"setting1": "value1", "setting2": "value2"}
        }
        override = {
            "config": {"setting2": "new_value", "setting3": "value3"}
        }

        result = service._deep_merge(base, override)

        assert result["config"]["setting1"] == "value1"
        assert result["config"]["setting2"] == "new_value"
        assert result["config"]["setting3"] == "value3"

    def test_merge_lists_with_assignees(self):
        """Test merging lists for assignees (deduplicated)"""
        service = ContextInheritanceService()

        base = {"assignees": ["agent1", "agent2"]}
        override = {"assignees": ["agent2", "agent3"]}

        result = service._deep_merge(base, override)

        # Should deduplicate while preserving order
        assert result["assignees"] == ["agent1", "agent2", "agent3"]

    def test_merge_lists_with_requirements(self):
        """Test merging lists for requirements (appended)"""
        service = ContextInheritanceService()

        base = {"requirements": ["req1", "req2"]}
        override = {"requirements": ["req3"]}

        result = service._deep_merge(base, override)

        # Should append
        assert result["requirements"] == ["req1", "req2", "req3"]


class TestApplyOverrides:
    """Test _apply_overrides utility method"""

    def test_simple_override(self):
        """Test simple key override"""
        service = ContextInheritanceService()

        context = {"field1": "value1"}
        overrides = {"field2": "value2"}

        result = service._apply_overrides(context, overrides)

        assert result["field1"] == "value1"
        assert result["field2"] == "value2"

    def test_nested_override(self):
        """Test nested key override with dot notation"""
        service = ContextInheritanceService()

        context = {
            "config": {
                "database": {"host": "localhost"}
            }
        }
        overrides = {
            "config.database.host": "prod-server"
        }

        result = service._apply_overrides(context, overrides)

        assert result["config"]["database"]["host"] == "prod-server"

    def test_create_nested_path(self):
        """Test creating nested path that doesn't exist"""
        service = ContextInheritanceService()

        context = {"existing": "data"}
        overrides = {
            "new.nested.field": "value"
        }

        result = service._apply_overrides(context, overrides)

        assert result["new"]["nested"]["field"] == "value"


class TestMergeDelegationRules:
    """Test _merge_delegation_rules utility method"""

    def test_merge_auto_delegate(self):
        """Test merging auto_delegate settings"""
        service = ContextInheritanceService()

        base_rules = {
            "auto_delegate": {"enabled": True, "max_depth": 3}
        }
        project_rules = {
            "auto_delegate": {"max_depth": 5, "timeout": 60}
        }

        result = service._merge_delegation_rules(base_rules, project_rules)

        assert result["auto_delegate"]["enabled"] is True
        assert result["auto_delegate"]["max_depth"] == 5
        assert result["auto_delegate"]["timeout"] == 60

    def test_merge_thresholds(self):
        """Test merging threshold settings"""
        service = ContextInheritanceService()

        base_rules = {
            "thresholds": {"complexity": 10}
        }
        project_rules = {
            "thresholds": {"complexity": 15, "priority": "high"}
        }

        result = service._merge_delegation_rules(base_rules, project_rules)

        assert result["thresholds"]["complexity"] == 15
        assert result["thresholds"]["priority"] == "high"


class TestCustomInheritanceRules:
    """Test custom inheritance rule processing"""

    def test_exclude_keys(self):
        """Test excluding keys from inherited context"""
        service = ContextInheritanceService()

        context = {
            "keep_this": "value1",
            "remove_this": "value2",
            "nested": {"keep": "yes", "remove": "no"}
        }

        result = service._process_exclude_keys(context, ["remove_this", "nested.remove"])

        assert "keep_this" in result
        assert "remove_this" not in result
        assert result["nested"]["keep"] == "yes"
        assert "remove" not in result["nested"]

    def test_force_values(self):
        """Test forcing specific values"""
        service = ContextInheritanceService()

        context = {"field": "old_value"}
        force_config = {"field": "forced_value"}

        result = service._process_force_values(context, force_config)

        assert result["field"] == "forced_value"

    def test_conditional_overrides(self):
        """Test conditional override processing"""
        service = ContextInheritanceService()

        context = {"environment": "production", "debug": True}
        conditional_config = [
            {
                "name": "prod_settings",
                "condition": {"type": "key_equals", "key": "environment", "value": "production"},
                "overrides": {"debug": False}
            }
        ]

        result = service._process_conditional_overrides(context, conditional_config)

        assert result["debug"] is False


class TestConditionEvaluation:
    """Test condition evaluation methods"""

    def test_key_exists_condition(self):
        """Test key_exists condition"""
        service = ContextInheritanceService()

        context = {"field1": "value", "nested": {"field2": "value"}}

        assert service._evaluate_condition(context, {"type": "key_exists", "key": "field1"}) is True
        assert service._evaluate_condition(context, {"type": "key_exists", "key": "nested.field2"}) is True
        assert service._evaluate_condition(context, {"type": "key_exists", "key": "nonexistent"}) is False

    def test_key_equals_condition(self):
        """Test key_equals condition"""
        service = ContextInheritanceService()

        context = {"status": "active", "nested": {"value": 42}}

        assert service._evaluate_condition(
            context,
            {"type": "key_equals", "key": "status", "value": "active"}
        ) is True
        assert service._evaluate_condition(
            context,
            {"type": "key_equals", "key": "nested.value", "value": 42}
        ) is True
        assert service._evaluate_condition(
            context,
            {"type": "key_equals", "key": "status", "value": "inactive"}
        ) is False

    def test_key_contains_condition(self):
        """Test key_contains condition"""
        service = ContextInheritanceService()

        context = {"message": "Hello World"}

        assert service._evaluate_condition(
            context,
            {"type": "key_contains", "key": "message", "value": "Hello"}
        ) is True
        assert service._evaluate_condition(
            context,
            {"type": "key_contains", "key": "message", "value": "Goodbye"}
        ) is False


class TestInheritanceValidation:
    """Test validate_inheritance_chain method"""

    def test_valid_task_inheritance(self):
        """Test validation of valid task inheritance"""
        service = ContextInheritanceService()

        resolved_context = {
            "inheritance_metadata": {
                "inherited_from": "branch",
                "inheritance_chain": ["global", "project", "branch", "task"]
            }
        }

        result = service.validate_inheritance_chain("task", "task123", resolved_context)

        assert result["valid"] is True
        assert len(result["issues"]) == 0

    def test_valid_branch_inheritance(self):
        """Test validation of valid branch inheritance"""
        service = ContextInheritanceService()

        resolved_context = {
            "inheritance_metadata": {
                "inherited_from": "project",
                "inheritance_chain": ["global", "project", "branch"]
            }
        }

        result = service.validate_inheritance_chain("branch", "branch123", resolved_context)

        assert result["valid"] is True
        assert len(result["issues"]) == 0

    def test_missing_inheritance_metadata(self):
        """Test validation with missing inheritance metadata"""
        service = ContextInheritanceService()

        resolved_context = {}

        result = service.validate_inheritance_chain("task", "task123", resolved_context)

        assert result["valid"] is False
        assert "Missing inheritance metadata" in result["issues"]

    def test_incorrect_inheritance_chain(self):
        """Test validation with incorrect inheritance chain"""
        service = ContextInheritanceService()

        resolved_context = {
            "inheritance_metadata": {
                "inherited_from": "branch",
                "inheritance_chain": ["global", "task"]  # Missing project and branch
            }
        }

        result = service.validate_inheritance_chain("task", "task123", resolved_context)

        assert len(result["warnings"]) > 0
        assert any("Unexpected inheritance chain" in w for w in result["warnings"])

    def test_override_path_not_found(self):
        """Test validation when override path is not in resolved context"""
        service = ContextInheritanceService()

        resolved_context = {
            "inheritance_metadata": {
                "inherited_from": "branch",
                "inheritance_chain": ["global", "project", "branch"]
            },
            "local_overrides": {
                "nonexistent.field": "value"
            }
        }

        result = service.validate_inheritance_chain("branch", "branch123", resolved_context)

        assert result["valid"] is False
        assert any("Override path not found" in issue for issue in result["issues"])


class TestUtilityMethods:
    """Test utility methods"""

    def test_get_nested_value(self):
        """Test getting nested value from context"""
        service = ContextInheritanceService()

        context = {
            "level1": {
                "level2": {
                    "level3": "target_value"
                }
            }
        }

        result = service._get_nested_value(context, "level1.level2.level3")
        assert result == "target_value"

    def test_key_exists_nested(self):
        """Test checking if nested key exists"""
        service = ContextInheritanceService()

        context = {
            "config": {
                "database": {"host": "localhost"}
            }
        }

        assert service._key_exists(context, "config.database.host") is True
        assert service._key_exists(context, "config.nonexistent") is False

    def test_get_timestamp(self):
        """Test timestamp generation"""
        service = ContextInheritanceService()

        timestamp = service._get_timestamp()

        # Should be ISO format with Z suffix
        assert isinstance(timestamp, str)
        assert timestamp.endswith('Z')
        assert 'T' in timestamp


class TestGetInheritedContext:
    """Test get_inherited_context method"""

    def test_returns_none_by_default(self):
        """Test get_inherited_context returns None (simplified implementation)"""
        service = ContextInheritanceService()

        result = service.get_inherited_context("task", "task123")

        assert result is None
