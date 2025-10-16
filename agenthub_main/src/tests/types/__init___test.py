"""Test suite for types module initialization."""

import pytest
import importlib
import sys

from fastmcp.types import (
    # Test that all expected exports are available
    entities,
    responses,
    summaries,
    converters
)


class TestTypesInit:
    """Test cases for types module initialization."""
    
    def test_module_imports(self):
        """Test that all submodules can be imported."""
        assert entities is not None
        assert responses is not None
        assert summaries is not None
        assert converters is not None
    
    def test_entities_exports(self):
        """Test that entities module exports expected classes."""
        # Check for some key entity classes
        assert hasattr(entities, 'TaskEntity')
        assert hasattr(entities, 'SubtaskEntity')
        assert hasattr(entities, 'ProjectEntity')
        assert hasattr(entities, 'GitBranchEntity')
        assert hasattr(entities, 'AgentEntity')
    
    def test_responses_exports(self):
        """Test that responses module exports expected classes."""
        # Check for response wrapper classes
        assert hasattr(responses, 'TaskListResponse')
        assert hasattr(responses, 'SubtaskListResponse')
        assert hasattr(responses, 'SearchResponse')
    
    def test_summaries_exports(self):
        """Test that summaries module exports expected classes."""
        # Check for summary classes
        assert hasattr(summaries, 'TaskSummary')
        assert hasattr(summaries, 'ProjectSummary')
        assert hasattr(summaries, 'BranchSummary')
    
    def test_converters_exports(self):
        """Test that converters module exports expected functions."""
        # Check for converter functions
        assert hasattr(converters, 'task_to_entity')
        assert hasattr(converters, 'subtask_to_entity')
        assert hasattr(converters, 'project_to_entity')
    
    def test_circular_import_protection(self):
        """Test that there are no circular import issues."""
        # Force reimport to check for circular dependencies
        if 'fastmcp.types' in sys.modules:
            del sys.modules['fastmcp.types']
        
        # This should not raise ImportError
        import fastmcp.types
        
        assert fastmcp.types is not None
    
    def test_type_compatibility(self):
        """Test that types are compatible across modules."""
        from fastmcp.types.entities import TaskEntity
        from fastmcp.types.converters import task_to_entity
        from fastmcp.task_management.domain.entities.task import Task
        from datetime import datetime
        from fastmcp.shared.domain.value_objects import UUID
        from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
        from fastmcp.task_management.domain.value_objects.priority import Priority
        
        # Create a domain task
        domain_task = Task(
            id=UUID.generate(),
            title="Test Task",
            description="Test Description",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            details=None,
            assignees=["user1"],
            labels=["test"],
            estimated_effort=None,
            due_date=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            git_branch_id=UUID.generate(),
            project_id=UUID.generate(),
            parent_task_id=None,
            dependencies=[],
            blocking_tasks=[],
            subtask_ids=[],
            subtask_count=0,
            context_id=None,
            completion_summary=None
        )
        
        # Convert to entity
        entity = task_to_entity(domain_task)
        
        # Verify it's the correct type
        assert isinstance(entity, TaskEntity)
        assert entity.title == "Test Task"
    
    def test_module_all_attribute(self):
        """Test that __all__ is properly defined if present."""
        import fastmcp.types as types_module
        
        # If __all__ is defined, verify it contains expected exports
        if hasattr(types_module, '__all__'):
            all_exports = types_module.__all__
            assert isinstance(all_exports, list)
            # Common exports that should be included
            expected = ['entities', 'responses', 'summaries', 'converters']
            for exp in expected:
                assert exp in all_exports or hasattr(types_module, exp)