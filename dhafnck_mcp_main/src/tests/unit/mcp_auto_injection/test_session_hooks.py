"""
Unit Tests for Session Hooks

Tests the session start hook functionality in isolation with comprehensive
edge cases, error handling, and context injection scenarios.

Test Coverage:
- Session initialization and context loading
- MCP context injection and formatting
- Git status integration
- Cache interaction patterns
- Error handling and fallback strategies
- Performance optimization paths
"""

import pytest
import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta

# Import session hook components
import sys
hooks_path = Path(__file__).parent.parent.parent.parent.parent.parent / ".claude" / "hooks"
sys.path.insert(0, str(hooks_path))

from session_start import (
    log_session_start,
    get_git_status,
    get_recent_issues,
    query_mcp_pending_tasks,
    query_mcp_next_task,
    get_git_branch_context,
    format_mcp_context,
    load_development_context,
    main
)


class TestLogSessionStart:
    """Unit tests for session logging functionality."""
    
    @pytest.fixture
    def temp_ai_data_dir(self):
        """Create temporary AI_DATA directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('session_start.get_ai_data_path', return_value=Path(temp_dir)):
                yield Path(temp_dir)
    
    def test_log_session_start_new_file(self, temp_ai_data_dir):
        """Test logging to new session start file."""
        input_data = {
            "session_id": "test-session-123",
            "source": "startup",
            "timestamp": datetime.now().isoformat()
        }
        
        log_session_start(input_data)
        
        log_file = temp_ai_data_dir / 'session_start.json'
        assert log_file.exists()
        
        with open(log_file, 'r') as f:
            logged_data = json.load(f)
        
        assert len(logged_data) == 1
        assert logged_data[0] == input_data
    
    def test_log_session_start_append_to_existing(self, temp_ai_data_dir):
        """Test appending to existing session log file."""
        log_file = temp_ai_data_dir / 'session_start.json'
        
        # Create existing log data
        existing_data = [{"session_id": "old-session", "source": "resume"}]
        with open(log_file, 'w') as f:
            json.dump(existing_data, f)
        
        # Add new log entry
        new_input = {"session_id": "new-session", "source": "startup"}
        log_session_start(new_input)
        
        # Verify both entries exist
        with open(log_file, 'r') as f:
            logged_data = json.load(f)
        
        assert len(logged_data) == 2
        assert logged_data[0] == existing_data[0]
        assert logged_data[1] == new_input
    
    def test_log_session_start_corrupted_existing_file(self, temp_ai_data_dir):
        """Test handling corrupted existing log file."""
        log_file = temp_ai_data_dir / 'session_start.json'
        
        # Create corrupted log file
        with open(log_file, 'w') as f:
            f.write("invalid json content")
        
        # Should handle gracefully and create new log
        input_data = {"session_id": "test-session", "source": "startup"}
        log_session_start(input_data)
        
        with open(log_file, 'r') as f:
            logged_data = json.load(f)
        
        assert len(logged_data) == 1
        assert logged_data[0] == input_data


class TestGitStatus:
    """Unit tests for git status functionality."""
    
    @patch('subprocess.run')
    def test_get_git_status_success(self, mock_run):
        """Test successful git status retrieval."""
        # Mock git branch command
        mock_branch_result = Mock()
        mock_branch_result.returncode = 0
        mock_branch_result.stdout = "main\n"
        
        # Mock git status command
        mock_status_result = Mock()
        mock_status_result.returncode = 0
        mock_status_result.stdout = "M file1.py\n?? file2.txt\nA file3.js\n"
        
        mock_run.side_effect = [mock_branch_result, mock_status_result]
        
        branch, changes = get_git_status()
        
        assert branch == "main"
        assert changes == 3
        assert mock_run.call_count == 2
    
    @patch('subprocess.run')
    def test_get_git_status_no_changes(self, mock_run):
        """Test git status with no uncommitted changes."""
        mock_branch_result = Mock()
        mock_branch_result.returncode = 0
        mock_branch_result.stdout = "develop\n"
        
        mock_status_result = Mock()
        mock_status_result.returncode = 0
        mock_status_result.stdout = ""
        
        mock_run.side_effect = [mock_branch_result, mock_status_result]
        
        branch, changes = get_git_status()
        
        assert branch == "develop"
        assert changes == 0
    
    @patch('subprocess.run')
    def test_get_git_status_command_failure(self, mock_run):
        """Test git status when git commands fail."""
        mock_run.return_value.returncode = 1
        
        branch, changes = get_git_status()
        
        assert branch is None
        assert changes is None
    
    @patch('subprocess.run', side_effect=subprocess.TimeoutExpired(['git'], 5))
    def test_get_git_status_timeout(self, mock_run):
        """Test git status with command timeout."""
        branch, changes = get_git_status()
        
        assert branch is None
        assert changes is None
    
    @patch('subprocess.run', side_effect=Exception("Git not available"))
    def test_get_git_status_exception(self, mock_run):
        """Test git status with subprocess exception."""
        branch, changes = get_git_status()
        
        assert branch is None
        assert changes is None


class TestGetRecentIssues:
    """Unit tests for GitHub issues functionality."""
    
    @patch('subprocess.run')
    def test_get_recent_issues_success(self, mock_run):
        """Test successful GitHub issues retrieval."""
        # Mock 'which gh' command
        mock_which_result = Mock()
        mock_which_result.returncode = 0
        
        # Mock 'gh issue list' command
        mock_issues_result = Mock()
        mock_issues_result.returncode = 0
        mock_issues_result.stdout = "123\tBug in authentication\topen\n456\tFeature request\topen\n"
        
        mock_run.side_effect = [mock_which_result, mock_issues_result]
        
        result = get_recent_issues()
        
        assert result == "123\tBug in authentication\topen\n456\tFeature request\topen"
        assert mock_run.call_count == 2
    
    @patch('subprocess.run')
    def test_get_recent_issues_gh_not_available(self, mock_run):
        """Test when gh CLI is not available."""
        mock_run.return_value.returncode = 1  # 'which gh' fails
        
        result = get_recent_issues()
        
        assert result is None
        assert mock_run.call_count == 1
    
    @patch('subprocess.run')
    def test_get_recent_issues_no_issues(self, mock_run):
        """Test when no issues are found."""
        mock_which_result = Mock()
        mock_which_result.returncode = 0
        
        mock_issues_result = Mock()
        mock_issues_result.returncode = 0
        mock_issues_result.stdout = ""
        
        mock_run.side_effect = [mock_which_result, mock_issues_result]
        
        result = get_recent_issues()
        
        assert result is None
    
    @patch('subprocess.run')
    def test_get_recent_issues_command_timeout(self, mock_run):
        """Test GitHub issues command timeout."""
        mock_which_result = Mock()
        mock_which_result.returncode = 0
        
        mock_run.side_effect = [
            mock_which_result,
            subprocess.TimeoutExpired(['gh'], 10)
        ]
        
        result = get_recent_issues()
        
        assert result is None


class TestMCPQueries:
    """Unit tests for MCP query functions."""
    
    @patch('session_start.get_session_cache')
    @patch('session_start.get_default_client')
    def test_query_mcp_pending_tasks_cache_hit(self, mock_get_client, mock_get_cache):
        """Test pending tasks query with cache hit."""
        cached_tasks = [
            {"id": "task1", "title": "Cached Task 1"},
            {"id": "task2", "title": "Cached Task 2"}
        ]
        
        mock_cache = Mock()
        mock_cache.get_pending_tasks.return_value = cached_tasks
        mock_get_cache.return_value = mock_cache
        
        result = query_mcp_pending_tasks()
        
        assert result == cached_tasks
        mock_cache.get_pending_tasks.assert_called_once()
        mock_get_client.assert_not_called()  # Should not hit server
    
    @patch('session_start.get_session_cache')
    @patch('session_start.get_default_client')
    def test_query_mcp_pending_tasks_server_success(self, mock_get_client, mock_get_cache):
        """Test pending tasks query with server success."""
        server_tasks = [
            {"id": "server1", "title": "Server Task 1"},
            {"id": "server2", "title": "Server Task 2"}
        ]
        
        mock_cache = Mock()
        mock_cache.get_pending_tasks.return_value = None  # Cache miss
        mock_get_cache.return_value = mock_cache
        
        mock_client = Mock()
        mock_client.query_pending_tasks.return_value = server_tasks
        mock_get_client.return_value = mock_client
        
        result = query_mcp_pending_tasks()
        
        assert result == server_tasks
        mock_cache.get_pending_tasks.assert_called_once()
        mock_client.query_pending_tasks.assert_called_once_with(limit=5)
        mock_cache.cache_pending_tasks.assert_called_once_with(server_tasks)
    
    @patch('session_start.get_session_cache')
    @patch('session_start.get_default_client')
    def test_query_mcp_pending_tasks_server_failure(self, mock_get_client, mock_get_cache):
        """Test pending tasks query with server failure."""
        mock_cache = Mock()
        mock_cache.get_pending_tasks.return_value = None
        mock_get_cache.return_value = mock_cache
        
        mock_client = Mock()
        mock_client.query_pending_tasks.side_effect = Exception("Server error")
        mock_get_client.return_value = mock_client
        
        result = query_mcp_pending_tasks()
        
        assert result is None
        mock_cache.get_pending_tasks.assert_called_once()
        mock_client.query_pending_tasks.assert_called_once_with(limit=5)
    
    @patch('session_start.get_session_cache')
    @patch('session_start.get_default_client')
    def test_query_mcp_next_task_success(self, mock_get_client, mock_get_cache):
        """Test next task query success."""
        branch_id = "branch-uuid-123"
        next_task = {"id": "next1", "title": "Next Task", "priority": "high"}
        
        mock_cache = Mock()
        mock_cache.get_next_task.return_value = None
        mock_get_cache.return_value = mock_cache
        
        mock_client = Mock()
        mock_client.get_next_recommended_task.return_value = next_task
        mock_get_client.return_value = mock_client
        
        result = query_mcp_next_task(branch_id)
        
        assert result == next_task
        mock_cache.get_next_task.assert_called_once_with(branch_id)
        mock_client.get_next_recommended_task.assert_called_once_with(branch_id)
        mock_cache.cache_next_task.assert_called_once_with(branch_id, next_task)
    
    def test_query_mcp_next_task_no_branch_id(self):
        """Test next task query without branch ID."""
        result = query_mcp_next_task(None)
        
        assert result is None
    
    @patch('session_start.get_session_cache')
    @patch('session_start.get_default_client')
    def test_query_mcp_next_task_server_error(self, mock_get_client, mock_get_cache):
        """Test next task query with server error."""
        branch_id = "branch-uuid-123"
        
        mock_cache = Mock()
        mock_cache.get_next_task.return_value = None
        mock_get_cache.return_value = mock_cache
        
        mock_client = Mock()
        mock_client.get_next_recommended_task.side_effect = Exception("Server error")
        mock_get_client.return_value = mock_client
        
        result = query_mcp_next_task(branch_id)
        
        assert result is None


class TestGitBranchContext:
    """Unit tests for git branch context functionality."""
    
    @patch('session_start.get_session_cache')
    @patch('subprocess.run')
    def test_get_git_branch_context_success(self, mock_run, mock_get_cache):
        """Test successful git branch context retrieval."""
        mock_cache = Mock()
        mock_cache.get_git_status.return_value = None  # Cache miss
        mock_get_cache.return_value = mock_cache
        
        # Mock subprocess calls
        mock_branch = Mock(returncode=0, stdout="feature/auth\n")
        mock_status = Mock(returncode=0, stdout="M auth.py\n?? test.py\n")
        mock_log = Mock(returncode=0, stdout="abc123 Add auth\ndef456 Fix bug\n")
        
        mock_run.side_effect = [mock_branch, mock_status, mock_log]
        
        result = get_git_branch_context()
        
        expected = {
            "branch": "feature/auth",
            "uncommitted_changes": 2,
            "recent_commits": ["abc123 Add auth", "def456 Fix bug"],
            "git_branch_id": None
        }
        
        assert result == expected
        mock_cache.cache_git_status.assert_called_once_with(expected)
    
    @patch('session_start.get_session_cache')
    def test_get_git_branch_context_cache_hit(self, mock_get_cache):
        """Test git branch context with cache hit."""
        cached_context = {
            "branch": "cached/branch",
            "uncommitted_changes": 1,
            "recent_commits": ["cached commit"],
            "git_branch_id": "cached-id"
        }
        
        mock_cache = Mock()
        mock_cache.get_git_status.return_value = cached_context
        mock_get_cache.return_value = mock_cache
        
        result = get_git_branch_context()
        
        assert result == cached_context
        mock_cache.get_git_status.assert_called_once()
    
    @patch('session_start.get_session_cache')
    @patch('subprocess.run', side_effect=Exception("Git error"))
    def test_get_git_branch_context_git_error(self, mock_run, mock_get_cache):
        """Test git branch context with git command error."""
        mock_cache = Mock()
        mock_cache.get_git_status.return_value = None
        mock_get_cache.return_value = mock_cache
        
        result = get_git_branch_context()
        
        assert result is None


class TestFormatMCPContext:
    """Unit tests for MCP context formatting."""
    
    def test_format_mcp_context_full_data(self):
        """Test formatting with all context data available."""
        tasks = [
            {"id": "task1", "title": "Task One", "status": "todo", "priority": "high"},
            {"id": "task2", "title": "Task Two", "status": "in_progress", "priority": "medium"}
        ]
        
        next_task = {
            "id": "next1", 
            "title": "Next Task", 
            "description": "This is a description of the next task that needs to be completed"
        }
        
        git_context = {
            "branch": "main",
            "uncommitted_changes": 3,
            "recent_commits": ["abc123 Recent commit", "def456 Another commit"]
        }
        
        result = format_mcp_context(tasks, next_task, git_context)
        
        assert "📋 **Current Pending Tasks:**" in result
        assert "1. ⚪ 🔴 Task One" in result
        assert "2. 🔵 🟡 Task Two" in result
        assert "Task ID: task1" in result
        assert "🎯 **Next Recommended Task:**" in result
        assert "• Next Task" in result
        assert "Description: This is a description" in result
        assert "🌿 **Git Status:**" in result
        assert "• Branch: main" in result
        assert "• Uncommitted changes: 3 files" in result
        assert "• Recent commits:" in result
        assert "  - abc123 Recent commit" in result
    
    def test_format_mcp_context_minimal_data(self):
        """Test formatting with minimal context data."""
        tasks = [{"title": "Minimal Task"}]  # Missing optional fields
        next_task = {"title": "Minimal Next"}
        git_context = {"branch": "minimal"}
        
        result = format_mcp_context(tasks, next_task, git_context)
        
        assert "📋 **Current Pending Tasks:**" in result
        assert "1. ⚫ ⚫ Minimal Task" in result  # Default status/priority emojis
        assert "🎯 **Next Recommended Task:**" in result
        assert "• Minimal Next" in result
        assert "🌿 **Git Status:**" in result
        assert "• Branch: minimal" in result
    
    def test_format_mcp_context_no_data(self):
        """Test formatting with no context data."""
        result = format_mcp_context(None, None, None)
        
        assert result == ""
    
    def test_format_mcp_context_long_description_truncation(self):
        """Test description truncation for long descriptions."""
        next_task = {
            "title": "Task with Long Description",
            "description": "x" * 250  # Longer than 200 char limit
        }
        
        result = format_mcp_context(None, next_task, None)
        
        assert "Description: " + "x" * 200 + "..." in result
    
    def test_format_mcp_context_task_limit(self):
        """Test task display limit (should show only top 3)."""
        tasks = [
            {"title": f"Task {i}", "status": "todo", "priority": "medium"}
            for i in range(5)
        ]
        
        result = format_mcp_context(tasks, None, None)
        
        # Should only show first 3 tasks
        assert "1. ⚪ 🟡 Task 0" in result
        assert "2. ⚪ 🟡 Task 1" in result
        assert "3. ⚪ 🟡 Task 2" in result
        assert "Task 3" not in result
        assert "Task 4" not in result


class TestLoadDevelopmentContext:
    """Unit tests for development context loading."""
    
    @patch('session_start.get_git_branch_context')
    @patch('session_start.query_mcp_pending_tasks')
    @patch('session_start.get_default_client')
    @patch('session_start.get_recent_issues')
    @patch('pathlib.Path.exists')
    def test_load_development_context_full_scenario(self, mock_exists, mock_issues, 
                                                   mock_client, mock_tasks, mock_git):
        """Test full development context loading scenario."""
        # Mock all data sources
        mock_git.return_value = {"branch": "main", "uncommitted_changes": 2}
        mock_tasks.return_value = [{"id": "task1", "title": "Test Task"}]
        mock_issues.return_value = "Recent issues data"
        mock_exists.return_value = True
        
        # Mock file reading
        mock_context_content = "## Project Context\nThis is test context"
        with patch('builtins.open', mock_open(read_data=mock_context_content)):
            result = load_development_context("startup")
        
        assert "🚀 INITIALIZATION REQUIRED" in result
        assert "call_agent('master-orchestrator-agent')" in result
        assert "Session source: startup" in result
        assert "=== MCP LIVE CONTEXT ===" in result
        assert "📋 **Current Pending Tasks:**" in result
        assert "=== STATIC PROJECT CONTEXT ===" in result
        assert "--- Recent GitHub Issues ---" in result
        assert "--- Context Generation Stats ---" in result
    
    @patch('session_start.get_git_branch_context')
    @patch('session_start.query_mcp_pending_tasks')
    @patch('session_start.get_recent_issues')
    @patch('pathlib.Path.exists')
    def test_load_development_context_mcp_unavailable(self, mock_exists, mock_issues, 
                                                     mock_tasks, mock_git):
        """Test context loading when MCP is unavailable."""
        mock_git.return_value = None
        mock_tasks.return_value = None
        mock_issues.return_value = None
        mock_exists.return_value = False
        
        result = load_development_context("startup")
        
        assert "🚀 INITIALIZATION REQUIRED" in result
        assert "⚠️ **MCP Status:** Server unavailable or no active tasks" in result
        assert "--- Context Generation Stats ---" in result
        assert "MCP tasks loaded: 0" in result
        assert "Git context: ❌" in result
    
    @patch('session_start.get_git_branch_context')
    @patch('session_start.query_mcp_pending_tasks')
    def test_load_development_context_performance_stats(self, mock_tasks, mock_git):
        """Test context generation performance statistics."""
        mock_git.return_value = {"branch": "test"}
        mock_tasks.return_value = [{"task": "1"}, {"task": "2"}]
        
        with patch('session_start.get_recent_issues', return_value=None):
            with patch('pathlib.Path.exists', return_value=False):
                result = load_development_context("resume")
        
        assert "--- Context Generation Stats ---" in result
        assert "MCP tasks loaded: 2" in result
        assert "Git context: ✅" in result
        assert "Static files: 0" in result


class TestMainFunction:
    """Unit tests for main function and CLI interface."""
    
    def test_main_help_output(self):
        """Test main function help output."""
        with patch('sys.argv', ['session_start.py', '--help']):
            with pytest.raises(SystemExit):
                with patch('argparse.ArgumentParser.print_help'):
                    main()
    
    @patch('sys.stdin')
    @patch('session_start.log_session_start')
    @patch('session_start.load_development_context')
    def test_main_normal_execution(self, mock_load_context, mock_log, mock_stdin):
        """Test normal main execution flow."""
        input_data = {
            "session_id": "test-123",
            "source": "startup"
        }
        mock_stdin.read.return_value = json.dumps(input_data)
        mock_load_context.return_value = "Test context loaded"
        
        with patch('sys.argv', ['session_start.py']):
            with patch('builtins.print') as mock_print:
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                assert exc_info.value.code == 0
                mock_log.assert_called_once_with(input_data)
                mock_load_context.assert_called_once_with("startup")
                
                # Verify JSON output
                print_call = mock_print.call_args[0][0]
                output_data = json.loads(print_call)
                assert "hookSpecificOutput" in output_data
                assert output_data["hookSpecificOutput"]["additionalContext"] == "Test context loaded"
    
    @patch('sys.stdin')
    def test_main_empty_input(self, mock_stdin):
        """Test main function with empty input."""
        mock_stdin.read.return_value = ""
        
        with patch('sys.argv', ['session_start.py']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 0
    
    @patch('sys.stdin')
    def test_main_invalid_json_input(self, mock_stdin):
        """Test main function with invalid JSON input."""
        mock_stdin.read.return_value = "invalid json"
        
        with patch('sys.argv', ['session_start.py']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 0
    
    @patch('session_start.get_default_client')
    def test_main_test_mcp_option(self, mock_get_client):
        """Test main function with --test-mcp option."""
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_client.query_pending_tasks.return_value = [{"test": "task"}]
        mock_get_client.return_value = mock_client
        
        with patch('sys.argv', ['session_start.py', '--test-mcp']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 0
            mock_client.authenticate.assert_called_once()
            mock_client.query_pending_tasks.assert_called_once_with(limit=1)
    
    @patch('session_start.get_session_cache')
    def test_main_cache_stats_option(self, mock_get_cache):
        """Test main function with --cache-stats option."""
        mock_cache = Mock()
        mock_cache.get_cache_stats.return_value = {
            "total_files": 5,
            "valid_files": 3,
            "expired_files": 2
        }
        mock_get_cache.return_value = mock_cache
        
        with patch('sys.argv', ['session_start.py', '--cache-stats']):
            with patch('builtins.print') as mock_print:
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                assert exc_info.value.code == 0
                
                # Verify stats output
                stats_output = mock_print.call_args[0][0]
                stats_data = json.loads(stats_output)
                assert stats_data["total_files"] == 5
                assert stats_data["valid_files"] == 3