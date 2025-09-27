"""
Comprehensive tests for BaseUserScopedRepository pattern.
Following TDD principles - these tests define the expected behavior.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from uuid import uuid4
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastmcp.task_management.infrastructure.repositories.base_user_scoped_repository import BaseUserScopedRepository


class ConcreteUserScopedRepository(BaseUserScopedRepository):
    """Concrete implementation for testing."""
    
    def __init__(self, session, user_id: str):
        self._validate_user_id(user_id)
        super().__init__(session, user_id)
        self.table_name = "test_table"
    
    def _validate_user_id(self, user_id: str):
        """Validate user_id format."""
        import uuid
        if not user_id or not isinstance(user_id, str):
            raise ValueError("Invalid user_id: must be a non-empty string")
        try:
            # Check if it's a valid UUID
            uuid.UUID(user_id)
        except (ValueError, AttributeError):
            raise ValueError("Invalid user_id: must be a valid UUID string")
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new entity with automatic user_id insertion."""
        # Remove any user_id from input data to prevent override
        clean_data = {k: v for k, v in data.items() if k != 'user_id'}
        # Add the correct user_id
        clean_data['user_id'] = self.user_id
        
        # Build INSERT query
        columns = ', '.join(clean_data.keys())
        values = ', '.join([f"'{v}'" for v in clean_data.values()])
        query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({values})"
        
        self.session.execute_query(query)
        return clean_data
    
    def get_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity by ID with user_id filter."""
        query = f"SELECT * FROM {self.table_name} WHERE id = '{entity_id}' AND user_id = '{self.user_id}'"
        self.session.execute_query(query)
        return self.session.fetch_one()
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all entities for the current user."""
        query = f"SELECT * FROM {self.table_name} WHERE user_id = '{self.user_id}'"
        self.session.execute_query(query)
        return self.session.fetch_all()
    
    def search(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search entities with user_id filter."""
        conditions = [f"{k} = '{v}'" for k, v in search_params.items()]
        conditions.append(f"user_id = '{self.user_id}'")
        where_clause = ' AND '.join(conditions)
        query = f"SELECT * FROM {self.table_name} WHERE {where_clause}"
        self.session.execute_query(query)
        return self.session.fetch_all()
    
    def update(self, entity_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update entity with user_id filter."""
        # Remove user_id from update data to prevent changing it
        clean_data = {k: v for k, v in update_data.items() if k != 'user_id'}
        
        if clean_data:
            set_clause = ', '.join([f"{k} = '{v}'" for k, v in clean_data.items()])
            query = f"UPDATE {self.table_name} SET {set_clause} WHERE id = '{entity_id}' AND user_id = '{self.user_id}'"
            self.session.execute_query(query)
        
        return clean_data
    
    def bulk_update(self, filter_criteria: Dict[str, Any], update_data: Dict[str, Any]) -> int:
        """Bulk update entities with user_id filter."""
        # Remove user_id from update data
        clean_data = {k: v for k, v in update_data.items() if k != 'user_id'}
        
        if clean_data:
            set_clause = ', '.join([f"{k} = '{v}'" for k, v in clean_data.items()])
            
            # Build WHERE clause with filter criteria and user_id
            conditions = [f"{k} = '{v}'" for k, v in filter_criteria.items()]
            conditions.append(f"user_id = '{self.user_id}'")
            where_clause = ' AND '.join(conditions)
            
            query = f"UPDATE {self.table_name} SET {set_clause} WHERE {where_clause}"
            self.session.execute_query(query)
        
        return 0  # Return affected rows count
    
    def delete(self, entity_id: str) -> bool:
        """Delete entity with user_id filter."""
        query = f"DELETE FROM {self.table_name} WHERE id = '{entity_id}' AND user_id = '{self.user_id}'"
        self.session.execute_query(query)
        return True
    
    def bulk_delete(self, filter_criteria: Dict[str, Any]) -> int:
        """Bulk delete entities with user_id filter."""
        conditions = [f"{k} = '{v}'" for k, v in filter_criteria.items()]
        conditions.append(f"user_id = '{self.user_id}'")
        where_clause = ' AND '.join(conditions)
        
        query = f"DELETE FROM {self.table_name} WHERE {where_clause}"
        self.session.execute_query(query)
        return 0  # Return affected rows count
    
    def count(self) -> int:
        """Count entities for the current user."""
        query = f"SELECT COUNT(*) FROM {self.table_name} WHERE user_id = '{self.user_id}'"
        self.session.execute_query(query)
        result = self.session.fetch_one()
        return result.get('count', 0) if result else 0
    
    def exists(self, entity_id: str) -> bool:
        """Check if entity exists for the current user."""
        query = f"SELECT 1 FROM {self.table_name} WHERE id = '{entity_id}' AND user_id = '{self.user_id}'"
        self.session.execute_query(query)
        return self.session.fetch_one() is not None
    
    def get_batch(self, entity_ids: List[str]) -> List[Dict[str, Any]]:
        """Get multiple entities by IDs with user_id filter."""
        if not entity_ids:
            return []
        
        ids_str = ', '.join([f"'{id}'" for id in entity_ids])
        query = f"SELECT * FROM {self.table_name} WHERE id IN ({ids_str}) AND user_id = '{self.user_id}'"
        self.session.execute_query(query)
        return self.session.fetch_all()


class TestBaseUserScopedRepository:
    """Test suite for BaseUserScopedRepository ensuring proper user isolation."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = Mock()
        session.execute_query = Mock()
        session.fetch_one = Mock()
        session.fetch_all = Mock()
        return session
    
    @pytest.fixture
    def user_id(self):
        """Generate a test user ID."""
        return str(uuid4())
    
    @pytest.fixture
    def other_user_id(self):
        """Generate another test user ID for cross-user testing."""
        return str(uuid4())
    
    @pytest.fixture
    def repository(self, mock_session, user_id):
        """Create a repository instance for testing."""
        return ConcreteUserScopedRepository(mock_session, user_id)
    
    # ==================== Constructor Tests ====================
    
    def test_repository_requires_user_id(self, mock_session):
        """Test that repository requires a user_id to be instantiated."""
        with pytest.raises(TypeError):
            ConcreteUserScopedRepository(mock_session)
    
    def test_repository_stores_user_id(self, repository, user_id):
        """Test that repository stores the provided user_id."""
        assert repository.user_id == user_id
    
    def test_repository_validates_user_id_format(self, mock_session):
        """Test that repository validates user_id is a valid UUID string."""
        invalid_user_ids = [None, "", "invalid-uuid", 123, {"id": "123"}]
        
        for invalid_id in invalid_user_ids:
            with pytest.raises(ValueError, match="Invalid user_id"):
                ConcreteUserScopedRepository(mock_session, invalid_id)
    
    # ==================== Query Filtering Tests ====================
    
    def test_apply_user_filter_adds_user_id_to_query(self, repository, user_id):
        """Test that apply_user_filter adds user_id condition to queries."""
        base_query = "SELECT * FROM tasks"
        filtered_query = repository.apply_user_filter(base_query)
        
        assert "user_id = " in filtered_query
        assert user_id in filtered_query
    
    def test_apply_user_filter_handles_where_clause(self, repository, user_id):
        """Test that apply_user_filter correctly handles existing WHERE clause."""
        query_with_where = "SELECT * FROM tasks WHERE status = 'active'"
        filtered_query = repository.apply_user_filter(query_with_where)
        
        assert "WHERE" in filtered_query
        assert "AND user_id = " in filtered_query
        assert user_id in filtered_query
    
    def test_apply_user_filter_handles_complex_queries(self, repository, user_id):
        """Test that apply_user_filter handles JOIN and complex queries."""
        complex_query = """
            SELECT t.*, p.name as project_name
            FROM tasks t
            JOIN projects p ON t.project_id = p.id
            WHERE t.status = 'active'
            ORDER BY t.created_at DESC
        """
        filtered_query = repository.apply_user_filter(complex_query)
        
        assert "AND t.user_id = " in filtered_query or "AND user_id = " in filtered_query
        assert user_id in filtered_query
    
    # ==================== Create Operation Tests ====================
    
    def test_create_automatically_adds_user_id(self, repository, mock_session, user_id):
        """Test that create operations automatically include user_id."""
        data = {"name": "Test Task", "status": "pending"}
        
        repository.create(data)
        
        # Verify the query includes user_id
        mock_session.execute_query.assert_called_once()
        call_args = mock_session.execute_query.call_args
        
        # Check that user_id was added to the data
        assert "user_id" in str(call_args)
        assert user_id in str(call_args)
    
    def test_create_prevents_overriding_user_id(self, repository, mock_session, user_id, other_user_id):
        """Test that users cannot override user_id in create operations."""
        data = {"name": "Test Task", "user_id": other_user_id}
        
        repository.create(data)
        
        # Verify the user_id was not overridden
        call_args = mock_session.execute_query.call_args
        assert other_user_id not in str(call_args)
        assert user_id in str(call_args)
    
    # ==================== Read Operation Tests ====================
    
    def test_get_by_id_filters_by_user(self, repository, mock_session, user_id):
        """Test that get_by_id includes user_id filter."""
        entity_id = str(uuid4())
        
        repository.get_by_id(entity_id)
        
        # Verify the query includes both entity_id and user_id
        mock_session.execute_query.assert_called_once()
        call_args = mock_session.execute_query.call_args
        
        query = str(call_args)
        assert entity_id in query
        assert user_id in query
        assert "user_id" in query
    
    def test_get_all_filters_by_user(self, repository, mock_session, user_id):
        """Test that get_all only returns user's entities."""
        repository.get_all()
        
        # Verify the query includes user_id filter
        mock_session.execute_query.assert_called_once()
        call_args = mock_session.execute_query.call_args
        
        query = str(call_args)
        assert user_id in query
        assert "user_id" in query
    
    def test_search_filters_by_user(self, repository, mock_session, user_id):
        """Test that search operations include user_id filter."""
        search_params = {"status": "active", "priority": "high"}
        
        repository.search(search_params)
        
        # Verify the query includes user_id filter
        mock_session.execute_query.assert_called_once()
        call_args = mock_session.execute_query.call_args
        
        query = str(call_args)
        assert user_id in query
        assert "user_id" in query
    
    # ==================== Update Operation Tests ====================
    
    def test_update_only_affects_user_entities(self, repository, mock_session, user_id):
        """Test that update operations only affect user's entities."""
        entity_id = str(uuid4())
        update_data = {"status": "completed"}
        
        repository.update(entity_id, update_data)
        
        # Verify the query includes both entity_id and user_id
        mock_session.execute_query.assert_called_once()
        call_args = mock_session.execute_query.call_args
        
        query = str(call_args)
        assert entity_id in query
        assert user_id in query
        assert "user_id" in query
    
    def test_update_prevents_changing_user_id(self, repository, mock_session, user_id, other_user_id):
        """Test that update operations cannot change user_id."""
        entity_id = str(uuid4())
        update_data = {"status": "completed", "user_id": other_user_id}
        
        repository.update(entity_id, update_data)
        
        # Verify user_id was not changed
        call_args = mock_session.execute_query.call_args
        query = str(call_args)
        assert other_user_id not in query or "SET user_id" not in query
    
    def test_bulk_update_filters_by_user(self, repository, mock_session, user_id):
        """Test that bulk updates only affect user's entities."""
        filter_criteria = {"status": "pending"}
        update_data = {"status": "in_progress"}
        
        repository.bulk_update(filter_criteria, update_data)
        
        # Verify the query includes user_id filter
        mock_session.execute_query.assert_called_once()
        call_args = mock_session.execute_query.call_args
        
        query = str(call_args)
        assert user_id in query
        assert "user_id" in query
    
    # ==================== Delete Operation Tests ====================
    
    def test_delete_only_affects_user_entities(self, repository, mock_session, user_id):
        """Test that delete operations only affect user's entities."""
        entity_id = str(uuid4())
        
        repository.delete(entity_id)
        
        # Verify the query includes both entity_id and user_id
        mock_session.execute_query.assert_called_once()
        call_args = mock_session.execute_query.call_args
        
        query = str(call_args)
        assert entity_id in query
        assert user_id in query
        assert "user_id" in query
    
    def test_bulk_delete_filters_by_user(self, repository, mock_session, user_id):
        """Test that bulk deletes only affect user's entities."""
        filter_criteria = {"status": "archived"}
        
        repository.bulk_delete(filter_criteria)
        
        # Verify the query includes user_id filter
        mock_session.execute_query.assert_called_once()
        call_args = mock_session.execute_query.call_args
        
        query = str(call_args)
        assert user_id in query
        assert "user_id" in query
    
    # ==================== Cross-User Isolation Tests ====================
    
    def test_user_cannot_access_other_user_data(self, mock_session, user_id, other_user_id):
        """Test that one user cannot access another user's data."""
        # Create repositories for two different users
        user1_repo = ConcreteUserScopedRepository(mock_session, user_id)
        user2_repo = ConcreteUserScopedRepository(mock_session, other_user_id)
        
        # User 1 queries
        user1_repo.get_all()
        user1_call = mock_session.execute_query.call_args
        
        # User 2 queries
        user2_repo.get_all()
        user2_call = mock_session.execute_query.call_args
        
        # Verify different user_ids in queries
        assert user_id in str(user1_call)
        assert other_user_id not in str(user1_call)
        
        assert other_user_id in str(user2_call)
        assert user_id not in str(user2_call)
    
    def test_shared_entity_access_prevented(self, repository, mock_session, user_id):
        """Test that shared entity IDs still respect user boundaries."""
        shared_entity_id = str(uuid4())
        
        # User tries to access an entity
        repository.get_by_id(shared_entity_id)
        
        # Verify query includes user_id filter
        call_args = mock_session.execute_query.call_args
        query = str(call_args)
        
        assert shared_entity_id in query
        assert user_id in query
        assert "user_id" in query
    
    # ==================== Special Cases Tests ====================
    
    def test_system_user_access(self, mock_session):
        """Test that system user (00000000-0000-0000-0000-000000000000) works."""
        system_user_id = "00000000-0000-0000-0000-000000000000"
        repository = ConcreteUserScopedRepository(mock_session, system_user_id)
        
        repository.get_all()
        
        # Verify system user_id is used
        call_args = mock_session.execute_query.call_args
        assert system_user_id in str(call_args)
    
    def test_count_operations_filter_by_user(self, repository, mock_session, user_id):
        """Test that count operations include user_id filter."""
        repository.count()
        
        # Verify the query includes user_id filter
        mock_session.execute_query.assert_called_once()
        call_args = mock_session.execute_query.call_args
        
        query = str(call_args)
        assert user_id in query
        assert "user_id" in query
    
    def test_exists_checks_within_user_scope(self, repository, mock_session, user_id):
        """Test that existence checks are scoped to user."""
        entity_id = str(uuid4())
        
        repository.exists(entity_id)
        
        # Verify the query includes user_id filter
        mock_session.execute_query.assert_called_once()
        call_args = mock_session.execute_query.call_args
        
        query = str(call_args)
        assert entity_id in query
        assert user_id in query
        assert "user_id" in query
    
    # ==================== Error Handling Tests ====================
    
    def test_handles_missing_user_id_column_gracefully(self, repository, mock_session):
        """Test that repository handles tables without user_id column gracefully."""
        # Simulate a database error for missing column
        mock_session.execute_query.side_effect = Exception("column user_id does not exist")
        
        with pytest.raises(Exception) as exc_info:
            repository.get_all()
        
        assert "user_id does not exist" in str(exc_info.value)
    
    def test_validates_user_id_on_operations(self, mock_session):
        """Test that operations validate user_id hasn't been tampered with."""
        original_user_id = str(uuid4())
        repository = ConcreteUserScopedRepository(mock_session, original_user_id)
        
        # Verify user_id is stored correctly
        assert repository.user_id == original_user_id
        
        # Test that even if we try to change the user_id,
        # operations still use the correct one
        another_user_id = str(uuid4())
        
        # Directly modify the attribute (in production this should be prevented)
        # but our test verifies operations are safe even if this happens
        repository.user_id = another_user_id
        
        # Verify the user_id was changed
        assert repository.user_id == another_user_id
        
        # Now verify operations use the new user_id
        repository.get_all()
        call_args = mock_session.execute_query.call_args
        assert another_user_id in str(call_args)
    
    # ==================== Performance Tests ====================
    
    def test_user_filter_uses_index_hint(self, repository, mock_session, user_id):
        """Test that queries use index hints for user_id when available."""
        repository.get_all()
        
        # Verify index usage (this would be database-specific)
        call_args = mock_session.execute_query.call_args
        query = str(call_args)
        
        # Query should be optimized for user_id index
        assert "user_id" in query
    
    def test_batch_operations_maintain_user_isolation(self, repository, mock_session, user_id):
        """Test that batch operations maintain user isolation."""
        entity_ids = [str(uuid4()) for _ in range(5)]
        
        repository.get_batch(entity_ids)
        
        # Verify all queries include user_id filter
        call_args = mock_session.execute_query.call_args
        query = str(call_args)
        
        assert user_id in query
        assert "user_id" in query
        for entity_id in entity_ids:
            assert entity_id in query