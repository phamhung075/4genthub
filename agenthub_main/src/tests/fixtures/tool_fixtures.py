"""
Test fixtures for MCP tool testing
Provides reusable test data and mock objects
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import uuid

# Fixed timestamp for test consistency
FIXED_TEST_TIMESTAMP = datetime(2024, 1, 1, 12, 0, 0)

from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.entities.project import Project
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority


class FixtureGenerator:
    """Generator for test fixtures"""
    
    @staticmethod
    def generate_uuid():
        """Generate a test UUID"""
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_timestamp():
        """Generate a test timestamp"""
        return FIXED_TEST_TIMESTAMP.isoformat()

    @staticmethod
    def generate_future_timestamp(hours=24):
        """Generate a future timestamp"""
        return (FIXED_TEST_TIMESTAMP + timedelta(hours=hours)).isoformat()


@pytest.fixture
def sample_project_data():
    """Sample project data for testing"""
    return {
        "id": "test-project-123",
        "name": "Test Project",
        "description": "A test project for unit testing",
        "git_branch_name": "feature/test-branch",
        "status": "active",
        "created_at": FixtureGenerator.generate_timestamp(),
        "updated_at": FixtureGenerator.generate_timestamp(),
        "git_branchs": ["feature_development", "bug_fixes"]
    }


@pytest.fixture
def sample_project_entity(sample_project_data):
    """Sample project entity for testing"""
    return Project(
        id=sample_project_data["id"],
        name=sample_project_data["name"],
        description=sample_project_data["description"],
        git_branch_name=sample_project_data["git_branch_name"],
        status=sample_project_data["status"]
    )


@pytest.fixture
def sample_task_data():
    """Sample task data for testing"""
    return {
        "id": "test-task-456",
        "title": "Test Task",
        "description": "A test task for unit testing",
        "status": TaskStatus.TODO.value,
        "priority": Priority.medium().value,
        "project_id": "test-project-123",
        "git_branch_name": "feature/test-branch",
        "user_id": "test-user-789",
        "estimated_effort": 5,
        "assignees": ["user1", "user2"],
        "labels": ["testing", "unit-test"],
        "due_date": FixtureGenerator.generate_future_timestamp(72),
        "created_at": FixtureGenerator.generate_timestamp(),
        "updated_at": FixtureGenerator.generate_timestamp(),
        "dependencies": [],
        "subtasks": []
    }


@pytest.fixture
def sample_task_entity(sample_task_data):
    """Sample task entity for testing"""
    return Task(
        id=sample_task_data["id"],
        title=sample_task_data["title"],
        description=sample_task_data["description"],
        status=TaskStatus.TODO,
        priority=Priority.medium(),
        project_id=sample_task_data["project_id"],
        git_branch_name=sample_task_data["git_branch_name"],
        user_id=sample_task_data["user_id"]
    )


@pytest.fixture
def sample_subtask_data():
    """Sample subtask data for testing"""
    return {
        "id": "test-subtask-789",
        "title": "Test Subtask",
        "description": "A test subtask for unit testing",
        "status": TaskStatus.TODO.value,
        "task_id": "test-task-456",
        "order": 1,
        "created_at": FixtureGenerator.generate_timestamp(),
        "updated_at": FixtureGenerator.generate_timestamp()
    }


@pytest.fixture
def sample_subtask_entity(sample_subtask_data):
    """Sample subtask entity for testing"""
    return Subtask(
        id=sample_subtask_data["id"],
        title=sample_subtask_data["title"],
        description=sample_subtask_data["description"],
        status=TaskStatus.TODO,
        task_id=sample_subtask_data["task_id"],
        order=sample_subtask_data["order"]
    )


@pytest.fixture
def sample_agent_data():
    """Sample agent data for testing"""
    return {
        "id": "test-agent-123",
        "name": "Test Agent",
        "description": "A test agent for unit testing",
        "type": "code_generator",
        "version": "1.0.0",
        "capabilities": ["code_generation", "documentation", "testing"],
        "status": "active",
        "configuration": {
            "max_tokens": 4000,
            "temperature": 0.7,
            "model": "gpt-4"
        },
        "created_at": FixtureGenerator.generate_timestamp(),
        "updated_at": FixtureGenerator.generate_timestamp()
    }


@pytest.fixture
def sample_template_data():
    """Sample template data for testing"""
    return {
        "id": "test-template-123",
        "name": "Test Template",
        "description": "A test template for unit testing",
        "type": "task",
        "content": "# {{title}}\n\n{{description}}\n\n## Tasks\n- [ ] {{task_item}}",
        "variables": ["title", "description", "task_item"],
        "agent_type": "task_planner",
        "file_patterns": ["*.md", "*.txt"],
        "version": "1.0.0",
        "tags": ["testing", "template"],
        "created_at": FixtureGenerator.generate_timestamp(),
        "updated_at": FixtureGenerator.generate_timestamp()
    }


@pytest.fixture
def sample_connection_data():
    """Sample connection data for testing"""
    return {
        "connection_id": "test-conn-123",
        "session_id": "test-session-456",
        "status": "connected",
        "connected_at": FixtureGenerator.generate_timestamp(),
        "last_activity": FixtureGenerator.generate_timestamp(),
        "client_info": {
            "client_name": "Test Client",
            "version": "1.0.0",
            "capabilities": ["tools", "resources", "prompts"],
            "user_agent": "TestClient/1.0"
        },
        "metrics": {
            "requests_count": 150,
            "errors_count": 2,
            "average_response_time_ms": 45
        }
    }


@pytest.fixture
def sample_auth_token_data():
    """Sample authentication token data for testing"""
    return {
        "token": "test-token-" + FixtureGenerator.generate_uuid()[:8],
        "user_id": "test-user-789",
        "scopes": ["read", "write", "admin"],
        "expires_at": FixtureGenerator.generate_future_timestamp(24),
        "created_at": FixtureGenerator.generate_timestamp(),
        "token_type": "bearer",
        "is_active": True
    }


@pytest.fixture
def sample_health_check_data():
    """Sample health check data for testing"""
    return {
        "healthy": True,
        "status": "ok",
        "checks": {
            "database": {"status": "ok", "response_time_ms": 15},
            "redis": {"status": "ok", "response_time_ms": 5},
            "file_system": {"status": "ok", "free_space_gb": 50},
            "memory": {"status": "ok", "usage_percent": 65}
        },
        "overall_response_time_ms": 25,
        "timestamp": FixtureGenerator.generate_timestamp(),
        "version": "1.0.0"
    }


@pytest.fixture
def sample_render_result():
    """Sample template render result for testing"""
    return {
        "success": True,
        "template_id": "test-template-123",
        "rendered_content": "# Test Task\n\nThis is a test task description\n\n## Tasks\n- [ ] Implement feature",
        "output_path": "/tmp/test_output.md",
        "variables_used": {
            "title": "Test Task",
            "description": "This is a test task description",
            "task_item": "Implement feature"
        },
        "render_time_ms": 50,
        "timestamp": FixtureGenerator.generate_timestamp()
    }


@pytest.fixture
def sample_agent_call_result():
    """Sample agent call result for testing"""
    return {
        "success": True,
        "agent_name": "test-agent",
        "result": {
            "output": "Agent execution completed successfully",
            "data": {
                "generated_code": "def hello_world():\n    return 'Hello, World!'",
                "documentation": "A simple hello world function"
            },
            "metadata": {
                "execution_time_ms": 1500,
                "tokens_used": 150,
                "model_used": "gpt-4"
            }
        },
        "timestamp": FixtureGenerator.generate_timestamp()
    }


# Mock Facades
@pytest.fixture
def mock_task_facade():
    """Mock task application facade"""
    facade = Mock()
    facade.create_task.return_value = None
    facade.update_task.return_value = None
    facade.get_task.return_value = None
    facade.delete_task.return_value = False
    facade.list_tasks.return_value = []
    facade.search_tasks.return_value = []
    facade.complete_task.return_value = None
    facade.get_next_task.return_value = None
    facade.add_task_dependency.return_value = False
    facade.remove_task_dependency.return_value = False
    return facade


@pytest.fixture
def mock_project_facade():
    """Mock project application facade"""
    facade = Mock()
    facade.create_project.return_value = None
    facade.update_project.return_value = None
    facade.get_project.return_value = None
    facade.delete_project.return_value = False
    facade.list_projects.return_value = []
    facade.add_git_branch.return_value = False
    facade.remove_git_branch.return_value = False
    return facade


@pytest.fixture
def mock_subtask_facade():
    """Mock subtask application facade"""
    facade = Mock()
    facade.add_subtask.return_value = None
    facade.complete_subtask.return_value = None
    facade.list_subtasks.return_value = []
    facade.update_subtask.return_value = None
    facade.remove_subtask.return_value = False
    return facade


@pytest.fixture
def mock_agent_facade():
    """Mock agent application facade"""
    facade = Mock()
    facade.list_agents.return_value = []
    facade.get_agent.return_value = None
    facade.validate_agent.return_value = {"valid": True, "issues": []}
    facade.search_agents.return_value = []
    return facade


@pytest.fixture
def mock_call_agent_facade():
    """Mock call agent application facade"""
    facade = Mock()
    facade.call_agent.return_value = {"success": False, "error": "Not implemented"}
    facade.validate_agent_exists.return_value = False
    return facade


@pytest.fixture
def mock_template_facade():
    """Mock template application facade"""
    facade = Mock()
    facade.render_template.return_value = {"success": False, "error": "Not implemented"}
    facade.list_templates.return_value = []
    facade.validate_template.return_value = {"valid": True, "issues": []}
    facade.suggest_templates.return_value = []
    facade.manage_cache.return_value = {"operation": "stats", "success": True}
    facade.get_template_metrics.return_value = {"total_renders": 0}
    facade.register_template.return_value = {"success": False}
    facade.update_template.return_value = {"success": False}
    facade.delete_template.return_value = False
    return facade


@pytest.fixture
def mock_connection_facade():
    """Mock connection application facade"""
    facade = Mock()
    facade.perform_health_check.return_value = {"healthy": True, "status": "ok"}
    facade.get_server_capabilities.return_value = {"tools": [], "resources": []}
    facade.get_connection_health.return_value = {"healthy": True}
    facade.get_server_status.return_value = {"server_status": "running"}
    facade.register_status_updates.return_value = {"success": False}
    return facade


# Test data collections
@pytest.fixture
def task_status_values():
    """All valid task status values"""
    return ["todo", "in_progress", "completed", "cancelled"]


@pytest.fixture
def task_priority_values():
    """All valid task priority values"""
    return ["low", "medium", "high", "urgent"]


@pytest.fixture
def project_status_values():
    """All valid project status values"""
    return ["active", "inactive", "archived", "completed"]


@pytest.fixture
def template_types():
    """All valid template types"""
    return ["task", "code", "documentation", "test", "configuration"]


@pytest.fixture
def agent_types():
    """All valid agent types"""
    return ["code_generator", "task_planner", "documentation_writer", "test_generator", "reviewer"]


@pytest.fixture
def cache_operations():
    """All valid cache operations"""
    return ["clear", "stats", "refresh", "size", "cleanup"]


# Utility fixtures
@pytest.fixture
def common_test_params():
    """Common test parameters used across multiple tests"""
    return {
        "project_id": "test-project-123",
        "git_branch_name": "feature/test-branch",
        "user_id": "test-user-789",
        "task_id": "test-task-456",
        "id": "test-subtask-789",
        "agent_id": "test-agent-123",
        "template_id": "test-template-123",
        "connection_id": "test-conn-123",
        "session_id": "test-session-456"
    }


@pytest.fixture
def error_scenarios():
    """Common error scenarios for testing"""
    return {
        "database_error": Exception("Database connection failed"),
        "validation_error": ValueError("Invalid input data"),
        "not_found_error": Exception("Resource not found"),
        "permission_error": Exception("Permission denied"),
        "timeout_error": Exception("Operation timed out")
    }


# Performance testing fixtures
@pytest.fixture
def performance_metrics():
    """Sample performance metrics for testing"""
    return {
        "response_time_ms": 45,
        "memory_usage_mb": 256,
        "cpu_usage_percent": 15.5,
        "requests_per_second": 100,
        "error_rate_percent": 0.1
    }


# Parameterized fixtures
@pytest.fixture(params=["todo", "in_progress", "completed", "cancelled"])
def task_status(request):
    """Parameterized task status fixture"""
    return request.param


@pytest.fixture(params=["low", "medium", "high", "urgent"])
def task_priority(request):
    """Parameterized task priority fixture"""
    return request.param


@pytest.fixture(params=["active", "inactive", "archived"])
def project_status(request):
    """Parameterized project status fixture"""
    return request.param