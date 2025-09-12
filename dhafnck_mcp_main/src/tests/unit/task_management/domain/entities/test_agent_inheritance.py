"""Unit tests for agent assignment and inheritance functionality"""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.subtask_id import SubtaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority


class TestAgentInheritance:
    """Test suite for agent assignment and inheritance"""
    
    def test_task_with_multiple_agents(self):
        """Test creating a task with multiple agents"""
        task = Task(
            id=TaskId("task-001"),
            title="Multi-agent task",
            description="Task with multiple agents",
            assignees=["coding-agent", "@test-orchestrator-agent", "code-reviewer-agent"]
        )
        
        assert len(task.assignees) == 3
        assert "coding-agent" in task.assignees
        assert "@test-orchestrator-agent" in task.assignees
        assert "code-reviewer-agent" in task.assignees
    
    def test_subtask_inherits_parent_assignees(self):
        """Test subtask inheriting assignees from parent task"""
        parent_task_id = TaskId("task-001")
        
        # Create subtask without assignees
        subtask = Subtask(
            id=SubtaskId(str(uuid.uuid4())),
            title="Subtask without agents",
            description="Should inherit from parent",
            parent_task_id=parent_task_id,
            assignees=[]  # No assignees initially
        )
        
        # Check that subtask has no assignees initially
        assert subtask.has_assignees() is False
        assert subtask.should_inherit_assignees() is True
        
        # Inherit assignees from parent
        parent_assignees = ["coding-agent", "@test-orchestrator-agent"]
        subtask.inherit_assignees_from_parent(parent_assignees)
        
        # Verify inheritance
        assert subtask.has_assignees() is True
        assert len(subtask.assignees) == 2
        assert "coding-agent" in subtask.assignees
        assert "@test-orchestrator-agent" in subtask.assignees
    
    def test_subtask_does_not_inherit_if_has_assignees(self):
        """Test that subtask with existing assignees doesn't inherit"""
        parent_task_id = TaskId("task-001")
        
        # Create subtask with its own assignees
        subtask = Subtask(
            id=SubtaskId(str(uuid.uuid4())),
            title="Subtask with agents",
            description="Has its own agents",
            parent_task_id=parent_task_id,
            assignees=["@security-auditor-agent"]
        )
        
        # Check that subtask has assignees
        assert subtask.has_assignees() is True
        assert subtask.should_inherit_assignees() is False
        
        # Try to inherit (should not change existing assignees)
        parent_assignees = ["coding-agent", "@test-orchestrator-agent"]
        subtask.inherit_assignees_from_parent(parent_assignees)
        
        # Verify original assignees remain unchanged
        assert len(subtask.assignees) == 1
        assert "@security-auditor-agent" in subtask.assignees
        assert "coding-agent" not in subtask.assignees
    
    def test_get_inherited_assignees_for_subtasks(self):
        """Test getting assignees that subtasks should inherit"""
        task = Task(
            id=TaskId("task-001"),
            title="Parent task",
            description="Task with agents to inherit",
            assignees=["coding-agent", "@debugger-agent"]
        )
        
        inherited = task.get_inherited_assignees_for_subtasks()
        
        assert len(inherited) == 2
        assert "coding-agent" in inherited
        assert "@debugger-agent" in inherited
        # Ensure it's a copy, not the original list
        inherited.append("@new-agent")
        assert "@new-agent" not in task.assignees
    
    def test_empty_parent_assignees_no_inheritance(self):
        """Test that empty parent assignees don't cause inheritance"""
        parent_task_id = TaskId("task-001")
        
        subtask = Subtask(
            id=SubtaskId(str(uuid.uuid4())),
            title="Subtask",
            description="Test subtask",
            parent_task_id=parent_task_id,
            assignees=[]
        )
        
        # Try to inherit empty list
        subtask.inherit_assignees_from_parent([])
        
        # Verify no change
        assert subtask.has_assignees() is False
        assert len(subtask.assignees) == 0
    
    def test_agent_inheritance_with_validation(self):
        """Test agent inheritance with proper AgentRole validation"""
        parent_task_id = TaskId("task-001")
        
        # Create subtask without assignees
        subtask = Subtask(
            id=SubtaskId(str(uuid.uuid4())),
            title="Subtask for validation test",
            description="Should inherit validated agents",
            parent_task_id=parent_task_id,
            assignees=[]
        )
        
        # Parent has valid and invalid assignees
        parent_assignees = ["coding-agent", "invalid-agent", "@test-orchestrator-agent", ""]
        
        # Apply inheritance
        subtask.inherit_assignees_from_parent(parent_assignees)
        
        # Should inherit all provided assignees (validation is done at task level)
        assert len(subtask.assignees) == 4  # All assignees including empty string preserved
        assert "coding-agent" in subtask.assignees
        assert "invalid-agent" in subtask.assignees  # Kept as-is per current logic
        assert "@test-orchestrator-agent" in subtask.assignees
        assert "" in subtask.assignees  # Empty string is preserved in inheritance
    
    def test_inheritance_preserves_assignee_format(self):
        """Test that inheritance preserves assignee format (@ prefix)"""
        parent_task_id = TaskId("task-001")
        
        subtask = Subtask(
            id=SubtaskId(str(uuid.uuid4())),
            title="Format test subtask",
            description="Test format preservation",
            parent_task_id=parent_task_id,
            assignees=[]
        )
        
        # Parent has assignees with and without @ prefix
        parent_assignees = ["coding-agent", "test-orchestrator-agent", "@security-auditor-agent"]
        
        subtask.inherit_assignees_from_parent(parent_assignees)
        
        # All assignees should be inherited as-is
        assert len(subtask.assignees) == 3
        assert "coding-agent" in subtask.assignees
        assert "test-orchestrator-agent" in subtask.assignees
        assert "@security-auditor-agent" in subtask.assignees
    
    def test_inheritance_generates_domain_event(self):
        """Test that inheritance generates proper domain events"""
        parent_task_id = TaskId("task-001")
        
        subtask = Subtask(
            id=SubtaskId(str(uuid.uuid4())),
            title="Event test subtask",
            description="Should generate events",
            parent_task_id=parent_task_id,
            assignees=[]
        )
        
        # Clear any existing events
        subtask.get_events()
        
        # Apply inheritance
        parent_assignees = ["coding-agent", "@test-orchestrator-agent"]
        subtask.inherit_assignees_from_parent(parent_assignees)
        
        # Check that domain event was generated
        events = subtask.get_events()
        assert len(events) > 0
        
        # Find the inheritance event
        inheritance_event = None
        for event in events:
            if hasattr(event, 'old_value') and 'inherited_from_parent' in str(event.old_value):
                inheritance_event = event
                break
        
        assert inheritance_event is not None
        assert str(subtask.id) in str(inheritance_event.new_value)
    
    def test_multiple_inheritance_cycles(self):
        """Test that multiple inheritance calls don't stack assignees"""
        parent_task_id = TaskId("task-001")
        
        subtask = Subtask(
            id=SubtaskId(str(uuid.uuid4())),
            title="Multiple inheritance test",
            description="Should not duplicate assignees",
            parent_task_id=parent_task_id,
            assignees=[]
        )
        
        parent_assignees = ["coding-agent", "@test-orchestrator-agent"]
        
        # Apply inheritance multiple times
        subtask.inherit_assignees_from_parent(parent_assignees)
        initial_count = len(subtask.assignees)
        
        # Second inheritance should not change anything (subtask already has assignees)
        subtask.inherit_assignees_from_parent(parent_assignees)
        
        # Count should remain the same
        assert len(subtask.assignees) == initial_count
        assert len(subtask.assignees) == 2  # Original assignees
    
    def test_inheritance_updates_timestamp(self):
        """Test that inheritance updates subtask timestamp"""
        parent_task_id = TaskId("task-001")
        
        subtask = Subtask(
            id=SubtaskId(str(uuid.uuid4())),
            title="Timestamp test subtask",
            description="Should update timestamp",
            parent_task_id=parent_task_id,
            assignees=[]
        )
        
        # Record original timestamp
        original_updated_at = subtask.updated_at
        
        # Wait a small amount to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        # Apply inheritance
        parent_assignees = ["coding-agent"]
        subtask.inherit_assignees_from_parent(parent_assignees)
        
        # Timestamp should be updated
        assert subtask.updated_at > original_updated_at
    
    def test_task_assignee_validation_method(self):
        """Test task's validate_assignee_list method works correctly"""
        task = Task(
            id=TaskId("task-001"),
            title="Validation test task",
            description="Test validation"
        )
        
        # Test valid assignees
        valid_assignees = ["coding-agent", "@test-orchestrator-agent"]
        validated = task.validate_assignee_list(valid_assignees)
        assert len(validated) == 2
        assert all(assignee.startswith("@") for assignee in validated)
        
        # Test empty list
        empty_validated = task.validate_assignee_list([])
        assert len(empty_validated) == 0
        
        # Test None input
        none_validated = task.validate_assignee_list(None)
        assert len(none_validated) == 0


class TestAgentInheritanceIntegration:
    """Integration tests for agent inheritance functionality"""
    
    def test_full_inheritance_workflow(self):
        """Test complete inheritance workflow from task creation to subtask inheritance"""
        # Create parent task with multiple agents
        parent_task = Task(
            id=TaskId("parent-001"),
            title="Parent Task",
            description="Task with multiple agents",
            assignees=["coding-agent", "@test-orchestrator-agent", "@security-auditor-agent"]
        )
        
        # Create multiple subtasks with different scenarios
        
        # Subtask 1: No assignees (should inherit)
        subtask1 = Subtask(
            id=SubtaskId(str(uuid.uuid4())),
            title="Subtask 1 - No assignees",
            description="Should inherit all parent assignees",
            parent_task_id=parent_task.id,
            assignees=[]
        )
        
        # Subtask 2: Has own assignees (should not inherit)
        subtask2 = Subtask(
            id=SubtaskId(str(uuid.uuid4())),
            title="Subtask 2 - Has assignees",
            description="Should keep own assignees",
            parent_task_id=parent_task.id,
            assignees=["code-reviewer-agent"]
        )
        
        # Apply inheritance to subtask 1
        inherited_assignees = parent_task.get_inherited_assignees_for_subtasks()
        subtask1.inherit_assignees_from_parent(inherited_assignees)
        
        # Try to apply inheritance to subtask 2 (should not change)
        subtask2.inherit_assignees_from_parent(inherited_assignees)
        
        # Verify results
        assert len(subtask1.assignees) == 3
        assert set(subtask1.assignees) == set(parent_task.assignees)
        
        assert len(subtask2.assignees) == 1
        assert subtask2.assignees[0] == "code-reviewer-agent"
    
    def test_inheritance_with_task_update(self):
        """Test that subtask inheritance works when parent task assignees are updated"""
        # Create parent task
        parent_task = Task(
            id=TaskId("parent-002"),
            title="Dynamic Parent Task",
            description="Task that will have assignees updated",
            assignees=["coding-agent"]
        )
        
        # Create subtask without assignees
        subtask = Subtask(
            id=SubtaskId(str(uuid.uuid4())),
            title="Dynamic Subtask",
            description="Should inherit updated assignees",
            parent_task_id=parent_task.id,
            assignees=[]
        )
        
        # Initial inheritance
        initial_assignees = parent_task.get_inherited_assignees_for_subtasks()
        subtask.inherit_assignees_from_parent(initial_assignees)
        
        assert len(subtask.assignees) == 1
        assert "coding-agent" in subtask.assignees
        
        # Update parent task assignees
        parent_task.update_assignees(["coding-agent", "@test-orchestrator-agent", "@security-auditor-agent"])
        
        # For new subtasks, they would inherit the updated assignees
        new_subtask = Subtask(
            id=SubtaskId(str(uuid.uuid4())),
            title="New Subtask",
            description="Should inherit updated assignees",
            parent_task_id=parent_task.id,
            assignees=[]
        )
        
        updated_assignees = parent_task.get_inherited_assignees_for_subtasks()
        new_subtask.inherit_assignees_from_parent(updated_assignees)
        
        assert len(new_subtask.assignees) == 3
        assert set(new_subtask.assignees) == set(parent_task.assignees)
    
    def test_inheritance_preserves_task_agent_info(self):
        """Test that inherited assignees preserve agent info functionality"""
        parent_task = Task(
            id=TaskId("parent-003"),
            title="Agent Info Parent",
            description="Parent with agent info",
            assignees=["coding-agent", "@test-orchestrator-agent"]
        )
        
        subtask = Subtask(
            id=SubtaskId(str(uuid.uuid4())),
            title="Agent Info Subtask",
            description="Should inherit agent info",
            parent_task_id=parent_task.id,
            assignees=[]
        )
        
        # Apply inheritance
        inherited_assignees = parent_task.get_inherited_assignees_for_subtasks()
        subtask.inherit_assignees_from_parent(inherited_assignees)
        
        # Test that assignees info methods work on subtask
        # (Note: Subtask doesn't have get_assignees_info method, but assignees should be valid)
        assert len(subtask.assignees) == 2
        assert all(isinstance(assignee, str) for assignee in subtask.assignees)
        
        # Verify parent task agent info methods still work
        parent_info = parent_task.get_assignees_info()
        assert len(parent_info) == 2
        assert all('role' in info for info in parent_info)