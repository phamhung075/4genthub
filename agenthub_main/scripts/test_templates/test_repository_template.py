"""Test template for repository with user isolation."""
import pytest
from unittest.mock import Mock, patch
from uuid import uuid4

class TestRepositoryUserIsolation:
    """Test repository properly filters by user_id."""
    
    def test_create_with_user_id(self):
        """Test that created entities include user_id."""
        # Arrange
        user_id = str(uuid4())
        repository = MyRepository(user_id=user_id)
        
        # Act
        entity = repository.create(data={"name": "test"})
        
        # Assert
        assert entity.user_id == user_id
    
    def test_get_filters_by_user(self):
        """Test that get operations filter by user_id."""
        # Arrange
        user_id = str(uuid4())
        other_user_id = str(uuid4())
        repository = MyRepository(user_id=user_id)
        
        # Create entities for both users
        entity1 = repository.create(data={"name": "user1_item"})
        
        # Switch to other user
        other_repo = MyRepository(user_id=other_user_id)
        entity2 = other_repo.create(data={"name": "user2_item"})
        
        # Act
        user1_items = repository.get_all()
        
        # Assert
        assert len(user1_items) == 1
        assert user1_items[0].user_id == user_id
    
    def test_update_prevents_cross_user_access(self):
        """Test that users cannot update other users' data."""
        # Test implementation here
        pass
    
    def test_delete_prevents_cross_user_access(self):
        """Test that users cannot delete other users' data."""
        # Test implementation here
        pass
