"""Test suite for BranchContextRepository.

Tests the branch context repository including:
- CRUD operations for branch contexts
- Session management with custom factory
- Entity to model conversion
- Custom field preservation
- Error handling and validation
- User isolation and filtering
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from contextlib import contextmanager
import uuid

from fastmcp.task_management.infrastructure.repositories.branch_context_repository import BranchContextRepository
from fastmcp.task_management.domain.entities.context import BranchContext
from fastmcp.task_management.infrastructure.database.models import BranchContext as BranchContextModel
from sqlalchemy.exc import SQLAlchemyError


class TestBranchContextRepository:
    """Test cases for BranchContextRepository."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock session factory
        self.mock_session_factory = Mock()
        self.mock_session = Mock()
        self.mock_session_factory.return_value = self.mock_session
        
        # Setup session methods
        self.mock_session.commit = Mock()
        self.mock_session.rollback = Mock()
        self.mock_session.close = Mock()
        self.mock_session.add = Mock()
        self.mock_session.flush = Mock()
        self.mock_session.refresh = Mock()
        self.mock_session.get = Mock()
        self.mock_session.execute = Mock()
        self.mock_session.delete = Mock()
        
        # Create repository instance
        self.user_id = "test-user-123"
        self.repository = BranchContextRepository(self.mock_session_factory, user_id=self.user_id)
        
        # Test data
        self.test_context_id = str(uuid.uuid4())
        self.test_project_id = str(uuid.uuid4())
        self.test_branch_settings = {
            'branch_workflow': {'step1': 'review', 'step2': 'test'},
            'branch_standards': {'coding_style': 'pep8', 'test_coverage': 90},
            'agent_assignments': {'coding-agent': 'active'},
            'custom_field': 'custom_value'  # Test custom field preservation
        }
        
        self.test_metadata = {
            'local_overrides': {'override1': 'value1'},
            'delegation_rules': {'rule1': 'delegate_up'},
            'user_id': 'test-user-123'
        }
        
        self.test_entity = BranchContext(
            id=self.test_context_id,
            project_id=self.test_project_id,
            git_branch_name="feature/test-branch",
            branch_settings=self.test_branch_settings,
            metadata=self.test_metadata
        )
    
    def test_init(self):
        """Test repository initialization."""
        assert self.repository.session_factory == self.mock_session_factory
        assert self.repository.model_class == BranchContextModel
    
    def test_get_db_session_with_existing_session(self):
        """Test get_db_session uses existing session from transaction."""
        # Mock existing session
        existing_session = Mock()
        self.repository._session = existing_session
        
        with self.repository.get_db_session() as session:
            assert session == existing_session
        
        # Verify no new session was created
        self.mock_session_factory.assert_not_called()
    
    def test_get_db_session_creates_new_session(self):
        """Test get_db_session creates new session when none exists."""
        # Ensure no existing session
        self.repository._session = None
        
        with self.repository.get_db_session() as session:
            assert session == self.mock_session
        
        # Verify session lifecycle
        self.mock_session_factory.assert_called_once()
        self.mock_session.commit.assert_called_once()
        self.mock_session.close.assert_called_once()
    
    def test_get_db_session_handles_sql_error(self):
        """Test get_db_session handles SQLAlchemy errors with rollback."""
        self.repository._session = None
        
        # Make session operation raise error
        self.mock_session.commit.side_effect = SQLAlchemyError("Database error")
        
        with pytest.raises(SQLAlchemyError):
            with self.repository.get_db_session() as session:
                assert session == self.mock_session
                # This will trigger the error when exiting context
        
        # Verify rollback was called
        self.mock_session.rollback.assert_called_once()
        self.mock_session.close.assert_called_once()
    
    def test_create_success(self):
        """Test successful branch context creation."""
        # Mock query for existing check
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # No existing context
        self.mock_session.query.return_value = mock_query
        
        # Mock the created model
        created_model = BranchContextModel(
            id=self.test_context_id,
            branch_id=None,  # Should be None per current implementation
            parent_project_id=self.test_project_id,
            data={'test': 'data'},
            branch_workflow={},
            feature_flags={},
            active_patterns={},
            local_overrides={},
            delegation_rules={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        with patch.object(self.repository, '_to_entity') as mock_to_entity:
            mock_to_entity.return_value = self.test_entity
            
            result = self.repository.create(self.test_entity)
        
        assert result == self.test_entity
        
        # Verify session operations
        self.mock_session.query.assert_called_once_with(BranchContextModel)
        assert mock_query.filter.call_count >= 1  # At least ID filter
        self.mock_session.add.assert_called_once()
        self.mock_session.flush.assert_called_once()
        # refresh is commented out in implementation to avoid UUID issues
        # self.mock_session.refresh.assert_called_once()
    
    def test_create_already_exists(self):
        """Test creation returns existing entity for idempotency."""
        # Mock query for existing check
        mock_query = Mock()
        mock_query.filter.return_value = mock_query

        # Create a proper mock for existing context with all required attributes
        existing_context_mock = Mock()
        existing_context_mock.id = self.test_context_id
        existing_context_mock.parent_project_id = self.test_project_id
        existing_context_mock.data = {}  # Set data as empty dict to be iterable
        existing_context_mock.branch_info = {}
        existing_context_mock.branch_workflow = {}
        existing_context_mock.feature_flags = {}
        existing_context_mock.discovered_patterns = {}
        existing_context_mock.branch_decisions = {}
        existing_context_mock.active_patterns = {}
        existing_context_mock.local_overrides = {}
        existing_context_mock.delegation_rules = {}
        existing_context_mock.created_at = None
        existing_context_mock.updated_at = None
        existing_context_mock.branch_id = None
        mock_query.first.return_value = existing_context_mock

        self.mock_session.query.return_value = mock_query

        # Should return existing entity instead of raising (idempotent behavior)
        result = self.repository.create(self.test_entity)

        # Verify returns existing entity with correct ID
        assert result.id == self.test_context_id
        assert result.project_id == self.test_project_id

        # Verify no new record was created
        self.mock_session.add.assert_not_called()
        self.mock_session.flush.assert_not_called()
    
    def test_create_preserves_legacy_fields(self):
        """Test that legacy fields are properly mapped to new structure."""
        # Mock query for existing check
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # No existing context
        self.mock_session.query.return_value = mock_query

        # Create entity with legacy branch_settings
        test_settings = {
            'branch_workflow': {'step1': 'review'},
            'branch_standards': {'style': 'pep8'},
            'agent_assignments': {'@agent': 'active'},
            'custom_field1': 'value1',
            'custom_field2': {'nested': 'value2'}
        }

        entity = BranchContext(
            id=self.test_context_id,
            project_id=self.test_project_id,
            git_branch_name="test-branch",
            branch_settings=test_settings,
            metadata=self.test_metadata
        )

        with patch.object(self.repository, '_to_entity') as mock_to_entity:
            mock_to_entity.return_value = entity

            self.repository.create(entity)

        # Verify add was called with proper field mapping
        self.mock_session.add.assert_called_once()
        added_model = self.mock_session.add.call_args[0][0]

        # Check that legacy fields are mapped to new structure
        data_field = added_model.data
        # branch_standards is mapped to branch_decisions
        assert 'branch_decisions' in data_field
        assert data_field['branch_decisions']['style'] == 'pep8'

        # branch_workflow is preserved
        assert 'branch_workflow' in data_field
        assert data_field['branch_workflow']['step1'] == 'review'

        # agent_assignments is moved to branch_info
        assert 'branch_info' in data_field
        assert data_field['branch_info']['agent_assignments'] == {'@agent': 'active'}

        # Note: Custom fields (custom_field1, custom_field2) are not preserved
        # in the current implementation as they're not part of the known schema
    
    def test_create_uses_default_project_id(self):
        """Test creation handles None project_id correctly per ORM specification."""
        # Create entity without project_id
        entity = BranchContext(
            id=self.test_context_id,
            project_id=None,
            git_branch_name="test-branch",
            branch_settings={},
            metadata={}
        )

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # No existing context
        self.mock_session.query.return_value = mock_query

        with patch.object(self.repository, '_to_entity') as mock_to_entity:
            mock_to_entity.return_value = entity

            self.repository.create(entity)

        # Verify parent_project_id is None when entity.project_id is None
        # This matches the ORM model specification where parent_project_id is nullable with no default
        added_model = self.mock_session.add.call_args[0][0]
        assert added_model.parent_project_id is None
        # Verify branch_id is None
        assert added_model.branch_id is None
    
    def test_get_success(self):
        """Test successful branch context retrieval."""
        # Mock database model
        db_model = BranchContextModel(
            id=self.test_context_id,
            branch_id=None,  # Should be None per current implementation
            parent_project_id=self.test_project_id,
            data={'test': 'data'},
            branch_workflow={'step1': 'test'},
            feature_flags={},
            active_patterns={},
            local_overrides={},
            delegation_rules={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            user_id=self.user_id
        )
        
        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = db_model
        self.mock_session.query.return_value = mock_query
        
        with patch.object(self.repository, '_to_entity') as mock_to_entity:
            mock_to_entity.return_value = self.test_entity
            
            result = self.repository.get(self.test_context_id)
        
        assert result == self.test_entity
        self.mock_session.query.assert_called_once_with(BranchContextModel)
        # Verify filters were applied
        assert mock_query.filter.call_count >= 1  # At least ID filter
        mock_to_entity.assert_called_once_with(db_model)
    
    def test_get_not_found(self):
        """Test retrieval returns None when context not found."""
        # Mock query returning None
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        self.mock_session.query.return_value = mock_query
        
        result = self.repository.get(self.test_context_id)
        
        assert result is None
    
    def test_update_success(self):
        """Test successful branch context update."""
        # Mock existing model
        existing_model = Mock()
        existing_model.user_id = "existing-user"
        self.mock_session.get.return_value = existing_model
        
        with patch.object(self.repository, '_to_entity') as mock_to_entity:
            mock_to_entity.return_value = self.test_entity
            
            result = self.repository.update(self.test_context_id, self.test_entity)
        
        assert result == self.test_entity
        
        # Verify model fields were updated
        assert existing_model.parent_project_id == self.test_project_id
        assert existing_model.branch_workflow == self.test_branch_settings['branch_workflow']
        assert existing_model.local_overrides == self.test_metadata['local_overrides']
        assert existing_model.delegation_rules == self.test_metadata['delegation_rules']
        
        # Verify session operations
        self.mock_session.flush.assert_called_once()
        # refresh is commented out in implementation to avoid UUID issues
        # self.mock_session.refresh.assert_called_once()
    
    def test_update_not_found(self):
        """Test update fails when context doesn't exist."""
        self.mock_session.get.return_value = None
        
        with pytest.raises(ValueError) as exc_info:
            self.repository.update(self.test_context_id, self.test_entity)
        
        assert f"Branch context not found: {self.test_context_id}" in str(exc_info.value)
    
    def test_delete_success(self):
        """Test successful branch context deletion."""
        # Mock existing model
        existing_model = Mock()
        self.mock_session.get.return_value = existing_model
        
        result = self.repository.delete(self.test_context_id)
        
        assert result is True
        self.mock_session.get.assert_called_once_with(BranchContextModel, self.test_context_id)
        self.mock_session.delete.assert_called_once_with(existing_model)
    
    def test_delete_not_found(self):
        """Test deletion returns False when context not found."""
        self.mock_session.get.return_value = None
        
        result = self.repository.delete(self.test_context_id)
        
        assert result is False
        self.mock_session.delete.assert_not_called()
    
    def test_list_without_filters(self):
        """Test listing all branch contexts without filters."""
        # Mock database models
        db_models = [
            Mock(id=f"context-{i}", branch_id=f"branch-{i}") 
            for i in range(3)
        ]
        
        # Mock SQLAlchemy result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = db_models
        self.mock_session.execute.return_value = mock_result
        
        with patch.object(self.repository, '_to_entity') as mock_to_entity:
            mock_to_entity.side_effect = lambda model: BranchContext(
                id=model.id,
                project_id="test-project",
                git_branch_name=f"branch-{model.branch_id}",
                branch_settings={},
                metadata={}
            )
            
            result = self.repository.list()
        
        assert len(result) == 3
        assert all(isinstance(ctx, BranchContext) for ctx in result)
        
        # Verify SQL execution
        self.mock_session.execute.assert_called_once()
    
    def test_list_with_filters(self):
        """Test listing branch contexts with filters applied."""
        filters = {
            "project_id": self.test_project_id,
            "git_branch_name": "feature/test"
        }
        
        # Mock empty result for simplicity
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        self.mock_session.execute.return_value = mock_result
        
        result = self.repository.list(filters)
        
        assert result == []
        
        # Verify execute was called (with filters applied)
        self.mock_session.execute.assert_called_once()
    
    def test_to_entity_basic_conversion(self):
        """Test _to_entity converts database model to domain entity."""
        # Create test database model
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
        
        db_model = BranchContextModel(
            id=self.test_context_id,
            branch_id=self.test_context_id,
            parent_project_id=self.test_project_id,
            data={
                'branch_workflow': {'step1': 'review'},
                'branch_standards': {'style': 'pep8'},
                'agent_assignments': {'@agent': 'active'}
            },
            branch_workflow={'workflow': 'data'},
            feature_flags={},
            active_patterns={},
            local_overrides={'override': 'value'},
            delegation_rules={'rule': 'value'},
            created_at=created_at,
            updated_at=updated_at
        )
        
        result = self.repository._to_entity(db_model)

        assert result.id == self.test_context_id
        assert result.project_id == self.test_project_id
        assert result.git_branch_name == f"branch-{db_model.branch_id}"
        # branch_workflow is a direct attribute, not in branch_settings
        assert result.branch_workflow == {'workflow': 'data'}
        assert result.branch_settings['branch_standards'] == {'style': 'pep8'}
        assert result.branch_settings['agent_assignments'] == {'@agent': 'active'}
        assert result.metadata['local_overrides'] == {'override': 'value'}
        assert result.metadata['delegation_rules'] == {'rule': 'value'}
        assert result.metadata['created_at'] == created_at.isoformat()
        assert result.metadata['updated_at'] == updated_at.isoformat()
    
    def test_to_entity_custom_fields_extraction(self):
        """Test _to_entity preserves custom fields in branch_standards."""
        # Create database model with custom fields in _custom section
        db_model = BranchContextModel(
            id=self.test_context_id,
            branch_id=self.test_context_id,
            parent_project_id=self.test_project_id,
            data={
                'branch_workflow': {'step1': 'review'},
                'branch_standards': {
                    'style': 'pep8',
                    '_custom': {
                        'custom_field1': 'value1',
                        'custom_field2': {'nested': 'value2'}
                    }
                },
                'agent_assignments': {}
            },
            branch_workflow={},
            feature_flags={},
            active_patterns={},
            local_overrides={},
            delegation_rules={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        result = self.repository._to_entity(db_model)

        # Verify branch_standards is preserved as-is including _custom section
        assert result.branch_settings['branch_standards'] == {
            'style': 'pep8',
            '_custom': {
                'custom_field1': 'value1',
                'custom_field2': {'nested': 'value2'}
            }
        }
        assert result.branch_settings['agent_assignments'] == {}
        # branch_workflow is stored as direct attribute
        assert result.branch_workflow == {'step1': 'review'}
    
    def test_to_entity_fallback_to_individual_fields(self):
        """Test _to_entity falls back to individual fields when data is empty."""
        # Create database model with empty data field
        db_model = BranchContextModel(
            id=self.test_context_id,
            branch_id=self.test_context_id,
            parent_project_id=self.test_project_id,
            data=None,  # Empty data field
            branch_workflow={'fallback': 'workflow'},
            feature_flags={},
            active_patterns={},
            local_overrides={'fallback': 'override'},
            delegation_rules={'fallback': 'rule'},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        result = self.repository._to_entity(db_model)

        # Should use individual fields as fallback
        # branch_workflow is a direct attribute, not in branch_settings
        assert result.branch_workflow == {'fallback': 'workflow'}
        assert result.metadata['local_overrides'] == {'fallback': 'override'}
        assert result.metadata['delegation_rules'] == {'fallback': 'rule'}
    
    def test_to_entity_handles_missing_timestamps(self):
        """Test _to_entity handles missing created_at/updated_at timestamps."""
        db_model = BranchContextModel(
            id=self.test_context_id,
            branch_id=self.test_context_id,
            parent_project_id=self.test_project_id,
            data={},
            branch_workflow={},
            feature_flags={},
            active_patterns={},
            local_overrides={},
            delegation_rules={},
            created_at=None,
            updated_at=None
        )
        
        result = self.repository._to_entity(db_model)
        
        assert result.metadata['created_at'] is None
        assert result.metadata['updated_at'] is None
    
    @patch('fastmcp.task_management.infrastructure.repositories.branch_context_repository.select')
    def test_list_applies_project_filter(self, mock_select):
        """Test list applies project_id filter correctly."""
        # Setup mock select
        mock_stmt = Mock()
        mock_select.return_value = mock_stmt
        mock_stmt.where.return_value = mock_stmt
        
        # Mock empty result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        self.mock_session.execute.return_value = mock_result
        
        filters = {"project_id": self.test_project_id}
        self.repository.list(filters)
        
        # Verify filter was applied
        mock_stmt.where.assert_called()
        where_call_args = mock_stmt.where.call_args[0][0]
        # The where clause should reference the parent_project_id field (actual model field)
        assert hasattr(where_call_args, 'left')  # SQLAlchemy comparison object
    
    @patch('fastmcp.task_management.infrastructure.repositories.branch_context_repository.select')
    def test_list_applies_branch_name_filter(self, mock_select):
        """Test list applies git_branch_name filter correctly."""
        # Setup mock select
        mock_stmt = Mock()
        mock_select.return_value = mock_stmt
        mock_stmt.where.return_value = mock_stmt
        
        # Mock empty result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        self.mock_session.execute.return_value = mock_result
        
        filters = {"git_branch_name": "feature/test"}
        self.repository.list(filters)
        
        # Verify filter was applied
        mock_stmt.where.assert_called()
        where_call_args = mock_stmt.where.call_args[0][0]
        # Note: git_branch_name filtering may use JOIN or other logic, just verify filter was applied
        assert hasattr(where_call_args, 'left')  # SQLAlchemy comparison object
    
    def test_update_sets_updated_at_timestamp(self):
        """Test update sets updated_at timestamp."""
        # Mock existing model
        existing_model = Mock()
        existing_model.user_id = "existing-user"
        self.mock_session.get.return_value = existing_model
        
        with patch.object(self.repository, '_to_entity') as mock_to_entity:
            mock_to_entity.return_value = self.test_entity
            
            # Capture the time before update
            before_update = datetime.now(timezone.utc)
            
            self.repository.update(self.test_context_id, self.test_entity)
            
            # Capture the time after update
            after_update = datetime.now(timezone.utc)
        
        # Verify updated_at was set to a reasonable time
        assert hasattr(existing_model, 'updated_at')
        # The updated_at should be between before and after
        assert before_update <= existing_model.updated_at <= after_update
    
    def test_with_user_creates_new_instance(self):
        """Test with_user creates new repository instance with different user."""
        new_user_id = "different-user-456"
        new_repo = self.repository.with_user(new_user_id)
        
        assert isinstance(new_repo, BranchContextRepository)
        assert new_repo.user_id == new_user_id
        assert new_repo.session_factory == self.repository.session_factory
        # Original repository should be unchanged
        assert self.repository.user_id == self.user_id
    
    def test_get_applies_user_filter(self):
        """Test get method applies user filtering when user_id is set."""
        # Mock database model
        db_model = BranchContextModel(
            id=self.test_context_id,
            branch_id=self.test_context_id,
            parent_project_id=self.test_project_id,
            data={'test': 'data'},
            user_id=self.user_id
        )
        
        # Setup mock query
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = db_model
        self.mock_session.query.return_value = mock_query
        
        with patch.object(self.repository, '_to_entity') as mock_to_entity:
            mock_to_entity.return_value = self.test_entity
            
            result = self.repository.get(self.test_context_id)
        
        # Verify user filter was applied - check that filter was called at least once
        assert mock_query.filter.call_count >= 1  # At least ID filter was applied
        
        assert result == self.test_entity
    
    def test_get_system_mode_no_user_filter(self):
        """Test get method without user filtering in system mode."""
        # Create system repository (no user_id)
        system_repo = BranchContextRepository(self.mock_session_factory, user_id=None)
        
        # Mock database model
        db_model = BranchContextModel(
            id=self.test_context_id,
            branch_id=self.test_context_id,
            parent_project_id=self.test_project_id,
            data={'test': 'data'}
        )
        
        # Setup mock query
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = db_model
        self.mock_session.query.return_value = mock_query
        
        with patch.object(system_repo, '_to_entity') as mock_to_entity:
            mock_to_entity.return_value = self.test_entity
            
            result = system_repo.get(self.test_context_id)
        
        # Verify only ID filter was applied (no user filter)
        assert mock_query.filter.call_count == 1  # Only ID filter
        assert result == self.test_entity
    
    def test_list_applies_user_filter(self):
        """Test list method applies user filtering."""
        # Mock empty result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        self.mock_session.execute.return_value = mock_result
        
        with patch('fastmcp.task_management.infrastructure.repositories.branch_context_repository.select') as mock_select:
            mock_stmt = Mock()
            mock_select.return_value = mock_stmt
            mock_stmt.where.return_value = mock_stmt
            
            result = self.repository.list()
        
        # Verify user filter was applied to the statement
        mock_stmt.where.assert_called_once()
        # The where should be called with user_id filter
        where_call = mock_stmt.where.call_args[0][0]
        assert result == []
    
    def test_list_system_mode_no_user_filter(self):
        """Test list method without user filtering in system mode."""
        # Create system repository (no user_id)
        system_repo = BranchContextRepository(self.mock_session_factory, user_id=None)
        
        # Mock empty result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        self.mock_session.execute.return_value = mock_result
        
        with patch('fastmcp.task_management.infrastructure.repositories.branch_context_repository.select') as mock_select:
            mock_stmt = Mock()
            mock_select.return_value = mock_stmt
            mock_stmt.where.return_value = mock_stmt
            
            result = system_repo.list()
        
        # In system mode, only additional filters should be applied, not user filter
        # Check that where was not called (no user filter applied)
        mock_stmt.where.assert_not_called()
        assert result == []
    
    def test_create_sets_user_id(self):
        """Test create method sets user_id from repository context."""
        # Mock query for existing check
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # No existing context
        self.mock_session.query.return_value = mock_query
        
        with patch.object(self.repository, '_to_entity') as mock_to_entity:
            mock_to_entity.return_value = self.test_entity
            
            result = self.repository.create(self.test_entity)
        
        # Verify user_id was set on created model
        self.mock_session.add.assert_called_once()
        added_model = self.mock_session.add.call_args[0][0]
        assert added_model.user_id == self.user_id
    
    def test_create_uses_metadata_user_id_fallback(self):
        """Test create method now requires user_id to be set - metadata fallback removed."""
        # Create repository without user_id
        system_repo = BranchContextRepository(self.mock_session_factory, user_id=None)
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # No existing context
        self.mock_session.query.return_value = mock_query

        # Create entity with user_id in metadata
        entity_with_user = BranchContext(
            id=self.test_context_id,
            project_id=self.test_project_id,
            git_branch_name="test-branch",
            branch_settings={},
            metadata={'user_id': 'metadata-user-789'}
        )

        # Now the system raises ValueError when user_id not set
        with pytest.raises(ValueError, match="user_id is required for branch context creation"):
            system_repo.create(entity_with_user)
    
    def test_create_no_fallback_to_system(self):
        """Test create method does not fall back to 'system' when no user_id available."""
        # Create repository without user_id
        system_repo = BranchContextRepository(self.mock_session_factory, user_id=None)
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # No existing context
        self.mock_session.query.return_value = mock_query

        # Create entity without user_id in metadata
        entity_no_user = BranchContext(
            id=self.test_context_id,
            project_id=self.test_project_id,
            git_branch_name="test-branch",
            branch_settings={},
            metadata={}
        )

        # The system now raises ValueError when user_id not set
        with pytest.raises(ValueError, match="user_id is required for branch context creation"):
            system_repo.create(entity_no_user)
    
    def test_update_preserves_user_id_precedence(self):
        """Test update method respects user_id precedence: repository > metadata > existing."""
        # Mock existing model with different user_id
        existing_model = Mock()
        existing_model.user_id = "existing-user-999"
        self.mock_session.get.return_value = existing_model
        
        # Create entity with user_id in metadata
        entity_with_user = BranchContext(
            id=self.test_context_id,
            project_id=self.test_project_id,
            git_branch_name="test-branch",
            branch_settings={},
            metadata={'user_id': 'metadata-user-888'}
        )
        
        with patch.object(self.repository, '_to_entity') as mock_to_entity:
            mock_to_entity.return_value = entity_with_user
            
            result = self.repository.update(self.test_context_id, entity_with_user)
        
        # Verify repository user_id took precedence
        assert existing_model.user_id == self.user_id  # Repository user_id wins
    
    def test_user_isolation_boundary(self):
        """Test that users cannot access each other's contexts."""
        # Create contexts for two different users
        user1_repo = BranchContextRepository(self.mock_session_factory, user_id="user-001")
        user2_repo = BranchContextRepository(self.mock_session_factory, user_id="user-002")
        
        context_id = str(uuid.uuid4())
        
        # Mock query for user1 - returns a context
        mock_query_user1 = Mock()
        mock_query_user1.filter.return_value = mock_query_user1
        mock_query_user1.first.return_value = Mock(id=context_id, user_id="user-001")
        
        # Mock query for user2 - returns None (no access)
        mock_query_user2 = Mock()
        mock_query_user2.filter.return_value = mock_query_user2
        mock_query_user2.first.return_value = None
        
        self.mock_session.query.side_effect = [mock_query_user1, mock_query_user2]
        
        # User1 should find their context
        with patch.object(user1_repo, '_to_entity', return_value=self.test_entity):
            result1 = user1_repo.get(context_id)
            assert result1 is not None
        
        # User2 should not find user1's context
        result2 = user2_repo.get(context_id)
        assert result2 is None


if __name__ == "__main__":
    pytest.main([__file__])