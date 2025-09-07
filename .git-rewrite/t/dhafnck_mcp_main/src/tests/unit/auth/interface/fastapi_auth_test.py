"""
Tests for FastAPI auth interface compatibility layer
"""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
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

    def test_get_current_user(self):
        """Test get_current_user returns default user"""
        user = get_current_user()
        
        assert isinstance(user, User)
        assert user.id == "default-user"
        assert user.email == "user@example.com"
        assert user.username == "user"

    def test_get_current_active_user(self):
        """Test get_current_active_user returns current user"""
        user = get_current_active_user()
        
        assert isinstance(user, User)
        assert user.id == "default-user"
        assert user.email == "user@example.com"
        assert user.username == "user"

    def test_require_admin(self):
        """Test require_admin returns admin user"""
        user = require_admin()
        
        assert isinstance(user, User)
        assert user.id == "default-user"
        assert user.role == UserRole.ADMIN

    def test_require_roles_with_user_role(self):
        """Test require_roles with USER role"""
        user = require_roles(UserRole.USER)
        
        assert isinstance(user, User)
        assert user.id == "default-user"
        assert user.role == UserRole.USER

    def test_require_roles_with_admin_role(self):
        """Test require_roles with ADMIN role"""
        user = require_roles(UserRole.ADMIN)
        
        assert isinstance(user, User)
        assert user.id == "default-user"
        assert user.role == UserRole.ADMIN

    def test_require_roles_with_multiple_roles(self):
        """Test require_roles with multiple roles uses first role"""
        user = require_roles(UserRole.ADMIN, UserRole.USER)
        
        assert isinstance(user, User)
        assert user.id == "default-user"
        assert user.role == UserRole.ADMIN

    def test_require_roles_with_no_roles(self):
        """Test require_roles with no roles"""
        user = require_roles()
        
        assert isinstance(user, User)
        assert user.id == "default-user"
        # Should keep default role when no roles specified

    def test_require_roles_with_non_enum_role(self):
        """Test require_roles with non-enum role defaults to USER"""
        user = require_roles("custom_role")
        
        assert isinstance(user, User)
        assert user.id == "default-user"
        assert user.role == UserRole.USER

    def test_get_optional_user_returns_user(self):
        """Test get_optional_user returns user when available"""
        user = get_optional_user()
        
        assert isinstance(user, User)
        assert user.id == "default-user"

    def test_get_optional_user_handles_exception(self):
        """Test get_optional_user returns None on exception"""
        with patch('fastmcp.auth.interface.fastapi_auth.get_current_user', side_effect=Exception("Auth error")):
            user = get_optional_user()
            assert user is None