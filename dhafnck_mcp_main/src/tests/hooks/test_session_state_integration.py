#!/usr/bin/env python3
"""
Tests for Session and State Management Integration

Tests the integration between session tracking and state management including:
- Session persistence across agent role changes
- State recovery after session timeouts
- Cross-component data consistency
- Session cleanup and state preservation
- Performance under concurrent access

Part of subtask: a160a5a8-e058-4594-8521-1a14121d2b6c
"""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime, timedelta
from freezegun import freeze_time

import sys

# Add hooks utils to path for testing
hooks_utils_path = Path(__file__).parent.parent.parent.parent.parent / '.claude' / 'hooks' / 'utils'
sys.path.insert(0, str(hooks_utils_path.absolute()))

try:
    # Import session tracker
    import session_tracker
    from session_tracker import (
        get_current_session,
        add_modified_file,
        is_file_in_session,
        clear_expired_sessions
    )

    # Import role enforcer
    from role_enforcer import (
        RoleEnforcer,
        get_role_enforcer,
        check_tool_permission
    )

    # Import agent state manager if available
    try:
        from agent_state_manager import (
            get_current_agent,
            set_current_agent,
            agent_state_manager
        )
        AGENT_STATE_AVAILABLE = True
    except ImportError:
        AGENT_STATE_AVAILABLE = False

except ImportError:
    # Skip these tests if the modules are not available
    pytest.skip("session/state management modules not available", allow_module_level=True)


class TestSessionStateIntegration:
    """Test integration between session tracking and state management."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directories for test data
        self.temp_dir = tempfile.mkdtemp()
        self.session_dir = Path(self.temp_dir) / "sessions"
        self.state_dir = Path(self.temp_dir) / "state"
        self.session_dir.mkdir()
        self.state_dir.mkdir()

        # Test session and state files
        self.session_file = self.session_dir / 'documentation_session.json'
        self.state_file = self.state_dir / 'agent_state.json'

        # Sample role configuration for testing
        self.role_config = {
            "enabled": True,
            "default_role": {
                "name": "uninitialized",
                "allowed_tools": ["mcp__dhafnck_mcp_http__call_agent", "Read"],
                "blocked_tools": "*"
            },
            "roles": {
                "master-orchestrator-agent": {
                    "name": "master-orchestrator-agent",
                    "allowed_tools": ["Task", "Read", "mcp__dhafnck_mcp_http__manage_task"],
                    "blocked_tools": ["Write", "Edit", "Bash"]
                },
                "coding-agent": {
                    "name": "coding-agent",
                    "allowed_tools": ["Read", "Write", "Edit", "Bash"],
                    "blocked_tools": ["Task"]
                }
            }
        }

        # Clear any global state
        import role_enforcer
        role_enforcer._enforcer_instance = None

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Clear global state
        import role_enforcer
        role_enforcer._enforcer_instance = None

    @patch('session_tracker.get_ai_data_path')
    @patch('role_enforcer.get_current_agent')
    def test_session_tracks_role_changes(self, mock_get_current_agent, mock_get_ai_data_path):
        """Test that session tracking works across role changes."""
        mock_get_ai_data_path.return_value = self.session_dir

        with freeze_time("2024-01-01 12:00:00") as frozen_time:
            # Start as uninitialized agent
            mock_get_current_agent.return_value = None

            with patch.object(RoleEnforcer, '_load_config') as mock_load:
                mock_load.return_value = self.role_config

                # Create session and add files
                session = get_current_session()
                add_modified_file(Path("/test/file1.txt"))

                # Verify session state
                assert is_file_in_session(Path("/test/file1.txt"))

                # Change to master orchestrator
                mock_get_current_agent.return_value = "master-orchestrator-agent"

                # Session should persist across role changes
                session2 = get_current_session()
                assert session2['session_id'] == session['session_id']
                assert is_file_in_session(Path("/test/file1.txt"))

                # Add more files as master orchestrator
                add_modified_file(Path("/test/file2.txt"))

                # Change to coding agent
                mock_get_current_agent.return_value = "coding-agent"

                # Session should still persist
                session3 = get_current_session()
                assert session3['session_id'] == session['session_id']
                assert is_file_in_session(Path("/test/file1.txt"))
                assert is_file_in_session(Path("/test/file2.txt"))

    @patch('session_tracker.get_ai_data_path')
    @patch('role_enforcer.get_current_agent')
    def test_role_enforcement_with_session_tracking(self, mock_get_current_agent, mock_get_ai_data_path):
        """Test role enforcement working with session tracking."""
        mock_get_ai_data_path.return_value = self.session_dir
        mock_get_current_agent.return_value = "coding-agent"

        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = self.role_config
            enforcer = get_role_enforcer("test-session")

            # Test workflow: check permission, then track usage
            allowed, message = enforcer.check_tool_permission("Write", {"file_path": "/test/code.py"})
            assert allowed is True

            # If permission granted, simulate file modification tracking
            if allowed:
                add_modified_file(Path("/test/code.py"))

            # Verify file is tracked in session
            assert is_file_in_session(Path("/test/code.py"))

            # Test blocked operation doesn't add to session
            allowed, message = enforcer.check_tool_permission("Task", {"prompt": "test"})
            assert allowed is False

            # Blocked operations shouldn't be tracked (in real implementation)
            # This test verifies the integration points exist

    @patch('session_tracker.get_ai_data_path')
    @patch('role_enforcer.get_current_agent')
    def test_session_timeout_with_role_state(self, mock_get_current_agent, mock_get_ai_data_path):
        """Test session timeout behavior with role state persistence."""
        mock_get_ai_data_path.return_value = self.session_dir
        mock_get_current_agent.return_value = "coding-agent"

        with freeze_time("2024-01-01 12:00:00") as frozen_time:
            # Create initial session with role state
            session1 = get_current_session()
            add_modified_file(Path("/test/file1.txt"))

            with patch.object(RoleEnforcer, '_load_config') as mock_load:
                mock_load.return_value = self.role_config
                enforcer = get_role_enforcer("test-session")

                # Verify role and permission work
                allowed, message = enforcer.check_tool_permission("Write", {"file_path": "/test/file2.py"})
                assert allowed is True

        # Fast forward past session timeout (3 hours)
        with freeze_time("2024-01-01 15:30:00") as frozen_time:
            # Session should be expired and new
            session2 = get_current_session()
            assert session2['session_id'] != session1['session_id']
            assert not is_file_in_session(Path("/test/file1.txt"))

            # But role state should persist (separate from session)
            with patch.object(RoleEnforcer, '_load_config') as mock_load:
                mock_load.return_value = self.role_config
                enforcer2 = get_role_enforcer("test-session")

                # Role permissions should still work
                allowed, message = enforcer2.check_tool_permission("Write", {"file_path": "/test/file3.py"})
                assert allowed is True

    @patch('session_tracker.get_ai_data_path')
    @patch('role_enforcer.get_current_agent')
    def test_concurrent_session_access_simulation(self, mock_get_current_agent, mock_get_ai_data_path):
        """Test behavior under simulated concurrent access."""
        mock_get_ai_data_path.return_value = self.session_dir

        # Simulate two different sessions/agents working concurrently
        mock_get_current_agent.return_value = "coding-agent"

        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = self.role_config

            # Session 1: coding agent
            enforcer1 = get_role_enforcer("session1")
            session1 = get_current_session()
            add_modified_file(Path("/test/session1_file.py"))

            # Session 2: master orchestrator (different role, different session)
            mock_get_current_agent.return_value = "master-orchestrator-agent"
            enforcer2 = get_role_enforcer("session2")

            # Both should work independently
            allowed1, msg1 = enforcer1.check_tool_permission("Write", {"file_path": "/test/file1.py"})
            allowed2, msg2 = enforcer2.check_tool_permission("Task", {"prompt": "test"})

            assert allowed1 is True  # coding-agent can write
            assert allowed2 is True  # master-orchestrator can delegate

            # Session tracking should be isolated (same session file but different sessions would be handled)
            assert is_file_in_session(Path("/test/session1_file.py"))

    @patch('session_tracker.get_ai_data_path')
    @patch('role_enforcer.get_current_agent')
    def test_state_recovery_after_errors(self, mock_get_current_agent, mock_get_ai_data_path):
        """Test state recovery after various error conditions."""
        mock_get_ai_data_path.return_value = self.session_dir

        # Start with valid state
        mock_get_current_agent.return_value = "coding-agent"
        session = get_current_session()
        add_modified_file(Path("/test/file1.txt"))

        # Simulate session file corruption
        with open(self.session_file, 'w') as f:
            f.write("corrupted json")

        # System should recover gracefully
        with freeze_time("2024-01-01 13:00:00"):
            recovered_session = get_current_session()

            # Should be a new session due to corruption
            assert recovered_session['session_id'] != session['session_id']
            assert recovered_session['modified_files'] == []

            # Role enforcement should still work
            with patch.object(RoleEnforcer, '_load_config') as mock_load:
                mock_load.return_value = self.role_config
                enforcer = get_role_enforcer("test-session")

                allowed, message = enforcer.check_tool_permission("Write", {"file_path": "/test/file2.py"})
                assert allowed is True

    @patch('session_tracker.get_ai_data_path')
    @patch('role_enforcer.get_current_agent')
    def test_performance_under_load(self, mock_get_current_agent, mock_get_ai_data_path):
        """Test performance of integrated system under load."""
        mock_get_ai_data_path.return_value = self.session_dir
        mock_get_current_agent.return_value = "coding-agent"

        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = self.role_config
            enforcer = get_role_enforcer("test-session")

            import time

            # Test many operations
            start_time = time.time()

            for i in range(100):
                # Check permission
                allowed, message = enforcer.check_tool_permission("Write", {"file_path": f"/test/file{i}.py"})

                # Track file modification
                if allowed:
                    add_modified_file(Path(f"/test/file{i}.py"))

                # Check if file is in session
                is_file_in_session(Path(f"/test/file{i}.py"))

            end_time = time.time()

            # Should complete within reasonable time (< 2 seconds for 100 operations)
            assert end_time - start_time < 2.0

            # Verify final state
            session = get_current_session()
            assert len(session['modified_files']) == 100

    @patch('session_tracker.get_ai_data_path')
    def test_session_cleanup_with_role_preservation(self, mock_get_ai_data_path):
        """Test that session cleanup doesn't affect role state."""
        mock_get_ai_data_path.return_value = self.session_dir

        # Create expired session
        expired_time = datetime.now() - timedelta(hours=3)
        expired_session = {
            "session_id": expired_time.isoformat(),
            "started_at": expired_time.isoformat(),
            "modified_files": ["/test/old_file.txt"],
            "modified_folders": []
        }

        with open(self.session_file, 'w') as f:
            json.dump(expired_session, f)

        # Set up role state (would be separate from session in real system)
        with patch('role_enforcer.get_current_agent') as mock_get_current_agent:
            mock_get_current_agent.return_value = "coding-agent"

            with patch.object(RoleEnforcer, '_load_config') as mock_load:
                mock_load.return_value = self.role_config

                # Clean expired sessions
                clear_expired_sessions()

                # Session should be cleaned
                assert not self.session_file.exists()

                # But role enforcement should still work
                enforcer = get_role_enforcer("test-session")
                allowed, message = enforcer.check_tool_permission("Write", {"file_path": "/test/file.py"})
                assert allowed is True

    @patch('session_tracker.get_ai_data_path')
    @patch('role_enforcer.get_current_agent')
    def test_workflow_master_to_coding_agent_transition(self, mock_get_current_agent, mock_get_ai_data_path):
        """Test complete workflow: master orchestrator delegates to coding agent."""
        mock_get_ai_data_path.return_value = self.session_dir

        with freeze_time("2024-01-01 12:00:00"):
            # 1. Start as master orchestrator
            mock_get_current_agent.return_value = "master-orchestrator-agent"

            with patch.object(RoleEnforcer, '_load_config') as mock_load:
                mock_load.return_value = self.role_config
                master_enforcer = get_role_enforcer("master-session")

                # Master can delegate but not write files
                allowed, message = master_enforcer.check_tool_permission("Task", {"prompt": "implement feature"})
                assert allowed is True

                allowed, message = master_enforcer.check_tool_permission("Write", {"file_path": "/src/feature.py"})
                assert allowed is False
                assert "delegate" in message.lower() or "orchestrator" in message.lower()

                # Track that delegation occurred (conceptually)
                session = get_current_session()
                add_modified_file(Path("/logs/delegation.log"))  # Master tracks delegation

            # 2. Transition to coding agent (simulates delegation)
            mock_get_current_agent.return_value = "coding-agent"

            with patch.object(RoleEnforcer, '_load_config') as mock_load:
                mock_load.return_value = self.role_config
                coding_enforcer = get_role_enforcer("coding-session")

                # Coding agent can write files but not delegate
                allowed, message = coding_enforcer.check_tool_permission("Write", {"file_path": "/src/feature.py"})
                assert allowed is True

                allowed, message = coding_enforcer.check_tool_permission("Task", {"prompt": "delegate work"})
                assert allowed is False

                # Track implementation work
                add_modified_file(Path("/src/feature.py"))
                add_modified_file(Path("/tests/test_feature.py"))

                # Verify files are tracked
                assert is_file_in_session(Path("/src/feature.py"))
                assert is_file_in_session(Path("/tests/test_feature.py"))

            # 3. Back to master orchestrator (simulates completion report)
            mock_get_current_agent.return_value = "master-orchestrator-agent"

            # Session persists across role changes
            final_session = get_current_session()
            assert is_file_in_session(Path("/logs/delegation.log"))
            assert is_file_in_session(Path("/src/feature.py"))
            assert is_file_in_session(Path("/tests/test_feature.py"))

    def test_data_consistency_across_components(self):
        """Test data consistency between session and state components."""
        # This test verifies that the interfaces between components are consistent

        # Test session data structure consistency
        with patch('session_tracker.get_ai_data_path') as mock_get_ai_data_path:
            mock_get_ai_data_path.return_value = self.session_dir

            session = get_current_session()

            # Verify required fields exist
            required_fields = ['session_id', 'started_at', 'modified_files', 'modified_folders']
            for field in required_fields:
                assert field in session

            # Verify data types
            assert isinstance(session['modified_files'], list)
            assert isinstance(session['modified_folders'], list)
            assert isinstance(session['session_id'], str)
            assert isinstance(session['started_at'], str)

        # Test role enforcement data structure consistency
        with patch('role_enforcer.get_current_agent') as mock_get_current_agent:
            mock_get_current_agent.return_value = "coding-agent"

            with patch.object(RoleEnforcer, '_load_config') as mock_load:
                mock_load.return_value = self.role_config
                enforcer = get_role_enforcer("test-session")

                # Test permission check return format
                allowed, message = enforcer.check_tool_permission("Read", {"file_path": "/test.txt"})
                assert isinstance(allowed, bool)
                assert isinstance(message, str)

                # Test role info format
                role_info = enforcer.get_role_info("coding-agent")
                required_info_fields = ['role', 'description', 'allowed_tools', 'blocked_tools']
                for field in required_info_fields:
                    assert field in role_info


class TestSessionStateErrorHandling:
    """Test error handling in integrated session and state management."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        # Clear global state
        import role_enforcer
        role_enforcer._enforcer_instance = None

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Clear global state
        import role_enforcer
        role_enforcer._enforcer_instance = None

    @patch('session_tracker.get_ai_data_path')
    @patch('role_enforcer.get_current_agent')
    def test_session_file_permission_error(self, mock_get_current_agent, mock_get_ai_data_path):
        """Test handling of session file permission errors."""
        # Create read-only directory
        readonly_dir = Path(self.temp_dir) / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)

        mock_get_ai_data_path.return_value = readonly_dir
        mock_get_current_agent.return_value = "coding-agent"

        # Should handle permission errors gracefully
        try:
            session = get_current_session()
            # If successful, verify it's a valid session
            assert 'session_id' in session
        except PermissionError:
            # Permission error is acceptable
            pass

        # Role enforcement should still work despite session errors
        role_config = {"enabled": False}  # Disabled for simplicity
        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = role_config
            enforcer = get_role_enforcer("test-session")

            allowed, message = enforcer.check_tool_permission("Read", {"file_path": "/test.txt"})
            assert allowed is True  # Should work when enforcement disabled

        # Restore permissions for cleanup
        readonly_dir.chmod(0o755)

    @patch('session_tracker.get_ai_data_path')
    @patch('role_enforcer.get_current_agent')
    def test_agent_state_error_recovery(self, mock_get_current_agent, mock_get_ai_data_path):
        """Test recovery when agent state management fails."""
        mock_get_ai_data_path.return_value = Path(self.temp_dir)

        # Simulate agent state manager failure
        mock_get_current_agent.side_effect = Exception("Agent state error")

        role_config = {
            "enabled": True,
            "default_role": {
                "name": "uninitialized",
                "allowed_tools": ["Read"],
                "blocked_tools": "*"
            }
        }

        with patch.object(RoleEnforcer, '_load_config') as mock_load:
            mock_load.return_value = role_config

            # Should fall back to uninitialized role
            enforcer = get_role_enforcer("test-session")
            allowed, message = enforcer.check_tool_permission("Write", {"file_path": "/test.py"})

            assert allowed is False  # Uninitialized role should deny write

        # Session tracking should still work
        session = get_current_session()
        assert 'session_id' in session

    @patch('session_tracker.get_ai_data_path')
    def test_disk_space_exhaustion_simulation(self, mock_get_ai_data_path):
        """Test behavior when disk space is exhausted."""
        mock_get_ai_data_path.return_value = Path(self.temp_dir)

        # Mock file write to simulate disk full error
        original_open = open

        def mock_open_disk_full(*args, **kwargs):
            if 'w' in args[1:] or 'w' in kwargs.get('mode', ''):
                raise OSError("No space left on device")
            return original_open(*args, **kwargs)

        with patch('builtins.open', side_effect=mock_open_disk_full):
            # Session operations should handle disk full gracefully
            try:
                add_modified_file(Path("/test/file.txt"))
                # If it succeeds, that's also acceptable (might use existing session)
            except OSError:
                # Disk full error is acceptable behavior
                pass

            # Should still be able to read existing session data
            try:
                session = get_current_session()
                # Might succeed if reading from memory or existing file
            except OSError:
                # Also acceptable if completely unable to access storage
                pass


if __name__ == "__main__":
    pytest.main([__file__])