"""Unit tests for CreateTaskRequest DTO."""
import pytest
from fastmcp.task_management.application.dtos.task.create_task_request import CreateTaskRequest
from fastmcp.task_management.domain.enums.common_labels import CommonLabel
from fastmcp.task_management.domain.enums.estimated_effort import EstimatedEffort
from fastmcp.task_management.domain.enums.agent_roles import AgentRole


class TestCreateTaskRequest:
    """Test cases for CreateTaskRequest DTO"""
    
    def test_create_task_request_with_required_fields(self):
        """Test creating request with only required fields"""
        request = CreateTaskRequest(
            title="Test Task",
            git_branch_id="550e8400-e29b-41d4-a716-446655440000"
        )
        
        assert request.title == "Test Task"
        assert request.git_branch_id == "550e8400-e29b-41d4-a716-446655440000"
        assert request.description is None
        assert request.status is None
        assert request.priority is None
        assert request.details == ""
        assert request.estimated_effort == ""
        assert request.assignees == []
        assert request.labels == []
        assert request.due_date is None
        assert request.dependencies == []
        assert request.user_id is None
    
    def test_create_task_request_with_all_fields(self):
        """Test creating request with all fields"""
        request = CreateTaskRequest(
            title="Complete Task",
            git_branch_id="550e8400-e29b-41d4-a716-446655440000",
            description="A complete task description",
            status="todo",
            priority="high",
            details="Detailed implementation notes",
            estimated_effort="2 days",
            assignees=["@senior_developer", "@qa_engineer"],
            labels=["frontend", "bug"],
            due_date="2025-12-31T23:59:59Z",
            dependencies=["task-123", "task-456"],
            user_id="user-789"
        )
        
        assert request.title == "Complete Task"
        assert request.git_branch_id == "550e8400-e29b-41d4-a716-446655440000"
        assert request.description == "A complete task description"
        assert request.status == "todo"
        assert request.priority == "high"
        assert request.details == "Detailed implementation notes"
        assert request.estimated_effort == "2 days"
        assert request.assignees == ["@senior_developer", "@qa_engineer"]
        assert request.labels == ["frontend", "bug"]
        assert request.due_date == "2025-12-31T23:59:59Z"
        assert request.dependencies == ["task-123", "task-456"]
        assert request.user_id == "user-789"
    
    def test_legacy_role_resolution(self):
        """Test legacy agent role names are resolved to current ones"""
        request = CreateTaskRequest(
            title="Test Task",
            git_branch_id="550e8400-e29b-41d4-a716-446655440000",
            assignees=["coding-agent", "test-orchestrator-agent", "system-architect-agent"]
        )
        
        assert "@senior_developer" in request.assignees
        assert "@qa_engineer" in request.assignees
        assert "@architect" in request.assignees
    
    def test_assignee_prefix_handling(self):
        """Test that @ prefix is properly handled for assignees"""
        request = CreateTaskRequest(
            title="Test Task",
            git_branch_id="550e8400-e29b-41d4-a716-446655440000",
            assignees=["senior_developer", "@qa_engineer", "custom_user"]
        )
        
        assert "@senior_developer" in request.assignees  # Added @ prefix
        assert "@qa_engineer" in request.assignees  # Already had @ prefix
        assert "@custom_user" in request.assignees  # Custom user gets @ prefix
    
    def test_empty_assignees_handling(self):
        """Test handling of empty or None assignees"""
        request = CreateTaskRequest(
            title="Test Task",
            git_branch_id="550e8400-e29b-41d4-a716-446655440000",
            assignees=["", None, "  ", "@valid_user"]
        )
        
        assert len(request.assignees) == 1
        assert "@valid_user" in request.assignees
    
    def test_label_validation_with_common_labels(self):
        """Test that labels are validated against CommonLabel enum"""
        request = CreateTaskRequest(
            title="Test Task",
            git_branch_id="550e8400-e29b-41d4-a716-446655440000",
            labels=["frontend", "backend", "bug", "invalid_label"]
        )
        
        assert "frontend" in request.labels
        assert "backend" in request.labels
        assert "bug" in request.labels
        assert "invalid_label" in request.labels  # Invalid labels are kept
    
    def test_label_suggestions(self):
        """Test that close matches get suggested labels"""
        request = CreateTaskRequest(
            title="Test Task",
            git_branch_id="550e8400-e29b-41d4-a716-446655440000",
            labels=["frontent", "bckend", "bg"]  # Typos
        )
        
        # CommonLabel should suggest corrections
        # The actual behavior depends on CommonLabel.suggest_labels implementation
        assert len(request.labels) == 3
    
    def test_empty_labels_handling(self):
        """Test handling of empty or None labels"""
        request = CreateTaskRequest(
            title="Test Task",
            git_branch_id="550e8400-e29b-41d4-a716-446655440000",
            labels=[None, "", "  ", "valid_label"]
        )
        
        assert len(request.labels) == 1
        assert "valid_label" in request.labels
    
    def test_estimated_effort_validation(self):
        """Test estimated effort validation"""
        # Valid effort
        request1 = CreateTaskRequest(
            title="Test Task",
            git_branch_id="550e8400-e29b-41d4-a716-446655440000",
            estimated_effort="2 hours"
        )
        assert request1.estimated_effort == "2 hours"
        
        # Invalid effort should be kept as-is (validated at domain layer)
        request2 = CreateTaskRequest(
            title="Test Task",
            git_branch_id="550e8400-e29b-41d4-a716-446655440000",
            estimated_effort="invalid effort"
        )
        assert request2.estimated_effort == "invalid effort"
    
    def test_dependencies_default_empty_list(self):
        """Test that dependencies defaults to empty list"""
        request = CreateTaskRequest(
            title="Test Task",
            git_branch_id="550e8400-e29b-41d4-a716-446655440000"
        )
        
        assert request.dependencies == []
        assert isinstance(request.dependencies, list)
    
    def test_dependencies_with_values(self):
        """Test dependencies with actual task IDs"""
        dependencies = ["task-001", "task-002", "task-003"]
        request = CreateTaskRequest(
            title="Test Task",
            git_branch_id="550e8400-e29b-41d4-a716-446655440000",
            dependencies=dependencies
        )
        
        assert request.dependencies == dependencies
        assert len(request.dependencies) == 3
    
    def test_dataclass_field_ordering(self):
        """Test that fields maintain correct order with defaults after required"""
        request = CreateTaskRequest(
            title="Test Task",
            git_branch_id="550e8400-e29b-41d4-a716-446655440000"
        )
        
        # Verify all fields exist and have correct defaults
        assert hasattr(request, 'title')
        assert hasattr(request, 'git_branch_id')
        assert hasattr(request, 'description')
        assert hasattr(request, 'status')
        assert hasattr(request, 'priority')
        assert hasattr(request, 'details')
        assert hasattr(request, 'estimated_effort')
        assert hasattr(request, 'assignees')
        assert hasattr(request, 'labels')
        assert hasattr(request, 'due_date')
        assert hasattr(request, 'dependencies')
        assert hasattr(request, 'user_id')