#!/usr/bin/env python3
"""
Tests for Role Enforcer System

Tests the role-based tool permission enforcement including:
- Agent role validation and tool restrictions
- Dynamic tool permission checking
- Path restrictions for write operations
- Violation tracking and logging
- Role configuration management
- Integration with agent state management

Part of subtask: a160a5a8-e058-4594-8521-1a14121d2b6c
"""

import pytest
import json
import yaml
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
from datetime import datetime

import sys

# Add hooks utils to path for testing
hooks_utils_path = Path(__file__).parent.parent.parent.parent.parent / '.claude' / 'hooks' / 'utils'
sys.path.insert(0, str(hooks_utils_path.absolute()))

try:
    from role_enforcer import (
        RoleEnforcer,
        get_role_enforcer,
        check_tool_permission
    )
except ImportError:
    # Skip these tests if the module is not available
    pytest.skip("role_enforcer module not available", allow_module_level=True)


class TestRoleEnforcer:
    """Test RoleEnforcer class functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directory for test config files
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "config"
        self.config_dir.mkdir()
        self.role_config_file = self.config_dir / "__hint_message__active_role.yaml"

        # Sample role configuration
        self.sample_config = {
            "enabled": True,
            "default_role": {
                "name": "uninitialized",
                "allowed_tools": ["mcp__agenthub_http__call_agent", "Read", "Grep", "Glob"],
                "blocked_tools": "*",
                "warnings": {
                    "write_attempt": "[NO ROLE] Must call mcp__agenthub_http__call_agent first!",
                    "modification_attempt": "[NO ROLE] Initialize your role before making changes!"
                }
            },
            "roles": {
                "master-orchestrator-agent": {
                    "name": "master-orchestrator-agent",
                    "description": "Supreme conductor of complex workflows",
                    "allowed_tools": ["Task", "Read", "mcp__agenthub_http__manage_task", "TodoWrite"],
                    "blocked_tools": ["Write", "Edit", "MultiEdit", "Bash"],
                    "warnings": {
                        "write_attempt": "[MASTER ORCHESTRATOR] Delegate file editing to coding-agent",
                        "edit_attempt": "[MASTER ORCHESTRATOR] Use Task tool to delegate editing work",
                        "execution_attempt": "[MASTER ORCHESTRATOR] Delegate system commands to appropriate agents"
                    }
                },
                "coding-agent": {
                    "name": "coding-agent",
                    "description": "Specialized code implementation agent",
                    "allowed_tools": ["Read", "Write", "Edit", "MultiEdit", "Bash", "Grep", "Glob"],
                    "blocked_tools": ["Task"],
                    "path_restrictions": {
                        "write_paths": ["*.py", "*.js", "*.ts", "*.json", "*.yaml", "*.yml"]
                    },
                    "warnings": {
                        "delegation_attempt": "[CODING AGENT] Cannot delegate - you are a specialist, not coordinator",
                        "wrong_path": "[CODING AGENT] Cannot write to this file type or location"
                    }
                },
                "documentation-agent": {
                    "name": "documentation-agent",
                    "description": "Documentation and content creation specialist",
                    "allowed_tools": ["Read", "Write", "Edit", "Grep", "WebFetch"],
                    "blocked_tools": ["Bash", "Task"],
                    "path_restrictions": {
                        "write_paths": ["*.md", "*.txt", "ai_docs/*"]
                    }
                }
            },
            "enforcement": {
                "log_violations": True,
                "log_all": False,
                "log_file": "logs/role_violations.json"
            }
        }

        # Clear any global enforcer instance
        import role_enforcer
        role_enforcer._enforcer_instance = None

    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up temporary files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Clear global enforcer instance
        import role_enforcer
        role_enforcer._enforcer_instance = None

    def create_config_file(self, config_data=None):
        """Helper to create role configuration file."""
        if config_data is None:
            config_data = self.sample_config

        with open(self.role_config_file, 'w') as f:
            yaml.dump(config_data, f)

    def test_init_with_config(self):
        """Test RoleEnforcer initialization with valid config."""
        self.create_config_file()

        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = self.sample_config
            enforcer = RoleEnforcer(session_id="test-session")

            assert enforcer.session_id == "test-session"
            assert enforcer.role_config == self.sample_config
            assert enforcer.violations == []

    def test_init_without_config(self):
        """Test RoleEnforcer initialization without config file."""
        # Don't create config file
        enforcer = RoleEnforcer()

        assert enforcer.role_config == {"enabled": False}

    def test_load_config_success(self):
        """Test successful config loading."""
        self.create_config_file()
        enforcer = RoleEnforcer()

        # Patch the config directory
        with patch.object(enforcer, 'config_dir', self.config_dir):
            enforcer.role_config_file = self.role_config_file
            config = enforcer._load_config(self.role_config_file)

            assert config == self.sample_config

    def test_load_config_file_not_found(self):
        """Test config loading when file doesn't exist."""
        enforcer = RoleEnforcer()
        config = enforcer._load_config(Path("/nonexistent/file.yaml"))

        assert config == {"enabled": False}

    def test_load_config_invalid_yaml(self):
        """Test config loading with invalid YAML."""
        # Create invalid YAML file
        with open(self.role_config_file, 'w') as f:
            f.write("invalid: yaml: content: [")

        enforcer = RoleEnforcer()
        config = enforcer._load_config(self.role_config_file)

        assert config == {"enabled": False}

    @patch('role_enforcer.get_current_agent')
    def test_get_current_role_from_agent_state(self, mock_get_current_agent):
        """Test getting current role from agent state manager."""
        mock_get_current_agent.return_value = "coding-agent"

        enforcer = RoleEnforcer(session_id="test-session")
        role = enforcer._get_current_role()

        assert role == "coding-agent"
        mock_get_current_agent.assert_called_once_with("test-session")

    @patch('role_enforcer.get_current_agent')
    def test_get_current_role_no_agent_state(self, mock_get_current_agent):
        """Test getting current role when no agent state."""
        mock_get_current_agent.return_value = None

        enforcer = RoleEnforcer()
        role = enforcer._get_current_role()

        assert role == "uninitialized"

    @patch('role_enforcer.get_current_agent', None)
    def test_get_current_role_no_state_manager(self):
        """Test getting current role when state manager unavailable."""
        enforcer = RoleEnforcer()
        role = enforcer._get_current_role()

        assert role == "uninitialized"

    def test_get_role_definition_existing(self):
        """Test getting role definition for existing role."""
        self.create_config_file()

        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = self.sample_config
            enforcer = RoleEnforcer()

            role_def = enforcer._get_role_definition("coding-agent")

            assert role_def == self.sample_config["roles"]["coding-agent"]

    def test_get_role_definition_nonexistent(self):
        """Test getting role definition for non-existent role."""
        self.create_config_file()

        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = self.sample_config
            enforcer = RoleEnforcer()

            role_def = enforcer._get_role_definition("unknown-agent")

            assert role_def is None

    def test_get_default_role_configured(self):
        """Test getting default role when configured."""
        self.create_config_file()

        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = self.sample_config
            enforcer = RoleEnforcer()

            default_role = enforcer._get_default_role()

            assert default_role == self.sample_config["default_role"]

    def test_get_default_role_fallback(self):
        """Test getting default role fallback."""
        config_without_default = {"enabled": True, "roles": {}}

        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = config_without_default
            enforcer = RoleEnforcer()

            default_role = enforcer._get_default_role()

            assert default_role["name"] == "uninitialized"
            assert "mcp__agenthub_http__call_agent" in default_role["allowed_tools"]
            assert default_role["blocked_tools"] == "*"

    @patch('role_enforcer.get_current_agent')
    def test_check_tool_permission_disabled(self, mock_get_current_agent):
        """Test tool permission check when enforcement disabled."""
        config_disabled = {"enabled": False}

        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = config_disabled
            enforcer = RoleEnforcer()

            allowed, message = enforcer.check_tool_permission("Write", {"file_path": "/test.py"})

            assert allowed is True
            assert message == ""

    @patch('role_enforcer.get_current_agent')
    def test_check_tool_permission_allowed(self, mock_get_current_agent):
        """Test tool permission check for allowed tool."""
        mock_get_current_agent.return_value = "coding-agent"
        self.create_config_file()

        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = self.sample_config
            enforcer = RoleEnforcer()

            allowed, message = enforcer.check_tool_permission("Write", {"file_path": "/test.py"})

            assert allowed is True
            assert message == ""

    @patch('role_enforcer.get_current_agent')
    def test_check_tool_permission_blocked(self, mock_get_current_agent):
        """Test tool permission check for blocked tool."""
        mock_get_current_agent.return_value = "master-orchestrator-agent"
        self.create_config_file()

        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = self.sample_config
            enforcer = RoleEnforcer()

            allowed, message = enforcer.check_tool_permission("Write", {"file_path": "/test.py"})

            assert allowed is False
            assert "[MASTER ORCHESTRATOR]" in message

    @patch('role_enforcer.get_current_agent')
    def test_check_tool_permission_not_in_allowed_list(self, mock_get_current_agent):
        """Test tool permission check for tool not in allowed list."""
        mock_get_current_agent.return_value = "coding-agent"
        self.create_config_file()

        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = self.sample_config
            enforcer = RoleEnforcer()

            allowed, message = enforcer.check_tool_permission("Task", {"prompt": "test"})

            assert allowed is False
            assert "not available" in message.lower()

    @patch('role_enforcer.get_current_agent')
    def test_check_tool_permission_uninitialized_agent(self, mock_get_current_agent):
        """Test tool permission check for uninitialized agent."""
        mock_get_current_agent.return_value = None
        self.create_config_file()

        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = self.sample_config
            enforcer = RoleEnforcer()

            allowed, message = enforcer.check_tool_permission("Write", {"file_path": "/test.py"})

            assert allowed is False
            assert "Must call mcp__agenthub_http__call_agent first" in message

    @patch('role_enforcer.get_current_agent')
    def test_check_path_restrictions_allowed(self, mock_get_current_agent):
        """Test path restrictions for allowed file types."""
        mock_get_current_agent.return_value = "coding-agent"
        self.create_config_file()

        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = self.sample_config
            enforcer = RoleEnforcer()

            allowed, message = enforcer.check_tool_permission("Write", {"file_path": "/project/test.py"})

            assert allowed is True
            assert message == ""

    @patch('role_enforcer.get_current_agent')
    def test_check_path_restrictions_denied(self, mock_get_current_agent):
        """Test path restrictions for denied file types."""
        mock_get_current_agent.return_value = "coding-agent"
        self.create_config_file()

        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = self.sample_config
            enforcer = RoleEnforcer()

            allowed, message = enforcer.check_tool_permission("Write", {"file_path": "/project/test.md"})

            assert allowed is False
            assert "cannot write to" in message.lower()

    @patch('role_enforcer.get_current_agent')
    def test_check_path_restrictions_documentation_agent(self, mock_get_current_agent):
        """Test path restrictions for documentation agent."""
        mock_get_current_agent.return_value = "documentation-agent"
        self.create_config_file()

        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = self.sample_config
            enforcer = RoleEnforcer()

            # Should allow markdown files
            allowed, message = enforcer.check_tool_permission("Write", {"file_path": "ai_docs/test.md"})
            assert allowed is True

            # Should deny Python files
            allowed, message = enforcer.check_tool_permission("Write", {"file_path": "/project/test.py"})
            assert allowed is False

    def test_violation_message_generation(self):
        """Test generation of violation messages."""
        self.create_config_file()

        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = self.sample_config
            enforcer = RoleEnforcer()

            # Test specific warning message
            role_def = self.sample_config["roles"]["master-orchestrator-agent"]
            message = enforcer._get_violation_message("master-orchestrator-agent", "Write", "blocked")

            assert "[MASTER ORCHESTRATOR]" in message

    @patch('role_enforcer.get_current_agent')
    def test_violation_logging_enabled(self, mock_get_current_agent):
        """Test violation logging when enabled."""
        mock_get_current_agent.return_value = "master-orchestrator-agent"
        self.create_config_file()

        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = self.sample_config
            enforcer = RoleEnforcer()

            # Mock file operations for logging
            with patch('builtins.open', mock_open()) as mock_file:
                with patch('json.load', return_value=[]):
                    with patch('json.dump') as mock_dump:
                        with patch('pathlib.Path.exists', return_value=False):
                            with patch('pathlib.Path.mkdir'):
                                allowed, message = enforcer.check_tool_permission("Write", {"file_path": "/test.py"})

                                assert allowed is False
                                assert len(enforcer.violations) == 1
                                assert enforcer.violations[0]["tool"] == "Write"
                                assert enforcer.violations[0]["allowed"] is False

    def test_get_role_info(self):
        """Test getting role information."""
        self.create_config_file()

        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = self.sample_config
            enforcer = RoleEnforcer()

            role_info = enforcer.get_role_info("coding-agent")

            assert role_info["role"] == "coding-agent"
            assert role_info["description"] == "Specialized code implementation agent"
            assert "Write" in role_info["allowed_tools"]
            assert "Task" in role_info["blocked_tools"]

    def test_suggest_delegation(self):
        """Test delegation suggestions."""
        enforcer = RoleEnforcer()

        suggestion = enforcer.suggest_delegation("Write")
        assert "coding-agent" in suggestion

        suggestion = enforcer.suggest_delegation("Task")
        assert "appropriate specialized agent" in suggestion

    def test_role_caching(self):
        """Test role caching mechanism."""
        with patch('role_enforcer.get_current_agent') as mock_get_current_agent:
            mock_get_current_agent.return_value = "coding-agent"

            enforcer = RoleEnforcer()

            # First call should hit the agent state manager
            role1 = enforcer._get_current_role()
            assert role1 == "coding-agent"
            assert mock_get_current_agent.call_count == 1

            # Second call within cache time should use cached value
            role2 = enforcer._get_current_role()
            assert role2 == "coding-agent"
            assert mock_get_current_agent.call_count == 1  # No additional calls

    def test_all_blocked_except_allowed(self):
        """Test configuration where all tools are blocked except explicitly allowed."""
        config_all_blocked = {
            "enabled": True,
            "roles": {
                "restricted-agent": {
                    "name": "restricted-agent",
                    "allowed_tools": ["Read", "Grep"],
                    "blocked_tools": "*"
                }
            }
        }

        with patch('role_enforcer.get_current_agent') as mock_get_current_agent:
            mock_get_current_agent.return_value = "restricted-agent"

            with patch.object(RoleEnforcer, '_load_config') as mock_load:
                mock_load.return_value = config_all_blocked
                enforcer = RoleEnforcer()

                # Allowed tool should work
                allowed, message = enforcer.check_tool_permission("Read", {"file_path": "/test.txt"})
                assert allowed is True

                # Non-allowed tool should be blocked
                allowed, message = enforcer.check_tool_permission("Write", {"file_path": "/test.txt"})
                assert allowed is False


class TestRoleEnforcerGlobalFunctions:
    """Test global convenience functions."""

    def setup_method(self):
        """Set up test fixtures."""
        # Clear global enforcer instance
        import role_enforcer
        role_enforcer._enforcer_instance = None

    def teardown_method(self):
        """Clean up test fixtures."""
        # Clear global enforcer instance
        import role_enforcer
        role_enforcer._enforcer_instance = None

    def test_get_role_enforcer_singleton(self):
        """Test that get_role_enforcer returns singleton instance."""
        enforcer1 = get_role_enforcer("session1")
        enforcer2 = get_role_enforcer("session1")

        assert enforcer1 is enforcer2
        assert enforcer1.session_id == "session1"

    def test_get_role_enforcer_different_sessions(self):
        """Test that different sessions get different enforcer instances."""
        enforcer1 = get_role_enforcer("session1")
        enforcer2 = get_role_enforcer("session2")

        assert enforcer1 is not enforcer2
        assert enforcer1.session_id == "session1"
        assert enforcer2.session_id == "session2"

    @patch('role_enforcer.get_role_enforcer')
    def test_check_tool_permission_convenience(self, mock_get_enforcer):
        """Test convenience function for checking tool permission."""
        mock_enforcer = Mock()
        mock_enforcer.check_tool_permission.return_value = (True, "")
        mock_get_enforcer.return_value = mock_enforcer

        result = check_tool_permission("Read", {"file_path": "/test.txt"}, "test-session")

        assert result == (True, "")
        mock_get_enforcer.assert_called_once_with("test-session")
        mock_enforcer.check_tool_permission.assert_called_once_with("Read", {"file_path": "/test.txt"})


class TestRoleEnforcerIntegration:
    """Test integration scenarios with other components."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        # Sample integrated configuration
        self.integrated_config = {
            "enabled": True,
            "default_role": {
                "name": "uninitialized",
                "allowed_tools": ["mcp__agenthub_http__call_agent"],
                "blocked_tools": "*"
            },
            "roles": {
                "master-orchestrator-agent": {
                    "name": "master-orchestrator-agent",
                    "allowed_tools": ["Task", "Read", "mcp__agenthub_http__manage_task"],
                    "blocked_tools": ["Write", "Edit", "Bash"]
                },
                "coding-agent": {
                    "name": "coding-agent",
                    "allowed_tools": ["Read", "Write", "Edit", "Bash"],
                    "blocked_tools": ["Task"]
                }
            }
        }

        # Clear global enforcer instance
        import role_enforcer
        role_enforcer._enforcer_instance = None

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Clear global enforcer instance
        import role_enforcer
        role_enforcer._enforcer_instance = None

    @patch('role_enforcer.get_current_agent')
    def test_workflow_master_orchestrator_delegation(self, mock_get_current_agent):
        """Test complete workflow: master orchestrator delegating to coding agent."""
        # Start as uninitialized
        mock_get_current_agent.return_value = None

        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = self.integrated_config
            enforcer = RoleEnforcer()

            # 1. Uninitialized agent cannot write files
            allowed, message = enforcer.check_tool_permission("Write", {"file_path": "/test.py"})
            assert allowed is False
            assert "call_agent" in message

            # 2. After initialization as master orchestrator
            mock_get_current_agent.return_value = "master-orchestrator-agent"
            enforcer._current_role = None  # Clear cache

            # Master orchestrator can use Task but not Write
            allowed, message = enforcer.check_tool_permission("Task", {"prompt": "test"})
            assert allowed is True

            allowed, message = enforcer.check_tool_permission("Write", {"file_path": "/test.py"})
            assert allowed is False

            # 3. Coding agent can write but not delegate
            mock_get_current_agent.return_value = "coding-agent"
            enforcer._current_role = None  # Clear cache

            allowed, message = enforcer.check_tool_permission("Write", {"file_path": "/test.py"})
            assert allowed is True

            allowed, message = enforcer.check_tool_permission("Task", {"prompt": "test"})
            assert allowed is False

    @patch('role_enforcer.get_current_agent')
    def test_session_isolation(self, mock_get_current_agent):
        """Test that different sessions maintain separate state."""
        mock_get_current_agent.return_value = "coding-agent"

        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = self.integrated_config

            # Create enforcers for different sessions
            enforcer1 = get_role_enforcer("session1")
            enforcer2 = get_role_enforcer("session2")

            assert enforcer1.session_id == "session1"
            assert enforcer2.session_id == "session2"
            assert enforcer1 is not enforcer2

            # Violations should be tracked separately
            with patch('builtins.open', mock_open()):
                with patch('json.load', return_value=[]):
                    with patch('json.dump'):
                        with patch('pathlib.Path.exists', return_value=False):
                            with patch('pathlib.Path.mkdir'):
                                # Generate violation in session1
                                mock_get_current_agent.return_value = "master-orchestrator-agent"
                                enforcer1._current_role = None
                                enforcer1.check_tool_permission("Write", {"file_path": "/test.py"})

                                # Session1 should have violation, session2 should not
                                assert len(enforcer1.violations) == 1
                                assert len(enforcer2.violations) == 0

    @patch('role_enforcer.get_current_agent')
    def test_error_recovery(self, mock_get_current_agent):
        """Test error recovery in various failure scenarios."""
        mock_get_current_agent.side_effect = Exception("Agent state error")

        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = self.integrated_config
            enforcer = RoleEnforcer()

            # Should gracefully handle agent state errors and fall back to uninitialized
            allowed, message = enforcer.check_tool_permission("Write", {"file_path": "/test.py"})
            assert allowed is False  # Should deny due to uninitialized state

    def test_config_hot_reload_simulation(self):
        """Test behavior when configuration changes during runtime."""
        # Start with permissive config
        permissive_config = {
            "enabled": False
        }

        # Switch to restrictive config
        restrictive_config = {
            "enabled": True,
            "default_role": {
                "allowed_tools": ["Read"],
                "blocked_tools": "*"
            }
        }

        with patch('role_enforcer.get_current_agent') as mock_get_current_agent:
            mock_get_current_agent.return_value = None

            # Create enforcer with permissive config
            with patch.object(RoleEnforcer, '_load_config') as mock_load:
                mock_load.return_value = permissive_config
                enforcer = RoleEnforcer()

                # Should allow everything when disabled
                allowed, message = enforcer.check_tool_permission("Write", {"file_path": "/test.py"})
                assert allowed is True

                # Simulate config reload by changing the loaded config
                enforcer.role_config = restrictive_config

                # Should now enforce restrictions
                allowed, message = enforcer.check_tool_permission("Write", {"file_path": "/test.py"})
                assert allowed is False


class TestRoleEnforcerPerformance:
    """Test performance characteristics of role enforcer."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create large role configuration for performance testing
        self.large_config = {
            "enabled": True,
            "roles": {}
        }

        # Generate many roles for stress testing
        for i in range(100):
            self.large_config["roles"][f"agent-{i}"] = {
                "name": f"agent-{i}",
                "allowed_tools": [f"Tool{j}" for j in range(10)],
                "blocked_tools": [f"BlockedTool{j}" for j in range(10)]
            }

        # Clear global enforcer instance
        import role_enforcer
        role_enforcer._enforcer_instance = None

    def teardown_method(self):
        """Clean up test fixtures."""
        import role_enforcer
        role_enforcer._enforcer_instance = None

    @patch('role_enforcer.get_current_agent')
    def test_permission_check_performance(self, mock_get_current_agent):
        """Test permission check performance with large configuration."""
        mock_get_current_agent.return_value = "agent-50"

        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = self.large_config
            enforcer = RoleEnforcer()

            import time

            # Test many permission checks
            start_time = time.time()
            for i in range(1000):
                enforcer.check_tool_permission(f"Tool{i % 10}", {"file_path": f"/test{i}.py"})
            end_time = time.time()

            # Should complete within reasonable time (< 1 second for 1000 checks)
            assert end_time - start_time < 1.0

    @patch('role_enforcer.get_current_agent')
    def test_role_cache_effectiveness(self, mock_get_current_agent):
        """Test that role caching improves performance."""
        mock_get_current_agent.return_value = "agent-0"

        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = self.large_config
            enforcer = RoleEnforcer()

            # First batch of checks - should cache role
            for i in range(100):
                enforcer.check_tool_permission("Tool0", {"file_path": f"/test{i}.py"})

            # Should have called get_current_agent only once due to caching
            assert mock_get_current_agent.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__])