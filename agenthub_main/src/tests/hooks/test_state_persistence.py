#!/usr/bin/env python3
"""
Tests for State Persistence and Recovery

Tests the persistence and recovery capabilities of the session and state management including:
- State persistence across application restarts
- Data recovery after corruption or loss
- State migration and versioning
- Long-term session management
- Memory vs disk state consistency

Part of subtask: a160a5a8-e058-4594-8521-1a14121d2b6c
"""

import pytest
import json
import tempfile
import os
import shutil
from unittest.mock import Mock, patch, mock_open
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
        save_session,
        add_modified_file,
        add_modified_folder,
        is_file_in_session,
        clear_expired_sessions
    )

    # Import agent state manager
    from agent_state_manager import (
        AgentStateManager,
        get_current_agent,
        set_current_agent,
        agent_state_manager
    )

    # Import role enforcer
    from role_enforcer import (
        RoleEnforcer,
        get_role_enforcer
    )

except ImportError:
    # Skip these tests if the modules are not available
    pytest.skip("state persistence modules not available", allow_module_level=True)


class TestStatePersistence:
    """Test state persistence across sessions and restarts."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directories for test data
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir) / "data"
        self.data_dir.mkdir()

        # Test files
        self.session_file = self.data_dir / 'documentation_session.json'
        self.agent_state_file = self.data_dir / 'agent_state.json'

        # Sample test data
        self.sample_session = {
            "session_id": "2024-01-01T12:00:00",
            "started_at": "2024-01-01T12:00:00",
            "modified_files": [
                "/src/main.py",
                "/tests/test_main.py",
                "/docs/api.md"
            ],
            "modified_folders": [
                "/src",
                "/tests"
            ]
        }

        self.sample_agent_state = {
            "session1": {
                "current_agent": "coding-agent",
                "last_updated": "2024-01-01T12:30:00"
            },
            "session2": {
                "current_agent": "master-orchestrator-agent",
                "last_updated": "2024-01-01T12:45:00"
            }
        }

        # Clear global state
        import role_enforcer
        role_enforcer._enforcer_instance = None

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Clear global state
        import role_enforcer
        role_enforcer._enforcer_instance = None

    def create_test_files(self):
        """Helper to create test state files."""
        # Create session file
        with open(self.session_file, 'w') as f:
            json.dump(self.sample_session, f, indent=2)

        # Create agent state file
        with open(self.agent_state_file, 'w') as f:
            json.dump(self.sample_agent_state, f, indent=2)

    @patch('session_tracker.get_ai_data_path')
    def test_session_persistence_across_restarts(self, mock_get_ai_data_path):
        """Test that session data persists across application restarts."""
        mock_get_ai_data_path.return_value = self.data_dir

        # Create initial session
        self.create_test_files()

        # First "application instance" - load existing session
        session1 = get_current_session()

        # Verify loaded data matches saved data
        assert session1['session_id'] == self.sample_session['session_id']
        assert session1['modified_files'] == self.sample_session['modified_files']
        assert session1['modified_folders'] == self.sample_session['modified_folders']

        # Add new data to session
        add_modified_file(Path("/new/file.py"))
        add_modified_folder(Path("/new"))

        # Verify changes are saved
        assert is_file_in_session(Path("/new/file.py"))

        # Simulate application restart by getting session again
        session2 = get_current_session()

        # New data should persist
        assert "/new/file.py" in session2['modified_files']
        assert "/new" in session2['modified_folders']

        # Original data should still be there
        assert "/src/main.py" in session2['modified_files']
        assert "/src" in session2['modified_folders']

    @patch('agent_state_manager.get_ai_data_path')
    def test_agent_state_persistence_across_restarts(self, mock_get_ai_data_path):
        """Test that agent state persists across application restarts."""
        mock_get_ai_data_path.return_value = self.data_dir

        # Create initial agent state
        self.create_test_files()

        # First "application instance" - load existing state
        state_manager1 = AgentStateManager()

        # Verify loaded state
        assert state_manager1.get_current_agent("session1") == "coding-agent"
        assert state_manager1.get_current_agent("session2") == "master-orchestrator-agent"

        # Update state
        state_manager1.set_current_agent("session1", "documentation-agent")
        state_manager1.set_current_agent("session3", "test-orchestrator-agent")

        # Simulate application restart with new state manager instance
        state_manager2 = AgentStateManager()

        # Updated state should persist
        assert state_manager2.get_current_agent("session1") == "documentation-agent"
        assert state_manager2.get_current_agent("session2") == "master-orchestrator-agent"
        assert state_manager2.get_current_agent("session3") == "test-orchestrator-agent"

    @patch('session_tracker.get_ai_data_path')
    def test_state_recovery_after_corruption(self, mock_get_ai_data_path):
        """Test state recovery when files are corrupted."""
        mock_get_ai_data_path.return_value = self.data_dir

        # Create corrupted session file
        with open(self.session_file, 'w') as f:
            f.write("invalid json content {[")

        # Should recover by creating new session
        with freeze_time("2024-01-01 15:00:00"):
            session = get_current_session()

            # Should be a new valid session
            assert session['session_id'] == "2024-01-01T15:00:00"
            assert session['modified_files'] == []
            assert session['modified_folders'] == []

            # Should be able to use normally
            add_modified_file(Path("/recovery/test.py"))
            assert is_file_in_session(Path("/recovery/test.py"))

    @patch('agent_state_manager.get_ai_data_path')
    def test_agent_state_recovery_after_corruption(self, mock_get_ai_data_path):
        """Test agent state recovery when files are corrupted."""
        mock_get_ai_data_path.return_value = self.data_dir

        # Create corrupted agent state file
        with open(self.agent_state_file, 'w') as f:
            f.write("corrupted json {[")

        # Should recover with default state
        state_manager = AgentStateManager()

        # Should default to master-orchestrator-agent for any session
        assert state_manager.get_current_agent("any-session") == "master-orchestrator-agent"

        # Should be able to set state normally
        state_manager.set_current_agent("test-session", "coding-agent")
        assert state_manager.get_current_agent("test-session") == "coding-agent"

    @patch('session_tracker.get_ai_data_path')
    @patch('agent_state_manager.get_ai_data_path')
    def test_partial_state_recovery(self, mock_agent_data_path, mock_session_data_path):
        """Test recovery when only some state files exist."""
        mock_session_data_path.return_value = self.data_dir
        mock_agent_data_path.return_value = self.data_dir

        # Only create session file, not agent state file
        with open(self.session_file, 'w') as f:
            json.dump(self.sample_session, f)

        # Session should load normally
        session = get_current_session()
        assert session['session_id'] == self.sample_session['session_id']

        # Agent state should use defaults
        state_manager = AgentStateManager()
        assert state_manager.get_current_agent("session1") == "master-orchestrator-agent"

        # Both should work independently
        add_modified_file(Path("/test/file.py"))
        state_manager.set_current_agent("session1", "coding-agent")

        assert is_file_in_session(Path("/test/file.py"))
        assert state_manager.get_current_agent("session1") == "coding-agent"

    @patch('session_tracker.get_ai_data_path')
    def test_large_session_data_persistence(self, mock_get_ai_data_path):
        """Test persistence of large session data."""
        mock_get_ai_data_path.return_value = self.data_dir

        # Create session with large amount of data
        large_session = {
            "session_id": "2024-01-01T12:00:00",
            "started_at": "2024-01-01T12:00:00",
            "modified_files": [f"/project/file{i}.py" for i in range(1000)],
            "modified_folders": [f"/project/folder{i}" for i in range(100)]
        }

        # Save large session
        save_session(large_session)

        # Load and verify
        loaded_session = get_current_session()
        assert len(loaded_session['modified_files']) == 1000
        assert len(loaded_session['modified_folders']) == 100

        # Verify specific entries
        assert "/project/file500.py" in loaded_session['modified_files']
        assert "/project/folder50" in loaded_session['modified_folders']

        # Add more data and verify persistence
        add_modified_file(Path("/project/file1000.py"))
        reloaded_session = get_current_session()
        assert "/project/file1000.py" in reloaded_session['modified_files']
        assert len(reloaded_session['modified_files']) == 1001

    @patch('agent_state_manager.get_ai_data_path')
    def test_concurrent_state_updates_simulation(self, mock_get_ai_data_path):
        """Test handling of concurrent state updates."""
        mock_get_ai_data_path.return_value = self.data_dir

        # Create initial state
        self.create_test_files()

        # Simulate concurrent updates by multiple state manager instances
        state_manager1 = AgentStateManager()
        state_manager2 = AgentStateManager()

        # Both managers should see initial state
        assert state_manager1.get_current_agent("session1") == "coding-agent"
        assert state_manager2.get_current_agent("session1") == "coding-agent"

        # Update from first manager
        state_manager1.set_current_agent("session1", "documentation-agent")

        # Second manager should see updated state when it reloads
        state_manager3 = AgentStateManager()  # Fresh instance to force reload
        assert state_manager3.get_current_agent("session1") == "documentation-agent"

    @patch('session_tracker.get_ai_data_path')
    def test_session_cleanup_with_persistence(self, mock_get_ai_data_path):
        """Test that session cleanup preserves important data."""
        mock_get_ai_data_path.return_value = self.data_dir

        # Create expired session
        expired_time = datetime.now() - timedelta(hours=3)
        expired_session = {
            "session_id": expired_time.isoformat(),
            "started_at": expired_time.isoformat(),
            "modified_files": ["/important/file.py"],
            "modified_folders": ["/important"]
        }

        with open(self.session_file, 'w') as f:
            json.dump(expired_session, f)

        # Clean expired sessions
        clear_expired_sessions()

        # Session file should be removed
        assert not self.session_file.exists()

        # New session should start fresh
        with freeze_time("2024-01-01 15:00:00"):
            new_session = get_current_session()
            assert new_session['modified_files'] == []
            assert new_session['session_id'] == "2024-01-01T15:00:00"

    def test_state_data_integrity(self):
        """Test data integrity constraints and validation."""
        # Test session data integrity
        with patch('session_tracker.get_ai_data_path') as mock_path:
            mock_path.return_value = self.data_dir

            # Valid session should work
            valid_session = {
                "session_id": "2024-01-01T12:00:00",
                "started_at": "2024-01-01T12:00:00",
                "modified_files": ["/test.py"],
                "modified_folders": ["/test"]
            }

            save_session(valid_session)
            loaded = get_current_session()
            assert loaded == valid_session

        # Test agent state data integrity
        with patch('agent_state_manager.get_ai_data_path') as mock_path:
            mock_path.return_value = self.data_dir

            state_manager = AgentStateManager()

            # Valid agent names should work
            state_manager.set_current_agent("session1", "coding-agent")
            assert state_manager.get_current_agent("session1") == "coding-agent"

            # Agent names with @ prefix should be cleaned
            state_manager.set_current_agent("session2", "@master-orchestrator-agent")
            assert state_manager.get_current_agent("session2") == "master-orchestrator-agent"

    @patch('session_tracker.get_ai_data_path')
    @patch('agent_state_manager.get_ai_data_path')
    def test_backup_and_recovery_simulation(self, mock_agent_path, mock_session_path):
        """Test backup and recovery procedures."""
        mock_session_path.return_value = self.data_dir
        mock_agent_path.return_value = self.data_dir

        # Create initial state
        self.create_test_files()

        # Load initial state
        session = get_current_session()
        state_manager = AgentStateManager()

        # Verify initial state
        assert len(session['modified_files']) == 3
        assert state_manager.get_current_agent("session1") == "coding-agent"

        # Simulate backup by copying files
        backup_dir = Path(self.temp_dir) / "backup"
        backup_dir.mkdir()

        shutil.copy2(self.session_file, backup_dir / "session_backup.json")
        shutil.copy2(self.agent_state_file, backup_dir / "agent_state_backup.json")

        # Simulate data loss
        self.session_file.unlink()
        self.agent_state_file.unlink()

        # Verify data is lost
        new_session = get_current_session()
        new_state_manager = AgentStateManager()

        assert new_session['modified_files'] == []  # Fresh session
        assert new_state_manager.get_current_agent("session1") == "master-orchestrator-agent"  # Default

        # Simulate recovery by restoring backups
        shutil.copy2(backup_dir / "session_backup.json", self.session_file)
        shutil.copy2(backup_dir / "agent_state_backup.json", self.agent_state_file)

        # Verify data is recovered
        recovered_session = get_current_session()
        recovered_state_manager = AgentStateManager()

        assert len(recovered_session['modified_files']) == 3
        assert recovered_state_manager.get_current_agent("session1") == "coding-agent"


class TestStateConsistency:
    """Test consistency between in-memory and persistent state."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir) / "data"
        self.data_dir.mkdir()

        # Clear global state
        import role_enforcer
        role_enforcer._enforcer_instance = None

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Clear global state
        import role_enforcer
        role_enforcer._enforcer_instance = None

    @patch('session_tracker.get_ai_data_path')
    def test_memory_disk_consistency_session(self, mock_get_ai_data_path):
        """Test consistency between in-memory session data and disk."""
        mock_get_ai_data_path.return_value = self.data_dir

        # Create session and add files
        session1 = get_current_session()
        add_modified_file(Path("/test1.py"))
        add_modified_file(Path("/test2.py"))

        # Verify in-memory state
        assert is_file_in_session(Path("/test1.py"))
        assert is_file_in_session(Path("/test2.py"))

        # Load fresh session (should read from disk)
        session2 = get_current_session()

        # Should be consistent
        assert session1['session_id'] == session2['session_id']
        assert "/test1.py" in session2['modified_files']
        assert "/test2.py" in session2['modified_files']

    @patch('agent_state_manager.get_ai_data_path')
    def test_memory_disk_consistency_agent_state(self, mock_get_ai_data_path):
        """Test consistency between in-memory agent state and disk."""
        mock_get_ai_data_path.return_value = self.data_dir

        # Create state manager and set states
        state_manager1 = AgentStateManager()
        state_manager1.set_current_agent("session1", "coding-agent")
        state_manager1.set_current_agent("session2", "documentation-agent")

        # Create new state manager instance (should read from disk)
        state_manager2 = AgentStateManager()

        # Should be consistent
        assert state_manager1.get_current_agent("session1") == state_manager2.get_current_agent("session1")
        assert state_manager1.get_current_agent("session2") == state_manager2.get_current_agent("session2")

    @patch('session_tracker.get_ai_data_path')
    def test_transactional_consistency(self, mock_get_ai_data_path):
        """Test that state updates are transactional."""
        mock_get_ai_data_path.return_value = self.data_dir

        # Start with clean session
        session = get_current_session()
        initial_count = len(session['modified_files'])

        # Add multiple files in sequence
        files_to_add = [
            Path("/file1.py"),
            Path("/file2.py"),
            Path("/file3.py")
        ]

        for file_path in files_to_add:
            add_modified_file(file_path)

            # After each addition, verify consistency
            current_session = get_current_session()
            assert str(file_path) in current_session['modified_files']

        # Verify final state
        final_session = get_current_session()
        assert len(final_session['modified_files']) == initial_count + 3

        # All files should be tracked
        for file_path in files_to_add:
            assert is_file_in_session(file_path)


class TestLongTermStatePersistence:
    """Test long-term state persistence and management."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir) / "data"
        self.data_dir.mkdir()

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('session_tracker.get_ai_data_path')
    @patch('agent_state_manager.get_ai_data_path')
    def test_long_term_session_evolution(self, mock_agent_path, mock_session_path):
        """Test session state evolution over time."""
        mock_session_path.return_value = self.data_dir
        mock_agent_path.return_value = self.data_dir

        # Day 1: Initial work
        with freeze_time("2024-01-01 09:00:00"):
            session = get_current_session()
            add_modified_file(Path("/project/day1_work.py"))
            state_manager = AgentStateManager()
            state_manager.set_current_agent("session1", "coding-agent")

        # Day 1 Evening: Session should expire
        with freeze_time("2024-01-01 23:00:00"):
            clear_expired_sessions()

        # Day 2: New session, but agent state persists
        with freeze_time("2024-01-02 09:00:00"):
            new_session = get_current_session()
            new_state_manager = AgentStateManager()

            # New session should be clean
            assert new_session['modified_files'] == []
            assert new_session['started_at'] == "2024-01-02T09:00:00"

            # But agent state should persist
            assert new_state_manager.get_current_agent("session1") == "coding-agent"

            # Continue work
            add_modified_file(Path("/project/day2_work.py"))
            assert is_file_in_session(Path("/project/day2_work.py"))
            assert not is_file_in_session(Path("/project/day1_work.py"))  # From expired session

    @patch('agent_state_manager.get_ai_data_path')
    def test_agent_state_history_management(self, mock_get_ai_data_path):
        """Test management of agent state history over time."""
        mock_get_ai_data_path.return_value = self.data_dir

        state_manager = AgentStateManager()

        # Simulate agent changes over multiple days
        with freeze_time("2024-01-01 09:00:00"):
            state_manager.set_current_agent("session1", "coding-agent")

        with freeze_time("2024-01-01 14:00:00"):
            state_manager.set_current_agent("session1", "documentation-agent")

        with freeze_time("2024-01-01 16:00:00"):
            state_manager.set_current_agent("session1", "test-orchestrator-agent")

        # Latest state should be preserved
        assert state_manager.get_current_agent("session1") == "test-orchestrator-agent"

        # Verify the state file contains proper timestamp
        state_file = self.data_dir / 'agent_state.json'
        with open(state_file, 'r') as f:
            state_data = json.load(f)

        assert state_data["session1"]["current_agent"] == "test-orchestrator-agent"
        assert "last_updated" in state_data["session1"]


if __name__ == "__main__":
    pytest.main([__file__])