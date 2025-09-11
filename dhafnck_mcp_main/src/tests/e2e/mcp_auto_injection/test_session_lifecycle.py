"""
End-to-End Tests for Session Lifecycle

Tests complete session lifecycle scenarios from initialization through
context injection to cleanup, simulating real user workflows.

Test Coverage:
- Complete session start-to-finish workflows
- Multi-session concurrent scenarios
- Context persistence across session changes
- Recovery from various failure modes
- Performance under realistic load
- Real git repository integration
"""

import pytest
import json
import time
import subprocess
import tempfile
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

# Import session components for E2E testing
import session_start
from utils.mcp_client import get_default_client, ResilientMCPClient
from utils.cache_manager import get_session_cache


@pytest.fixture(scope="function")
def temp_git_repo():
    """Create temporary git repository for E2E testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)
        
        # Initialize git repo
        subprocess.run(['git', 'init'], cwd=repo_path, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo_path, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=repo_path, capture_output=True)
        
        # Create initial commit
        (repo_path / "README.md").write_text("# Test Repository")
        subprocess.run(['git', 'add', 'README.md'], cwd=repo_path, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=repo_path, capture_output=True)
        
        yield repo_path


@pytest.fixture
def mock_keycloak_server():
    """Mock Keycloak server for E2E authentication testing."""
    class MockKeycloakServer:
        def __init__(self):
            self.token_counter = 0
            self.valid_tokens = set()
            self.token_expiry = {}
            self.server_available = True
            self.response_delay = 0.1
        
        def set_server_available(self, available):
            """Control server availability."""
            self.server_available = available
        
        def issue_token(self, client_id, client_secret):
            """Issue new JWT token."""
            if not self.server_available:
                raise ConnectionError("Keycloak server unavailable")
            
            time.sleep(self.response_delay)
            
            self.token_counter += 1
            token = f"mock-jwt-token-{self.token_counter}"
            expires_in = 3600
            
            self.valid_tokens.add(token)
            self.token_expiry[token] = datetime.now() + timedelta(seconds=expires_in)
            
            return {
                "access_token": token,
                "expires_in": expires_in,
                "token_type": "Bearer",
                "scope": "openid"
            }
        
        def validate_token(self, token):
            """Validate token."""
            if token not in self.valid_tokens:
                return False
            
            expiry = self.token_expiry.get(token)
            if expiry and datetime.now() > expiry:
                self.valid_tokens.discard(token)
                return False
            
            return True
    
    return MockKeycloakServer()


@pytest.fixture
def mock_mcp_server():
    """Mock MCP server for E2E testing with realistic behavior."""
    class MockMCPServer:
        def __init__(self):
            self.request_count = 0
            self.response_times = []
            self.error_rate = 0.0
            self.response_delay = 0.05
            self.server_available = True
            
            # Realistic test data
            self.projects = {
                "proj-1": {"id": "proj-1", "name": "E2E Test Project", "status": "active"},
            }
            
            self.git_branches = {
                "branch-1": {"id": "branch-1", "name": "main", "project_id": "proj-1"},
                "branch-2": {"id": "branch-2", "name": "feature/e2e-test", "project_id": "proj-1"},
            }
            
            self.tasks = {
                "task-1": {
                    "id": "task-1", 
                    "title": "E2E Test Task 1", 
                    "status": "todo", 
                    "priority": "high",
                    "git_branch_id": "branch-1",
                    "description": "Complete end-to-end test task"
                },
                "task-2": {
                    "id": "task-2", 
                    "title": "E2E Test Task 2", 
                    "status": "in_progress", 
                    "priority": "medium",
                    "git_branch_id": "branch-1",
                    "description": "Another test task for validation"
                },
                "task-3": {
                    "id": "task-3", 
                    "title": "Feature Task", 
                    "status": "todo", 
                    "priority": "low",
                    "git_branch_id": "branch-2",
                    "description": "Task for feature branch"
                }
            }
        
        def configure_behavior(self, error_rate=0.0, response_delay=0.05, server_available=True):
            """Configure server behavior."""
            self.error_rate = error_rate
            self.response_delay = response_delay
            self.server_available = server_available
        
        def handle_request(self, endpoint, payload):
            """Handle mock MCP request."""
            import random
            
            if not self.server_available:
                raise ConnectionError("MCP server unavailable")
            
            start_time = time.time()
            
            # Simulate network delay
            time.sleep(self.response_delay)
            
            # Simulate errors
            if random.random() < self.error_rate:
                raise ConnectionError("Simulated server error")
            
            self.request_count += 1
            
            try:
                response = self._route_request(endpoint, payload)
                response_time = time.time() - start_time
                self.response_times.append(response_time)
                return response
            except Exception as e:
                response_time = time.time() - start_time
                self.response_times.append(response_time)
                raise
        
        def _route_request(self, endpoint, payload):
            """Route request to appropriate handler."""
            if endpoint == "manage_task":
                return self._handle_task_request(payload)
            elif endpoint == "manage_project":
                return self._handle_project_request(payload)
            elif endpoint == "manage_git_branch":
                return self._handle_branch_request(payload)
            else:
                return {"success": False, "error": f"Unknown endpoint: {endpoint}"}
        
        def _handle_task_request(self, payload):
            """Handle task management requests."""
            action = payload.get("action")
            
            if action == "list":
                status_filter = payload.get("status", "").split(",")
                filtered_tasks = []
                
                for task in self.tasks.values():
                    if not status_filter or task["status"] in status_filter:
                        filtered_tasks.append(task.copy())
                
                # Apply limit
                limit = payload.get("limit", len(filtered_tasks))
                filtered_tasks = filtered_tasks[:limit]
                
                return {"success": True, "data": {"tasks": filtered_tasks}}
            
            elif action == "next":
                git_branch_id = payload.get("git_branch_id")
                
                # Find next task for branch
                for task in self.tasks.values():
                    if (task.get("git_branch_id") == git_branch_id and 
                        task["status"] == "todo"):
                        return {"success": True, "data": task.copy()}
                
                return {"success": True, "data": None}
            
            elif action == "get":
                task_id = payload.get("task_id")
                task = self.tasks.get(task_id)
                
                if task:
                    return {"success": True, "data": task.copy()}
                else:
                    return {"success": False, "error": "Task not found"}
            
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        
        def _handle_project_request(self, payload):
            """Handle project requests."""
            action = payload.get("action")
            
            if action == "list":
                return {"success": True, "data": {"projects": list(self.projects.values())}}
            else:
                return {"success": False, "error": f"Unknown project action: {action}"}
        
        def _handle_branch_request(self, payload):
            """Handle git branch requests."""
            action = payload.get("action")
            
            if action == "list":
                project_id = payload.get("project_id")
                filtered_branches = []
                
                for branch in self.git_branches.values():
                    if not project_id or branch.get("project_id") == project_id:
                        filtered_branches.append(branch.copy())
                
                return {"success": True, "data": {"git_branches": filtered_branches}}
            else:
                return {"success": False, "error": f"Unknown branch action: {action}"}
        
        def get_stats(self):
            """Get server statistics."""
            return {
                "request_count": self.request_count,
                "avg_response_time": sum(self.response_times) / len(self.response_times) if self.response_times else 0,
                "max_response_time": max(self.response_times) if self.response_times else 0
            }
    
    return MockMCPServer()


class TestCompleteSessionLifecycle:
    """Test complete session lifecycle scenarios."""
    
    def test_session_startup_complete_workflow(self, temp_git_repo, mock_keycloak_server, mock_mcp_server):
        """Test complete session startup workflow from initialization to context injection."""
        # Change to temp repo directory for realistic git operations
        original_cwd = Path.cwd()
        
        try:
            import os
            os.chdir(temp_git_repo)
            
            # Mock authentication
            with patch('requests.post') as mock_keycloak_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_keycloak_server.issue_token("claude-hooks", "test-secret")
                mock_keycloak_post.return_value = mock_response
                
                # Mock MCP server
                with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_mcp_request:
                    mock_mcp_request.side_effect = lambda endpoint, data: mock_mcp_server.handle_request(endpoint, data)
                    
                    # Simulate session start input
                    session_input = {
                        "session_id": "e2e-test-session-123",
                        "source": "startup",
                        "timestamp": datetime.now().isoformat(),
                        "user_id": "test-user"
                    }
                    
                    # Mock stdin for main function
                    with patch('sys.stdin') as mock_stdin:
                        mock_stdin.read.return_value = json.dumps(session_input)
                        
                        with patch('sys.argv', ['session_start.py', '--load-context']):
                            with patch('builtins.print') as mock_print:
                                with pytest.raises(SystemExit) as exc_info:
                                    session_start.main()
                                
                                assert exc_info.value.code == 0
                    
                    # Verify output was generated
                    assert mock_print.called
                    output_json = mock_print.call_args[0][0]
                    output_data = json.loads(output_json)
                    
                    # Verify structure
                    assert "hookSpecificOutput" in output_data
                    hook_output = output_data["hookSpecificOutput"]
                    assert "additionalContext" in hook_output
                    assert "metadata" in hook_output
                    
                    context = hook_output["additionalContext"]
                    
                    # Verify required context elements
                    assert "🚀 INITIALIZATION REQUIRED" in context
                    assert "call_agent('master-orchestrator-agent')" in context
                    assert "Session source: startup" in context
                    
                    # Verify MCP integration
                    if mock_mcp_server.request_count > 0:
                        assert "=== MCP LIVE CONTEXT ===" in context
                        assert "📋 **Current Pending Tasks:**" in context
                    
                    # Verify git integration
                    assert "🌿 **Git Status:**" in context
                    assert "Branch: main" in context  # From temp repo
                    
                    # Verify metadata
                    metadata = hook_output["metadata"]
                    assert metadata["session_id"] == "e2e-test-session-123"
                    assert metadata["source"] == "startup"
                    assert metadata["mcp_enabled"] is True
                    
                    print(f"Session startup test: {mock_mcp_server.request_count} MCP requests")
                    print(f"Keycloak auth attempts: {mock_keycloak_post.call_count}")
                    print(f"Context length: {len(context)} characters")
        
        finally:
            os.chdir(original_cwd)
    
    def test_session_resume_with_cached_context(self, temp_git_repo, mock_keycloak_server, mock_mcp_server):
        """Test session resume using cached context data."""
        original_cwd = Path.cwd()
        
        try:
            import os
            os.chdir(temp_git_repo)
            
            # First session - populate cache
            with patch('requests.post') as mock_keycloak_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_keycloak_server.issue_token("claude-hooks", "test-secret")
                mock_keycloak_post.return_value = mock_response
                
                with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_mcp_request:
                    mock_mcp_request.side_effect = lambda endpoint, data: mock_mcp_server.handle_request(endpoint, data)
                    
                    # First session
                    cache = get_session_cache()
                    
                    # Load initial context
                    context1 = session_start.load_development_context("startup")
                    
                    initial_requests = mock_mcp_server.request_count
                    assert initial_requests > 0
                    
                    # Brief pause to simulate session work
                    time.sleep(0.1)
                    
                    # Second session (resume) - should use cache more
                    context2 = session_start.load_development_context("resume")
                    
                    final_requests = mock_mcp_server.request_count
                    
                    # Both contexts should contain valid data
                    assert "=== MCP LIVE CONTEXT ===" in context1
                    assert "=== MCP LIVE CONTEXT ===" in context2 or "⚠️ **MCP Status:**" in context2
                    
                    # Cache should reduce server requests for second session
                    print(f"Initial session requests: {initial_requests}")
                    print(f"Resume session total requests: {final_requests}")
                    print(f"Resume session new requests: {final_requests - initial_requests}")
                    
                    # Verify cache is working (fewer requests for resume)
                    assert final_requests <= initial_requests + 2, "Cache not reducing server requests effectively"
        
        finally:
            os.chdir(original_cwd)
    
    def test_session_clear_fresh_start(self, temp_git_repo, mock_keycloak_server, mock_mcp_server):
        """Test session clear with fresh context loading."""
        original_cwd = Path.cwd()
        
        try:
            import os
            os.chdir(temp_git_repo)
            
            with patch('requests.post') as mock_keycloak_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_keycloak_server.issue_token("claude-hooks", "test-secret")
                mock_keycloak_post.return_value = mock_response
                
                with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_mcp_request:
                    mock_mcp_request.side_effect = lambda endpoint, data: mock_mcp_server.handle_request(endpoint, data)
                    
                    # Clear any existing cache
                    cache = get_session_cache()
                    cache.clear_all()
                    
                    # Fresh session
                    context = session_start.load_development_context("clear")
                    
                    # Verify fresh context is loaded
                    assert "Session source: clear" in context
                    assert "🚀 INITIALIZATION REQUIRED" in context
                    
                    # Should have made server requests for fresh data
                    assert mock_mcp_server.request_count > 0
                    
                    print(f"Fresh session requests: {mock_mcp_server.request_count}")
        
        finally:
            os.chdir(original_cwd)


class TestMultiSessionConcurrency:
    """Test concurrent session scenarios."""
    
    def test_concurrent_session_starts(self, temp_git_repo, mock_keycloak_server, mock_mcp_server):
        """Test multiple sessions starting concurrently."""
        original_cwd = Path.cwd()
        
        try:
            import os
            os.chdir(temp_git_repo)
            
            # Configure for concurrent load
            mock_mcp_server.configure_behavior(response_delay=0.1, error_rate=0.1)
            
            def start_session(session_id):
                """Start a session and return results."""
                session_start_time = time.time()
                
                try:
                    with patch('requests.post') as mock_keycloak_post:
                        mock_response = Mock()
                        mock_response.status_code = 200
                        mock_response.json.return_value = mock_keycloak_server.issue_token("claude-hooks", f"secret-{session_id}")
                        mock_keycloak_post.return_value = mock_response
                        
                        with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_mcp_request:
                            mock_mcp_request.side_effect = lambda endpoint, data: mock_mcp_server.handle_request(endpoint, data)
                            
                            # Load context for this session
                            context = session_start.load_development_context("startup")
                            
                            session_duration = time.time() - session_start_time
                            
                            return {
                                "session_id": session_id,
                                "success": True,
                                "duration": session_duration,
                                "context_length": len(context),
                                "has_mcp_context": "=== MCP LIVE CONTEXT ===" in context,
                                "has_git_context": "🌿 **Git Status:**" in context,
                                "auth_calls": mock_keycloak_post.call_count,
                                "mcp_requests": mock_mcp_request.call_count
                            }
                
                except Exception as e:
                    return {
                        "session_id": session_id,
                        "success": False,
                        "duration": time.time() - session_start_time,
                        "error": str(e)
                    }
            
            # Run concurrent sessions
            concurrent_sessions = 5
            with ThreadPoolExecutor(max_workers=concurrent_sessions) as executor:
                futures = [
                    executor.submit(start_session, i) 
                    for i in range(concurrent_sessions)
                ]
                results = [future.result() for future in as_completed(futures)]
            
            # Analyze results
            successful_sessions = [r for r in results if r["success"]]
            failed_sessions = [r for r in results if not r["success"]]
            
            assert len(successful_sessions) >= concurrent_sessions * 0.8, "Too many concurrent sessions failed"
            
            # Performance analysis
            if successful_sessions:
                avg_duration = sum(r["duration"] for r in successful_sessions) / len(successful_sessions)
                max_duration = max(r["duration"] for r in successful_sessions)
                
                assert avg_duration < 2.0, f"Concurrent sessions too slow: {avg_duration:.2f}s average"
                assert max_duration < 5.0, f"Slowest session too slow: {max_duration:.2f}s"
                
                # Content verification
                sessions_with_mcp = sum(1 for r in successful_sessions if r["has_mcp_context"])
                sessions_with_git = sum(1 for r in successful_sessions if r["has_git_context"])
                
                assert sessions_with_git == len(successful_sessions), "Not all sessions got git context"
                
                print(f"Concurrent sessions: {len(successful_sessions)}/{concurrent_sessions} successful")
                print(f"Average duration: {avg_duration:.3f}s, Max: {max_duration:.3f}s")
                print(f"Sessions with MCP context: {sessions_with_mcp}")
                print(f"Total MCP server requests: {mock_mcp_server.request_count}")
                
                # Print failed sessions for debugging
                for failed in failed_sessions:
                    print(f"Failed session {failed['session_id']}: {failed.get('error', 'Unknown')}")
        
        finally:
            os.chdir(original_cwd)
    
    def test_session_handoff_context_persistence(self, temp_git_repo, mock_keycloak_server, mock_mcp_server):
        """Test context persistence across session handoffs."""
        original_cwd = Path.cwd()
        
        try:
            import os
            os.chdir(temp_git_repo)
            
            session_timeline = []
            
            with patch('requests.post') as mock_keycloak_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_keycloak_server.issue_token("claude-hooks", "test-secret")
                mock_keycloak_post.return_value = mock_response
                
                with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_mcp_request:
                    mock_mcp_request.side_effect = lambda endpoint, data: mock_mcp_server.handle_request(endpoint, data)
                    
                    # Session 1: Initial work session
                    start_time = time.time()
                    context1 = session_start.load_development_context("startup")
                    session_timeline.append({
                        "session": 1,
                        "type": "startup",
                        "duration": time.time() - start_time,
                        "requests": mock_mcp_server.request_count
                    })
                    
                    # Simulate some work (cache should be populated)
                    cache = get_session_cache()
                    
                    # Check what's cached
                    cached_tasks = cache.get_pending_tasks()
                    cached_git = cache.get_git_status()
                    
                    print(f"After session 1 - Cached tasks: {cached_tasks is not None}")
                    print(f"After session 1 - Cached git: {cached_git is not None}")
                    
                    # Session 2: Resume (should benefit from cache)
                    time.sleep(0.1)
                    start_time = time.time()
                    context2 = session_start.load_development_context("resume")
                    session2_requests = mock_mcp_server.request_count - session_timeline[0]["requests"]
                    session_timeline.append({
                        "session": 2,
                        "type": "resume",
                        "duration": time.time() - start_time,
                        "requests": session2_requests
                    })
                    
                    # Session 3: Context switch (different branch simulation)
                    time.sleep(0.1)
                    start_time = time.time()
                    
                    # Simulate branch change
                    with patch('subprocess.run') as mock_git:
                        mock_branch = Mock(returncode=0, stdout="feature/new-branch\n")
                        mock_status = Mock(returncode=0, stdout="")
                        mock_log = Mock(returncode=0, stdout="xyz789 Feature commit\n")
                        mock_git.side_effect = [mock_branch, mock_status, mock_log]
                        
                        context3 = session_start.load_development_context("resume")
                    
                    session3_requests = mock_mcp_server.request_count - sum(s["requests"] for s in session_timeline)
                    session_timeline.append({
                        "session": 3,
                        "type": "branch_switch",
                        "duration": time.time() - start_time,
                        "requests": session3_requests
                    })
                    
                    # Verify context persistence and efficiency
                    for i, context in enumerate([context1, context2, context3], 1):
                        assert "🚀 INITIALIZATION REQUIRED" in context, f"Session {i} missing init instruction"
                        assert "🌿 **Git Status:**" in context, f"Session {i} missing git context"
                    
                    # Cache should reduce requests over time
                    assert session_timeline[1]["requests"] <= session_timeline[0]["requests"], "Resume session not using cache effectively"
                    
                    # All sessions should complete reasonably quickly
                    max_duration = max(s["duration"] for s in session_timeline)
                    assert max_duration < 1.0, f"Session too slow: {max_duration:.3f}s"
                    
                    print("Session handoff timeline:")
                    for session in session_timeline:
                        print(f"  Session {session['session']} ({session['type']}): "
                              f"{session['duration']:.3f}s, {session['requests']} requests")
        
        finally:
            os.chdir(original_cwd)


class TestErrorRecoveryScenarios:
    """Test error recovery and fallback scenarios."""
    
    def test_mcp_server_outage_recovery(self, temp_git_repo, mock_keycloak_server, mock_mcp_server):
        """Test recovery from MCP server outage."""
        original_cwd = Path.cwd()
        
        try:
            import os
            os.chdir(temp_git_repo)
            
            recovery_timeline = []
            
            with patch('requests.post') as mock_keycloak_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_keycloak_server.issue_token("claude-hooks", "test-secret")
                mock_keycloak_post.return_value = mock_response
                
                # Phase 1: Normal operation
                mock_mcp_server.configure_behavior(server_available=True)
                
                with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_mcp_request:
                    mock_mcp_request.side_effect = lambda endpoint, data: mock_mcp_server.handle_request(endpoint, data)
                    
                    start_time = time.time()
                    context1 = session_start.load_development_context("startup")
                    recovery_timeline.append({
                        "phase": "normal_operation",
                        "duration": time.time() - start_time,
                        "mcp_requests": mock_mcp_server.request_count,
                        "has_mcp_context": "=== MCP LIVE CONTEXT ===" in context1
                    })
                    
                    # Verify normal operation
                    assert recovery_timeline[0]["has_mcp_context"], "Normal operation should have MCP context"
                    
                    # Phase 2: Server outage
                    mock_mcp_server.configure_behavior(server_available=False)
                    
                    start_time = time.time()
                    try:
                        context2 = session_start.load_development_context("resume")
                        outage_success = True
                    except Exception as e:
                        context2 = f"Error during outage: {str(e)}"
                        outage_success = False
                    
                    recovery_timeline.append({
                        "phase": "server_outage",
                        "duration": time.time() - start_time,
                        "success": outage_success,
                        "fallback_used": "⚠️ **MCP Status:**" in context2 if outage_success else False
                    })
                    
                    # Phase 3: Server recovery
                    mock_mcp_server.configure_behavior(server_available=True)
                    
                    start_time = time.time()
                    context3 = session_start.load_development_context("resume")
                    final_requests = mock_mcp_server.request_count
                    recovery_timeline.append({
                        "phase": "server_recovery",
                        "duration": time.time() - start_time,
                        "mcp_requests": final_requests - recovery_timeline[0]["mcp_requests"],
                        "has_mcp_context": "=== MCP LIVE CONTEXT ===" in context3
                    })
                    
                    # Verify recovery
                    assert recovery_timeline[2]["has_mcp_context"], "Server recovery should restore MCP context"
                    
                    print("MCP server outage recovery timeline:")
                    for phase in recovery_timeline:
                        print(f"  {phase['phase']}: {phase['duration']:.3f}s")
                        if 'mcp_requests' in phase:
                            print(f"    MCP requests: {phase['mcp_requests']}")
                        if 'success' in phase:
                            print(f"    Success: {phase['success']}")
                        if 'fallback_used' in phase:
                            print(f"    Fallback used: {phase['fallback_used']}")
        
        finally:
            os.chdir(original_cwd)
    
    def test_authentication_failure_handling(self, temp_git_repo, mock_keycloak_server, mock_mcp_server):
        """Test handling of authentication failures."""
        original_cwd = Path.cwd()
        
        try:
            import os
            os.chdir(temp_git_repo)
            
            auth_test_timeline = []
            
            # Phase 1: Auth failure
            with patch('requests.post') as mock_keycloak_post:
                mock_response = Mock()
                mock_response.status_code = 401
                mock_response.json.return_value = {"error": "invalid_client"}
                mock_keycloak_post.return_value = mock_response
                
                with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_mcp_request:
                    # Should not make MCP requests due to auth failure
                    mock_mcp_request.side_effect = lambda endpoint, data: mock_mcp_server.handle_request(endpoint, data)
                    
                    start_time = time.time()
                    context1 = session_start.load_development_context("startup")
                    auth_test_timeline.append({
                        "phase": "auth_failure",
                        "duration": time.time() - start_time,
                        "mcp_requests": mock_mcp_request.call_count,
                        "has_mcp_warning": "⚠️ **MCP Status:**" in context1
                    })
                    
                    # Should gracefully handle auth failure
                    assert "🚀 INITIALIZATION REQUIRED" in context1, "Should still provide basic context"
                    assert "🌿 **Git Status:**" in context1, "Should still provide git context"
                    
            # Phase 2: Auth recovery
            with patch('requests.post') as mock_keycloak_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_keycloak_server.issue_token("claude-hooks", "test-secret")
                mock_keycloak_post.return_value = mock_response
                
                with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_mcp_request:
                    mock_mcp_request.side_effect = lambda endpoint, data: mock_mcp_server.handle_request(endpoint, data)
                    
                    start_time = time.time()
                    context2 = session_start.load_development_context("resume")
                    auth_test_timeline.append({
                        "phase": "auth_recovery",
                        "duration": time.time() - start_time,
                        "mcp_requests": mock_mcp_request.call_count,
                        "has_mcp_context": "=== MCP LIVE CONTEXT ===" in context2
                    })
                    
                    # Should recover and provide MCP context
                    assert auth_test_timeline[1]["mcp_requests"] > 0, "Should make MCP requests after auth recovery"
            
            print("Authentication failure handling timeline:")
            for phase in auth_test_timeline:
                print(f"  {phase['phase']}: {phase['duration']:.3f}s, "
                      f"MCP requests: {phase['mcp_requests']}")
        
        finally:
            os.chdir(original_cwd)
    
    def test_partial_failure_resilience(self, temp_git_repo, mock_keycloak_server, mock_mcp_server):
        """Test resilience to partial system failures."""
        original_cwd = Path.cwd()
        
        try:
            import os
            os.chdir(temp_git_repo)
            
            # Configure intermittent failures
            mock_mcp_server.configure_behavior(error_rate=0.3, response_delay=0.1)
            
            resilience_results = []
            
            with patch('requests.post') as mock_keycloak_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_keycloak_server.issue_token("claude-hooks", "test-secret")
                mock_keycloak_post.return_value = mock_response
                
                # Test multiple session attempts under failure conditions
                for attempt in range(5):
                    with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_mcp_request:
                        def resilient_request(endpoint, data):
                            # Implement retry logic in mock
                            max_retries = 3
                            for retry in range(max_retries):
                                try:
                                    return mock_mcp_server.handle_request(endpoint, data)
                                except ConnectionError:
                                    if retry == max_retries - 1:
                                        raise
                                    time.sleep(0.01 * (retry + 1))
                        
                        mock_mcp_request.side_effect = resilient_request
                        
                        start_time = time.time()
                        try:
                            context = session_start.load_development_context("startup")
                            success = True
                            has_mcp_data = "=== MCP LIVE CONTEXT ===" in context
                        except Exception as e:
                            success = False
                            has_mcp_data = False
                            context = str(e)
                        
                        resilience_results.append({
                            "attempt": attempt + 1,
                            "success": success,
                            "duration": time.time() - start_time,
                            "has_mcp_data": has_mcp_data,
                            "mcp_requests": mock_mcp_request.call_count
                        })
            
            # Analyze resilience
            successful_attempts = sum(1 for r in resilience_results if r["success"])
            attempts_with_mcp = sum(1 for r in resilience_results if r["has_mcp_data"])
            
            success_rate = successful_attempts / len(resilience_results)
            mcp_success_rate = attempts_with_mcp / len(resilience_results)
            
            # Should maintain reasonable success rate despite failures
            assert success_rate >= 0.6, f"Success rate too low: {success_rate:.1%}"
            
            avg_duration = sum(r["duration"] for r in resilience_results if r["success"]) / max(successful_attempts, 1)
            assert avg_duration < 2.0, f"Average session time too slow under failures: {avg_duration:.3f}s"
            
            print(f"Partial failure resilience: {successful_attempts}/5 sessions successful ({success_rate:.1%})")
            print(f"MCP data retrieved: {attempts_with_mcp}/5 attempts ({mcp_success_rate:.1%})")
            print(f"Average successful session duration: {avg_duration:.3f}s")
            print(f"Total MCP server requests across all attempts: {mock_mcp_server.request_count}")
        
        finally:
            os.chdir(original_cwd)


@pytest.mark.performance
class TestPerformanceUnderLoad:
    """Test performance characteristics under realistic load."""
    
    def test_session_performance_targets_e2e(self, temp_git_repo, mock_keycloak_server, mock_mcp_server):
        """Test end-to-end session performance targets."""
        original_cwd = Path.cwd()
        
        try:
            import os
            os.chdir(temp_git_repo)
            
            # Configure realistic server delays
            mock_mcp_server.configure_behavior(response_delay=0.05, error_rate=0.05)
            mock_keycloak_server.response_delay = 0.1
            
            performance_metrics = []
            
            with patch('requests.post') as mock_keycloak_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_keycloak_server.issue_token("claude-hooks", "test-secret")
                mock_keycloak_post.return_value = mock_response
                
                # Test multiple sessions for consistent performance
                for test_run in range(10):
                    with patch('utils.mcp_client.MCPHTTPClient._make_request') as mock_mcp_request:
                        mock_mcp_request.side_effect = lambda endpoint, data: mock_mcp_server.handle_request(endpoint, data)
                        
                        # Measure complete session lifecycle
                        start_time = time.time()
                        
                        # Simulate complete main() execution
                        session_input = {
                            "session_id": f"perf-test-{test_run}",
                            "source": "startup",
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        with patch('sys.stdin') as mock_stdin:
                            mock_stdin.read.return_value = json.dumps(session_input)
                            
                            with patch('session_start.log_session_start'):
                                with patch('builtins.print'):
                                    try:
                                        with pytest.raises(SystemExit) as exc_info:
                                            session_start.main()
                                        
                                        session_success = exc_info.value.code == 0
                                    except Exception:
                                        session_success = False
                        
                        total_time = time.time() - start_time
                        
                        performance_metrics.append({
                            "run": test_run + 1,
                            "success": session_success,
                            "total_time": total_time,
                            "mcp_requests": mock_mcp_request.call_count,
                            "auth_requests": mock_keycloak_post.call_count
                        })
            
            # Analyze performance
            successful_runs = [m for m in performance_metrics if m["success"]]
            if successful_runs:
                avg_time = sum(m["total_time"] for m in successful_runs) / len(successful_runs)
                max_time = max(m["total_time"] for m in successful_runs)
                min_time = min(m["total_time"] for m in successful_runs)
                
                # Performance targets
                TARGET_AVG_TIME = 2.0  # 2 seconds average
                TARGET_MAX_TIME = 5.0  # 5 seconds maximum
                
                assert avg_time < TARGET_AVG_TIME, f"Average session time too slow: {avg_time:.3f}s > {TARGET_AVG_TIME}s"
                assert max_time < TARGET_MAX_TIME, f"Maximum session time too slow: {max_time:.3f}s > {TARGET_MAX_TIME}s"
                
                success_rate = len(successful_runs) / len(performance_metrics)
                assert success_rate >= 0.9, f"Success rate too low: {success_rate:.1%}"
                
                print(f"E2E Performance Results ({len(successful_runs)}/{len(performance_metrics)} successful):")
                print(f"  Average time: {avg_time:.3f}s (target: {TARGET_AVG_TIME}s)")
                print(f"  Max time: {max_time:.3f}s (target: {TARGET_MAX_TIME}s)")
                print(f"  Min time: {min_time:.3f}s")
                print(f"  Success rate: {success_rate:.1%}")
                print(f"  Total MCP requests: {mock_mcp_server.request_count}")
                
                # Server performance analysis
                server_stats = mock_mcp_server.get_stats()
                print(f"  MCP Server - Avg response: {server_stats['avg_response_time']:.3f}s")
                print(f"  MCP Server - Max response: {server_stats['max_response_time']:.3f}s")
        
        finally:
            os.chdir(original_cwd)