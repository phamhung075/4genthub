"""Test suite for Context domain entities.

Tests the Context entities including:
- TaskContext creation and validation
- Context metadata management
- Objective and requirements handling
- Technical details and dependencies
- Progress tracking and completion
- Notes and insights management
- Subtask context handling
- Context schema validation
- Serialization and deserialization
- Vision System integration
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
import json
import uuid

from fastmcp.task_management.domain.entities.context import (
    TaskContext,
    ContextMetadata,
    ContextObjective,
    ContextRequirement,
    ContextRequirements,
    ContextTechnical,
    ContextDependency,
    ContextDependencies,
    ContextProgress,
    ContextProgressAction,
    ContextInsight,
    ContextNotes,
    ContextSubtask,
    ContextSubtasks,
    ContextCustomSection,
    ContextSchema,
    GlobalContext,
    ProjectContext,
    BranchContext,
    TaskContextUnified
)
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus, TaskStatusEnum
from fastmcp.task_management.domain.value_objects.priority import Priority, PriorityLevel


class TestTaskContextCreation:
    """Test cases for TaskContext creation and initialization."""
    
    def test_create_task_context_minimal(self):
        """Test creating task context with minimal required data."""
        metadata = ContextMetadata(task_id="task-123")
        objective = ContextObjective(title="Test Task")
        
        context = TaskContext(metadata=metadata, objective=objective)
        
        assert context.metadata.task_id == "task-123"
        assert context.objective.title == "Test Task"
        assert context.metadata.status.value == TaskStatusEnum.TODO.value
        assert context.metadata.priority.value == PriorityLevel.MEDIUM.label
        assert context.metadata.assignees == []
        assert context.metadata.labels == []
        assert context.metadata.version == 1
        assert context.requirements.checklist == []
        assert context.technical.technologies == []
        assert context.dependencies.task_dependencies == []
        assert context.progress.completed_actions == []
        assert context.subtasks.items == []
        assert context.notes.agent_insights == []
        assert context.custom_sections == []
    
    def test_create_task_context_full_data(self):
        """Test creating task context with full data."""
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
        
        metadata = ContextMetadata(
            task_id="task-456",
            status=TaskStatus.in_progress(),
            priority=Priority.high(),
            assignees=["@user1", "@user2"],
            labels=["feature", "urgent"],
            created_at=created_at,
            updated_at=updated_at,
            version=2
        )
        
        objective = ContextObjective(
            title="Complex Task",
            description="A complex task with full context",
            estimated_effort="3 days",
            due_date=datetime(2024, 12, 31, tzinfo=timezone.utc)
        )
        
        requirements = ContextRequirements(
            checklist=[
                ContextRequirement(
                    id="req-1",
                    title="First requirement",
                    completed=True,
                    priority=Priority.high()
                )
            ],
            custom_requirements=["Custom req 1", "Custom req 2"],
            completion_criteria=["All tests pass", "Code review approved"]
        )
        
        context = TaskContext(
            metadata=metadata,
            objective=objective,
            requirements=requirements
        )
        
        assert context.metadata.task_id == "task-456"
        assert context.metadata.status.value == TaskStatusEnum.IN_PROGRESS.value
        assert context.metadata.priority.value == "high"
        assert context.metadata.assignees == ["@user1", "@user2"]
        assert context.metadata.labels == ["feature", "urgent"]
        assert context.metadata.version == 2
        assert context.objective.title == "Complex Task"
        assert context.objective.description == "A complex task with full context"
        assert context.objective.estimated_effort == "3 days"
        assert len(context.requirements.checklist) == 1
        assert context.requirements.checklist[0].title == "First requirement"
        assert context.requirements.checklist[0].completed is True
    
    def test_task_context_timezone_handling(self):
        """Test timezone handling in task context."""
        # Naive datetime should be converted to UTC
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        metadata = ContextMetadata(
            task_id="task-123",
            created_at=naive_dt,
            updated_at=naive_dt
        )
        objective = ContextObjective(title="Test")
        
        context = TaskContext(metadata=metadata, objective=objective)
        
        assert context.metadata.created_at.tzinfo == timezone.utc
        assert context.metadata.updated_at.tzinfo == timezone.utc


class TestContextMetadata:
    """Test cases for ContextMetadata."""
    
    def test_context_metadata_defaults(self):
        """Test default values for context metadata."""
        metadata = ContextMetadata(task_id="task-123")
        
        assert metadata.task_id == "task-123"
        assert metadata.status.value == TaskStatusEnum.TODO.value
        assert metadata.priority.value == PriorityLevel.MEDIUM.label
        assert metadata.assignees == []
        assert metadata.labels == []
        assert metadata.version == 1
        assert metadata.created_at is not None
        assert metadata.updated_at is not None
        assert metadata.created_at.tzinfo == timezone.utc
        assert metadata.updated_at.tzinfo == timezone.utc
    
    def test_context_metadata_value_objects(self):
        """Test value object usage in metadata."""
        metadata = ContextMetadata(
            task_id="task-456",
            status=TaskStatus.done(),
            priority=Priority.urgent()
        )
        
        assert isinstance(metadata.status, TaskStatus)
        assert isinstance(metadata.priority, Priority)
        assert metadata.status.value == TaskStatusEnum.DONE.value
        assert metadata.priority.value == "urgent"


class TestContextObjective:
    """Test cases for ContextObjective."""
    
    def test_context_objective_minimal(self):
        """Test objective with minimal data."""
        objective = ContextObjective(title="Simple Task")
        
        assert objective.title == "Simple Task"
        assert objective.description == ""
        assert objective.estimated_effort is None
        assert objective.due_date is None
    
    def test_context_objective_full_data(self):
        """Test objective with full data."""
        due_date = datetime(2024, 12, 31, tzinfo=timezone.utc)
        
        objective = ContextObjective(
            title="Complex Task",
            description="A complex task requiring multiple steps",
            estimated_effort="1 week",
            due_date=due_date
        )
        
        assert objective.title == "Complex Task"
        assert objective.description == "A complex task requiring multiple steps"
        assert objective.estimated_effort == "1 week"
        assert objective.due_date == due_date


class TestContextRequirements:
    """Test cases for ContextRequirements and ContextRequirement."""
    
    def test_context_requirement_creation(self):
        """Test creating individual requirement."""
        requirement = ContextRequirement(
            id="req-1",
            title="Must implement authentication",
            completed=True,
            priority=Priority.high(),
            notes="Using JWT tokens"
        )
        
        assert requirement.id == "req-1"
        assert requirement.title == "Must implement authentication"
        assert requirement.completed is True
        assert requirement.priority.value == "high"
        assert requirement.notes == "Using JWT tokens"
    
    def test_context_requirement_defaults(self):
        """Test requirement defaults."""
        requirement = ContextRequirement(id="req-1", title="Basic requirement")
        
        assert requirement.completed is False
        assert requirement.priority.value == PriorityLevel.MEDIUM.label
        assert requirement.notes == ""
    
    def test_context_requirements_collection(self):
        """Test requirements collection."""
        req1 = ContextRequirement(id="req-1", title="First", completed=True)
        req2 = ContextRequirement(id="req-2", title="Second", completed=False)
        
        requirements = ContextRequirements(
            checklist=[req1, req2],
            custom_requirements=["Custom 1", "Custom 2"],
            completion_criteria=["All tests pass", "Code reviewed"]
        )
        
        assert len(requirements.checklist) == 2
        assert requirements.checklist[0].title == "First"
        assert requirements.checklist[1].title == "Second"
        assert len(requirements.custom_requirements) == 2
        assert len(requirements.completion_criteria) == 2


class TestContextProgress:
    """Test cases for ContextProgress and related classes."""
    
    def test_context_progress_action(self):
        """Test progress action creation."""
        action = ContextProgressAction(
            timestamp="2024-01-01T12:00:00Z",
            action="Implemented user login",
            agent="@coding_agent",
            details="Added JWT authentication",
            status="completed"
        )
        
        assert action.timestamp == "2024-01-01T12:00:00Z"
        assert action.action == "Implemented user login"
        assert action.agent == "@coding_agent"
        assert action.details == "Added JWT authentication"
        assert action.status == "completed"
    
    def test_context_progress_defaults(self):
        """Test progress defaults."""
        progress = ContextProgress()
        
        assert progress.completed_actions == []
        assert progress.current_session_summary == ""
        assert progress.next_steps == []
        assert progress.completion_percentage == 0.0
        assert progress.time_spent_minutes == 0
        assert progress.completion_summary is None
        assert progress.testing_notes is None
        assert progress.next_recommendations is None
        assert progress.vision_alignment_score is None
    
    def test_context_progress_with_actions(self):
        """Test progress with actions and vision fields."""
        action1 = ContextProgressAction(
            timestamp="2024-01-01T12:00:00Z",
            action="Started implementation",
            agent="@coding_agent"
        )
        action2 = ContextProgressAction(
            timestamp="2024-01-01T14:00:00Z",
            action="Completed implementation",
            agent="@coding_agent"
        )
        
        progress = ContextProgress(
            completed_actions=[action1, action2],
            current_session_summary="Made good progress on authentication",
            next_steps=["Add tests", "Update documentation"],
            completion_percentage=75.0,
            time_spent_minutes=180,
            completion_summary="Authentication feature completed",
            testing_notes="Unit tests added and passing",
            vision_alignment_score=0.95
        )
        
        assert len(progress.completed_actions) == 2
        assert progress.current_session_summary == "Made good progress on authentication"
        assert len(progress.next_steps) == 2
        assert progress.completion_percentage == 75.0
        assert progress.time_spent_minutes == 180
        assert progress.completion_summary == "Authentication feature completed"
        assert progress.testing_notes == "Unit tests added and passing"
        assert progress.vision_alignment_score == 0.95


class TestContextNotes:
    """Test cases for ContextNotes and ContextInsight."""
    
    def test_context_insight(self):
        """Test context insight creation."""
        insight = ContextInsight(
            timestamp="2024-01-01T12:00:00Z",
            agent="@coding_agent",
            category="insight",
            content="Using JWT tokens provides better security",
            importance="high"
        )
        
        assert insight.timestamp == "2024-01-01T12:00:00Z"
        assert insight.agent == "@coding_agent"
        assert insight.category == "insight"
        assert insight.content == "Using JWT tokens provides better security"
        assert insight.importance == "high"
    
    def test_context_insight_defaults(self):
        """Test insight defaults."""
        insight = ContextInsight(
            timestamp="2024-01-01T12:00:00Z",
            agent="@agent",
            category="decision",
            content="Made a decision"
        )
        
        assert insight.importance == "medium"
    
    def test_context_notes_collection(self):
        """Test notes collection."""
        insight = ContextInsight(
            timestamp="2024-01-01T12:00:00Z",
            agent="@agent",
            category="insight",
            content="Found useful pattern"
        )
        
        challenge = ContextInsight(
            timestamp="2024-01-01T13:00:00Z",
            agent="@agent",
            category="challenge",
            content="API rate limiting issue"
        )
        
        notes = ContextNotes(
            agent_insights=[insight],
            challenges_encountered=[challenge],
            general_notes="Overall progress is good"
        )
        
        assert len(notes.agent_insights) == 1
        assert len(notes.challenges_encountered) == 1
        assert notes.general_notes == "Overall progress is good"


class TestTaskContextValidation:
    """Test cases for TaskContext validation and Vision System integration."""
    
    def test_update_completion_summary_valid(self):
        """Test updating completion summary with valid data."""
        metadata = ContextMetadata(task_id="task-123")
        objective = ContextObjective(title="Test Task")
        context = TaskContext(metadata=metadata, objective=objective)
        
        original_updated = context.metadata.updated_at
        
        context.update_completion_summary(
            completion_summary="Task completed successfully",
            testing_notes="All tests passing",
            next_recommendations="Consider optimization"
        )
        
        assert context.progress.completion_summary == "Task completed successfully"
        assert context.progress.testing_notes == "All tests passing"
        assert context.progress.next_recommendations == "Consider optimization"
        assert context.metadata.updated_at > original_updated
    
    def test_update_completion_summary_empty_fails(self):
        """Test that empty completion summary fails."""
        metadata = ContextMetadata(task_id="task-123")
        objective = ContextObjective(title="Test Task")
        context = TaskContext(metadata=metadata, objective=objective)
        
        with pytest.raises(ValueError, match="completion_summary cannot be empty"):
            context.update_completion_summary("")
        
        with pytest.raises(ValueError, match="completion_summary cannot be empty"):
            context.update_completion_summary("   ")
        
        with pytest.raises(ValueError, match="completion_summary cannot be empty"):
            context.update_completion_summary(None)
    
    def test_has_completion_summary(self):
        """Test checking for completion summary."""
        metadata = ContextMetadata(task_id="task-123")
        objective = ContextObjective(title="Test Task")
        context = TaskContext(metadata=metadata, objective=objective)
        
        assert not context.has_completion_summary()
        
        context.progress.completion_summary = "Task completed"
        assert context.has_completion_summary()
        
        context.progress.completion_summary = "   "
        assert not context.has_completion_summary()
    
    def test_validate_for_task_completion_success(self):
        """Test validation for task completion succeeds."""
        metadata = ContextMetadata(task_id="task-123")
        objective = ContextObjective(title="Test Task")
        context = TaskContext(metadata=metadata, objective=objective)
        
        context.update_completion_summary("Task completed successfully")
        
        is_valid, errors = context.validate_for_task_completion()
        assert is_valid is True
        assert errors == []
    
    def test_validate_for_task_completion_missing_summary(self):
        """Test validation fails without completion summary."""
        metadata = ContextMetadata(task_id="task-123")
        objective = ContextObjective(title="Test Task")
        context = TaskContext(metadata=metadata, objective=objective)
        
        is_valid, errors = context.validate_for_task_completion()
        assert is_valid is False
        assert "completion_summary is required for task completion" in errors


class TestTaskContextSerialization:
    """Test cases for TaskContext serialization and deserialization."""
    
    def test_to_dict_minimal(self):
        """Test converting minimal context to dict."""
        metadata = ContextMetadata(task_id="task-123")
        objective = ContextObjective(title="Test Task")
        context = TaskContext(metadata=metadata, objective=objective)
        
        data = context.to_dict()
        
        assert data["task_id"] == "task-123"  # Backward compatibility
        assert data["metadata"]["task_id"] == "task-123"
        assert data["objective"]["title"] == "Test Task"
        assert "requirements" in data
        assert "technical" in data
        assert "dependencies" in data
        assert "progress" in data
        assert "subtasks" in data
        assert "notes" in data
        assert "custom_sections" in data
    
    def test_to_dict_with_custom_sections(self):
        """Test serialization with custom sections."""
        metadata = ContextMetadata(task_id="task-123")
        objective = ContextObjective(title="Test Task")
        context = TaskContext(metadata=metadata, objective=objective)
        
        custom_section = ContextCustomSection(
            name="deployment",
            data={"environment": "production", "replicas": 3},
            schema_version="1.0"
        )
        context.custom_sections = [custom_section]
        
        data = context.to_dict()
        
        assert len(data["custom_sections"]) == 1
        assert data["custom_sections"][0]["name"] == "deployment"
        assert data["custom_sections"][0]["data"]["environment"] == "production"
    
    def test_from_dict_minimal(self):
        """Test creating context from minimal dict."""
        data = {
            "metadata": {
                "task_id": "task-456"
            },
            "objective": {
                "title": "Restored Task"
            }
        }
        
        context = TaskContext.from_dict(data)
        
        assert context.metadata.task_id == "task-456"
        assert context.objective.title == "Restored Task"
        assert context.metadata.status.value == TaskStatusEnum.TODO.value
        assert context.metadata.priority.value == PriorityLevel.MEDIUM.label
    
    def test_from_dict_backward_compatibility(self):
        """Test loading from old flat format."""
        data = {
            "task_id": "task-old",
            "title": "Old Format Task",
            "description": "From old format",
            "status": "in_progress",
            "priority": "high",
            "assignees": ["@user1"],
            "labels": ["legacy"]
        }
        
        context = TaskContext.from_dict(data)
        
        assert context.metadata.task_id == "task-old"
        assert context.objective.title == "Old Format Task"
        assert context.objective.description == "From old format"
        assert context.metadata.status.value == TaskStatusEnum.IN_PROGRESS.value
        assert context.metadata.priority.value == "high"
        assert context.metadata.assignees == ["@user1"]
        assert context.metadata.labels == ["legacy"]
    
    def test_from_dict_with_custom_fields(self):
        """Test handling custom fields at root level."""
        data = {
            "metadata": {"task_id": "task-123"},
            "objective": {"title": "Test"},
            "custom_field1": "value1",
            "custom_field2": {"nested": "value2"}
        }
        
        context = TaskContext.from_dict(data)
        
        # Custom fields should be stored in custom_sections
        custom_section = next(
            (cs for cs in context.custom_sections if cs.name == "root_level_custom_fields"),
            None
        )
        assert custom_section is not None
        assert custom_section.data["custom_field1"] == "value1"
        assert custom_section.data["custom_field2"]["nested"] == "value2"
    
    def test_roundtrip_serialization(self):
        """Test that to_dict/from_dict roundtrip preserves data."""
        metadata = ContextMetadata(
            task_id="task-roundtrip",
            status=TaskStatus.in_progress(),
            priority=Priority.high(),
            assignees=["@user1", "@user2"],
            labels=["feature", "urgent"]
        )
        objective = ContextObjective(
            title="Roundtrip Task",
            description="Test roundtrip",
            estimated_effort="2 hours"
        )
        
        original_context = TaskContext(metadata=metadata, objective=objective)
        original_context.update_completion_summary("Completed successfully")
        
        # Serialize and deserialize
        data = original_context.to_dict()
        restored_context = TaskContext.from_dict(data)
        
        assert restored_context.metadata.task_id == original_context.metadata.task_id
        assert restored_context.objective.title == original_context.objective.title
        assert restored_context.metadata.status.value == original_context.metadata.status.value
        assert restored_context.metadata.priority.value == original_context.metadata.priority.value
        assert restored_context.metadata.assignees == original_context.metadata.assignees
        assert restored_context.metadata.labels == original_context.metadata.labels
        assert restored_context.progress.completion_summary == original_context.progress.completion_summary


class TestUnifiedContextEntities:
    """Test cases for unified context system entities."""
    
    def test_global_context(self):
        """Test GlobalContext entity."""
        global_context = GlobalContext(
            id="global_singleton",
            organization_name="Test Org",
            global_settings={"theme": "dark", "notifications": True},
            metadata={"version": "1.0"}
        )
        
        assert global_context.id == "global_singleton"
        assert global_context.organization_name == "Test Org"
        assert global_context.global_settings["theme"] == "dark"
        assert global_context.metadata["version"] == "1.0"
        
        data = global_context.dict()
        assert data["id"] == "global_singleton"
        assert data["organization_name"] == "Test Org"
    
    def test_project_context(self):
        """Test ProjectContext entity."""
        project_context = ProjectContext(
            id="project-123",
            project_name="Test Project",
            project_settings={"language": "python", "framework": "fastapi"},
            metadata={"created": "2024-01-01"}
        )
        
        assert project_context.id == "project-123"
        assert project_context.project_name == "Test Project"
        assert project_context.project_settings["language"] == "python"
        
        data = project_context.dict()
        assert data["project_name"] == "Test Project"
    
    def test_branch_context(self):
        """Test BranchContext entity."""
        branch_context = BranchContext(
            id="branch-456",
            project_id="project-123",
            git_branch_name="feature/auth",
            branch_settings={"auto_deploy": False},
            metadata={"last_commit": "abc123"}
        )
        
        assert branch_context.id == "branch-456"
        assert branch_context.project_id == "project-123"
        assert branch_context.git_branch_name == "feature/auth"
        
        data = branch_context.dict()
        assert data["git_branch_name"] == "feature/auth"
    
    def test_task_context_unified(self):
        """Test TaskContextUnified entity."""
        task_context = TaskContextUnified(
            id="task-789",
            branch_id="branch-456",
            task_data={"title": "Test Task", "status": "in_progress"},
            progress=50,
            insights=[{"type": "performance", "note": "Optimized query"}],
            next_steps=["Add tests", "Update docs"],
            metadata={"agent": "@coding_agent"}
        )
        
        assert task_context.id == "task-789"
        assert task_context.branch_id == "branch-456"
        assert task_context.progress == 50
        assert len(task_context.insights) == 1
        assert len(task_context.next_steps) == 2
        
        data = task_context.dict()
        assert data["progress"] == 50
        assert len(data["next_steps"]) == 2


class TestContextSchema:
    """Test cases for ContextSchema validation and utilities."""
    
    def test_get_default_schema(self):
        """Test getting default JSON schema."""
        schema = ContextSchema.get_default_schema()
        
        assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert schema["type"] == "object"
        assert schema["title"] == "Task Context Schema"
        assert "metadata" in schema["required"]
        assert "objective" in schema["required"]
        assert "metadata" in schema["properties"]
        assert "objective" in schema["properties"]
        assert schema["version"] == ContextSchema.SCHEMA_VERSION
    
    def test_validate_context_valid(self):
        """Test validating valid context data."""
        data = {
            "metadata": {
                "task_id": "task-123",
                "status": "todo",
                "priority": "medium"
            },
            "objective": {
                "title": "Valid Task"
            }
        }
        
        is_valid, errors = ContextSchema.validate_context(data)
        assert is_valid is True
        assert errors == []
    
    def test_validate_context_missing_required(self):
        """Test validation fails with missing required fields."""
        data = {
            "metadata": {
                "task_id": "task-123"
            }
            # Missing objective
        }
        
        is_valid, errors = ContextSchema.validate_context(data)
        assert is_valid is False
        assert "Missing required field: objective" in errors
    
    def test_validate_context_missing_nested_required(self):
        """Test validation fails with missing nested required fields."""
        data = {
            "metadata": {
                # Missing task_id
                "status": "todo"
            },
            "objective": {
                # Missing title
                "description": "Has description but no title"
            }
        }
        
        is_valid, errors = ContextSchema.validate_context(data)
        assert is_valid is False
        assert "Missing required field: metadata.task_id" in errors
        assert "Missing required field: objective.title" in errors
    
    def test_create_empty_context(self):
        """Test creating empty context with schema factory."""
        context = ContextSchema.create_empty_context(
            task_id="new-task",
            title="New Task",
            description="A new task",
            status="in_progress",
            priority="high",
            assignees=["@user1"],
            labels=["urgent"]
        )
        
        assert context.metadata.task_id == "new-task"
        assert context.objective.title == "New Task"
        assert context.objective.description == "A new task"
        assert context.metadata.status.value == TaskStatusEnum.IN_PROGRESS.value
        assert context.metadata.priority.value == "high"
        assert context.metadata.assignees == ["@user1"]
        assert context.metadata.labels == ["urgent"]


if __name__ == "__main__":
    pytest.main([__file__])