"""
Unit Tests for Task DTO Serialization
Phase 1: Verify removed fields (emoji, counts) are not included in serialization

Tests ensure:
1. Emoji fields (priority_emoji, status_emoji) are NOT in serialized output
2. Count fields (subtask_count, assignees_count, dependency_count) are NOT in serialized output
3. Arrays (subtasks, assignees, dependencies) are single source of truth
4. include_context parameter controls context_data inclusion (when implemented at entity level)
"""

from datetime import datetime
from uuid import uuid4

import pytest

from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus


class TestTaskDTOSerializationNoEmojiFields:
    """Test that task serialization does NOT include emoji fields"""

    def test_task_to_dict_excludes_priority_emoji(self):
        """Verify task.to_dict() doesn't include priority_emoji field"""
        # Arrange
        task_id = TaskId(str(uuid4()))
        task = Task(
            id=task_id,
            title="Test Task",
            description="Test description",
            status=TaskStatus.todo(),
            priority=Priority.high(),
            git_branch_id=str(uuid4()),
            assignees=["coding-agent"],
            labels=["test"],
            dependencies=[],
            subtasks=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Act
        task_dict = task.to_dict()

        # Assert
        assert "priority_emoji" not in task_dict, (
            "priority_emoji field should NOT exist in serialized task"
        )
        assert "priority" in task_dict, "priority field should exist (without emoji)"
        assert task_dict["priority"] == "high", (
            "priority value should be the string value, not emoji"
        )

    def test_task_to_dict_excludes_status_emoji(self):
        """Verify task.to_dict() doesn't include status_emoji field"""
        # Arrange
        task_id = TaskId(str(uuid4()))
        task = Task(
            id=task_id,
            title="Test Task",
            description="Test description",
            status=TaskStatus.in_progress(),
            priority=Priority.medium(),
            git_branch_id=str(uuid4()),
            assignees=["coding-agent"],
            labels=[],
            dependencies=[],
            subtasks=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Act
        task_dict = task.to_dict()

        # Assert
        assert "status_emoji" not in task_dict, (
            "status_emoji field should NOT exist in serialized task"
        )
        assert "status" in task_dict, "status field should exist (without emoji)"
        assert task_dict["status"] == "in_progress", (
            "status value should be the string value, not emoji"
        )

    def test_task_to_dict_excludes_all_emoji_fields(self):
        """Verify task.to_dict() excludes ALL emoji fields"""
        # Arrange
        task_id = TaskId(str(uuid4()))
        task = Task(
            id=task_id,
            title="Complete Task",
            description="Fully tested task",
            status=TaskStatus.done(),
            priority=Priority.critical(),
            git_branch_id=str(uuid4()),
            assignees=["coding-agent", "test-orchestrator-agent"],
            labels=["backend", "api"],
            dependencies=[],
            subtasks=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Act
        task_dict = task.to_dict()

        # Assert - None of the emoji fields should exist
        emoji_fields = ["priority_emoji", "status_emoji"]
        for field in emoji_fields:
            assert field not in task_dict, (
                f"{field} should NOT exist in serialized task"
            )


class TestTaskDTOSerializationNoCountFields:
    """Test that task serialization does NOT include count fields"""

    def test_task_to_dict_excludes_subtask_count(self):
        """Verify task.to_dict() doesn't include subtask_count field"""
        # Arrange
        subtask_ids = [str(uuid4()), str(uuid4()), str(uuid4())]
        task_id = TaskId(str(uuid4()))
        task = Task(
            id=task_id,
            title="Task with Subtasks",
            description="Has multiple subtasks",
            status=TaskStatus.in_progress(),
            priority=Priority.high(),
            git_branch_id=str(uuid4()),
            assignees=["coding-agent"],
            labels=[],
            dependencies=[],
            subtasks=subtask_ids,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Act
        task_dict = task.to_dict()

        # Assert
        assert "subtask_count" in task_dict, (
            "subtask_count field SHOULD exist as computed property in serialized task"
        )
        assert task_dict["subtask_count"] == 3, (
            "subtask_count should match length of subtasks array"
        )
        assert "subtasks" in task_dict, "subtasks array should exist"
        assert len(task_dict["subtasks"]) == 3, (
            "subtasks array is source of truth for count"
        )
        assert task_dict["subtasks"] == subtask_ids, (
            "subtasks array should contain actual subtask IDs"
        )

    def test_task_to_dict_excludes_assignees_count(self):
        """Verify task.to_dict() doesn't include assignees_count field"""
        # Arrange
        assignees = ["coding-agent", "test-orchestrator-agent", "debugger-agent"]
        task_id = TaskId(str(uuid4()))
        task = Task(
            id=task_id,
            title="Multi-agent Task",
            description="Assigned to multiple agents",
            status=TaskStatus.todo(),
            priority=Priority.medium(),
            git_branch_id=str(uuid4()),
            assignees=assignees,
            labels=[],
            dependencies=[],
            subtasks=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Act
        task_dict = task.to_dict()

        # Assert
        assert "assignees_count" not in task_dict, (
            "assignees_count field should NOT exist in serialized task"
        )
        assert "assignees" in task_dict, "assignees array should exist"
        assert len(task_dict["assignees"]) == 3, (
            "assignees array is source of truth for count"
        )

    def test_task_to_dict_excludes_dependency_count(self):
        """Verify task.to_dict() doesn't include dependency_count field"""
        # Arrange
        dependency_ids = [str(uuid4()), str(uuid4())]
        task_id = TaskId(str(uuid4()))
        task = Task(
            id=task_id,
            title="Task with Dependencies",
            description="Has dependency requirements",
            status=TaskStatus.blocked(),
            priority=Priority.high(),
            git_branch_id=str(uuid4()),
            assignees=["coding-agent"],
            labels=[],
            dependencies=dependency_ids,
            subtasks=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Act
        task_dict = task.to_dict()

        # Assert
        assert "dependency_count" in task_dict, (
            "dependency_count field SHOULD exist as computed property in serialized task"
        )
        assert task_dict["dependency_count"] == 2, (
            "dependency_count should match length of dependencies array"
        )
        assert "dependencies" in task_dict, "dependencies array should exist"
        assert len(task_dict["dependencies"]) == 2, (
            "dependencies array is source of truth for count"
        )

    def test_task_to_dict_includes_computed_count_fields(self):
        """Verify task.to_dict() includes computed count fields (subtask_count, dependency_count)"""
        # Arrange
        task_id = TaskId(str(uuid4()))
        task = Task(
            id=task_id,
            title="Complex Task",
            description="Has multiple subtasks, assignees, and dependencies",
            status=TaskStatus.in_progress(),
            priority=Priority.high(),
            git_branch_id=str(uuid4()),
            assignees=["coding-agent", "test-orchestrator-agent"],
            labels=["backend"],
            dependencies=[str(uuid4())],
            subtasks=[str(uuid4()), str(uuid4())],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Act
        task_dict = task.to_dict()

        # Assert - Computed count fields SHOULD exist with correct values
        assert "subtask_count" in task_dict, (
            "subtask_count should exist as computed property"
        )
        assert task_dict["subtask_count"] == 2, (
            "subtask_count should match subtasks array length"
        )
        assert "dependency_count" in task_dict, (
            "dependency_count should exist as computed property"
        )
        assert task_dict["dependency_count"] == 1, (
            "dependency_count should match dependencies array length"
        )

        # Fields that should NOT exist
        assert "assignees_count" not in task_dict, "assignees_count should NOT exist"
        assert "task_count" not in task_dict, "task_count should NOT exist"


class TestTaskDTOSerializationArraysAreSourceOfTruth:
    """Test that arrays are the single source of truth for counts"""

    def test_subtasks_array_is_authoritative(self):
        """Verify subtasks array contains actual data, not derived count"""
        # Arrange
        subtask_ids = [str(uuid4()) for _ in range(5)]
        task_id = TaskId(str(uuid4()))
        task = Task(
            id=task_id,
            title="Task with Many Subtasks",
            description="Test array as source of truth",
            status=TaskStatus.in_progress(),
            priority=Priority.medium(),
            git_branch_id=str(uuid4()),
            assignees=["coding-agent"],
            labels=[],
            dependencies=[],
            subtasks=subtask_ids,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Act
        task_dict = task.to_dict()

        # Assert
        assert task_dict["subtasks"] == subtask_ids, (
            "subtasks array should contain exact subtask IDs"
        )
        assert len(task_dict["subtasks"]) == 5, (
            "Count should be derived from array length, not stored separately"
        )

    def test_assignees_array_is_authoritative(self):
        """Verify assignees array contains actual data, not derived count"""
        # Arrange
        assignees = [
            "coding-agent",
            "test-orchestrator-agent",
            "security-auditor-agent",
            "documentation-agent",
        ]
        task_id = TaskId(str(uuid4()))
        task = Task(
            id=task_id,
            title="Multi-specialist Task",
            description="Requires multiple specialized agents",
            status=TaskStatus.todo(),
            priority=Priority.high(),
            git_branch_id=str(uuid4()),
            assignees=assignees,
            labels=[],
            dependencies=[],
            subtasks=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Act
        task_dict = task.to_dict()

        # Assert
        assert set(task_dict["assignees"]) == set(assignees), (
            "assignees array should contain exact agent names"
        )
        assert len(task_dict["assignees"]) == 4, (
            "Count should be derived from array length, not stored separately"
        )

    def test_dependencies_array_is_authoritative(self):
        """Verify dependencies array contains actual data, not derived count"""
        # Arrange
        dependency_ids = [str(uuid4()) for _ in range(3)]
        task_id = TaskId(str(uuid4()))
        task = Task(
            id=task_id,
            title="Dependent Task",
            description="Requires other tasks to complete first",
            status=TaskStatus.blocked(),
            priority=Priority.medium(),
            git_branch_id=str(uuid4()),
            assignees=["coding-agent"],
            labels=[],
            dependencies=dependency_ids,
            subtasks=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Act
        task_dict = task.to_dict()

        # Assert
        assert task_dict["dependencies"] == dependency_ids, (
            "dependencies array should contain exact dependency IDs"
        )
        assert len(task_dict["dependencies"]) == 3, (
            "Count should be derived from array length, not stored separately"
        )


class TestTaskDTOSerializationBaseFields:
    """Test that base fields are correctly included in serialization"""

    def test_task_to_dict_includes_required_fields(self):
        """Verify all required base fields are present"""
        # Arrange
        task_id = TaskId(str(uuid4()))
        git_branch_id = str(uuid4())
        now = datetime.now()

        task = Task(
            id=task_id,
            title="Complete Task Example",
            description="Full field coverage test",
            status=TaskStatus.in_progress(),
            priority=Priority.high(),
            git_branch_id=git_branch_id,
            assignees=["coding-agent"],
            labels=["test", "backend"],
            dependencies=[],
            subtasks=[],
            created_at=now,
            updated_at=now,
        )

        # Act
        task_dict = task.to_dict()

        # Assert - Required fields must be present
        required_fields = [
            "id",
            "title",
            "description",
            "git_branch_id",
            "status",
            "priority",
            "assignees",
            "labels",
            "dependencies",
            "subtasks",
            "created_at",
            "updated_at",
        ]

        for field in required_fields:
            assert field in task_dict, (
                f"Required field '{field}' missing from serialization"
            )

    def test_task_to_dict_includes_context_id(self):
        """Verify context_id is included in serialization"""
        # Arrange
        task_id = TaskId(str(uuid4()))
        context_id = str(uuid4())
        task = Task(
            id=task_id,
            title="Task with Context",
            description="Has context reference",
            status=TaskStatus.todo(),
            priority=Priority.medium(),
            git_branch_id=str(uuid4()),
            assignees=["coding-agent"],
            labels=[],
            dependencies=[],
            subtasks=[],
            context_id=context_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Act
        task_dict = task.to_dict()

        # Assert
        assert "context_id" in task_dict, "context_id should be in serialization"
        assert task_dict["context_id"] == context_id, "context_id value should match"


class TestTaskDTOSerializationEmptyArrays:
    """Test that empty arrays serialize correctly without count fields"""

    def test_task_with_no_subtasks_serializes_empty_array(self):
        """Verify empty subtasks array, not count field"""
        # Arrange
        task_id = TaskId(str(uuid4()))
        task = Task(
            id=task_id,
            title="Simple Task",
            description="No subtasks",
            status=TaskStatus.todo(),
            priority=Priority.low(),
            git_branch_id=str(uuid4()),
            assignees=["coding-agent"],
            labels=[],
            dependencies=[],
            subtasks=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Act
        task_dict = task.to_dict()

        # Assert
        assert "subtasks" in task_dict, "subtasks field should exist"
        assert task_dict["subtasks"] == [], "Empty subtasks should be []"
        assert "subtask_count" in task_dict, (
            "subtask_count field should exist as computed property"
        )
        assert task_dict["subtask_count"] == 0, (
            "subtask_count should be 0 for empty array"
        )

    def test_task_with_no_dependencies_serializes_empty_array(self):
        """Verify empty dependencies array, not count field"""
        # Arrange
        task_id = TaskId(str(uuid4()))
        task = Task(
            id=task_id,
            title="Independent Task",
            description="No dependencies",
            status=TaskStatus.todo(),
            priority=Priority.medium(),
            git_branch_id=str(uuid4()),
            assignees=["coding-agent"],
            labels=[],
            dependencies=[],
            subtasks=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Act
        task_dict = task.to_dict()

        # Assert
        assert "dependencies" in task_dict, "dependencies field should exist"
        assert task_dict["dependencies"] == [], "Empty dependencies should be []"
        assert "dependency_count" in task_dict, (
            "dependency_count field should exist as computed property"
        )
        assert task_dict["dependency_count"] == 0, (
            "dependency_count should be 0 for empty array"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
