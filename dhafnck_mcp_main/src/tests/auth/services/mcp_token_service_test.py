"""
Test Suite for MCP Token Service

Tests the MCP token service functionality including token generation,
validation, revocation, and cleanup operations with comprehensive coverage.
"""

import pytest
import asyncio
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import hashlib

from fastmcp.auth.services.mcp_token_service import MCPTokenService, MCPToken
from fastmcp.auth.models.api_token import ApiToken


@pytest.mark.unit
class TestMCPTokenService:
    """Test suite for MCPTokenService"""
    
    @pytest.fixture
    def service(self):
        """Create service instance"""
        service = MCPTokenService()
        # Initialize the tokens dictionary for testing
        service._tokens = {}
        return service
    
    @pytest.fixture
    def mock_session(self):
        """Create mock database session"""
        session = Mock()
        session.execute = Mock()
        session.commit = Mock()
        session.__enter__ = Mock(return_value=session)
        session.__exit__ = Mock(return_value=None)
        return session
    
    @pytest.mark.asyncio
    async def test_generate_mcp_token_from_user_id_basic(self, service):
        """Test basic MCP token generation"""
        token = await service.generate_mcp_token_from_user_id(
            user_id="user123",
            email="test@example.com",
            expires_in_hours=24
        )
        
        assert isinstance(token, MCPToken)
        assert token.user_id == "user123"
        assert token.email == "test@example.com"
        assert token.token.startswith("mcp_")
        assert len(token.token) == 68  # mcp_ (4 chars) + 64 hex chars
        assert token.is_active is True
        assert token.created_at is not None
        assert token.expires_at is not None
        assert token.expires_at > token.created_at
        
        # Verify token is stored
        assert token.token in service._tokens
        assert service._tokens[token.token] == token
    
    @pytest.mark.asyncio
    async def test_generate_mcp_token_with_metadata(self, service):
        """Test MCP token generation with metadata"""
        metadata = {"source": "test", "version": 1}
        
        token = await service.generate_mcp_token_from_user_id(
            user_id="user456",
            expires_in_hours=48,
            metadata=metadata
        )
        
        assert token.metadata == metadata
        assert token.email is None  # Not provided
        
        # Check expiration is set correctly
        expected_expiry = token.created_at + timedelta(hours=48)
        assert abs((token.expires_at - expected_expiry).total_seconds()) < 1
    
    @pytest.mark.asyncio
    async def test_validate_mcp_token_success(self, service):
        """Test successful token validation"""
        # Generate a token first
        original_token = await service.generate_mcp_token_from_user_id(
            user_id="user789",
            email="valid@example.com",
            expires_in_hours=1
        )
        
        # Mock the database update
        with patch('fastmcp.auth.services.mcp_token_service.get_session') as mock_get_session:
            mock_session = Mock()
            mock_result = Mock()
            mock_result.rowcount = 1
            mock_session.execute.return_value = mock_result
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            mock_get_session.return_value = mock_session
            
            # Validate the token
            validated_token = await service.validate_mcp_token(original_token.token)
            
            assert validated_token is not None
            assert validated_token.user_id == "user789"
            assert validated_token.email == "valid@example.com"
            assert validated_token.is_active is True
            
            # Verify database update was called
            mock_session.execute.assert_called_once()
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_mcp_token_invalid_format(self, service):
        """Test validation with invalid token format"""
        result = await service.validate_mcp_token("invalid_token")
        assert result is None
        
        result = await service.validate_mcp_token("")
        assert result is None
        
        result = await service.validate_mcp_token(None)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_mcp_token_not_found(self, service):
        """Test validation with non-existent token"""
        result = await service.validate_mcp_token("mcp_nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_mcp_token_inactive(self, service):
        """Test validation with inactive token"""
        # Create and deactivate a token
        token = await service.generate_mcp_token_from_user_id(user_id="user_inactive")
        service._tokens[token.token].is_active = False
        
        result = await service.validate_mcp_token(token.token)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_mcp_token_expired(self, service):
        """Test validation with expired token"""
        # Create an expired token
        token = await service.generate_mcp_token_from_user_id(user_id="user_expired")
        service._tokens[token.token].expires_at = datetime.now(UTC) - timedelta(hours=1)
        
        # Mock database session
        with patch('fastmcp.auth.services.mcp_token_service.get_session'):
            result = await service.validate_mcp_token(token.token)
            assert result is None
            
            # Verify token was removed
            assert token.token not in service._tokens
    
    @pytest.mark.asyncio
    async def test_update_token_usage_success(self, service):
        """Test successful token usage update"""
        token = "mcp_test_token"
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        with patch('fastmcp.auth.services.mcp_token_service.get_session') as mock_get_session:
            mock_session = Mock()
            mock_result = Mock()
            mock_result.rowcount = 1
            mock_session.execute.return_value = mock_result
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            mock_get_session.return_value = mock_session
            
            await service._update_token_usage(token)
            
            # Verify database update
            mock_session.execute.assert_called_once()
            mock_session.commit.assert_called_once()
            
            # Check the update statement
            stmt = mock_session.execute.call_args[0][0]
            # Verify it's updating the right fields
            assert 'usage_count' in str(stmt)
            assert 'last_used_at' in str(stmt)
    
    @pytest.mark.asyncio
    async def test_update_token_usage_not_found(self, service):
        """Test token usage update when token not found in database"""
        token = "mcp_not_in_db"
        
        with patch('fastmcp.auth.services.mcp_token_service.get_session') as mock_get_session:
            mock_session = Mock()
            mock_result = Mock()
            mock_result.rowcount = 0
            mock_session.execute.return_value = mock_result
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            mock_get_session.return_value = mock_session
            
            # Should not raise exception
            await service._update_token_usage(token)
            
            mock_session.execute.assert_called_once()
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_token_usage_error(self, service):
        """Test token usage update error handling"""
        token = "mcp_error_token"
        
        with patch('fastmcp.auth.services.mcp_token_service.get_session') as mock_get_session:
            mock_session = Mock()
            mock_session.execute.side_effect = Exception("Database error")
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            mock_get_session.return_value = mock_session
            
            # Should not raise exception
            await service._update_token_usage(token)
    
    @pytest.mark.asyncio
    async def test_revoke_user_tokens_success(self, service):
        """Test successful user token revocation"""
        # Create multiple tokens for the same user
        user_id = "user_revoke"
        tokens = []
        for i in range(3):
            token = await service.generate_mcp_token_from_user_id(
                user_id=user_id,
                email=f"test{i}@example.com"
            )
            tokens.append(token)
        
        # Create a token for different user
        other_token = await service.generate_mcp_token_from_user_id(
            user_id="other_user",
            email="other@example.com"
        )
        
        # Revoke tokens for first user
        result = await service.revoke_user_tokens(user_id)
        
        assert result is True
        
        # Verify tokens were removed
        for token in tokens:
            assert token.token not in service._tokens
        
        # Verify other user's token remains
        assert other_token.token in service._tokens
        assert service._tokens[other_token.token].is_active is True
    
    @pytest.mark.asyncio
    async def test_revoke_user_tokens_no_tokens(self, service):
        """Test revoking tokens when user has none"""
        result = await service.revoke_user_tokens("user_no_tokens")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_revoke_user_tokens_already_inactive(self, service):
        """Test revoking already inactive tokens"""
        # Create an inactive token
        token = await service.generate_mcp_token_from_user_id(user_id="user_inactive")
        service._tokens[token.token].is_active = False
        
        result = await service.revoke_user_tokens("user_inactive")
        assert result is False  # No active tokens to revoke
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_tokens(self, service):
        """Test expired token cleanup"""
        # Create mix of valid and expired tokens
        valid_tokens = []
        expired_tokens = []
        
        # Valid tokens
        for i in range(2):
            token = await service.generate_mcp_token_from_user_id(
                user_id=f"user_valid_{i}",
                expires_in_hours=24
            )
            valid_tokens.append(token)
        
        # Expired tokens
        for i in range(3):
            token = await service.generate_mcp_token_from_user_id(
                user_id=f"user_expired_{i}",
                expires_in_hours=0
            )
            # Manually set to expired
            service._tokens[token.token].expires_at = datetime.now(UTC) - timedelta(hours=1)
            expired_tokens.append(token)
        
        # Run cleanup
        cleaned = await service.cleanup_expired_tokens()
        
        assert cleaned == 3
        
        # Verify expired tokens removed
        for token in expired_tokens:
            assert token.token not in service._tokens
        
        # Verify valid tokens remain
        for token in valid_tokens:
            assert token.token in service._tokens
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_tokens_none_expired(self, service):
        """Test cleanup when no tokens are expired"""
        # Create only valid tokens
        for i in range(3):
            await service.generate_mcp_token_from_user_id(
                user_id=f"user_{i}",
                expires_in_hours=24
            )
        
        cleaned = await service.cleanup_expired_tokens()
        assert cleaned == 0
        assert len(service._tokens) == 3
    
    def test_get_token_stats(self, service):
        """Test getting token statistics"""
        # Start with empty service
        stats = service.get_token_stats()
        assert stats["total_tokens"] == 0
        assert stats["active_tokens"] == 0
        assert stats["expired_tokens"] == 0
        assert stats["service_status"] == "running"
        assert stats["storage_type"] == "in-memory"
        
        # Add some tokens
        asyncio.run(self._setup_tokens_for_stats(service))
        
        stats = service.get_token_stats()
        assert stats["total_tokens"] == 5
        assert stats["active_tokens"] == 2
        assert stats["expired_tokens"] == 3
    
    async def _setup_tokens_for_stats(self, service):
        """Helper to set up tokens for stats testing"""
        # Active tokens
        for i in range(2):
            await service.generate_mcp_token_from_user_id(
                user_id=f"active_{i}",
                expires_in_hours=24
            )
        
        # Expired tokens
        for i in range(2):
            token = await service.generate_mcp_token_from_user_id(
                user_id=f"expired_{i}"
            )
            service._tokens[token.token].expires_at = datetime.now(UTC) - timedelta(hours=1)
        
        # Inactive token
        token = await service.generate_mcp_token_from_user_id(user_id="inactive")
        service._tokens[token.token].is_active = False
    
    @pytest.mark.asyncio
    async def test_get_user_tokens(self, service):
        """Test getting tokens for a specific user"""
        user_id = "test_user"
        
        # Create tokens for the user
        active_token = await service.generate_mcp_token_from_user_id(
            user_id=user_id,
            email="active@example.com",
            expires_in_hours=24
        )
        
        expired_token = await service.generate_mcp_token_from_user_id(
            user_id=user_id,
            email="expired@example.com"
        )
        service._tokens[expired_token.token].expires_at = datetime.now(UTC) - timedelta(hours=1)
        
        # Create token for different user
        await service.generate_mcp_token_from_user_id(
            user_id="other_user",
            email="other@example.com"
        )
        
        # Get user tokens
        user_tokens = await service.get_user_tokens(user_id)
        
        assert len(user_tokens) == 2
        
        # Check active token
        active_found = False
        expired_found = False
        
        for token in user_tokens:
            if token.email == "active@example.com":
                assert token.is_active is True
                active_found = True
            elif token.email == "expired@example.com":
                assert token.is_active is False  # Should be marked inactive
                expired_found = True
        
        assert active_found and expired_found
    
    @pytest.mark.asyncio
    async def test_get_user_tokens_no_tokens(self, service):
        """Test getting tokens when user has none"""
        tokens = await service.get_user_tokens("user_with_no_tokens")
        assert tokens == []
    
    @pytest.mark.asyncio
    async def test_concurrent_token_operations(self, service):
        """Test concurrent token generation and validation"""
        user_id = "concurrent_user"
        
        # Generate multiple tokens concurrently
        tasks = []
        for i in range(5):
            task = service.generate_mcp_token_from_user_id(
                user_id=user_id,
                email=f"test{i}@example.com",
                expires_in_hours=24
            )
            tasks.append(task)
        
        tokens = await asyncio.gather(*tasks)
        
        # Verify all tokens were created
        assert len(tokens) == 5
        assert len(service._tokens) == 5
        
        # Verify each token is unique
        token_strings = [t.token for t in tokens]
        assert len(set(token_strings)) == 5
        
        # Validate tokens concurrently
        with patch('fastmcp.auth.services.mcp_token_service.get_session'):
            validation_tasks = []
            for token in tokens:
                task = service.validate_mcp_token(token.token)
                validation_tasks.append(task)
            
            validated = await asyncio.gather(*validation_tasks)
            
            # All should be valid
            assert all(t is not None for t in validated)
            assert all(t.user_id == user_id for t in validated)
    
    @pytest.mark.asyncio
    async def test_token_expiration_edge_cases(self, service):
        """Test edge cases around token expiration"""
        # Token that expires exactly now
        token1 = await service.generate_mcp_token_from_user_id(user_id="user1")
        service._tokens[token1.token].expires_at = datetime.now(UTC)
        
        # Token with no expiration
        token2 = await service.generate_mcp_token_from_user_id(user_id="user2")
        service._tokens[token2.token].expires_at = None
        
        with patch('fastmcp.auth.services.mcp_token_service.get_session'):
            # Token expiring now should be invalid
            result1 = await service.validate_mcp_token(token1.token)
            assert result1 is None
            
            # Token with no expiration should be valid
            result2 = await service.validate_mcp_token(token2.token)
            assert result2 is not None
            assert result2.user_id == "user2"


@pytest.mark.unit
@pytest.mark.asyncio
class TestMCPTokenServiceIntegration:
    """Integration tests for MCPTokenService"""
    
    @pytest.fixture
    def service(self):
        """Create service instance for integration tests"""
        service = MCPTokenService()
        service._tokens = {}
        return service
    
    async def test_complete_token_lifecycle(self, service):
        """Test complete token lifecycle from creation to expiration"""
        user_id = "lifecycle_user"
        email = "lifecycle@example.com"
        
        # 1. Generate token
        token = await service.generate_mcp_token_from_user_id(
            user_id=user_id,
            email=email,
            expires_in_hours=1,
            metadata={"test": "lifecycle"}
        )
        
        assert token.is_active is True
        initial_token_count = len(service._tokens)
        
        # 2. Validate token (mock database)
        with patch('fastmcp.auth.services.mcp_token_service.get_session'):
            validated = await service.validate_mcp_token(token.token)
            assert validated is not None
            assert validated.user_id == user_id
        
        # 3. Get user tokens
        user_tokens = await service.get_user_tokens(user_id)
        assert len(user_tokens) == 1
        assert user_tokens[0].token == token.token
        
        # 4. Get stats
        stats = service.get_token_stats()
        assert stats["total_tokens"] == initial_token_count
        assert stats["active_tokens"] == 1
        assert stats["expired_tokens"] == 0
        
        # 5. Expire the token manually
        service._tokens[token.token].expires_at = datetime.now(UTC) - timedelta(minutes=1)
        
        # 6. Validate expired token
        with patch('fastmcp.auth.services.mcp_token_service.get_session'):
            validated = await service.validate_mcp_token(token.token)
            assert validated is None
        
        # Token should be removed after validation attempt
        assert token.token not in service._tokens
        
        # 7. Cleanup should find no more expired tokens
        cleaned = await service.cleanup_expired_tokens()
        assert cleaned == 0
    
    async def test_multiple_users_token_management(self, service):
        """Test token management across multiple users"""
        users = ["alice", "bob", "charlie"]
        tokens_per_user = {}
        
        # Generate tokens for each user
        for user in users:
            tokens = []
            for i in range(3):
                token = await service.generate_mcp_token_from_user_id(
                    user_id=user,
                    email=f"{user}{i}@example.com",
                    expires_in_hours=24 if i < 2 else 0  # Last one expires immediately
                )
                tokens.append(token)
            tokens_per_user[user] = tokens
        
        # Set some tokens as expired
        for user in users:
            last_token = tokens_per_user[user][-1]
            service._tokens[last_token.token].expires_at = datetime.now(UTC) - timedelta(hours=1)
        
        # Get stats
        stats = service.get_token_stats()
        assert stats["total_tokens"] == 9  # 3 users * 3 tokens
        assert stats["active_tokens"] == 6  # 2 active per user
        assert stats["expired_tokens"] == 3  # 1 expired per user
        
        # Revoke all tokens for bob
        revoked = await service.revoke_user_tokens("bob")
        assert revoked is True
        
        # Verify only bob's tokens were removed
        bob_tokens_remain = sum(1 for t in service._tokens.values() if t.user_id == "bob")
        assert bob_tokens_remain == 0
        
        alice_tokens = await service.get_user_tokens("alice")
        assert len(alice_tokens) == 3
        
        # Cleanup expired tokens
        cleaned = await service.cleanup_expired_tokens()
        assert cleaned == 2  # Only alice and charlie's expired tokens
        
        # Final verification
        remaining_tokens = len(service._tokens)
        assert remaining_tokens == 4  # 2 for alice + 2 for charlie