"""Unit tests for Agent Inheritance functionality"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.subtask_id import SubtaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.task_management.domain.enums.agent_roles import AgentRole
from fastmcp.task_management.application.services.agent_inheritance_service import AgentInheritanceService


class TestTaskEntityAgentInheritance:
    """Test Task entity methods for agent inheritance"""

    def setup_method(self):
        """Setup test data"""
        self.task_id = TaskId("test-task-123")
        self.task = Task(
            id=self.task_id,
            title="Test Task",
            description="Test Description",
            assignees=["coding-agent", "@test-orchestrator-agent"]
        )

    def test_get_inherited_assignees_for_subtasks_with_assignees(self):
        """Test getting assignees for subtask inheritance when task has assignees"""
        inherited = self.task.get_inherited_assignees_for_subtasks()
        
        assert inherited == ["coding-agent", "@test-orchestrator-agent"]
        assert inherited is not self.task.assignees  # Should be a copy

    def test_get_inherited_assignees_for_subtasks_empty(self):
        """Test getting assignees for subtask inheritance when task has no assignees"""
        self.task.assignees = []
        inherited = self.task.get_inherited_assignees_for_subtasks()
        
        assert inherited == []

    def test_validate_assignee_list_valid(self):
        """Test validating a list of valid assignees"""
        assignees = ["coding-agent", "@test-orchestrator-agent", "documentation-agent"]
        validated = self.task.validate_assignee_list(assignees)
        
        expected = ["@coding-agent", "@test-orchestrator-agent", "@documentation-agent"]
        assert validated == expected

    def test_validate_assignee_list_invalid(self):
        """Test validating a list with invalid assignees raises ValueError"""
        assignees = ["coding-agent", "invalid-agent", "test-orchestrator-agent"]
        
        with pytest.raises(ValueError) as excinfo:
            self.task.validate_assignee_list(assignees)
        
        assert "Invalid assignees" in str(excinfo.value)
        assert "invalid-agent" in str(excinfo.value)

    def test_validate_assignee_list_empty(self):
        """Test validating empty assignee list"""
        validated = self.task.validate_assignee_list([])
        assert validated == []

    def test_validate_assignee_list_none(self):
        """Test validating None assignee list"""
        validated = self.task.validate_assignee_list(None)
        assert validated == []


class TestSubtaskEntityAgentInheritance:
    """Test Subtask entity methods for agent inheritance"""

    def setup_method(self):
        """Setup test data"""
        self.parent_task_id = TaskId("parent-task-123")
        self.subtask_id = SubtaskId("subtask-456")
        
        # Subtask with no assignees (should inherit)
        self.subtask_no_assignees = Subtask(
            id=self.subtask_id,
            title="Test Subtask",
            description="Test Description",
            parent_task_id=self.parent_task_id,
            assignees=[]
        )
        
        # Subtask with assignees (should not inherit)
        self.subtask_with_assignees = Subtask(
            id=self.subtask_id,
            title="Test Subtask",
            description="Test Description", 
            parent_task_id=self.parent_task_id,
            assignees=["@security-auditor-agent"]
        )

    def test_has_assignees_true(self):
        """Test has_assignees when subtask has assignees"""
        assert self.subtask_with_assignees.has_assignees() is True

    def test_has_assignees_false(self):
        """Test has_assignees when subtask has no assignees"""
        assert self.subtask_no_assignees.has_assignees() is False

    def test_should_inherit_assignees_true(self):
        """Test should_inherit_assignees when subtask has no assignees"""
        assert self.subtask_no_assignees.should_inherit_assignees() is True

    def test_should_inherit_assignees_false(self):
        """Test should_inherit_assignees when subtask has assignees"""
        assert self.subtask_with_assignees.should_inherit_assignees() is False

    def test_inherit_assignees_from_parent_success(self):
        """Test successful inheritance of assignees from parent"""
        parent_assignees = ["coding-agent", "@test-orchestrator-agent"]
        
        original_updated_at = self.subtask_no_assignees.updated_at
        self.subtask_no_assignees.inherit_assignees_from_parent(parent_assignees)
        
        assert self.subtask_no_assignees.assignees == parent_assignees
        assert self.subtask_no_assignees.updated_at > original_updated_at
        
        # Check domain event was raised
        events = self.subtask_no_assignees.get_events()
        assert len(events) == 1
        assert "inherited_from_parent" in events[0].old_value

    def test_inherit_assignees_from_parent_already_has_assignees(self):
        """Test inheritance when subtask already has assignees (should not inherit)"""
        parent_assignees = ["coding-agent", "@test-orchestrator-agent"]
        original_assignees = self.subtask_with_assignees.assignees.copy()
        
        self.subtask_with_assignees.inherit_assignees_from_parent(parent_assignees)
        
        # Should not change assignees
        assert self.subtask_with_assignees.assignees == original_assignees

    def test_inherit_assignees_from_parent_empty_parent(self):
        """Test inheritance when parent has no assignees"""
        parent_assignees = []
        
        self.subtask_no_assignees.inherit_assignees_from_parent(parent_assignees)
        
        # Should not change assignees
        assert self.subtask_no_assignees.assignees == []


class TestAgentInheritanceService:
    """Test Agent Inheritance Service"""

    def setup_method(self):
        """Setup test data"""
        self.mock_task_repo = Mock()
        self.mock_subtask_repo = Mock()
        self.service = AgentInheritanceService(self.mock_task_repo, self.mock_subtask_repo)
        
        # Setup test entities
        self.parent_task_id = TaskId("parent-123")
        self.parent_task = Task(
            id=self.parent_task_id,
            title="Parent Task",
            description="Parent Description",
            assignees=["coding-agent", "@test-orchestrator-agent"]
        )
        
        self.subtask_id = SubtaskId("subtask-456")
        self.subtask_no_assignees = Subtask(
            id=self.subtask_id,
            title="Subtask",
            description="Subtask Description",
            parent_task_id=self.parent_task_id,
            assignees=[]
        )
        
        self.subtask_with_assignees = Subtask(
            id=self.subtask_id,
            title="Subtask",
            description="Subtask Description",
            parent_task_id=self.parent_task_id,
            assignees=["@security-auditor-agent"]
        )

    def test_apply_agent_inheritance_success(self):
        """Test successful agent inheritance application"""
        result = self.service.apply_agent_inheritance(
            self.subtask_no_assignees, 
            self.parent_task
        )
        
        assert result.assignees == ["coding-agent", "@test-orchestrator-agent"]
        
        # Check domain event was raised
        events = result.get_events()
        assert len(events) == 1

    def test_apply_agent_inheritance_subtask_has_assignees(self):
        """Test inheritance when subtask already has assignees"""
        original_assignees = self.subtask_with_assignees.assignees.copy()
        
        result = self.service.apply_agent_inheritance(
            self.subtask_with_assignees,
            self.parent_task
        )
        
        # Should not change assignees
        assert result.assignees == original_assignees

    def test_apply_agent_inheritance_fetch_parent_task(self):
        """Test inheritance when parent task is fetched from repository"""
        self.mock_task_repo.find_by_id.return_value = self.parent_task
        
        result = self.service.apply_agent_inheritance(self.subtask_no_assignees)
        
        self.mock_task_repo.find_by_id.assert_called_once_with(self.parent_task_id)
        assert result.assignees == ["coding-agent", "@test-orchestrator-agent"]

    def test_apply_agent_inheritance_parent_not_found(self):
        """Test inheritance when parent task is not found"""
        self.mock_task_repo.find_by_id.return_value = None
        
        result = self.service.apply_agent_inheritance(self.subtask_no_assignees)
        
        # Should not change assignees
        assert result.assignees == []

    def test_apply_inheritance_to_all_subtasks(self):
        """Test applying inheritance to all subtasks of a task"""
        subtasks = [self.subtask_no_assignees, self.subtask_with_assignees]
        
        self.mock_task_repo.find_by_id.return_value = self.parent_task
        self.mock_subtask_repo.find_by_parent_task_id.return_value = subtasks
        
        updated = self.service.apply_inheritance_to_all_subtasks(self.parent_task_id)
        
        assert len(updated) == 1  # Only one subtask should be updated
        assert updated[0] == self.subtask_no_assignees
        self.mock_subtask_repo.save.assert_called_once()

    def test_validate_agent_assignments_valid(self):
        """Test validating valid agent assignments"""
        assignees = ["coding-agent", "@test-orchestrator-agent"]
        validated = self.service.validate_agent_assignments(assignees)
        
        expected = ["@coding-agent", "@test-orchestrator-agent"]
        assert validated == expected

    def test_validate_agent_assignments_invalid(self):
        """Test validating invalid agent assignments"""
        assignees = ["invalid-agent"]
        
        with pytest.raises(ValueError):
            self.service.validate_agent_assignments(assignees)

    def test_get_inheritance_summary(self):
        """Test getting inheritance summary for a task"""
        subtasks = [self.subtask_no_assignees, self.subtask_with_assignees]
        
        self.mock_task_repo.find_by_id.return_value = self.parent_task
        self.mock_subtask_repo.find_by_parent_task_id.return_value = subtasks
        
        summary = self.service.get_inheritance_summary(self.parent_task_id)
        
        assert summary["task_id"] == str(self.parent_task_id)
        assert summary["parent_assignee_count"] == 2
        assert summary["total_subtasks"] == 2
        assert summary["subtasks_with_assignees"] == 1
        assert summary["subtasks_inheriting"] == 1
        assert len(summary["subtask_details"]) == 2

    def test_get_inheritance_summary_task_not_found(self):
        """Test getting inheritance summary when task not found"""
        self.mock_task_repo.find_by_id.return_value = None
        
        summary = self.service.get_inheritance_summary(self.parent_task_id)
        
        assert "error" in summary
        assert "not found" in summary["error"]


class TestAgentInheritanceIntegration:
    """Integration tests for agent inheritance functionality"""

    @pytest.fixture
    def sample_parent_task(self):
        """Create a sample parent task with assignees"""
        return Task(
            id=TaskId("parent-task-123"),
            title="Parent Task",
            description="Parent Description",
            assignees=["coding-agent", "@test-orchestrator-agent", "documentation-agent"]
        )

    @pytest.fixture
    def sample_subtask_no_assignees(self, sample_parent_task):
        """Create a sample subtask with no assignees"""
        return Subtask(
            id=SubtaskId("subtask-no-assignees"),
            title="Subtask Without Assignees",
            description="Should inherit from parent",
            parent_task_id=sample_parent_task.id,
            assignees=[]
        )

    @pytest.fixture
    def sample_subtask_with_assignees(self, sample_parent_task):
        """Create a sample subtask with assignees"""
        return Subtask(
            id=SubtaskId("subtask-with-assignees"),
            title="Subtask With Assignees", 
            description="Should not inherit from parent",
            parent_task_id=sample_parent_task.id,
            assignees=["@security-auditor-agent"]
        )

    def test_end_to_end_inheritance_flow(self, sample_parent_task, sample_subtask_no_assignees):
        """Test complete inheritance flow from parent to subtask"""
        # Mock repositories
        mock_task_repo = Mock()
        mock_subtask_repo = Mock()
        mock_task_repo.find_by_id.return_value = sample_parent_task
        
        # Create service
        service = AgentInheritanceService(mock_task_repo, mock_subtask_repo)
        
        # Apply inheritance
        result = service.apply_agent_inheritance(sample_subtask_no_assignees)
        
        # Verify inheritance was applied
        assert result.assignees == ["coding-agent", "@test-orchestrator-agent", "documentation-agent"]
        assert result.has_assignees() is True
        assert result.should_inherit_assignees() is False  # Now has assignees

    def test_inheritance_with_validation_errors(self):
        """Test inheritance behavior when validation fails"""
        # Create task with invalid assignees (for testing error handling)
        invalid_parent = Task(
            id=TaskId("invalid-parent"),
            title="Invalid Parent",
            description="Has invalid assignees",
        )
        # Manually set invalid assignees to test error handling
        invalid_parent.assignees = ["coding-agent", "invalid-agent"]  # One valid, one invalid
        
        subtask = Subtask(
            id=SubtaskId("test-subtask"),
            title="Test Subtask",
            description="Test",
            parent_task_id=invalid_parent.id,
            assignees=[]
        )
        
        # The inheritance should work since we're copying existing assignees
        # Validation happens at input time, not inheritance time
        subtask.inherit_assignees_from_parent(invalid_parent.assignees)
        
        assert subtask.assignees == ["coding-agent", "invalid-agent"]


if __name__ == "__main__":
    pytest.main([__file__])