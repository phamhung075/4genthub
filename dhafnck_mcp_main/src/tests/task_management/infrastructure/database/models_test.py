"""
Comprehensive tests for database models

This module tests all SQLAlchemy ORM models including:
- Model creation and validation
- Relationships and foreign key constraints
- Data integrity and constraints
- User isolation fields
- Database schema validation
"""

import pytest
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, StatementError

from fastmcp.task_management.infrastructure.database.models import (
    Base, APIToken, Project, ProjectGitBranch, Task, TaskSubtask, TaskAssignee,
    TaskDependency, Agent, Label, TaskLabel, Template, GlobalContext, ProjectContext,
    BranchContext, TaskContext, ContextDelegation, ContextInheritanceCache,
    GLOBAL_SINGLETON_UUID
)


class TestDatabaseModels:
    """Test suite for database models"""
    
    @pytest.fixture(scope="function")
    def engine(self):
        """Create in-memory SQLite database for testing"""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture(scope="function")
    def session(self, engine):
        """Create database session"""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    def test_api_token_model_creation(self, session):
        """Test APIToken model creation and basic functionality"""
        token = APIToken(
            id="token-123",
            user_id="user-123",
            name="Test Token",
            token_hash="hashed_token_value",
            scopes=["read", "write"],
            expires_at=datetime.now(timezone.utc) + timedelta(days=30)
        )
        
        session.add(token)
        session.commit()
        
        retrieved = session.query(APIToken).filter_by(id="token-123").first()
        assert retrieved is not None
        assert retrieved.name == "Test Token"
        assert retrieved.scopes == ["read", "write"]
        assert retrieved.usage_count == 0
        assert retrieved.is_active is True
    
    def test_project_model_creation(self, session):
        """Test Project model creation and validation"""
        project_id = str(uuid.uuid4())
        project = Project(
            id=project_id,
            name="Test Project",
            description="Test project description",
            user_id="user-123"
        )
        
        session.add(project)
        session.commit()
        
        retrieved = session.query(Project).filter_by(id=project_id).first()
        assert retrieved is not None
        assert retrieved.name == "Test Project"
        assert retrieved.status == "active"
        assert retrieved.user_id == "user-123"
        assert retrieved.created_at is not None
        assert retrieved.updated_at is not None
    
    def test_project_git_branch_model_creation(self, session):
        """Test ProjectGitBranch model creation and foreign key relationship"""
        # First create a project
        project_id = str(uuid.uuid4())
        project = Project(
            id=project_id,
            name="Test Project",
            user_id="user-123"
        )
        session.add(project)
        session.commit()
        
        # Create git branch
        branch_id = str(uuid.uuid4())
        git_branch = ProjectGitBranch(
            id=branch_id,
            project_id=project_id,
            name="feature/test-branch",
            description="Test branch description",
            user_id="user-123"
        )
        
        session.add(git_branch)
        session.commit()
        
        retrieved = session.query(ProjectGitBranch).filter_by(id=branch_id).first()
        assert retrieved is not None
        assert retrieved.name == "feature/test-branch"
        assert retrieved.project_id == project_id
        assert retrieved.task_count == 0
        assert retrieved.completed_task_count == 0
        assert retrieved.priority == "medium"
        assert retrieved.status == "todo"
        
        # Test relationship
        assert retrieved.project.id == project_id
    
    def test_task_model_creation(self, session):
        """Test Task model creation and all field validation"""
        # Create prerequisites
        project_id = str(uuid.uuid4())
        project = Project(id=project_id, name="Test Project", user_id="user-123")
        session.add(project)
        
        branch_id = str(uuid.uuid4())
        git_branch = ProjectGitBranch(
            id=branch_id,
            project_id=project_id,
            name="test-branch",
            user_id="user-123"
        )
        session.add(git_branch)
        session.commit()
        
        # Create task
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            title="Test Task",
            description="Test task description",
            git_branch_id=branch_id,
            status="todo",
            priority="high",
            details="Additional details",
            estimated_effort="2 hours",
            due_date="2024-12-31",
            progress_percentage=25,
            user_id="user-123"
        )
        
        session.add(task)
        session.commit()
        
        retrieved = session.query(Task).filter_by(id=task_id).first()
        assert retrieved is not None
        assert retrieved.title == "Test Task"
        assert retrieved.git_branch_id == branch_id
        assert retrieved.status == "todo"
        assert retrieved.priority == "high"
        assert retrieved.progress_percentage == 25
        assert retrieved.user_id == "user-123"
        assert retrieved.created_at is not None
        assert retrieved.updated_at is not None
        
        # Test relationship
        assert retrieved.git_branch.id == branch_id
    
    def test_task_subtask_model_creation(self, session):
        """Test TaskSubtask model creation and relationship"""
        # Create prerequisites
        project_id = str(uuid.uuid4())
        project = Project(id=project_id, name="Test Project", user_id="user-123")
        session.add(project)
        
        branch_id = str(uuid.uuid4())
        git_branch = ProjectGitBranch(
            id=branch_id,
            project_id=project_id,
            name="test-branch",
            user_id="user-123"
        )
        session.add(git_branch)
        
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            title="Parent Task",
            description="Parent task",
            git_branch_id=branch_id,
            user_id="user-123"
        )
        session.add(task)
        session.commit()
        
        # Create subtask
        subtask_id = str(uuid.uuid4())
        subtask = TaskSubtask(
            id=subtask_id,
            task_id=task_id,
            title="Test Subtask",
            description="Subtask description",
            status="in_progress",
            priority="medium",
            assignees=["user1", "user2"],
            progress_percentage=75,
            insights_found=["insight1", "insight2"],
            user_id="user-123"
        )
        
        session.add(subtask)
        session.commit()
        
        retrieved = session.query(TaskSubtask).filter_by(id=subtask_id).first()
        assert retrieved is not None
        assert retrieved.title == "Test Subtask"
        assert retrieved.task_id == task_id
        assert retrieved.assignees == ["user1", "user2"]
        assert retrieved.progress_percentage == 75
        assert retrieved.insights_found == ["insight1", "insight2"]
        
        # Test relationship
        assert retrieved.task.id == task_id
    
    def test_task_assignee_model_creation(self, session):
        """Test TaskAssignee model creation and unique constraint"""
        # Create prerequisites
        project_id = str(uuid.uuid4())
        project = Project(id=project_id, name="Test Project", user_id="user-123")
        session.add(project)
        
        branch_id = str(uuid.uuid4())
        git_branch = ProjectGitBranch(
            id=branch_id,
            project_id=project_id,
            name="test-branch",
            user_id="user-123"
        )
        session.add(git_branch)
        
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            title="Test Task",
            description="Test task",
            git_branch_id=branch_id,
            user_id="user-123"
        )
        session.add(task)
        session.commit()
        
        # Create assignee
        assignee_id = str(uuid.uuid4())
        assignee = TaskAssignee(
            id=assignee_id,
            task_id=task_id,
            assignee_id="user-456",
            role="contributor",
            user_id="user-123"
        )
        
        session.add(assignee)
        session.commit()
        
        retrieved = session.query(TaskAssignee).filter_by(id=assignee_id).first()
        assert retrieved is not None
        assert retrieved.assignee_id == "user-456"
        assert retrieved.role == "contributor"
        
        # Test unique constraint violation
        duplicate_assignee = TaskAssignee(
            id=str(uuid.uuid4()),
            task_id=task_id,
            assignee_id="user-456",  # Same assignee for same task
            user_id="user-123"
        )
        session.add(duplicate_assignee)
        
        with pytest.raises(IntegrityError):
            session.commit()
    
    def test_task_dependency_model_creation(self, session):
        """Test TaskDependency model creation and constraints"""
        # Create prerequisites
        project_id = str(uuid.uuid4())
        project = Project(id=project_id, name="Test Project", user_id="user-123")
        session.add(project)
        
        branch_id = str(uuid.uuid4())
        git_branch = ProjectGitBranch(
            id=branch_id,
            project_id=project_id,
            name="test-branch",
            user_id="user-123"
        )
        session.add(git_branch)
        
        # Create two tasks
        task1_id = str(uuid.uuid4())
        task2_id = str(uuid.uuid4())
        
        task1 = Task(
            id=task1_id,
            title="Task 1",
            description="First task",
            git_branch_id=branch_id,
            user_id="user-123"
        )
        task2 = Task(
            id=task2_id,
            title="Task 2",
            description="Second task",
            git_branch_id=branch_id,
            user_id="user-123"
        )
        
        session.add_all([task1, task2])
        session.commit()
        
        # Create dependency
        dependency = TaskDependency(
            task_id=task2_id,
            depends_on_task_id=task1_id,
            dependency_type="blocks",
            user_id="user-123"
        )
        
        session.add(dependency)
        session.commit()
        
        retrieved = session.query(TaskDependency).filter_by(task_id=task2_id).first()
        assert retrieved is not None
        assert retrieved.depends_on_task_id == task1_id
        assert retrieved.dependency_type == "blocks"
        
        # Test self-dependency constraint (should fail)
        session.rollback()
        self_dependency = TaskDependency(
            task_id=task1_id,
            depends_on_task_id=task1_id,  # Self dependency
            user_id="user-123"
        )
        session.add(self_dependency)
        
        with pytest.raises(IntegrityError):
            session.commit()
    
    def test_agent_model_creation(self, session):
        """Test Agent model creation and fields"""
        agent_id = str(uuid.uuid4())
        agent = Agent(
            id=agent_id,
            name="Test Agent",
            description="Test agent description",
            role="assistant",
            capabilities=["coding", "testing"],
            status="available",
            availability_score=0.8,
            user_id=str(uuid.uuid4())
        )
        
        session.add(agent)
        session.commit()
        
        retrieved = session.query(Agent).filter_by(id=agent_id).first()
        assert retrieved is not None
        assert retrieved.name == "Test Agent"
        assert retrieved.capabilities == ["coding", "testing"]
        assert retrieved.availability_score == 0.8
        assert retrieved.status == "available"
    
    def test_label_and_task_label_relationship(self, session):
        """Test Label and TaskLabel models and their relationship"""
        # Create prerequisites
        project_id = str(uuid.uuid4())
        project = Project(id=project_id, name="Test Project", user_id="user-123")
        session.add(project)
        
        branch_id = str(uuid.uuid4())
        git_branch = ProjectGitBranch(
            id=branch_id,
            project_id=project_id,
            name="test-branch",
            user_id="user-123"
        )
        session.add(git_branch)
        
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            title="Test Task",
            description="Test task",
            git_branch_id=branch_id,
            user_id="user-123"
        )
        session.add(task)
        
        # Create label
        label = Label(
            id="label-123",
            name="bug",
            color="#ff0000",
            description="Bug label",
            user_id="user-123"
        )
        session.add(label)
        session.commit()
        
        # Create task-label relationship
        task_label = TaskLabel(
            task_id=task_id,
            label_id="label-123",
            user_id="user-123"
        )
        session.add(task_label)
        session.commit()
        
        # Test relationships
        retrieved_task_label = session.query(TaskLabel).filter_by(task_id=task_id).first()
        assert retrieved_task_label is not None
        assert retrieved_task_label.label.name == "bug"
        assert retrieved_task_label.task.title == "Test Task"
    
    def test_template_model_creation(self, session):
        """Test Template model creation and all fields"""
        template_id = str(uuid.uuid4())
        template = Template(
            id=template_id,
            name="Test Template",
            template_name="test-template",
            template_content="Template content",
            template_type="task",
            type="task",
            content={"steps": ["step1", "step2"]},
            category="development",
            tags=["coding", "testing"],
            usage_count=5,
            user_id="user-123"
        )
        
        session.add(template)
        session.commit()
        
        retrieved = session.query(Template).filter_by(id=template_id).first()
        assert retrieved is not None
        assert retrieved.name == "Test Template"
        assert retrieved.content == {"steps": ["step1", "step2"]}
        assert retrieved.tags == ["coding", "testing"]
        assert retrieved.usage_count == 5
    
    def test_global_context_model_creation(self, session):
        """Test GlobalContext model creation"""
        context_id = str(uuid.uuid4())
        global_context = GlobalContext(
            id=context_id,
            organization_id=str(uuid.uuid4()),
            autonomous_rules={"rule1": "value1"},
            security_policies={"policy1": "secure"},
            coding_standards={"standard1": "clean"},
            workflow_templates={"template1": "workflow"},
            delegation_rules={"rule1": "delegate"},
            user_id="user-123"
        )
        
        session.add(global_context)
        session.commit()
        
        retrieved = session.query(GlobalContext).filter_by(id=context_id).first()
        assert retrieved is not None
        assert retrieved.autonomous_rules == {"rule1": "value1"}
        assert retrieved.version == 1
        assert retrieved.user_id == "user-123"
    
    def test_project_context_model_creation(self, session):
        """Test ProjectContext model creation and relationship to GlobalContext"""
        # Create global context first
        global_context_id = str(uuid.uuid4())
        global_context = GlobalContext(
            id=global_context_id,
            user_id="user-123"
        )
        session.add(global_context)
        session.commit()
        
        # Create project context
        project_context_id = str(uuid.uuid4())
        project_context = ProjectContext(
            id=project_context_id,
            project_id=str(uuid.uuid4()),
            parent_global_id=global_context_id,
            data={"key": "value"},
            team_preferences={"pref1": "value1"},
            technology_stack={"tech1": "value1"},
            user_id="user-123"
        )
        
        session.add(project_context)
        session.commit()
        
        retrieved = session.query(ProjectContext).filter_by(id=project_context_id).first()
        assert retrieved is not None
        assert retrieved.data == {"key": "value"}
        assert retrieved.team_preferences == {"pref1": "value1"}
        assert retrieved.global_context.id == global_context_id
    
    def test_branch_context_model_creation(self, session):
        """Test BranchContext model creation and relationships"""
        # Create prerequisites
        project_id = str(uuid.uuid4())
        project = Project(id=project_id, name="Test Project", user_id="user-123")
        session.add(project)
        
        branch_id = str(uuid.uuid4())
        git_branch = ProjectGitBranch(
            id=branch_id,
            project_id=project_id,
            name="test-branch",
            user_id="user-123"
        )
        session.add(git_branch)
        
        project_context_id = str(uuid.uuid4())
        project_context = ProjectContext(
            id=project_context_id,
            project_id=project_id,
            user_id="user-123"
        )
        session.add(project_context)
        session.commit()
        
        # Create branch context
        branch_context_id = str(uuid.uuid4())
        branch_context = BranchContext(
            id=branch_context_id,
            branch_id=branch_id,
            parent_project_id=project_context_id,
            data={"branch_data": "value"},
            branch_workflow={"workflow": "git"},
            feature_flags={"flag1": True},
            user_id="user-123"
        )
        
        session.add(branch_context)
        session.commit()
        
        retrieved = session.query(BranchContext).filter_by(id=branch_context_id).first()
        assert retrieved is not None
        assert retrieved.data == {"branch_data": "value"}
        assert retrieved.feature_flags == {"flag1": True}
        assert retrieved.git_branch.id == branch_id
        assert retrieved.project_context.id == project_context_id
    
    def test_task_context_model_creation(self, session):
        """Test TaskContext model creation and relationships"""
        # Create prerequisites
        project_id = str(uuid.uuid4())
        project = Project(id=project_id, name="Test Project", user_id="user-123")
        session.add(project)
        
        branch_id = str(uuid.uuid4())
        git_branch = ProjectGitBranch(
            id=branch_id,
            project_id=project_id,
            name="test-branch",
            user_id="user-123"
        )
        session.add(git_branch)
        
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            title="Test Task",
            description="Test task",
            git_branch_id=branch_id,
            user_id="user-123"
        )
        session.add(task)
        
        branch_context_id = str(uuid.uuid4())
        branch_context = BranchContext(
            id=branch_context_id,
            branch_id=branch_id,
            user_id="user-123"
        )
        session.add(branch_context)
        session.commit()
        
        # Create task context
        task_context_id = str(uuid.uuid4())
        task_context = TaskContext(
            id=task_context_id,
            task_id=task_id,
            parent_branch_id=branch_id,
            parent_branch_context_id=branch_context_id,
            data={"task_data": "value"},
            task_data={"specific": "data"},
            execution_context={"exec": "context"},
            user_id="user-123"
        )
        
        session.add(task_context)
        session.commit()
        
        retrieved = session.query(TaskContext).filter_by(id=task_context_id).first()
        assert retrieved is not None
        assert retrieved.data == {"task_data": "value"}
        assert retrieved.task_data == {"specific": "data"}
        assert retrieved.task.id == task_id
        assert retrieved.branch_context.id == branch_context_id
    
    def test_context_delegation_model_creation(self, session):
        """Test ContextDelegation model creation and constraints"""
        delegation_id = str(uuid.uuid4())
        delegation = ContextDelegation(
            id=delegation_id,
            source_level="task",
            source_id=str(uuid.uuid4()),
            source_type="context",
            target_level="project",
            target_id=str(uuid.uuid4()),
            target_type="context",
            delegated_data={"pattern": "auth_flow"},
            delegation_data={"extra": "data"},
            delegation_reason="Reusable authentication pattern",
            trigger_type="manual",
            confidence_score=0.9,
            user_id="user-123"
        )
        
        session.add(delegation)
        session.commit()
        
        retrieved = session.query(ContextDelegation).filter_by(id=delegation_id).first()
        assert retrieved is not None
        assert retrieved.source_level == "task"
        assert retrieved.target_level == "project"
        assert retrieved.delegated_data == {"pattern": "auth_flow"}
        assert retrieved.confidence_score == 0.9
    
    def test_context_inheritance_cache_model_creation(self, session):
        """Test ContextInheritanceCache model creation"""
        cache_id = str(uuid.uuid4())
        context_id = str(uuid.uuid4())
        cache = ContextInheritanceCache(
            id=cache_id,
            context_id=context_id,
            context_level="task",
            context_type="hierarchical",
            resolved_context={"resolved": "data"},
            resolved_data={"extra": "resolved"},
            dependencies_hash="hash123",
            resolution_path="global->project->branch->task",
            parent_chain=[str(uuid.uuid4()), str(uuid.uuid4())],
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            cache_size_bytes=1024,
            user_id="user-123"
        )
        
        session.add(cache)
        session.commit()
        
        retrieved = session.query(ContextInheritanceCache).filter_by(id=cache_id).first()
        assert retrieved is not None
        assert retrieved.context_level == "task"
        assert retrieved.resolved_context == {"resolved": "data"}
        assert retrieved.cache_size_bytes == 1024
        assert len(retrieved.parent_chain) == 2
    
    def test_cascade_deletion_project_to_branches(self, session):
        """Test that deleting a project cascades to delete git branches"""
        project_id = str(uuid.uuid4())
        project = Project(id=project_id, name="Test Project", user_id="user-123")
        session.add(project)
        
        branch_id = str(uuid.uuid4())
        git_branch = ProjectGitBranch(
            id=branch_id,
            project_id=project_id,
            name="test-branch",
            user_id="user-123"
        )
        session.add(git_branch)
        session.commit()
        
        # Verify branch exists
        assert session.query(ProjectGitBranch).filter_by(id=branch_id).first() is not None
        
        # Delete project
        session.delete(project)
        session.commit()
        
        # Verify branch was cascaded deleted
        assert session.query(ProjectGitBranch).filter_by(id=branch_id).first() is None
    
    def test_cascade_deletion_branch_to_tasks(self, session):
        """Test that deleting a git branch cascades to delete tasks"""
        # Create prerequisites
        project_id = str(uuid.uuid4())
        project = Project(id=project_id, name="Test Project", user_id="user-123")
        session.add(project)
        
        branch_id = str(uuid.uuid4())
        git_branch = ProjectGitBranch(
            id=branch_id,
            project_id=project_id,
            name="test-branch",
            user_id="user-123"
        )
        session.add(git_branch)
        
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            title="Test Task",
            description="Test task",
            git_branch_id=branch_id,
            user_id="user-123"
        )
        session.add(task)
        session.commit()
        
        # Verify task exists
        assert session.query(Task).filter_by(id=task_id).first() is not None
        
        # Delete git branch
        session.delete(git_branch)
        session.commit()
        
        # Verify task was cascaded deleted
        assert session.query(Task).filter_by(id=task_id).first() is None
    
    def test_user_isolation_constraints(self, session):
        """Test that user_id fields are properly enforced"""
        # Test that user_id is required for models that have NOT NULL constraint
        with pytest.raises(IntegrityError):
            project = Project(
                id=str(uuid.uuid4()),
                name="Test Project"
                # Missing user_id - should fail
            )
            session.add(project)
            session.commit()
    
    def test_global_singleton_uuid_constant(self):
        """Test that GLOBAL_SINGLETON_UUID is properly defined"""
        assert GLOBAL_SINGLETON_UUID == "00000000-0000-0000-0000-000000000001"
        # Verify it's a valid UUID format
        uuid.UUID(GLOBAL_SINGLETON_UUID)  # Should not raise exception
    
    def test_model_indexes_exist(self, engine):
        """Test that expected database indexes are created"""
        inspector = inspect(engine)
        
        # Test Task model indexes
        task_indexes = inspector.get_indexes("tasks")
        index_names = [idx["name"] for idx in task_indexes]
        
        expected_task_indexes = [
            "idx_task_branch",
            "idx_task_status",
            "idx_task_priority", 
            "idx_task_created"
        ]
        
        for expected_idx in expected_task_indexes:
            assert expected_idx in index_names, f"Missing index: {expected_idx}"
    
    def test_json_fields_functionality(self, session):
        """Test that JSON fields work correctly"""
        # Test with complex nested data
        complex_data = {
            "nested": {
                "array": [1, 2, 3],
                "object": {"key": "value"},
                "boolean": True,
                "null_value": None
            },
            "list": ["item1", "item2", "item3"]
        }
        
        template = Template(
            id=str(uuid.uuid4()),
            name="JSON Test Template",
            type="test",
            content=complex_data,
            tags=["json", "test"],
            user_id="user-123"
        )
        
        session.add(template)
        session.commit()
        
        retrieved = session.query(Template).filter_by(name="JSON Test Template").first()
        assert retrieved.content == complex_data
        assert retrieved.tags == ["json", "test"]
    
    def test_datetime_fields_auto_population(self, session):
        """Test that datetime fields are automatically populated"""
        before_create = datetime.now(timezone.utc)
        
        project = Project(
            id=str(uuid.uuid4()),
            name="Datetime Test Project",
            user_id="user-123"
        )
        
        session.add(project)
        session.commit()
        
        after_create = datetime.now(timezone.utc) + timedelta(seconds=2)  # Add buffer
        
        retrieved = session.query(Project).filter_by(name="Datetime Test Project").first()
        assert retrieved.created_at is not None
        assert retrieved.updated_at is not None
        # Check that timestamps are within reasonable range
        assert before_create <= retrieved.created_at <= after_create
        assert before_create <= retrieved.updated_at <= after_create
    
    def test_unique_constraints_enforcement(self, session):
        """Test that unique constraints are properly enforced"""
        # Test Label name uniqueness
        label1 = Label(id="label-1", name="unique_label", user_id="user-123")
        session.add(label1)
        session.commit()
        
        # Try to create another label with same name
        label2 = Label(id="label-2", name="unique_label", user_id="user-123")
        session.add(label2)
        
        with pytest.raises(IntegrityError):
            session.commit()
    
    def test_foreign_key_constraints(self, session):
        """Test that foreign key constraints are enforced"""
        # Enable foreign keys for this session (needed for SQLite)
        from sqlalchemy import text
        session.execute(text('PRAGMA foreign_keys=ON'))
        
        # Verify foreign keys are now enabled
        result = session.execute(text('PRAGMA foreign_keys'))
        fk_enabled = result.fetchone()[0]
        assert fk_enabled == 1, "Foreign keys should be enabled after setting pragma"
        
        # Try to create a task with non-existent git_branch_id
        non_existent_branch_id = str(uuid.uuid4())  # Use a UUID that definitely doesn't exist
        task = Task(
            id=str(uuid.uuid4()),
            title="Invalid Task",
            description="Task with invalid branch",
            git_branch_id=non_existent_branch_id,
            user_id="user-123"
        )
        session.add(task)
        
        # Force explicit commit in a try/catch to get better error details
        try:
            session.commit()
            # If we get here, foreign key wasn't enforced
            pytest.fail("Expected IntegrityError due to foreign key constraint violation")
        except IntegrityError:
            # This is expected - foreign key constraint should prevent the commit
            pass