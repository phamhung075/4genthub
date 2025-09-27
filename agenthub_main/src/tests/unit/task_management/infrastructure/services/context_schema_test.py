"""Unit tests for context schema infrastructure service"""

import pytest
from datetime import datetime
from dataclasses import is_dataclass
import json

from fastmcp.task_management.infrastructure.services.context_schema import (
    ContextMetadata,
    ContextObjective,
    ContextRequirement,
    ContextRequirements,
    ContextTechnical,
    ContextDependency,
    ContextDependencies,
    ContextProgressAction,
    ContextProgress,
    ContextInsight,
    ContextNotes,
    ContextSubtask,
    ContextSubtasks,
    ContextCustomSection,
    TaskContext,
    ContextSchema
)
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus, TaskStatusEnum
from fastmcp.task_management.domain.value_objects.priority import Priority, PriorityLevel


class TestContextMetadata:
    """Test ContextMetadata dataclass"""
    
    def test_context_metadata_creation(self):
        """Test creating ContextMetadata with all fields"""
        metadata = ContextMetadata(
            task_id="task123",
            project_id="proj456",
            git_branch_id="feature/test",
            user_id="user789",
            status=TaskStatus.in_progress(),
            priority=Priority.high(),
            assignees=["agent1", "agent2"],
            labels=["frontend", "urgent"],
            created_at="2024-09-26T10:00:00",
            updated_at="2024-09-26T11:00:00",
            version="1.1"
        )
        
        assert metadata.task_id == "task123"
        assert metadata.project_id == "proj456"
        assert metadata.git_branch_id == "feature/test"
        assert metadata.user_id == "user789"
        assert str(metadata.status) == "in_progress"
        assert str(metadata.priority) == "high"
        assert metadata.assignees == ["agent1", "agent2"]
        assert metadata.labels == ["frontend", "urgent"]
        assert metadata.version == "1.1"
    
    def test_context_metadata_defaults(self):
        """Test ContextMetadata with default values"""
        metadata = ContextMetadata(
            task_id="task123",
            project_id="proj456"
        )
        
        assert metadata.git_branch_id == "main"
        assert metadata.user_id is None
        assert str(metadata.status) == "todo"
        assert str(metadata.priority) == "medium"
        assert metadata.assignees == []
        assert metadata.labels == []
        assert metadata.version == "1.0"


class TestContextObjective:
    """Test ContextObjective dataclass"""
    
    def test_context_objective_creation(self):
        """Test creating ContextObjective"""
        objective = ContextObjective(
            title="Implement authentication",
            description="Add JWT-based authentication",
            estimated_effort="large",
            due_date="2024-12-31"
        )
        
        assert objective.title == "Implement authentication"
        assert objective.description == "Add JWT-based authentication"
        assert objective.estimated_effort == "large"
        assert objective.due_date == "2024-12-31"
    
    def test_context_objective_defaults(self):
        """Test ContextObjective with defaults"""
        objective = ContextObjective(title="Test task")
        
        assert objective.title == "Test task"
        assert objective.description == ""
        assert objective.estimated_effort == "medium"
        assert objective.due_date is None


class TestContextRequirement:
    """Test ContextRequirement dataclass"""
    
    def test_context_requirement_creation(self):
        """Test creating ContextRequirement"""
        requirement = ContextRequirement(
            id="req1",
            title="Add login endpoint",
            completed=True,
            priority=Priority.high(),
            notes="Use OAuth2"
        )
        
        assert requirement.id == "req1"
        assert requirement.title == "Add login endpoint"
        assert requirement.completed is True
        assert str(requirement.priority) == "high"
        assert requirement.notes == "Use OAuth2"


class TestContextDependency:
    """Test ContextDependency dataclass"""
    
    def test_context_dependency_creation(self):
        """Test creating ContextDependency"""
        dependency = ContextDependency(
            task_id="dep123",
            title="Database setup",
            status=TaskStatus.done(),
            blocking_reason="Tables must exist first"
        )
        
        assert dependency.task_id == "dep123"
        assert dependency.title == "Database setup"
        assert str(dependency.status) == "done"
        assert dependency.blocking_reason == "Tables must exist first"
    
    def test_context_dependency_default_status(self):
        """Test ContextDependency with default status"""
        dependency = ContextDependency(
            task_id="dep123"
        )
        
        # Default status should be "todo" per the context_schema default_factory
        assert dependency.task_id == "dep123"
        assert dependency.title == ""
        # from_string("unknown") actually falls back to "todo"
        assert str(dependency.status) == "todo"  
        assert dependency.blocking_reason == ""


class TestTaskContext:
    """Test TaskContext dataclass and methods"""
    
    def test_task_context_creation(self):
        """Test creating TaskContext with required fields"""
        metadata = ContextMetadata(
            task_id="task123",
            project_id="proj456"
        )
        objective = ContextObjective(
            title="Test task"
        )
        
        context = TaskContext(
            metadata=metadata,
            objective=objective
        )
        
        assert context.metadata.task_id == "task123"
        assert context.objective.title == "Test task"
        assert is_dataclass(context.requirements)
        assert is_dataclass(context.technical)
        assert is_dataclass(context.dependencies)
        assert is_dataclass(context.progress)
        assert is_dataclass(context.subtasks)
        assert is_dataclass(context.notes)
        assert context.custom_sections == []
    
    def test_task_context_to_dict(self):
        """Test converting TaskContext to dictionary"""
        metadata = ContextMetadata(
            task_id="task123",
            project_id="proj456",
            status=TaskStatus.in_progress(),
            priority=Priority.high()
        )
        objective = ContextObjective(
            title="Test task",
            description="Test description"
        )
        
        context = TaskContext(metadata=metadata, objective=objective)
        context_dict = context.to_dict()
        
        assert isinstance(context_dict, dict)
        assert context_dict['metadata']['task_id'] == "task123"
        assert context_dict['metadata']['project_id'] == "proj456"
        assert context_dict['metadata']['status'] == "in_progress"
        assert context_dict['metadata']['priority'] == "high"
        assert context_dict['objective']['title'] == "Test task"
        assert context_dict['objective']['description'] == "Test description"
    
    def test_task_context_from_dict(self):
        """Test creating TaskContext from dictionary"""
        data = {
            'metadata': {
                'task_id': 'task123',
                'project_id': 'proj456',
                'status': 'in_progress',
                'priority': 'high',
                'assignees': ['agent1'],
                'labels': ['test']
            },
            'objective': {
                'title': 'Test task',
                'description': 'From dict test'
            },
            'requirements': {
                'checklist': [{
                    'id': 'req1',
                    'title': 'Requirement 1',
                    'completed': True,
                    'priority': 'medium',
                    'notes': 'Test note'
                }],
                'custom_requirements': ['Custom req 1'],
                'completion_criteria': ['All tests pass']
            },
            'dependencies': {
                'task_dependencies': [{
                    'task_id': 'dep1',
                    'title': 'Dependency task',
                    'status': 'done',
                    'blocking_reason': 'Must finish first'
                }],
                'external_dependencies': ['External API'],
                'blocked_by': ['task999']
            },
            'subtasks': {
                'items': [{
                    'id': 'sub1',
                    'title': 'Subtask 1',
                    'description': 'First subtask',
                    'status': 'todo',
                    'assignees': ['agent2'],
                    'completed': False,
                    'progress_notes': 'Not started'
                }],
                'total_count': 1,
                'completed_count': 0,
                'progress_percentage': 0.0
            }
        }
        
        context = TaskContext.from_dict(data)
        
        assert context.metadata.task_id == 'task123'
        assert context.metadata.project_id == 'proj456'
        assert str(context.metadata.status) == 'in_progress'
        assert str(context.metadata.priority) == 'high'
        assert context.metadata.assignees == ['agent1']
        assert context.metadata.labels == ['test']
        
        assert context.objective.title == 'Test task'
        assert context.objective.description == 'From dict test'
        
        assert len(context.requirements.checklist) == 1
        assert context.requirements.checklist[0].id == 'req1'
        assert context.requirements.checklist[0].completed is True
        assert str(context.requirements.checklist[0].priority) == 'medium'
        
        assert len(context.dependencies.task_dependencies) == 1
        assert context.dependencies.task_dependencies[0].task_id == 'dep1'
        assert str(context.dependencies.task_dependencies[0].status) == 'done'
        
        assert len(context.subtasks.items) == 1
        assert context.subtasks.items[0].id == 'sub1'
        assert str(context.subtasks.items[0].status) == 'todo'
        assert context.subtasks.items[0].assignees == ['agent2']
    
    def test_task_context_roundtrip(self):
        """Test converting to dict and back maintains data"""
        original = TaskContext(
            metadata=ContextMetadata(
                task_id="task123",
                project_id="proj456",
                status=TaskStatus.in_progress(),
                priority=Priority.critical(),
                assignees=["agent1", "agent2"]
            ),
            objective=ContextObjective(
                title="Test roundtrip",
                description="Testing serialization"
            )
        )
        
        # Add some data to other sections
        original.requirements.checklist.append(
            ContextRequirement(
                id="req1",
                title="Test requirement",
                priority=Priority.high()
            )
        )
        
        # Convert to dict and back
        dict_data = original.to_dict()
        reconstructed = TaskContext.from_dict(dict_data)
        
        assert reconstructed.metadata.task_id == original.metadata.task_id
        assert str(reconstructed.metadata.status) == str(original.metadata.status)
        assert str(reconstructed.metadata.priority) == str(original.metadata.priority)
        assert reconstructed.metadata.assignees == original.metadata.assignees
        assert reconstructed.objective.title == original.objective.title
        assert len(reconstructed.requirements.checklist) == 1
        assert reconstructed.requirements.checklist[0].title == "Test requirement"
        assert str(reconstructed.requirements.checklist[0].priority) == "high"


class TestContextSchema:
    """Test ContextSchema static methods"""
    
    def test_get_default_schema(self):
        """Test getting default schema"""
        schema = ContextSchema.get_default_schema()
        
        assert schema['version'] == '1.0'
        assert schema['type'] == 'object'
        assert 'metadata' in schema['required']
        assert 'objective' in schema['required']
        assert 'properties' in schema
        assert 'definitions' in schema
        
        # Check metadata properties
        metadata_props = schema['properties']['metadata']['properties']
        assert 'task_id' in metadata_props
        assert 'project_id' in metadata_props
        assert 'status' in metadata_props
        assert 'priority' in metadata_props
        
        # Check status enum values
        status_enum = metadata_props['status']['enum']
        expected_statuses = [status.value for status in TaskStatusEnum]
        assert set(status_enum) == set(expected_statuses)
        
        # Check priority enum values
        priority_enum = metadata_props['priority']['enum']
        expected_priorities = [priority.label for priority in PriorityLevel]
        assert set(priority_enum) == set(expected_priorities)
    
    def test_validate_context_valid(self):
        """Test validating valid context data"""
        valid_context = {
            'metadata': {
                'task_id': 'task123',
                'project_id': 'proj456'
            },
            'objective': {
                'title': 'Test task'
            }
        }
        
        is_valid, errors = ContextSchema.validate_context(valid_context)
        
        assert is_valid is True
        assert errors == []
    
    def test_validate_context_invalid(self):
        """Test validating invalid context data"""
        # Missing required sections
        invalid_context = {
            'metadata': {
                'task_id': 'task123'
            }
            # Missing objective
        }
        
        is_valid, errors = ContextSchema.validate_context(invalid_context)
        
        assert is_valid is False
        assert len(errors) == 1
        assert 'objective' in errors[0]
    
    def test_validate_context_not_dict(self):
        """Test validating non-dict context data"""
        is_valid, errors = ContextSchema.validate_context("not a dict")
        
        assert is_valid is False
        assert len(errors) == 1
        assert "dictionary" in errors[0]
    
    def test_create_empty_context(self):
        """Test creating empty context with defaults"""
        context = ContextSchema.create_empty_context(
            task_id="task123",
            project_id="proj456",
            title="Empty context test"
        )
        
        assert context.metadata.task_id == "task123"
        assert context.metadata.project_id == "proj456"
        assert context.metadata.git_branch_id == "main"
        assert context.metadata.user_id == ""
        assert str(context.metadata.status) == "todo"
        assert str(context.metadata.priority) == "medium"
        assert context.objective.title == "Empty context test"
        assert context.objective.description == ""
    
    def test_create_empty_context_with_kwargs(self):
        """Test creating empty context with custom values"""
        context = ContextSchema.create_empty_context(
            task_id="task123",
            project_id="proj456",
            title="Custom context",
            git_branch_id="feature/test",
            user_id="user789",
            status="in_progress",
            priority="high",
            assignees=["agent1", "agent2"],
            labels=["urgent"],
            description="Custom description",
            estimated_effort="large",
            due_date="2024-12-31"
        )
        
        assert context.metadata.task_id == "task123"
        assert context.metadata.project_id == "proj456"
        assert context.metadata.git_branch_id == "feature/test"
        assert context.metadata.user_id == "user789"
        assert str(context.metadata.status) == "in_progress"
        assert str(context.metadata.priority) == "high"
        assert context.metadata.assignees == ["agent1", "agent2"]
        assert context.metadata.labels == ["urgent"]
        assert context.objective.title == "Custom context"
        assert context.objective.description == "Custom description"
        assert context.objective.estimated_effort == "large"
        assert context.objective.due_date == "2024-12-31"


class TestEdgeCases:
    """Test edge cases and special scenarios"""
    
    def test_context_insight_categories(self):
        """Test ContextInsight with different categories"""
        insight1 = ContextInsight(
            timestamp="2024-09-26T10:00:00",
            agent="analyzer",
            category="insight",
            content="Found optimization opportunity",
            importance="high"
        )
        
        insight2 = ContextInsight(
            timestamp="2024-09-26T11:00:00",
            agent="debugger",
            category="challenge",
            content="Complex dependency issue",
            importance="critical"
        )
        
        assert insight1.category == "insight"
        assert insight2.category == "challenge"
        assert insight1.importance == "high"
        assert insight2.importance == "critical"
    
    def test_progress_action_status(self):
        """Test ContextProgressAction with different statuses"""
        action = ContextProgressAction(
            timestamp="2024-09-26T10:00:00",
            action="implement_feature",
            agent="coding-agent",
            details="Added authentication",
            status="completed"
        )
        
        assert action.status == "completed"
        assert action.details == "Added authentication"
    
    def test_custom_section_flexibility(self):
        """Test ContextCustomSection with arbitrary data"""
        custom_data = {
            "metrics": {
                "performance": 95.5,
                "coverage": 88.2
            },
            "tags": ["performance", "tested", "reviewed"]
        }
        
        section = ContextCustomSection(
            name="quality_metrics",
            data=custom_data,
            schema_version="2.0"
        )
        
        assert section.name == "quality_metrics"
        assert section.data["metrics"]["performance"] == 95.5
        assert "reviewed" in section.data["tags"]
        assert section.schema_version == "2.0"
    
    def test_empty_collections_serialization(self):
        """Test that empty collections serialize properly"""
        context = TaskContext(
            metadata=ContextMetadata(
                task_id="task123",
                project_id="proj456"
            ),
            objective=ContextObjective(
                title="Test empty collections"
            )
        )
        
        dict_data = context.to_dict()
        
        # Verify empty collections are preserved
        assert dict_data['metadata']['assignees'] == []
        assert dict_data['metadata']['labels'] == []
        assert dict_data['requirements']['checklist'] == []
        assert dict_data['requirements']['custom_requirements'] == []
        assert dict_data['subtasks']['items'] == []
        assert dict_data['custom_sections'] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])