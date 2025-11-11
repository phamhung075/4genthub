"""Unit tests for DependencyValidationService"""

from unittest.mock import Mock, patch

import pytest

from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.repositories.task_repository import TaskRepository
from fastmcp.task_management.domain.services.dependency_validation_service import (
    DependencyValidationService,
)
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.utilities.id_validator import IDValidator


class TestDependencyValidationService:
    """Test cases for DependencyValidationService"""

    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock TaskRepository"""
        return Mock(spec=TaskRepository)

    @pytest.fixture
    def mock_id_validator(self):
        """Create a mock IDValidator"""
        validator = Mock(spec=IDValidator)
        # Default to valid IDs
        valid_result = Mock()
        valid_result.is_valid = True
        valid_result.error_message = None
        validator.detect_id_type.return_value = valid_result
        return validator

    @pytest.fixture
    def service(self, mock_task_repository, mock_id_validator):
        """Create the service under test"""
        return DependencyValidationService(mock_task_repository, mock_id_validator)

    @pytest.fixture
    def sample_task(self):
        """Create a sample task with dependencies"""
        task = Mock(spec=Task)
        task.id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        task.title = "Sample Task"
        task.status = Mock()
        task.status.value = "in_progress"
        task.get_dependency_ids = Mock(
            return_value=["550e8400-e29b-41d4-a716-446655440002"]
        )
        return task

    @pytest.fixture
    def dependency_task(self):
        """Create a sample dependency task"""
        task = Mock(spec=Task)
        task.id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440002")
        task.title = "Dependency Task"
        task.status = Mock()
        task.status.value = "done"
        task.status.is_done = Mock(return_value=True)
        return task

    def test_validate_dependency_chain_invalid_task_id(
        self, service, mock_id_validator
    ):
        """Test validation with invalid task ID format"""
        # Set up invalid ID result
        invalid_result = Mock()
        invalid_result.is_valid = False
        invalid_result.error_message = "Invalid UUID format"
        mock_id_validator.detect_id_type.return_value = invalid_result

        result = service.validate_dependency_chain(TaskId.from_string("invalid-id"))

        assert result["valid"] is False
        assert "Invalid task ID format" in result["errors"][0]
        assert result["issues"] == []

    def test_validate_dependency_chain_task_not_found(
        self, service, mock_task_repository
    ):
        """Test validation when task is not found"""
        mock_task_repository.find_by_id.return_value = None

        task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        result = service.validate_dependency_chain(task_id)

        assert result["valid"] is False
        assert (
            "Task 550e8400-e29b-41d4-a716-446655440001 not found" in result["errors"][0]
        )

    def test_validate_dependency_chain_no_dependencies(
        self, service, mock_task_repository, sample_task
    ):
        """Test validation when task has no dependencies"""
        sample_task.get_dependency_ids.return_value = []
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.find_all.return_value = [sample_task]

        result = service.validate_dependency_chain(sample_task.id)

        assert result["valid"] is True
        assert result["message"] == "Task has no dependencies"
        assert result["issues"] == []
        assert result["errors"] == []

    def test_validate_dependency_chain_self_dependency(
        self, service, mock_task_repository, sample_task
    ):
        """Test detection of self-dependency"""
        # Task depends on itself
        sample_task.get_dependency_ids.return_value = [str(sample_task.id)]
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.find_all.return_value = [sample_task]

        result = service.validate_dependency_chain(sample_task.id)

        assert result["valid"] is False
        assert any("cannot depend on itself" in error for error in result["errors"])

    def test_validate_dependency_chain_invalid_dependency_id(
        self, service, mock_task_repository, mock_id_validator, sample_task
    ):
        """Test validation with invalid dependency ID format"""
        sample_task.get_dependency_ids.return_value = ["invalid-dependency-id"]
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.find_all.return_value = [sample_task]

        # First call returns valid for task ID, second call returns invalid for dependency
        valid_result = Mock()
        valid_result.is_valid = True
        invalid_result = Mock()
        invalid_result.is_valid = False
        invalid_result.error_message = "Invalid UUID format"

        mock_id_validator.detect_id_type.side_effect = [valid_result, invalid_result]

        result = service.validate_dependency_chain(sample_task.id)

        assert result["valid"] is False
        assert any(
            "Invalid dependency ID format" in error for error in result["errors"]
        )

    def test_validate_dependency_chain_missing_dependency(
        self, service, mock_task_repository, sample_task
    ):
        """Test validation when dependency is missing"""
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.find_all.return_value = [
            sample_task
        ]  # Dependency not in list

        # Mock _find_dependency_across_states to return None (dependency not found)
        with patch.object(service, "_find_dependency_across_states", return_value=None):
            result = service.validate_dependency_chain(sample_task.id)

        assert result["valid"] is False
        assert result["can_proceed"] is False
        assert len(result["errors"]) > 0  # It's in errors, not issues
        assert any("no longer exists" in error for error in result["errors"])
        assert len(result["issues"]) > 0  # Should have issues too
        assert result["issues"][0]["type"] == "missing_dependency"

    def test_validate_dependency_chain_cancelled_dependency(
        self, service, mock_task_repository, sample_task, dependency_task
    ):
        """Test validation when dependency is cancelled"""
        dependency_task.status.value = "cancelled"
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.find_all.return_value = [sample_task, dependency_task]

        result = service.validate_dependency_chain(sample_task.id)

        assert result["valid"] is True  # No errors, just warnings
        assert len(result["issues"]) == 1
        assert result["issues"][0]["type"] == "cancelled_dependency"
        assert result["issues"][0]["severity"] == "warning"

    def test_validate_dependency_chain_blocked_dependency(
        self, service, mock_task_repository, sample_task, dependency_task
    ):
        """Test validation when dependency is blocked"""
        dependency_task.status.value = "blocked"
        dependency_task.status.is_done.return_value = False
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.find_all.return_value = [sample_task, dependency_task]

        result = service.validate_dependency_chain(sample_task.id)

        assert result["valid"] is True  # No errors, just warnings
        assert result["can_proceed"] is False
        assert len(result["issues"]) == 1
        assert result["issues"][0]["type"] == "blocked_dependency"
        assert result["issues"][0]["severity"] == "warning"

    def test_validate_dependency_chain_satisfied_dependency(
        self, service, mock_task_repository, sample_task, dependency_task
    ):
        """Test validation when dependency is completed"""
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.find_all.return_value = [sample_task, dependency_task]

        result = service.validate_dependency_chain(sample_task.id)

        assert result["valid"] is True
        assert result["can_proceed"] is True
        assert len(result["issues"]) == 1
        assert result["issues"][0]["type"] == "satisfied_dependency"
        assert result["issues"][0]["severity"] == "info"

    def test_check_circular_dependencies(self, service, mock_task_repository):
        """Test detection of circular dependencies"""
        # Create circular dependency: A -> B -> C -> A
        task_a = Mock(spec=Task)
        task_a.id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        task_a.get_dependency_ids = Mock(
            return_value=["550e8400-e29b-41d4-a716-446655440002"]
        )

        task_b = Mock(spec=Task)
        task_b.id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440002")
        task_b.get_dependency_ids = Mock(
            return_value=["550e8400-e29b-41d4-a716-446655440003"]
        )

        task_c = Mock(spec=Task)
        task_c.id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440003")
        task_c.get_dependency_ids = Mock(
            return_value=["550e8400-e29b-41d4-a716-446655440001"]
        )  # Points back to A

        mock_task_repository.find_by_id.return_value = task_a
        mock_task_repository.find_all.return_value = [task_a, task_b, task_c]

        result = service.validate_dependency_chain(task_a.id)

        assert result["valid"] is False
        assert any(
            "Circular dependency detected" in error for error in result["errors"]
        )

    def test_check_orphaned_dependencies(
        self, service, mock_task_repository, sample_task
    ):
        """Test detection of orphaned dependencies"""
        # Task has dependency that doesn't exist anywhere
        sample_task.get_dependency_ids.return_value = [
            "550e8400-e29b-41d4-a716-446655440099"
        ]
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.find_all.return_value = [sample_task]

        # Make sure _find_dependency_across_states also returns None
        with patch.object(service, "_find_dependency_across_states", return_value=None):
            result = service.validate_dependency_chain(sample_task.id)

        assert result["valid"] is False
        assert any("no longer exists" in error for error in result["errors"])

    def test_find_dependency_across_states(
        self, service, mock_task_repository, dependency_task
    ):
        """Test finding dependencies across different states"""
        # Test when repository supports find_by_id_across_contexts
        mock_task_repository.find_by_id_across_contexts = Mock(
            return_value=dependency_task
        )

        result = service._find_dependency_across_states(
            "550e8400-e29b-41d4-a716-446655440002"
        )

        assert result == dependency_task
        mock_task_repository.find_by_id_across_contexts.assert_called_once()

    def test_find_dependency_across_states_fallback(
        self, service, mock_task_repository, dependency_task
    ):
        """Test fallback when repository doesn't support find_by_id_across_contexts"""
        # Repository doesn't have the method
        mock_task_repository.find_by_id.return_value = dependency_task

        result = service._find_dependency_across_states(
            "550e8400-e29b-41d4-a716-446655440002"
        )

        assert result == dependency_task
        mock_task_repository.find_by_id.assert_called_once()

    def test_get_dependency_chain_status(
        self, service, mock_task_repository, sample_task, dependency_task
    ):
        """Test getting detailed dependency chain status"""
        mock_task_repository.find_by_id.return_value = sample_task
        mock_task_repository.find_all.return_value = [sample_task, dependency_task]

        result = service.get_dependency_chain_status(sample_task.id)

        assert result["task_id"] == str(sample_task.id)
        assert result["task_title"] == "Sample Task"
        assert len(result["dependency_chain"]) == 1
        assert result["chain_statistics"]["total_dependencies"] == 1
        assert result["chain_statistics"]["completed_dependencies"] == 1
        assert result["chain_statistics"]["completion_percentage"] == 100
        assert result["can_proceed"] is True
        assert "analysis_timestamp" in result

    def test_get_dependency_chain_status_task_not_found(
        self, service, mock_task_repository
    ):
        """Test getting chain status when task not found"""
        mock_task_repository.find_by_id.return_value = None

        task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        result = service.get_dependency_chain_status(task_id)

        assert "error" in result
        assert "not found" in result["error"]

    def test_exception_handling(self, service, mock_task_repository):
        """Test exception handling in validate_dependency_chain"""
        mock_task_repository.find_by_id.side_effect = Exception("Database error")

        task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        result = service.validate_dependency_chain(task_id)

        assert result["valid"] is False
        assert "Validation failed" in result["errors"][0]

    def test_find_dependency_across_states_exception(
        self, service, mock_task_repository
    ):
        """Test exception handling in _find_dependency_across_states (lines 205-206)"""
        # Make TaskId.from_string raise an exception
        with patch(
            "fastmcp.task_management.domain.value_objects.task_id.TaskId.from_string",
            side_effect=Exception("Invalid ID"),
        ):
            result = service._find_dependency_across_states("invalid-id")

        assert result is None  # Should return None on exception

    def test_can_task_proceed_missing_method(self, service, mock_task_repository):
        """Test _can_task_proceed when task doesn't have get_dependency_ids (line 286)"""
        task = Mock(spec=Task)
        task.id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        # Simulate task without get_dependency_ids by making hasattr return False
        task.get_dependency_ids = None
        del task.get_dependency_ids  # Remove the attribute entirely

        task_map = {}
        result = service._can_task_proceed(task, task_map)

        assert result is True  # Should return True when method doesn't exist

    def test_can_task_proceed_status_value_attribute(
        self, service, mock_task_repository
    ):
        """Test _can_task_proceed with dep_status using .value (lines 307-309)"""
        task = Mock(spec=Task)
        task.id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        task.get_dependency_ids = Mock(
            return_value=["550e8400-e29b-41d4-a716-446655440002"]
        )

        dep_task = Mock(spec=Task)
        dep_task.id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440002")
        dep_task.status = Mock()
        # Set up status without is_done method, only has .value
        del dep_task.status.is_done  # Remove is_done method
        dep_task.status.value = "in_progress"  # Not done

        task_map = {str(dep_task.id): dep_task}

        result = service._can_task_proceed(task, task_map)

        assert result is False  # Should return False when dependency not done

        # Now test with done status
        dep_task.status.value = "done"
        result = service._can_task_proceed(task, task_map)

        assert result is True  # Should return True when dependency done

    def test_get_dependency_chain_status_exception(self, service, mock_task_repository):
        """Test exception handling in get_dependency_chain_status (lines 357-359)"""
        mock_task_repository.find_by_id.side_effect = Exception(
            "Database connection lost"
        )

        task_id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        result = service.get_dependency_chain_status(task_id)

        assert "error" in result
        assert "Analysis failed" in result["error"]
        assert "Database connection lost" in result["error"]

    def test_validate_dependency_chain_partial_branch_60_63(
        self, service, mock_task_repository, sample_task
    ):
        """Test partial branch 60->63 (task without get_dependency_ids method)"""
        # Create task without get_dependency_ids method
        task_without_method = Mock(spec=Task)
        task_without_method.id = TaskId.from_string(
            "550e8400-e29b-41d4-a716-446655440001"
        )
        task_without_method.title = "Task Without Deps Method"
        task_without_method.status = Mock()
        task_without_method.status.value = "todo"
        # Remove get_dependency_ids attribute to simulate task without the method
        task_without_method.get_dependency_ids = None
        del task_without_method.get_dependency_ids

        mock_task_repository.find_by_id.return_value = task_without_method
        mock_task_repository.find_all.return_value = [task_without_method]

        result = service.validate_dependency_chain(task_without_method.id)

        # Should handle missing method gracefully
        assert result["valid"] is True
        assert result["message"] == "Task has no dependencies"

    def test_find_dependency_across_states_partial_branch_197_201(
        self, service, mock_task_repository, dependency_task
    ):
        """Test partial branch 197->201 (when find_by_id_across_contexts returns task)"""
        # Set up repository with find_by_id_across_contexts that returns a task
        mock_task_repository.find_by_id_across_contexts = Mock(
            return_value=dependency_task
        )

        result = service._find_dependency_across_states(
            "550e8400-e29b-41d4-a716-446655440002"
        )

        assert result == dependency_task
        assert result is not None
        # Verify find_by_id was not called (returned early from find_by_id_across_contexts)
        mock_task_repository.find_by_id.assert_not_called()

    def test_check_orphaned_dependencies_partial_branch_265_272(
        self, service, mock_task_repository
    ):
        """Test partial branch 265->272 (task without get_dependency_ids in _check_orphaned_dependencies)"""
        task_without_method = Mock(spec=Task)
        task_without_method.id = TaskId.from_string(
            "550e8400-e29b-41d4-a716-446655440001"
        )
        # Remove get_dependency_ids to simulate task without the method
        task_without_method.get_dependency_ids = None
        del task_without_method.get_dependency_ids

        task_map = {}

        orphaned = service._check_orphaned_dependencies(task_without_method, task_map)

        assert orphaned == []  # Should return empty list when method doesn't exist

    def test_can_task_proceed_partial_branch_332_338(
        self, service, mock_task_repository
    ):
        """Test partial branch 332->338 (dependency with is_done method that returns True)"""
        task = Mock(spec=Task)
        task.id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440001")
        task.get_dependency_ids = Mock(
            return_value=["550e8400-e29b-41d4-a716-446655440002"]
        )

        dep_task = Mock(spec=Task)
        dep_task.id = TaskId.from_string("550e8400-e29b-41d4-a716-446655440002")
        dep_task.status = Mock()
        dep_task.status.is_done = Mock(
            return_value=True
        )  # Has is_done and returns True

        task_map = {str(dep_task.id): dep_task}

        result = service._can_task_proceed(task, task_map)

        assert (
            result is True
        )  # Should return True when dependency has is_done() returning True
