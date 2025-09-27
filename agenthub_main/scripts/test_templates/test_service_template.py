"""Test template for service with user context."""
import pytest
from unittest.mock import Mock, patch
from uuid import uuid4

class TestServiceUserContext:
    """Test service properly handles user context."""
    
    def test_service_passes_user_id_to_repository(self):
        """Test that service passes user_id to repository."""
        # Arrange
        user_id = str(uuid4())
        mock_repo = Mock()
        service = MyService(repository=mock_repo, user_id=user_id)
        
        # Act
        service.create_item(data={"name": "test"})
        
        # Assert
        mock_repo.create.assert_called_once()
        call_args = mock_repo.create.call_args
        assert "user_id" in call_args.kwargs or user_id in call_args.args
    
    def test_service_validates_user_context(self):
        """Test that service validates user context."""
        # Test implementation here
        pass
