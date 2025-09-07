"""Tests for UnifiedContextService"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import uuid

from fastmcp.task_management.application.services.unified_context_service import UnifiedContextService
from fastmcp.task_management.domain.value_objects.context_enums import ContextLevel
from fastmcp.task_management.domain.entities.context import GlobalContext, ProjectContext, BranchContext, TaskContextUnified as TaskContext


class TestUnifiedContextService:
    """Test cases for UnifiedContextService"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_global_repo = Mock()
        self.mock_project_repo = Mock()
        self.mock_branch_repo = Mock()
        self.mock_task_repo = Mock()
        self.mock_cache_service = Mock()
        self.mock_inheritance_service = Mock()
        self.mock_delegation_service = Mock()
        self.mock_validation_service = Mock()
        
        self.user_id = "user-123"
        
        self.service = UnifiedContextService(
            global_context_repository=self.mock_global_repo,
            project_context_repository=self.mock_project_repo,
            branch_context_repository=self.mock_branch_repo,
            task_context_repository=self.mock_task_repo,
            cache_service=self.mock_cache_service,
            inheritance_service=self.mock_inheritance_service,
            delegation_service=self.mock_delegation_service,
            validation_service=self.mock_validation_service,
            user_id=self.user_id
        )

    def test_init(self):
        """Test service initialization"""
        assert self.service._user_id == self.user_id
        assert self.service.repositories[ContextLevel.GLOBAL] == self.mock_global_repo
        assert self.service.repositories[ContextLevel.PROJECT] == self.mock_project_repo
        assert self.service.repositories[ContextLevel.BRANCH] == self.mock_branch_repo
        assert self.service.repositories[ContextLevel.TASK] == self.mock_task_repo

    def test_init_with_defaults(self):
        """Test initialization with default services"""
        service = UnifiedContextService(
            global_context_repository=self.mock_global_repo,
            project_context_repository=self.mock_project_repo,
            branch_context_repository=self.mock_branch_repo,
            task_context_repository=self.mock_task_repo
        )
        
        assert service.cache_service is not None
        assert service.inheritance_service is not None
        assert service.delegation_service is not None
        assert service.validation_service is not None
        assert service.hierarchy_validator is not None

    def test_with_user(self):
        """Test creating user-scoped service"""
        new_user_id = "new-user-456"
        
        # Mock with_user method on repositories
        self.mock_global_repo.with_user.return_value = Mock()
        self.mock_project_repo.with_user.return_value = Mock()
        self.mock_branch_repo.with_user.return_value = Mock()
        self.mock_task_repo.with_user.return_value = Mock()
        
        new_service = self.service.with_user(new_user_id)
        
        assert isinstance(new_service, UnifiedContextService)
        assert new_service._user_id == new_user_id

    def test_get_user_scoped_repository_with_user_method(self):
        """Test getting user-scoped repository when repository has with_user method"""
        mock_repo = Mock()
        mock_scoped_repo = Mock()
        mock_repo.with_user.return_value = mock_scoped_repo
        
        result = self.service._get_user_scoped_repository(mock_repo)
        
        mock_repo.with_user.assert_called_once_with(self.user_id)
        assert result == mock_scoped_repo

    def test_get_user_scoped_repository_without_user_method(self):
        """Test fallback when repository doesn't have with_user method"""
        mock_repo = Mock()
        del mock_repo.with_user
        
        result = self.service._get_user_scoped_repository(mock_repo)
        
        assert result == mock_repo

    def test_normalize_context_id_global_singleton(self):
        """Test normalization of global_singleton to proper UUID"""
        with patch('fastmcp.task_management.application.services.unified_context_service.GLOBAL_SINGLETON_UUID', 'uuid-123'):
            result = self.service._normalize_context_id("global", "global_singleton")
            assert result == 'uuid-123'

    def test_normalize_context_id_other_levels(self):
        """Test that other levels pass through unchanged"""
        result = self.service._normalize_context_id("project", "project-456")
        assert result == "project-456"

    def test_create_context_global_success(self):
        """Test successful global context creation"""
        context_id = "global-123"
        data = {
            "organization_name": "Test Org",
            "global_settings": {"timezone": "UTC"}
        }
        
        # Mock validation
        self.mock_validation_service.validate_context_data.return_value = {"valid": True}
        
        # Mock repository
        mock_saved_context = GlobalContext(
            id=context_id,
            organization_name="Test Org",
            global_settings={"timezone": "UTC"},
            metadata={}
        )
        self.mock_global_repo.create.return_value = mock_saved_context
        
        result = self.service.create_context("global", context_id, data)
        
        assert result["success"] is True
        assert result["level"] == "global"
        assert result["context_id"] == context_id
        self.mock_validation_service.validate_context_data.assert_called_once()
        self.mock_global_repo.create.assert_called_once()

    def test_create_context_validation_failure(self):
        """Test context creation with validation failure"""
        context_id = "project-123"
        data = {"project_name": "Test Project"}
        
        # Mock validation failure
        self.mock_validation_service.validate_context_data.return_value = {
            "valid": False,
            "errors": ["Missing required field"]
        }
        
        result = self.service.create_context("project", context_id, data)
        
        assert result["success"] is False
        assert "Validation failed" in result["error"]

    def test_create_context_unknown_level(self):
        """Test context creation with unknown level"""
        result = self.service.create_context("unknown", "id-123", {})
        
        assert result["success"] is False
        assert "error" in result

    def test_get_context_success(self):
        """Test successful context retrieval"""
        level = "project"
        context_id = "project-123"
        
        # Mock entity
        mock_context = ProjectContext(
            id=context_id,
            project_name="Test Project",
            project_settings={},
            metadata={}
        )
        
        self.mock_project_repo.get.return_value = mock_context
        
        result = self.service.get_context(level, context_id)
        
        assert result["success"] is True
        assert result["level"] == level
        assert result["context_id"] == context_id
        assert "context" in result
        self.mock_project_repo.get.assert_called_once_with(context_id)

    def test_get_context_not_found(self):
        """Test context retrieval when context doesn't exist"""
        level = "project"
        context_id = "nonexistent-123"
        
        self.mock_project_repo.get.return_value = None
        
        result = self.service.get_context(level, context_id)
        
        assert result["success"] is False
        assert "Context not found" in result["error"]

    def test_get_context_empty_context_id(self):
        """Test context retrieval with empty context_id"""
        result = self.service.get_context("project", "")
        
        assert result["success"] is False
        assert "Context ID is required" in result["error"]

    def test_get_context_with_inheritance(self):
        """Test context retrieval with inheritance resolution"""
        level = "task"
        context_id = "task-123"
        
        # Mock entity
        mock_context = TaskContext(
            id=context_id,
            branch_id="branch-456",
            task_data={},
            progress=0,
            insights=[],
            next_steps=[],
            metadata={}
        )
        
        self.mock_task_repo.get.return_value = mock_context
        
        # Mock inheritance resolution
        with patch.object(self.service, '_resolve_inheritance_sync') as mock_resolve:
            mock_resolved_data = {"resolved": True, "task_data": {}}
            mock_resolve.return_value = mock_resolved_data
            
            result = self.service.get_context(level, context_id, include_inherited=True)
            
            assert result["success"] is True
            assert result["inherited"] is True
            mock_resolve.assert_called_once()

    def test_update_context_success(self):
        """Test successful context update"""
        level = "project"
        context_id = "project-123"
        update_data = {"project_name": "Updated Project"}
        
        # Mock existing context
        existing_context = ProjectContext(
            id=context_id,
            project_name="Original Project",
            project_settings={},
            metadata={}
        )
        self.mock_project_repo.get.return_value = existing_context
        
        # Mock updated context
        updated_context = ProjectContext(
            id=context_id,
            project_name="Updated Project",
            project_settings={},
            metadata={}
        )
        self.mock_project_repo.update.return_value = updated_context
        
        result = self.service.update_context(level, context_id, update_data)
        
        assert result["success"] is True
        assert result["level"] == level
        assert result["context_id"] == context_id
        self.mock_project_repo.update.assert_called_once()

    def test_update_context_not_found(self):
        """Test context update when context doesn't exist"""
        level = "project"
        context_id = "nonexistent-123"
        
        self.mock_project_repo.get.return_value = None
        
        result = self.service.update_context(level, context_id, {})
        
        assert result["success"] is False
        assert "Context not found" in result["error"]

    def test_delete_context_success(self):
        """Test successful context deletion"""
        level = "project"
        context_id = "project-123"
        
        # Mock existing context
        mock_context = ProjectContext(
            id=context_id,
            project_name="Test Project",
            project_settings={},
            metadata={}
        )
        self.mock_project_repo.get.return_value = mock_context
        self.mock_project_repo.delete.return_value = True
        
        result = self.service.delete_context(level, context_id)
        
        assert result["success"] is True
        assert result["level"] == level
        assert result["context_id"] == context_id
        self.mock_project_repo.delete.assert_called_once_with(context_id)

    def test_delete_context_not_found(self):
        """Test context deletion when context doesn't exist"""
        level = "project"
        context_id = "nonexistent-123"
        
        self.mock_project_repo.get.return_value = None
        
        result = self.service.delete_context(level, context_id)
        
        assert result["success"] is False
        assert "Context not found" in result["error"]

    def test_resolve_context(self):
        """Test context resolution with inheritance"""
        level = "task"
        context_id = "task-123"
        
        with patch.object(self.service, 'get_context') as mock_get:
            mock_get.return_value = {
                "success": True,
                "context": {"id": context_id},
                "level": level,
                "context_id": context_id
            }
            
            result = self.service.resolve_context(level, context_id)
            
            assert result["success"] is True
            assert result["resolved"] is True
            assert result["inheritance_applied"] is True
            mock_get.assert_called_once_with(
                level=level,
                context_id=context_id,
                include_inherited=True,
                force_refresh=False
            )

    def test_list_contexts_success(self):
        """Test successful context listing"""
        level = "project"
        filters = {"active": True}
        
        # Mock contexts
        mock_contexts = [
            ProjectContext(id="proj-1", project_name="Project 1", project_settings={}, metadata={}),
            ProjectContext(id="proj-2", project_name="Project 2", project_settings={}, metadata={})
        ]
        self.mock_project_repo.list.return_value = mock_contexts
        
        result = self.service.list_contexts(level, filters)
        
        assert result["success"] is True
        assert result["level"] == level
        assert result["count"] == 2
        assert len(result["contexts"]) == 2
        self.mock_project_repo.list.assert_called_once_with(filters=filters)

    def test_list_contexts_no_repository(self):
        """Test context listing with no repository configured"""
        # Create service without project repository
        service = UnifiedContextService(
            global_context_repository=self.mock_global_repo,
            project_context_repository=None,
            branch_context_repository=self.mock_branch_repo,
            task_context_repository=self.mock_task_repo
        )
        
        result = service.list_contexts("project")
        
        assert result["success"] is False
        assert "No repository configured" in result["error"]

    def test_add_insight(self):
        """Test adding insight to context"""
        level = "task"
        context_id = "task-123"
        content = "Important insight"
        
        # Mock existing context
        existing_context = {"insights": []}
        
        with patch.object(self.service, 'get_context') as mock_get, \
             patch.object(self.service, 'update_context') as mock_update:
            
            mock_get.return_value = {"success": True, "context": existing_context}
            mock_update.return_value = {"success": True}
            
            result = self.service.add_insight(level, context_id, content)
            
            assert result["success"] is True
            
            # Verify update was called with insights
            update_call_args = mock_update.call_args[1]
            insights = update_call_args["data"]["insights"]
            assert len(insights) == 1
            assert insights[0]["content"] == content

    def test_add_insight_context_not_found(self):
        """Test adding insight when context doesn't exist"""
        level = "task"
        context_id = "nonexistent-123"
        
        with patch.object(self.service, 'get_context') as mock_get:
            mock_get.return_value = {"success": False, "error": "Context not found"}
            
            result = self.service.add_insight(level, context_id, "insight")
            
            assert result["success"] is False
            assert "Context not found" in result["error"]

    def test_add_progress(self):
        """Test adding progress update to context"""
        level = "task"
        context_id = "task-123"
        content = "Made progress on feature"
        
        # Mock existing context
        existing_context = {"progress_updates": []}
        
        with patch.object(self.service, 'get_context') as mock_get, \
             patch.object(self.service, 'update_context') as mock_update:
            
            mock_get.return_value = {"success": True, "context": existing_context}
            mock_update.return_value = {"success": True}
            
            result = self.service.add_progress(level, context_id, content)
            
            assert result["success"] is True
            
            # Verify update was called with progress_updates
            update_call_args = mock_update.call_args[1]
            progress_updates = update_call_args["data"]["progress_updates"]
            assert len(progress_updates) == 1
            assert progress_updates[0]["content"] == content

    def test_create_context_entity_global(self):
        """Test creating global context entity"""
        context_id = "global-123"
        data = {
            "organization_name": "Test Org",
            "global_settings": {"timezone": "UTC"},
            "metadata": {"created": True}
        }
        
        entity = self.service._create_context_entity(
            ContextLevel.GLOBAL, context_id, data
        )
        
        assert isinstance(entity, GlobalContext)
        assert entity.id == context_id
        assert entity.organization_name == "Test Org"
        assert entity.global_settings == {"timezone": "UTC"}

    def test_create_context_entity_project(self):
        """Test creating project context entity"""
        context_id = "project-123"
        data = {
            "project_name": "Test Project",
            "project_settings": {"default_branch": "main"},
            "metadata": {"created": True}
        }
        
        entity = self.service._create_context_entity(
            ContextLevel.PROJECT, context_id, data
        )
        
        assert isinstance(entity, ProjectContext)
        assert entity.id == context_id
        assert entity.project_name == "Test Project"

    def test_create_context_entity_branch(self):
        """Test creating branch context entity"""
        context_id = "branch-123"
        project_id = "project-456"
        data = {
            "project_id": project_id,
            "git_branch_name": "feature/test",
            "branch_settings": {"workflow": "gitflow"},
            "metadata": {"created": True}
        }
        
        entity = self.service._create_context_entity(
            ContextLevel.BRANCH, context_id, data, project_id=project_id
        )
        
        assert isinstance(entity, BranchContext)
        assert entity.id == context_id
        assert entity.project_id == project_id
        assert entity.git_branch_name == "feature/test"

    def test_create_context_entity_task(self):
        """Test creating task context entity"""
        context_id = "task-123"
        data = {
            "branch_id": "branch-456",
            "task_data": {"title": "Test Task"},
            "progress": 50,
            "insights": [],
            "next_steps": [],
            "metadata": {"created": True}
        }
        
        entity = self.service._create_context_entity(
            ContextLevel.TASK, context_id, data
        )
        
        assert isinstance(entity, TaskContext)
        assert entity.id == context_id
        assert entity.branch_id == "branch-456"
        assert entity.task_data == {"title": "Test Task"}

    def test_create_context_entity_task_missing_branch_id(self):
        """Test creating task context entity without branch_id"""
        context_id = "task-123"
        data = {"task_data": {"title": "Test Task"}}
        
        with pytest.raises(ValueError, match="Task context requires branch_id"):
            self.service._create_context_entity(ContextLevel.TASK, context_id, data)

    def test_entity_to_dict_with_dict_method(self):
        """Test converting entity to dict when entity has dict method"""
        mock_entity = Mock()
        mock_entity.dict.return_value = {"id": "test", "name": "Test Entity"}
        
        result = self.service._entity_to_dict(mock_entity)
        
        assert result == {"id": "test", "name": "Test Entity"}
        mock_entity.dict.assert_called_once()

    def test_entity_to_dict_with_vars(self):
        """Test converting entity to dict using vars fallback"""
        mock_entity = Mock()
        # Remove dict method
        del mock_entity.dict
        
        # Mock vars behavior
        with patch('builtins.vars') as mock_vars:
            mock_vars.return_value = {"id": "test", "name": "Test Entity"}
            
            result = self.service._entity_to_dict(mock_entity)
            
            assert result == {"id": "test", "name": "Test Entity"}

    def test_merge_context_data_nested_dicts(self):
        """Test merging context data with nested dictionaries"""
        existing_data = {
            "settings": {"theme": "dark", "lang": "en"},
            "metadata": {"created": "2023-01-01"}
        }
        new_data = {
            "settings": {"theme": "light"},
            "metadata": {"updated": "2023-12-31"}
        }
        
        result = self.service._merge_context_data(existing_data, new_data)
        
        assert result["settings"]["theme"] == "light"  # Overwritten
        assert result["settings"]["lang"] == "en"  # Preserved
        assert result["metadata"]["created"] == "2023-01-01"  # Preserved
        assert result["metadata"]["updated"] == "2023-12-31"  # Added
        assert "updated_at" in result  # Timestamp added

    def test_merge_context_data_list_extension(self):
        """Test merging context data with list extension"""
        existing_data = {"tags": ["tag1", "tag2"]}
        new_data = {"tags": ["tag3", "tag4"]}
        
        result = self.service._merge_context_data(existing_data, new_data)
        
        assert result["tags"] == ["tag1", "tag2", "tag3", "tag4"]

    def test_merge_context_data_special_list_fields(self):
        """Test merging context data with special list fields that get replaced"""
        existing_data = {"insights": ["insight1"], "tags": ["tag1"]}
        new_data = {"insights": ["insight2"], "tags": ["tag2"]}
        
        result = self.service._merge_context_data(existing_data, new_data)
        
        assert result["insights"] == ["insight2"]  # Replaced (special field)
        assert result["tags"] == ["tag1", "tag2"]  # Extended (normal field)

    def test_auto_create_context_if_missing_exists(self):
        """Test auto-creation when context already exists"""
        level = "project"
        context_id = "project-123"
        
        with patch.object(self.service, 'get_context') as mock_get:
            mock_get.return_value = {
                "success": True,
                "context": {"id": context_id}
            }
            
            result = self.service.auto_create_context_if_missing(level, context_id)
            
            assert result["success"] is True
            assert result["created"] is False
            mock_get.assert_called_once()

    def test_auto_create_context_if_missing_creates(self):
        """Test auto-creation when context doesn't exist"""
        level = "project"
        context_id = "project-123"
        
        with patch.object(self.service, 'get_context') as mock_get, \
             patch.object(self.service, 'create_context') as mock_create:
            
            mock_get.return_value = {"success": False}
            mock_create.return_value = {"success": True, "context": {"id": context_id}}
            
            result = self.service.auto_create_context_if_missing(level, context_id)
            
            assert result["success"] is True
            assert result["created"] is True
            mock_create.assert_called_once()

    def test_build_default_context_data_global(self):
        """Test building default data for global context"""
        result = self.service._build_default_context_data("global", "global-123")
        
        assert "organization_name" in result
        assert "global_settings" in result
        assert "metadata" in result
        assert result["metadata"]["auto_created"] is True

    def test_build_default_context_data_project(self):
        """Test building default data for project context"""
        result = self.service._build_default_context_data("project", "project-123")
        
        assert "project_name" in result
        assert "project_settings" in result
        assert "metadata" in result
        assert result["metadata"]["auto_created"] is True

    def test_build_default_context_data_with_existing_data(self):
        """Test building default data with existing data provided"""
        existing_data = {"project_name": "Custom Project"}
        
        result = self.service._build_default_context_data(
            "project", "project-123", data=existing_data
        )
        
        assert result["project_name"] == "Custom Project"
        assert "project_settings" in result
        assert result["metadata"]["auto_created"] is True

    def test_exception_handling_in_create_context(self):
        """Test exception handling during context creation"""
        context_id = "test-123"
        data = {"test": "data"}
        
        # Mock repository to raise exception
        self.mock_global_repo.create.side_effect = Exception("Database error")
        
        result = self.service.create_context("global", context_id, data)
        
        assert result["success"] is False
        assert "error" in result

    def test_exception_handling_in_get_context(self):
        """Test exception handling during context retrieval"""
        # Mock repository to raise exception
        self.mock_project_repo.get.side_effect = Exception("Database error")
        
        result = self.service.get_context("project", "project-123")
        
        assert result["success"] is False
        assert "error" in result

    def test_delegate_context_basic(self):
        """Test basic context delegation (currently returns success/skipped)"""
        result = self.service.delegate_context(
            level="task",
            context_id="task-123",
            delegate_to="branch",
            data={"pattern": "auth_flow"},
            delegation_reason="Reusable pattern"
        )
        
        assert result["success"] is True
        assert result["source_level"] == "task"
        assert result["target_level"] == "branch"