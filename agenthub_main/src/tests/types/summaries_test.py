"""Test suite for summary types."""

import pytest
from uuid import uuid4
from datetime import datetime

from fastmcp.types.summaries import (
    TaskSummary,
    SubtaskSummary,
    ProjectSummary,
    BranchSummary,
    AgentSummary,
    WorkflowSummary,
    StatisticsSummary
)


class TestTaskSummary:
    """Test cases for TaskSummary."""
    
    def test_task_summary_complete(self):
        """Test TaskSummary with all fields."""
        summary = TaskSummary(
            id=str(uuid4()),
            title="Task Summary",
            status="in_progress",
            priority="high",
            assignee_count=3,
            subtask_count=5,
            completed_subtasks=2,
            progress_percentage=40,
            has_blockers=True,
            is_overdue=False,
            labels=["urgent", "backend"]
        )
        
        assert summary.title == "Task Summary"
        assert summary.status == "in_progress"
        assert summary.priority == "high"
        assert summary.assignee_count == 3
        assert summary.subtask_count == 5
        assert summary.completed_subtasks == 2
        assert summary.progress_percentage == 40
        assert summary.has_blockers is True
        assert summary.is_overdue is False
        assert summary.labels == ["urgent", "backend"]
    
    def test_task_summary_minimal(self):
        """Test TaskSummary with minimal fields."""
        summary = TaskSummary(
            id=str(uuid4()),
            title="Minimal Task",
            status="todo",
            priority="low",
            assignee_count=0,
            subtask_count=0,
            completed_subtasks=0,
            progress_percentage=0,
            has_blockers=False,
            is_overdue=False,
            labels=[]
        )
        
        assert summary.assignee_count == 0
        assert summary.subtask_count == 0
        assert summary.progress_percentage == 0
        assert summary.has_blockers is False
    
    def test_task_summary_progress_calculation(self):
        """Test TaskSummary progress calculation logic."""
        # Task with 10 subtasks, 7 completed
        summary = TaskSummary(
            id=str(uuid4()),
            title="Progress Test",
            status="in_progress",
            priority="medium",
            assignee_count=1,
            subtask_count=10,
            completed_subtasks=7,
            progress_percentage=70,
            has_blockers=False,
            is_overdue=False,
            labels=[]
        )
        
        assert summary.subtask_count == 10
        assert summary.completed_subtasks == 7
        assert summary.progress_percentage == 70


class TestSubtaskSummary:
    """Test cases for SubtaskSummary."""
    
    def test_subtask_summary(self):
        """Test SubtaskSummary creation."""
        summary = SubtaskSummary(
            id=str(uuid4()),
            title="Subtask Summary",
            status="done",
            priority="medium",
            progress_percentage=100,
            parent_task_id=str(uuid4()),
            parent_task_title="Parent Task"
        )
        
        assert summary.title == "Subtask Summary"
        assert summary.status == "done"
        assert summary.priority == "medium"
        assert summary.progress_percentage == 100
        assert summary.parent_task_title == "Parent Task"
    
    def test_subtask_summary_in_progress(self):
        """Test SubtaskSummary for in-progress subtask."""
        summary = SubtaskSummary(
            id=str(uuid4()),
            title="WIP Subtask",
            status="in_progress",
            priority="high",
            progress_percentage=60,
            parent_task_id=str(uuid4()),
            parent_task_title="Main Feature"
        )
        
        assert summary.status == "in_progress"
        assert summary.progress_percentage == 60


class TestProjectSummary:
    """Test cases for ProjectSummary."""
    
    def test_project_summary(self):
        """Test ProjectSummary with statistics."""
        summary = ProjectSummary(
            id=str(uuid4()),
            name="Test Project",
            description="Project for testing",
            total_tasks=100,
            completed_tasks=75,
            in_progress_tasks=20,
            blocked_tasks=5,
            total_branches=10,
            active_branches=3,
            total_agents=5,
            active_agents=4,
            overall_progress=75
        )
        
        assert summary.name == "Test Project"
        assert summary.total_tasks == 100
        assert summary.completed_tasks == 75
        assert summary.in_progress_tasks == 20
        assert summary.blocked_tasks == 5
        assert summary.total_branches == 10
        assert summary.active_branches == 3
        assert summary.total_agents == 5
        assert summary.active_agents == 4
        assert summary.overall_progress == 75
    
    def test_project_summary_empty(self):
        """Test ProjectSummary for empty project."""
        summary = ProjectSummary(
            id=str(uuid4()),
            name="Empty Project",
            description=None,
            total_tasks=0,
            completed_tasks=0,
            in_progress_tasks=0,
            blocked_tasks=0,
            total_branches=0,
            active_branches=0,
            total_agents=0,
            active_agents=0,
            overall_progress=0
        )
        
        assert summary.total_tasks == 0
        assert summary.overall_progress == 0


class TestBranchSummary:
    """Test cases for BranchSummary."""
    
    def test_branch_summary(self):
        """Test BranchSummary creation."""
        summary = BranchSummary(
            id=str(uuid4()),
            name="feature/authentication",
            project_id=str(uuid4()),
            project_name="Main Project",
            total_tasks=15,
            completed_tasks=10,
            in_progress_tasks=3,
            blocked_tasks=2,
            assigned_agents=["coding-agent", "test-agent"],
            progress_percentage=67,
            is_active=True,
            last_activity="2024-01-01T12:00:00Z"
        )
        
        assert summary.name == "feature/authentication"
        assert summary.total_tasks == 15
        assert summary.completed_tasks == 10
        assert summary.assigned_agents == ["coding-agent", "test-agent"]
        assert summary.progress_percentage == 67
        assert summary.is_active is True
    
    def test_branch_summary_inactive(self):
        """Test BranchSummary for inactive branch."""
        summary = BranchSummary(
            id=str(uuid4()),
            name="archive/old-feature",
            project_id=str(uuid4()),
            project_name="Main Project",
            total_tasks=50,
            completed_tasks=50,
            in_progress_tasks=0,
            blocked_tasks=0,
            assigned_agents=[],
            progress_percentage=100,
            is_active=False,
            last_activity="2023-12-01T00:00:00Z"
        )
        
        assert summary.is_active is False
        assert summary.progress_percentage == 100
        assert len(summary.assigned_agents) == 0


class TestAgentSummary:
    """Test cases for AgentSummary."""
    
    def test_agent_summary(self):
        """Test AgentSummary with workload."""
        summary = AgentSummary(
            id=str(uuid4()),
            name="coding-agent",
            project_id=str(uuid4()),
            project_name="Dev Project",
            assigned_tasks=8,
            completed_tasks=5,
            in_progress_tasks=2,
            blocked_tasks=1,
            branches_assigned_to=["feature/auth", "feature/ui"],
            workload_score=75,
            efficiency_score=85,
            status="active",
            last_activity="2024-01-01T10:00:00Z"
        )
        
        assert summary.name == "coding-agent"
        assert summary.assigned_tasks == 8
        assert summary.completed_tasks == 5
        assert summary.branches_assigned_to == ["feature/auth", "feature/ui"]
        assert summary.workload_score == 75
        assert summary.efficiency_score == 85
        assert summary.status == "active"
    
    def test_agent_summary_idle(self):
        """Test AgentSummary for idle agent."""
        summary = AgentSummary(
            id=str(uuid4()),
            name="idle-agent",
            project_id=str(uuid4()),
            project_name="Test Project",
            assigned_tasks=0,
            completed_tasks=10,
            in_progress_tasks=0,
            blocked_tasks=0,
            branches_assigned_to=[],
            workload_score=0,
            efficiency_score=100,
            status="idle",
            last_activity="2024-01-01T00:00:00Z"
        )
        
        assert summary.assigned_tasks == 0
        assert summary.workload_score == 0
        assert summary.status == "idle"


class TestWorkflowSummary:
    """Test cases for WorkflowSummary."""
    
    def test_workflow_summary(self):
        """Test WorkflowSummary creation."""
        summary = WorkflowSummary(
            id=str(uuid4()),
            name="Feature Development Workflow",
            type="sequential",
            total_steps=5,
            completed_steps=3,
            current_step="Code Review",
            estimated_completion="2024-02-01T00:00:00Z",
            blockers=["Pending approval", "Test failures"],
            assigned_agents=["coding-agent", "review-agent"],
            progress_percentage=60
        )
        
        assert summary.name == "Feature Development Workflow"
        assert summary.type == "sequential"
        assert summary.total_steps == 5
        assert summary.completed_steps == 3
        assert summary.current_step == "Code Review"
        assert len(summary.blockers) == 2
        assert summary.progress_percentage == 60
    
    def test_workflow_summary_parallel(self):
        """Test WorkflowSummary for parallel workflow."""
        summary = WorkflowSummary(
            id=str(uuid4()),
            name="Parallel Testing Workflow",
            type="parallel",
            total_steps=10,
            completed_steps=7,
            current_step="Multiple steps in progress",
            estimated_completion=None,
            blockers=[],
            assigned_agents=["test-agent-1", "test-agent-2", "test-agent-3"],
            progress_percentage=70
        )
        
        assert summary.type == "parallel"
        assert summary.current_step == "Multiple steps in progress"
        assert len(summary.assigned_agents) == 3


class TestStatisticsSummary:
    """Test cases for StatisticsSummary."""
    
    def test_statistics_summary(self):
        """Test StatisticsSummary with various metrics."""
        summary = StatisticsSummary(
            period="weekly",
            start_date="2024-01-01T00:00:00Z",
            end_date="2024-01-07T23:59:59Z",
            tasks_created=50,
            tasks_completed=35,
            tasks_cancelled=2,
            average_completion_time_hours=24.5,
            average_subtasks_per_task=3.2,
            most_productive_agent="coding-agent",
            most_active_branch="feature/main",
            bottleneck_areas=["Code Review", "Testing"],
            productivity_score=87
        )
        
        assert summary.period == "weekly"
        assert summary.tasks_created == 50
        assert summary.tasks_completed == 35
        assert summary.average_completion_time_hours == 24.5
        assert summary.average_subtasks_per_task == 3.2
        assert summary.most_productive_agent == "coding-agent"
        assert summary.bottleneck_areas == ["Code Review", "Testing"]
        assert summary.productivity_score == 87
    
    def test_statistics_summary_monthly(self):
        """Test StatisticsSummary for monthly period."""
        summary = StatisticsSummary(
            period="monthly",
            start_date="2024-01-01T00:00:00Z",
            end_date="2024-01-31T23:59:59Z",
            tasks_created=200,
            tasks_completed=150,
            tasks_cancelled=10,
            average_completion_time_hours=36.0,
            average_subtasks_per_task=4.5,
            most_productive_agent="test-agent",
            most_active_branch="develop",
            bottleneck_areas=["Deployment"],
            productivity_score=75
        )
        
        assert summary.period == "monthly"
        assert summary.tasks_created == 200
        assert summary.tasks_completed == 150
        assert summary.productivity_score == 75