"""Test suite for entity types."""

import pytest
from uuid import uuid4
from datetime import datetime
from pydantic import ValidationError

from fastmcp.types.entities import (
    TaskEntity,
    SubtaskEntity,
    ProjectEntity,
    GitBranchEntity,
    AgentEntity,
    ContextEntity,
    TokenEntity
)


class TestTaskEntity:
    """Test cases for TaskEntity."""
    
    def test_task_entity_complete(self):
        """Test creating TaskEntity with all fields."""
        task_id = str(uuid4())
        entity = TaskEntity(
            id=task_id,
            title="Test Task",
            description="Test Description",
            status="todo",
            priority="medium",
            details="Additional details",
            assignees=["user1", "user2"],
            labels=["frontend", "bug"],
            estimated_effort="3 hours",
            due_date="2024-12-31T00:00:00Z",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
            git_branch_id=str(uuid4()),
            project_id=str(uuid4()),
            parent_task_id=str(uuid4()),
            dependencies=[str(uuid4()), str(uuid4())],
            blocking_tasks=[str(uuid4())],
            subtask_ids=[str(uuid4())],
            subtask_count=1,
            context_id=str(uuid4()),
            completion_summary="Completed successfully"
        )
        
        assert entity.id == task_id
        assert entity.title == "Test Task"
        assert entity.status == "todo"
        assert entity.priority == "medium"
        assert len(entity.assignees) == 2
        assert len(entity.labels) == 2
        assert entity.subtask_count == 1
    
    def test_task_entity_minimal(self):
        """Test creating TaskEntity with minimal fields."""
        entity = TaskEntity(
            id=str(uuid4()),
            title="Minimal Task",
            status="todo",
            priority="low",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
            git_branch_id=str(uuid4()),
            project_id=str(uuid4()),
            subtask_count=0
        )
        
        assert entity.title == "Minimal Task"
        assert entity.description is None
        assert entity.details is None
        assert entity.assignees == []
        assert entity.labels == []
        assert entity.estimated_effort is None
        assert entity.due_date is None
        assert entity.parent_task_id is None
        assert entity.dependencies == []
        assert entity.blocking_tasks == []
        assert entity.subtask_ids == []
        assert entity.context_id is None
        assert entity.completion_summary is None
    
    def test_task_entity_validation_error(self):
        """Test TaskEntity validation errors."""
        # Missing required fields
        with pytest.raises(ValidationError) as exc_info:
            TaskEntity(
                id=str(uuid4()),
                title="Test"
                # Missing required fields: status, priority, etc.
            )
        
        errors = exc_info.value.errors()
        assert len(errors) > 0
        assert any(e['loc'][0] in ['status', 'priority', 'created_at', 'updated_at', 'git_branch_id', 'project_id', 'subtask_count'] 
                   for e in errors)
    
    def test_task_entity_status_validation(self):
        """Test TaskEntity status field validation."""
        valid_statuses = ["todo", "in_progress", "done", "blocked", "review", "testing", "cancelled"]
        
        for status in valid_statuses:
            entity = TaskEntity(
                id=str(uuid4()),
                title="Status Test",
                status=status,
                priority="medium",
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
                git_branch_id=str(uuid4()),
                project_id=str(uuid4()),
                subtask_count=0
            )
            assert entity.status == status
    
    def test_task_entity_priority_validation(self):
        """Test TaskEntity priority field validation."""
        valid_priorities = ["low", "medium", "high", "urgent", "critical"]
        
        for priority in valid_priorities:
            entity = TaskEntity(
                id=str(uuid4()),
                title="Priority Test",
                status="todo",
                priority=priority,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
                git_branch_id=str(uuid4()),
                project_id=str(uuid4()),
                subtask_count=0
            )
            assert entity.priority == priority


class TestSubtaskEntity:
    """Test cases for SubtaskEntity."""
    
    def test_subtask_entity_complete(self):
        """Test creating SubtaskEntity with all fields."""
        subtask_id = str(uuid4())
        task_id = str(uuid4())
        
        entity = SubtaskEntity(
            id=subtask_id,
            title="Test Subtask",
            description="Subtask Description",
            status="in_progress",
            priority="high",
            assignees=["user1", "user2"],
            progress_notes="50% complete",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
            task_id=task_id,
            parent_title="Parent Task Title"
        )
        
        assert entity.id == subtask_id
        assert entity.title == "Test Subtask"
        assert entity.status == "in_progress"
        assert entity.priority == "high"
        assert entity.assignees == ["user1", "user2"]
        assert entity.progress_notes == "50% complete"
        assert entity.task_id == task_id
        assert entity.parent_title == "Parent Task Title"
    
    def test_subtask_entity_minimal(self):
        """Test creating SubtaskEntity with minimal fields."""
        entity = SubtaskEntity(
            id=str(uuid4()),
            title="Minimal Subtask",
            status="todo",
            priority="low",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
            task_id=str(uuid4()),
            parent_title=""
        )
        
        assert entity.title == "Minimal Subtask"
        assert entity.description is None
        assert entity.assignees == []
        assert entity.progress_notes is None
        assert entity.parent_title == ""


class TestProjectEntity:
    """Test cases for ProjectEntity."""
    
    def test_project_entity(self):
        """Test creating ProjectEntity."""
        project_id = str(uuid4())
        
        entity = ProjectEntity(
            id=project_id,
            name="Test Project",
            description="Project Description",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        
        assert entity.id == project_id
        assert entity.name == "Test Project"
        assert entity.description == "Project Description"
        assert entity.created_at == "2024-01-01T00:00:00Z"
        assert entity.updated_at == "2024-01-01T00:00:00Z"
    
    def test_project_entity_optional_description(self):
        """Test ProjectEntity with optional description."""
        entity = ProjectEntity(
            id=str(uuid4()),
            name="No Description Project",
            description=None,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        
        assert entity.description is None


class TestGitBranchEntity:
    """Test cases for GitBranchEntity."""
    
    def test_git_branch_entity(self):
        """Test creating GitBranchEntity."""
        branch_id = str(uuid4())
        project_id = str(uuid4())
        
        entity = GitBranchEntity(
            id=branch_id,
            name="feature/test-branch",
            description="Feature branch for testing",
            project_id=project_id,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        
        assert entity.id == branch_id
        assert entity.name == "feature/test-branch"
        assert entity.description == "Feature branch for testing"
        assert entity.project_id == project_id


class TestAgentEntity:
    """Test cases for AgentEntity."""
    
    def test_agent_entity(self):
        """Test creating AgentEntity."""
        agent_id = str(uuid4())
        project_id = str(uuid4())
        
        entity = AgentEntity(
            id=agent_id,
            name="test-agent",
            description="Test Agent for development",
            capabilities=["coding", "testing", "debugging"],
            status="active",
            project_id=project_id,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        
        assert entity.id == agent_id
        assert entity.name == "test-agent"
        assert entity.description == "Test Agent for development"
        assert entity.capabilities == ["coding", "testing", "debugging"]
        assert entity.status == "active"
        assert entity.project_id == project_id
    
    def test_agent_entity_default_capabilities(self):
        """Test AgentEntity with default empty capabilities."""
        entity = AgentEntity(
            id=str(uuid4()),
            name="basic-agent",
            description="Basic Agent",
            status="active",
            project_id=str(uuid4()),
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        
        assert entity.capabilities == []


class TestContextEntity:
    """Test cases for ContextEntity."""
    
    def test_context_entity(self):
        """Test creating ContextEntity."""
        context_id = str(uuid4())
        
        entity = ContextEntity(
            id=context_id,
            level="project",
            data={"key": "value", "nested": {"data": "structure"}},
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        
        assert entity.id == context_id
        assert entity.level == "project"
        assert entity.data == {"key": "value", "nested": {"data": "structure"}}


class TestTokenEntity:
    """Test cases for TokenEntity."""
    
    def test_token_entity(self):
        """Test creating TokenEntity."""
        token_id = str(uuid4())
        user_id = str(uuid4())
        
        entity = TokenEntity(
            id=token_id,
            user_id=user_id,
            name="API Token",
            token="secret_token_value",
            expires_at="2025-01-01T00:00:00Z",
            scopes=["read", "write"],
            is_active=True,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        
        assert entity.id == token_id
        assert entity.user_id == user_id
        assert entity.name == "API Token"
        assert entity.token == "secret_token_value"
        assert entity.expires_at == "2025-01-01T00:00:00Z"
        assert entity.scopes == ["read", "write"]
        assert entity.is_active is True
    
    def test_token_entity_optional_fields(self):
        """Test TokenEntity with optional fields."""
        entity = TokenEntity(
            id=str(uuid4()),
            user_id=str(uuid4()),
            name="Basic Token",
            token="token_value",
            is_active=True,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        
        assert entity.expires_at is None
        assert entity.scopes == []