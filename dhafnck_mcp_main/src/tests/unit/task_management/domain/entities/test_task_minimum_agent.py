"""Unit tests for minimum agent requirement on task creation"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority


class TestTaskMinimumAgentRequirement:
    """Test suite for task minimum agent requirement validation"""
    
    def test_task_creation_requires_at_least_one_agent(self):
        """Test that task creation fails without any agents"""
        with pytest.raises(ValueError, match="Task must have at least one agent assigned"):
            task = Task(
                id=TaskId(str(uuid4())),
                title="Task without agents",
                description="This task has no agents assigned",
                assignees=[]  # Empty assignees list
            )
    
    def test_task_creation_with_none_assignees_fails(self):
        """Test that task creation fails with None assignees"""
        with pytest.raises(ValueError, match="Task must have at least one agent assigned"):
            task = Task(
                id=TaskId(str(uuid4())),
                title="Task with None agents",
                description="This task has None for assignees",
                assignees=None  # None assignees
            )
    
    def test_task_creation_succeeds_with_one_agent(self):
        """Test that task creation succeeds with exactly one agent"""
        task = Task(
            id=TaskId(str(uuid4())),
            title="Task with one agent",
            description="This task has one agent assigned",
            assignees=["coding-agent"]
        )
        
        assert len(task.assignees) == 1
        assert "coding-agent" in task.assignees
    
    def test_task_creation_succeeds_with_multiple_agents(self):
        """Test that task creation succeeds with multiple agents"""
        task = Task(
            id=TaskId(str(uuid4())),
            title="Task with multiple agents",
            description="This task has multiple agents assigned",
            assignees=["coding-agent", "@test-orchestrator-agent", "code-reviewer-agent"]
        )
        
        assert len(task.assignees) == 3
        assert "coding-agent" in task.assignees
        assert "@test-orchestrator-agent" in task.assignees
        assert "code-reviewer-agent" in task.assignees
    
    def test_task_update_can_change_agents_but_not_remove_all(self):
        """Test that task update can change agents but cannot remove all"""
        task = Task(
            id=TaskId(str(uuid4())),
            title="Task to update",
            description="This task will have its agents updated",
            assignees=["coding-agent", "@test-orchestrator-agent"]
        )
        
        # Update to different agents - should succeed
        task.update_assignees(["@security-auditor-agent", "@debugger-agent"])
        assert len(task.assignees) == 2
        # Note: Agent names are normalized (hyphens to underscores)
        assert "security-auditor-agent" in task.assignees
        assert "debugger-agent" in task.assignees
        
        # Update to single agent - should succeed
        task.update_assignees(["coding-agent"])
        assert len(task.assignees) == 1
        assert "coding-agent" in task.assignees  # Normalized name
    
    def test_task_creation_with_invalid_agent_format_but_not_empty(self):
        """Test that task creation succeeds even with non-standard agent format as long as not empty"""
        # The validation at domain level only requires non-empty assignees
        # Agent role validation happens at the application/interface layer
        task = Task(
            id=TaskId(str(uuid4())),
            title="Task with custom agent",
            description="This task has a custom agent format",
            assignees=["custom-agent-name"]  # No @ prefix, not in enum
        )
        
        assert len(task.assignees) == 1
        assert "custom-agent-name" in task.assignees
    
    def test_task_creation_validates_other_fields_before_agents(self):
        """Test that other validations run before agent validation"""
        # Title validation should fail first
        with pytest.raises(ValueError, match="Task title cannot be empty"):
            task = Task(
                id=TaskId(str(uuid4())),
                title="",  # Empty title
                description="Valid description",
                assignees=[]  # Also invalid, but title should fail first
            )
        
        # Description validation should fail after title passes
        with pytest.raises(ValueError, match="Task description cannot be empty"):
            task = Task(
                id=TaskId(str(uuid4())),
                title="Valid title",
                description="",  # Empty description
                assignees=[]  # Also invalid, but description should fail first
            )
    
    def test_task_factory_method_requires_agents(self):
        """Test that Task.create factory method also requires agents"""
        # When using the factory method without assignees
        with pytest.raises(ValueError, match="Task must have at least one agent assigned"):
            task = Task.create(
                id=TaskId(str(uuid4())),
                title="Task via factory",
                description="Created using factory method",
                # No assignees parameter provided - defaults to empty
            )
    
    def test_task_factory_method_with_agents_succeeds(self):
        """Test that Task.create factory method works with agents"""
        task = Task.create(
            id=TaskId(str(uuid4())),
            title="Task via factory",
            description="Created using factory method",
            assignees=["coding-agent", "@test-orchestrator-agent"]
        )
        
        assert len(task.assignees) == 2
        assert "coding-agent" in task.assignees
        assert "@test-orchestrator-agent" in task.assignees
        # Check that TaskCreated event was raised
        events = task.get_events()
        assert len(events) == 1
        assert events[0].__class__.__name__ == "TaskCreated"