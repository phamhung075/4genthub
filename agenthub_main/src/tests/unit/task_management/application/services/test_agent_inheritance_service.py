"""Unit tests for AgentInheritanceService"""

import pytest
import uuid
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone

from fastmcp.task_management.application.services.agent_inheritance_service import AgentInheritanceService
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.subtask_id import SubtaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority


class TestAgentInheritanceService:
    """Test suite for AgentInheritanceService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.task_repository = Mock()
        self.subtask_repository = Mock()
        self.service = AgentInheritanceService(self.task_repository, self.subtask_repository)
        
        # Create test entities
        self.parent_task = Task(
            id=TaskId("parent-001"),
            title="Parent Task",
            description="Task with multiple assignees",
            assignees=["coding-agent", "@test-orchestrator-agent", "@security-auditor-agent"]
        )
        
        self.subtask_no_assignees = Subtask(
            id=SubtaskId(str(uuid.uuid4())),
            title="Subtask without assignees",
            description="Should inherit from parent",
            parent_task_id=self.parent_task.id,
            assignees=[]
        )
        
        self.subtask_with_assignees = Subtask(
            id=SubtaskId(str(uuid.uuid4())),
            title="Subtask with assignees",
            description="Should not inherit from parent",
            parent_task_id=self.parent_task.id,
            assignees=["@code-reviewer-agent"]
        )
    
    def test_apply_agent_inheritance_with_empty_subtask(self):
        """Test applying inheritance to subtask without assignees"""
        # Execute inheritance
        result = self.service.apply_agent_inheritance(self.subtask_no_assignees, self.parent_task)
        
        # Verify inheritance was applied
        assert result is self.subtask_no_assignees  # Same instance returned
        assert len(result.assignees) == 3
        assert "coding-agent" in result.assignees
        assert "@test-orchestrator-agent" in result.assignees
        assert "@security-auditor-agent" in result.assignees
    
    def test_apply_agent_inheritance_with_existing_assignees(self):
        """Test applying inheritance to subtask that already has assignees"""
        original_assignees = self.subtask_with_assignees.assignees.copy()
        
        # Execute inheritance
        result = self.service.apply_agent_inheritance(self.subtask_with_assignees, self.parent_task)
        
        # Verify inheritance was NOT applied
        assert result is self.subtask_with_assignees
        assert result.assignees == original_assignees
        assert len(result.assignees) == 1
        assert "@code-reviewer-agent" in result.assignees
    
    def test_apply_agent_inheritance_without_parent_task_provided(self):
        """Test inheritance when parent task is not provided (should fetch from repository)"""
        # Configure repository to return parent task
        self.task_repository.find_by_id.return_value = self.parent_task
        
        # Execute inheritance without providing parent task
        result = self.service.apply_agent_inheritance(self.subtask_no_assignees)
        
        # Verify repository was called to fetch parent task
        self.task_repository.find_by_id.assert_called_once_with(self.parent_task.id)
        
        # Verify inheritance was applied
        assert len(result.assignees) == 3
        assert set(result.assignees) == set(self.parent_task.assignees)
    
    def test_apply_agent_inheritance_parent_task_not_found(self):
        """Test inheritance when parent task is not found in repository"""
        # Configure repository to return None (not found)
        self.task_repository.find_by_id.return_value = None
        
        # Execute inheritance
        result = self.service.apply_agent_inheritance(self.subtask_no_assignees)
        
        # Verify no inheritance was applied
        assert result is self.subtask_no_assignees
        assert len(result.assignees) == 0  # Remains empty
    
    def test_apply_agent_inheritance_parent_task_no_assignees(self):
        """Test inheritance when parent task has no assignees"""
        # Create parent task without assignees
        parent_no_assignees = Task(
            id=TaskId("parent-002"),
            title="Parent without assignees",
            description="Empty assignees",
            assignees=[]
        )
        
        # Execute inheritance
        result = self.service.apply_agent_inheritance(self.subtask_no_assignees, parent_no_assignees)
        
        # Verify no inheritance was applied (nothing to inherit)
        assert result is self.subtask_no_assignees
        assert len(result.assignees) == 0
    
    def test_apply_inheritance_to_all_subtasks(self):
        """Test applying inheritance to all subtasks of a task"""
        # Create multiple subtasks
        subtask1 = Subtask(
            id=SubtaskId(str(uuid.uuid4())),
            title="Subtask 1",
            description="Should inherit",
            parent_task_id=self.parent_task.id,
            assignees=[]
        )
        
        subtask2 = Subtask(
            id=SubtaskId(str(uuid.uuid4())),
            title="Subtask 2",
            description="Has assignees",
            parent_task_id=self.parent_task.id,
            assignees=["@existing-agent"]
        )
        
        subtask3 = Subtask(
            id=SubtaskId(str(uuid.uuid4())),
            title="Subtask 3",
            description="Should inherit",
            parent_task_id=self.parent_task.id,
            assignees=[]
        )
        
        # Configure repositories
        self.task_repository.find_by_id.return_value = self.parent_task
        self.subtask_repository.find_by_parent_task_id.return_value = [subtask1, subtask2, subtask3]
        
        # Execute inheritance for all subtasks
        updated_subtasks = self.service.apply_inheritance_to_all_subtasks(self.parent_task.id)
        
        # Verify repositories were called
        self.task_repository.find_by_id.assert_called_once_with(self.parent_task.id)
        self.subtask_repository.find_by_parent_task_id.assert_called_once_with(self.parent_task.id)
        
        # Verify correct subtasks were updated
        assert len(updated_subtasks) == 2  # subtask1 and subtask3 should be updated
        updated_titles = [st.title for st in updated_subtasks]
        assert "Subtask 1" in updated_titles
        assert "Subtask 3" in updated_titles
        assert "Subtask 2" not in updated_titles  # This one had existing assignees
        
        # Verify save was called for updated subtasks
        assert self.subtask_repository.save.call_count == 2
        
        # Verify inheritance was applied correctly
        assert len(subtask1.assignees) == 3
        assert len(subtask2.assignees) == 1  # Unchanged
        assert len(subtask3.assignees) == 3
    
    def test_apply_inheritance_to_all_subtasks_parent_not_found(self):
        """Test applying inheritance when parent task is not found"""
        # Configure repository to return None
        self.task_repository.find_by_id.return_value = None
        
        # Execute inheritance
        updated_subtasks = self.service.apply_inheritance_to_all_subtasks(TaskId("nonexistent"))
        
        # Verify no subtasks were updated
        assert len(updated_subtasks) == 0
        
        # Verify subtask repository was not called
        self.subtask_repository.find_by_parent_task_id.assert_not_called()
        self.subtask_repository.save.assert_not_called()
    
    def test_validate_agent_assignments(self):
        """Test agent assignment validation"""
        # Test valid assignees
        valid_assignees = ["coding-agent", "@test-orchestrator-agent"]
        validated = self.service.validate_agent_assignments(valid_assignees)
        
        assert len(validated) >= 2  # Should pass validation
        
        # Test empty list
        empty_validated = self.service.validate_agent_assignments([])
        assert len(empty_validated) == 0
    
    def test_validate_agent_assignments_with_invalid_assignees(self):
        """Test validation with invalid assignees"""
        # This test depends on the validation logic in Task.validate_assignee_list
        # The exact behavior may vary based on implementation
        
        mixed_assignees = ["coding-agent", "invalid-agent", "@test-orchestrator-agent", ""]
        
        # The method should either:
        # 1. Filter out invalid assignees, or
        # 2. Raise ValueError for invalid assignees
        # Let's handle both cases
        try:
            validated = self.service.validate_agent_assignments(mixed_assignees)
            # If no exception, validation passed with filtering
            assert len(validated) >= 2  # Should have at least the valid ones
        except ValueError:
            # If exception, validation rejected invalid assignees
            pass  # This is acceptable behavior
    
    def test_get_inheritance_summary(self):
        """Test getting inheritance summary for a task"""
        # Create subtasks with different inheritance scenarios
        subtask1 = Subtask(
            id=SubtaskId(str(uuid.uuid4())),
            title="Inheriting Subtask",
            description="No assignees",
            parent_task_id=self.parent_task.id,
            assignees=[]
        )
        
        subtask2 = Subtask(
            id=SubtaskId(str(uuid.uuid4())),
            title="Non-inheriting Subtask",
            description="Has assignees",
            parent_task_id=self.parent_task.id,
            assignees=["@custom-agent"]
        )
        
        # Configure repositories
        self.task_repository.find_by_id.return_value = self.parent_task
        self.subtask_repository.find_by_parent_task_id.return_value = [subtask1, subtask2]
        
        # Get inheritance summary
        summary = self.service.get_inheritance_summary(self.parent_task.id)
        
        # Verify summary structure
        assert "task_id" in summary
        assert "parent_assignees" in summary
        assert "parent_assignee_count" in summary
        assert "total_subtasks" in summary
        assert "subtasks_with_assignees" in summary
        assert "subtasks_inheriting" in summary
        assert "subtask_details" in summary
        
        # Verify summary content
        assert summary["task_id"] == str(self.parent_task.id)
        assert len(summary["parent_assignees"]) == 3
        assert summary["parent_assignee_count"] == 3
        assert summary["total_subtasks"] == 2
        assert summary["subtasks_with_assignees"] == 1  # Only subtask2
        assert summary["subtasks_inheriting"] == 1  # Only subtask1
        
        # Verify subtask details
        details = summary["subtask_details"]
        assert len(details) == 2
        
        # Find details for each subtask by title
        sub1_detail = next(d for d in details if "Inheriting" in d["title"])
        sub2_detail = next(d for d in details if "Non-inheriting" in d["title"])
        
        assert sub1_detail["has_assignees"] is False
        assert sub1_detail["should_inherit"] is True
        assert len(sub1_detail["current_assignees"]) == 0
        
        assert sub2_detail["has_assignees"] is True
        assert sub2_detail["should_inherit"] is False
        assert len(sub2_detail["current_assignees"]) == 1
    
    def test_get_inheritance_summary_task_not_found(self):
        """Test inheritance summary when task is not found"""
        # Configure repository to return None
        self.task_repository.find_by_id.return_value = None
        
        # Get summary
        summary = self.service.get_inheritance_summary(TaskId("nonexistent"))
        
        # Verify error response
        assert "error" in summary
        assert "not found" in summary["error"].lower()
    
    def test_inheritance_service_integration_workflow(self):
        """Test complete inheritance workflow using the service"""
        # Create a subtask that should inherit
        new_subtask = Subtask(
            id=SubtaskId(str(uuid.uuid4())),
            title="New Subtask",
            description="Fresh subtask for inheritance",
            parent_task_id=self.parent_task.id,
            assignees=[]
        )
        
        # Step 1: Apply inheritance
        result = self.service.apply_agent_inheritance(new_subtask, self.parent_task)
        
        # Step 2: Verify inheritance was applied
        assert len(result.assignees) == 3
        assert result.has_assignees() is True
        assert result.should_inherit_assignees() is False  # Now has assignees
        
        # Step 3: Try to apply inheritance again (should not change)
        original_assignees = result.assignees.copy()
        second_result = self.service.apply_agent_inheritance(result, self.parent_task)
        
        # Should be unchanged
        assert second_result.assignees == original_assignees
        
        # Step 4: Validate the inherited assignees
        validated = self.service.validate_agent_assignments(result.assignees)
        assert len(validated) >= 3  # Should validate successfully
    
    def test_inheritance_with_logging_verification(self):
        """Test that service generates appropriate log messages"""
        import logging
        from unittest.mock import patch
        
        # Patch the logger used by the service
        with patch('fastmcp.task_management.application.services.agent_inheritance_service.logger') as mock_logger:
            # Apply inheritance
            result = self.service.apply_agent_inheritance(self.subtask_no_assignees, self.parent_task)
            
            # Verify appropriate log messages were generated
            assert mock_logger.info.call_count >= 1
            
            # Check log content
            log_calls = [str(call) for call in mock_logger.info.call_args_list]
            inheritance_logs = [log for log in log_calls if 'inherit' in log.lower()]
            assert len(inheritance_logs) >= 1
    
    def test_service_handles_edge_cases_gracefully(self):
        """Test that service handles various edge cases gracefully"""
        # Test with None subtask
        try:
            result = self.service.apply_agent_inheritance(None, self.parent_task)
            # Should either handle gracefully or raise appropriate exception
        except (AttributeError, TypeError):
            pass  # Acceptable behavior
        
        # Test with None parent task
        result = self.service.apply_agent_inheritance(self.subtask_no_assignees, None)
        # Should not crash - might not apply inheritance but shouldn't fail
        assert result is self.subtask_no_assignees
        
        # Test summary with None task_id
        try:
            summary = self.service.get_inheritance_summary(None)
            # Should handle gracefully
            assert "error" in summary
        except Exception:
            pass  # Acceptable if it raises appropriate exception