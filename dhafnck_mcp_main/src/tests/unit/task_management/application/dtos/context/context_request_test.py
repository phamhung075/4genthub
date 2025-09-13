"""
Tests for Context Request DTOs

This module tests the context request DTO classes including:
- CreateContextRequest
- UpdateContextRequest
- GetContextRequest
- DeleteContextRequest
- ListContextsRequest
- GetPropertyRequest
- UpdatePropertyRequest
- MergeContextRequest
- MergeDataRequest
- AddInsightRequest
- AddProgressRequest
- UpdateNextStepsRequest
"""

import pytest
from datetime import datetime, timezone
from dataclasses import fields, is_dataclass

from fastmcp.task_management.application.dtos.context.context_request import (
    CreateContextRequest,
    UpdateContextRequest,
    GetContextRequest,
    DeleteContextRequest,
    ListContextsRequest,
    GetPropertyRequest,
    UpdatePropertyRequest,
    MergeContextRequest,
    MergeDataRequest,
    AddInsightRequest,
    AddProgressRequest,
    UpdateNextStepsRequest
)


class TestCreateContextRequest:
    """Test suite for CreateContextRequest DTO"""
    
    def test_create_context_request_creation(self):
        """Test creating a CreateContextRequest instance"""
        now = datetime.now(timezone.utc)
        request = CreateContextRequest(
            task_id="task-123",
            title="Test Context",
            description="Test Description",
            status="in_progress",
            priority="high",
            assignees=["user-1", "user-2"],
            labels=["bug", "urgent"],
            estimated_effort="3 hours",
            due_date=now,
            data={"custom": "data"}
        )
        
        assert pytest_request.task_id == "task-123"
        assert pytest_request.title == "Test Context"
        assert pytest_request.description == "Test Description"
        assert pytest_request.status == "in_progress"
        assert pytest_request.priority == "high"
        assert pytest_request.assignees == ["user-1", "user-2"]
        assert pytest_request.labels == ["bug", "urgent"]
        assert pytest_request.estimated_effort == "3 hours"
        assert pytest_request.due_date == now
        assert pytest_request.data == {"custom": "data"}
    
    def test_create_context_request_minimal(self):
        """Test creating a CreateContextRequest with minimal fields"""
        request = CreateContextRequest(
            task_id="task-123",
            title="Test Context"
        )
        
        assert pytest_request.task_id == "task-123"
        assert pytest_request.title == "Test Context"
        assert pytest_request.description == ""
        assert pytest_request.status is None
        assert pytest_request.priority is None
        assert pytest_request.assignees is None
        assert pytest_request.labels is None
        assert pytest_request.estimated_effort is None
        assert pytest_request.due_date is None
        assert pytest_request.data is None
    
    def test_create_context_request_is_dataclass(self):
        """Test that CreateContextRequest is a proper dataclass"""
        assert is_dataclass(CreateContextRequest)
        
        # Check expected fields
        field_names = {f.name for f in fields(CreateContextRequest)}
        expected_fields = {
            'task_id', 'title', 'description', 'status', 'priority',
            'assignees', 'labels', 'estimated_effort', 'due_date', 'data'
        }
        assert field_names == expected_fields


class TestUpdateContextRequest:
    """Test suite for UpdateContextRequest DTO"""
    
    def test_update_context_request_creation(self):
        """Test creating an UpdateContextRequest instance"""
        request = UpdateContextRequest(
            task_id="task-123",
            data={"status": "completed", "progress": 100}
        )
        
        assert pytest_request.task_id == "task-123"
        assert pytest_request.data == {"status": "completed", "progress": 100}
    
    def test_update_context_request_minimal(self):
        """Test creating an UpdateContextRequest with minimal fields"""
        request = UpdateContextRequest(task_id="task-123")
        
        assert pytest_request.task_id == "task-123"
        assert pytest_request.data is None


class TestGetContextRequest:
    """Test suite for GetContextRequest DTO"""
    
    def test_get_context_request_creation(self):
        """Test creating a GetContextRequest instance"""
        request = GetContextRequest(task_id="task-123")
        
        assert pytest_request.task_id == "task-123"
    
    def test_get_context_request_is_dataclass(self):
        """Test that GetContextRequest is a proper dataclass"""
        assert is_dataclass(GetContextRequest)
        field_names = {f.name for f in fields(GetContextRequest)}
        assert field_names == {'task_id'}


class TestDeleteContextRequest:
    """Test suite for DeleteContextRequest DTO"""
    
    def test_delete_context_request_creation(self):
        """Test creating a DeleteContextRequest instance"""
        request = DeleteContextRequest(task_id="task-123")
        
        assert pytest_request.task_id == "task-123"
    
    def test_delete_context_request_is_dataclass(self):
        """Test that DeleteContextRequest is a proper dataclass"""
        assert is_dataclass(DeleteContextRequest)
        field_names = {f.name for f in fields(DeleteContextRequest)}
        assert field_names == {'task_id'}


class TestListContextsRequest:
    """Test suite for ListContextsRequest DTO"""
    
    def test_list_contexts_request_creation(self):
        """Test creating a ListContextsRequest instance"""
        request = ListContextsRequest(
            user_id="user-123",
            project_id="project-456"
        )
        
        assert pytest_request.user_id == "user-123"
        assert pytest_request.project_id == "project-456"
    
    def test_list_contexts_request_defaults(self):
        """Test ListContextsRequest with default values"""
        request = ListContextsRequest()
        
        assert pytest_request.user_id is None
        assert pytest_request.project_id == ""


class TestGetPropertyRequest:
    """Test suite for GetPropertyRequest DTO"""
    
    def test_get_property_request_creation(self):
        """Test creating a GetPropertyRequest instance"""
        request = GetPropertyRequest(
            task_id="task-123",
            property_path="data.custom.field"
        )
        
        assert pytest_request.task_id == "task-123"
        assert pytest_request.property_path == "data.custom.field"


class TestUpdatePropertyRequest:
    """Test suite for UpdatePropertyRequest DTO"""
    
    def test_update_property_request_creation(self):
        """Test creating an UpdatePropertyRequest instance"""
        request = UpdatePropertyRequest(
            task_id="task-123",
            property_path="data.status",
            value="completed"
        )
        
        assert pytest_request.task_id == "task-123"
        assert pytest_request.property_path == "data.status"
        assert pytest_request.value == "completed"
    
    def test_update_property_request_complex_value(self):
        """Test UpdatePropertyRequest with complex value"""
        complex_value = {"nested": {"data": [1, 2, 3]}}
        request = UpdatePropertyRequest(
            task_id="task-123",
            property_path="data.config",
            value=complex_value
        )
        
        assert pytest_request.value == complex_value


class TestMergeContextRequest:
    """Test suite for MergeContextRequest DTO"""
    
    def test_merge_context_request_creation(self):
        """Test creating a MergeContextRequest instance"""
        merge_data = {
            "status": "completed",
            "metrics": {"performance": 95, "coverage": 80}
        }
        request = MergeContextRequest(
            task_id="task-123",
            data=merge_data
        )
        
        assert pytest_request.task_id == "task-123"
        assert pytest_request.data == merge_data


class TestMergeDataRequest:
    """Test suite for MergeDataRequest DTO"""
    
    def test_merge_data_request_creation(self):
        """Test creating a MergeDataRequest instance"""
        merge_data = {"updates": {"field1": "value1"}}
        request = MergeDataRequest(
            task_id="task-123",
            data=merge_data
        )
        
        assert pytest_request.task_id == "task-123"
        assert pytest_request.data == merge_data
    
    def test_merge_data_request_is_dataclass(self):
        """Test that MergeDataRequest is a proper dataclass"""
        assert is_dataclass(MergeDataRequest)
        field_names = {f.name for f in fields(MergeDataRequest)}
        assert field_names == {'task_id', 'data'}


class TestAddInsightRequest:
    """Test suite for AddInsightRequest DTO"""
    
    def test_add_insight_request_creation(self):
        """Test creating an AddInsightRequest instance"""
        request = AddInsightRequest(
            task_id="task-123",
            agent="debugger-agent",
            category="performance",
            content="Found memory leak in authentication module",
            importance="high"
        )
        
        assert pytest_request.task_id == "task-123"
        assert pytest_request.agent == "debugger-agent"
        assert pytest_request.category == "performance"
        assert pytest_request.content == "Found memory leak in authentication module"
        assert pytest_request.importance == "high"
    
    def test_add_insight_request_default_importance(self):
        """Test AddInsightRequest with default importance"""
        request = AddInsightRequest(
            task_id="task-123",
            agent="coding-agent",
            category="technical",
            content="Refactored database queries"
        )
        
        assert pytest_request.importance == "medium"


class TestAddProgressRequest:
    """Test suite for AddProgressRequest DTO"""
    
    def test_add_progress_request_creation(self):
        """Test creating an AddProgressRequest instance"""
        request = AddProgressRequest(
            task_id="task-123",
            action="update_code",
            agent="coding-agent",
            details="Implemented JWT authentication",
            status="completed"
        )
        
        assert pytest_request.task_id == "task-123"
        assert pytest_request.action == "update_code"
        assert pytest_request.agent == "coding-agent"
        assert pytest_request.details == "Implemented JWT authentication"
        assert pytest_request.status == "completed"
    
    def test_add_progress_request_defaults(self):
        """Test AddProgressRequest with default values"""
        request = AddProgressRequest(
            task_id="task-123",
            action="analyze",
            agent="debugger-agent"
        )
        
        assert pytest_request.details == ""
        assert pytest_request.status == "completed"


class TestUpdateNextStepsRequest:
    """Test suite for UpdateNextStepsRequest DTO"""
    
    def test_update_next_steps_request_creation(self):
        """Test creating an UpdateNextStepsRequest instance"""
        next_steps = [
            "Write unit tests",
            "Update documentation",
            "Deploy to staging"
        ]
        request = UpdateNextStepsRequest(
            task_id="task-123",
            next_steps=next_steps
        )
        
        assert pytest_request.task_id == "task-123"
        assert pytest_request.next_steps == next_steps
    
    def test_update_next_steps_request_empty_list(self):
        """Test UpdateNextStepsRequest with empty list"""
        request = UpdateNextStepsRequest(
            task_id="task-123",
            next_steps=[]
        )
        
        assert pytest_request.task_id == "task-123"
        assert pytest_request.next_steps == []


class TestDTORelationships:
    """Test suite for verifying DTO relationships and patterns"""
    
    def test_all_dtos_follow_task_relationship_chain(self):
        """Test that all DTOs follow the clean relationship chain via task_id"""
        dto_classes = [
            CreateContextRequest, UpdateContextRequest, GetContextRequest,
            DeleteContextRequest, GetPropertyRequest, UpdatePropertyRequest,
            MergeContextRequest, MergeDataRequest, AddInsightRequest,
            AddProgressRequest, UpdateNextStepsRequest
        ]
        
        for dto_class in dto_classes:
            field_names = {f.name for f in fields(dto_class)}
            assert 'task_id' in field_names, f"{dto_class.__name__} must have task_id field"
    
    def test_dto_documentation(self):
        """Test that all DTOs have proper documentation"""
        dto_classes = [
            CreateContextRequest, UpdateContextRequest, GetContextRequest,
            DeleteContextRequest, ListContextsRequest, GetPropertyRequest,
            UpdatePropertyRequest, MergeContextRequest, MergeDataRequest,
            AddInsightRequest, AddProgressRequest, UpdateNextStepsRequest
        ]
        
        for dto_class in dto_classes:
            assert dto_class.__doc__ is not None
            assert "clean relationship chain" in dto_class.__doc__.lower()