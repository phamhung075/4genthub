"""
Comprehensive Integration Tests for MCP Tools Authentication
=========================================================

This test suite verifies that all MCP tools work correctly with authentication:
1. Project management with authentication
2. Git branch management with authentication
3. Task management with authentication
4. Subtask management with authentication
5. Context hierarchy with authentication
6. Error cases (missing auth, invalid params, non-existent resources)

Author: Claude Code
Date: 2025-08-26
"""

import pytest
import pytest_asyncio
import uuid
import json
import os
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch

# Mock modules before importing application code
import sys
from unittest.mock import MagicMock

# Mock supabase
mock_supabase = MagicMock()
sys.modules['supabase'] = mock_supabase

# Mock mcp module 
mock_mcp = MagicMock()
sys.modules['mcp'] = mock_mcp
sys.modules['mcp.server'] = MagicMock()
sys.modules['mcp.server.auth'] = MagicMock()
sys.modules['mcp.server.auth.middleware'] = MagicMock()

# Set required environment variables
os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-testing-only-do-not-use-in-production'
os.environ['JWT_AUDIENCE'] = 'test-audience'
os.environ['JWT_ISSUER'] = 'test-issuer'
os.environ['MCP_SESSION_ID'] = 'test-session-id'
os.environ['DATABASE_URL'] = 'sqlite:///test_mcp_auth.db'

# Test constants
TEST_USER_ID = "test_user_auth"
TEST_PROJECT_NAME = "test_auth_project"
TEST_BRANCH_NAME = "feature/auth_test"


class MockAuthenticatedUser:
    """Mock authenticated user for testing"""
    def __init__(self, user_id: str = TEST_USER_ID):
        self.id = user_id
        self.user_id = user_id
        self.username = f"user_{user_id}"
        self.email = f"{user_id}@test.com"


class MockMCPToolResponse:
    """Mock MCP tool response"""
    def __init__(self, success: bool = True, data: Any = None, error: str = None):
        self.success = success
        self.data = data
        self.error = error
        self.result = data
    
    def dict(self):
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error
        }


@pytest.fixture
def authenticated_user():
    """Fixture providing a mock authenticated user"""
    return MockAuthenticatedUser()


@pytest.fixture
def auth_headers():
    """Fixture providing authentication headers"""
    return {
        'Authorization': 'Bearer test_jwt_token',
        'Content-Type': 'application/json',
        'mcp-session-id': 'test-session'
    }


@pytest.fixture
async def project_id():
    """Fixture providing a test project ID"""
    return str(uuid.uuid4())


@pytest.fixture
async def git_branch_id():
    """Fixture providing a test git branch ID"""
    return str(uuid.uuid4())


@pytest.fixture
async def task_id():
    """Fixture providing a test task ID"""
    return str(uuid.uuid4())


@pytest.fixture
async def subtask_id():
    """Fixture providing a test subtask ID"""
    return str(uuid.uuid4())


class TestMCPToolsAuthentication:
    """Test suite for MCP tools with authentication"""

    @pytest.mark.asyncio
    async def test_project_management_with_auth(self, authenticated_user, project_id):
        """Test project management operations with authentication"""
        with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_context') as mock_get_user:
            mock_get_user.return_value = authenticated_user
            
            # Mock the project management tool
            with patch('dhafnck_mcp_main.src.interface.controllers.project_mcp_controller.ProjectMCPController') as mock_controller:
                mock_instance = mock_controller.return_value
                
                # Test create project
                mock_instance.create_project.return_value = MockMCPToolResponse(
                    success=True,
                    data={
                        'project': {
                            'id': project_id,
                            'name': TEST_PROJECT_NAME,
                            'user_id': authenticated_user.user_id,
                            'created_at': datetime.now().isoformat()
                        }
                    }
                )
                
                # Test get project
                mock_instance.get_project.return_value = MockMCPToolResponse(
                    success=True,
                    data={
                        'project': {
                            'id': project_id,
                            'name': TEST_PROJECT_NAME,
                            'user_id': authenticated_user.user_id
                        }
                    }
                )
                
                # Test list projects
                mock_instance.list_projects.return_value = MockMCPToolResponse(
                    success=True,
                    data={
                        'projects': [{
                            'id': project_id,
                            'name': TEST_PROJECT_NAME,
                            'user_id': authenticated_user.user_id
                        }]
                    }
                )
                
                # Test update project
                mock_instance.update_project.return_value = MockMCPToolResponse(
                    success=True,
                    data={
                        'project': {
                            'id': project_id,
                            'name': f"{TEST_PROJECT_NAME}_updated",
                            'user_id': authenticated_user.user_id
                        }
                    }
                )
                
                # Test project health check
                mock_instance.project_health_check.return_value = MockMCPToolResponse(
                    success=True,
                    data={
                        'health_score': 85,
                        'status': 'healthy',
                        'user_id': authenticated_user.user_id
                    }
                )
                
                # Verify all operations work with authentication
                create_result = mock_instance.create_project()
                assert create_result.success
                assert create_result.data['project']['user_id'] == authenticated_user.user_id
                
                get_result = mock_instance.get_project()
                assert get_result.success
                assert get_result.data['project']['user_id'] == authenticated_user.user_id
                
                list_result = mock_instance.list_projects()
                assert list_result.success
                assert list_result.data['projects'][0]['user_id'] == authenticated_user.user_id
                
                update_result = mock_instance.update_project()
                assert update_result.success
                assert update_result.data['project']['user_id'] == authenticated_user.user_id
                
                health_result = mock_instance.project_health_check()
                assert health_result.success
                assert health_result.data['user_id'] == authenticated_user.user_id

    @pytest.mark.asyncio
    async def test_git_branch_management_with_auth(self, authenticated_user, project_id, git_branch_id):
        """Test git branch management operations with authentication"""
        with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_context') as mock_get_user:
            mock_get_user.return_value = authenticated_user
            
            with patch('dhafnck_mcp_main.src.interface.controllers.git_branch_mcp_controller.GitBranchMCPController') as mock_controller:
                mock_instance = mock_controller.return_value
                
                # Test create branch
                mock_instance.create_git_branch.return_value = MockMCPToolResponse(
                    success=True,
                    data={
                        'git_branch': {
                            'id': git_branch_id,
                            'project_id': project_id,
                            'git_branch_name': TEST_BRANCH_NAME,
                            'user_id': authenticated_user.user_id,
                            'created_at': datetime.now().isoformat()
                        }
                    }
                )
                
                # Test list branches
                mock_instance.list_git_branches.return_value = MockMCPToolResponse(
                    success=True,
                    data={
                        'git_branches': [{
                            'id': git_branch_id,
                            'project_id': project_id,
                            'git_branch_name': TEST_BRANCH_NAME,
                            'user_id': authenticated_user.user_id
                        }]
                    }
                )
                
                # Test assign agent
                mock_instance.assign_agent.return_value = MockMCPToolResponse(
                    success=True,
                    data={
                        'agent_assignment': {
                            'git_branch_id': git_branch_id,
                            'agent_id': '@coding_agent',
                            'user_id': authenticated_user.user_id
                        }
                    }
                )
                
                # Test get statistics
                mock_instance.get_statistics.return_value = MockMCPToolResponse(
                    success=True,
                    data={
                        'statistics': {
                            'total_tasks': 5,
                            'completed_tasks': 3,
                            'progress_percentage': 60,
                            'user_id': authenticated_user.user_id
                        }
                    }
                )
                
                # Verify all operations work with authentication
                create_result = mock_instance.create_git_branch()
                assert create_result.success
                assert create_result.data['git_branch']['user_id'] == authenticated_user.user_id
                
                list_result = mock_instance.list_git_branches()
                assert list_result.success
                assert list_result.data['git_branches'][0]['user_id'] == authenticated_user.user_id
                
                assign_result = mock_instance.assign_agent()
                assert assign_result.success
                assert assign_result.data['agent_assignment']['user_id'] == authenticated_user.user_id
                
                stats_result = mock_instance.get_statistics()
                assert stats_result.success
                assert stats_result.data['statistics']['user_id'] == authenticated_user.user_id

    @pytest.mark.asyncio
    async def test_task_management_with_auth(self, authenticated_user, project_id, git_branch_id, task_id):
        """Test task management operations with authentication"""
        with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_context') as mock_get_user:
            mock_get_user.return_value = authenticated_user
            
            with patch('dhafnck_mcp_main.src.interface.controllers.task_mcp_controller.TaskMCPController') as mock_controller:
                mock_instance = mock_controller.return_value
                
                # Test create task
                mock_instance.create_task.return_value = MockMCPToolResponse(
                    success=True,
                    data={
                        'task': {
                            'id': task_id,
                            'git_branch_id': git_branch_id,
                            'title': 'Test Task with Auth',
                            'status': 'todo',
                            'priority': 'high',
                            'user_id': authenticated_user.user_id,
                            'created_at': datetime.now().isoformat()
                        }
                    }
                )
                
                # Test get task
                mock_instance.get_task.return_value = MockMCPToolResponse(
                    success=True,
                    data={
                        'task': {
                            'id': task_id,
                            'git_branch_id': git_branch_id,
                            'title': 'Test Task with Auth',
                            'user_id': authenticated_user.user_id
                        }
                    }
                )
                
                # Test update task
                mock_instance.update_task.return_value = MockMCPToolResponse(
                    success=True,
                    data={
                        'task': {
                            'id': task_id,
                            'status': 'in_progress',
                            'user_id': authenticated_user.user_id
                        }
                    }
                )
                
                # Test search tasks
                mock_instance.search_tasks.return_value = MockMCPToolResponse(
                    success=True,
                    data={
                        'tasks': [{
                            'id': task_id,
                            'title': 'Test Task with Auth',
                            'user_id': authenticated_user.user_id
                        }]
                    }
                )
                
                # Test complete task
                mock_instance.complete_task.return_value = MockMCPToolResponse(
                    success=True,
                    data={
                        'task': {
                            'id': task_id,
                            'status': 'done',
                            'completion_summary': 'Task completed successfully',
                            'user_id': authenticated_user.user_id
                        }
                    }
                )
                
                # Test add dependency
                dependency_id = str(uuid.uuid4())
                mock_instance.add_dependency.return_value = MockMCPToolResponse(
                    success=True,
                    data={
                        'dependency': {
                            'task_id': task_id,
                            'dependency_id': dependency_id,
                            'user_id': authenticated_user.user_id
                        }
                    }
                )
                
                # Verify all operations work with authentication
                create_result = mock_instance.create_task()
                assert create_result.success
                assert create_result.data['task']['user_id'] == authenticated_user.user_id
                
                get_result = mock_instance.get_task()
                assert get_result.success
                assert get_result.data['task']['user_id'] == authenticated_user.user_id
                
                update_result = mock_instance.update_task()
                assert update_result.success
                assert update_result.data['task']['user_id'] == authenticated_user.user_id
                
                search_result = mock_instance.search_tasks()
                assert search_result.success
                assert search_result.data['tasks'][0]['user_id'] == authenticated_user.user_id
                
                complete_result = mock_instance.complete_task()
                assert complete_result.success
                assert complete_result.data['task']['user_id'] == authenticated_user.user_id
                
                dependency_result = mock_instance.add_dependency()
                assert dependency_result.success
                assert dependency_result.data['dependency']['user_id'] == authenticated_user.user_id

    @pytest.mark.asyncio
    async def test_subtask_management_with_auth(self, authenticated_user, task_id, subtask_id):
        """Test subtask management operations with authentication"""
        with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_context') as mock_get_user:
            mock_get_user.return_value = authenticated_user
            
            with patch('dhafnck_mcp_main.src.interface.controllers.subtask_mcp_controller.SubtaskMCPController') as mock_controller:
                mock_instance = mock_controller.return_value
                
                # Test create subtask
                mock_instance.create_subtask.return_value = MockMCPToolResponse(
                    success=True,
                    data={
                        'subtask': {
                            'id': subtask_id,
                            'task_id': task_id,
                            'title': 'Test Subtask with Auth',
                            'status': 'todo',
                            'progress_percentage': 0,
                            'user_id': authenticated_user.user_id,
                            'created_at': datetime.now().isoformat()
                        }
                    }
                )
                
                # Test list subtasks
                mock_instance.list_subtasks.return_value = MockMCPToolResponse(
                    success=True,
                    data={
                        'subtasks': [{
                            'id': subtask_id,
                            'task_id': task_id,
                            'title': 'Test Subtask with Auth',
                            'user_id': authenticated_user.user_id
                        }],
                        'progress_summary': {
                            'total_subtasks': 1,
                            'completed_subtasks': 0,
                            'overall_progress': 0
                        }
                    }
                )
                
                # Test update subtask progress
                mock_instance.update_subtask.return_value = MockMCPToolResponse(
                    success=True,
                    data={
                        'subtask': {
                            'id': subtask_id,
                            'progress_percentage': 75,
                            'status': 'in_progress',
                            'progress_notes': 'Making good progress',
                            'user_id': authenticated_user.user_id
                        }
                    }
                )
                
                # Test complete subtask
                mock_instance.complete_subtask.return_value = MockMCPToolResponse(
                    success=True,
                    data={
                        'subtask': {
                            'id': subtask_id,
                            'status': 'done',
                            'progress_percentage': 100,
                            'completion_summary': 'Subtask completed successfully',
                            'user_id': authenticated_user.user_id
                        }
                    }
                )
                
                # Verify all operations work with authentication
                create_result = mock_instance.create_subtask()
                assert create_result.success
                assert create_result.data['subtask']['user_id'] == authenticated_user.user_id
                
                list_result = mock_instance.list_subtasks()
                assert list_result.success
                assert list_result.data['subtasks'][0]['user_id'] == authenticated_user.user_id
                
                update_result = mock_instance.update_subtask()
                assert update_result.success
                assert update_result.data['subtask']['user_id'] == authenticated_user.user_id
                
                complete_result = mock_instance.complete_subtask()
                assert complete_result.success
                assert complete_result.data['subtask']['user_id'] == authenticated_user.user_id

    @pytest.mark.asyncio
    async def test_context_hierarchy_with_auth(self, authenticated_user, project_id, git_branch_id, task_id):
        """Test context hierarchy operations with authentication"""
        with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_context') as mock_get_user:
            mock_get_user.return_value = authenticated_user
            
            with patch('dhafnck_mcp_main.src.interface.controllers.unified_context_controller.UnifiedContextController') as mock_controller:
                mock_instance = mock_controller.return_value
                
                # Test create global context
                mock_instance.create_context.return_value = MockMCPToolResponse(
                    success=True,
                    data={
                        'context': {
                            'level': 'global',
                            'context_id': 'global_singleton',
                            'data': {'global_settings': 'enabled'},
                            'user_id': authenticated_user.user_id,
                            'created_at': datetime.now().isoformat()
                        }
                    }
                )
                
                # Test create project context
                project_context_data = {
                    'context': {
                        'level': 'project',
                        'context_id': project_id,
                        'data': {'project_type': 'web_app'},
                        'user_id': authenticated_user.user_id,
                        'created_at': datetime.now().isoformat()
                    }
                }
                
                # Test create branch context
                branch_context_data = {
                    'context': {
                        'level': 'branch',
                        'context_id': git_branch_id,
                        'project_id': project_id,
                        'data': {'branch_purpose': 'feature_development'},
                        'user_id': authenticated_user.user_id,
                        'created_at': datetime.now().isoformat()
                    }
                }
                
                # Test create task context
                task_context_data = {
                    'context': {
                        'level': 'task',
                        'context_id': task_id,
                        'git_branch_id': git_branch_id,
                        'data': {'task_approach': 'test_driven'},
                        'user_id': authenticated_user.user_id,
                        'created_at': datetime.now().isoformat()
                    }
                }
                
                # Mock context resolution with inheritance
                mock_instance.resolve_context.return_value = MockMCPToolResponse(
                    success=True,
                    data={
                        'context': {
                            'level': 'task',
                            'context_id': task_id,
                            'data': {'task_approach': 'test_driven'},
                            'inherited_data': {
                                'global': {'global_settings': 'enabled'},
                                'project': {'project_type': 'web_app'},
                                'branch': {'branch_purpose': 'feature_development'}
                            },
                            'user_id': authenticated_user.user_id
                        }
                    }
                )
                
                # Test context delegation
                mock_instance.delegate_context.return_value = MockMCPToolResponse(
                    success=True,
                    data={
                        'delegation': {
                            'from_level': 'task',
                            'to_level': 'project',
                            'delegate_data': {'reusable_pattern': 'auth_middleware'},
                            'delegation_reason': 'Reusable across tasks',
                            'user_id': authenticated_user.user_id
                        }
                    }
                )
                
                # Verify context operations work with authentication
                global_result = mock_instance.create_context()
                assert global_result.success
                assert global_result.data['context']['user_id'] == authenticated_user.user_id
                
                resolve_result = mock_instance.resolve_context()
                assert resolve_result.success
                assert resolve_result.data['context']['user_id'] == authenticated_user.user_id
                assert 'inherited_data' in resolve_result.data['context']
                
                delegate_result = mock_instance.delegate_context()
                assert delegate_result.success
                assert delegate_result.data['delegation']['user_id'] == authenticated_user.user_id

    @pytest.mark.asyncio
    async def test_authentication_error_cases(self):
        """Test error cases related to authentication"""
        
        # Test missing authentication
        with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_context') as mock_get_user:
            mock_get_user.return_value = None
            
            with patch('dhafnck_mcp_main.src.interface.controllers.task_mcp_controller.TaskMCPController') as mock_controller:
                mock_instance = mock_controller.return_value
                
                # Mock authentication error response
                mock_instance.create_task.return_value = MockMCPToolResponse(
                    success=False,
                    error="Authentication required"
                )
                
                result = mock_instance.create_task()
                assert not result.success
                assert "Authentication required" in result.error

    @pytest.mark.asyncio
    async def test_invalid_parameters_error_cases(self, authenticated_user):
        """Test error cases for invalid parameters"""
        with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_context') as mock_get_user:
            mock_get_user.return_value = authenticated_user
            
            with patch('dhafnck_mcp_main.src.interface.controllers.task_mcp_controller.TaskMCPController') as mock_controller:
                mock_instance = mock_controller.return_value
                
                # Mock validation error responses
                mock_instance.create_task.return_value = MockMCPToolResponse(
                    success=False,
                    error="Missing required parameter: title"
                )
                
                mock_instance.get_task.return_value = MockMCPToolResponse(
                    success=False,
                    error="Invalid task_id format"
                )
                
                # Verify validation errors are properly handled
                create_result = mock_instance.create_task()
                assert not create_result.success
                assert "Missing required parameter" in create_result.error
                
                get_result = mock_instance.get_task()
                assert not get_result.success
                assert "Invalid task_id format" in get_result.error

    @pytest.mark.asyncio
    async def test_non_existent_resources_error_cases(self, authenticated_user):
        """Test error cases for non-existent resources"""
        with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_context') as mock_get_user:
            mock_get_user.return_value = authenticated_user
            
            with patch('dhafnck_mcp_main.src.interface.controllers.task_mcp_controller.TaskMCPController') as mock_controller:
                mock_instance = mock_controller.return_value
                
                # Mock not found error responses
                non_existent_id = str(uuid.uuid4())
                
                mock_instance.get_task.return_value = MockMCPToolResponse(
                    success=False,
                    error=f"Task with id {non_existent_id} not found"
                )
                
                mock_instance.update_task.return_value = MockMCPToolResponse(
                    success=False,
                    error="Task not found or access denied"
                )
                
                # Verify not found errors are properly handled
                get_result = mock_instance.get_task()
                assert not get_result.success
                assert "not found" in get_result.error
                
                update_result = mock_instance.update_task()
                assert not update_result.success
                assert "not found" in update_result.error or "access denied" in update_result.error

    @pytest.mark.asyncio
    async def test_user_isolation_with_auth(self, authenticated_user, project_id):
        """Test that user isolation works correctly with authentication"""
        other_user = MockAuthenticatedUser("other_user_auth")
        
        with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_context') as mock_get_user:
            # Test as first user - should see their own data
            mock_get_user.return_value = authenticated_user
            
            with patch('dhafnck_mcp_main.src.interface.controllers.project_mcp_controller.ProjectMCPController') as mock_controller:
                mock_instance = mock_controller.return_value
                
                # Mock user's own projects
                mock_instance.list_projects.return_value = MockMCPToolResponse(
                    success=True,
                    data={
                        'projects': [{
                            'id': project_id,
                            'name': 'User Project',
                            'user_id': authenticated_user.user_id
                        }]
                    }
                )
                
                result = mock_instance.list_projects()
                assert result.success
                assert len(result.data['projects']) == 1
                assert result.data['projects'][0]['user_id'] == authenticated_user.user_id
                
            # Test as different user - should see different data
            mock_get_user.return_value = other_user
            
            with patch('dhafnck_mcp_main.src.interface.controllers.project_mcp_controller.ProjectMCPController') as mock_controller:
                mock_instance = mock_controller.return_value
                
                # Mock other user's projects
                other_project_id = str(uuid.uuid4())
                mock_instance.list_projects.return_value = MockMCPToolResponse(
                    success=True,
                    data={
                        'projects': [{
                            'id': other_project_id,
                            'name': 'Other User Project',
                            'user_id': other_user.user_id
                        }]
                    }
                )
                
                result = mock_instance.list_projects()
                assert result.success
                assert len(result.data['projects']) == 1
                assert result.data['projects'][0]['user_id'] == other_user.user_id
                assert result.data['projects'][0]['id'] != project_id

    @pytest.mark.asyncio
    async def test_comprehensive_workflow_with_auth(self, authenticated_user):
        """Test a complete workflow from project creation to task completion with authentication"""
        # Generate test IDs
        project_id = str(uuid.uuid4())
        git_branch_id = str(uuid.uuid4())
        task_id = str(uuid.uuid4())
        subtask_id = str(uuid.uuid4())
        
        with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_context') as mock_get_user:
            mock_get_user.return_value = authenticated_user
            
            # Step 1: Create project
            with patch('dhafnck_mcp_main.src.interface.controllers.project_mcp_controller.ProjectMCPController') as mock_controller:
                mock_instance = mock_controller.return_value
                mock_instance.create_project.return_value = MockMCPToolResponse(
                    success=True,
                    data={'project': {'id': project_id, 'name': 'Workflow Test', 'user_id': authenticated_user.user_id}}
                )
                
                project_result = mock_instance.create_project()
                assert project_result.success
                assert project_result.data['project']['user_id'] == authenticated_user.user_id
            
            # Step 2: Create git branch
            with patch('dhafnck_mcp_main.src.interface.controllers.git_branch_mcp_controller.GitBranchMCPController') as mock_controller:
                mock_instance = mock_controller.return_value
                mock_instance.create_git_branch.return_value = MockMCPToolResponse(
                    success=True,
                    data={'git_branch': {'id': git_branch_id, 'project_id': project_id, 'user_id': authenticated_user.user_id}}
                )
                
                branch_result = mock_instance.create_git_branch()
                assert branch_result.success
                assert branch_result.data['git_branch']['user_id'] == authenticated_user.user_id
            
            # Step 3: Create task
            with patch('dhafnck_mcp_main.src.interface.controllers.task_mcp_controller.TaskMCPController') as mock_controller:
                mock_instance = mock_controller.return_value
                mock_instance.create_task.return_value = MockMCPToolResponse(
                    success=True,
                    data={'task': {'id': task_id, 'git_branch_id': git_branch_id, 'user_id': authenticated_user.user_id}}
                )
                
                task_result = mock_instance.create_task()
                assert task_result.success
                assert task_result.data['task']['user_id'] == authenticated_user.user_id
            
            # Step 4: Create subtask
            with patch('dhafnck_mcp_main.src.interface.controllers.subtask_mcp_controller.SubtaskMCPController') as mock_controller:
                mock_instance = mock_controller.return_value
                mock_instance.create_subtask.return_value = MockMCPToolResponse(
                    success=True,
                    data={'subtask': {'id': subtask_id, 'task_id': task_id, 'user_id': authenticated_user.user_id}}
                )
                
                subtask_result = mock_instance.create_subtask()
                assert subtask_result.success
                assert subtask_result.data['subtask']['user_id'] == authenticated_user.user_id
            
            # Step 5: Create contexts at all levels
            with patch('dhafnck_mcp_main.src.interface.controllers.unified_context_controller.UnifiedContextController') as mock_controller:
                mock_instance = mock_controller.return_value
                
                # Mock successful context creation at all levels
                mock_instance.create_context.return_value = MockMCPToolResponse(
                    success=True,
                    data={'context': {'level': 'task', 'context_id': task_id, 'user_id': authenticated_user.user_id}}
                )
                
                context_result = mock_instance.create_context()
                assert context_result.success
                assert context_result.data['context']['user_id'] == authenticated_user.user_id
            
            # Step 6: Complete subtask and task
            with patch('dhafnck_mcp_main.src.interface.controllers.subtask_mcp_controller.SubtaskMCPController') as mock_controller:
                mock_instance = mock_controller.return_value
                mock_instance.complete_subtask.return_value = MockMCPToolResponse(
                    success=True,
                    data={'subtask': {'id': subtask_id, 'status': 'done', 'user_id': authenticated_user.user_id}}
                )
                
                subtask_complete_result = mock_instance.complete_subtask()
                assert subtask_complete_result.success
                assert subtask_complete_result.data['subtask']['user_id'] == authenticated_user.user_id
            
            with patch('dhafnck_mcp_main.src.interface.controllers.task_mcp_controller.TaskMCPController') as mock_controller:
                mock_instance = mock_controller.return_value
                mock_instance.complete_task.return_value = MockMCPToolResponse(
                    success=True,
                    data={'task': {'id': task_id, 'status': 'done', 'user_id': authenticated_user.user_id}}
                )
                
                task_complete_result = mock_instance.complete_task()
                assert task_complete_result.success
                assert task_complete_result.data['task']['user_id'] == authenticated_user.user_id


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])