"""
Unit Tests for CascadeDeletionService

Tests cascade deletion functionality for tasks, branches, and projects
with proper cleanup of related entities and domain event dispatching.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timezone
import uuid

from fastmcp.task_management.domain.services.cascade_deletion_service import (
    CascadeDeletionService,
    DeleteScope
)
from fastmcp.task_management.domain.value_objects.task_id import TaskId


class TestCascadeDeletionService:
    """Test suite for CascadeDeletionService."""

    @pytest.fixture
    def mock_repositories(self):
        """Create mock repositories for testing."""
        return {
            'task_repository': Mock(),
            'subtask_repository': Mock(),
            'branch_repository': Mock(),
            'project_repository': Mock(),
            'context_repository': Mock()
        }

    @pytest.fixture
    def service(self, mock_repositories):
        """Create CascadeDeletionService instance with mocked dependencies."""
        return CascadeDeletionService(
            task_repository=mock_repositories['task_repository'],
            subtask_repository=mock_repositories['subtask_repository'],
            branch_repository=mock_repositories['branch_repository'],
            project_repository=mock_repositories['project_repository'],
            context_repository=mock_repositories['context_repository']
        )

    @pytest.fixture
    def mock_task(self):
        """Create a mock task with standard attributes."""
        task = Mock()
        task.id = TaskId.from_string(str(uuid.uuid4()))
        task.git_branch_id = str(uuid.uuid4())
        task.status = Mock(value="in_progress")
        task.title = "Test Task"
        task.context_id = str(uuid.uuid4())
        return task

    @pytest.fixture
    def mock_branch(self):
        """Create a mock branch with standard attributes."""
        branch = Mock()
        branch.id = str(uuid.uuid4())
        branch.project_id = str(uuid.uuid4())
        branch.name = "feature/test-branch"
        branch.context_id = str(uuid.uuid4())
        return branch

    @pytest.fixture
    def mock_project(self):
        """Create a mock project with standard attributes."""
        project = Mock()
        project.id = str(uuid.uuid4())
        project.name = "Test Project"
        project.context_id = str(uuid.uuid4())
        return project


class TestTaskCascadeDeletion(TestCascadeDeletionService):
    """Test cascade deletion for tasks."""

    def test_delete_task_only_success(self, service, mock_repositories, mock_task):
        """Test deleting only the task without cascading."""
        task_id = str(mock_task.id.value)
        mock_repositories['task_repository'].find_by_id.return_value = mock_task
        mock_repositories['task_repository'].delete.return_value = True

        with patch('fastmcp.task_management.domain.services.event_dispatcher.dispatch_domain_event'):
            result = service.delete_task_cascade(task_id, DeleteScope.TASK_ONLY)

        assert result["task_deleted"] is True
        assert result["subtasks_deleted"] == 0
        assert result["contexts_deleted"] == 0
        assert "task_deleted" in result["events_dispatched"]

        # Verify repositories were called correctly
        mock_repositories['task_repository'].find_by_id.assert_called_once()
        mock_repositories['task_repository'].delete.assert_called_once()
        mock_repositories['subtask_repository'].delete_by_parent_task_id.assert_not_called()
        mock_repositories['context_repository'].delete.assert_not_called()

    def test_delete_task_with_subtasks(self, service, mock_repositories, mock_task):
        """Test deleting task with subtasks."""
        task_id = str(mock_task.id.value)
        mock_repositories['task_repository'].find_by_id.return_value = mock_task
        mock_repositories['task_repository'].delete.return_value = True
        mock_repositories['subtask_repository'].count_by_parent_task_id.return_value = 5
        mock_repositories['subtask_repository'].delete_by_parent_task_id.return_value = True

        with patch('fastmcp.task_management.domain.services.event_dispatcher.dispatch_domain_event'):
            result = service.delete_task_cascade(task_id, DeleteScope.TASK_WITH_SUBTASKS)

        assert result["task_deleted"] is True
        assert result["subtasks_deleted"] == 5
        assert result["contexts_deleted"] == 0

        # Verify subtasks were deleted
        mock_repositories['subtask_repository'].count_by_parent_task_id.assert_called_once()
        mock_repositories['subtask_repository'].delete_by_parent_task_id.assert_called_once()

    def test_delete_task_full_cascade(self, service, mock_repositories, mock_task):
        """Test full cascade deletion including context."""
        task_id = str(mock_task.id.value)
        mock_repositories['task_repository'].find_by_id.return_value = mock_task
        mock_repositories['task_repository'].delete.return_value = True
        mock_repositories['subtask_repository'].count_by_parent_task_id.return_value = 3
        mock_repositories['subtask_repository'].delete_by_parent_task_id.return_value = True
        mock_repositories['context_repository'].delete.return_value = True

        with patch('fastmcp.task_management.domain.services.event_dispatcher.dispatch_domain_event'):
            result = service.delete_task_cascade(task_id, DeleteScope.TASK_FULL)

        assert result["task_deleted"] is True
        assert result["subtasks_deleted"] == 3
        assert result["contexts_deleted"] == 1

        # Verify context was deleted
        mock_repositories['context_repository'].delete.assert_called_once_with(mock_task.context_id)

    def test_delete_task_not_found(self, service, mock_repositories):
        """Test deleting a task that doesn't exist."""
        task_id = str(uuid.uuid4())
        mock_repositories['task_repository'].find_by_id.return_value = None

        result = service.delete_task_cascade(task_id)

        assert result["task_deleted"] is False
        assert result["subtasks_deleted"] == 0
        assert result["contexts_deleted"] == 0
        assert len(result["events_dispatched"]) == 0

        # Verify delete was not called
        mock_repositories['task_repository'].delete.assert_not_called()

    def test_delete_task_failure(self, service, mock_repositories, mock_task):
        """Test handling task deletion failure."""
        task_id = str(mock_task.id.value)
        mock_repositories['task_repository'].find_by_id.return_value = mock_task
        mock_repositories['task_repository'].delete.return_value = False

        result = service.delete_task_cascade(task_id)

        assert result["task_deleted"] is False
        assert len(result["events_dispatched"]) == 0

    def test_delete_task_context_failure(self, service, mock_repositories, mock_task):
        """Test graceful handling of context deletion failure."""
        task_id = str(mock_task.id.value)
        mock_repositories['task_repository'].find_by_id.return_value = mock_task
        mock_repositories['task_repository'].delete.return_value = True
        mock_repositories['context_repository'].delete.side_effect = Exception("Context deletion failed")

        with patch('fastmcp.task_management.domain.services.event_dispatcher.dispatch_domain_event'):
            result = service.delete_task_cascade(task_id, DeleteScope.TASK_FULL)

        assert result["task_deleted"] is True
        assert result["contexts_deleted"] == 0  # Failed to delete context

    def test_delete_task_without_context_repository(self, mock_repositories):
        """Test cascade deletion when context repository is None."""
        service = CascadeDeletionService(
            task_repository=mock_repositories['task_repository'],
            subtask_repository=mock_repositories['subtask_repository'],
            branch_repository=mock_repositories['branch_repository'],
            project_repository=mock_repositories['project_repository'],
            context_repository=None
        )

        mock_task = Mock()
        mock_task.id = TaskId.from_string(str(uuid.uuid4()))
        mock_task.status = Mock(value="done")
        mock_task.title = "Test Task"
        
        task_id = str(mock_task.id.value)
        mock_repositories['task_repository'].find_by_id.return_value = mock_task
        mock_repositories['task_repository'].delete.return_value = True

        with patch('fastmcp.task_management.domain.services.event_dispatcher.dispatch_domain_event'):
            result = service.delete_task_cascade(task_id, DeleteScope.TASK_FULL)

        assert result["task_deleted"] is True
        assert result["contexts_deleted"] == 0


class TestBranchCascadeDeletion(TestCascadeDeletionService):
    """Test cascade deletion for branches."""

    def test_delete_branch_cascade_success(self, service, mock_repositories, mock_branch):
        """Test successful branch cascade deletion with tasks."""
        branch_id = mock_branch.id
        
        # Setup mock tasks in branch
        mock_tasks = []
        for i in range(3):
            task = Mock()
            task.id = Mock(value=str(uuid.uuid4()))
            task.git_branch_id = branch_id
            task.status = Mock(value="done")
            task.title = f"Task {i}"
            task.context_id = str(uuid.uuid4())
            mock_tasks.append(task)
        
        mock_repositories['branch_repository'].find_by_id.return_value = mock_branch
        mock_repositories['task_repository'].find_by_git_branch_id.return_value = mock_tasks
        mock_repositories['branch_repository'].delete.return_value = True
        
        # Mock task deletion
        def mock_find_by_id(task_id):
            for task in mock_tasks:
                if str(task.id.value) == str(task_id.value):
                    return task
            return None
        
        mock_repositories['task_repository'].find_by_id.side_effect = mock_find_by_id
        mock_repositories['task_repository'].delete.return_value = True
        mock_repositories['subtask_repository'].count_by_parent_task_id.return_value = 2
        mock_repositories['subtask_repository'].delete_by_parent_task_id.return_value = True
        mock_repositories['context_repository'].delete.return_value = True

        with patch('fastmcp.task_management.domain.services.event_dispatcher.dispatch_domain_event'):
            result = service.delete_branch_cascade(branch_id)

        assert result["branch_deleted"] is True
        assert result["tasks_deleted"] == 3
        assert result["subtasks_deleted"] == 6  # 3 tasks * 2 subtasks each
        assert result["contexts_deleted"] == 4  # 3 task contexts + 1 branch context
        assert "branch_deleted" in result["events_dispatched"]

    def test_delete_branch_not_found(self, service, mock_repositories):
        """Test deleting a branch that doesn't exist."""
        branch_id = str(uuid.uuid4())
        mock_repositories['branch_repository'].find_by_id.return_value = None

        result = service.delete_branch_cascade(branch_id)

        assert result["branch_deleted"] is False
        assert result["tasks_deleted"] == 0
        assert len(result["events_dispatched"]) == 0

    def test_delete_branch_empty(self, service, mock_repositories, mock_branch):
        """Test deleting a branch with no tasks."""
        branch_id = mock_branch.id
        mock_repositories['branch_repository'].find_by_id.return_value = mock_branch
        mock_repositories['task_repository'].find_by_git_branch_id.return_value = []
        mock_repositories['branch_repository'].delete.return_value = True
        mock_repositories['context_repository'].delete.return_value = True

        with patch('fastmcp.task_management.domain.services.event_dispatcher.dispatch_domain_event'):
            result = service.delete_branch_cascade(branch_id)

        assert result["branch_deleted"] is True
        assert result["tasks_deleted"] == 0
        assert result["contexts_deleted"] == 1  # Just branch context

    def test_delete_branch_failure(self, service, mock_repositories, mock_branch):
        """Test handling branch deletion failure."""
        branch_id = mock_branch.id
        mock_repositories['branch_repository'].find_by_id.return_value = mock_branch
        mock_repositories['task_repository'].find_by_git_branch_id.return_value = []
        mock_repositories['branch_repository'].delete.return_value = False

        result = service.delete_branch_cascade(branch_id)

        assert result["branch_deleted"] is False
        assert len(result["events_dispatched"]) == 0


class TestProjectCascadeDeletion(TestCascadeDeletionService):
    """Test cascade deletion for projects."""

    def test_delete_project_cascade_success(self, service, mock_repositories, mock_project):
        """Test successful project cascade deletion with branches and tasks."""
        project_id = mock_project.id
        
        # Setup mock branches in project
        mock_branches = []
        for i in range(2):
            branch = Mock()
            branch.id = str(uuid.uuid4())
            branch.project_id = project_id
            branch.name = f"branch-{i}"
            branch.context_id = str(uuid.uuid4())
            mock_branches.append(branch)
        
        mock_repositories['project_repository'].find_by_id.return_value = mock_project
        mock_repositories['branch_repository'].find_by_project_id.return_value = mock_branches
        mock_repositories['project_repository'].delete.return_value = True
        
        # Mock branch deletion results
        def mock_find_branch_by_id(branch_id):
            for branch in mock_branches:
                if str(branch.id) == str(branch_id):
                    return branch
            return None
        
        mock_repositories['branch_repository'].find_by_id.side_effect = mock_find_branch_by_id
        mock_repositories['branch_repository'].delete.return_value = True
        mock_repositories['task_repository'].find_by_git_branch_id.return_value = []
        mock_repositories['context_repository'].delete.return_value = True

        with patch('fastmcp.task_management.domain.services.event_dispatcher.dispatch_domain_event'):
            result = service.delete_project_cascade(project_id)

        assert result["project_deleted"] is True
        assert result["branches_deleted"] == 2
        assert result["contexts_deleted"] == 3  # 2 branch contexts + 1 project context
        assert "project_deleted" in result["events_dispatched"]

    def test_delete_project_not_found(self, service, mock_repositories):
        """Test deleting a project that doesn't exist."""
        project_id = str(uuid.uuid4())
        mock_repositories['project_repository'].find_by_id.return_value = None

        result = service.delete_project_cascade(project_id)

        assert result["project_deleted"] is False
        assert result["branches_deleted"] == 0
        assert len(result["events_dispatched"]) == 0

    def test_delete_project_with_full_hierarchy(self, service, mock_repositories, mock_project):
        """Test deleting project with complete hierarchy of branches, tasks, and subtasks."""
        project_id = mock_project.id
        
        # Create mock branch
        mock_branch = Mock()
        mock_branch.id = str(uuid.uuid4())
        mock_branch.project_id = project_id
        mock_branch.name = "feature/complex"
        mock_branch.context_id = str(uuid.uuid4())
        
        # Create mock task
        mock_task = Mock()
        mock_task.id = Mock(value=str(uuid.uuid4()))
        mock_task.git_branch_id = mock_branch.id
        mock_task.status = Mock(value="done")
        mock_task.title = "Complex Task"
        mock_task.context_id = str(uuid.uuid4())
        
        # Setup repository returns
        mock_repositories['project_repository'].find_by_id.return_value = mock_project
        mock_repositories['branch_repository'].find_by_project_id.return_value = [mock_branch]
        mock_repositories['branch_repository'].find_by_id.return_value = mock_branch
        mock_repositories['task_repository'].find_by_git_branch_id.return_value = [mock_task]
        mock_repositories['task_repository'].find_by_id.return_value = mock_task
        mock_repositories['subtask_repository'].count_by_parent_task_id.return_value = 5
        mock_repositories['subtask_repository'].delete_by_parent_task_id.return_value = True
        
        # All deletions succeed
        mock_repositories['project_repository'].delete.return_value = True
        mock_repositories['branch_repository'].delete.return_value = True
        mock_repositories['task_repository'].delete.return_value = True
        mock_repositories['context_repository'].delete.return_value = True

        with patch('fastmcp.task_management.domain.services.event_dispatcher.dispatch_domain_event'):
            result = service.delete_project_cascade(project_id)

        assert result["project_deleted"] is True
        assert result["branches_deleted"] == 1
        assert result["tasks_deleted"] == 1
        assert result["subtasks_deleted"] == 5
        assert result["contexts_deleted"] == 3  # project + branch + task contexts


class TestEventDispatching(TestCascadeDeletionService):
    """Test domain event dispatching during cascade deletion."""

    @patch('fastmcp.task_management.domain.services.event_dispatcher.dispatch_domain_event')
    @patch('fastmcp.task_management.domain.events.task_lifecycle_events.TaskDeletedEvent')
    def test_task_deleted_event_dispatched(self, mock_event_class, mock_dispatch, 
                                          service, mock_repositories, mock_task):
        """Test that task deleted event is properly dispatched."""
        task_id = str(mock_task.id.value)
        mock_repositories['task_repository'].find_by_id.return_value = mock_task
        mock_repositories['task_repository'].delete.return_value = True
        
        mock_event = Mock()
        mock_event_class.create.return_value = mock_event

        service.delete_task_cascade(task_id)

        # Verify event was created with correct parameters
        mock_event_class.create.assert_called_once_with(
            task_id=task_id,
            branch_id=mock_task.git_branch_id,
            status="in_progress",
            title="Test Task"
        )
        
        # Verify event was dispatched
        mock_dispatch.assert_called_once_with("task_deleted", mock_event)

    @patch('fastmcp.task_management.domain.services.event_dispatcher.dispatch_domain_event')
    def test_event_dispatch_failure_handled(self, mock_dispatch, service, mock_repositories, mock_task):
        """Test that event dispatch failures don't break cascade deletion."""
        task_id = str(mock_task.id.value)
        mock_repositories['task_repository'].find_by_id.return_value = mock_task
        mock_repositories['task_repository'].delete.return_value = True
        
        # Make event dispatch fail
        mock_dispatch.side_effect = Exception("Event dispatch failed")

        # Should still succeed despite event failure
        result = service.delete_task_cascade(task_id)

        assert result["task_deleted"] is True
        # Event dispatch failed, but was attempted
        assert "task_deleted" in result["events_dispatched"]


class TestSubtaskDeletion(TestCascadeDeletionService):
    """Test subtask deletion logic."""

    def test_delete_subtasks_success(self, service, mock_repositories):
        """Test successful subtask deletion."""
        task_id = TaskId.from_string(str(uuid.uuid4()))
        mock_repositories['subtask_repository'].count_by_parent_task_id.return_value = 10
        mock_repositories['subtask_repository'].delete_by_parent_task_id.return_value = True

        count = service._delete_task_subtasks(task_id)

        assert count == 10
        mock_repositories['subtask_repository'].count_by_parent_task_id.assert_called_once_with(task_id)
        mock_repositories['subtask_repository'].delete_by_parent_task_id.assert_called_once_with(task_id)

    def test_delete_subtasks_failure(self, service, mock_repositories):
        """Test handling of subtask deletion failure."""
        task_id = TaskId.from_string(str(uuid.uuid4()))
        mock_repositories['subtask_repository'].count_by_parent_task_id.return_value = 5
        mock_repositories['subtask_repository'].delete_by_parent_task_id.return_value = False

        count = service._delete_task_subtasks(task_id)

        assert count == 0  # Returns 0 on failure

    def test_delete_subtasks_exception(self, service, mock_repositories):
        """Test handling of exceptions during subtask deletion."""
        task_id = TaskId.from_string(str(uuid.uuid4()))
        mock_repositories['subtask_repository'].count_by_parent_task_id.side_effect = Exception("DB error")

        count = service._delete_task_subtasks(task_id)

        assert count == 0  # Returns 0 on exception


class TestEdgeCases(TestCascadeDeletionService):
    """Test edge cases and special scenarios."""

    def test_task_without_branch_id(self, service, mock_repositories):
        """Test deleting task without branch_id."""
        mock_task = Mock()
        mock_task.id = TaskId.from_string(str(uuid.uuid4()))
        mock_task.status = Mock(value="done")
        mock_task.title = "Orphan Task"
        # Configure mock to not have git_branch_id
        del mock_task.git_branch_id  # Remove the auto-created attribute
        
        task_id = str(mock_task.id.value)
        mock_repositories['task_repository'].find_by_id.return_value = mock_task
        mock_repositories['task_repository'].delete.return_value = True

        with patch('fastmcp.task_management.domain.services.event_dispatcher.dispatch_domain_event') as mock_dispatch:
            result = service.delete_task_cascade(task_id)

        assert result["task_deleted"] is True
        # Event should not be dispatched without branch_id
        mock_dispatch.assert_not_called()

    def test_string_task_id_conversion(self, service, mock_repositories, mock_task):
        """Test that string task IDs are properly converted to TaskId objects."""
        task_id_str = str(uuid.uuid4())
        mock_task.id = TaskId.from_string(task_id_str)
        
        # Mock find_by_id to verify it receives TaskId object
        def verify_task_id_type(task_id):
            assert isinstance(task_id, TaskId)
            assert str(task_id.value) == task_id_str
            return mock_task
        
        mock_repositories['task_repository'].find_by_id.side_effect = verify_task_id_type
        mock_repositories['task_repository'].delete.return_value = True

        with patch('fastmcp.task_management.domain.services.event_dispatcher.dispatch_domain_event'):
            result = service.delete_task_cascade(task_id_str)

        assert result["task_deleted"] is True

    def test_task_with_no_context_id(self, service, mock_repositories):
        """Test deleting task without context_id attribute."""
        mock_task = Mock()
        mock_task.id = TaskId.from_string(str(uuid.uuid4()))
        mock_task.git_branch_id = str(uuid.uuid4())
        mock_task.status = Mock(value="done")
        mock_task.title = "No Context Task"
        # Configure mock to not have context_id
        del mock_task.context_id  # Remove the auto-created attribute
        
        task_id = str(mock_task.id.value)
        mock_repositories['task_repository'].find_by_id.return_value = mock_task
        mock_repositories['task_repository'].delete.return_value = True

        with patch('fastmcp.task_management.domain.services.event_dispatcher.dispatch_domain_event'):
            result = service.delete_task_cascade(task_id, DeleteScope.TASK_FULL)

        assert result["task_deleted"] is True
        assert result["contexts_deleted"] == 0
        mock_repositories['context_repository'].delete.assert_not_called()