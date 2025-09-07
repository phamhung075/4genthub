"""
Test cases for BranchContextRepository

Tests the repository for branch context operations in the unified context system.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timezone
from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, Dict, Any, List
import logging

from dhafnck_mcp_main.src.fastmcp.task_management.domain.entities.context import BranchContext
from dhafnck_mcp_main.src.fastmcp.task_management.infrastructure.database.models import BranchContext as BranchContextModel
from dhafnck_mcp_main.src.fastmcp.task_management.infrastructure.repositories.branch_context_repository import BranchContextRepository


class TestBranchContextRepository:
    """Test cases for BranchContextRepository"""

    def setup_method(self):
        """Set up test fixtures"""
        self.session_factory = Mock()
        self.session = Mock()
        self.session_factory.return_value = self.session
        self.user_id = "test-user-123"
        self.context_id = "branch-context-456"
        self.project_id = "project-789"

    def create_test_branch_context(self) -> BranchContext:
        """Create a test branch context entity"""
        return BranchContext(
            id=self.context_id,
            project_id=self.project_id,
            git_branch_name="feature/test-branch",
            branch_settings={
                "branch_workflow": {"steps": ["analyze", "implement", "test"]},
                "branch_standards": {"coding_style": "PEP8"},
                "agent_assignments": {"primary": "@coding_agent"},
                "custom_field": "custom_value"
            },
            metadata={
                "local_overrides": {"override1": "value1"},
                "delegation_rules": {"rule1": "delegate_up"},
                "user_id": self.user_id
            }
        )

    def create_test_db_model(self) -> BranchContextModel:
        """Create a test database model"""
        return BranchContextModel(
            id=self.context_id,
            branch_id=None,
            parent_project_id=self.project_id,
            data={
                "branch_workflow": {"steps": ["analyze", "implement", "test"]},
                "branch_standards": {"coding_style": "PEP8"},
                "agent_assignments": {"primary": "@coding_agent"}
            },
            branch_workflow={"steps": ["analyze", "implement", "test"]},
            feature_flags={},
            active_patterns={},
            local_overrides={"override1": "value1"},
            delegation_rules={"rule1": "delegate_up"},
            user_id=self.user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

    def test_init(self):
        """Test repository initialization"""
        repo = BranchContextRepository(self.session_factory, self.user_id)
        
        assert repo.session_factory == self.session_factory
        assert repo.user_id == self.user_id

    def test_init_without_user(self):
        """Test repository initialization without user ID"""
        repo = BranchContextRepository(self.session_factory)
        
        assert repo.session_factory == self.session_factory
        assert repo.user_id is None

    def test_with_user(self):
        """Test with_user method"""
        repo = BranchContextRepository(self.session_factory)
        new_repo = repo.with_user("new-user-456")
        
        assert isinstance(new_repo, BranchContextRepository)
        assert new_repo.session_factory == self.session_factory
        assert new_repo.user_id == "new-user-456"

    def test_get_db_session_existing_session(self):
        """Test get_db_session when session already exists"""
        repo = BranchContextRepository(self.session_factory, self.user_id)
        existing_session = Mock()
        repo._session = existing_session
        
        with repo.get_db_session() as session:
            assert session == existing_session

    def test_get_db_session_new_session_success(self):
        """Test get_db_session creating new session successfully"""
        repo = BranchContextRepository(self.session_factory, self.user_id)
        repo._session = None
        
        with repo.get_db_session() as session:
            assert session == self.session
        
        self.session.commit.assert_called_once()
        self.session.close.assert_called_once()

    def test_get_db_session_new_session_error(self):
        """Test get_db_session with database error"""
        repo = BranchContextRepository(self.session_factory, self.user_id)
        repo._session = None
        self.session.commit.side_effect = SQLAlchemyError("Database error")
        
        with pytest.raises(SQLAlchemyError):
            with repo.get_db_session() as session:
                pass
        
        self.session.rollback.assert_called_once()
        self.session.close.assert_called_once()

    def test_create_success(self):
        """Test successful branch context creation"""
        repo = BranchContextRepository(self.session_factory, self.user_id)
        repo._session = None
        entity = self.create_test_branch_context()
        
        # Mock query for existing check
        query_mock = Mock()
        filter_mock = Mock()
        query_mock.filter.return_value = filter_mock
        filter_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = None
        self.session.query.return_value = query_mock
        
        # Mock the created model
        created_model = self.create_test_db_model()
        
        with patch.object(repo, '_to_entity') as mock_to_entity:
            mock_to_entity.return_value = entity
            result = repo.create(entity)
        
        # Verify queries
        self.session.query.assert_called_once_with(BranchContextModel)
        query_mock.filter.assert_called_once()
        filter_mock.filter.assert_called_once()
        
        # Verify model creation
        self.session.add.assert_called_once()
        self.session.flush.assert_called_once()
        mock_to_entity.assert_called_once()
        
        assert result == entity

    def test_create_already_exists(self):
        """Test branch context creation when already exists"""
        repo = BranchContextRepository(self.session_factory, self.user_id)
        repo._session = None
        entity = self.create_test_branch_context()
        
        # Mock existing entity
        existing_model = self.create_test_db_model()
        query_mock = Mock()
        filter_mock = Mock()
        query_mock.filter.return_value = filter_mock
        filter_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = existing_model
        self.session.query.return_value = query_mock
        
        with pytest.raises(ValueError) as exc_info:
            repo.create(entity)
        
        assert "Branch context already exists" in str(exc_info.value)
        assert self.context_id in str(exc_info.value)

    def test_create_without_user_id(self):
        """Test branch context creation without user ID"""
        repo = BranchContextRepository(self.session_factory)
        repo._session = None
        entity = self.create_test_branch_context()
        
        # Mock query for existing check (no user filter applied)
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = None
        self.session.query.return_value = query_mock
        
        with patch.object(repo, '_to_entity') as mock_to_entity:
            mock_to_entity.return_value = entity
            result = repo.create(entity)
        
        # Verify only one filter call (for ID, not for user_id)
        query_mock.filter.assert_called_once()
        assert result == entity

    def test_get_success(self):
        """Test successful branch context retrieval"""
        repo = BranchContextRepository(self.session_factory, self.user_id)
        repo._session = None
        db_model = self.create_test_db_model()
        entity = self.create_test_branch_context()
        
        # Mock query
        query_mock = Mock()
        filter_mock = Mock()
        query_mock.filter.return_value = filter_mock
        filter_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = db_model
        self.session.query.return_value = query_mock
        
        with patch.object(repo, '_to_entity') as mock_to_entity:
            mock_to_entity.return_value = entity
            result = repo.get(self.context_id)
        
        # Verify queries
        self.session.query.assert_called_once_with(BranchContextModel)
        query_mock.filter.assert_called_once()
        filter_mock.filter.assert_called_once()
        
        mock_to_entity.assert_called_once_with(db_model)
        assert result == entity

    def test_get_not_found(self):
        """Test branch context retrieval when not found"""
        repo = BranchContextRepository(self.session_factory, self.user_id)
        repo._session = None
        
        # Mock query returning None
        query_mock = Mock()
        filter_mock = Mock()
        query_mock.filter.return_value = filter_mock
        filter_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = None
        self.session.query.return_value = query_mock
        
        result = repo.get(self.context_id)
        
        assert result is None

    def test_get_without_user_id(self):
        """Test branch context retrieval without user ID"""
        repo = BranchContextRepository(self.session_factory)
        repo._session = None
        db_model = self.create_test_db_model()
        entity = self.create_test_branch_context()
        
        # Mock query (no user filter applied)
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = db_model
        self.session.query.return_value = query_mock
        
        with patch.object(repo, '_to_entity') as mock_to_entity:
            mock_to_entity.return_value = entity
            result = repo.get(self.context_id)
        
        # Verify only one filter call (for ID, not for user_id)
        query_mock.filter.assert_called_once()
        assert result == entity

    def test_update_success(self):
        """Test successful branch context update"""
        repo = BranchContextRepository(self.session_factory, self.user_id)
        repo._session = None
        entity = self.create_test_branch_context()
        db_model = self.create_test_db_model()
        
        # Mock session.get
        self.session.get.return_value = db_model
        
        with patch.object(repo, '_to_entity') as mock_to_entity:
            mock_to_entity.return_value = entity
            result = repo.update(self.context_id, entity)
        
        # Verify model update
        self.session.get.assert_called_once_with(BranchContextModel, self.context_id)
        self.session.flush.assert_called_once()
        assert db_model.parent_project_id == entity.project_id
        assert db_model.user_id == self.user_id
        
        mock_to_entity.assert_called_once_with(db_model)
        assert result == entity

    def test_update_not_found(self):
        """Test branch context update when not found"""
        repo = BranchContextRepository(self.session_factory, self.user_id)
        repo._session = None
        entity = self.create_test_branch_context()
        
        # Mock session.get returning None
        self.session.get.return_value = None
        
        with pytest.raises(ValueError) as exc_info:
            repo.update(self.context_id, entity)
        
        assert "Branch context not found" in str(exc_info.value)
        assert self.context_id in str(exc_info.value)

    def test_delete_success(self):
        """Test successful branch context deletion"""
        repo = BranchContextRepository(self.session_factory, self.user_id)
        repo._session = None
        db_model = self.create_test_db_model()
        
        # Mock session.get
        self.session.get.return_value = db_model
        
        result = repo.delete(self.context_id)
        
        self.session.get.assert_called_once_with(BranchContextModel, self.context_id)
        self.session.delete.assert_called_once_with(db_model)
        assert result is True

    def test_delete_not_found(self):
        """Test branch context deletion when not found"""
        repo = BranchContextRepository(self.session_factory, self.user_id)
        repo._session = None
        
        # Mock session.get returning None
        self.session.get.return_value = None
        
        result = repo.delete(self.context_id)
        
        self.session.get.assert_called_once_with(BranchContextModel, self.context_id)
        self.session.delete.assert_not_called()
        assert result is False

    def test_list_no_filters(self):
        """Test listing branch contexts without filters"""
        repo = BranchContextRepository(self.session_factory, self.user_id)
        repo._session = None
        db_models = [self.create_test_db_model()]
        entities = [self.create_test_branch_context()]
        
        # Mock select and execute
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = db_models
        self.session.execute.return_value = mock_result
        
        with patch('dhafnck_mcp_main.src.fastmcp.task_management.infrastructure.repositories.branch_context_repository.select') as mock_select:
            mock_stmt = Mock()
            mock_select.return_value = mock_stmt
            mock_stmt.where.return_value = mock_stmt
            
            with patch.object(repo, '_to_entity') as mock_to_entity:
                mock_to_entity.return_value = entities[0]
                result = repo.list()
        
        # Verify select and where clauses
        mock_select.assert_called_once_with(BranchContextModel)
        mock_stmt.where.assert_called_once()  # User filter applied
        self.session.execute.assert_called_once()
        
        assert result == entities

    def test_list_with_filters(self):
        """Test listing branch contexts with filters"""
        repo = BranchContextRepository(self.session_factory, self.user_id)
        repo._session = None
        db_models = [self.create_test_db_model()]
        entities = [self.create_test_branch_context()]
        filters = {"project_id": self.project_id}
        
        # Mock select and execute
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = db_models
        self.session.execute.return_value = mock_result
        
        with patch('dhafnck_mcp_main.src.fastmcp.task_management.infrastructure.repositories.branch_context_repository.select') as mock_select:
            mock_stmt = Mock()
            mock_select.return_value = mock_stmt
            mock_stmt.where.return_value = mock_stmt
            
            with patch.object(repo, '_to_entity') as mock_to_entity:
                mock_to_entity.return_value = entities[0]
                result = repo.list(filters)
        
        # Verify where clauses (user filter + project filter)
        assert mock_stmt.where.call_count == 2
        assert result == entities

    def test_list_without_user_id(self):
        """Test listing branch contexts without user ID"""
        repo = BranchContextRepository(self.session_factory)
        repo._session = None
        db_models = [self.create_test_db_model()]
        entities = [self.create_test_branch_context()]
        
        # Mock select and execute
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = db_models
        self.session.execute.return_value = mock_result
        
        with patch('dhafnck_mcp_main.src.fastmcp.task_management.infrastructure.repositories.branch_context_repository.select') as mock_select:
            mock_stmt = Mock()
            mock_select.return_value = mock_stmt
            
            with patch.object(repo, '_to_entity') as mock_to_entity:
                mock_to_entity.return_value = entities[0]
                result = repo.list()
        
        # Verify no user filter applied
        mock_stmt.where.assert_not_called()
        assert result == entities

    def test_to_entity_with_data_field(self):
        """Test _to_entity conversion with data in data field"""
        repo = BranchContextRepository(self.session_factory, self.user_id)
        db_model = BranchContextModel(
            id=self.context_id,
            parent_project_id=self.project_id,
            branch_id="branch-123",
            data={
                "branch_workflow": {"steps": ["analyze", "implement"]},
                "branch_standards": {"coding_style": "PEP8", "_custom": {"custom_field": "custom_value"}},
                "agent_assignments": {"primary": "@coding_agent"}
            },
            branch_workflow={},
            local_overrides={"override1": "value1"},
            delegation_rules={"rule1": "delegate_up"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        entity = repo._to_entity(db_model)
        
        assert entity.id == self.context_id
        assert entity.project_id == self.project_id
        assert entity.git_branch_name == "branch-branch-123"
        assert entity.branch_settings["branch_workflow"] == {"steps": ["analyze", "implement"]}
        assert entity.branch_settings["branch_standards"] == {"coding_style": "PEP8"}
        assert entity.branch_settings["agent_assignments"] == {"primary": "@coding_agent"}
        assert entity.branch_settings["custom_field"] == "custom_value"  # Custom field extracted
        assert entity.metadata["local_overrides"] == {"override1": "value1"}

    def test_to_entity_with_individual_fields(self):
        """Test _to_entity conversion with data in individual fields"""
        repo = BranchContextRepository(self.session_factory, self.user_id)
        db_model = BranchContextModel(
            id=self.context_id,
            parent_project_id=self.project_id,
            branch_id="branch-123",
            data={},  # Empty data field
            branch_workflow={"steps": ["analyze", "implement"]},
            local_overrides={"override1": "value1"},
            delegation_rules={"rule1": "delegate_up"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        entity = repo._to_entity(db_model)
        
        assert entity.id == self.context_id
        assert entity.project_id == self.project_id
        assert entity.branch_settings["branch_workflow"] == {"steps": ["analyze", "implement"]}
        assert entity.branch_settings["branch_standards"] == {}
        assert entity.branch_settings["agent_assignments"] == {}

    def test_to_entity_none_values(self):
        """Test _to_entity conversion with None values"""
        repo = BranchContextRepository(self.session_factory, self.user_id)
        db_model = BranchContextModel(
            id=self.context_id,
            parent_project_id=self.project_id,
            branch_id="branch-123",
            data=None,
            branch_workflow=None,
            local_overrides=None,
            delegation_rules=None,
            created_at=None,
            updated_at=None
        )
        
        entity = repo._to_entity(db_model)
        
        assert entity.id == self.context_id
        assert entity.project_id == self.project_id
        assert entity.branch_settings["branch_workflow"] == {}
        assert entity.branch_settings["branch_standards"] == {}
        assert entity.branch_settings["agent_assignments"] == {}
        assert entity.metadata["local_overrides"] == {}
        assert entity.metadata["delegation_rules"] == {}
        assert entity.metadata["created_at"] is None
        assert entity.metadata["updated_at"] is None


class TestBranchContextRepositoryIntegration:
    """Integration tests for BranchContextRepository"""

    def setup_method(self):
        """Set up test fixtures"""
        self.session_factory = Mock()
        self.session = Mock()
        self.session_factory.return_value = self.session
        self.user_id = "integration-test-user"
        self.repo = BranchContextRepository(self.session_factory, self.user_id)
        self.repo._session = None

    def test_complete_crud_workflow(self):
        """Test complete CRUD workflow"""
        context_id = "integration-test-context"
        project_id = "integration-test-project"
        
        # Create test entity
        entity = BranchContext(
            id=context_id,
            project_id=project_id,
            git_branch_name="feature/integration-test",
            branch_settings={
                "branch_workflow": {"steps": ["design", "implement", "test"]},
                "branch_standards": {"style": "clean"},
                "agent_assignments": {"lead": "@integration_agent"}
            },
            metadata={"user_id": self.user_id}
        )
        
        # Mock create workflow
        query_mock = Mock()
        filter_mock = Mock()
        query_mock.filter.return_value = filter_mock
        filter_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = None  # Not exists
        self.session.query.return_value = query_mock
        
        # Mock get workflow
        db_model = BranchContextModel(
            id=context_id,
            parent_project_id=project_id,
            branch_id=None,
            data={
                "branch_workflow": {"steps": ["design", "implement", "test"]},
                "branch_standards": {"style": "clean"},
                "agent_assignments": {"lead": "@integration_agent"}
            },
            user_id=self.user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Test create
        with patch.object(self.repo, '_to_entity') as mock_to_entity:
            mock_to_entity.return_value = entity
            created = self.repo.create(entity)
            assert created == entity
        
        # Test get - need to reset query mock for get method
        get_query_mock = Mock()
        get_filter_mock = Mock()
        get_query_mock.filter.return_value = get_filter_mock
        get_filter_mock.filter.return_value = get_filter_mock
        get_filter_mock.first.return_value = db_model
        self.session.query.return_value = get_query_mock
        
        with patch.object(self.repo, '_to_entity') as mock_to_entity:
            mock_to_entity.return_value = entity
            retrieved = self.repo.get(context_id)
            assert retrieved == entity
        
        # Test update
        self.session.get.return_value = db_model
        updated_entity = BranchContext(
            id=context_id,
            project_id=project_id,
            git_branch_name="feature/updated",
            branch_settings={"updated": True},
            metadata={"user_id": self.user_id}
        )
        with patch.object(self.repo, '_to_entity') as mock_to_entity:
            mock_to_entity.return_value = updated_entity
            updated = self.repo.update(context_id, updated_entity)
            assert updated == updated_entity
        
        # Test delete
        self.session.get.return_value = db_model
        deleted = self.repo.delete(context_id)
        assert deleted is True

    def test_user_isolation(self):
        """Test user isolation functionality"""
        user1_id = "user-1"
        user2_id = "user-2"
        
        repo1 = BranchContextRepository(self.session_factory, user1_id)
        repo2 = BranchContextRepository(self.session_factory, user2_id)
        
        # Mock queries to verify user filters are applied correctly
        query_mock1 = Mock()
        filter_mock1 = Mock()
        query_mock1.filter.return_value = filter_mock1
        filter_mock1.filter.return_value = filter_mock1
        filter_mock1.first.return_value = None
        
        query_mock2 = Mock()
        filter_mock2 = Mock()
        query_mock2.filter.return_value = filter_mock2
        filter_mock2.filter.return_value = filter_mock2
        filter_mock2.first.return_value = None
        
        # Test that different repos use different user filters
        self.session.query.side_effect = [query_mock1, query_mock2]
        
        # Both repos attempt to get same context ID
        context_id = "shared-context-id"
        result1 = repo1.get(context_id)
        result2 = repo2.get(context_id)
        
        # Verify both queries had user filters applied
        assert filter_mock1.filter.called
        assert filter_mock2.filter.called
        assert result1 is None
        assert result2 is None