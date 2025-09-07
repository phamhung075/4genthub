"""
Authentication Module for DhafnckMCP

This module provides complete authentication functionality including:
- User registration and login
- JWT token management
- Password hashing and reset
- Email verification
- Session management
"""

from .domain.entities.user import User, UserStatus, UserRole
from .domain.value_objects.email import Email
from .domain.value_objects.user_id import UserId
from .domain.services.password_service import PasswordService
from .domain.services.jwt_service import JWTService
from .application.services.auth_service import AuthService, LoginResult, RegistrationResult
from .middleware import JWTAuthMiddleware as AuthMiddleware
from .token_validator import TokenValidator, TokenValidationError, RateLimitError

__all__ = [
    # Domain Entities
    "User",
    "UserStatus",
    "UserRole",
    
    # Value Objects
    "Email",
    "UserId",
    
    # Domain Services
    "PasswordService",
    "JWTService",
    
    # Application Services
    "AuthService",
    "LoginResult",
    "RegistrationResult",
    
    # Middleware
    "AuthMiddleware",
    
    # Validators
    "TokenValidator",
    "TokenValidationError", 
    "RateLimitError",
]