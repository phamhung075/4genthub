"""
Unit tests for TokenValidator.

This module tests the token validation, rate limiting, and security monitoring functionality.
"""

import pytest
import time
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from collections import deque

from fastmcp.auth.token_validator import (
    TokenValidator, 
    TokenValidationError, 
    RateLimitError,
    RateLimitConfig
)
from fastmcp.auth.supabase_client import TokenInfo


class TestTokenValidator:
    """Test suite for TokenValidator."""
    
    @pytest.fixture
    def rate_config(self):
        """Create a test rate limit configuration."""
        return RateLimitConfig(
            requests_per_minute=10,
            requests_per_hour=100,
            burst_limit=5,
            window_size=60
        )
    
    @pytest.fixture
    def validator(self, rate_config):
        """Create a TokenValidator instance with test config."""
        return TokenValidator(rate_limit_config=rate_config)
    
    @pytest.fixture
    def sample_token_info(self):
        """Create a sample TokenInfo for testing."""
        return TokenInfo(
            token_hash="hashed_token_123",
            user_id="user_123",
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            usage_count=5,
            last_used=datetime.now(UTC)
        )
    
    # Initialization Tests
    
    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        validator = TokenValidator()
        
        assert validator.rate_config.requests_per_minute == 100
        assert validator.rate_config.requests_per_hour == 1000
        assert validator.rate_config.burst_limit == 20
        assert validator._cache_ttl == 300
    
    def test_init_with_custom_config(self, rate_config):
        """Test initialization with custom configuration."""
        validator = TokenValidator(rate_limit_config=rate_config)
        
        assert validator.rate_config.requests_per_minute == 10
        assert validator.rate_config.requests_per_hour == 100
        assert validator.rate_config.burst_limit == 5
    
    # Token Validation Tests
    
    @pytest.mark.asyncio
    async def test_validate_token_empty(self, validator):
        """Test validation with empty token."""
        with pytest.raises(TokenValidationError, match="Token is required"):
            await validator.validate_token("")
    
    @pytest.mark.asyncio
    async def test_validate_token_none(self, validator):
        """Test validation with None token."""
        with pytest.raises(TokenValidationError, match="Token is required"):
            await validator.validate_token(None)
    
    @pytest.mark.asyncio
    async def test_validate_token_strips_bearer_prefix(self, validator, sample_token_info):
        """Test that Bearer prefix is stripped from token."""
        with patch.object(validator, '_get_token_info', return_value=sample_token_info) as mock_get:
            with patch.object(validator, '_check_rate_limit'):
                with patch.object(validator.supabase_client, 'log_security_event'):
                    result = await validator.validate_token("Bearer test_token")
                    
                    # Verify token was stripped
                    mock_get.assert_called_once_with("test_token")
                    assert result == sample_token_info
    
    @pytest.mark.asyncio
    async def test_validate_token_success(self, validator, sample_token_info):
        """Test successful token validation."""
        with patch.object(validator, '_get_token_info', return_value=sample_token_info):
            with patch.object(validator, '_check_rate_limit'):
                with patch.object(validator.supabase_client, 'log_security_event') as mock_log:
                    result = await validator.validate_token("test_token")
                    
                    assert result == sample_token_info
                    mock_log.assert_called_once()
                    call_args = mock_log.call_args[0]
                    assert call_args[0] == "token_validated"
    
    @pytest.mark.asyncio
    async def test_validate_token_invalid(self, validator):
        """Test validation with invalid token."""
        with patch.object(validator, '_get_token_info', return_value=None):
            with patch.object(validator, '_check_rate_limit'):
                with patch.object(validator, '_log_failed_attempt'):
                    with pytest.raises(TokenValidationError, match="Invalid or expired token"):
                        await validator.validate_token("invalid_token")
    
    @pytest.mark.asyncio
    async def test_validate_token_rate_limited(self, validator):
        """Test validation when rate limited."""
        with patch.object(validator, '_check_rate_limit', side_effect=RateLimitError("Too many requests")):
            with patch.object(validator, '_log_failed_attempt'):
                with pytest.raises(RateLimitError, match="Too many requests"):
                    await validator.validate_token("test_token")
    
    # Rate Limiting Tests
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_under_limit(self, validator):
        """Test rate limit check when under limit."""
        token_hash = "test_hash"
        
        # Add some requests but stay under limit
        current_time = time.time()
        validator._rate_limits[token_hash].extend([current_time - 30, current_time - 20, current_time - 10])
        
        # Should not raise
        await validator._check_rate_limit(token_hash)
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_minute_exceeded(self, validator):
        """Test rate limit when minute limit is exceeded."""
        token_hash = "test_hash"
        current_time = time.time()
        
        # Add requests exceeding minute limit (10 per minute)
        for i in range(11):
            validator._rate_limits[token_hash].append(current_time - i)
        
        with pytest.raises(RateLimitError, match="requests per minute"):
            await validator._check_rate_limit(token_hash)
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_burst_exceeded(self, validator):
        """Test rate limit when burst limit is exceeded."""
        token_hash = "test_hash"
        current_time = time.time()
        
        # Add requests exceeding burst limit (5 in 10 seconds)
        for i in range(6):
            validator._rate_limits[token_hash].append(current_time - i)
        
        with pytest.raises(RateLimitError, match="Burst limit exceeded"):
            await validator._check_rate_limit(token_hash)
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_removes_old_requests(self, validator):
        """Test that old requests are removed from rate limit tracking."""
        token_hash = "test_hash"
        current_time = time.time()
        
        # Add old requests (>1 hour ago)
        validator._rate_limits[token_hash].extend([
            current_time - 3700,  # Over 1 hour ago
            current_time - 3650,  # Over 1 hour ago
            current_time - 30     # Recent
        ])
        
        await validator._check_rate_limit(token_hash)
        
        # Old requests should be removed
        assert len(validator._rate_limits[token_hash]) == 2  # Recent + new request
    
    # Caching Tests
    
    @pytest.mark.asyncio
    async def test_get_token_info_uses_cache(self, validator, sample_token_info):
        """Test that valid cached tokens are returned from cache."""
        token = "test_token"
        token_hash = validator.supabase_client._hash_token(token)
        
        # Add to cache
        validator._token_cache[token_hash] = (sample_token_info, time.time())
        
        with patch.object(validator.supabase_client, 'validate_token') as mock_validate:
            result = await validator._get_token_info(token)
            
            assert result == sample_token_info
            mock_validate.assert_not_called()  # Should use cache
    
    @pytest.mark.asyncio
    async def test_get_token_info_expired_cache(self, validator, sample_token_info):
        """Test that expired cache entries are removed and revalidated."""
        token = "test_token"
        token_hash = validator.supabase_client._hash_token(token)
        
        # Add expired cache entry
        validator._token_cache[token_hash] = (sample_token_info, time.time() - 400)  # Expired
        
        with patch.object(validator.supabase_client, 'validate_token', return_value=sample_token_info) as mock_validate:
            result = await validator._get_token_info(token)
            
            assert result == sample_token_info
            mock_validate.assert_called_once()  # Should revalidate
    
    @pytest.mark.asyncio
    async def test_get_token_info_mcp_token(self, validator):
        """Test validation of MCP tokens."""
        token = "mcp_test_token_123"
        
        with patch.object(validator, '_validate_mcp_token') as mock_mcp:
            mock_token_info = Mock(spec=TokenInfo)
            mock_mcp.return_value = mock_token_info
            
            result = await validator._get_token_info(token)
            
            assert result == mock_token_info
            mock_mcp.assert_called_once_with(token)
    
    # MCP Token Validation Tests
    
    @pytest.mark.asyncio
    async def test_validate_mcp_token_success(self, validator):
        """Test successful MCP token validation."""
        token = "mcp_test_token"
        
        mock_mcp_token = Mock()
        mock_mcp_token.user_id = "user_mcp_123"
        mock_mcp_token.created_at = datetime.now(UTC)
        mock_mcp_token.expires_at = datetime.now(UTC) + timedelta(hours=1)
        
        with patch.object(validator, '_validate_mcp_token', AsyncMock(return_value=mock_mcp_token)):
            result = await validator._validate_mcp_token(token)
            
            assert result is not None
            assert result.user_id == "user_mcp_123"
    
    @pytest.mark.asyncio
    async def test_validate_mcp_token_invalid(self, validator):
        """Test invalid MCP token validation."""
        token = "mcp_invalid_token"
        
        with patch.object(validator, '_validate_mcp_token', AsyncMock(return_value=None)):
            result = await validator._validate_mcp_token(token)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_mcp_token_error(self, validator):
        """Test MCP token validation with error."""
        token = "mcp_error_token"
        
        with patch.object(validator, '_validate_mcp_token', AsyncMock(side_effect=Exception("Service error"))):
            with patch('fastmcp.auth.token_validator.logger') as mock_logger:
                try:
                    result = await validator._validate_mcp_token(token)
                except Exception:
                    result = None
                
                assert result is None
    
    # Failed Attempt Logging Tests
    
    @pytest.mark.asyncio
    async def test_log_failed_attempt(self, validator):
        """Test logging of failed validation attempts."""
        token_hash = "test_hash"
        
        with patch.object(validator.supabase_client, 'log_security_event') as mock_log:
            await validator._log_failed_attempt(token_hash, "invalid_token", {"ip": "127.0.0.1"})
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args[0]
            assert call_args[0] == "validation_failed"
            assert call_args[2]["reason"] == "invalid_token"
    
    @pytest.mark.asyncio
    async def test_log_failed_attempt_multiple_failures(self, validator):
        """Test alert on multiple failed attempts."""
        token_hash = "test_hash"
        current_time = time.time()
        
        # Add 4 previous failures
        for i in range(4):
            validator._failed_attempts[token_hash].append(current_time - i * 10)
        
        with patch.object(validator.supabase_client, 'log_security_event'):
            with patch('fastmcp.auth.token_validator.logger') as mock_logger:
                await validator._log_failed_attempt(token_hash, "invalid_token")
                
                # Should log warning for 5+ failures
                mock_logger.warning.assert_called_once()
    
    # Token Revocation Tests
    
    @pytest.mark.asyncio
    async def test_revoke_token_success(self, validator, sample_token_info):
        """Test successful token revocation."""
        token = "test_token"
        token_hash = validator.supabase_client._hash_token(token)
        
        # Add to cache
        validator._token_cache[token_hash] = (sample_token_info, time.time())
        
        with patch.object(validator.supabase_client, 'revoke_token', return_value=True) as mock_revoke:
            with patch.object(validator.supabase_client, 'log_security_event'):
                result = await validator.revoke_token(token)
                
                assert result is True
                assert token_hash not in validator._token_cache  # Removed from cache
                mock_revoke.assert_called_once_with(token)
    
    @pytest.mark.asyncio
    async def test_revoke_token_failure(self, validator):
        """Test failed token revocation."""
        token = "test_token"
        
        with patch.object(validator.supabase_client, 'revoke_token', return_value=False) as mock_revoke:
            result = await validator.revoke_token(token)
            
            assert result is False
    
    # Rate Limit Status Tests
    
    def test_get_rate_limit_status(self, validator):
        """Test getting rate limit status for a token."""
        token = "test_token"
        token_hash = validator.supabase_client._hash_token(token)
        current_time = time.time()
        
        # Add some requests
        validator._rate_limits[token_hash].extend([
            current_time - 30,   # Within minute
            current_time - 45,   # Within minute
            current_time - 1800  # Within hour
        ])
        
        status = validator.get_rate_limit_status(token)
        
        assert status["requests_per_minute"] == 2  # Two within last minute
        assert status["requests_per_hour"] == 3    # Three within last hour
        assert status["remaining_minute"] == 8     # 10 - 2
        assert status["remaining_hour"] == 97      # 100 - 3
    
    # Cache Management Tests
    
    def test_clear_cache(self, validator, sample_token_info):
        """Test clearing the token cache."""
        # Add items to cache
        validator._token_cache["hash1"] = (sample_token_info, time.time())
        validator._token_cache["hash2"] = (sample_token_info, time.time())
        
        validator.clear_cache()
        
        assert len(validator._token_cache) == 0
    
    def test_get_cache_stats(self, validator):
        """Test getting cache statistics."""
        # Add test data
        validator._token_cache["hash1"] = (Mock(), time.time())
        validator._rate_limits["token1"].append(time.time())
        validator._failed_attempts["token2"].append(time.time())
        
        stats = validator.get_cache_stats()
        
        assert stats["cached_tokens"] == 1
        assert stats["rate_limited_tokens"] == 1
        assert stats["failed_attempt_records"] == 1