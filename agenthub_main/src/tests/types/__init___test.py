"""Test suite for types module initialization."""

import sys

from fastmcp.types import (
    converters,
    # Test that all expected exports are available
    entities,
    responses,
    summaries,
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
        """Test that entities module exports expected DTO classes."""
        # Check for entity DTO classes (NOT legacy aliases)
        assert hasattr(entities, 'TaskDTO')
        assert hasattr(entities, 'SubtaskDTO')
        assert hasattr(entities, 'ProjectDTO')
        assert hasattr(entities, 'BranchDTO')
        assert hasattr(entities, 'RuleDTO')

    def test_responses_exports(self):
        """Test that responses module exports expected response classes."""
        # Check for response wrapper classes (NOT legacy aliases)
        assert hasattr(responses, 'TasksResponse')
        assert hasattr(responses, 'SubtasksResponse')
        assert hasattr(responses, 'TaskSummariesResponse')

    def test_summaries_exports(self):
        """Test that summaries module exports expected summary DTO classes."""
        # Check for summary DTO classes (NOT legacy aliases)
        assert hasattr(summaries, 'TaskSummaryDTO')
        assert hasattr(summaries, 'SubtaskSummaryDTO')
        assert hasattr(summaries, 'ProjectSummaryDTO')
        assert hasattr(summaries, 'BranchSummaryDTO')

    def test_converters_exports(self):
        """Test that converters module exports expected converter functions."""
        # Check for converter functions (NOT legacy aliases)
        assert hasattr(converters, 'task_to_dto')
        assert hasattr(converters, 'subtask_to_dto')
        assert hasattr(converters, 'task_summary_to_dto')
        assert hasattr(converters, 'subtask_summary_to_dto')

    def test_circular_import_protection(self):
        """Test that there are no circular import issues."""
        # Force reimport to check for circular dependencies
        if 'fastmcp.types' in sys.modules:
            del sys.modules['fastmcp.types']

        # This should not raise ImportError
        import fastmcp.types

        assert fastmcp.types is not None

    def test_type_compatibility(self):
        """Test that DTOs can be properly instantiated."""
        from fastmcp.types.entities import TaskDTO

        # Test that the DTO can be instantiated with basic data
        task_dto = TaskDTO(
            id="123e4567-e89b-12d3-a456-426614174000",
            title="Test Task",
            description="Test Description",
            status="todo",
            priority="medium",
            assignees=["user1"],
            assignees_count=1,
            subtask_count=0,
            has_dependencies=False,
            has_context=False
        )

        # Verify it's the correct type
        assert isinstance(task_dto, TaskDTO)
        assert task_dto.title == "Test Task"

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
