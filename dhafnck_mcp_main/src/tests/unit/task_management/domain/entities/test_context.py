"""Unit tests for Context entity and related classes."""

import pytest
from datetime import datetime, timezone
from fastmcp.task_management.domain.entities.context import (
    ContextMetadata, ContextObjective, ContextRequirement, ContextRequirements,
    ContextTechnical, ContextDependency, ContextDependencies, ContextProgressAction,
    ContextProgress, ContextInsight, ContextNotes, ContextSubtask, ContextSubtasks,
    ContextCustomSection, TaskContext, ContextSchema
)
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus


class TestContextMetadata:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test ContextMetadata dataclass."""
    
    def test_metadata_creation_minimal(self):
        """Test creating metadata with minimal required fields."""
        metadata = ContextMetadata(task_id="task-123")
        
        assert metadata.task_id == "task-123"
        assert metadata.status.value == "todo"
        assert metadata.priority.value == "medium"
        assert metadata.assignees == []
        assert metadata.labels == []
        assert metadata.version == 1
        assert isinstance(metadata.created_at, datetime)
        assert isinstance(metadata.updated_at, datetime)
    
    def test_metadata_creation_full(self):
        """Test creating metadata with all fields."""
        now = datetime.now(timezone.utc)
        metadata = ContextMetadata(
            task_id="task-456",
            status=TaskStatus.in_progress(),
            priority=Priority.high(),
            assignees=["user1", "user2"],
            labels=["backend", "urgent"],
            created_at=now,
            updated_at=now,
            version=2
        )
        
        assert metadata.task_id == "task-456"
        assert metadata.status.value == "in_progress"
        assert metadata.priority.value == "high"
        assert metadata.assignees == ["user1", "user2"]
        assert metadata.labels == ["backend", "urgent"]
        assert metadata.created_at == now
        assert metadata.updated_at == now
        assert metadata.version == 2


class TestContextObjective:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test ContextObjective dataclass."""
    
    def test_objective_creation_minimal(self):
        """Test creating objective with minimal fields."""
        objective = ContextObjective(title="Test Task")
        
        assert objective.title == "Test Task"
        assert objective.description == ""
        assert objective.estimated_effort is None
        assert objective.due_date is None
    
    def test_objective_creation_full(self):
        """Test creating objective with all fields."""
        due_date = datetime.now(timezone.utc)
        objective = ContextObjective(
            title="Complete Feature",
            description="Implement user authentication",
            estimated_effort="3 days",
            due_date=due_date
        )
        
        assert objective.title == "Complete Feature"
        assert objective.description == "Implement user authentication"
        assert objective.estimated_effort == "3 days"
        assert objective.due_date == due_date


class TestContextRequirement:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test ContextRequirement and ContextRequirements."""
    
    def test_requirement_creation(self):
        """Test creating individual requirement."""
        req = ContextRequirement(
            id="req-1",
            title="Add validation",
            completed=False,
            priority=Priority.high(),
            notes="Must validate email format"
        )
        
        assert req.id == "req-1"
        assert req.title == "Add validation"
        assert req.completed is False
        assert req.priority.value == "high"
        assert req.notes == "Must validate email format"
    
    def test_requirements_section(self):
        """Test requirements section with multiple items."""
        req1 = ContextRequirement(id="r1", title="Requirement 1")
        req2 = ContextRequirement(id="r2", title="Requirement 2", completed=True)
        
        requirements = ContextRequirements(
            checklist=[req1, req2],
            custom_requirements=["Custom req 1", "Custom req 2"],
            completion_criteria=["All tests pass", "Code review approved"]
        )
        
        assert len(requirements.checklist) == 2
        assert requirements.checklist[0].title == "Requirement 1"
        assert requirements.checklist[1].completed is True
        assert len(requirements.custom_requirements) == 2
        assert len(requirements.completion_criteria) == 2


class TestContextDependency:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test ContextDependency and ContextDependencies."""
    
    def test_dependency_creation(self):
        """Test creating individual dependency."""
        dep = ContextDependency(
            task_id="dep-task-1",
            title="API Implementation",
            status=TaskStatus.in_progress(),
            blocking_reason="Need API endpoints before UI"
        )
        
        assert dep.task_id == "dep-task-1"
        assert dep.title == "API Implementation"
        assert dep.status.value == "in_progress"
        assert dep.blocking_reason == "Need API endpoints before UI"
    
    def test_dependencies_section(self):
        """Test dependencies section."""
        dep1 = ContextDependency(task_id="t1", title="Task 1")
        dep2 = ContextDependency(task_id="t2", title="Task 2")
        
        dependencies = ContextDependencies(
            task_dependencies=[dep1, dep2],
            external_dependencies=["Database setup", "API key"],
            blocked_by=["task-3", "task-4"]
        )
        
        assert len(dependencies.task_dependencies) == 2
        assert len(dependencies.external_dependencies) == 2
        assert len(dependencies.blocked_by) == 2


class TestContextProgress:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test progress tracking classes."""
    
    def test_progress_action_creation(self):
        """Test creating progress action."""
        action = ContextProgressAction(
            timestamp="2024-01-01T12:00:00Z",
            action="Implemented login endpoint",
            agent="backend-agent",
            details="Added JWT authentication",
            status="completed"
        )
        
        assert action.timestamp == "2024-01-01T12:00:00Z"
        assert action.action == "Implemented login endpoint"
        assert action.agent == "backend-agent"
        assert action.details == "Added JWT authentication"
        assert action.status == "completed"
    
    def test_progress_section(self):
        """Test progress section with vision fields."""
        action1 = ContextProgressAction(
            timestamp="2024-01-01T10:00:00Z",
            action="Started task",
            agent="agent-1"
        )
        
        progress = ContextProgress(
            completed_actions=[action1],
            current_session_summary="Working on authentication",
            next_steps=["Add tests", "Code review"],
            completion_percentage=75.0,
            time_spent_minutes=120,
            completion_summary="Implemented full authentication system",
            testing_notes="All tests passing, 95% coverage",
            next_recommendations="Consider adding 2FA",
            vision_alignment_score=0.85
        )
        
        assert len(progress.completed_actions) == 1
        assert progress.current_session_summary == "Working on authentication"
        assert len(progress.next_steps) == 2
        assert progress.completion_percentage == 75.0
        assert progress.time_spent_minutes == 120
        assert progress.completion_summary == "Implemented full authentication system"
        assert progress.testing_notes == "All tests passing, 95% coverage"
        assert progress.next_recommendations == "Consider adding 2FA"
        assert progress.vision_alignment_score == 0.85


class TestContextInsight:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test insight and notes classes."""
    
    def test_insight_creation(self):
        """Test creating insight."""
        insight = ContextInsight(
            timestamp="2024-01-01T14:00:00Z",
            agent="analysis-agent",
            category="insight",
            content="Consider using Redis for caching",
            importance="high"
        )
        
        assert insight.timestamp == "2024-01-01T14:00:00Z"
        assert insight.agent == "analysis-agent"
        assert insight.category == "insight"
        assert insight.content == "Consider using Redis for caching"
        assert insight.importance == "high"
    
    def test_notes_section(self):
        """Test notes section with various insights."""
        insight1 = ContextInsight(
            timestamp="2024-01-01T10:00:00Z",
            agent="agent-1",
            category="insight",
            content="Found existing utility"
        )
        challenge1 = ContextInsight(
            timestamp="2024-01-01T11:00:00Z",
            agent="agent-1",
            category="challenge",
            content="Database connection issues"
        )
        solution1 = ContextInsight(
            timestamp="2024-01-01T12:00:00Z",
            agent="agent-1",
            category="solution",
            content="Used connection pooling"
        )
        decision1 = ContextInsight(
            timestamp="2024-01-01T13:00:00Z",
            agent="agent-1",
            category="decision",
            content="Chose PostgreSQL over MySQL"
        )
        
        notes = ContextNotes(
            agent_insights=[insight1],
            challenges_encountered=[challenge1],
            solutions_applied=[solution1],
            decisions_made=[decision1],
            general_notes="This task requires careful planning"
        )
        
        assert len(notes.agent_insights) == 1
        assert len(notes.challenges_encountered) == 1
        assert len(notes.solutions_applied) == 1
        assert len(notes.decisions_made) == 1
        assert notes.general_notes == "This task requires careful planning"


class TestContextSubtask:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test subtask classes."""
    
    def test_subtask_creation(self):
        """Test creating subtask."""
        subtask = ContextSubtask(
            id="sub-1",
            title="Write unit tests",
            description="Cover all edge cases",
            status=TaskStatus.done(),
            assignees=["test-agent"],
            completed=True,
            progress_notes="All tests written and passing"
        )
        
        assert subtask.id == "sub-1"
        assert subtask.title == "Write unit tests"
        assert subtask.description == "Cover all edge cases"
        assert subtask.status.value == "done"
        assert subtask.assignees == ["test-agent"]
        assert subtask.completed is True
        assert subtask.progress_notes == "All tests written and passing"
    
    def test_subtasks_section(self):
        """Test subtasks section with progress tracking."""
        sub1 = ContextSubtask(id="s1", title="Subtask 1", completed=True)
        sub2 = ContextSubtask(id="s2", title="Subtask 2", completed=False)
        sub3 = ContextSubtask(id="s3", title="Subtask 3", completed=True)
        
        subtasks = ContextSubtasks(
            items=[sub1, sub2, sub3],
            total_count=3,
            completed_count=2,
            progress_percentage=66.67
        )
        
        assert len(subtasks.items) == 3
        assert subtasks.total_count == 3
        assert subtasks.completed_count == 2
        assert subtasks.progress_percentage == 66.67


class TestContextCustomSection:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test custom section functionality."""
    
    def test_custom_section_creation(self):
        """Test creating custom section."""
        custom = ContextCustomSection(
            name="performance_metrics",
            data={
                "response_time": 250,
                "throughput": 1000,
                "error_rate": 0.01
            },
            schema_version="1.0"
        )
        
        assert custom.name == "performance_metrics"
        assert custom.data["response_time"] == 250
        assert custom.data["throughput"] == 1000
        assert custom.data["error_rate"] == 0.01
        assert custom.schema_version == "1.0"


class TestTaskContext:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test main TaskContext class."""
    
    def test_context_creation_minimal(self):
        """Test creating context with minimal required fields."""
        metadata = ContextMetadata(task_id="ctx-task-1")
        objective = ContextObjective(title="Test Context")
        
        context = TaskContext(metadata=metadata, objective=objective)
        
        assert context.metadata.task_id == "ctx-task-1"
        assert context.objective.title == "Test Context"
        assert isinstance(context.requirements, ContextRequirements)
        assert isinstance(context.technical, ContextTechnical)
        assert isinstance(context.dependencies, ContextDependencies)
        assert isinstance(context.progress, ContextProgress)
        assert isinstance(context.subtasks, ContextSubtasks)
        assert isinstance(context.notes, ContextNotes)
        assert context.custom_sections == []
    
    def test_update_completion_summary(self):
        """Test updating completion summary (Vision System requirement)."""
        metadata = ContextMetadata(task_id="test-task")
        objective = ContextObjective(title="Test Task")
        context = TaskContext(metadata=metadata, objective=objective)
        
        # Store original timestamp
        original_updated_at = context.metadata.updated_at
        
        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        # Update with all fields
        context.update_completion_summary(
            completion_summary="Task completed successfully",
            testing_notes="All tests passing",
            next_recommendations="Consider adding more tests"
        )
        
        assert context.progress.completion_summary == "Task completed successfully"
        assert context.progress.testing_notes == "All tests passing"
        assert context.progress.next_recommendations == "Consider adding more tests"
        assert context.metadata.updated_at > original_updated_at
    
    def test_update_completion_summary_empty_raises_error(self):
        """Test that empty completion summary raises error."""
        metadata = ContextMetadata(task_id="test-task")
        objective = ContextObjective(title="Test Task")
        context = TaskContext(metadata=metadata, objective=objective)
        
        with pytest.raises(ValueError, match="completion_summary cannot be empty"):
            context.update_completion_summary("")
        
        with pytest.raises(ValueError, match="completion_summary cannot be empty"):
            context.update_completion_summary("   ")  # Only whitespace
    
    def test_has_completion_summary(self):
        """Test checking for completion summary."""
        metadata = ContextMetadata(task_id="test-task")
        objective = ContextObjective(title="Test Task")
        context = TaskContext(metadata=metadata, objective=objective)
        
        # Initially no summary
        assert context.has_completion_summary() is False
        
        # After adding summary
        context.update_completion_summary("Task completed")
        assert context.has_completion_summary() is True
        
        # Empty summary after setting
        context.progress.completion_summary = ""
        assert context.has_completion_summary() is False
    
    def test_validate_for_task_completion(self):
        """Test validation for task completion."""
        metadata = ContextMetadata(task_id="test-task")
        objective = ContextObjective(title="Test Task")
        context = TaskContext(metadata=metadata, objective=objective)
        
        # Without completion summary
        is_valid, errors = context.validate_for_task_completion()
        assert is_valid is False
        assert len(errors) == 1
        assert "completion_summary is required" in errors[0]
        
        # With completion summary
        context.update_completion_summary("Task completed")
        is_valid, errors = context.validate_for_task_completion()
        assert is_valid is True
        assert len(errors) == 0


class TestTaskContextSerialization:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test TaskContext serialization and deserialization."""
    
    def test_to_dict_minimal(self):
        """Test converting minimal context to dictionary."""
        metadata = ContextMetadata(task_id="ser-task-1")
        objective = ContextObjective(title="Serialization Test")
        context = TaskContext(metadata=metadata, objective=objective)
        
        result = context.to_dict()
        
        assert isinstance(result, dict)
        assert result["task_id"] == "ser-task-1"  # Root level for compatibility
        assert result["metadata"]["task_id"] == "ser-task-1"
        assert result["metadata"]["status"] == "todo"
        assert result["metadata"]["priority"] == "medium"
        assert result["objective"]["title"] == "Serialization Test"
    
    def test_to_dict_with_value_objects(self):
        """Test that value objects are properly serialized."""
        metadata = ContextMetadata(
            task_id="vo-task",
            status=TaskStatus.in_progress(),
            priority=Priority.high()
        )
        objective = ContextObjective(title="Value Object Test")
        req = ContextRequirement(
            id="r1",
            title="Test Req",
            priority=Priority.critical()
        )
        context = TaskContext(metadata=metadata, objective=objective)
        context.requirements.checklist.append(req)
        
        result = context.to_dict()
        
        # Value objects should be converted to strings
        assert result["metadata"]["status"] == "in_progress"
        assert result["metadata"]["priority"] == "high"
        assert result["requirements"]["checklist"][0]["priority"] == "critical"
    
    def test_to_dict_with_datetime(self):
        """Test that datetime objects are properly serialized."""
        now = datetime.now(timezone.utc)
        metadata = ContextMetadata(
            task_id="dt-task",
            created_at=now,
            updated_at=now
        )
        objective = ContextObjective(
            title="DateTime Test",
            due_date=now
        )
        context = TaskContext(metadata=metadata, objective=objective)
        
        result = context.to_dict()
        
        # Datetime should be ISO format strings
        assert isinstance(result["metadata"]["created_at"], str)
        assert isinstance(result["metadata"]["updated_at"], str)
        assert isinstance(result["objective"]["due_date"], str)
        assert now.isoformat() in result["metadata"]["created_at"]
    
    def test_from_dict_new_format(self):
        """Test creating context from dictionary (new nested format)."""
        data = {
            "metadata": {
                "task_id": "from-dict-1",
                "status": "in_progress",
                "priority": "high",
                "assignees": ["user1"],
                "labels": ["backend"],
                "created_at": "2024-01-01T12:00:00+00:00",
                "updated_at": "2024-01-01T12:00:00+00:00",
                "version": 2
            },
            "objective": {
                "title": "Test Task",
                "description": "Test description",
                "estimated_effort": "2 days",
                "due_date": "2024-01-05T12:00:00+00:00"
            }
        }
        
        context = TaskContext.from_dict(data)
        
        assert context.metadata.task_id == "from-dict-1"
        assert context.metadata.status.value == "in_progress"
        assert context.metadata.priority.value == "high"
        assert context.metadata.assignees == ["user1"]
        assert context.metadata.labels == ["backend"]
        assert context.metadata.version == 2
        assert context.objective.title == "Test Task"
        assert context.objective.description == "Test description"
        assert context.objective.estimated_effort == "2 days"
        assert isinstance(context.objective.due_date, datetime)
    
    def test_from_dict_old_format(self):
        """Test creating context from dictionary (old flat format for backward compatibility)."""
        data = {
            "task_id": "old-format-1",
            "status": "todo",
            "priority": "medium",
            "assignees": ["user2"],
            "labels": ["frontend"],
            "title": "Old Format Task",
            "description": "Testing backward compatibility"
        }
        
        context = TaskContext.from_dict(data)
        
        assert context.metadata.task_id == "old-format-1"
        assert context.metadata.status.value == "todo"
        assert context.metadata.priority.value == "medium"
        assert context.metadata.assignees == ["user2"]
        assert context.metadata.labels == ["frontend"]
        assert context.objective.title == "Old Format Task"
        assert context.objective.description == "Testing backward compatibility"
    
    def test_from_dict_with_all_sections(self):
        """Test creating context from dictionary with all sections."""
        data = {
            "metadata": {"task_id": "full-task"},
            "objective": {"title": "Full Task"},
            "requirements": {
                "checklist": [
                    {"id": "r1", "title": "Req 1", "priority": "high", "completed": True}
                ],
                "custom_requirements": ["Custom 1"],
                "completion_criteria": ["All done"]
            },
            "technical": {
                "technologies": ["Python", "FastAPI"],
                "frameworks": ["pytest"],
                "database": "PostgreSQL"
            },
            "dependencies": {
                "task_dependencies": [
                    {"task_id": "dep-1", "title": "Dependency", "status": "done"}
                ],
                "external_dependencies": ["API"],
                "blocked_by": ["task-2"]
            },
            "progress": {
                "completed_actions": [
                    {
                        "timestamp": "2024-01-01T10:00:00Z",
                        "action": "Started",
                        "agent": "agent-1"
                    }
                ],
                "completion_percentage": 50.0,
                "completion_summary": "Half done",
                "vision_alignment_score": 0.75
            },
            "subtasks": {
                "items": [
                    {"id": "s1", "title": "Subtask 1", "status": "done", "completed": True}
                ],
                "total_count": 1,
                "completed_count": 1,
                "progress_percentage": 100.0
            },
            "notes": {
                "agent_insights": [
                    {
                        "timestamp": "2024-01-01T11:00:00Z",
                        "agent": "agent-1",
                        "category": "insight",
                        "content": "Found optimization"
                    }
                ],
                "general_notes": "Going well"
            },
            "custom_sections": [
                {
                    "name": "metrics",
                    "data": {"speed": 100},
                    "schema_version": "1.0"
                }
            ]
        }
        
        context = TaskContext.from_dict(data)
        
        # Check all sections loaded
        assert len(context.requirements.checklist) == 1
        assert context.requirements.checklist[0].priority.value == "high"
        assert context.requirements.checklist[0].completed is True
        
        assert len(context.technical.technologies) == 2
        assert context.technical.database == "PostgreSQL"
        
        assert len(context.dependencies.task_dependencies) == 1
        assert context.dependencies.task_dependencies[0].status.value == "done"
        
        assert len(context.progress.completed_actions) == 1
        assert context.progress.completion_percentage == 50.0
        assert context.progress.completion_summary == "Half done"
        
        assert len(context.subtasks.items) == 1
        assert context.subtasks.items[0].completed is True
        
        assert len(context.notes.agent_insights) == 1
        assert context.notes.general_notes == "Going well"
        
        assert len(context.custom_sections) == 1
        assert context.custom_sections[0].name == "metrics"
    
    def test_round_trip_serialization(self):
        """Test that serialization and deserialization preserve data."""
        # Create complex context
        metadata = ContextMetadata(
            task_id="round-trip",
            status=TaskStatus.in_progress(),
            priority=Priority.high()
        )
        objective = ContextObjective(
            title="Round Trip Test",
            description="Testing serialization"
        )
        context = TaskContext(metadata=metadata, objective=objective)
        
        # Add some data
        context.requirements.checklist.append(
            ContextRequirement(id="r1", title="Test Req", priority=Priority.critical())
        )
        context.progress.completion_summary = "In progress"
        context.notes.general_notes = "Test notes"
        
        # Serialize and deserialize
        data = context.to_dict()
        restored = TaskContext.from_dict(data)
        
        # Verify data preserved
        assert restored.metadata.task_id == "round-trip"
        assert restored.metadata.status.value == "in_progress"
        assert restored.metadata.priority.value == "high"
        assert restored.objective.title == "Round Trip Test"
        assert len(restored.requirements.checklist) == 1
        assert restored.requirements.checklist[0].priority.value == "critical"
        assert restored.progress.completion_summary == "In progress"
        assert restored.notes.general_notes == "Test notes"


class TestContextSchema:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test ContextSchema validation and utilities."""
    
    def test_get_default_schema(self):
        """Test getting default schema."""
        schema = ContextSchema.get_default_schema()
        
        assert isinstance(schema, dict)
        assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert schema["type"] == "object"
        assert schema["title"] == "Task Context Schema"
        assert schema["version"] == ContextSchema.SCHEMA_VERSION
        assert "metadata" in schema["required"]
        assert "objective" in schema["required"]
        assert "properties" in schema
    
    def test_validate_context_valid(self):
        """Test validating valid context data."""
        valid_data = {
            "metadata": {"task_id": "test-123"},
            "objective": {"title": "Test Task"}
        }
        
        is_valid, errors = ContextSchema.validate_context(valid_data)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_context_invalid(self):
        """Test validating invalid context data."""
        # Not a dictionary
        is_valid, errors = ContextSchema.validate_context("not a dict")
        assert is_valid is False
        assert "must be a dictionary" in errors[0]
        
        # Missing required fields
        is_valid, errors = ContextSchema.validate_context({})
        assert is_valid is False
        assert any("metadata" in e for e in errors)
        assert any("objective" in e for e in errors)
        
        # Missing task_id in metadata
        is_valid, errors = ContextSchema.validate_context({
            "metadata": {},
            "objective": {"title": "Test"}
        })
        assert is_valid is False
        assert any("task_id" in e for e in errors)
        
        # Missing title in objective
        is_valid, errors = ContextSchema.validate_context({
            "metadata": {"task_id": "123"},
            "objective": {}
        })
        assert is_valid is False
        assert any("title" in e for e in errors)
    
    def test_create_empty_context(self):
        """Test creating empty context with minimal fields."""
        context = ContextSchema.create_empty_context(
            task_id="empty-123",
            title="Empty Context Test"
        )
        
        assert context.metadata.task_id == "empty-123"
        assert context.objective.title == "Empty Context Test"
        assert context.metadata.status.value == "todo"
        assert context.metadata.priority.value == "medium"
        
        # With optional fields
        context2 = ContextSchema.create_empty_context(
            task_id="empty-456",
            title="Another Test",
            status="in_progress",
            priority="high",
            description="Test description",
            assignees=["user1"],
            labels=["test"]
        )
        
        assert context2.metadata.task_id == "empty-456"
        assert context2.metadata.status.value == "in_progress"
        assert context2.metadata.priority.value == "high"
        assert context2.objective.description == "Test description"
        assert context2.metadata.assignees == ["user1"]
        assert context2.metadata.labels == ["test"]


class TestContextIntegration:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Integration tests for Context functionality."""
    
    def test_full_context_workflow(self):
        """Test complete context workflow from creation to completion."""
        # Create context
        context = ContextSchema.create_empty_context(
            task_id="workflow-test",
            title="Test Workflow Task",
            description="Testing full workflow"
        )
        
        # Add requirements
        context.requirements.checklist.append(
            ContextRequirement(
                id="req-1",
                title="Implement feature",
                priority=Priority.high()
            )
        )
        context.requirements.completion_criteria.append("All tests pass")
        
        # Add technical details
        context.technical.technologies.extend(["Python", "FastAPI"])
        context.technical.database = "PostgreSQL"
        
        # Add progress
        context.progress.completed_actions.append(
            ContextProgressAction(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action="Started implementation",
                agent="dev-agent"
            )
        )
        context.progress.completion_percentage = 25.0
        
        # Add subtasks
        context.subtasks.items.append(
            ContextSubtask(
                id="sub-1",
                title="Write tests",
                status=TaskStatus.todo()
            )
        )
        context.subtasks.total_count = 1
        
        # Add insights
        context.notes.agent_insights.append(
            ContextInsight(
                timestamp=datetime.now(timezone.utc).isoformat(),
                agent="dev-agent",
                category="insight",
                content="Found existing utility function",
                importance="medium"
            )
        )
        
        # Validate before completion
        is_valid, errors = context.validate_for_task_completion()
        assert is_valid is False  # No completion summary
        
        # Complete the task
        context.update_completion_summary(
            completion_summary="Successfully implemented feature with tests",
            testing_notes="All tests passing, 100% coverage",
            next_recommendations="Consider adding performance tests"
        )
        
        # Update subtask
        context.subtasks.items[0].completed = True
        context.subtasks.items[0].status = TaskStatus.done()
        context.subtasks.completed_count = 1
        context.subtasks.progress_percentage = 100.0
        
        # Update progress
        context.progress.completion_percentage = 100.0
        
        # Final validation
        is_valid, errors = context.validate_for_task_completion()
        assert is_valid is True
        assert len(errors) == 0
        
        # Serialize to verify structure
        data = context.to_dict()
        assert data["progress"]["completion_summary"] == "Successfully implemented feature with tests"
        assert data["subtasks"]["progress_percentage"] == 100.0
        assert len(data["notes"]["agent_insights"]) == 1
        
        # Verify can restore from serialized data
        restored = TaskContext.from_dict(data)
        assert restored.has_completion_summary()
        assert restored.progress.completion_percentage == 100.0