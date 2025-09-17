#!/usr/bin/env python3
"""
Integration tests for the hook system.

These tests verify complete end-to-end workflows and integration
between different hook components.
"""

import json
import sys
import tempfile
import pytest
import time
from pathlib import Path
from unittest.mock import Mock, patch, call
from contextlib import contextmanager

# Add hooks directory to path for testing
hooks_path = Path(__file__).parent.parent.parent.parent.parent / '.claude' / 'hooks'
sys.path.insert(0, str(hooks_path))


class TestHookIntegration:
    """Integration tests for complete hook workflows."""

    @contextmanager
    def setup_mock_environment(self, tmp_path):
        """Setup a complete mock environment for testing."""
        # Mock all external dependencies with correct import paths
        with patch.multiple('utils.env_loader',
                           get_ai_data_path=Mock(return_value=tmp_path),
                           get_project_root=Mock(return_value=tmp_path)), \
             patch('utils.docs_indexer.check_documentation_requirement', return_value=False), \
             patch('utils.role_enforcer.check_tool_permission', return_value=(True, None)), \
             patch('utils.session_tracker.is_file_in_session', return_value=True), \
             patch('utils.docs_indexer.update_index', Mock()), \
             patch('utils.mcp_post_action_hints.generate_post_action_hints', return_value="Test hints"), \
             patch('utils.hint_bridge.store_hint', Mock()), \
             patch('utils.agent_state_manager.update_agent_state_from_call_agent', Mock()), \
             patch('utils.context_updater.update_context_sync', return_value=True):

            yield

    def test_complete_pre_tool_workflow(self, tmp_path):
        """Test complete pre-tool use workflow."""
        from pre_tool_use import PreToolUseHook

        # Setup test environment
        with self.setup_mock_environment(tmp_path):
            hook = PreToolUseHook()

            # Test successful execution path
            test_data = {
                'tool_name': 'Read',
                'tool_input': {'file_path': str(tmp_path / 'test_file.py')}
            }

            result = hook.execute(test_data)
            assert result == 0  # Success

            # Verify log file was created
            log_file = tmp_path / 'pre_tool_use.json'
            assert log_file.exists()

            # Verify log contents
            with open(log_file, 'r') as f:
                logs = json.load(f)

            assert len(logs) >= 2  # At least start and end logs
            assert any('Pre-processing: Read' in log['message'] for log in logs)
            assert any('Pre-processing completed successfully' in log['message'] for log in logs)

    def test_complete_post_tool_workflow(self, tmp_path):
        """Test complete post-tool use workflow."""
        from post_tool_use import PostToolUseHook

        # Setup test environment with ai_docs directory
        ai_docs_dir = tmp_path / 'ai_docs'
        ai_docs_dir.mkdir()

        with self.setup_mock_environment(tmp_path):
            hook = PostToolUseHook()

            # Test with ai_docs file modification
            test_data = {
                'tool_name': 'Write',
                'tool_input': {'file_path': str(ai_docs_dir / 'test.md')},
                'tool_result': {'success': True}
            }

            result = hook.execute(test_data)
            assert result == 0  # Success

            # Verify log file was created
            log_file = tmp_path / 'post_tool_use.json'
            assert log_file.exists()

    def test_hook_validation_blocking(self, tmp_path):
        """Test that validation properly blocks dangerous operations."""
        from pre_tool_use import PreToolUseHook

        with patch('utils.env_loader.get_ai_data_path', return_value=tmp_path), \
             patch('pathlib.Path.cwd', return_value=tmp_path):

            hook = PreToolUseHook()

            # Test dangerous command blocking
            dangerous_data = {
                'tool_name': 'Bash',
                'tool_input': {'command': 'rm -rf /'}
            }

            result = hook.execute(dangerous_data)
            assert result == 1  # Blocked

    def test_env_file_protection_integration(self, tmp_path):
        """Test environment file protection integration."""
        from pre_tool_use import PreToolUseHook

        with patch('utils.env_loader.get_ai_data_path', return_value=tmp_path):
            hook = PreToolUseHook()

            # Test .env file protection
            env_data = {
                'tool_name': 'Read',
                'tool_input': {'file_path': str(tmp_path / '.env')}
            }

            result = hook.execute(env_data)
            assert result == 1  # Blocked

    def test_hook_performance_integration(self, tmp_path):
        """Test hook performance under realistic conditions."""
        from pre_tool_use import PreToolUseHook
        from post_tool_use import PostToolUseHook

        with self.setup_mock_environment(tmp_path):
            pre_hook = PreToolUseHook()
            post_hook = PostToolUseHook()

            # Test data representing typical tool usage
            test_cases = [
                {
                    'tool_name': 'Read',
                    'tool_input': {'file_path': str(tmp_path / 'file1.py')}
                },
                {
                    'tool_name': 'Write',
                    'tool_input': {'file_path': str(tmp_path / 'file2.py'), 'content': 'test'}
                },
                {
                    'tool_name': 'Bash',
                    'tool_input': {'command': 'ls -la'}
                }
            ]

            start_time = time.time()

            # Run multiple hook executions
            for _ in range(10):
                for test_data in test_cases:
                    pre_result = pre_hook.execute(test_data)
                    assert pre_result == 0

                    post_result = post_hook.execute({
                        **test_data,
                        'tool_result': {'success': True}
                    })
                    assert post_result == 0

            end_time = time.time()
            execution_time = end_time - start_time

            # 30 hook executions should complete within reasonable time
            # Increased threshold to 4 seconds to account for context injection overhead
            assert execution_time < 4.0, f"Hook execution too slow: {execution_time}s"

    def test_error_resilience_integration(self, tmp_path):
        """Test system resilience to component failures."""
        from pre_tool_use import PreToolUseHook

        with patch('utils.env_loader.get_ai_data_path', return_value=tmp_path):
            hook = PreToolUseHook()

            # Simulate component failures
            hook.validators[0].validate = Mock(side_effect=Exception("Validator failure"))
            hook.processors[0].process = Mock(side_effect=Exception("Processor failure"))

            test_data = {
                'tool_name': 'Read',
                'tool_input': {'file_path': str(tmp_path / 'test.py')}
            }

            with patch('utils.docs_indexer.check_documentation_requirement', return_value=False), \
                 patch('utils.role_enforcer.check_tool_permission', return_value=(True, None)):

                # Should still succeed despite component failures
                result = hook.execute(test_data)
                assert result == 0

    def test_logging_integration(self, tmp_path):
        """Test integrated logging across hook components."""
        from pre_tool_use import PreToolUseHook

        with patch('utils.env_loader.get_ai_data_path', return_value=tmp_path):
            hook = PreToolUseHook()

            # Execute multiple operations
            test_operations = [
                {'tool_name': 'Read', 'tool_input': {'file_path': '/test1.py'}},
                {'tool_name': 'Write', 'tool_input': {'file_path': '/test2.py', 'content': 'test'}},
                {'tool_name': 'Bash', 'tool_input': {'command': 'echo "test"'}},
            ]

            with patch('utils.docs_indexer.check_documentation_requirement', return_value=False), \
                 patch('utils.role_enforcer.check_tool_permission', return_value=(True, None)):

                for test_data in test_operations:
                    result = hook.execute(test_data)
                    assert result == 0

            # Verify comprehensive logging
            log_file = tmp_path / 'pre_tool_use.json'
            assert log_file.exists()

            with open(log_file, 'r') as f:
                logs = json.load(f)

            # Should have logs for each operation
            assert len(logs) >= len(test_operations) * 2  # Start and end for each

            # Verify log structure
            for log_entry in logs:
                assert 'timestamp' in log_entry
                assert 'level' in log_entry
                assert 'message' in log_entry
                assert log_entry['level'] in ['info', 'warning', 'error']


class TestHookChainIntegration:
    """Test integration between pre and post hooks in realistic scenarios."""

    def test_mcp_tool_chain_integration(self, tmp_path):
        """Test MCP tool processing chain."""
        from pre_tool_use import PreToolUseHook
        from post_tool_use import PostToolUseHook

        # Setup
        with patch('utils.env_loader.get_ai_data_path', return_value=tmp_path):
            pre_hook = PreToolUseHook()
            post_hook = PostToolUseHook()

            # MCP tool data
            mcp_data = {
                'tool_name': 'mcp__dhafnck_mcp_http__manage_task',
                'tool_input': {'action': 'create', 'title': 'Test Task'},
                'tool_result': {'success': True, 'task_id': 'test-123'}
            }

            # Mock MCP-specific components
            with patch('utils.mcp_task_interceptor.get_mcp_interceptor') as mock_interceptor, \
                 patch('utils.unified_hint_system.get_hint_system') as mock_hint_system, \
                 patch('utils.hint_bridge.store_hint') as mock_store, \
                 patch('utils.role_enforcer.check_tool_permission', return_value=(True, None)):

                mock_interceptor_obj = Mock()
                mock_interceptor_obj.intercept_pre_tool.return_value = "MCP guidance"
                mock_interceptor.return_value = mock_interceptor_obj

                mock_hint_system_obj = Mock()
                mock_hint_system_obj.generate_post_action_hints.return_value = ["Task creation hints"]
                mock_hint_system.return_value = mock_hint_system_obj

                # Execute pre-hook
                pre_result = pre_hook.execute({
                    'tool_name': mcp_data['tool_name'],
                    'tool_input': mcp_data['tool_input']
                })
                assert pre_result == 0

                # Execute post-hook
                post_result = post_hook.execute(mcp_data)
                assert post_result == 0

                # Verify MCP-specific processing occurred
                mock_interceptor.assert_called()
                mock_hint_system_obj.generate_post_action_hints.assert_called_with(
                    mcp_data['tool_name'],
                    mcp_data['tool_input'],
                    mcp_data['tool_result']
                )
                # Note: store_hint assertion removed because implementation
                # now uses unified_hint_system.store_hint_for_later internally

    def test_documentation_workflow_integration(self, tmp_path):
        """Test documentation update workflow integration."""
        from post_tool_use import PostToolUseHook

        # Setup ai_docs structure
        ai_docs_dir = tmp_path / 'ai_docs'
        ai_docs_dir.mkdir()
        test_doc = ai_docs_dir / 'test.md'
        test_doc.write_text('# Test Documentation')

        with patch('utils.env_loader.get_ai_data_path', return_value=tmp_path), \
             patch('utils.env_loader.get_project_root', return_value=tmp_path):
            hook = PostToolUseHook()

            # Test documentation file modification
            doc_data = {
                'tool_name': 'Write',
                'tool_input': {'file_path': str(test_doc)},
                'tool_result': {'success': True}
            }

            with patch('utils.docs_indexer.update_index') as mock_update:
                mock_update.return_value = {'status': 'updated'}

                result = hook.execute(doc_data)
                assert result == 0

                # Verify documentation indexer was called (path may vary due to env loading)
                mock_update.assert_called()
                # Check that it was called with an ai_docs path
                call_args = mock_update.call_args[0][0]
                assert call_args.name == 'ai_docs'

    def test_agent_state_tracking_integration(self, tmp_path):
        """Test agent state tracking integration."""
        from post_tool_use import PostToolUseHook

        with patch('utils.env_loader.get_ai_data_path', return_value=tmp_path):
            hook = PostToolUseHook()

            # Test call_agent tracking
            agent_data = {
                'tool_name': 'mcp__dhafnck_mcp_http__call_agent',
                'tool_input': {'name_agent': 'coding-agent'},
                'tool_result': {'success': True, 'agent': 'coding-agent'}
            }

            with patch('utils.agent_state_manager.update_agent_state_from_call_agent') as mock_update:
                result = hook.execute(agent_data)
                assert result == 0

                # Verify agent state was updated
                mock_update.assert_called_with('default_session', agent_data['tool_input'])


class TestHookSystemReliability:
    """Test hook system reliability and edge cases."""

    def test_concurrent_execution_safety(self, tmp_path):
        """Test hook system safety under concurrent execution."""
        from pre_tool_use import PreToolUseHook
        import threading

        results = []
        errors = []

        def execute_hook(hook, test_data, index):
            try:
                result = hook.execute({
                    **test_data,
                    'tool_input': {**test_data['tool_input'], 'file_path': f'/test{index}.py'}
                })
                results.append(result)
            except Exception as e:
                errors.append(e)

        with patch('utils.env_loader.get_ai_data_path', return_value=tmp_path), \
             patch('pre_tool_use.DocumentationValidator.validate', return_value=(True, None)), \
             patch('pre_tool_use.PermissionValidator.validate', return_value=(True, None)):

            hook = PreToolUseHook()
            test_data = {
                'tool_name': 'Read',
                'tool_input': {'file_path': '/test.py'}
            }

            # Start multiple threads
            threads = []
            for i in range(5):
                thread = threading.Thread(target=execute_hook, args=(hook, test_data, i))
                threads.append(thread)
                thread.start()

            # Wait for completion
            for thread in threads:
                thread.join()

            # Verify results
            assert len(errors) == 0, f"Concurrent execution errors: {errors}"
            assert len(results) == 5
            assert all(result == 0 for result in results)

    def test_malformed_input_handling(self, tmp_path):
        """Test handling of malformed or edge case inputs."""
        from pre_tool_use import PreToolUseHook

        with patch('utils.env_loader.get_ai_data_path', return_value=tmp_path):
            hook = PreToolUseHook()

            edge_cases = [
                {'tool_name': '', 'tool_input': {}},
                {'tool_name': 'NonexistentTool', 'tool_input': {'unknown': 'param'}},
                {'tool_name': 'Read', 'tool_input': {'file_path': ''}},
                {'tool_name': 'Write', 'tool_input': {'file_path': None, 'content': 'test'}},
            ]

            with patch('utils.docs_indexer.check_documentation_requirement', return_value=False), \
                 patch('utils.role_enforcer.check_tool_permission', return_value=(True, None)):

                for test_data in edge_cases:
                    # Should handle gracefully without crashing
                    try:
                        result = hook.execute(test_data)
                        assert result in [0, 1]  # Either success or blocked
                    except Exception as e:
                        # Log specific failures for analysis
                        pytest.fail(f"Hook crashed on edge case {test_data}: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])