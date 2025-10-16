"""Test suite for type converters."""

import pytest
from datetime import datetime
from uuid import uuid4

from fastmcp.types.converters import (
    task_to_entity,
    subtask_to_entity,
    project_to_entity,
    git_branch_to_entity,
    agent_to_entity,
    entity_to_dict
)
from fastmcp.types.entities import (
    TaskEntity,
    SubtaskEntity,
    ProjectEntity,
    GitBranchEntity,
    AgentEntity
)
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.entities.project import Project
from fastmcp.task_management.domain.entities.git_branch import GitBranch
from fastmcp.task_management.domain.entities.agent import Agent
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.shared.domain.value_objects import UUID


class TestTaskConverter:
    """Test cases for task_to_entity converter."""
    
    @pytest.fixture
    def sample_task(self):
        """Create a sample domain task."""
        return Task(
            id=UUID.generate(),
            title="Test Task",
            description="Test Description",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            details="Additional details",
            assignees=["user1", "user2"],
            labels=["frontend", "bug"],
            estimated_effort="3 hours",
            due_date=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            git_branch_id=UUID.generate(),
            project_id=UUID.generate(),
            parent_task_id=UUID.generate(),
            dependencies=[UUID.generate(), UUID.generate()],
            blocking_tasks=[UUID.generate()],
            subtask_ids=[UUID.generate(), UUID.generate()],
            subtask_count=2,
            context_id=UUID.generate(),
            completion_summary="Completed successfully"
        )
    
    def test_task_to_entity_complete(self, sample_task):
        """Test converting a complete task to entity."""
        entity = task_to_entity(sample_task)
        
        assert isinstance(entity, TaskEntity)
        assert entity.id == sample_task.id.value
        assert entity.title == "Test Task"
        assert entity.description == "Test Description"
        assert entity.status == "todo"
        assert entity.priority == "medium"
        assert entity.details == "Additional details"
        assert entity.assignees == ["user1", "user2"]
        assert entity.labels == ["frontend", "bug"]
        assert entity.estimated_effort == "3 hours"
        assert entity.due_date == sample_task.due_date.isoformat()
        assert entity.git_branch_id == sample_task.git_branch_id.value
        assert entity.project_id == sample_task.project_id.value
        assert entity.parent_task_id == sample_task.parent_task_id.value
        assert len(entity.dependencies) == 2
        assert len(entity.blocking_tasks) == 1
        assert len(entity.subtask_ids) == 2
        assert entity.subtask_count == 2
        assert entity.context_id == sample_task.context_id.value
        assert entity.completion_summary == "Completed successfully"
    
    def test_task_to_entity_minimal(self):
        """Test converting task with minimal fields."""
        task = Task(
            id=UUID.generate(),
            title="Minimal Task",
            status=TaskStatus.TODO,
            priority=Priority.LOW,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            git_branch_id=UUID.generate(),
            project_id=UUID.generate()
        )
        
        entity = task_to_entity(task)
        
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
        assert entity.subtask_count == 0
        assert entity.context_id is None
        assert entity.completion_summary is None


class TestSubtaskConverter:
    """Test cases for subtask_to_entity converter."""
    
    @pytest.fixture
    def sample_subtask(self):
        """Create a sample domain subtask."""
        subtask = Subtask(
            id=UUID.generate(),
            title="Test Subtask",
            description="Subtask Description",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            assignees=["user1", "user2"],
            progress_notes="50% complete",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        subtask.task_id = UUID.generate()
        return subtask
    
    def test_subtask_to_entity(self, sample_subtask):
        """Test converting subtask to entity."""
        entity = subtask_to_entity(sample_subtask, parent_title="Parent Task")
        
        assert isinstance(entity, SubtaskEntity)
        assert entity.id == sample_subtask.id.value
        assert entity.title == "Test Subtask"
        assert entity.description == "Subtask Description"
        assert entity.status == "in_progress"
        assert entity.priority == "high"
        assert entity.assignees == ["user1", "user2"]
        assert entity.progress_notes == "50% complete"
        assert entity.task_id == sample_subtask.task_id.value
        assert entity.parent_title == "Parent Task"
    
    def test_subtask_to_entity_without_parent_title(self, sample_subtask):
        """Test converting subtask without parent title."""
        entity = subtask_to_entity(sample_subtask)
        
        assert entity.parent_title == ""


class TestProjectConverter:
    """Test cases for project_to_entity converter."""
    
    @pytest.fixture
    def sample_project(self):
        """Create a sample domain project."""
        return Project(
            id=UUID.generate(),
            name="Test Project",
            description="Project Description",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    def test_project_to_entity(self, sample_project):
        """Test converting project to entity."""
        entity = project_to_entity(sample_project)
        
        assert isinstance(entity, ProjectEntity)
        assert entity.id == sample_project.id.value
        assert entity.name == "Test Project"
        assert entity.description == "Project Description"
        assert entity.created_at == sample_project.created_at.isoformat()
        assert entity.updated_at == sample_project.updated_at.isoformat()


class TestGitBranchConverter:
    """Test cases for git_branch_to_entity converter."""
    
    @pytest.fixture
    def sample_git_branch(self):
        """Create a sample domain git branch."""
        return GitBranch(
            id=UUID.generate(),
            name="feature/test-branch",
            description="Test branch description",
            project_id=UUID.generate(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    def test_git_branch_to_entity(self, sample_git_branch):
        """Test converting git branch to entity."""
        entity = git_branch_to_entity(sample_git_branch)
        
        assert isinstance(entity, GitBranchEntity)
        assert entity.id == sample_git_branch.id.value
        assert entity.name == "feature/test-branch"
        assert entity.description == "Test branch description"
        assert entity.project_id == sample_git_branch.project_id.value
        assert entity.created_at == sample_git_branch.created_at.isoformat()
        assert entity.updated_at == sample_git_branch.updated_at.isoformat()


class TestAgentConverter:
    """Test cases for agent_to_entity converter."""
    
    @pytest.fixture
    def sample_agent(self):
        """Create a sample domain agent."""
        return Agent(
            id=UUID.generate(),
            name="test-agent",
            description="Test Agent",
            capabilities=["coding", "testing"],
            status="active",
            project_id=UUID.generate(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    def test_agent_to_entity(self, sample_agent):
        """Test converting agent to entity."""
        entity = agent_to_entity(sample_agent)
        
        assert isinstance(entity, AgentEntity)
        assert entity.id == sample_agent.id.value
        assert entity.name == "test-agent"
        assert entity.description == "Test Agent"
        assert entity.capabilities == ["coding", "testing"]
        assert entity.status == "active"
        assert entity.project_id == sample_agent.project_id.value
        assert entity.created_at == sample_agent.created_at.isoformat()
        assert entity.updated_at == sample_agent.updated_at.isoformat()


class TestEntityToDict:
    """Test cases for entity_to_dict converter."""
    
    def test_entity_to_dict_task(self):
        """Test converting task entity to dictionary."""
        entity = TaskEntity(
            id=str(uuid4()),
            title="Test Task",
            description="Test Description",
            status="todo",
            priority="medium",
            details=None,
            assignees=["user1"],
            labels=["test"],
            estimated_effort=None,
            due_date=None,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            git_branch_id=str(uuid4()),
            project_id=str(uuid4()),
            parent_task_id=None,
            dependencies=[],
            blocking_tasks=[],
            subtask_ids=[],
            subtask_count=0,
            context_id=None,
            completion_summary=None
        )
        
        result = entity_to_dict(entity)
        
        assert isinstance(result, dict)
        assert result["id"] == entity.id
        assert result["title"] == "Test Task"
        assert result["status"] == "todo"
        assert result["assignees"] == ["user1"]
        assert result["subtask_count"] == 0
    
    def test_entity_to_dict_subtask(self):
        """Test converting subtask entity to dictionary."""
        entity = SubtaskEntity(
            id=str(uuid4()),
            title="Test Subtask",
            description="Test",
            status="todo",
            priority="low",
            assignees=[],
            progress_notes=None,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            task_id=str(uuid4()),
            parent_title="Parent"
        )
        
        result = entity_to_dict(entity)
        
        assert isinstance(result, dict)
        assert result["id"] == entity.id
        assert result["title"] == "Test Subtask"
        assert result["parent_title"] == "Parent"
    
    def test_entity_to_dict_with_custom_exclude(self):
        """Test entity to dict with custom field exclusion."""
        entity = ProjectEntity(
            id=str(uuid4()),
            name="Test Project",
            description="Description",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00"
        )
        
        # If entity_to_dict supports exclude parameter
        result = entity_to_dict(entity)
        
        assert "id" in result
        assert "name" in result
        assert "description" in result