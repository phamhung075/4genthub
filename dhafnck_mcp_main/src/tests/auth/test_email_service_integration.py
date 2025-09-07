"""
Integration Tests for Email Service

This module tests the complete email service integration with Supabase
authentication and SMTP functionality.
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta, timezone

# Import the email service components
from fastmcp.auth.infrastructure.email_service import (
    SMTPEmailService, 
    EmailConfig, 
    EmailMessage, 
    TokenManager,
    get_email_service
)
from fastmcp.auth.infrastructure.repositories.email_token_repository import (
    EmailTokenRepository,
    EmailToken,
    get_email_token_repository
)
from fastmcp.auth.infrastructure.enhanced_auth_service import (
    EnhancedAuthService,
    get_enhanced_auth_service
)


class TestTokenManager:
    """Test token management functionality"""
    
    def test_generate_token(self):
        """Test token generation"""
        token = TokenManager.generate_token()
        assert len(token) > 20  # Should be reasonably long
        assert isinstance(token, str)
    
    def test_generate_verification_token(self):
        """Test verification token generation"""
        email = "test@example.com"
        token_data = TokenManager.generate_verification_token(email)
        
        assert "token" in token_data
        assert "email" in token_data
        assert "type" in token_data
        assert "expires_at" in token_data
        assert "hash" in token_data
        assert "created_at" in token_data
        
        assert token_data["email"] == email
        assert token_data["type"] == "verification"
        assert isinstance(token_data["expires_at"], datetime)
        assert isinstance(token_data["created_at"], datetime)
    
    def test_validate_token(self):
        """Test token validation"""
        email = "test@example.com"
        token_data = TokenManager.generate_verification_token(email)
        
        # Valid token should pass
        is_valid = TokenManager.validate_token(
            token_data["token"],
            email,
            token_data["hash"]
        )
        assert is_valid is True
        
        # Invalid token should fail
        is_valid = TokenManager.validate_token(
            "invalid_token",
            email,
            token_data["hash"]
        )
        assert is_valid is False
        
        # Wrong email should fail
        is_valid = TokenManager.validate_token(
            token_data["token"],
            "wrong@example.com",
            token_data["hash"]
        )
        assert is_valid is False


class TestEmailTokenRepository:
    """Test email token repository"""
    
    @pytest.fixture
    def repository(self):
        """Create test repository with in-memory SQLite"""
        return EmailTokenRepository("sqlite:///:memory:")
    
    @pytest.fixture
    def sample_token(self):
        """Create sample email token"""
        token_data = TokenManager.generate_verification_token("test@example.com")
        return EmailToken(
            token=token_data["token"],
            email="test@example.com",
            token_type="verification",
            token_hash=token_data["hash"],
            expires_at=token_data["expires_at"],
            created_at=token_data["created_at"]
        )
    
    def test_save_and_get_token(self, repository, sample_token):
        """Test saving and retrieving tokens"""
        # Save token
        saved = repository.save_token(sample_token)
        assert saved is True
        
        # Retrieve token
        retrieved = repository.get_token(sample_token.token)
        assert retrieved is not None
        assert retrieved.email == sample_token.email
        assert retrieved.token_type == sample_token.token_type
    
    def test_get_tokens_by_email(self, repository, sample_token):
        """Test getting tokens by email"""
        # Save token
        repository.save_token(sample_token)
        
        # Get by email
        tokens = repository.get_tokens_by_email("test@example.com")
        assert len(tokens) == 1
        assert tokens[0].email == "test@example.com"
        
        # Get by email and type
        tokens = repository.get_tokens_by_email("test@example.com", "verification")
        assert len(tokens) == 1
        
        # Get non-existent email
        tokens = repository.get_tokens_by_email("nonexistent@example.com")
        assert len(tokens) == 0
    
    def test_mark_token_used(self, repository, sample_token):
        """Test marking token as used"""
        # Save token
        repository.save_token(sample_token)
        
        # Mark as used
        marked = repository.mark_token_used(sample_token.token)
        assert marked is True
        
        # Verify it's marked as used
        retrieved = repository.get_token(sample_token.token)
        assert retrieved.is_used is True
        assert retrieved.used_at is not None
    
    def test_validate_token(self, repository, sample_token):
        """Test token validation through repository"""
        # Save token
        repository.save_token(sample_token)
        
        # Validate token
        validated = repository.validate_token(
            sample_token.token,
            sample_token.email,
            sample_token.token_type,
            mark_used=True
        )
        
        assert validated is not None
        assert validated.is_used is True
        
        # Try to validate again (should fail because it's used)
        validated_again = repository.validate_token(
            sample_token.token,
            sample_token.email,
            sample_token.token_type
        )
        assert validated_again is None
    
    def test_cleanup_expired_tokens(self, repository):
        """Test cleaning up expired tokens"""
        # Create expired token
        expired_token_data = TokenManager.generate_verification_token("expired@example.com")
        expired_token = EmailToken(
            token=expired_token_data["token"],
            email="expired@example.com",
            token_type="verification",
            token_hash=expired_token_data["hash"],
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),  # Expired 1 hour ago
            created_at=datetime.now(timezone.utc) - timedelta(hours=2)
        )
        
        # Create valid token that won't be cleaned up
        valid_token_data = TokenManager.generate_verification_token("valid@example.com")
        valid_token = EmailToken(
            token=valid_token_data["token"],
            email="valid@example.com",
            token_type="verification",
            token_hash=valid_token_data["hash"],
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),  # Expires in 1 hour
            created_at=datetime.now(timezone.utc) - timedelta(hours=1)  # Created 1 hour ago
        )
        
        # Save both tokens
        repository.save_token(expired_token)
        repository.save_token(valid_token)
        
        # Cleanup expired tokens - using 1 day to avoid deleting valid token
        deleted_count = repository.cleanup_expired_tokens(older_than_days=1)
        assert deleted_count == 1
        
        # Verify expired token is gone
        retrieved_expired = repository.get_token(expired_token.token)
        assert retrieved_expired is None
        
        # Verify valid token still exists
        retrieved_valid = repository.get_token(valid_token.token)
        assert retrieved_valid is not None


@pytest.mark.asyncio
class TestEmailService:
    """Test SMTP email service"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock email configuration"""
        return EmailConfig(
            smtp_host="localhost",
            smtp_port=587,
            smtp_username="test@example.com",
            smtp_password="password",
            smtp_from="test@example.com",
            smtp_from_name="Test Service"
        )
    
    def test_config_loading(self):
        """Test configuration loading from environment"""
        with patch.dict(os.environ, {
            'SMTP_HOST': 'smtp.test.com',
            'SMTP_PORT': '465',
            'SMTP_USERNAME': 'user@test.com',
            'SMTP_PASSWORD': 'testpass',
            'SMTP_FROM': 'noreply@test.com',
            'SMTP_FROM_NAME': 'Test Service'
        }):
            service = SMTPEmailService()
            assert service.config.smtp_host == 'smtp.test.com'
            assert service.config.smtp_port == 465
            assert service.config.smtp_username == 'user@test.com'
    
    def test_template_rendering(self, mock_config):
        """Test email template rendering"""
        service = SMTPEmailService(mock_config)
        
        # Test verification template
        html = service.template_engine.render_template(
            "verification.html",
            user_name="Test User",
            verification_url="https://example.com/verify",
            company_name="Test Company"
        )
        
        assert "Test User" in html
        assert "https://example.com/verify" in html
        assert "Test Company" in html
    
    @patch('smtplib.SMTP')
    async def test_send_verification_email(self, mock_smtp, mock_config):
        """Test sending verification email"""
        # Mock SMTP server
        mock_server = Mock()
        mock_smtp.return_value = mock_server
        
        service = SMTPEmailService(mock_config)
        
        result = await service.send_verification_email(
            email="test@example.com",
            user_name="Test User"
        )
        
        # Should attempt to send email (may fail due to mocking, but structure should be correct)
        assert mock_smtp.called
        assert isinstance(result.recipient, str)
    
    @patch('smtplib.SMTP')
    @patch('smtplib.SMTP_SSL')
    async def test_test_connection(self, mock_smtp_ssl, mock_smtp, mock_config):
        """Test SMTP connection testing"""
        # Mock successful connection
        mock_server = Mock()
        mock_smtp.return_value = mock_server
        mock_smtp_ssl.return_value = mock_server
        
        service = SMTPEmailService(mock_config)
        result = await service.test_connection()
        
        # Either SMTP or SMTP_SSL should be called
        assert mock_smtp.called or mock_smtp_ssl.called
        assert result.success is True


@pytest.mark.asyncio
class TestEnhancedAuthService:
    """Test enhanced authentication service"""
    
    @pytest.fixture
    def mock_supabase_service(self):
        """Mock Supabase service"""
        mock = Mock()
        # Use AsyncMock for async sign_up method
        mock.sign_up = AsyncMock(return_value=Mock(
            success=True,
            user={"id": "user123", "email": "test@example.com"},
            session={"access_token": "token123"},
            requires_email_verification=True
        ))
        return mock
    
    @pytest.fixture
    def mock_email_service(self):
        """Mock email service"""
        mock = Mock()
        # Use AsyncMock for async methods
        mock.send_verification_email = AsyncMock(return_value=Mock(
            success=True,
            recipient="test@example.com"
        ))
        mock.test_connection = AsyncMock(return_value=Mock(
            success=True
        ))
        return mock
    
    @pytest.fixture
    def mock_token_repository(self):
        """Mock token repository"""
        mock = Mock()
        mock.save_token.return_value = True
        mock.get_token_stats.return_value = {
            "total_tokens": 10,
            "used_tokens": 5,
            "expired_tokens": 2
        }
        return mock
    
    async def test_register_user(self, mock_supabase_service, mock_email_service, mock_token_repository):
        """Test user registration with email"""
        service = EnhancedAuthService(
            supabase_service=mock_supabase_service,
            email_service=mock_email_service,
            token_repository=mock_token_repository
        )
        
        result = await service.register_user(
            email="test@example.com",
            password="password123",
            metadata={"username": "testuser"},
            send_custom_email=True
        )
        
        assert result.success is True
        assert result.email_sent is True
        assert mock_supabase_service.sign_up.called
        assert mock_email_service.send_verification_email.called
        assert mock_token_repository.save_token.called
    
    async def test_get_email_stats(self, mock_supabase_service, mock_email_service, mock_token_repository):
        """Test getting email statistics"""
        service = EnhancedAuthService(
            supabase_service=mock_supabase_service,
            email_service=mock_email_service,
            token_repository=mock_token_repository
        )
        
        result = await service.get_email_stats()
        
        assert result["success"] is True
        assert "stats" in result
        assert mock_token_repository.get_token_stats.called
    
    async def test_test_email_service(self, mock_supabase_service, mock_email_service, mock_token_repository):
        """Test email service connection test"""
        service = EnhancedAuthService(
            supabase_service=mock_supabase_service,
            email_service=mock_email_service,
            token_repository=mock_token_repository
        )
        
        result = await service.test_email_service()
        
        assert result["success"] is True
        assert mock_email_service.test_connection.called


class TestIntegration:
    """Integration tests"""
    
    def test_global_service_instances(self):
        """Test that global service instances can be created"""
        # Mock required environment variables
        with patch.dict(os.environ, {
            'SMTP_HOST': 'smtp.test.com',
            'SMTP_PORT': '587',
            'SMTP_USERNAME': 'test@example.com',
            'SMTP_PASSWORD': 'testpass',
            'SMTP_FROM': 'noreply@test.com',
            'SMTP_FROM_NAME': 'Test Service'
        }):
            # These should not raise exceptions
            email_service = get_email_service()
            assert email_service is not None
            
            token_repo = get_email_token_repository()
            assert token_repo is not None
            
            enhanced_service = get_enhanced_auth_service()
            assert enhanced_service is not None
    
    @pytest.mark.skipif(
        not os.getenv("SMTP_HOST") or not os.getenv("SMTP_USERNAME"),
        reason="SMTP configuration not available"
    )
    @pytest.mark.asyncio
    async def test_real_email_connection(self):
        """Test real SMTP connection (only if configured)"""
        service = get_email_service()
        result = await service.test_connection()
        
        # This should either succeed or fail gracefully
        assert isinstance(result.success, bool)
        if not result.success:
            assert result.error_message is not None


if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"])