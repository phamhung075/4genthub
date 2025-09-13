"""
JWT Authentication Backend for MCP Integration

This module provides the integration between our JWT authentication system
and the MCP server infrastructure.
"""

import os
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from mcp.server.auth.provider import AccessToken, TokenVerifier
from starlette.authentication import AuthCredentials
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser

from ..domain.services.jwt_service import JWTService
from ..application.services.auth_service import AuthService
from ..infrastructure.repositories.user_repository import UserRepository


@dataclass
class MCPUserContext:
    """User context for MCP operations"""
    user_id: str
    email: str
    username: str
    roles: List[str]
    scopes: List[str]


class JWTAuthBackend(TokenVerifier):
    """
    JWT Authentication Backend that integrates our authentication system
    with the MCP server infrastructure.
    
    This backend:
    1. Validates JWT tokens using our JWTService
    2. Extracts user context from tokens
    3. Provides user filtering for MCP operations
    """
    
    def __init__(
        self,
        jwt_service: Optional[JWTService] = None,
        auth_service: Optional[AuthService] = None,
        user_repository: Optional[UserRepository] = None,
        required_scopes: Optional[List[str]] = None
    ):
        """
        Initialize the JWT auth backend.
        
        Args:
            jwt_service: Service for JWT operations
            auth_service: Authentication service
            user_repository: User repository for user lookups
            required_scopes: List of required scopes for MCP access
        """
        # Get JWT secret from environment
        jwt_secret = os.getenv("JWT_SECRET_KEY")
        if not jwt_secret:
            raise ValueError("JWT_SECRET_KEY environment variable not set")
        
        # Initialize services if not provided
        self._jwt_service = jwt_service or JWTService(secret_key=jwt_secret)
        self._auth_service = auth_service
        self._user_repository = user_repository
        
        # Store required scopes
        self._required_scopes = required_scopes or ["mcp:access"]
        
        # Cache for user contexts
        self._user_context_cache: Dict[str, MCPUserContext] = {}
        self._cache_ttl = 300  # 5 minutes
        self._cache_timestamps: Dict[str, float] = {}
    
    @property
    def secret_key(self) -> str:
        """Get the JWT secret key from the internal JWT service."""
        return self._jwt_service.secret_key
    
    @property
    def algorithm(self) -> str:
        """Get the JWT algorithm from the internal JWT service."""
        return self._jwt_service.ALGORITHM
    
    async def _validate_token_dual_auth(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Try to validate token with both local JWT secret and Supabase JWT secret.
        Handles audience validation properly for both token types.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload if valid with either secret, None otherwise
        """
        import logging
        import jwt as pyjwt
        from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
        
        logger = logging.getLogger(__name__)
        
        # Try local JWT service first (for locally generated tokens with "mcp-server" audience)
        logger.debug("🔍 Trying local JWT validation...")
        for token_type in ["access", "api_token"]:
            try:
                payload = self._jwt_service.verify_token(
                    token, 
                    expected_type=token_type, 
                    expected_audience="mcp-server"
                )
                if payload:
                    logger.info(f"✅ Token validated with local JWT secret as '{token_type}' type with audience 'mcp-server'")
                    return payload
                else:
                    logger.debug(f"❌ Local JWT validation failed for type '{token_type}'")
            except Exception as e:
                logger.debug(f"❌ Local JWT validation exception for type '{token_type}': {e}")
        
        # Try Supabase JWT secret (for Supabase-generated tokens with "authenticated" audience)
        logger.debug("🔍 Trying Supabase JWT validation...")
        supabase_jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
        
        if supabase_jwt_secret:
            logger.info(f"✅ SUPABASE_JWT_SECRET found, length: {len(supabase_jwt_secret)}")
            try:
                logger.info(f"🔍 Attempting to decode token with Supabase secret and 'authenticated' audience...")
                logger.info(f"🔍 Token header (first 50 chars): {token[:50]}...")
                
                # Try to validate with Supabase secret and proper audience validation
                payload = pyjwt.decode(
                    token,
                    supabase_jwt_secret,
                    algorithms=["HS256"],
                    audience="authenticated",  # Supabase tokens have this audience
                    options={
                        "verify_signature": True,
                        "verify_aud": True,        # Verify audience
                        "verify_iss": False,       # Don't verify issuer (Supabase has different issuer)
                        "verify_exp": True,        # Verify expiration
                        "verify_iat": True,        # Verify issued at
                        "verify_nbf": True,        # Verify not before
                    }
                )
                
                if payload:
                    logger.info("✅ Token validated with Supabase JWT secret and audience 'authenticated'")
                    logger.debug(f"✅ Supabase payload keys: {list(payload.keys())}")
                    logger.debug(f"✅ User from Supabase token: {payload.get('sub')} ({payload.get('email')})")
                    # Add type for compatibility
                    if "type" not in payload:
                        payload["type"] = "supabase_access"
                    return payload
                    
            except ExpiredSignatureError:
                logger.debug("❌ Supabase JWT token expired")
            except InvalidTokenError as e:
                logger.debug(f"❌ Supabase JWT validation failed: {e}")
                logger.debug(f"❌ Token that failed: {token[:100]}...")
            except Exception as e:
                logger.debug(f"❌ Supabase JWT validation exception: {e}")
                import traceback
                logger.debug(f"❌ Exception traceback: {traceback.format_exc()}")
        else:
            logger.debug("❌ SUPABASE_JWT_SECRET not configured, skipping Supabase validation")
        
        # Both validation methods failed
        logger.debug("❌ Token validation failed with both JWT secrets")
        return None

    async def verify_token(self, token: str) -> Optional[AccessToken]:
        """
        Validate JWT token and return AccessToken for MCP.
        
        Args:
            token: JWT token string
            
        Returns:
            AccessToken if valid, None otherwise
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"🔍 JWT Auth Backend: Verifying token for MCP access")
            logger.debug(f"Token (first 20 chars): {token[:20]}...")
            
            # Try dual JWT validation - first local, then Supabase
            payload = await self._validate_token_dual_auth(token)
            
            if not payload:
                logger.error("❌ Token validation failed with both local and Supabase JWT secrets")
                return None
            
            logger.debug(f"JWT payload keys: {list(payload.keys())}")
            
            # Extract user information - check both "sub" and "user_id" fields
            user_id = payload.get("sub") or payload.get("user_id")
            logger.debug(f"Extracted user_id: {user_id}")
            
            if not user_id:
                logger.error("❌ No user_id found in token payload")
                return None
            
            # Get or cache user context
            user_context = await self._get_user_context(user_id, payload)
            if not user_context:
                logger.error(f"❌ Could not get user context for user_id: {user_id}")
                return None
            
            logger.info(f"✅ User context loaded for: {user_id}")
            
            # Extract scopes from token
            scopes = payload.get("scopes", [])
            if isinstance(scopes, str):
                scopes = scopes.split()
            
            logger.debug(f"Token scopes: {scopes}")
            
            # Add MCP-specific scopes based on user roles
            mcp_scopes = self._map_roles_to_scopes(user_context.roles)
            all_scopes = list(set(scopes + mcp_scopes))
            
            logger.debug(f"Final scopes (token + MCP): {all_scopes}")
            
            # Get expiration
            exp = payload.get("exp")
            
            # Return AccessToken for MCP
            access_token = AccessToken(
                token=token,
                client_id=user_id,  # Use user_id as client_id
                scopes=all_scopes,
                expires_at=int(exp) if exp else None
            )
            
            logger.info(f"🎉 Successfully created AccessToken for user: {user_id}")
            return access_token
            
        except Exception as e:
            # Log error but don't expose internal details
            logger.error(f"❌ Token validation failed: {e}")
            import traceback
            logger.debug(f"Full error trace:\n{traceback.format_exc()}")
            return None
    
    
    async def _get_user_context(self, user_id: str, payload: Dict[str, Any] = None) -> Optional[MCPUserContext]:
        """
        Get user context, using cache if available.
        
        Args:
            user_id: User ID to get context for
            payload: JWT payload containing user data
            
        Returns:
            User context or None if user not found
        """
        # Check cache
        now = time.time()
        if user_id in self._user_context_cache:
            cache_time = self._cache_timestamps.get(user_id, 0)
            if now - cache_time < self._cache_ttl:
                return self._user_context_cache[user_id]
        
        # Load from repository if available
        if self._user_repository:
            try:
                from fastmcp.auth.domain.value_objects import UserId
                domain_user_id = UserId(user_id)
                user = self._user_repository.find_by_id(domain_user_id)
                
                if user:
                    # Extract role names from UserRole enums
                    role_names = []
                    for role in user.roles:
                        if hasattr(role, 'value'):
                            role_names.append(role.value.lower())
                        else:
                            # Handle string roles or other formats
                            role_str = str(role).lower()
                            if role_str.startswith('userrole.'):
                                role_str = role_str.replace('userrole.', '')
                            role_names.append(role_str)
                    
                    context = MCPUserContext(
                        user_id=str(user.id.value),
                        email=user.email,
                        username=user.username,
                        roles=role_names,
                        scopes=[]  # Scopes come from token
                    )
                    
                    # Cache the context
                    self._user_context_cache[user_id] = context
                    self._cache_timestamps[user_id] = now
                    
                    return context
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to load user {user_id}: {e}")
        
        # Fallback: Create minimal context from token data
        # This allows the system to work even without database access
        fallback_roles = ["user"]  # Default role
        fallback_email = ""
        
        # Extract data from JWT payload if available
        if payload:
            fallback_roles = payload.get("roles", ["user"])
            fallback_email = payload.get("email", "")
        
        return MCPUserContext(
            user_id=user_id,
            email=fallback_email,
            username=user_id,
            roles=fallback_roles,
            scopes=[]
        )
    
    def _map_roles_to_scopes(self, roles: List[str]) -> List[str]:
        """
        Map user roles to resource-specific CRUD scopes.
        
        Args:
            roles: List of user roles
            
        Returns:
            List of resource-specific CRUD scopes
        """
        from ..domain.permissions import ResourceType, PermissionAction
        
        # Define role-based resource permissions
        role_permissions = {
            "admin": {
                # Admin gets full CRUD on all resources
                ResourceType.PROJECTS: [PermissionAction.CREATE, PermissionAction.READ, PermissionAction.UPDATE, PermissionAction.DELETE, PermissionAction.EXECUTE],
                ResourceType.TASKS: [PermissionAction.CREATE, PermissionAction.READ, PermissionAction.UPDATE, PermissionAction.DELETE, PermissionAction.EXECUTE],
                ResourceType.SUBTASKS: [PermissionAction.CREATE, PermissionAction.READ, PermissionAction.UPDATE, PermissionAction.DELETE],
                ResourceType.CONTEXTS: [PermissionAction.CREATE, PermissionAction.READ, PermissionAction.UPDATE, PermissionAction.DELETE, PermissionAction.DELEGATE],
                ResourceType.AGENTS: [PermissionAction.CREATE, PermissionAction.READ, PermissionAction.UPDATE, PermissionAction.DELETE, PermissionAction.EXECUTE],
                ResourceType.BRANCHES: [PermissionAction.CREATE, PermissionAction.READ, PermissionAction.UPDATE, PermissionAction.DELETE],
                ResourceType.MCP: [PermissionAction.CREATE, PermissionAction.READ, PermissionAction.UPDATE, PermissionAction.DELETE, PermissionAction.EXECUTE]
            },
            "developer": {
                # Developer gets CRUD except delete on most resources
                ResourceType.PROJECTS: [PermissionAction.READ, PermissionAction.UPDATE],
                ResourceType.TASKS: [PermissionAction.CREATE, PermissionAction.READ, PermissionAction.UPDATE, PermissionAction.DELETE, PermissionAction.EXECUTE],
                ResourceType.SUBTASKS: [PermissionAction.CREATE, PermissionAction.READ, PermissionAction.UPDATE, PermissionAction.DELETE],
                ResourceType.CONTEXTS: [PermissionAction.CREATE, PermissionAction.READ, PermissionAction.UPDATE, PermissionAction.DELEGATE],
                ResourceType.AGENTS: [PermissionAction.READ, PermissionAction.UPDATE, PermissionAction.EXECUTE],
                ResourceType.BRANCHES: [PermissionAction.CREATE, PermissionAction.READ, PermissionAction.UPDATE, PermissionAction.DELETE],
                ResourceType.MCP: [PermissionAction.READ, PermissionAction.EXECUTE]
            },
            "user": {
                # User gets read access and limited create/update
                ResourceType.PROJECTS: [PermissionAction.READ],
                ResourceType.TASKS: [PermissionAction.CREATE, PermissionAction.READ, PermissionAction.UPDATE],
                ResourceType.SUBTASKS: [PermissionAction.CREATE, PermissionAction.READ, PermissionAction.UPDATE],
                ResourceType.CONTEXTS: [PermissionAction.READ, PermissionAction.UPDATE],
                ResourceType.AGENTS: [PermissionAction.READ],
                ResourceType.BRANCHES: [PermissionAction.READ],
                ResourceType.MCP: [PermissionAction.READ]
            }
        }
        
        scopes = ["mcp:access"]  # Base scope for all authenticated users

        for role in roles:
            role_lower = role.lower()

            # Add legacy admin scopes for admin role compatibility
            if role_lower == "admin":
                scopes.extend(["mcp:admin", "mcp:write"])

            # Add legacy write scope for developer role compatibility
            if role_lower in ["admin", "developer"]:
                scopes.append("mcp:write")

            if role_lower in role_permissions:
                permissions = role_permissions[role_lower]
                for resource_type, actions in permissions.items():
                    for action in actions:
                        scope = f"{resource_type.value}:{action.value}"
                        scopes.append(scope)

        return list(set(scopes))  # Remove duplicates
    
    @property
    def required_scopes(self) -> List[str]:
        """Get the required scopes for this auth backend."""
        return self._required_scopes
    
    def get_current_user_id(self, token: str) -> Optional[str]:
        """
        Extract user ID from token without full validation.
        Useful for filtering operations by user.
        
        Args:
            token: JWT token string
            
        Returns:
            User ID or None
        """
        try:
            # Decode without verification for quick user extraction
            # This is safe for filtering, not for authentication
            import jwt
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload.get("sub")
        except:
            return None


def create_jwt_auth_backend(
    database_session_factory=None,
    required_scopes: Optional[List[str]] = None
) -> JWTAuthBackend:
    """
    Factory function to create JWT auth backend with dependencies.
    
    Args:
        database_session_factory: Database session factory
        required_scopes: Required scopes for MCP access
        
    Returns:
        Configured JWT auth backend
    """
    # Initialize services
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    if not jwt_secret:
        raise ValueError("JWT_SECRET_KEY environment variable not set")
    
    jwt_service = JWTService(secret_key=jwt_secret)
    
    # Initialize repositories if database is available
    user_repository = None
    auth_service = None
    
    if database_session_factory:
        user_repository = UserRepository(database_session_factory)
        # AuthService initialization would go here if needed
    
    return JWTAuthBackend(
        jwt_service=jwt_service,
        auth_service=auth_service,
        user_repository=user_repository,
        required_scopes=required_scopes
    )