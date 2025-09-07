"""Tests for UnifiedContextService"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from uuid import UUID
import uuid
from decimal import Decimal

from fastmcp.task_management.application.services.unified_context_service import UnifiedContextService
from fastmcp.task_management.domain.entities.context import GlobalContext, ProjectContext, BranchContext
from fastmcp.task_management.domain.value_objects.context_enums import ContextLevel
from fastmcp.task_management.domain.exceptions.base_exceptions import ValidationException


class TestUnifiedContextService:
    """Test suite for UnifiedContextService"""

    @pytest.fixture
    def mock_repositories(self):
        """Create mock repositories"""
        global_repo = Mock()
        project_repo = Mock()
        branch_repo = Mock()
        task_repo = Mock()
        
        # Make repositories return successful results by default
        global_repo.create.return_value = Mock(id="global-123", global_settings={})
        project_repo.create.return_value = Mock(id="project-123", project_settings={})
        branch_repo.create.return_value = Mock(id="branch-123", branch_data={})
        task_repo.create.return_value = Mock(id="task-123", task_data={})
        
        return {
            ContextLevel.GLOBAL: global_repo,
            ContextLevel.PROJECT: project_repo,
            ContextLevel.BRANCH: branch_repo,
            ContextLevel.TASK: task_repo
        }
    
    @pytest.fixture
    def mock_services(self):
        """Create mock services"""
        return {
            "cache": Mock(),
            "inheritance": Mock(),
            "delegation": Mock(),
            "validation": Mock()
        }
    
    @pytest.fixture
    def service(self, mock_repositories, mock_services):
        """Create UnifiedContextService with mocked dependencies"""
        return UnifiedContextService(
            global_context_repository=mock_repositories[ContextLevel.GLOBAL],
            project_context_repository=mock_repositories[ContextLevel.PROJECT],
            branch_context_repository=mock_repositories[ContextLevel.BRANCH],
            task_context_repository=mock_repositories[ContextLevel.TASK],
            cache_service=mock_services["cache"],
            inheritance_service=mock_services["inheritance"],
            delegation_service=mock_services["delegation"],
            validation_service=mock_services["validation"],
            user_id="test-user"
        )
    
    def test_service_initialization(self, mock_repositories, mock_services):
        """Test service initializes correctly with all dependencies"""
        service = UnifiedContextService(
            global_context_repository=mock_repositories[ContextLevel.GLOBAL],
            project_context_repository=mock_repositories[ContextLevel.PROJECT],
            branch_context_repository=mock_repositories[ContextLevel.BRANCH],
            task_context_repository=mock_repositories[ContextLevel.TASK],
            cache_service=mock_services["cache"],
            inheritance_service=mock_services["inheritance"],
            delegation_service=mock_services["delegation"],
            validation_service=mock_services["validation"],
            user_id="test-user"
        )
        
        assert service._user_id == "test-user"
        assert service.repositories == mock_repositories
        assert service.cache_service == mock_services["cache"]
        assert service.inheritance_service == mock_services["inheritance"]
        assert service.delegation_service == mock_services["delegation"]
        assert service.validation_service == mock_services["validation"]
    
    def test_service_initialization_without_optional_services(self, mock_repositories):
        """Test service creates default services when not provided"""
        service = UnifiedContextService(
            global_context_repository=mock_repositories[ContextLevel.GLOBAL],
            project_context_repository=mock_repositories[ContextLevel.PROJECT],
            branch_context_repository=mock_repositories[ContextLevel.BRANCH],
            task_context_repository=mock_repositories[ContextLevel.TASK]
        )
        
        assert service.cache_service is not None
        assert service.inheritance_service is not None
        assert service.delegation_service is not None
        assert service.validation_service is not None
    
    def test_with_user_creates_scoped_instance(self, service, mock_repositories):
        """Test with_user creates new scoped instance"""
        # Setup repository mocks to support with_user
        for repo in mock_repositories.values():
            scoped_repo = Mock()
            repo.with_user.return_value = scoped_repo
        
        new_user_id = "new-user-123"
        scoped_service = service.with_user(new_user_id)
        
        # Verify it's a new instance
        assert scoped_service is not service
        assert scoped_service._user_id == new_user_id
        
        # Verify repositories were scoped
        for repo in mock_repositories.values():
            repo.with_user.assert_called_once_with(new_user_id)
    
    def test_get_user_scoped_repository_with_user(self, service):
        """Test _get_user_scoped_repository returns scoped repo when user_id exists"""
        mock_repo = Mock()
        scoped_repo = Mock()
        mock_repo.with_user.return_value = scoped_repo
        
        result = service._get_user_scoped_repository(mock_repo)
        
        assert result == scoped_repo
        mock_repo.with_user.assert_called_once_with("test-user")
    
    def test_get_user_scoped_repository_without_user(self, service):
        """Test _get_user_scoped_repository returns original repo when no user_id"""
        service._user_id = None
        mock_repo = Mock()
        
        result = service._get_user_scoped_repository(mock_repo)
        
        assert result == mock_repo
        mock_repo.with_user.assert_not_called()
    
    def test_get_user_scoped_repository_no_with_user_method(self, service):
        """Test _get_user_scoped_repository handles repos without with_user method"""
        mock_repo = Mock(spec=[])  # No with_user method
        
        result = service._get_user_scoped_repository(mock_repo)
        
        assert result == mock_repo
    
    def test_serialize_for_json_with_uuid(self, service):
        """Test JSON serialization of UUID objects"""
        test_uuid = UUID('12345678-1234-5678-1234-567812345678')
        result = service._serialize_for_json(test_uuid)
        
        assert result == str(test_uuid)
    
    def test_serialize_for_json_with_datetime(self, service):
        """Test JSON serialization of datetime objects"""
        test_dt = datetime(2025, 1, 27, 12, 0, 0, tzinfo=timezone.utc)
        result = service._serialize_for_json(test_dt)
        
        assert result == str(test_dt)
    
    def test_serialize_for_json_with_decimal(self, service):
        """Test JSON serialization of Decimal objects"""
        test_decimal = Decimal("123.45")
        result = service._serialize_for_json(test_decimal)
        
        assert result == 123.45
        assert isinstance(result, float)
    
    def test_serialize_for_json_with_dict(self, service):
        """Test JSON serialization of dictionaries with mixed types"""
        test_dict = {
            "uuid": UUID('12345678-1234-5678-1234-567812345678'),
            "datetime": datetime(2025, 1, 27, 12, 0, 0, tzinfo=timezone.utc),
            "decimal": Decimal("123.45"),
            "string": "test",
            "number": 42,
            "nested": {
                "uuid": UUID('87654321-4321-8765-4321-876543210987')
            }
        }
        
        result = service._serialize_for_json(test_dict)
        
        assert result["uuid"] == str(test_dict["uuid"])
        assert result["datetime"] == str(test_dict["datetime"])
        assert result["decimal"] == 123.45
        assert result["string"] == "test"
        assert result["number"] == 42
        assert result["nested"]["uuid"] == str(test_dict["nested"]["uuid"])
    
    def test_serialize_for_json_with_list(self, service):
        """Test JSON serialization of lists"""
        test_list = [
            UUID('12345678-1234-5678-1234-567812345678'),
            datetime(2025, 1, 27, 12, 0, 0, tzinfo=timezone.utc),
            "string",
            42
        ]
        
        result = service._serialize_for_json(test_list)
        
        assert len(result) == 4
        assert result[0] == str(test_list[0])
        assert result[1] == str(test_list[1])
        assert result[2] == "string"
        assert result[3] == 42
    
    def test_serialize_for_json_with_custom_object(self, service):
        """Test JSON serialization of custom objects"""
        class CustomObject:
            def __init__(self):
                self.uuid = UUID('12345678-1234-5678-1234-567812345678')
                self.name = "test"
        
        test_obj = CustomObject()
        result = service._serialize_for_json(test_obj)
        
        assert isinstance(result, dict)
        assert result["uuid"] == str(test_obj.uuid)
        assert result["name"] == "test"
    
    def test_create_context_basic(self, service, mock_repositories):
        """Test basic context creation"""
        # Mock hierarchy validator
        service.hierarchy_validator = Mock()
        service.hierarchy_validator.validate_parent_exists.return_value = True
        service.hierarchy_validator.auto_create_parent_hierarchy.return_value = True
        
        # Mock repository response
        mock_entity = Mock(
            id="task-123",
            task_data={"title": "Test Task"},
            branch_id="branch-456",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_repositories[ContextLevel.TASK].create.return_value = mock_entity
        
        result = service.create_context(
            level="task",
            context_id="task-123",
            data={"title": "Test Task"},
            project_id="project-456"
        )
        
        assert result["success"] is True
        assert "context" in result
        assert result["context"]["id"] == "task-123"
    
    def test_create_context_invalid_level(self, service):
        """Test create_context with invalid level"""
        result = service.create_context(
            level="invalid",
            context_id="test-123",
            data={}
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "invalid" in result["error"].lower()
    
    def test_create_context_with_auto_create_parents(self, service, mock_repositories):
        """Test create_context with auto-create parents enabled"""
        # Mock hierarchy validator
        service.hierarchy_validator = Mock()
        service.hierarchy_validator.validate_parent_exists.return_value = False
        service.hierarchy_validator.auto_create_parent_hierarchy.return_value = True
        
        mock_entity = Mock(
            id="task-123",
            task_data={"title": "Test Task"},
            branch_id="branch-456",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_repositories[ContextLevel.TASK].create.return_value = mock_entity
        
        result = service.create_context(
            level="task",
            context_id="task-123",
            data={"branch_id": "branch-456"},
            auto_create_parents=True
        )
        
        # Should call auto_create_parent_hierarchy
        service.hierarchy_validator.auto_create_parent_hierarchy.assert_called()
        assert result["success"] is True
    
    def test_create_context_without_auto_create_parents(self, service):
        """Test create_context fails when parent doesn't exist and auto-create disabled"""
        # Mock hierarchy validator
        service.hierarchy_validator = Mock()
        service.hierarchy_validator.validate_parent_exists.return_value = False
        
        result = service.create_context(
            level="task",
            context_id="task-123",
            data={"branch_id": "branch-456"},
            auto_create_parents=False
        )
        
        assert result["success"] is False
        assert "Parent context does not exist" in result["error"]
    
    def test_create_context_repository_exception(self, service, mock_repositories):
        """Test create_context handles repository exceptions"""
        service.hierarchy_validator = Mock()
        service.hierarchy_validator.validate_parent_exists.return_value = True
        
        mock_repositories[ContextLevel.TASK].create.side_effect = Exception("Database error")
        
        result = service.create_context(
            level="task",
            context_id="task-123",
            data={}
        )
        
        assert result["success"] is False
        assert "Database error" in result["error"]
    
    def test_hierarchy_validator_initialization(self, mock_repositories):
        """Test hierarchy validator is properly initialized"""
        service = UnifiedContextService(
            global_context_repository=mock_repositories[ContextLevel.GLOBAL],
            project_context_repository=mock_repositories[ContextLevel.PROJECT],
            branch_context_repository=mock_repositories[ContextLevel.BRANCH],
            task_context_repository=mock_repositories[ContextLevel.TASK],
            user_id="test-user"
        )
        
        assert service.hierarchy_validator is not None
        assert hasattr(service.hierarchy_validator, 'validate_parent_exists')
        assert hasattr(service.hierarchy_validator, 'auto_create_parent_hierarchy')
    
    def test_create_context_with_validation_error(self, service):
        """Test create_context handles validation errors"""
        # Mock hierarchy validator to raise validation exception
        service.hierarchy_validator = Mock()
        service.hierarchy_validator.validate_parent_exists.side_effect = ValidationException("Invalid parent")
        
        result = service.create_context(
            level="task",
            context_id="task-123",
            data={}
        )
        
        assert result["success"] is False
        assert "Invalid parent" in result["error"]
    
    def test_create_context_with_user_id_override(self, service, mock_repositories):
        """Test create_context with user_id override parameter"""
        service.hierarchy_validator = Mock()
        service.hierarchy_validator.validate_parent_exists.return_value = True
        
        mock_entity = Mock(
            id="task-123",
            task_data={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_repositories[ContextLevel.TASK].create.return_value = mock_entity
        
        # Original user_id is "test-user"
        assert service._user_id == "test-user"
        
        result = service.create_context(
            level="task",
            context_id="task-123",
            data={},
            user_id="override-user"
        )
        
        assert result["success"] is True
        # User ID should be restored after operation
        assert service._user_id == "test-user"