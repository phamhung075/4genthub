"""
Unit tests for MCPTokenService.

This module tests the MCP token generation, validation, and management functionality.
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import patch, MagicMock
from fastmcp.auth.services.mcp_token_service import MCPTokenService, MCPToken, mcp_token_service


class TestMCPTokenService:
    """Test suite for MCPTokenService."""
    
    @pytest.fixture
    def service(self):
        """Create a fresh MCPTokenService instance."""
        return MCPTokenService()
    
    @pytest.fixture
    def sample_token(self):
        """Create a sample MCPToken for testing."""
        return MCPToken(
            token="mcp_test_token_123",
            user_id="user_123",
            email="test@example.com",
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            metadata={"key": "value"},
            is_active=True
        )
    
    # Token Generation Tests
    
    @pytest.mark.asyncio
    async def test_generate_mcp_token_basic(self, service):
        """Test basic MCP token generation."""
        # Act
        token = await service.generate_mcp_token_from_user_id(
            user_id="user_123",
            email="test@example.com"
        )
        
        # Assert
        assert token is not None
        assert token.token.startswith("mcp_")
        assert len(token.token) > 10  # Should have reasonable length
        assert token.user_id == "user_123"
        assert token.email == "test@example.com"
        assert token.is_active is True
        assert token.created_at is not None
        assert token.expires_at is not None
    
    @pytest.mark.asyncio
    async def test_generate_mcp_token_with_custom_expiration(self, service):
        """Test MCP token generation with custom expiration."""
        # Act
        token = await service.generate_mcp_token_from_user_id(
            user_id="user_456",
            expires_in_hours=48
        )
        
        # Assert
        expected_expiry = token.created_at + timedelta(hours=48)
        assert abs((token.expires_at - expected_expiry).total_seconds()) < 1
    
    @pytest.mark.asyncio
    async def test_generate_mcp_token_with_metadata(self, service):
        """Test MCP token generation with metadata."""
        # Arrange
        metadata = {"scope": "admin", "client": "web"}
        
        # Act
        token = await service.generate_mcp_token_from_user_id(
            user_id="user_789",
            metadata=metadata
        )
        
        # Assert
        assert token.metadata == metadata
    
    @pytest.mark.asyncio
    async def test_generate_mcp_token_stores_in_memory(self, service):
        """Test that generated tokens are stored in memory."""
        # Act
        token = await service.generate_mcp_token_from_user_id(
            user_id="user_abc"
        )
        
        # Assert
        assert token.token in service._tokens
        assert service._tokens[token.token] == token
    
    # Token Validation Tests
    
    @pytest.mark.asyncio
    async def test_validate_mcp_token_valid(self, service, sample_token):
        """Test validation of a valid MCP token."""
        # Arrange
        service._tokens[sample_token.token] = sample_token
        
        # Act
        result = await service.validate_mcp_token(sample_token.token)
        
        # Assert
        assert result is not None
        assert result == sample_token
    
    @pytest.mark.asyncio
    async def test_validate_mcp_token_not_found(self, service):
        """Test validation of a non-existent token."""
        # Act
        result = await service.validate_mcp_token("mcp_nonexistent")
        
        # Assert
        assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_mcp_token_invalid_format(self, service):
        """Test validation with invalid token format."""
        # Act
        result = await service.validate_mcp_token("invalid_token")
        
        # Assert
        assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_mcp_token_empty(self, service):
        """Test validation with empty token."""
        # Act
        result = await service.validate_mcp_token("")
        
        # Assert
        assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_mcp_token_inactive(self, service, sample_token):
        """Test validation of an inactive token."""
        # Arrange
        sample_token.is_active = False
        service._tokens[sample_token.token] = sample_token
        
        # Act
        result = await service.validate_mcp_token(sample_token.token)
        
        # Assert
        assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_mcp_token_expired(self, service):
        """Test validation of an expired token."""
        # Arrange
        expired_token = MCPToken(
            token="mcp_expired_token",
            user_id="user_exp",
            created_at=datetime.now(UTC) - timedelta(hours=25),
            expires_at=datetime.now(UTC) - timedelta(hours=1),
            is_active=True
        )
        service._tokens[expired_token.token] = expired_token
        
        # Act
        result = await service.validate_mcp_token(expired_token.token)
        
        # Assert
        assert result is None
        # Token should be removed after expiration
        assert expired_token.token not in service._tokens
    
    # Token Revocation Tests
    
    @pytest.mark.asyncio
    async def test_revoke_user_tokens_single(self, service):
        """Test revoking tokens for a user with one token."""
        # Arrange
        token = await service.generate_mcp_token_from_user_id("user_revoke")
        
        # Act
        result = await service.revoke_user_tokens("user_revoke")
        
        # Assert
        assert result is True
        assert token.token not in service._tokens
    
    @pytest.mark.asyncio
    async def test_revoke_user_tokens_multiple(self, service):
        """Test revoking multiple tokens for a user."""
        # Arrange
        token1 = await service.generate_mcp_token_from_user_id("user_multi")
        token2 = await service.generate_mcp_token_from_user_id("user_multi")
        token3 = await service.generate_mcp_token_from_user_id("other_user")
        
        # Act
        result = await service.revoke_user_tokens("user_multi")
        
        # Assert
        assert result is True
        assert token1.token not in service._tokens
        assert token2.token not in service._tokens
        assert token3.token in service._tokens  # Other user's token should remain
    
    @pytest.mark.asyncio
    async def test_revoke_user_tokens_no_tokens(self, service):
        """Test revoking tokens for a user with no tokens."""
        # Act
        result = await service.revoke_user_tokens("nonexistent_user")
        
        # Assert
        assert result is False
    
    @pytest.mark.asyncio
    async def test_revoke_user_tokens_already_inactive(self, service, sample_token):
        """Test revoking already inactive tokens."""
        # Arrange
        sample_token.is_active = False
        service._tokens[sample_token.token] = sample_token
        
        # Act
        result = await service.revoke_user_tokens(sample_token.user_id)
        
        # Assert
        assert result is False  # No active tokens to revoke
    
    # Cleanup Tests
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_tokens(self, service):
        """Test cleaning up expired tokens."""
        # Arrange
        # Create expired token
        expired_token = MCPToken(
            token="mcp_expired",
            user_id="user_exp",
            created_at=datetime.now(UTC) - timedelta(hours=25),
            expires_at=datetime.now(UTC) - timedelta(hours=1),
            is_active=True
        )
        service._tokens[expired_token.token] = expired_token
        
        # Create valid token
        valid_token = await service.generate_mcp_token_from_user_id("user_valid")
        
        # Act
        cleaned_count = await service.cleanup_expired_tokens()
        
        # Assert
        assert cleaned_count == 1
        assert expired_token.token not in service._tokens
        assert valid_token.token in service._tokens
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_tokens_none_expired(self, service):
        """Test cleanup when no tokens are expired."""
        # Arrange
        await service.generate_mcp_token_from_user_id("user_1")
        await service.generate_mcp_token_from_user_id("user_2")
        
        # Act
        cleaned_count = await service.cleanup_expired_tokens()
        
        # Assert
        assert cleaned_count == 0
        assert len(service._tokens) == 2
    
    # Statistics Tests
    
    def test_get_token_stats_empty(self, service):
        """Test getting stats when no tokens exist."""
        # Act
        stats = service.get_token_stats()
        
        # Assert
        assert stats["total_tokens"] == 0
        assert stats["active_tokens"] == 0
        assert stats["expired_tokens"] == 0
        assert stats["service_status"] == "running"
        assert stats["storage_type"] == "in-memory"
    
    def test_get_token_stats_with_tokens(self, service):
        """Test getting stats with various token states."""
        # Arrange
        # Active token
        active_token = MCPToken(
            token="mcp_active",
            user_id="user_1",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            is_active=True
        )
        service._tokens[active_token.token] = active_token
        
        # Expired token
        expired_token = MCPToken(
            token="mcp_expired",
            user_id="user_2",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
            is_active=True
        )
        service._tokens[expired_token.token] = expired_token
        
        # Inactive token
        inactive_token = MCPToken(
            token="mcp_inactive",
            user_id="user_3",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            is_active=False
        )
        service._tokens[inactive_token.token] = inactive_token
        
        # Act
        stats = service.get_token_stats()
        
        # Assert
        assert stats["total_tokens"] == 3
        assert stats["active_tokens"] == 1
        assert stats["expired_tokens"] == 2
    
    # Get User Tokens Tests
    
    @pytest.mark.asyncio
    async def test_get_user_tokens_single(self, service):
        """Test getting tokens for a user with one token."""
        # Arrange
        token = await service.generate_mcp_token_from_user_id("user_single")
        
        # Act
        user_tokens = await service.get_user_tokens("user_single")
        
        # Assert
        assert len(user_tokens) == 1
        assert user_tokens[0] == token
    
    @pytest.mark.asyncio
    async def test_get_user_tokens_multiple(self, service):
        """Test getting multiple tokens for a user."""
        # Arrange
        token1 = await service.generate_mcp_token_from_user_id("user_multi")
        token2 = await service.generate_mcp_token_from_user_id("user_multi")
        await service.generate_mcp_token_from_user_id("other_user")
        
        # Act
        user_tokens = await service.get_user_tokens("user_multi")
        
        # Assert
        assert len(user_tokens) == 2
        assert token1 in user_tokens
        assert token2 in user_tokens
    
    @pytest.mark.asyncio
    async def test_get_user_tokens_marks_expired(self, service):
        """Test that get_user_tokens marks expired tokens as inactive."""
        # Arrange
        expired_token = MCPToken(
            token="mcp_expired",
            user_id="user_exp",
            created_at=datetime.now(UTC) - timedelta(hours=25),
            expires_at=datetime.now(UTC) - timedelta(hours=1),
            is_active=True
        )
        service._tokens[expired_token.token] = expired_token
        
        # Act
        user_tokens = await service.get_user_tokens("user_exp")
        
        # Assert
        assert len(user_tokens) == 1
        assert user_tokens[0].is_active is False
    
    @pytest.mark.asyncio
    async def test_get_user_tokens_no_tokens(self, service):
        """Test getting tokens for a user with no tokens."""
        # Act
        user_tokens = await service.get_user_tokens("nonexistent_user")
        
        # Assert
        assert len(user_tokens) == 0


# Global Instance Test (moved outside class)
def test_global_mcp_token_service_instance():
    """Test that global service instance is available."""
    from fastmcp.auth.services.mcp_token_service import mcp_token_service, MCPTokenService as ImportedMCPTokenService
    
    assert mcp_token_service is not None
    assert isinstance(mcp_token_service, ImportedMCPTokenService)