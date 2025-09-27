"""
Test Suite for Token Application Facade

Tests the token facade's business logic, JWT integration, and repository operations
with comprehensive coverage including edge cases and error scenarios.
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone
import jwt

from fastmcp.task_management.application.facades.token_application_facade import TokenApplicationFacade
from fastmcp.task_management.domain.repositories.token_repository_interface import ITokenRepository
from fastmcp.auth.services.mcp_token_service import MCPToken


@pytest.mark.unit
class TestTokenApplicationFacade:
    """Test suite for TokenApplicationFacade"""
    
    @pytest.fixture
    def mock_repository(self):
        """Create mock repository"""
        repo = Mock(spec=ITokenRepository)
        # Set up async methods
        repo.create_token = AsyncMock()
        repo.get_token = AsyncMock()
        repo.get_token_by_id = AsyncMock()
        repo.get_user_tokens = AsyncMock()
        repo.count_user_tokens = AsyncMock()
        repo.revoke_token = AsyncMock()
        repo.reactivate_token = AsyncMock()
        repo.delete_token = AsyncMock()
        repo.update_token_usage = AsyncMock()
        return repo
    
    @pytest.fixture
    def mock_session(self):
        """Create mock database session"""
        return Mock()
    
    @pytest.fixture
    def mock_jwt_service(self):
        """Create mock JWT service"""
        service = Mock()
        service.generate_token = Mock(return_value="test.jwt.token")
        service.decode_token = Mock(return_value={
            "user_id": "test_user",
            "token_id": "tok_12345",
            "scopes": ["read", "write"]
        })
        return service
    
    @pytest.fixture
    def mock_mcp_token_service(self):
        """Create mock MCP token service"""
        service = Mock()
        service.generate_mcp_token_from_user_id = AsyncMock()
        service.revoke_user_tokens = AsyncMock(return_value=True)
        service.get_token_stats = Mock(return_value={
            "total": 10,
            "active": 8,
            "expired": 2
        })
        service.cleanup_expired_tokens = AsyncMock(return_value=3)
        return service
    
    @pytest.fixture
    def facade(self, mock_repository, monkeypatch):
        """Create facade instance with mocked dependencies"""
        # Set JWT secret in environment
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")
        
        # Create facade with injected repository
        facade = TokenApplicationFacade(token_repository=mock_repository)
        return facade
    
    @pytest.fixture
    def facade_with_mocks(self, facade, mock_jwt_service, mock_mcp_token_service):
        """Facade with all services mocked"""
        facade.jwt_service = mock_jwt_service
        facade.mcp_token_service = mock_mcp_token_service
        return facade
    
    def test_init_without_jwt_secret(self, mock_repository):
        """Test initialization fails without JWT secret"""
        # Remove JWT secret from environment
        if "JWT_SECRET_KEY" in os.environ:
            del os.environ["JWT_SECRET_KEY"]
        
        with pytest.raises(ValueError, match="JWT_SECRET_KEY must be set"):
            TokenApplicationFacade(token_repository=mock_repository)
    
    def test_init_with_jwt_secret(self, mock_repository, monkeypatch):
        """Test successful initialization with JWT secret"""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
        
        facade = TokenApplicationFacade(token_repository=mock_repository)
        assert facade._token_repository == mock_repository
        assert facade.jwt_service is not None
        assert facade.mcp_token_service is not None
    
    @pytest.mark.asyncio
    async def test_generate_mcp_token_from_user_success(self, facade_with_mocks):
        """Test successful MCP token generation"""
        # Mock token object
        mock_token = MCPToken(
            token="mcp_token_12345",
            user_id="user123",
            email="test@example.com",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        # Add token_id as an attribute since MCPToken doesn't have it by default
        mock_token.token_id = "tok_abc123"
        
        facade_with_mocks.mcp_token_service.generate_mcp_token_from_user_id.return_value = mock_token
        
        result = await facade_with_mocks.generate_mcp_token_from_user(
            user_id="user123",
            email="test@example.com",
            expires_in_hours=24,
            metadata={"key": "value"}
        )
        
        assert result["success"] is True
        assert result["token"] == "mcp_token_12345"
        assert result["token_id"] == "tok_abc123"
        assert "expires_at" in result
        
        # Verify service was called correctly
        facade_with_mocks.mcp_token_service.generate_mcp_token_from_user_id.assert_called_once_with(
            user_id="user123",
            email="test@example.com",
            expires_in_hours=24,
            metadata={"key": "value"}
        )
    
    @pytest.mark.asyncio
    async def test_generate_mcp_token_from_user_failure(self, facade_with_mocks):
        """Test MCP token generation failure"""
        facade_with_mocks.mcp_token_service.generate_mcp_token_from_user_id.side_effect = Exception("Service error")
        
        result = await facade_with_mocks.generate_mcp_token_from_user(
            user_id="user123",
            email="test@example.com",
            expires_in_hours=24
        )
        
        assert result["success"] is False
        assert "Service error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_revoke_user_tokens_success(self, facade_with_mocks):
        """Test successful token revocation"""
        result = await facade_with_mocks.revoke_user_tokens("user123")
        
        assert result["success"] is True
        assert result["revoked"] is True
        assert "All tokens revoked successfully" in result["message"]
        
        facade_with_mocks.mcp_token_service.revoke_user_tokens.assert_called_once_with("user123")
    
    @pytest.mark.asyncio
    async def test_revoke_user_tokens_no_tokens(self, facade_with_mocks):
        """Test revocation when no tokens exist"""
        facade_with_mocks.mcp_token_service.revoke_user_tokens.return_value = False
        
        result = await facade_with_mocks.revoke_user_tokens("user123")
        
        assert result["success"] is False
        assert result["revoked"] is False
        assert "No tokens found to revoke" in result["message"]
    
    @pytest.mark.asyncio
    async def test_revoke_user_tokens_error(self, facade_with_mocks):
        """Test revocation error handling"""
        facade_with_mocks.mcp_token_service.revoke_user_tokens.side_effect = Exception("Revocation error")
        
        result = await facade_with_mocks.revoke_user_tokens("user123")
        
        assert result["success"] is False
        assert "Revocation error" in result["error"]
    
    def test_get_token_stats_success(self, facade_with_mocks):
        """Test getting token statistics"""
        result = facade_with_mocks.get_token_stats()
        
        assert result["success"] is True
        assert result["stats"]["total"] == 10
        assert result["stats"]["active"] == 8
        assert result["stats"]["expired"] == 2
    
    def test_get_token_stats_error(self, facade_with_mocks):
        """Test token stats error handling"""
        facade_with_mocks.mcp_token_service.get_token_stats.side_effect = Exception("Stats error")
        
        result = facade_with_mocks.get_token_stats()
        
        assert result["success"] is False
        assert "Stats error" in result["error"]
        assert result["stats"] == {}
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_tokens_success(self, facade_with_mocks):
        """Test successful expired token cleanup"""
        result = await facade_with_mocks.cleanup_expired_tokens()
        
        assert result["success"] is True
        assert result["cleaned_count"] == 3
        assert "Cleaned up 3 expired tokens" in result["message"]
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_tokens_error(self, facade_with_mocks):
        """Test cleanup error handling"""
        facade_with_mocks.mcp_token_service.cleanup_expired_tokens.side_effect = Exception("Cleanup error")
        
        result = await facade_with_mocks.cleanup_expired_tokens()
        
        assert result["success"] is False
        assert "Cleanup error" in result["error"]
        assert result["cleaned_count"] == 0
    
    @pytest.mark.asyncio
    async def test_create_api_token_success(self, facade_with_mocks, mock_session):
        """Test successful API token creation"""
        # Mock created token
        mock_created_token = Mock()
        mock_created_token.id = "tok_12345"
        mock_created_token.name = "Test Token"
        mock_created_token.scopes = ["read", "write"]
        mock_created_token.created_at = datetime.now(timezone.utc)
        mock_created_token.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        mock_created_token.rate_limit = 1000
        mock_created_token.is_active = True
        
        facade_with_mocks._token_repository.create_token.return_value = mock_created_token
        
        result = await facade_with_mocks.create_api_token(
            user_id="user123",
            name="Test Token",
            scopes=["read", "write"],
            expires_in_days=30,
            rate_limit=1000,
            metadata={"purpose": "testing"},
            session=mock_session
        )
        
        assert result["success"] is True
        assert result["token"]["id"] == "tok_12345"
        assert result["token"]["name"] == "Test Token"
        assert result["token"]["token"] == "test.jwt.token"
        assert result["token"]["scopes"] == ["read", "write"]
        assert result["token"]["rate_limit"] == 1000
        assert result["token"]["is_active"] is True
    
    @pytest.mark.asyncio
    async def test_create_api_token_repository_failure(self, facade_with_mocks, mock_session):
        """Test API token creation when repository fails"""
        facade_with_mocks._token_repository.create_token.return_value = None
        
        result = await facade_with_mocks.create_api_token(
            user_id="user123",
            name="Test Token",
            scopes=["read"],
            expires_in_days=30,
            rate_limit=None,
            metadata=None,
            session=mock_session
        )
        
        assert result["success"] is False
        assert "Failed to create token" in result["error"]
    
    @pytest.mark.asyncio
    async def test_create_api_token_exception(self, facade_with_mocks, mock_session):
        """Test API token creation exception handling"""
        facade_with_mocks._token_repository.create_token.side_effect = Exception("Database error")
        
        result = await facade_with_mocks.create_api_token(
            user_id="user123",
            name="Test Token",
            scopes=["read"],
            expires_in_days=30,
            rate_limit=500,
            metadata={},
            session=mock_session
        )
        
        assert result["success"] is False
        assert "Database error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_list_user_tokens_success(self, facade_with_mocks, mock_session):
        """Test listing user tokens"""
        # Mock tokens
        mock_tokens = []
        for i in range(3):
            token = Mock()
            token.id = f"tok_{i}"
            token.name = f"Token {i}"
            token.scopes = ["read"]
            token.created_at = datetime.now(timezone.utc)
            token.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
            token.last_used_at = datetime.now(timezone.utc) if i < 2 else None
            token.usage_count = i * 10
            token.rate_limit = 1000
            token.is_active = True
            mock_tokens.append(token)
        
        facade_with_mocks._token_repository.get_user_tokens.return_value = mock_tokens
        facade_with_mocks._token_repository.count_user_tokens.return_value = 3
        
        result = await facade_with_mocks.list_user_tokens(
            user_id="user123",
            session=mock_session,
            skip=0,
            limit=10
        )
        
        assert result["success"] is True
        assert len(result["tokens"]) == 3
        assert result["total"] == 3
        
        # Verify token data
        for i, token in enumerate(result["tokens"]):
            assert token["id"] == f"tok_{i}"
            assert token["name"] == f"Token {i}"
            assert token["usage_count"] == i * 10
    
    @pytest.mark.asyncio
    async def test_list_user_tokens_empty(self, facade_with_mocks, mock_session):
        """Test listing tokens when user has none"""
        facade_with_mocks._token_repository.get_user_tokens.return_value = []
        facade_with_mocks._token_repository.count_user_tokens.return_value = 0
        
        result = await facade_with_mocks.list_user_tokens(
            user_id="user123",
            session=mock_session
        )
        
        assert result["success"] is True
        assert result["tokens"] == []
        assert result["total"] == 0
    
    @pytest.mark.asyncio
    async def test_list_user_tokens_error(self, facade_with_mocks, mock_session):
        """Test list tokens error handling"""
        facade_with_mocks._token_repository.get_user_tokens.side_effect = Exception("Query error")
        
        result = await facade_with_mocks.list_user_tokens(
            user_id="user123",
            session=mock_session
        )
        
        assert result["success"] is False
        assert "Query error" in result["error"]
        assert result["tokens"] == []
        assert result["total"] == 0
    
    @pytest.mark.asyncio
    async def test_get_token_details_success(self, facade_with_mocks, mock_session):
        """Test getting token details"""
        mock_token = Mock()
        mock_token.id = "tok_12345"
        mock_token.name = "Test Token"
        mock_token.scopes = ["read", "write"]
        mock_token.created_at = datetime.now(timezone.utc)
        mock_token.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        mock_token.last_used_at = datetime.now(timezone.utc)
        mock_token.usage_count = 42
        mock_token.rate_limit = 1000
        mock_token.is_active = True
        mock_token.token_metadata = {"purpose": "testing"}
        
        facade_with_mocks._token_repository.get_token.return_value = mock_token
        
        result = await facade_with_mocks.get_token_details(
            token_id="tok_12345",
            user_id="user123",
            session=mock_session
        )
        
        assert result["success"] is True
        assert result["token"]["id"] == "tok_12345"
        assert result["token"]["name"] == "Test Token"
        assert result["token"]["usage_count"] == 42
        assert result["token"]["metadata"] == {"purpose": "testing"}
    
    @pytest.mark.asyncio
    async def test_get_token_details_not_found(self, facade_with_mocks, mock_session):
        """Test getting details for non-existent token"""
        facade_with_mocks._token_repository.get_token.return_value = None
        
        result = await facade_with_mocks.get_token_details(
            token_id="tok_invalid",
            user_id="user123",
            session=mock_session
        )
        
        assert result["success"] is False
        assert "Token not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_revoke_token_success(self, facade_with_mocks, mock_session):
        """Test successful token revocation"""
        facade_with_mocks._token_repository.revoke_token.return_value = True
        
        result = await facade_with_mocks.revoke_token(
            token_id="tok_12345",
            user_id="user123",
            session=mock_session
        )
        
        assert result["success"] is True
        assert "Token revoked successfully" in result["message"]
    
    @pytest.mark.asyncio
    async def test_revoke_token_not_found(self, facade_with_mocks, mock_session):
        """Test revoking non-existent token"""
        facade_with_mocks._token_repository.revoke_token.return_value = False
        
        result = await facade_with_mocks.revoke_token(
            token_id="tok_invalid",
            user_id="user123",
            session=mock_session
        )
        
        assert result["success"] is False
        assert "Token not found or could not be revoked" in result["error"]
    
    @pytest.mark.asyncio
    async def test_delete_token_success(self, facade_with_mocks, mock_session):
        """Test successful token deletion"""
        facade_with_mocks._token_repository.delete_token.return_value = True
        
        result = await facade_with_mocks.delete_token(
            token_id="tok_12345",
            user_id="user123",
            session=mock_session
        )
        
        assert result["success"] is True
        assert "Token deleted successfully" in result["message"]
    
    @pytest.mark.asyncio
    async def test_reactivate_token_success(self, facade_with_mocks, mock_session):
        """Test successful token reactivation"""
        facade_with_mocks._token_repository.reactivate_token.return_value = True
        
        result = await facade_with_mocks.reactivate_token(
            token_id="tok_12345",
            user_id="user123",
            session=mock_session
        )
        
        assert result["success"] is True
        assert "Token reactivated successfully" in result["message"]
    
    @pytest.mark.asyncio
    async def test_rotate_token_success(self, facade_with_mocks, mock_session):
        """Test successful token rotation"""
        # Mock old token
        old_token = Mock()
        old_token.id = "tok_old"
        old_token.name = "Old Token"
        old_token.scopes = ["read", "write"]
        old_token.rate_limit = 500
        
        facade_with_mocks._token_repository.get_token.return_value = old_token
        facade_with_mocks._token_repository.revoke_token.return_value = True
        
        # Mock new token creation
        new_token = Mock()
        new_token.id = "tok_new"
        new_token.name = "Old Token (rotated)"
        new_token.scopes = ["read", "write"]
        new_token.created_at = datetime.now(timezone.utc)
        new_token.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        new_token.rate_limit = 500
        new_token.is_active = True
        
        facade_with_mocks._token_repository.create_token.return_value = new_token
        
        result = await facade_with_mocks.rotate_token(
            token_id="tok_old",
            user_id="user123",
            session=mock_session
        )
        
        assert result["success"] is True
        assert result["token_data"]["id"] == "tok_new"
        assert result["token_data"]["name"] == "Old Token (rotated)"
    
    @pytest.mark.asyncio
    async def test_rotate_token_not_found(self, facade_with_mocks, mock_session):
        """Test rotating non-existent token"""
        facade_with_mocks._token_repository.get_token.return_value = None
        
        result = await facade_with_mocks.rotate_token(
            token_id="tok_invalid",
            user_id="user123",
            session=mock_session
        )
        
        assert result["success"] is False
        assert "Token not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_validate_token_success(self, facade_with_mocks, mock_session):
        """Test successful token validation"""
        # Mock valid token in database
        db_token = Mock()
        db_token.is_active = True
        
        facade_with_mocks._token_repository.get_token_by_id.return_value = db_token
        facade_with_mocks._token_repository.update_token_usage.return_value = True
        
        result = await facade_with_mocks.validate_token(
            token="test.jwt.token",
            session=mock_session
        )
        
        assert result["success"] is True
        assert result["claims"]["user_id"] == "test_user"
        assert result["claims"]["token_id"] == "tok_12345"
        assert result["claims"]["scopes"] == ["read", "write"]
    
    @pytest.mark.asyncio
    async def test_validate_token_invalid_format(self, facade_with_mocks, mock_session):
        """Test validating token with invalid format"""
        facade_with_mocks.jwt_service.decode_token.return_value = None
        
        result = await facade_with_mocks.validate_token(
            token="invalid.token",
            session=mock_session
        )
        
        assert result["success"] is False
        assert "Invalid token format" in result["error"]
    
    @pytest.mark.asyncio
    async def test_validate_token_revoked(self, facade_with_mocks, mock_session):
        """Test validating revoked token"""
        # Mock revoked token
        db_token = Mock()
        db_token.is_active = False
        
        facade_with_mocks._token_repository.get_token_by_id.return_value = db_token
        
        result = await facade_with_mocks.validate_token(
            token="test.jwt.token",
            session=mock_session
        )
        
        assert result["success"] is False
        assert "Token is invalid or revoked" in result["error"]
    
    @pytest.mark.asyncio
    async def test_validate_token_expired(self, facade_with_mocks, mock_session):
        """Test validating expired token"""
        facade_with_mocks.jwt_service.decode_token.side_effect = jwt.ExpiredSignatureError("Token expired")
        
        result = await facade_with_mocks.validate_token(
            token="expired.jwt.token",
            session=mock_session
        )
        
        assert result["success"] is False
        assert "Token has expired" in result["error"]
    
    @pytest.mark.asyncio
    async def test_validate_token_invalid_jwt(self, facade_with_mocks, mock_session):
        """Test validating invalid JWT token"""
        facade_with_mocks.jwt_service.decode_token.side_effect = jwt.InvalidTokenError("Invalid signature")
        
        result = await facade_with_mocks.validate_token(
            token="invalid.jwt.token",
            session=mock_session
        )
        
        assert result["success"] is False
        assert "Invalid token" in result["error"]
        assert "Invalid signature" in result["error"]
    
    def test_get_repository_with_session(self, facade, mock_session):
        """Test getting repository with session"""
        repo = facade._get_repository(mock_session)
        assert repo == facade._token_repository
    
    @patch('fastmcp.task_management.infrastructure.repositories.token_repository.TokenRepository')
    def test_get_repository_creates_new(self, mock_token_repo_class, mock_session, monkeypatch):
        """Test creating new repository when none injected"""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
        
        # Create facade without repository
        facade = TokenApplicationFacade(token_repository=None)
        
        # Mock repository instance
        mock_repo_instance = Mock()
        mock_token_repo_class.return_value = mock_repo_instance
        
        # Get repository
        repo = facade._get_repository(mock_session)
        
        # Verify repository was created
        mock_token_repo_class.assert_called_once_with(mock_session)
        assert repo == mock_repo_instance
        assert facade._token_repository == mock_repo_instance


@pytest.mark.unit
@pytest.mark.asyncio
class TestTokenApplicationFacadeIntegration:
    """Integration tests for TokenApplicationFacade"""
    
    @pytest.fixture
    def real_jwt_service(self, monkeypatch):
        """Create real JWT service for integration tests"""
        from fastmcp.auth.domain.services.jwt_service import JWTService
        
        secret = "integration-test-secret"
        monkeypatch.setenv("JWT_SECRET_KEY", secret)
        return JWTService(secret_key=secret)
    
    @pytest.fixture
    def mock_session_integration(self):
        """Create mock database session for integration tests"""
        return Mock()
    
    @pytest.fixture
    def mock_repository_integration(self):
        """Create mock repository for integration tests"""
        repo = Mock(spec=ITokenRepository)
        # Set up async methods
        repo.create_token = AsyncMock()
        repo.get_token = AsyncMock()
        repo.get_token_by_id = AsyncMock()
        repo.get_user_tokens = AsyncMock()
        repo.count_user_tokens = AsyncMock()
        repo.revoke_token = AsyncMock()
        repo.reactivate_token = AsyncMock()
        repo.delete_token = AsyncMock()
        repo.update_token_usage = AsyncMock()
        return repo
    
    @pytest.fixture
    def mock_mcp_token_service_integration(self):
        """Create mock MCP token service for integration tests"""
        service = Mock()
        service.generate_mcp_token_from_user_id = AsyncMock()
        service.revoke_user_tokens = AsyncMock(return_value=True)
        service.get_token_stats = Mock(return_value={
            "total": 10,
            "active": 8,
            "expired": 2
        })
        service.cleanup_expired_tokens = AsyncMock(return_value=3)
        return service
    
    @pytest.fixture
    def facade_integration(self, mock_repository_integration, real_jwt_service, mock_mcp_token_service_integration, monkeypatch):
        """Facade with real JWT service for integration tests"""
        monkeypatch.setenv("JWT_SECRET_KEY", "integration-test-secret")
        
        facade = TokenApplicationFacade(token_repository=mock_repository_integration)
        # Use mock jwt service with decode_token method
        mock_jwt = Mock()
        mock_jwt.generate_token = real_jwt_service.generate_token
        mock_jwt.decode_token = Mock(return_value={
            "user_id": "user_integration",
            "token_id": "tok_integration",
            "scopes": ["read", "write", "admin"]
        })
        facade.jwt_service = mock_jwt
        facade.mcp_token_service = mock_mcp_token_service_integration
        return facade
    
    async def test_token_lifecycle_integration(self, facade_integration, mock_session_integration):
        """Test complete token lifecycle with real JWT"""
        # Create token
        mock_created_token = Mock()
        mock_created_token.id = "tok_integration"
        mock_created_token.name = "Integration Token"
        mock_created_token.scopes = ["read", "write", "admin"]
        mock_created_token.created_at = datetime.now(timezone.utc)
        mock_created_token.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        mock_created_token.rate_limit = 5000
        mock_created_token.is_active = True
        
        facade_integration._token_repository.create_token.return_value = mock_created_token
        facade_integration._token_repository.get_token_by_id.return_value = mock_created_token
        facade_integration._token_repository.update_token_usage.return_value = True
        
        # Create API token
        create_result = await facade_integration.create_api_token(
            user_id="user_integration",
            name="Integration Token",
            scopes=["read", "write", "admin"],
            expires_in_days=7,
            rate_limit=5000,
            metadata={"test": "integration"},
            session=mock_session_integration
        )
        
        assert create_result["success"] is True
        jwt_token = create_result["token"]["token"]
        
        # Validate the created token
        validate_result = await facade_integration.validate_token(
            token=jwt_token,
            session=mock_session_integration
        )
        
        assert validate_result["success"] is True
        assert validate_result["claims"]["user_id"] == "user_integration"
        assert validate_result["claims"]["scopes"] == ["read", "write", "admin"]
        assert validate_result["claims"]["token_id"] == "tok_integration"
    
    async def test_concurrent_token_operations(self, facade_integration, mock_session_integration):
        """Test concurrent token operations"""
        # Mock repository to handle concurrent operations
        tokens_created = []
        
        async def mock_create(token_data):
            token = Mock()
            token.id = token_data["id"]
            token.name = token_data["name"]
            token.scopes = token_data["scopes"]
            token.created_at = datetime.now(timezone.utc)
            token.expires_at = token_data["expires_at"]
            token.rate_limit = token_data["rate_limit"]
            token.is_active = True
            tokens_created.append(token)
            return token
        
        facade_integration._token_repository.create_token = mock_create
        
        # Create multiple tokens concurrently
        tasks = []
        for i in range(5):
            task = facade_integration.create_api_token(
                user_id=f"user_{i}",
                name=f"Concurrent Token {i}",
                scopes=["read"],
                expires_in_days=30,
                rate_limit=1000,
                metadata={"index": i},
                session=mock_session_integration
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Verify all tokens were created
        assert len(results) == 5
        assert all(r["success"] for r in results)
        assert len(tokens_created) == 5
        
        # Verify each token has unique ID
        token_ids = [t.id for t in tokens_created]
        assert len(set(token_ids)) == 5