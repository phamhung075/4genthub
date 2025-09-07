"""Tests for RuleOrchestrationFacade"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from typing import Dict, Any, Optional

from fastmcp.task_management.application.facades.rule_orchestration_facade import (
    RuleOrchestrationFacade, IRuleOrchestrationFacade
)


class TestRuleOrchestrationFacade:
    """Test suite for RuleOrchestrationFacade"""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for facade"""
        return {
            'rule_orchestration_use_case': Mock(),
            'rule_composition_service': Mock(),
            'rule_parser_service': Mock(),
            'project_root': Path('/test/project'),
            'rules_dir': Path('/test/project/.cursor/rules')
        }

    @pytest.fixture
    def facade(self, mock_dependencies):
        """Create facade instance with mocked dependencies"""
        return RuleOrchestrationFacade(**mock_dependencies)

    def test_facade_initialization(self, mock_dependencies):
        """Test facade initializes correctly with dependencies"""
        facade = RuleOrchestrationFacade(**mock_dependencies)
        
        assert facade.rule_orchestration_use_case == mock_dependencies['rule_orchestration_use_case']
        assert facade.rule_composition_service == mock_dependencies['rule_composition_service']
        assert facade.rule_parser_service == mock_dependencies['rule_parser_service']
        assert facade.project_root == mock_dependencies['project_root']
        assert facade.rules_dir == mock_dependencies['rules_dir']

    def test_facade_initialization_default_rules_dir(self, mock_dependencies):
        """Test facade initializes with default rules directory"""
        # Remove rules_dir from dependencies
        mock_dependencies.pop('rules_dir')
        facade = RuleOrchestrationFacade(**mock_dependencies)
        
        expected_rules_dir = mock_dependencies['project_root'] / ".cursor" / "rules"
        assert facade.rules_dir == expected_rules_dir

    def test_action_handlers_mapping(self, facade):
        """Test that all expected action handlers are mapped"""
        expected_actions = [
            # Core actions
            "list", "backup", "restore", "clean", "info",
            
            # Enhanced actions
            "load_core", "parse_rule", "analyze_hierarchy", "get_dependencies", "enhanced_info",
            
            # Composition actions
            "compose_nested_rules", "resolve_rule_inheritance", "validate_rule_hierarchy",
            "build_hierarchy", "load_nested",
            
            # Cache actions
            "cache_status",
            
            # Client integration actions
            "register_client", "authenticate_client", "sync_client", "client_diff",
            "resolve_conflicts", "client_status", "client_analytics"
        ]
        
        for action in expected_actions:
            assert action in facade.action_handlers
            assert callable(facade.action_handlers[action])

    def test_execute_action_success(self, facade):
        """Test successful action execution"""
        # Mock the list handler
        facade._handle_list = Mock(return_value={"success": True, "rules": ["rule1", "rule2"]})
        
        result = facade.execute_action("list", target="test_target", content="test_content")
        
        assert result["success"] is True
        assert "rules" in result
        facade._handle_list.assert_called_once_with("test_target", "test_content")

    def test_execute_action_unknown_action(self, facade):
        """Test execution with unknown action"""
        result = facade.execute_action("unknown_action")
        
        assert result["success"] is False
        assert "Unknown action" in result["error"]
        assert "available_actions" in result
        assert isinstance(result["available_actions"], list)

    def test_execute_action_exception_handling(self, facade):
        """Test action execution exception handling"""
        # Mock handler that raises exception
        facade._handle_list = Mock(side_effect=Exception("Test error"))
        
        result = facade.execute_action("list", target="test", content="test")
        
        assert result["success"] is False
        assert "Action execution failed" in result["error"]
        assert "Test error" in result["error"]
        assert result["action"] == "list"
        assert result["target"] == "test"

    def test_get_enhanced_rule_info(self, facade):
        """Test get enhanced rule info delegation"""
        expected_info = {"version": "1.0", "rules_count": 5}
        facade.rule_orchestration_use_case.get_enhanced_rule_info.return_value = expected_info
        
        result = facade.get_enhanced_rule_info()
        
        assert result == expected_info
        facade.rule_orchestration_use_case.get_enhanced_rule_info.assert_called_once()

    def test_compose_nested_rules(self, facade):
        """Test compose nested rules delegation"""
        rule_path = "test/rule/path"
        expected_result = {"success": True, "composed_rules": {}}
        facade.rule_orchestration_use_case.compose_nested_rules.return_value = expected_result
        
        result = facade.compose_nested_rules(rule_path)
        
        assert result == expected_result
        facade.rule_orchestration_use_case.compose_nested_rules.assert_called_once_with(rule_path)

    def test_register_client(self, facade):
        """Test register client delegation"""
        client_config = {"id": "client1", "type": "test"}
        expected_result = {"success": True, "client_id": "client1"}
        facade.rule_orchestration_use_case.register_client.return_value = expected_result
        
        result = facade.register_client(client_config)
        
        assert result == expected_result
        facade.rule_orchestration_use_case.register_client.assert_called_once_with(client_config)

    def test_sync_with_client(self, facade):
        """Test sync with client delegation"""
        client_id = "client1"
        operation = "pull"
        client_rules = {"rule1": "content"}
        expected_result = {"success": True, "synced": True}
        facade.rule_orchestration_use_case.sync_with_client.return_value = expected_result
        
        result = facade.sync_with_client(client_id, operation, client_rules)
        
        assert result == expected_result
        facade.rule_orchestration_use_case.sync_with_client.assert_called_once_with(
            client_id, operation, client_rules
        )

    def test_sync_with_client_no_rules(self, facade):
        """Test sync with client without client rules"""
        client_id = "client1"
        operation = "push"
        expected_result = {"success": True, "synced": True}
        facade.rule_orchestration_use_case.sync_with_client.return_value = expected_result
        
        result = facade.sync_with_client(client_id, operation)
        
        assert result == expected_result
        facade.rule_orchestration_use_case.sync_with_client.assert_called_once_with(
            client_id, operation, None
        )

    def test_handle_list(self, facade):
        """Test list action handler"""
        target = "test_target"
        expected_result = {"success": True, "rules": []}
        facade.rule_orchestration_use_case.list_rules.return_value = expected_result
        
        result = facade._handle_list(target, "")
        
        assert result == expected_result
        facade.rule_orchestration_use_case.list_rules.assert_called_once_with(target)

    def test_handle_backup(self, facade):
        """Test backup action handler"""
        target = "backup_target"
        expected_result = {"success": True, "backup_path": "/path/to/backup"}
        facade.rule_orchestration_use_case.backup_rules.return_value = expected_result
        
        result = facade._handle_backup(target, "")
        
        assert result == expected_result
        facade.rule_orchestration_use_case.backup_rules.assert_called_once_with(target)

    def test_handle_restore(self, facade):
        """Test restore action handler"""
        target = "restore_target"
        expected_result = {"success": True, "restored": True}
        facade.rule_orchestration_use_case.restore_rules.return_value = expected_result
        
        result = facade._handle_restore(target, "")
        
        assert result == expected_result
        facade.rule_orchestration_use_case.restore_rules.assert_called_once_with(target)

    def test_user_id_parameter_handling(self, facade):
        """Test that user_id parameter is handled correctly"""
        # Mock handler to capture user_id usage
        facade._handle_list = Mock(return_value={"success": True})
        
        # Execute action with user_id
        result = facade.execute_action("list", user_id="test-user")
        
        # Verify action was executed (user_id is for audit/auth, not passed to handlers)
        assert result["success"] is True
        facade._handle_list.assert_called_once_with("", "")

    def test_interface_compliance(self):
        """Test that RuleOrchestrationFacade implements IRuleOrchestrationFacade"""
        assert issubclass(RuleOrchestrationFacade, IRuleOrchestrationFacade)
        
        # Check that all interface methods are implemented
        interface_methods = [method for method in dir(IRuleOrchestrationFacade) 
                           if not method.startswith('_') and callable(getattr(IRuleOrchestrationFacade, method))]
        
        for method_name in interface_methods:
            assert hasattr(RuleOrchestrationFacade, method_name)
            assert callable(getattr(RuleOrchestrationFacade, method_name))

    def test_facade_dependencies_type_validation(self):
        """Test that facade validates dependency types"""
        from pathlib import Path
        
        # Test with valid types
        dependencies = {
            'rule_orchestration_use_case': Mock(),
            'rule_composition_service': Mock(),
            'rule_parser_service': Mock(),
            'project_root': Path('/test'),
            'rules_dir': Path('/test/rules')
        }
        
        # Should not raise any exceptions
        facade = RuleOrchestrationFacade(**dependencies)
        assert facade is not None

    def test_action_execution_with_empty_parameters(self, facade):
        """Test action execution with empty target and content"""
        facade._handle_info = Mock(return_value={"success": True, "info": "test"})
        
        result = facade.execute_action("info", "", "")
        
        assert result["success"] is True
        facade._handle_info.assert_called_once_with("", "")

    def test_action_execution_parameter_passing(self, facade):
        """Test that target and content parameters are passed correctly"""
        test_target = "specific_target"
        test_content = "specific_content"
        facade._handle_parse_rule = Mock(return_value={"success": True})
        
        result = facade.execute_action("parse_rule", test_target, test_content)
        
        assert result["success"] is True
        facade._handle_parse_rule.assert_called_once_with(test_target, test_content)

    def test_all_action_handlers_exist(self, facade):
        """Test that all mapped actions have corresponding handler methods"""
        for action, handler in facade.action_handlers.items():
            assert hasattr(facade, handler.__name__)
            assert callable(getattr(facade, handler.__name__))

    @patch('fastmcp.task_management.application.facades.rule_orchestration_facade.logger')
    def test_logging_not_explicitly_used(self, mock_logger, facade):
        """Test facade functionality (logger is imported but not actively used in current implementation)"""
        # Execute an action to ensure facade works without explicit logging
        facade._handle_list = Mock(return_value={"success": True})
        
        result = facade.execute_action("list")
        
        assert result["success"] is True
        # Logger is available but not required to be called in current implementation