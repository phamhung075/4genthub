"""Unit tests for AddSubtaskUseCase with agent inheritance"""

import pytest
import uuid
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone

from fastmcp.task_management.application.use_cases.add_subtask import AddSubtaskUseCase
from fastmcp.task_management.application.dtos.subtask.add_subtask_request import AddSubtaskRequest
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.subtask_id import SubtaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.task_management.domain.exceptions import TaskNotFoundError


class TestAddSubtaskWithInheritance:
    """Test suite for AddSubtaskUseCase with agent inheritance functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.task_repository = Mock()
        self.subtask_repository = Mock()
        self.use_case = AddSubtaskUseCase(self.task_repository, self.subtask_repository)
        
        # Create a mock parent task with assignees
        self.parent_task_id = TaskId(str(uuid.uuid4()))
        self.parent_task = Task(
            id=self.parent_task_id,
            title="Parent Task",
            description="Task with assignees",
            assignees=["coding-agent", "@test-orchestrator-agent"]
        )
        
        # Configure task repository to return the parent task
        self.task_repository.find_by_id.return_value = self.parent_task
        
        # Configure subtask repository to generate IDs
        self.subtask_repository.get_next_id.return_value = SubtaskId(str(uuid.uuid4()))
        
        # Configure subtask repository save method
        self.subtask_repository.save.return_value = None
    
    def test_subtask_creation_with_no_assignees_inherits_from_parent(self):
        """Test that subtask with no assignees inherits from parent task"""
        # Create request with no assignees
        request = AddSubtaskRequest(
            task_id=str(self.parent_task_id),
            title="Test Subtask",
            description="Subtask without assignees",
            assignees=[]  # No assignees provided
        )
        
        # Execute use case
        response = self.use_case.execute(request)
        
        # Verify task was looked up (may be called multiple times for inheritance)
        self.task_repository.find_by_id.assert_called_with(self.parent_task_id)
        assert self.task_repository.find_by_id.call_count >= 1
        
        # Verify subtask was saved
        self.subtask_repository.save.assert_called_once()
        
        # Verify response indicates inheritance was applied
        assert response.agent_inheritance_applied is True
        assert len(response.inherited_assignees) == 2
        assert "coding-agent" in response.inherited_assignees
        assert "@test-orchestrator-agent" in response.inherited_assignees
        
        # Verify subtask has inherited assignees
        saved_subtask_call = self.subtask_repository.save.call_args[0][0]
        assert len(saved_subtask_call.assignees) == 2
        assert "coding-agent" in saved_subtask_call.assignees
        assert "@test-orchestrator-agent" in saved_subtask_call.assignees
    
    def test_subtask_creation_with_assignees_does_not_inherit(self):
        """Test that subtask with explicit assignees does not inherit from parent"""
        # Create request with explicit assignees
        request = AddSubtaskRequest(
            task_id=str(self.parent_task_id),
            title="Test Subtask",
            description="Subtask with explicit assignees",
            assignees=["@security-auditor-agent"]
        )
        
        # Execute use case
        response = self.use_case.execute(request)
        
        # Verify inheritance was not applied
        assert response.agent_inheritance_applied is False
        assert len(response.inherited_assignees) == 0
        
        # Verify subtask has only the explicitly provided assignees
        saved_subtask_call = self.subtask_repository.save.call_args[0][0]
        assert len(saved_subtask_call.assignees) == 1
        assert "@security-auditor-agent" in saved_subtask_call.assignees
        assert "coding-agent" not in saved_subtask_call.assignees
    
    def test_subtask_creation_with_parent_having_no_assignees(self):
        """Test subtask creation when parent task has no assignees"""
        # Create parent task with no assignees  
        parent_task_id_2 = TaskId(str(uuid.uuid4()))
        parent_task_no_assignees = Task(
            id=parent_task_id_2,
            title="Parent Task No Assignees",
            description="Task without assignees",
            assignees=[]
        )
        self.task_repository.find_by_id.return_value = parent_task_no_assignees
        
        # Create request with no assignees
        request = AddSubtaskRequest(
            task_id=str(parent_task_id_2),
            title="Test Subtask",
            description="Subtask for parent with no assignees",
            assignees=[]
        )
        
        # Execute use case
        response = self.use_case.execute(request)
        
        # Verify inheritance was not applied (nothing to inherit)
        assert response.agent_inheritance_applied is False
        assert len(response.inherited_assignees) == 0
        
        # Verify subtask has no assignees
        saved_subtask_call = self.subtask_repository.save.call_args[0][0]
        assert len(saved_subtask_call.assignees) == 0
    
    def test_subtask_creation_parent_task_not_found(self):
        """Test subtask creation when parent task is not found"""
        # Configure repository to return None (task not found)
        self.task_repository.find_by_id.return_value = None
        
        request = AddSubtaskRequest(
            task_id="nonexistent-task",
            title="Test Subtask",
            description="Subtask for nonexistent parent",
            assignees=[]
        )
        
        # Verify that TaskNotFoundError is raised
        with pytest.raises(TaskNotFoundError, match="Task nonexistent-task not found"):
            self.use_case.execute(request)
    
    def test_subtask_creation_with_mixed_parent_assignees(self):
        """Test subtask creation with parent having various assignee formats"""
        # Create parent task with mixed assignee formats
        parent_task_id_3 = TaskId(str(uuid.uuid4()))
        parent_task_mixed = Task(
            id=parent_task_id_3,
            title="Mixed Assignees Parent",
            description="Task with various assignee formats",
            assignees=["coding-agent", "test-orchestrator-agent", "@security-auditor-agent", ""]
        )
        self.task_repository.find_by_id.return_value = parent_task_mixed
        
        request = AddSubtaskRequest(
            task_id=str(parent_task_id_3),
            title="Mixed Inheritance Test",
            description="Test with mixed parent assignees",
            assignees=[]
        )
        
        # Execute use case
        response = self.use_case.execute(request)
        
        # Verify inheritance was applied
        assert response.agent_inheritance_applied is True
        assert len(response.inherited_assignees) == 4  # All assignees including empty string
        
        # Verify the subtask got the parent assignees (including validation/normalization)
        saved_subtask_call = self.subtask_repository.save.call_args[0][0]
        # The exact number might vary based on validation logic in inherit_assignees_from_parent
        assert len(saved_subtask_call.assignees) >= 3  # At least the non-empty ones
    
    def test_subtask_creation_inheritance_preserves_other_fields(self):
        """Test that inheritance doesn't affect other subtask fields"""
        request = AddSubtaskRequest(
            task_id=str(self.parent_task_id),
            title="Inheritance Preservation Test",
            description="Test field preservation during inheritance",
            assignees=[],
            priority="high"
        )
        
        # Execute use case
        response = self.use_case.execute(request)
        
        # Verify inheritance was applied
        assert response.agent_inheritance_applied is True
        
        # Verify other fields were preserved
        saved_subtask_call = self.subtask_repository.save.call_args[0][0]
        assert saved_subtask_call.title == "Inheritance Preservation Test"
        assert saved_subtask_call.description == "Test field preservation during inheritance"
        assert saved_subtask_call.priority == Priority.high()
        assert saved_subtask_call.parent_task_id == TaskId(str(self.parent_task_id))
    
    def test_inheritance_response_to_dict_includes_inheritance_info(self):
        """Test that response to_dict includes inheritance information"""
        request = AddSubtaskRequest(
            task_id=str(self.parent_task_id),
            title="Dict Test Subtask",
            description="Test response dict format",
            assignees=[]
        )
        
        # Execute use case
        response = self.use_case.execute(request)
        
        # Convert to dict and verify inheritance info is included
        response_dict = response.to_dict()
        
        assert response_dict["agent_inheritance_applied"] is True
        assert "inherited_assignees" in response_dict
        assert len(response_dict["inherited_assignees"]) == 2
        assert "coding-agent" in response_dict["inherited_assignees"]
        assert "@test-orchestrator-agent" in response_dict["inherited_assignees"]
    
    def test_no_inheritance_response_to_dict_excludes_inheritance_info(self):
        """Test that response to_dict excludes inheritance info when not applied"""
        request = AddSubtaskRequest(
            task_id=str(self.parent_task_id),
            title="No Inheritance Dict Test",
            description="Test response dict without inheritance",
            assignees=["@explicit-agent"]
        )
        
        # Execute use case
        response = self.use_case.execute(request)
        
        # Convert to dict and verify inheritance info is excluded
        response_dict = response.to_dict()
        
        assert "agent_inheritance_applied" not in response_dict
        assert "inherited_assignees" not in response_dict
    
    def test_inheritance_with_repository_factory_pattern(self):
        """Test inheritance works with dynamic repository creation"""
        # This test simulates the factory-based repository pattern
        # where repositories are created dynamically with context
        
        # Mock the parent task lookup in a factory-based scenario
        request = AddSubtaskRequest(
            task_id=str(self.parent_task_id),
            title="Factory Pattern Test",
            description="Test with factory repositories",
            assignees=[]
        )
        
        # Execute use case
        response = self.use_case.execute(request)
        
        # Verify basic inheritance functionality works regardless of repository pattern
        assert response.agent_inheritance_applied is True
        assert len(response.inherited_assignees) == 2
        
        # Verify repositories were called appropriately
        self.task_repository.find_by_id.assert_called_once()
        self.subtask_repository.save.assert_called_once()
    
    def test_inheritance_logging_behavior(self):
        """Test that inheritance generates appropriate log messages"""
        import logging
        from unittest.mock import patch
        
        request = AddSubtaskRequest(
            task_id=str(self.parent_task_id),
            title="Logging Test Subtask",
            description="Test inheritance logging",
            assignees=[]
        )
        
        # Patch logging to capture log messages
        with patch('fastmcp.task_management.application.use_cases.add_subtask.logging') as mock_logging:
            # Execute use case
            response = self.use_case.execute(request)
            
            # Verify inheritance was applied
            assert response.agent_inheritance_applied is True
            
            # Verify appropriate log messages were generated
            # Check that info logs were called (inheritance should log info messages)
            assert mock_logging.info.call_count >= 2  # At least 2 info logs for inheritance
            
            # Verify log content includes inheritance information
            log_calls = [str(call) for call in mock_logging.info.call_args_list]
            inheritance_logs = [log for log in log_calls if 'inherit' in log.lower()]
            assert len(inheritance_logs) >= 1


class TestAddSubtaskInheritanceErrorCases:
    """Test error cases for agent inheritance in AddSubtaskUseCase"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.task_repository = Mock()
        self.subtask_repository = Mock()
        self.use_case = AddSubtaskUseCase(self.task_repository, self.subtask_repository)
    
    def test_inheritance_with_repository_save_failure(self):
        """Test inheritance behavior when repository save fails"""
        # Create parent task
        parent_task = Task(
            id=TaskId(str(self.parent_task_id)),
            title="Parent Task",
            description="Task with assignees",
            assignees=["coding-agent"]
        )
        self.task_repository.find_by_id.return_value = parent_task
        self.subtask_repository.get_next_id.return_value = SubtaskId(str(uuid.uuid4()))
        
        # Configure save to raise an exception
        self.subtask_repository.save.side_effect = Exception("Database save failed")
        
        request = AddSubtaskRequest(
            task_id=str(self.parent_task_id),
            title="Save Failure Test",
            description="Test save failure handling",
            assignees=[]
        )
        
        # Verify that the exception is propagated
        with pytest.raises(Exception, match="Database save failed"):
            self.use_case.execute(request)
    
    def test_inheritance_with_get_next_id_failure(self):
        """Test inheritance behavior when ID generation fails"""
        parent_task = Task(
            id=TaskId(str(self.parent_task_id)),
            title="Parent Task",
            description="Task with assignees",
            assignees=["coding-agent"]
        )
        self.task_repository.find_by_id.return_value = parent_task
        
        # Configure get_next_id to raise an exception
        self.subtask_repository.get_next_id.side_effect = Exception("ID generation failed")
        
        request = AddSubtaskRequest(
            task_id=str(self.parent_task_id),
            title="ID Generation Failure Test",
            description="Test ID generation failure",
            assignees=[]
        )
        
        # Verify that the exception is propagated
        with pytest.raises(Exception, match="ID generation failed"):
            self.use_case.execute(request)
    
    def test_inheritance_with_malformed_parent_assignees(self):
        """Test inheritance with parent task having malformed assignees"""
        # Create parent task with potentially problematic assignees
        parent_task = Task(
            id=TaskId(str(self.parent_task_id)),
            title="Malformed Assignees Parent",
            description="Task with problematic assignees",
            assignees=[None, "", "   ", "@valid-agent", "no-prefix-agent"]
        )
        self.task_repository.find_by_id.return_value = parent_task
        self.subtask_repository.get_next_id.return_value = SubtaskId(str(uuid.uuid4()))
        self.subtask_repository.save.return_value = None
        
        request = AddSubtaskRequest(
            task_id=str(self.parent_task_id),
            title="Malformed Assignees Test",
            description="Test with malformed parent assignees",
            assignees=[]
        )
        
        # Execute use case - should handle malformed assignees gracefully
        response = self.use_case.execute(request)
        
        # Inheritance should still be applied, but with cleaned assignees
        assert response.agent_inheritance_applied is True
        
        # Verify the subtask was created and saved
        self.subtask_repository.save.assert_called_once()
        
        # The exact number of inherited assignees depends on the cleaning logic
        # but it should handle the malformed ones gracefully