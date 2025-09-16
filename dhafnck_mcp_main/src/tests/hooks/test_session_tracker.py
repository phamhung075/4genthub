#!/usr/bin/env python3
"""
Tests for Session Tracker System

Tests the session tracking functionality including:
- 2-hour session timeout management
- File modification tracking
- Folder modification tracking
- Session persistence and cleanup
- State recovery across sessions

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
    import session_tracker
    from session_tracker import (
        get_session_file,
        get_current_session,
        save_session,
        add_modified_file,
        add_modified_folder,
        is_file_in_session,
        is_folder_in_session,
        clear_expired_sessions
    )
except ImportError:
    # Skip these tests if the module is not available
    pytest.skip("session_tracker module not available", allow_module_level=True)


class TestSessionTracker:
    """Test session tracking functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directory for test session files
        self.temp_dir = tempfile.mkdtemp()
        self.test_session_file = Path(self.temp_dir) / 'documentation_session.json'

        # Mock the get_ai_data_path function to use our temp directory
        self.mock_ai_data_path = Mock(return_value=Path(self.temp_dir))

        # Clear any existing session state
        if self.test_session_file.exists():
            self.test_session_file.unlink()

    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up temporary files
        if self.test_session_file.exists():
            self.test_session_file.unlink()

        try:
            os.rmdir(self.temp_dir)
        except OSError:
            pass  # Directory not empty or already removed

    @patch('session_tracker.get_ai_data_path')
    def test_get_session_file(self, mock_get_ai_data_path):
        """Test session file path generation."""
        mock_get_ai_data_path.return_value = Path(self.temp_dir)

        session_file = get_session_file()

        assert session_file == self.test_session_file
        mock_get_ai_data_path.assert_called_once()

    @patch('session_tracker.get_ai_data_path')
    def test_get_current_session_new(self, mock_get_ai_data_path):
        """Test creating a new session when none exists."""
        mock_get_ai_data_path.return_value = Path(self.temp_dir)

        with freeze_time("2024-01-01 12:00:00") as frozen_time:
            session = get_current_session()

            # Verify session structure
            assert 'session_id' in session
            assert 'started_at' in session
            assert 'modified_files' in session
            assert 'modified_folders' in session

            # Verify timestamps
            assert session['started_at'] == "2024-01-01T12:00:00"
            assert session['session_id'] == "2024-01-01T12:00:00"

            # Verify empty lists
            assert session['modified_files'] == []
            assert session['modified_folders'] == []

            # Verify file was created
            assert self.test_session_file.exists()

    @patch('session_tracker.get_ai_data_path')
    def test_get_current_session_existing_valid(self, mock_get_ai_data_path):
        """Test loading an existing valid session."""
        mock_get_ai_data_path.return_value = Path(self.temp_dir)

        # Create a valid session (1 hour old)
        session_time = datetime.now() - timedelta(hours=1)
        existing_session = {
            "session_id": session_time.isoformat(),
            "started_at": session_time.isoformat(),
            "modified_files": ["/test/file1.txt", "/test/file2.txt"],
            "modified_folders": ["/test/folder1"]
        }

        # Write session file
        with open(self.test_session_file, 'w') as f:
            json.dump(existing_session, f)

        session = get_current_session()

        # Should return existing session
        assert session == existing_session
        assert len(session['modified_files']) == 2
        assert len(session['modified_folders']) == 1

    @patch('session_tracker.get_ai_data_path')
    def test_get_current_session_expired(self, mock_get_ai_data_path):
        """Test creating new session when existing one is expired."""
        mock_get_ai_data_path.return_value = Path(self.temp_dir)

        # Create an expired session (3 hours old)
        session_time = datetime.now() - timedelta(hours=3)
        expired_session = {
            "session_id": session_time.isoformat(),
            "started_at": session_time.isoformat(),
            "modified_files": ["/test/old_file.txt"],
            "modified_folders": ["/test/old_folder"]
        }

        # Write expired session file
        with open(self.test_session_file, 'w') as f:
            json.dump(expired_session, f)

        with freeze_time("2024-01-01 15:00:00") as frozen_time:
            session = get_current_session()

            # Should be a new session, not the expired one
            assert session['started_at'] == "2024-01-01T15:00:00"
            assert session['modified_files'] == []
            assert session['modified_folders'] == []

    @patch('session_tracker.get_ai_data_path')
    def test_get_current_session_corrupted_file(self, mock_get_ai_data_path):
        """Test handling corrupted session file."""
        mock_get_ai_data_path.return_value = Path(self.temp_dir)

        # Write corrupted JSON
        with open(self.test_session_file, 'w') as f:
            f.write("invalid json content")

        with freeze_time("2024-01-01 12:00:00") as frozen_time:
            session = get_current_session()

            # Should create new session despite corrupted file
            assert session['started_at'] == "2024-01-01T12:00:00"
            assert session['modified_files'] == []
            assert session['modified_folders'] == []

    @patch('session_tracker.get_ai_data_path')
    def test_save_session(self, mock_get_ai_data_path):
        """Test saving session data."""
        mock_get_ai_data_path.return_value = Path(self.temp_dir)

        test_session = {
            "session_id": "test-session-id",
            "started_at": "2024-01-01T12:00:00",
            "modified_files": ["/test/file.txt"],
            "modified_folders": ["/test/folder"]
        }

        save_session(test_session)

        # Verify file was written
        assert self.test_session_file.exists()

        # Verify content
        with open(self.test_session_file, 'r') as f:
            saved_data = json.load(f)

        assert saved_data == test_session

    @patch('session_tracker.get_current_session')
    @patch('session_tracker.save_session')
    def test_add_modified_file(self, mock_save, mock_get_session):
        """Test adding modified file to session."""
        # Mock existing session
        mock_session = {
            "session_id": "test-session",
            "started_at": "2024-01-01T12:00:00",
            "modified_files": [],
            "modified_folders": []
        }
        mock_get_session.return_value = mock_session

        # Add file
        test_file = Path("/test/file.txt")
        add_modified_file(test_file)

        # Verify file was added to session
        assert str(test_file) in mock_session['modified_files']
        mock_save.assert_called_once_with(mock_session)

    @patch('session_tracker.get_current_session')
    @patch('session_tracker.save_session')
    def test_add_modified_file_duplicate(self, mock_save, mock_get_session):
        """Test adding duplicate file doesn't create duplicates."""
        # Mock session with existing file
        test_file = "/test/file.txt"
        mock_session = {
            "session_id": "test-session",
            "started_at": "2024-01-01T12:00:00",
            "modified_files": [test_file],
            "modified_folders": []
        }
        mock_get_session.return_value = mock_session

        # Add same file again
        add_modified_file(Path(test_file))

        # Verify no duplicate added
        assert mock_session['modified_files'].count(test_file) == 1
        mock_save.assert_called_once_with(mock_session)

    @patch('session_tracker.get_current_session')
    @patch('session_tracker.save_session')
    def test_add_modified_folder(self, mock_save, mock_get_session):
        """Test adding modified folder to session."""
        # Mock existing session
        mock_session = {
            "session_id": "test-session",
            "started_at": "2024-01-01T12:00:00",
            "modified_files": [],
            "modified_folders": []
        }
        mock_get_session.return_value = mock_session

        # Add folder
        test_folder = Path("/test/folder")
        add_modified_folder(test_folder)

        # Verify folder was added to session
        assert str(test_folder) in mock_session['modified_folders']
        mock_save.assert_called_once_with(mock_session)

    @patch('session_tracker.get_current_session')
    def test_is_file_in_session_true(self, mock_get_session):
        """Test checking if file is in session - positive case."""
        test_file = "/test/file.txt"
        mock_session = {
            "modified_files": [test_file, "/other/file.txt"],
            "modified_folders": []
        }
        mock_get_session.return_value = mock_session

        result = is_file_in_session(Path(test_file))
        assert result is True

    @patch('session_tracker.get_current_session')
    def test_is_file_in_session_false(self, mock_get_session):
        """Test checking if file is in session - negative case."""
        mock_session = {
            "modified_files": ["/other/file.txt"],
            "modified_folders": []
        }
        mock_get_session.return_value = mock_session

        result = is_file_in_session(Path("/test/file.txt"))
        assert result is False

    @patch('session_tracker.get_current_session')
    def test_is_folder_in_session_true(self, mock_get_session):
        """Test checking if folder is in session - positive case."""
        test_folder = "/test/folder"
        mock_session = {
            "modified_files": [],
            "modified_folders": [test_folder, "/other/folder"]
        }
        mock_get_session.return_value = mock_session

        result = is_folder_in_session(Path(test_folder))
        assert result is True

    @patch('session_tracker.get_current_session')
    def test_is_folder_in_session_false(self, mock_get_session):
        """Test checking if folder is in session - negative case."""
        mock_session = {
            "modified_files": [],
            "modified_folders": ["/other/folder"]
        }
        mock_get_session.return_value = mock_session

        result = is_folder_in_session(Path("/test/folder"))
        assert result is False

    @patch('session_tracker.get_ai_data_path')
    def test_clear_expired_sessions_expired(self, mock_get_ai_data_path):
        """Test clearing expired sessions."""
        mock_get_ai_data_path.return_value = Path(self.temp_dir)

        # Create expired session
        expired_time = datetime.now() - timedelta(hours=3)
        expired_session = {
            "session_id": expired_time.isoformat(),
            "started_at": expired_time.isoformat(),
            "modified_files": ["/test/file.txt"],
            "modified_folders": []
        }

        # Write expired session
        with open(self.test_session_file, 'w') as f:
            json.dump(expired_session, f)

        # Clear expired sessions
        clear_expired_sessions()

        # Session file should be deleted
        assert not self.test_session_file.exists()

    @patch('session_tracker.get_ai_data_path')
    def test_clear_expired_sessions_valid(self, mock_get_ai_data_path):
        """Test not clearing valid sessions."""
        mock_get_ai_data_path.return_value = Path(self.temp_dir)

        # Create valid session (1 hour old)
        valid_time = datetime.now() - timedelta(hours=1)
        valid_session = {
            "session_id": valid_time.isoformat(),
            "started_at": valid_time.isoformat(),
            "modified_files": ["/test/file.txt"],
            "modified_folders": []
        }

        # Write valid session
        with open(self.test_session_file, 'w') as f:
            json.dump(valid_session, f)

        # Clear expired sessions
        clear_expired_sessions()

        # Session file should still exist
        assert self.test_session_file.exists()

    @patch('session_tracker.get_ai_data_path')
    def test_clear_expired_sessions_no_file(self, mock_get_ai_data_path):
        """Test clearing expired sessions when no session file exists."""
        mock_get_ai_data_path.return_value = Path(self.temp_dir)

        # Ensure no session file exists
        assert not self.test_session_file.exists()

        # Should not raise error
        clear_expired_sessions()

        # Still no file should exist
        assert not self.test_session_file.exists()

    @patch('session_tracker.get_ai_data_path')
    def test_clear_expired_sessions_corrupted_file(self, mock_get_ai_data_path):
        """Test handling corrupted session file during cleanup."""
        mock_get_ai_data_path.return_value = Path(self.temp_dir)

        # Write corrupted session file
        with open(self.test_session_file, 'w') as f:
            f.write("invalid json")

        # Should not raise error
        clear_expired_sessions()

        # File should still exist (not deleted due to parsing error)
        assert self.test_session_file.exists()

    @patch('session_tracker.get_ai_data_path')
    def test_session_timeout_boundary(self, mock_get_ai_data_path):
        """Test session timeout exactly at 2-hour boundary."""
        mock_get_ai_data_path.return_value = Path(self.temp_dir)

        # Create session exactly 2 hours old
        boundary_time = datetime.now() - timedelta(hours=2)
        boundary_session = {
            "session_id": boundary_time.isoformat(),
            "started_at": boundary_time.isoformat(),
            "modified_files": ["/test/file.txt"],
            "modified_folders": []
        }

        # Write session
        with open(self.test_session_file, 'w') as f:
            json.dump(boundary_session, f)

        # Get current session should create new one (>= 2 hours is expired)
        with freeze_time("2024-01-01 14:00:00") as frozen_time:
            session = get_current_session()

            # Should be new session
            assert session['started_at'] == "2024-01-01T14:00:00"
            assert session['modified_files'] == []

    @patch('session_tracker.get_ai_data_path')
    def test_session_workflow_integration(self, mock_get_ai_data_path):
        """Test complete session workflow integration."""
        mock_get_ai_data_path.return_value = Path(self.temp_dir)

        with freeze_time("2024-01-01 12:00:00") as frozen_time:
            # 1. Get new session
            session = get_current_session()
            assert session['modified_files'] == []
            assert session['modified_folders'] == []

            # 2. Add some files and folders
            add_modified_file(Path("/test/file1.txt"))
            add_modified_file(Path("/test/file2.txt"))
            add_modified_folder(Path("/test/folder1"))

            # 3. Check files are tracked
            assert is_file_in_session(Path("/test/file1.txt"))
            assert is_file_in_session(Path("/test/file2.txt"))
            assert is_folder_in_session(Path("/test/folder1"))
            assert not is_file_in_session(Path("/test/untracked.txt"))

            # 4. Get session again - should return same session
            session2 = get_current_session()
            assert len(session2['modified_files']) == 2
            assert len(session2['modified_folders']) == 1

        # 5. Fast forward 3 hours - session should expire
        with freeze_time("2024-01-01 15:30:00") as frozen_time:
            session3 = get_current_session()
            assert session3['modified_files'] == []
            assert session3['modified_folders'] == []
            assert session3['started_at'] == "2024-01-01T15:30:00"


class TestSessionTrackerEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures."""
        try:
            os.rmdir(self.temp_dir)
        except OSError:
            pass

    @patch('session_tracker.get_ai_data_path')
    def test_permission_denied_handling(self, mock_get_ai_data_path):
        """Test handling permission denied errors."""
        # Set up read-only directory
        readonly_dir = Path(self.temp_dir) / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)

        mock_get_ai_data_path.return_value = readonly_dir

        # Should handle permission errors gracefully
        try:
            session = get_current_session()
            # If it succeeds, verify it's a valid session
            assert 'session_id' in session
        except PermissionError:
            # Permission error is acceptable behavior
            pass
        finally:
            # Restore permissions for cleanup
            readonly_dir.chmod(0o755)

    @patch('session_tracker.get_ai_data_path')
    def test_concurrent_access_simulation(self, mock_get_ai_data_path):
        """Test behavior under simulated concurrent access."""
        mock_get_ai_data_path.return_value = Path(self.temp_dir)

        # Simulate race condition by modifying file between read and write
        original_save = session_tracker.save_session

        def racing_save(session_data):
            # Another process writes to the file first
            competing_session = {
                "session_id": "competing-session",
                "started_at": "2024-01-01T11:00:00",
                "modified_files": ["/competing/file.txt"],
                "modified_folders": []
            }
            original_save(competing_session)
            # Now save our session (should overwrite)
            original_save(session_data)

        with patch.object(session_tracker, 'save_session', side_effect=racing_save):
            add_modified_file(Path("/test/file.txt"))

            # Verify our session eventually wins
            session = get_current_session()
            assert "/test/file.txt" in session['modified_files']


# Performance test class
class TestSessionTrackerPerformance:
    """Test performance characteristics of session tracker."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures."""
        try:
            os.rmdir(self.temp_dir)
        except OSError:
            pass

    @patch('session_tracker.get_ai_data_path')
    def test_large_session_handling(self, mock_get_ai_data_path):
        """Test handling large sessions with many tracked files."""
        mock_get_ai_data_path.return_value = Path(self.temp_dir)

        # Add many files to session
        for i in range(1000):
            add_modified_file(Path(f"/test/file_{i}.txt"))

        # Session operations should still be reasonably fast
        import time

        start_time = time.time()
        session = get_current_session()
        end_time = time.time()

        # Should complete within reasonable time (< 1 second)
        assert end_time - start_time < 1.0
        assert len(session['modified_files']) == 1000

        # Check operations should also be fast
        start_time = time.time()
        result = is_file_in_session(Path("/test/file_500.txt"))
        end_time = time.time()

        assert result is True
        assert end_time - start_time < 0.1  # Very fast lookup


if __name__ == "__main__":
    pytest.main([__file__])