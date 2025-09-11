"""
Test Fixtures for MCP Auto-Injection Testing

Provides reusable fixtures, mocks, and test utilities for MCP auto-injection
system testing across unit, integration, and end-to-end test suites.

Fixtures Categories:
- Mock Servers (Keycloak, MCP)
- Test Data Generators
- Environment Setup
- Performance Testing Utilities
- Validation Helpers
"""

import pytest
import json
import time
import tempfile
import subprocess
import threading
from pathlib import Path
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import requests


@pytest.fixture(scope="session")
def test_data_generator():
    """Generate consistent test data across all test suites."""
    class TestDataGenerator:
        def __init__(self):
            self.counter = 0
            self.base_timestamp = datetime.now()
        
        def generate_task(self, **overrides):
            """Generate test task with consistent structure."""
            self.counter += 1
            base_task = {
                "id": f"test-task-{self.counter}",
                "title": f"Test Task {self.counter}",
                "description": f"Description for test task {self.counter}",
                "status": "todo",
                "priority": "medium",
                "created_at": (self.base_timestamp + timedelta(minutes=self.counter)).isoformat(),
                "updated_at": (self.base_timestamp + timedelta(minutes=self.counter + 1)).isoformat(),
                "assignees": ["@test-agent"],
                "labels": ["test", "auto-injection"],
                "estimated_effort": "2 hours"
            }
            base_task.update(overrides)
            return base_task
        
        def generate_task_list(self, count: int, **base_overrides):
            """Generate list of test tasks."""
            return [self.generate_task(**base_overrides) for _ in range(count)]
        
        def generate_git_context(self, **overrides):
            """Generate test git context."""
            base_git = {
                "branch": "test-main",
                "uncommitted_changes": 2,
                "recent_commits": [
                    f"abc123{self.counter} Test commit {self.counter}",
                    f"def456{self.counter} Another test commit"
                ],
                "git_branch_id": f"git-branch-{self.counter}"
            }
            base_git.update(overrides)
            return base_git
        
        def generate_project_context(self, **overrides):
            """Generate test project context."""
            base_project = {
                "project_id": f"test-proj-{self.counter}",
                "name": f"Test Project {self.counter}",
                "environment": "test",
                "status": "active",
                "dependencies": ["dep1", "dep2"]
            }
            base_project.update(overrides)
            return base_project
        
        def generate_session_input(self, **overrides):
            """Generate test session input."""
            self.counter += 1
            base_input = {
                "session_id": f"test-session-{self.counter}",
                "source": "startup",
                "timestamp": datetime.now().isoformat(),
                "user_id": f"test-user-{self.counter}"
            }
            base_input.update(overrides)
            return base_input
    
    return TestDataGenerator()


@pytest.fixture(scope="function")
def mock_keycloak_server():
    """Comprehensive mock Keycloak server for authentication testing."""
    class MockKeycloakServer:
        def __init__(self):
            self.token_counter = 0
            self.issued_tokens = {}
            self.server_available = True
            self.response_delay = 0.0
            self.error_rate = 0.0
            self.client_secrets = {
                "claude-hooks": "test-secret-123",
                "test-client": "test-secret-456"
            }
        
        def configure_behavior(self, 
                             server_available: bool = True,
                             response_delay: float = 0.0,
                             error_rate: float = 0.0):
            """Configure server behavior for testing."""
            self.server_available = server_available
            self.response_delay = response_delay
            self.error_rate = error_rate
        
        def issue_token(self, client_id: str, client_secret: str) -> Dict[str, Any]:
            """Issue JWT token with realistic behavior."""
            import random
            
            if not self.server_available:
                raise requests.exceptions.ConnectionError("Keycloak server unavailable")
            
            time.sleep(self.response_delay)
            
            if random.random() < self.error_rate:
                raise requests.exceptions.Timeout("Token request timeout")
            
            # Validate client credentials
            expected_secret = self.client_secrets.get(client_id)
            if not expected_secret or client_secret != expected_secret:
                return {
                    "error": "invalid_client",
                    "error_description": "Invalid client credentials"
                }
            
            # Generate token
            self.token_counter += 1
            token_id = f"mock-jwt-{self.token_counter}"
            expires_in = 3600
            
            token_data = {
                "token_id": token_id,
                "client_id": client_id,
                "issued_at": datetime.now(),
                "expires_at": datetime.now() + timedelta(seconds=expires_in),
                "scopes": ["openid", "profile", "email"]
            }
            
            self.issued_tokens[token_id] = token_data
            
            return {
                "access_token": token_id,
                "expires_in": expires_in,
                "token_type": "Bearer",
                "scope": "openid profile email",
                "refresh_token": f"refresh-{token_id}"
            }
        
        def validate_token(self, token: str) -> bool:
            """Validate issued token."""
            token_data = self.issued_tokens.get(token)
            if not token_data:
                return False
            
            return datetime.now() < token_data["expires_at"]
        
        def get_token_info(self, token: str) -> Optional[Dict]:
            """Get token information."""
            return self.issued_tokens.get(token)
        
        def revoke_token(self, token: str) -> bool:
            """Revoke token."""
            if token in self.issued_tokens:
                del self.issued_tokens[token]
                return True
            return False
        
        def get_stats(self) -> Dict[str, Any]:
            """Get server statistics."""
            active_tokens = sum(1 for token_data in self.issued_tokens.values()
                              if datetime.now() < token_data["expires_at"])
            
            return {
                "total_tokens_issued": self.token_counter,
                "active_tokens": active_tokens,
                "expired_tokens": len(self.issued_tokens) - active_tokens,
                "server_available": self.server_available
            }
    
    return MockKeycloakServer()


@pytest.fixture(scope="function")
def mock_mcp_server():
    """Comprehensive mock MCP server for testing."""
    class MockMCPServer:
        def __init__(self):
            self.request_counter = 0
            self.response_times = []
            self.server_available = True
            self.response_delay = 0.0
            self.error_rate = 0.0
            
            # Initialize test data
            self._init_test_data()
        
        def _init_test_data(self):
            """Initialize realistic test data."""
            self.projects = {
                "proj-1": {
                    "id": "proj-1",
                    "name": "Test Project Alpha",
                    "description": "Primary test project",
                    "status": "active",
                    "created_at": datetime.now().isoformat()
                },
                "proj-2": {
                    "id": "proj-2", 
                    "name": "Test Project Beta",
                    "description": "Secondary test project",
                    "status": "active",
                    "created_at": datetime.now().isoformat()
                }
            }
            
            self.git_branches = {
                "branch-1": {
                    "id": "branch-1",
                    "name": "main",
                    "project_id": "proj-1",
                    "description": "Main development branch"
                },
                "branch-2": {
                    "id": "branch-2",
                    "name": "feature/test-suite",
                    "project_id": "proj-1",
                    "description": "Test suite development"
                },
                "branch-3": {
                    "id": "branch-3",
                    "name": "main",
                    "project_id": "proj-2",
                    "description": "Main branch for project 2"
                }
            }
            
            self.tasks = {
                "task-1": {
                    "id": "task-1",
                    "title": "Implement Authentication",
                    "description": "Add JWT-based authentication system",
                    "status": "todo",
                    "priority": "high",
                    "git_branch_id": "branch-1",
                    "project_id": "proj-1",
                    "assignees": ["@coding-agent", "@security-auditor-agent"],
                    "estimated_effort": "3 days"
                },
                "task-2": {
                    "id": "task-2",
                    "title": "Add Unit Tests",
                    "description": "Comprehensive unit test coverage",
                    "status": "in_progress",
                    "priority": "medium",
                    "git_branch_id": "branch-2",
                    "project_id": "proj-1",
                    "assignees": ["@test-orchestrator-agent"],
                    "estimated_effort": "2 days"
                },
                "task-3": {
                    "id": "task-3",
                    "title": "Performance Optimization",
                    "description": "Optimize system performance",
                    "status": "blocked",
                    "priority": "low",
                    "git_branch_id": "branch-1",
                    "project_id": "proj-1",
                    "assignees": ["@performance-load-tester-agent"],
                    "estimated_effort": "1 week"
                }
            }
            
            self.contexts = {}
        
        def configure_behavior(self,
                             server_available: bool = True,
                             response_delay: float = 0.0,
                             error_rate: float = 0.0):
            """Configure server behavior."""
            self.server_available = server_available
            self.response_delay = response_delay
            self.error_rate = error_rate
        
        def add_test_task(self, task_data: Dict[str, Any]) -> str:
            """Add task to test data."""
            task_id = task_data.get("id", f"task-{len(self.tasks) + 1}")
            self.tasks[task_id] = task_data
            return task_id
        
        def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
            """Update existing task."""
            if task_id in self.tasks:
                self.tasks[task_id].update(updates)
                return True
            return False
        
        def handle_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
            """Handle mock MCP request with realistic behavior."""
            import random
            
            start_time = time.time()
            
            if not self.server_available:
                raise requests.exceptions.ConnectionError("MCP server unavailable")
            
            time.sleep(self.response_delay)
            
            if random.random() < self.error_rate:
                error_types = [
                    requests.exceptions.ConnectionError("Connection failed"),
                    requests.exceptions.Timeout("Request timeout"),
                    requests.exceptions.HTTPError("Server error")
                ]
                raise random.choice(error_types)
            
            self.request_counter += 1
            
            try:
                response = self._route_request(endpoint, payload)
                response_time = time.time() - start_time
                self.response_times.append(response_time)
                return response
            except Exception as e:
                response_time = time.time() - start_time
                self.response_times.append(response_time)
                return {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
        
        def _route_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
            """Route request to appropriate handler."""
            if endpoint == "manage_task":
                return self._handle_task_request(payload)
            elif endpoint == "manage_project":
                return self._handle_project_request(payload)
            elif endpoint == "manage_git_branch":
                return self._handle_git_branch_request(payload)
            elif endpoint == "manage_context":
                return self._handle_context_request(payload)
            else:
                return {
                    "success": False,
                    "error": f"Unknown endpoint: {endpoint}"
                }
        
        def _handle_task_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
            """Handle task management requests."""
            action = payload.get("action")
            
            if action == "list":
                return self._list_tasks(payload)
            elif action == "next":
                return self._get_next_task(payload)
            elif action == "get":
                return self._get_task(payload)
            elif action == "create":
                return self._create_task(payload)
            elif action == "update":
                return self._update_task(payload)
            else:
                return {
                    "success": False,
                    "error": f"Unknown task action: {action}"
                }
        
        def _list_tasks(self, payload: Dict[str, Any]) -> Dict[str, Any]:
            """List tasks with filtering."""
            status_filter = payload.get("status", "").split(",") if payload.get("status") else []
            git_branch_id = payload.get("git_branch_id")
            project_id = payload.get("project_id")
            limit = payload.get("limit", 50)
            
            filtered_tasks = []
            for task in self.tasks.values():
                # Apply filters
                if status_filter and task["status"] not in status_filter:
                    continue
                if git_branch_id and task.get("git_branch_id") != git_branch_id:
                    continue
                if project_id and task.get("project_id") != project_id:
                    continue
                
                filtered_tasks.append(task.copy())
            
            # Apply limit
            filtered_tasks = filtered_tasks[:limit]
            
            return {
                "success": True,
                "data": {"tasks": filtered_tasks},
                "metadata": {
                    "total_count": len(filtered_tasks),
                    "filtered": bool(status_filter or git_branch_id or project_id)
                }
            }
        
        def _get_next_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
            """Get next recommended task."""
            git_branch_id = payload.get("git_branch_id")
            
            # Find highest priority todo task for branch
            candidates = []
            for task in self.tasks.values():
                if (task.get("git_branch_id") == git_branch_id and
                    task["status"] == "todo"):
                    candidates.append(task)
            
            if not candidates:
                return {"success": True, "data": None}
            
            # Sort by priority (high > medium > low)
            priority_order = {"high": 3, "medium": 2, "low": 1}
            candidates.sort(key=lambda t: priority_order.get(t["priority"], 0), reverse=True)
            
            return {"success": True, "data": candidates[0].copy()}
        
        def _get_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
            """Get specific task."""
            task_id = payload.get("task_id")
            task = self.tasks.get(task_id)
            
            if task:
                return {"success": True, "data": task.copy()}
            else:
                return {"success": False, "error": "Task not found"}
        
        def _create_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
            """Create new task."""
            task_id = f"task-{len(self.tasks) + 1}"
            task_data = {
                "id": task_id,
                "title": payload.get("title", "New Task"),
                "description": payload.get("description", ""),
                "status": payload.get("status", "todo"),
                "priority": payload.get("priority", "medium"),
                "git_branch_id": payload.get("git_branch_id"),
                "project_id": payload.get("project_id"),
                "assignees": payload.get("assignees", []),
                "created_at": datetime.now().isoformat()
            }
            
            self.tasks[task_id] = task_data
            return {"success": True, "data": task_data}
        
        def _update_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
            """Update existing task."""
            task_id = payload.get("task_id")
            task = self.tasks.get(task_id)
            
            if not task:
                return {"success": False, "error": "Task not found"}
            
            # Update fields
            updateable_fields = ["title", "description", "status", "priority", "assignees"]
            for field in updateable_fields:
                if field in payload:
                    task[field] = payload[field]
            
            task["updated_at"] = datetime.now().isoformat()
            
            return {"success": True, "data": task.copy()}
        
        def _handle_project_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
            """Handle project requests."""
            action = payload.get("action", "list")
            
            if action == "list":
                return {"success": True, "data": {"projects": list(self.projects.values())}}
            else:
                return {"success": False, "error": f"Unknown project action: {action}"}
        
        def _handle_git_branch_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
            """Handle git branch requests."""
            action = payload.get("action", "list")
            
            if action == "list":
                project_id = payload.get("project_id")
                branches = []
                
                for branch in self.git_branches.values():
                    if not project_id or branch.get("project_id") == project_id:
                        branches.append(branch.copy())
                
                return {"success": True, "data": {"git_branches": branches}}
            else:
                return {"success": False, "error": f"Unknown branch action: {action}"}
        
        def _handle_context_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
            """Handle context requests."""
            action = payload.get("action", "get")
            context_id = payload.get("context_id")
            level = payload.get("level", "task")
            
            if action == "get":
                context_key = f"{level}_{context_id}"
                context_data = self.contexts.get(context_key, {})
                return {"success": True, "data": context_data}
            elif action == "update":
                context_key = f"{level}_{context_id}"
                self.contexts[context_key] = payload.get("data", {})
                return {"success": True, "data": self.contexts[context_key]}
            else:
                return {"success": False, "error": f"Unknown context action: {action}"}
        
        def get_stats(self) -> Dict[str, Any]:
            """Get server statistics."""
            return {
                "request_count": self.request_counter,
                "avg_response_time": sum(self.response_times) / len(self.response_times) if self.response_times else 0,
                "max_response_time": max(self.response_times) if self.response_times else 0,
                "min_response_time": min(self.response_times) if self.response_times else 0,
                "total_tasks": len(self.tasks),
                "total_projects": len(self.projects),
                "total_branches": len(self.git_branches),
                "server_available": self.server_available
            }
        
        def reset_stats(self):
            """Reset server statistics."""
            self.request_counter = 0
            self.response_times = []
    
    return MockMCPServer()


@pytest.fixture(scope="function")
def temp_cache_environment():
    """Temporary cache environment for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir) / "test_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        yield {
            "cache_dir": cache_dir,
            "temp_dir": Path(temp_dir)
        }


@pytest.fixture(scope="function")
def temp_git_repository():
    """Temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)
        
        # Initialize repository
        subprocess.run(['git', 'init'], cwd=repo_path, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo_path, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=repo_path, capture_output=True, check=True)
        
        # Create initial content
        (repo_path / "README.md").write_text("# Test Repository\n\nThis is a test repository for MCP auto-injection testing.")
        (repo_path / "src" / "main.py").parent.mkdir(parents=True, exist_ok=True)
        (repo_path / "src" / "main.py").write_text('print("Hello, World!")')
        
        # Initial commit
        subprocess.run(['git', 'add', '.'], cwd=repo_path, capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=repo_path, capture_output=True, check=True)
        
        # Create test branch
        subprocess.run(['git', 'checkout', '-b', 'feature/test'], cwd=repo_path, capture_output=True, check=True)
        (repo_path / "tests" / "test_main.py").parent.mkdir(parents=True, exist_ok=True)
        (repo_path / "tests" / "test_main.py").write_text('def test_example():\n    assert True')
        subprocess.run(['git', 'add', 'tests/'], cwd=repo_path, capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'Add test file'], cwd=repo_path, capture_output=True, check=True)
        
        # Return to main branch
        subprocess.run(['git', 'checkout', 'main'], cwd=repo_path, capture_output=True, check=True)
        
        yield repo_path


@pytest.fixture(scope="function")  
def performance_monitor():
    """Performance monitoring utilities for tests."""
    class PerformanceMonitor:
        def __init__(self):
            self.measurements = {}
            self.thresholds = {
                "session_start": 2.0,  # 2 seconds
                "cache_operation": 0.01,  # 10ms
                "mcp_request": 0.5,  # 500ms
                "auth_request": 1.0,  # 1 second
            }
        
        def start_measurement(self, operation: str) -> str:
            """Start performance measurement."""
            measurement_id = f"{operation}_{int(time.time() * 1000)}"
            self.measurements[measurement_id] = {
                "operation": operation,
                "start_time": time.time(),
                "end_time": None,
                "duration": None
            }
            return measurement_id
        
        def end_measurement(self, measurement_id: str) -> float:
            """End performance measurement and return duration."""
            if measurement_id not in self.measurements:
                raise ValueError(f"Measurement {measurement_id} not found")
            
            measurement = self.measurements[measurement_id]
            measurement["end_time"] = time.time()
            measurement["duration"] = measurement["end_time"] - measurement["start_time"]
            
            return measurement["duration"]
        
        def measure_operation(self, operation: str):
            """Context manager for measuring operations."""
            class MeasurementContext:
                def __init__(self, monitor, op):
                    self.monitor = monitor
                    self.operation = op
                    self.measurement_id = None
                
                def __enter__(self):
                    self.measurement_id = self.monitor.start_measurement(self.operation)
                    return self
                
                def __exit__(self, exc_type, exc_val, exc_tb):
                    self.duration = self.monitor.end_measurement(self.measurement_id)
            
            return MeasurementContext(self, operation)
        
        def check_performance(self, operation: str, duration: float) -> bool:
            """Check if operation meets performance threshold."""
            threshold = self.thresholds.get(operation)
            if threshold is None:
                return True
            return duration <= threshold
        
        def get_summary(self) -> Dict[str, Any]:
            """Get performance measurement summary."""
            completed_measurements = {
                mid: m for mid, m in self.measurements.items()
                if m["duration"] is not None
            }
            
            if not completed_measurements:
                return {"total_measurements": 0, "operations": {}}
            
            # Group by operation
            operations = {}
            for measurement in completed_measurements.values():
                op = measurement["operation"]
                if op not in operations:
                    operations[op] = {
                        "count": 0,
                        "total_duration": 0,
                        "durations": [],
                        "threshold": self.thresholds.get(op),
                        "threshold_violations": 0
                    }
                
                operations[op]["count"] += 1
                operations[op]["total_duration"] += measurement["duration"]
                operations[op]["durations"].append(measurement["duration"])
                
                if not self.check_performance(op, measurement["duration"]):
                    operations[op]["threshold_violations"] += 1
            
            # Calculate statistics
            for op_data in operations.values():
                durations = op_data["durations"]
                op_data["avg_duration"] = sum(durations) / len(durations)
                op_data["min_duration"] = min(durations)
                op_data["max_duration"] = max(durations)
                
                # Calculate percentiles
                sorted_durations = sorted(durations)
                n = len(sorted_durations)
                if n >= 4:
                    op_data["p95_duration"] = sorted_durations[int(n * 0.95)]
                    op_data["p99_duration"] = sorted_durations[int(n * 0.99)]
            
            return {
                "total_measurements": len(completed_measurements),
                "operations": operations
            }
    
    return PerformanceMonitor()


@pytest.fixture(scope="function")
def validation_helpers():
    """Validation helper utilities for test assertions."""
    class ValidationHelpers:
        @staticmethod
        def validate_context_structure(context: str) -> Dict[str, bool]:
            """Validate session context structure."""
            validations = {
                "has_initialization": "🚀 INITIALIZATION REQUIRED" in context,
                "has_call_agent": "call_agent('@master_orchestrator_agent')" in context,
                "has_session_source": "Session source:" in context,
                "has_mcp_context": "=== MCP LIVE CONTEXT ===" in context or "⚠️ **MCP Status:**" in context,
                "has_git_context": "🌿 **Git Status:**" in context,
                "has_context_stats": "--- Context Generation Stats ---" in context,
                "not_empty": len(context.strip()) > 0,
                "reasonable_length": 100 < len(context) < 10000  # Reasonable bounds
            }
            return validations
        
        @staticmethod
        def validate_mcp_response(response: Dict[str, Any]) -> Dict[str, bool]:
            """Validate MCP server response structure."""
            validations = {
                "has_success_field": "success" in response,
                "is_successful": response.get("success", False),
                "has_data_or_error": "data" in response or "error" in response,
                "proper_structure": isinstance(response, dict)
            }
            
            if response.get("success") and "data" in response:
                data = response["data"]
                validations["data_is_dict_or_list"] = isinstance(data, (dict, list))
                
                if isinstance(data, dict) and "tasks" in data:
                    validations["tasks_is_list"] = isinstance(data["tasks"], list)
                    if data["tasks"]:
                        validations["task_has_id"] = "id" in data["tasks"][0]
                        validations["task_has_title"] = "title" in data["tasks"][0]
            
            return validations
        
        @staticmethod
        def validate_authentication_token(token_response: Dict[str, Any]) -> Dict[str, bool]:
            """Validate authentication token response."""
            validations = {
                "has_access_token": "access_token" in token_response,
                "has_expires_in": "expires_in" in token_response,
                "has_token_type": "token_type" in token_response,
                "token_type_bearer": token_response.get("token_type") == "Bearer",
                "expires_in_positive": isinstance(token_response.get("expires_in"), int) and token_response.get("expires_in") > 0,
                "access_token_string": isinstance(token_response.get("access_token"), str),
                "access_token_not_empty": bool(token_response.get("access_token", "").strip())
            }
            return validations
        
        @staticmethod
        def validate_cache_operation(operation_result: Any, operation_type: str) -> Dict[str, bool]:
            """Validate cache operation results."""
            if operation_type == "set":
                return {
                    "returns_boolean": isinstance(operation_result, bool),
                    "is_successful": operation_result is True
                }
            elif operation_type == "get":
                return {
                    "returns_data_or_none": operation_result is not None or operation_result is None,
                    "not_empty_if_exists": not operation_result or len(str(operation_result)) > 0
                }
            elif operation_type == "delete":
                return {
                    "returns_boolean": isinstance(operation_result, bool),
                    "is_successful": operation_result is True
                }
            else:
                return {"unknown_operation": False}
        
        @staticmethod
        def assert_all_validations(validations: Dict[str, bool], context: str = ""):
            """Assert all validation checks pass."""
            failed_validations = [key for key, passed in validations.items() if not passed]
            
            if failed_validations:
                failure_msg = f"Validation failures{' in ' + context if context else ''}: {', '.join(failed_validations)}"
                failure_details = "\n".join(f"  {key}: {validations[key]}" for key in failed_validations)
                raise AssertionError(f"{failure_msg}\nDetails:\n{failure_details}")
    
    return ValidationHelpers()


# Convenience fixture for common mock combination
@pytest.fixture(scope="function")
def integrated_mock_environment(mock_keycloak_server, mock_mcp_server, temp_cache_environment, test_data_generator):
    """Integrated mock environment with all common components."""
    return {
        "keycloak": mock_keycloak_server,
        "mcp": mock_mcp_server,
        "cache": temp_cache_environment,
        "data_generator": test_data_generator
    }


# Performance testing configuration
@pytest.fixture(scope="session")
def performance_config():
    """Performance testing configuration."""
    return {
        "test_iterations": 10,
        "concurrent_sessions": 5,
        "response_time_targets": {
            "mcp_query": 0.5,
            "cache_hit": 0.01,
            "full_injection": 2.0,
            "auth_request": 1.0
        },
        "max_tokens_per_injection": 100,
        "cache_ttl_test": 1,  # 1 second for testing
        "timeout_test": 5,  # 5 seconds
        "error_rates": {
            "low": 0.05,
            "medium": 0.2,
            "high": 0.5
        }
    }