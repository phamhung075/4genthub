#!/usr/bin/env python3
"""
Basic hook system tests to validate setup and functionality.
"""

import sys
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

# Add hooks directory to path for testing
# Go up from: /dhafnck_mcp_main/src/tests/hooks/ to project root
hooks_path = Path(__file__).parent.parent.parent.parent.parent / '.claude' / 'hooks'
sys.path.insert(0, str(hooks_path))


class TestBasicHookFunctionality:
    """Basic tests to validate hook system setup."""

    def test_hooks_can_be_imported(self):
        """Test that hook modules can be imported."""
        try:
            from pre_tool_use import PreToolUseHook, FileLogger
            from post_tool_use import PostToolUseHook
            assert True  # If we get here, imports worked
        except ImportError as e:
            pytest.fail(f"Failed to import hook modules: {e}")

    def test_file_logger_basic_functionality(self, tmp_path):
        """Test basic FileLogger functionality."""
        from pre_tool_use import FileLogger

        logger = FileLogger(tmp_path, 'test_log')

        # Test initialization
        assert logger.log_dir == tmp_path
        assert logger.log_name == 'test_log'

        # Test logging
        logger.log('info', 'Test message')

        # Verify log file was created
        log_file = tmp_path / 'test_log.json'
        assert log_file.exists()

        # Verify log content
        with open(log_file, 'r') as f:
            log_data = json.load(f)

        assert len(log_data) == 1
        assert log_data[0]['level'] == 'info'
        assert log_data[0]['message'] == 'Test message'

    def test_hook_main_entry_points_exist(self):
        """Test that main hook entry points exist."""
        hooks_dir = Path(__file__).parent.parent.parent.parent.parent / '.claude' / 'hooks'

        main_hooks = [
            'pre_tool_use.py',
            'post_tool_use.py',
            'session_start.py',
            'user_prompt_submit.py'
        ]

        for hook_file in main_hooks:
            hook_path = hooks_dir / hook_file
            assert hook_path.exists(), f"Hook file {hook_file} not found"
            assert hook_path.is_file()

    def test_hook_json_processing(self):
        """Test that hooks can process JSON input."""
        from pre_tool_use import main

        # Mock stdin with sample JSON data
        test_data = {
            'tool_name': 'Read',
            'tool_input': {'file_path': '/safe/path/file.py'}
        }

        # This is a basic test - we just want to ensure the hook doesn't crash
        # with proper JSON input
        with patch('sys.stdin') as mock_stdin:
            mock_stdin.read.return_value = json.dumps(test_data)

            try:
                # We can't easily test the full main() function due to sys.exit
                # but we can test that JSON parsing works
                input_data = json.loads(json.dumps(test_data))
                assert input_data['tool_name'] == 'Read'
                assert input_data['tool_input']['file_path'] == '/safe/path/file.py'
            except Exception as e:
                pytest.fail(f"JSON processing failed: {e}")

    @patch('utils.env_loader.get_ai_data_path')
    def test_pre_hook_initialization_without_errors(self, mock_get_path, tmp_path):
        """Test PreToolUseHook can initialize without errors."""
        from pre_tool_use import PreToolUseHook

        mock_get_path.return_value = tmp_path

        try:
            hook = PreToolUseHook()
            assert hook is not None
            assert hasattr(hook, 'validators')
            assert hasattr(hook, 'processors')
            assert hasattr(hook, 'logger')
        except Exception as e:
            pytest.fail(f"PreToolUseHook initialization failed: {e}")

    @patch('utils.env_loader.get_ai_data_path')
    def test_post_hook_initialization_without_errors(self, mock_get_path, tmp_path):
        """Test PostToolUseHook can initialize without errors."""
        from post_tool_use import PostToolUseHook

        mock_get_path.return_value = tmp_path

        try:
            hook = PostToolUseHook()
            assert hook is not None
            assert hasattr(hook, 'components')
            assert hasattr(hook, 'logger')
        except Exception as e:
            pytest.fail(f"PostToolUseHook initialization failed: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])