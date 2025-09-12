"""
Pytest Configuration and Shared Fixtures for MCP Controller Tests

This module provides shared fixtures and configuration for all MCP controller tests.
It includes common test data, mock setups, and reusable testing utilities.
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, Optional, List

# Import common dependencies that need to be mocked across tests
from fastmcp.task_management.application.services.facade_service import FacadeService
from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade
from fastmcp.task_management.application.facades.project_application_facade import ProjectApplicationFacade
from fastmcp.task_management.application.facades.git_branch_application_facade import GitBranchApplicationFacade
from fastmcp.task_management.interface.utils.response_formatter import StandardResponseFormatter


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Common Test Data Fixtures
@pytest.fixture
def sample_user_id():
    """Sample authenticated user ID for testing."""
    return "test-user-12345"


@pytest.fixture
def sample_project_id():
    """Sample project ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_git_branch_id():
    """Sample git branch ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_task_id():
    """Sample task ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_subtask_id():
    """Sample subtask ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def current_timestamp():
    """Current timestamp for testing."""
    return datetime.now(timezone.utc)


@pytest.fixture
def sample_project_data(sample_project_id, current_timestamp):
    """Comprehensive sample project data for testing."""
    return {
        "project_id": sample_project_id,
        "name": "Test Project",
        "description": "A comprehensive test project for unit testing",
        "status": "active",
        "created_at": current_timestamp.isoformat(),
        "updated_at": current_timestamp.isoformat(),
        "git_branches": [],
        "tasks_count": 0,
        "health_status": "healthy",
        "settings": {
            "auto_cleanup": True,
            "retention_days": 30
        }
    }


@pytest.fixture
def sample_git_branch_data(sample_git_branch_id, sample_project_id, current_timestamp):
    """Comprehensive sample git branch data for testing."""
    return {
        "git_branch_id": sample_git_branch_id,
        "project_id": sample_project_id,
        "git_branch_name": "feature/test-branch",
        "git_branch_description": "Test branch for unit testing",
        "status": "active",
        "created_at": current_timestamp.isoformat(),
        "updated_at": current_timestamp.isoformat(),
        "tasks": [],
        "tasks_count": 0,
        "assigned_agents": ["coding-agent"],
        "statistics": {
            "total_tasks": 0,
            "completed_tasks": 0,
            "progress_percentage": 0
        }
    }


@pytest.fixture
def sample_task_data(sample_task_id, sample_git_branch_id, current_timestamp):
    """Comprehensive sample task data for testing."""
    return {
        "task_id": sample_task_id,
        "git_branch_id": sample_git_branch_id,
        "title": "Test Task",
        "description": "A comprehensive test task for unit testing",
        "status": "todo",
        "priority": "medium",
        "details": "Detailed implementation notes for the test task",
        "estimated_effort": "2 hours",
        "assignees": ["coding-agent", "@test-orchestrator-agent"],
        "labels": ["backend", "api", "unit-test"],
        "due_date": "2024-12-31T23:59:59Z",
        "dependencies": [],
        "subtasks": [],
        "created_at": current_timestamp.isoformat(),
        "updated_at": current_timestamp.isoformat(),
        "progress_percentage": 0,
        "completion_summary": None,
        "testing_notes": None
    }


@pytest.fixture
def sample_subtask_data(sample_subtask_id, sample_task_id, current_timestamp):
    """Comprehensive sample subtask data for testing."""
    return {
        "subtask_id": sample_subtask_id,
        "task_id": sample_task_id,
        "title": "Test Subtask",
        "description": "A test subtask for unit testing",
        "status": "todo",
        "priority": "medium",
        "assignees": ["coding-agent"],
        "progress_notes": "Starting implementation",
        "progress_percentage": 0,
        "blockers": [],
        "insights_found": [],
        "created_at": current_timestamp.isoformat(),
        "updated_at": current_timestamp.isoformat()
    }


# Mock Service Fixtures
@pytest.fixture
def mock_facade_service():
    """Mock FacadeService with all facade types."""
    mock_service = Mock(spec=FacadeService)
    
    # Create mock facades
    task_facade = Mock(spec=TaskApplicationFacade)
    project_facade = Mock(spec=ProjectApplicationFacade)
    git_branch_facade = Mock(spec=GitBranchApplicationFacade)
    
    # Configure all facade methods as async mocks
    # Task facade methods
    task_facade.create_task = AsyncMock()
    task_facade.get_task = AsyncMock()
    task_facade.update_task = AsyncMock()
    task_facade.delete_task = AsyncMock()
    task_facade.list_tasks = AsyncMock()
    task_facade.search_tasks = AsyncMock()
    task_facade.complete_task = AsyncMock()
    task_facade.add_dependency = AsyncMock()
    task_facade.remove_dependency = AsyncMock()
    task_facade.get_next_task = AsyncMock()
    
    # Project facade methods
    project_facade.create_project = AsyncMock()
    project_facade.get_project = AsyncMock()
    project_facade.get_project_by_name = AsyncMock()
    project_facade.update_project = AsyncMock()
    project_facade.list_projects = AsyncMock()
    project_facade.project_health_check = AsyncMock()
    project_facade.cleanup_obsolete = AsyncMock()
    project_facade.validate_integrity = AsyncMock()
    project_facade.rebalance_agents = AsyncMock()
    
    # Git branch facade methods
    git_branch_facade.create_git_branch = AsyncMock()
    git_branch_facade.get_git_branch = AsyncMock()
    git_branch_facade.update_git_branch = AsyncMock()
    git_branch_facade.delete_git_branch = AsyncMock()
    git_branch_facade.list_git_branches = AsyncMock()
    git_branch_facade.assign_agent = AsyncMock()
    git_branch_facade.unassign_agent = AsyncMock()
    git_branch_facade.get_statistics = AsyncMock()
    git_branch_facade.archive = AsyncMock()
    git_branch_facade.restore = AsyncMock()
    
    # Configure facade service to return appropriate facades
    mock_service.get_task_facade.return_value = task_facade
    mock_service.get_project_facade.return_value = project_facade
    mock_service.get_git_branch_facade.return_value = git_branch_facade
    
    return mock_service, {
        "task": task_facade,
        "project": project_facade,
        "git_branch": git_branch_facade
    }


@pytest.fixture
def mock_authentication(sample_user_id):
    """Mock authentication functions for all controllers."""
    def create_auth_mock(controller_module_path):
        """Create authentication mock for specific controller module."""
        return patch(f'{controller_module_path}.get_authenticated_user_id'), \
               patch(f'{controller_module_path}.log_authentication_details')
    
    return create_auth_mock


@pytest.fixture
def mock_permissions():
    """Mock permission system for all controllers."""
    def create_permission_mock(controller_module_path, permissions=None):
        """Create permission mock for specific controller module with given permissions."""
        if permissions is None:
            # Default permissions for all operations
            permissions = [
                "tasks:read", "tasks:write", "tasks:create", "tasks:update", "tasks:delete",
                "projects:read", "projects:write", "projects:create", "projects:update", "projects:delete",
                "branches:read", "branches:write", "branches:create", "branches:update", "branches:delete",
                "contexts:read", "contexts:write", "contexts:create", "contexts:update", "contexts:delete",
                "agents:read", "agents:write", "agents:create", "agents:update", "agents:delete"
            ]
        
        def configure_mock_context():
            mock_request_context = Mock()
            mock_user = Mock()
            mock_user.token = {"sub": "test-user", "permissions": permissions}
            mock_request_context.user = mock_user
            return mock_request_context
        
        return patch(f'{controller_module_path}.get_current_request_context', 
                    return_value=configure_mock_context())
    
    return create_permission_mock


@pytest.fixture
def response_formatter():
    """Standard response formatter for testing."""
    return StandardResponseFormatter()


# Test Data Generators
@pytest.fixture
def create_test_task():
    """Factory function to create test task data with variations."""
    def _create_task(
        task_id: Optional[str] = None,
        git_branch_id: Optional[str] = None,
        title: str = "Test Task",
        status: str = "todo",
        priority: str = "medium",
        assignees: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        return {
            "task_id": task_id or str(uuid.uuid4()),
            "git_branch_id": git_branch_id or str(uuid.uuid4()),
            "title": title,
            "description": f"Description for {title}",
            "status": status,
            "priority": priority,
            "assignees": assignees or ["coding-agent"],
            "labels": ["test"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    return _create_task


@pytest.fixture
def create_test_project():
    """Factory function to create test project data with variations."""
    def _create_project(
        project_id: Optional[str] = None,
        name: str = "Test Project",
        status: str = "active"
    ) -> Dict[str, Any]:
        return {
            "project_id": project_id or str(uuid.uuid4()),
            "name": name,
            "description": f"Description for {name}",
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    return _create_project


# Mock Response Builders
@pytest.fixture
def create_success_response():
    """Factory to create successful API responses."""
    def _create_response(data: Any = None, message: str = "Operation successful") -> Dict[str, Any]:
        return {
            "success": True,
            "data": data,
            "message": message
        }
    return _create_response


@pytest.fixture
def create_error_response():
    """Factory to create error API responses."""
    def _create_response(error: str, error_code: str = "OPERATION_FAILED") -> Dict[str, Any]:
        return {
            "success": False,
            "error": error,
            "error_code": error_code
        }
    return _create_response


# Common Test Utilities
@pytest.fixture
def assert_response_structure():
    """Utility to validate response structure."""
    def _assert_structure(response: Dict[str, Any], expect_success: bool = True):
        """Validate that response has proper structure."""
        assert "success" in response
        assert response["success"] is expect_success
        
        if expect_success:
            assert "data" in response or "message" in response
        else:
            assert "error" in response
            assert "error_code" in response
    
    return _assert_structure


# Parametrized Test Data
@pytest.fixture
def valid_task_statuses():
    """List of valid task status values for parametrized tests."""
    return ["todo", "in_progress", "blocked", "review", "testing", "done", "cancelled"]


@pytest.fixture
def valid_priorities():
    """List of valid priority values for parametrized tests."""
    return ["low", "medium", "high", "urgent", "critical"]


@pytest.fixture
def valid_agent_types():
    """List of valid agent types for parametrized tests."""
    return [
        "coding-agent", "@test-orchestrator-agent", "code-reviewer-agent",
        "@security-auditor-agent", "@performance-load-tester-agent", 
        "devops-agent", "documentation-agent"
    ]


# Async Test Helpers
@pytest.fixture
def run_async():
    """Helper to run async functions in tests."""
    def _run_async(coro):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    return _run_async


# Error Injection Fixtures
@pytest.fixture
def inject_facade_error():
    """Utility to inject errors in facade methods for testing error handling."""
    def _inject_error(facade_mock, method_name: str, error: Exception):
        """Configure facade method to raise specified error."""
        method = getattr(facade_mock, method_name)
        method.side_effect = error
    return _inject_error


# Database State Fixtures
@pytest.fixture
def mock_database_state():
    """Mock database state for testing without actual database."""
    return {
        "projects": {},
        "git_branches": {},
        "tasks": {},
        "subtasks": {},
        "contexts": {}
    }


@pytest.fixture
def cleanup_test_data():
    """Cleanup fixture to ensure tests don't interfere with each other."""
    yield  # Run the test
    # Cleanup logic would go here if needed