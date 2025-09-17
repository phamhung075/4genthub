"""
Test Suite for Token Repository Implementation

Tests the infrastructure layer token repository with database operations,
error handling, and model compatibility.
"""

import pytest
from unittest.mock import Mock, MagicMock, create_autospec, AsyncMock
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from fastmcp.task_management.infrastructure.repositories.token_repository import TokenRepository
from fastmcp.task_management.infrastructure.database.models import APIToken
from fastmcp.auth.models.api_token import ApiToken


class TestTokenRepository:
    """Test suite for TokenRepository"""
    
    @pytest.fixture
    def mock_session(self):
        """Create mock database session"""
        session = create_autospec(Session, instance=True)
        # Set up query mock
        session.query = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        session.refresh = Mock()
        session.delete = Mock()
        return session
    
    @pytest.fixture
    def repository(self, mock_session):
        """Create repository instance with mock session"""
        return TokenRepository(mock_session)
    
    def create_mock_token(self, **kwargs):
        """Create a mock APIToken object"""
        token = Mock(spec=APIToken)
        token.id = kwargs.get('id', 'tok_12345')
        token.user_id = kwargs.get('user_id', 'user_123')
        token.name = kwargs.get('name', 'Test Token')
        token.token_hash = kwargs.get('token_hash', 'hash_abc123')
        token.scopes = kwargs.get('scopes', ['read', 'write'])
        token.expires_at = kwargs.get('expires_at', datetime.now(timezone.utc) + timedelta(days=30))
        token.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
        token.last_used_at = kwargs.get('last_used_at', None)
        token.usage_count = kwargs.get('usage_count', 0)
        token.rate_limit = kwargs.get('rate_limit', 1000)
        token.is_active = kwargs.get('is_active', True)
        token.token_metadata = kwargs.get('token_metadata', {})
        return token
    
    @pytest.mark.asyncio
    async def test_create_token_success(self, repository, mock_session):
        """Test successful token creation"""
        token_data = {
            'id': 'tok_new',
            'user_id': 'user_123',
            'name': 'New Token',
            'token_hash': 'hash_new',
            'scopes': ['read'],
            'expires_at': datetime.now(timezone.utc) + timedelta(days=7),
            'rate_limit': 500,
            'token_metadata': {'purpose': 'testing'}
        }
        
        # Mock successful creation
        mock_session.commit.return_value = None
        mock_session.refresh.return_value = None
        
        result = await repository.create_token(token_data)
        
        # Verify token was added to session
        assert mock_session.add.called
        added_token = mock_session.add.call_args[0][0]
        assert isinstance(added_token, APIToken)
        assert added_token.id == 'tok_new'
        assert added_token.user_id == 'user_123'
        assert added_token.name == 'New Token'
        
        # Verify commit and refresh were called
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_token_database_error(self, repository, mock_session):
        """Test token creation with database error"""
        token_data = {
            'id': 'tok_error',
            'user_id': 'user_123',
            'name': 'Error Token',
            'token_hash': 'hash_error'
        }
        
        # Mock database error
        mock_session.commit.side_effect = SQLAlchemyError("Database error")
        
        result = await repository.create_token(token_data)
        
        assert result is None
        mock_session.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_token_found(self, repository, mock_session):
        """Test getting existing token"""
        mock_token = self.create_mock_token()
        
        # Mock query chain
        query_mock = Mock()
        filter_mock = Mock()
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = mock_token
        mock_session.query.return_value = query_mock
        
        result = await repository.get_token('tok_12345', 'user_123')
        
        assert result == mock_token
        mock_session.query.assert_called_with(APIToken)
    
    @pytest.mark.asyncio
    async def test_get_token_not_found(self, repository, mock_session):
        """Test getting non-existent token"""
        # Mock empty result
        query_mock = Mock()
        filter_mock = Mock()
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = None
        mock_session.query.return_value = query_mock
        
        result = await repository.get_token('tok_invalid', 'user_123')
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_token_by_id_api_token(self, repository, mock_session):
        """Test getting token by ID from APIToken model"""
        mock_token = self.create_mock_token()
        
        # Mock query for APIToken
        query_mock = Mock()
        filter_mock = Mock()
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = mock_token
        mock_session.query.return_value = query_mock
        
        result = await repository.get_token_by_id('tok_12345')
        
        assert result == mock_token
        # Should query APIToken first
        mock_session.query.assert_any_call(APIToken)
    
    @pytest.mark.asyncio
    async def test_get_token_by_id_fallback(self, repository, mock_session):
        """Test fallback to ApiToken model when not found in APIToken"""
        # Create mock for fallback model
        mock_fallback_token = Mock(spec=ApiToken)
        mock_fallback_token.id = 'tok_fallback'
        
        # Setup query mocks
        call_count = 0
        def query_side_effect(model):
            nonlocal call_count
            query_mock = Mock()
            filter_mock = Mock()
            query_mock.filter.return_value = filter_mock
            
            if call_count == 0:  # First call (APIToken)
                filter_mock.first.return_value = None
            else:  # Second call (ApiToken)
                filter_mock.first.return_value = mock_fallback_token
            
            call_count += 1
            return query_mock
        
        mock_session.query.side_effect = query_side_effect
        
        result = await repository.get_token_by_id('tok_fallback')
        
        assert result == mock_fallback_token
        # Should have queried both models
        assert mock_session.query.call_count == 2
    
    @pytest.mark.asyncio
    async def test_get_user_tokens_with_pagination(self, repository, mock_session):
        """Test getting user tokens with pagination"""
        mock_tokens = [
            self.create_mock_token(id=f'tok_{i}', name=f'Token {i}')
            for i in range(5)
        ]
        
        # Mock query chain
        query_mock = Mock()
        filter_mock = Mock()
        order_mock = Mock()
        offset_mock = Mock()
        limit_mock = Mock()
        
        query_mock.filter.return_value = filter_mock
        filter_mock.order_by.return_value = order_mock
        order_mock.offset.return_value = offset_mock
        offset_mock.limit.return_value = limit_mock
        limit_mock.all.return_value = mock_tokens[1:4]  # Skip 1, limit 3
        
        mock_session.query.return_value = query_mock
        
        result = await repository.get_user_tokens('user_123', skip=1, limit=3)
        
        assert len(result) == 3
        assert result[0].id == 'tok_1'
        offset_mock.limit.assert_called_with(3)
        order_mock.offset.assert_called_with(1)
    
    @pytest.mark.asyncio
    async def test_get_user_tokens_error(self, repository, mock_session):
        """Test handling error when getting user tokens"""
        mock_session.query.side_effect = SQLAlchemyError("Query error")
        
        result = await repository.get_user_tokens('user_123')
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_count_user_tokens(self, repository, mock_session):
        """Test counting user tokens"""
        # Mock query chain
        query_mock = Mock()
        filter_mock = Mock()
        query_mock.filter.return_value = filter_mock
        filter_mock.count.return_value = 10
        mock_session.query.return_value = query_mock
        
        result = await repository.count_user_tokens('user_123')
        
        assert result == 10
        filter_mock.count.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_revoke_token_success(self, repository, mock_session):
        """Test successful token revocation"""
        mock_token = self.create_mock_token(is_active=True)
        
        # Mock get_token to return the token (async method)
        repository.get_token = AsyncMock(return_value=mock_token)
        
        result = await repository.revoke_token('tok_12345', 'user_123')
        
        assert result is True
        assert mock_token.is_active is False
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_revoke_token_not_found(self, repository, mock_session):
        """Test revoking non-existent token"""
        repository.get_token = AsyncMock(return_value=None)
        
        result = await repository.revoke_token('tok_invalid', 'user_123')
        
        assert result is False
        mock_session.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_revoke_token_error(self, repository, mock_session):
        """Test handling error during revocation"""
        mock_token = self.create_mock_token()
        repository.get_token = AsyncMock(return_value=mock_token)
        mock_session.commit.side_effect = SQLAlchemyError("Commit error")
        
        result = await repository.revoke_token('tok_12345', 'user_123')
        
        assert result is False
        mock_session.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reactivate_token_api_token_model(self, repository, mock_session):
        """Test reactivating token from APIToken model"""
        mock_token = self.create_mock_token(is_active=False)
        
        # Mock query
        query_mock = Mock()
        filter_mock = Mock()
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = mock_token
        mock_session.query.return_value = query_mock
        
        result = await repository.reactivate_token('tok_12345', 'user_123')
        
        assert result is True
        assert mock_token.is_active is True
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reactivate_token_fallback_model(self, repository, mock_session):
        """Test reactivating token from fallback ApiToken model"""
        mock_fallback_token = Mock(spec=ApiToken)
        mock_fallback_token.is_active = False
        
        # Setup query mocks for fallback
        call_count = 0
        def query_side_effect(model):
            nonlocal call_count
            query_mock = Mock()
            filter_mock = Mock()
            query_mock.filter.return_value = filter_mock
            
            if call_count == 0:  # APIToken query
                filter_mock.first.return_value = None
            else:  # ApiToken query
                filter_mock.first.return_value = mock_fallback_token
            
            call_count += 1
            return query_mock
        
        mock_session.query.side_effect = query_side_effect
        
        result = await repository.reactivate_token('tok_12345', 'user_123')
        
        assert result is True
        assert mock_fallback_token.is_active is True
    
    @pytest.mark.asyncio
    async def test_delete_token_success(self, repository, mock_session):
        """Test successful token deletion"""
        mock_token = self.create_mock_token()
        
        # Mock query
        query_mock = Mock()
        filter_mock = Mock()
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = mock_token
        mock_session.query.return_value = query_mock
        
        result = await repository.delete_token('tok_12345', 'user_123')
        
        assert result is True
        mock_session.delete.assert_called_once_with(mock_token)
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_token_not_found(self, repository, mock_session):
        """Test deleting non-existent token"""
        # Mock empty results for both models
        query_mock = Mock()
        filter_mock = Mock()
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = None
        mock_session.query.return_value = query_mock
        
        result = await repository.delete_token('tok_invalid', 'user_123')
        
        assert result is False
        mock_session.delete.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_update_token_usage_success(self, repository, mock_session):
        """Test updating token usage statistics"""
        mock_token = self.create_mock_token(usage_count=5, last_used_at=None)
        
        # Mock query
        query_mock = Mock()
        filter_mock = Mock()
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = mock_token
        mock_session.query.return_value = query_mock
        
        result = await repository.update_token_usage('tok_12345')
        
        assert result is True
        assert mock_token.usage_count == 6
        assert mock_token.last_used_at is not None
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_token_usage_not_found(self, repository, mock_session):
        """Test updating usage for non-existent token"""
        # Mock empty result
        query_mock = Mock()
        filter_mock = Mock()
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = None
        mock_session.query.return_value = query_mock
        
        result = await repository.update_token_usage('tok_invalid')
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_tokens(self, repository, mock_session):
        """Test cleaning up expired tokens"""
        expiry_date = datetime.now(timezone.utc)
        
        # Mock query chain
        query_mock = Mock()
        filter_mock = Mock()
        filter_mock2 = Mock()
        
        query_mock.filter.return_value = filter_mock
        filter_mock.count.return_value = 5  # 5 expired tokens
        filter_mock.delete.return_value = None
        
        # Different mock for delete query
        query_mock2 = Mock()
        query_mock2.filter.return_value = filter_mock2
        filter_mock2.delete.return_value = None
        
        # First call for count, second for delete
        mock_session.query.side_effect = [query_mock, query_mock2]
        
        result = await repository.cleanup_expired_tokens(expiry_date)
        
        assert result == 5
        filter_mock.count.assert_called_once()
        filter_mock2.delete.assert_called_once()
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_tokens_error(self, repository, mock_session):
        """Test error handling during cleanup"""
        expiry_date = datetime.now(timezone.utc)
        
        mock_session.query.side_effect = SQLAlchemyError("Cleanup error")
        
        result = await repository.cleanup_expired_tokens(expiry_date)
        
        assert result == 0
        mock_session.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_repository_with_none_values(self, repository, mock_session):
        """Test handling None values in token data"""
        token_data = {
            'id': 'tok_minimal',
            'user_id': 'user_123',
            'name': 'Minimal Token',
            'token_hash': 'hash_minimal',
            'scopes': None,  # Should default to []
            'expires_at': None,
            'rate_limit': None,  # Should default to 1000
            'token_metadata': None  # Should default to {}
        }
        
        result = await repository.create_token(token_data)
        
        # Verify defaults were applied
        added_token = mock_session.add.call_args[0][0]
        assert added_token.scopes == []
        assert added_token.rate_limit == 1000
        assert added_token.token_metadata == {}


class TestTokenRepositoryIntegration:
    """Integration tests for TokenRepository with real-like behavior"""
    
    @pytest.fixture
    def integrated_session(self):
        """Create a more realistic mock session"""
        session = Mock(spec=Session)
        
        # Storage for tokens
        token_storage = {}
        
        def add_token(token):
            token_storage[token.id] = token
        
        def query_tokens(model):
            query = Mock()
            
            def filter_tokens(*args):
                # Simple filter implementation
                filter_mock = Mock()
                
                def first():
                    # Find first matching token
                    for token in token_storage.values():
                        return token
                    return None
                
                def all():
                    return list(token_storage.values())
                
                def count():
                    return len(token_storage)
                
                def delete(**kwargs):
                    token_storage.clear()
                
                filter_mock.first = first
                filter_mock.all = all
                filter_mock.count = count
                filter_mock.delete = delete
                filter_mock.order_by = lambda *args: filter_mock
                filter_mock.offset = lambda n: filter_mock
                filter_mock.limit = lambda n: filter_mock
                
                return filter_mock
            
            query.filter = filter_tokens
            return query
        
        session.add = add_token
        session.query = query_tokens
        session.commit = Mock()
        session.rollback = Mock()
        session.refresh = Mock()
        
        return session
    
    @pytest.mark.asyncio
    async def test_token_lifecycle(self, integrated_session):
        """Test complete token lifecycle"""
        repository = TokenRepository(integrated_session)
        
        # Create token
        token_data = {
            'id': 'tok_lifecycle',
            'user_id': 'user_test',
            'name': 'Lifecycle Token',
            'token_hash': 'hash_lifecycle',
            'scopes': ['read', 'write'],
            'rate_limit': 1000
        }
        
        created = await repository.create_token(token_data)
        assert created is not None
        
        # Get token
        fetched = await repository.get_token_by_id('tok_lifecycle')
        assert fetched.id == 'tok_lifecycle'
        
        # Update usage
        updated = await repository.update_token_usage('tok_lifecycle')
        assert updated is True
        
        # Revoke token
        revoked = await repository.revoke_token('tok_lifecycle', 'user_test')
        assert revoked is True
        
        # Reactivate token
        reactivated = await repository.reactivate_token('tok_lifecycle', 'user_test')
        assert reactivated is True