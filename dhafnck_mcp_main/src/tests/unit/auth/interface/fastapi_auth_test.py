"""
Tests for FastAPI auth interface compatibility layer
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os
from sqlalchemy.orm import Session
from fastapi.security import HTTPAuthorizationCredentials
from fastmcp.auth.interface.fastapi_auth import (
    get_db,
    get_current_user,
    get_current_active_user,
    require_admin,
    require_roles,
    get_optional_user
)
from fastmcp.auth.domain.entities.user import User, UserRole
from fastmcp.task_management.infrastructure.database.database_config import get_session


class TestFastAPIAuth:
    """Test suite for FastAPI auth interface compatibility functions"""

    def test_get_db(self):
        """Test get_db returns database session"""
        mock_session = Mock(spec=Session)
        
        with patch('fastmcp.auth.interface.fastapi_auth.get_session', return_value=mock_session):
            db_gen = get_db()
            session = next(db_gen)
            
            assert session == mock_session
            
            # Test cleanup
            try:
                next(db_gen)
            except StopIteration:
                pass
            
            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_current_user(self):
        """Test get_current_user returns default user"""
        # Mock credentials
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "test_token"
        
        # Create a mock user to return
        mock_user = User(
            id="test-user-001",
            email="test@example.com",
            username="test-user",
            password_hash="test-hash"
        )
        
        # Mock the keycloak function
        with patch('fastmcp.auth.interface.fastapi_auth.AUTH_PROVIDER', 'keycloak'):
            with patch('fastmcp.auth.keycloak_dependencies.get_current_user_universal') as mock_get_user:
                mock_get_user.return_value = mock_user
                user = await get_current_user(mock_credentials)
        
        assert isinstance(user, User)
        assert user.id == "test-user-001"
        assert user.email == "test@example.com"
        assert user.username == "test-user"

    @pytest.mark.asyncio
    async def test_get_current_active_user(self):
        """Test get_current_active_user returns current user"""
        # Mock credentials
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "test_token"
        
        # Create a mock user to return
        mock_user = User(
            id="test-user-001",
            email="test@example.com",
            username="test-user",
            password_hash="test-hash"
        )
        
        # Mock the keycloak function
        with patch('fastmcp.auth.interface.fastapi_auth.AUTH_PROVIDER', 'keycloak'):
            with patch('fastmcp.auth.keycloak_dependencies.get_current_user_universal') as mock_get_user:
                mock_get_user.return_value = mock_user
                user = await get_current_active_user(mock_credentials)
        
        assert isinstance(user, User)
        assert user.id == "test-user-001"
        assert user.email == "test@example.com"
        assert user.username == "test-user"

    @pytest.mark.asyncio
    async def test_require_admin(self):
        """Test require_admin returns admin user"""
        # Mock credentials
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "test_token"
        
        # Create a mock user to return
        mock_user = User(
            id="test-user-001",
            email="test@example.com",
            username="test-user",
            password_hash="test-hash"
        )
        
        # Mock the keycloak function
        with patch('fastmcp.auth.interface.fastapi_auth.AUTH_PROVIDER', 'keycloak'):
            with patch('fastmcp.auth.keycloak_dependencies.get_current_user_universal') as mock_get_user:
                mock_get_user.return_value = mock_user
                user = await require_admin(mock_credentials)
        
        assert isinstance(user, User)
        assert user.id == "test-user-001"

    @pytest.mark.asyncio
    async def test_require_roles_with_user_role(self):
        """Test require_roles with USER role"""
        # Mock credentials
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "test_token"
        
        # Create a mock user to return
        mock_user = User(
            id="test-user-001",
            email="test@example.com",
            username="test-user",
            password_hash="test-hash"
        )
        
        # Mock the keycloak function
        with patch('fastmcp.auth.interface.fastapi_auth.AUTH_PROVIDER', 'keycloak'):
            with patch('fastmcp.auth.keycloak_dependencies.get_current_user_universal') as mock_get_user:
                mock_get_user.return_value = mock_user
                user = await require_roles(UserRole.USER, credentials=mock_credentials)
        
        assert isinstance(user, User)
        assert user.id == "test-user-001"

    @pytest.mark.asyncio
    async def test_require_roles_with_admin_role(self):
        """Test require_roles with ADMIN role"""
        # Mock credentials
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "test_token"
        
        # Create a mock user to return
        mock_user = User(
            id="test-user-001",
            email="test@example.com",
            username="test-user",
            password_hash="test-hash"
        )
        
        # Mock the keycloak function
        with patch('fastmcp.auth.interface.fastapi_auth.AUTH_PROVIDER', 'keycloak'):
            with patch('fastmcp.auth.keycloak_dependencies.get_current_user_universal') as mock_get_user:
                mock_get_user.return_value = mock_user
                user = await require_roles(UserRole.ADMIN, credentials=mock_credentials)
        
        assert isinstance(user, User)
        assert user.id == "test-user-001"

    @pytest.mark.asyncio
    async def test_require_roles_with_multiple_roles(self):
        """Test require_roles with multiple roles uses first role"""
        # Mock credentials
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "test_token"
        
        # Create a mock user to return
        mock_user = User(
            id="test-user-001",
            email="test@example.com",
            username="test-user",
            password_hash="test-hash"
        )
        
        # Mock the keycloak function
        with patch('fastmcp.auth.interface.fastapi_auth.AUTH_PROVIDER', 'keycloak'):
            with patch('fastmcp.auth.keycloak_dependencies.get_current_user_universal') as mock_get_user:
                mock_get_user.return_value = mock_user
                user = await require_roles(UserRole.ADMIN, UserRole.USER, credentials=mock_credentials)
        
        assert isinstance(user, User)
        assert user.id == "test-user-001"

    @pytest.mark.asyncio
    async def test_require_roles_with_no_roles(self):
        """Test require_roles with no roles"""
        # Mock credentials
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "test_token"
        
        # Create a mock user to return
        mock_user = User(
            id="test-user-001",
            email="test@example.com",
            username="test-user",
            password_hash="test-hash"
        )
        
        # Mock the keycloak function
        with patch('fastmcp.auth.interface.fastapi_auth.AUTH_PROVIDER', 'keycloak'):
            with patch('fastmcp.auth.keycloak_dependencies.get_current_user_universal') as mock_get_user:
                mock_get_user.return_value = mock_user
                user = await require_roles(credentials=mock_credentials)
        
        assert isinstance(user, User)
        assert user.id == "test-user-001"
        # Should keep default role when no roles specified

    @pytest.mark.asyncio
    async def test_require_roles_with_non_enum_role(self):
        """Test require_roles with non-enum role defaults to USER"""
        # Mock credentials
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "test_token"
        
        # Create a mock user to return
        mock_user = User(
            id="test-user-001",
            email="test@example.com",
            username="test-user",
            password_hash="test-hash"
        )
        
        # Mock the keycloak function
        with patch('fastmcp.auth.interface.fastapi_auth.AUTH_PROVIDER', 'keycloak'):
            with patch('fastmcp.auth.keycloak_dependencies.get_current_user_universal') as mock_get_user:
                mock_get_user.return_value = mock_user
                user = await require_roles("custom_role", credentials=mock_credentials)
        
        assert isinstance(user, User)
        assert user.id == "test-user-001"

    @pytest.mark.asyncio
    async def test_get_optional_user_returns_user(self):
        """Test get_optional_user returns user when available"""
        # Mock credentials
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "test_token"
        
        # Create a mock user to return
        mock_user = User(
            id="test-user-001",
            email="test@example.com",
            username="test-user",
            password_hash="test-hash"
        )
        
        # Mock the keycloak function
        with patch('fastmcp.auth.interface.fastapi_auth.AUTH_PROVIDER', 'keycloak'):
            with patch('fastmcp.auth.keycloak_dependencies.get_current_user_universal') as mock_get_user:
                mock_get_user.return_value = mock_user
                user = await get_optional_user(mock_credentials)
        
        assert isinstance(user, User)
        assert user.id == "test-user-001"

    @pytest.mark.asyncio
    async def test_get_optional_user_handles_exception(self):
        """Test get_optional_user returns None on exception"""
        with patch('fastmcp.auth.interface.fastapi_auth.get_current_user', side_effect=Exception("Auth error")):
            user = await get_optional_user()
            assert user is None