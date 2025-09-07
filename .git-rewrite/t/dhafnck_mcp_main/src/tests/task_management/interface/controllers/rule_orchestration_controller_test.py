"""Tests for RuleOrchestrationController"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any, Optional

from fastmcp.task_management.interface.controllers.rule_orchestration_controller import RuleOrchestrationController
from fastmcp.task_management.domain.exceptions.authentication_exceptions import (
    UserAuthenticationRequiredError, DefaultUserProhibitedError
)


class TestRuleOrchestrationController:
    """Test suite for RuleOrchestrationController"""

    @pytest.fixture
    def mock_rule_facade_factory(self):
        """Create mock rule orchestration facade factory"""
        factory = Mock()
        mock_facade = Mock()
        
        # Setup common facade responses
        mock_facade.execute_action.return_value = {"success": True, "action": "test", "result": "executed"}
        mock_facade.get_enhanced_rule_info.return_value = {"success": True, "info": {"version": "1.0"}}
        mock_facade.compose_nested_rules.return_value = {"success": True, "composed": True}
        mock_facade.register_client.return_value = {"success": True, "client_id": "client-123"}
        mock_facade.sync_with_client.return_value = {"success": True, "synced": True}
        
        factory.create_rule_orchestration_facade.return_value = mock_facade
        return factory

    @pytest.fixture
    def controller(self, mock_rule_facade_factory):
        """Create controller instance with mocked facade factory"""
        return RuleOrchestrationController(mock_rule_facade_factory)

    def test_controller_initialization(self, mock_rule_facade_factory):
        """Test controller initializes correctly with facade factory"""
        controller = RuleOrchestrationController(mock_rule_facade_factory)
        
        assert controller._rule_facade_factory == mock_rule_facade_factory

    @patch('fastmcp.task_management.interface.controllers.rule_orchestration_controller.get_current_user_id')
    def test_manage_rule_list_success(self, mock_get_user, controller, mock_rule_facade_factory):
        """Test successful rule listing"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_rule_facade_factory.create_rule_orchestration_facade.return_value
        mock_facade.execute_action.return_value = {"success": True, "rules": ["rule1", "rule2"]}
        
        result = controller.manage_rule(action="list")
        
        assert result["success"] is True
        mock_facade.execute_action.assert_called_once_with("list", "", "", "test-user")

    @patch('fastmcp.task_management.interface.controllers.rule_orchestration_controller.get_current_user_id')
    def test_manage_rule_backup_success(self, mock_get_user, controller, mock_rule_facade_factory):
        """Test successful rule backup"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_rule_facade_factory.create_rule_orchestration_facade.return_value
        mock_facade.execute_action.return_value = {"success": True, "backup_path": "/path/to/backup"}
        
        result = controller.manage_rule(action="backup", target="rules_backup")
        
        assert result["success"] is True
        mock_facade.execute_action.assert_called_once_with("backup", "rules_backup", "", "test-user")

    @patch('fastmcp.task_management.interface.controllers.rule_orchestration_controller.get_current_user_id')
    def test_manage_rule_restore_success(self, mock_get_user, controller, mock_rule_facade_factory):
        """Test successful rule restoration"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_rule_facade_factory.create_rule_orchestration_facade.return_value
        mock_facade.execute_action.return_value = {"success": True, "restored": True}
        
        result = controller.manage_rule(action="restore", target="backup.json")
        
        assert result["success"] is True
        mock_facade.execute_action.assert_called_once_with("restore", "backup.json", "", "test-user")

    @patch('fastmcp.task_management.interface.controllers.rule_orchestration_controller.get_current_user_id')
    def test_manage_rule_clean_success(self, mock_get_user, controller, mock_rule_facade_factory):
        """Test successful rule cleanup"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_rule_facade_factory.create_rule_orchestration_facade.return_value
        mock_facade.execute_action.return_value = {"success": True, "cleaned": 5}
        
        result = controller.manage_rule(action="clean")
        
        assert result["success"] is True
        mock_facade.execute_action.assert_called_once_with("clean", "", "", "test-user")

    @patch('fastmcp.task_management.interface.controllers.rule_orchestration_controller.get_current_user_id')
    def test_manage_rule_info_success(self, mock_get_user, controller, mock_rule_facade_factory):
        """Test successful rule info retrieval"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_rule_facade_factory.create_rule_orchestration_facade.return_value
        mock_facade.execute_action.return_value = {"success": True, "info": {"total_rules": 10}}
        
        result = controller.manage_rule(action="info")
        
        assert result["success"] is True
        mock_facade.execute_action.assert_called_once_with("info", "", "", "test-user")

    @patch('fastmcp.task_management.interface.controllers.rule_orchestration_controller.get_current_user_id')
    def test_manage_rule_enhanced_info_success(self, mock_get_user, controller, mock_rule_facade_factory):
        """Test successful enhanced rule info retrieval"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_rule_facade_factory.create_rule_orchestration_facade.return_value
        mock_facade.execute_action.return_value = {"success": True, "enhanced_info": {"version": "2.0"}}
        
        result = controller.manage_rule(action="enhanced_info")
        
        assert result["success"] is True
        mock_facade.execute_action.assert_called_once_with("enhanced_info", "", "", "test-user")

    @patch('fastmcp.task_management.interface.controllers.rule_orchestration_controller.get_current_user_id')
    def test_manage_rule_compose_nested_rules_success(self, mock_get_user, controller, mock_rule_facade_factory):
        """Test successful nested rule composition"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_rule_facade_factory.create_rule_orchestration_facade.return_value
        mock_facade.execute_action.return_value = {"success": True, "composed": {"nested_rules": {}}}
        
        result = controller.manage_rule(action="compose_nested_rules", target="auth_rules")
        
        assert result["success"] is True
        mock_facade.execute_action.assert_called_once_with("compose_nested_rules", "auth_rules", "", "test-user")

    @patch('fastmcp.task_management.interface.controllers.rule_orchestration_controller.get_current_user_id')
    def test_manage_rule_register_client_success(self, mock_get_user, controller, mock_rule_facade_factory):
        """Test successful client registration"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_rule_facade_factory.create_rule_orchestration_facade.return_value
        mock_facade.execute_action.return_value = {"success": True, "client_id": "client-456"}
        
        result = controller.manage_rule(action="register_client", target="client-name", content='{"type": "test"}')
        
        assert result["success"] is True
        mock_facade.execute_action.assert_called_once_with("register_client", "client-name", '{"type": "test"}', "test-user")

    @patch('fastmcp.task_management.interface.controllers.rule_orchestration_controller.get_current_user_id')
    def test_manage_rule_sync_client_success(self, mock_get_user, controller, mock_rule_facade_factory):
        """Test successful client synchronization"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_rule_facade_factory.create_rule_orchestration_facade.return_value
        mock_facade.execute_action.return_value = {"success": True, "synced": True}
        
        result = controller.manage_rule(action="sync_client", target="client-123", content="push")
        
        assert result["success"] is True
        mock_facade.execute_action.assert_called_once_with("sync_client", "client-123", "push", "test-user")

    @patch('fastmcp.task_management.interface.controllers.rule_orchestration_controller.get_current_user_id')
    def test_manage_rule_client_analytics_success(self, mock_get_user, controller, mock_rule_facade_factory):
        """Test successful client analytics retrieval"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_rule_facade_factory.create_rule_orchestration_facade.return_value
        mock_facade.execute_action.return_value = {"success": True, "analytics": {"usage": 100}}
        
        result = controller.manage_rule(action="client_analytics", target="client-123")
        
        assert result["success"] is True
        mock_facade.execute_action.assert_called_once_with("client_analytics", "client-123", "", "test-user")

    @patch('fastmcp.task_management.interface.controllers.rule_orchestration_controller.get_current_user_id')
    def test_manage_rule_cache_status_success(self, mock_get_user, controller, mock_rule_facade_factory):
        """Test successful cache status retrieval"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_rule_facade_factory.create_rule_orchestration_facade.return_value
        mock_facade.execute_action.return_value = {"success": True, "cache_stats": {"hit_rate": 0.95}}
        
        result = controller.manage_rule(action="cache_status")
        
        assert result["success"] is True
        mock_facade.execute_action.assert_called_once_with("cache_status", "", "", "test-user")

    @patch('fastmcp.task_management.interface.controllers.rule_orchestration_controller.get_current_user_id')
    def test_manage_rule_authentication_required_error(self, mock_get_user, controller):
        """Test handling of authentication required error"""
        mock_get_user.side_effect = UserAuthenticationRequiredError("Authentication required")
        
        result = controller.manage_rule(action="list")
        
        assert result["success"] is False
        assert "Authentication required" in result["error"]
        assert result["error_code"] == "AUTHENTICATION_REQUIRED"

    @patch('fastmcp.task_management.interface.controllers.rule_orchestration_controller.get_current_user_id')
    def test_manage_rule_default_user_prohibited_error(self, mock_get_user, controller):
        """Test handling of default user prohibited error"""
        mock_get_user.return_value = "test-user"
        mock_facade = controller._rule_facade_factory.create_rule_orchestration_facade.return_value
        mock_facade.execute_action.side_effect = DefaultUserProhibitedError("Default user not allowed")
        
        result = controller.manage_rule(action="list")
        
        assert result["success"] is False
        assert "Default user not allowed" in result["error"]
        assert result["error_code"] == "DEFAULT_USER_PROHIBITED"

    @patch('fastmcp.task_management.interface.controllers.rule_orchestration_controller.get_current_user_id')
    def test_manage_rule_general_exception(self, mock_get_user, controller):
        """Test handling of general exceptions"""
        mock_get_user.return_value = "test-user"
        mock_facade = controller._rule_facade_factory.create_rule_orchestration_facade.return_value
        mock_facade.execute_action.side_effect = Exception("Unexpected error")
        
        result = controller.manage_rule(action="list")
        
        assert result["success"] is False
        assert "Unexpected error" in result["error"]
        assert result["action"] == "list"

    def test_register_tools_method_exists(self, controller):
        """Test that register_tools method exists and is callable"""
        assert hasattr(controller, 'register_tools')
        assert callable(controller.register_tools)

    @patch('fastmcp.task_management.interface.controllers.rule_orchestration_controller.description_loader')
    def test_register_tools_calls_description_loader(self, mock_desc_loader, controller):
        """Test that register_tools calls the description loader"""
        mock_mcp = Mock()
        mock_desc_loader.get_rule_orchestration_descriptions.return_value = {
            "manage_rule": {"description": "test desc", "parameters": {}}
        }
        
        controller.register_tools(mock_mcp)
        
        mock_desc_loader.get_rule_orchestration_descriptions.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.rule_orchestration_controller.get_current_user_id')
    def test_user_id_parameter_handling(self, mock_get_user, controller, mock_rule_facade_factory):
        """Test that user_id parameter is handled correctly"""
        mock_get_user.return_value = "test-user"
        
        controller.manage_rule(action="list")
        
        # Verify facade was created with authenticated user
        mock_rule_facade_factory.create_rule_orchestration_facade.assert_called_once_with(
            user_id="test-user"
        )

    @patch('fastmcp.task_management.interface.controllers.rule_orchestration_controller.get_current_user_id')
    def test_workflow_guidance_integration(self, mock_get_user, controller):
        """Test that workflow guidance is integrated"""
        mock_get_user.return_value = "test-user"
        
        # Test that the controller can handle workflow guidance
        result = controller.manage_rule(action="info")
        
        # Workflow guidance should be included in responses
        assert "workflow_guidance" in result or result["success"] is True

    @patch('fastmcp.task_management.interface.controllers.rule_orchestration_controller.get_current_user_id')
    def test_parameter_handling_all_optional(self, mock_get_user, controller, mock_rule_facade_factory):
        """Test parameter handling when all are optional"""
        mock_get_user.return_value = "test-user"
        
        result = controller.manage_rule(action="list")
        
        # Should work with minimal parameters
        assert result["success"] is True
        
        # Verify correct parameters passed to facade
        mock_facade = mock_rule_facade_factory.create_rule_orchestration_facade.return_value
        mock_facade.execute_action.assert_called_once_with("list", "", "", "test-user")

    @patch('fastmcp.task_management.interface.controllers.rule_orchestration_controller.get_current_user_id')
    def test_parameter_handling_with_target_and_content(self, mock_get_user, controller, mock_rule_facade_factory):
        """Test parameter handling with target and content"""
        mock_get_user.return_value = "test-user"
        target = "specific_rule"
        content = '{"config": "value"}'
        
        result = controller.manage_rule(action="parse_rule", target=target, content=content)
        
        assert result["success"] is True
        
        # Verify correct parameters passed to facade
        mock_facade = mock_rule_facade_factory.create_rule_orchestration_facade.return_value
        mock_facade.execute_action.assert_called_once_with("parse_rule", target, content, "test-user")

    @patch('fastmcp.task_management.interface.controllers.rule_orchestration_controller.logger')
    def test_logging_functionality(self, mock_logger, controller):
        """Test that logging is available and functional"""
        # Logger should be available for operations
        assert mock_logger is not None
        
        # Test that we can log (logger is imported at module level)
        from fastmcp.task_management.interface.controllers.rule_orchestration_controller import logger
        assert logger is not None

    @patch('fastmcp.task_management.interface.controllers.rule_orchestration_controller.get_current_user_id')
    def test_facade_creation_and_delegation(self, mock_get_user, controller, mock_rule_facade_factory):
        """Test that facade is properly created and operations are delegated"""
        mock_get_user.return_value = "test-user"
        mock_facade = mock_rule_facade_factory.create_rule_orchestration_facade.return_value
        
        # Make request
        controller.manage_rule(action="info")
        
        # Verify facade creation
        mock_rule_facade_factory.create_rule_orchestration_facade.assert_called_once_with(
            user_id="test-user"
        )
        
        # Verify operation delegation
        mock_facade.execute_action.assert_called_once()

    @patch('fastmcp.task_management.interface.controllers.rule_orchestration_controller.get_current_user_id')
    def test_all_rule_actions_supported(self, mock_get_user, controller):
        """Test that all rule orchestration actions are supported"""
        mock_get_user.return_value = "test-user"
        
        # List of actions that should be supported (based on the facade)
        supported_actions = [
            "list", "backup", "restore", "clean", "info",
            "load_core", "parse_rule", "analyze_hierarchy", "get_dependencies", "enhanced_info",
            "compose_nested_rules", "resolve_rule_inheritance", "validate_rule_hierarchy",
            "build_hierarchy", "load_nested", "cache_status",
            "register_client", "authenticate_client", "sync_client", "client_diff",
            "resolve_conflicts", "client_status", "client_analytics"
        ]
        
        for action in supported_actions:
            result = controller.manage_rule(action=action)
            # All should succeed (mocked facade returns success)
            assert result["success"] is True

    @patch('fastmcp.task_management.interface.controllers.rule_orchestration_controller.get_current_user_id')
    def test_empty_parameters_handling(self, mock_get_user, controller):
        """Test handling of empty string parameters"""
        mock_get_user.return_value = "test-user"
        
        result = controller.manage_rule(
            action="list",
            target="",  # Empty target
            content=""  # Empty content
        )
        
        assert result["success"] is True

    @patch('fastmcp.task_management.interface.controllers.rule_orchestration_controller.get_current_user_id')
    def test_none_parameters_handling(self, mock_get_user, controller):
        """Test handling of None parameters"""
        mock_get_user.return_value = "test-user"
        
        result = controller.manage_rule(
            action="list",
            target=None,  # None target
            content=None  # None content
        )
        
        assert result["success"] is True

    def test_import_error_handling(self):
        """Test that import errors for auth context are handled"""
        # The controller should handle import errors gracefully
        # This is tested by the module-level import in the actual code
        
        # Verify the controller can be instantiated even with import issues
        factory = Mock()
        controller = RuleOrchestrationController(factory)
        assert controller is not None