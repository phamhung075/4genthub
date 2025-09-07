"""
MCP Keycloak Token Validator

Validates Keycloak tokens for MCP connections.
Ensures proper authentication and authorization for MCP tools.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import httpx
from jose import jwt, JWTError
import asyncio
from functools import lru_cache

logger = logging.getLogger(__name__)

class MCPKeycloakValidator:
    """
    Validates Keycloak tokens specifically for MCP connections.
    Integrates with MCP tools to ensure proper authentication.
    """
    
    def __init__(self):
        """Initialize the MCP Keycloak validator."""
        self.keycloak_url = os.getenv("KEYCLOAK_URL")
        self.realm = os.getenv("KEYCLOAK_REALM", "dhafnck-mcp")
        self.client_id = os.getenv("KEYCLOAK_CLIENT_ID", "mcp-backend")
        self.client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET")
        
        # Build endpoints
        self.realm_url = f"{self.keycloak_url}/realms/{self.realm}"
        self.jwks_uri = f"{self.realm_url}/protocol/openid-connect/certs"
        self.introspect_endpoint = f"{self.realm_url}/protocol/openid-connect/token/introspect"
        
        # Cache for JWKS and validated tokens
        self._jwks_cache = None
        self._jwks_cache_time = None
        self._token_cache = {}
        self._cache_ttl = int(os.getenv("KEYCLOAK_TOKEN_CACHE_TTL", "300"))
        
        logger.info(f"MCP Keycloak validator initialized for realm: {self.realm}")
    
    async def validate_mcp_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate a token for MCP access.
        
        Args:
            token: Bearer token from MCP request
            
        Returns:
            Token claims if valid, None otherwise
        """
        # Check cache first
        cached = self._get_cached_validation(token)
        if cached is not None:
            return cached
        
        try:
            # Get JWKS for validation
            jwks = await self._get_jwks()
            if not jwks:
                logger.error("Failed to retrieve JWKS from Keycloak")
                return None
            
            # Decode and validate token
            claims = await self._decode_token(token, jwks)
            if not claims:
                return None
            
            # Validate MCP-specific requirements
            if not self._validate_mcp_requirements(claims):
                logger.warning("Token does not meet MCP requirements")
                return None
            
            # Cache successful validation
            self._cache_validation(token, claims)
            
            return claims
            
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return None
    
    async def introspect_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Introspect token with Keycloak server for detailed validation.
        
        Args:
            token: Token to introspect
            
        Returns:
            Introspection result if token is active
        """
        try:
            async with httpx.AsyncClient() as client:
                data = {
                    "token": token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                }
                
                response = await client.post(
                    self.introspect_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("active"):
                        return result
                        
            return None
            
        except Exception as e:
            logger.error(f"Token introspection error: {e}")
            return None
    
    def extract_user_info(self, claims: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract user information from token claims.
        
        Args:
            claims: JWT token claims
            
        Returns:
            User information dictionary
        """
        return {
            "user_id": claims.get("sub"),
            "username": claims.get("preferred_username"),
            "email": claims.get("email"),
            "name": claims.get("name"),
            "given_name": claims.get("given_name"),
            "family_name": claims.get("family_name"),
            "email_verified": claims.get("email_verified", False),
            "roles": self._extract_roles(claims),
            "mcp_permissions": self._extract_mcp_permissions(claims)
        }
    
    def _extract_roles(self, claims: Dict[str, Any]) -> List[str]:
        """Extract user roles from token claims."""
        roles = []
        
        # Realm roles
        realm_access = claims.get("realm_access", {})
        roles.extend(realm_access.get("roles", []))
        
        # Client-specific roles
        resource_access = claims.get("resource_access", {})
        client_roles = resource_access.get(self.client_id, {})
        roles.extend(client_roles.get("roles", []))
        
        return list(set(roles))
    
    def _extract_mcp_permissions(self, claims: Dict[str, Any]) -> List[str]:
        """
        Extract MCP-specific permissions from token.
        
        Args:
            claims: Token claims
            
        Returns:
            List of MCP permissions
        """
        permissions = []
        roles = self._extract_roles(claims)
        
        # Map roles to MCP permissions
        role_permissions = {
            "admin": ["mcp:*"],
            "developer": ["mcp:read", "mcp:write", "mcp:execute"],
            "user": ["mcp:read", "mcp:execute"],
            "viewer": ["mcp:read"]
        }
        
        for role in roles:
            if role in role_permissions:
                permissions.extend(role_permissions[role])
        
        # Check for custom MCP permissions in token
        custom_permissions = claims.get("mcp_permissions", [])
        if isinstance(custom_permissions, list):
            permissions.extend(custom_permissions)
        
        return list(set(permissions))
    
    def _validate_mcp_requirements(self, claims: Dict[str, Any]) -> bool:
        """
        Validate that token meets MCP-specific requirements.
        
        Args:
            claims: Token claims
            
        Returns:
            True if token meets requirements
        """
        # Check token is not expired
        exp = claims.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.now():
            logger.warning("Token is expired")
            return False
        
        # Check audience if configured
        if os.getenv("KEYCLOAK_VERIFY_TOKEN_AUDIENCE", "true").lower() == "true":
            audience = claims.get("aud")
            expected_audience = os.getenv("KEYCLOAK_TOKEN_AUDIENCE", self.client_id)
            
            if isinstance(audience, list):
                if expected_audience not in audience:
                    logger.warning(f"Invalid audience: {audience}")
                    return False
            elif audience != expected_audience:
                logger.warning(f"Invalid audience: {audience}")
                return False
        
        # Check required MCP claims
        required_claims = ["sub", "iat", "exp"]
        for claim in required_claims:
            if claim not in claims:
                logger.warning(f"Missing required claim: {claim}")
                return False
        
        # Check user has at least one MCP permission
        permissions = self._extract_mcp_permissions(claims)
        if not permissions:
            logger.warning("No MCP permissions found in token")
            return False
        
        return True
    
    async def _get_jwks(self) -> Optional[Dict[str, Any]]:
        """Get JSON Web Key Set from Keycloak."""
        # Check cache
        if self._jwks_cache and self._jwks_cache_time:
            cache_age = (datetime.now() - self._jwks_cache_time).seconds
            if cache_age < 3600:  # 1 hour cache
                return self._jwks_cache
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_uri)
                
                if response.status_code == 200:
                    self._jwks_cache = response.json()
                    self._jwks_cache_time = datetime.now()
                    return self._jwks_cache
                    
            return None
            
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            return None
    
    async def _decode_token(self, token: str, jwks: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Decode and validate JWT token.
        
        Args:
            token: JWT token
            jwks: JSON Web Key Set
            
        Returns:
            Token claims if valid
        """
        try:
            # Get unverified header to find key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            # Find the correct key
            key = None
            for jwk in jwks.get("keys", []):
                if jwk.get("kid") == kid:
                    key = jwk
                    break
            
            if not key:
                logger.error(f"Key {kid} not found in JWKS")
                return None
            
            # Decode with verification
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=os.getenv("KEYCLOAK_TOKEN_AUDIENCE", self.client_id),
                issuer=f"{self.realm_url}"
            )
            
            return claims
            
        except JWTError as e:
            logger.error(f"JWT decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"Token decode error: {e}")
            return None
    
    def _get_cached_validation(self, token: str) -> Optional[Dict[str, Any]]:
        """Get cached validation result."""
        cached = self._token_cache.get(token)
        if cached:
            cache_time, claims = cached
            if (datetime.now() - cache_time).seconds < self._cache_ttl:
                return claims
            else:
                # Remove expired cache entry
                del self._token_cache[token]
        return None
    
    def _cache_validation(self, token: str, claims: Dict[str, Any]) -> None:
        """Cache validation result."""
        self._token_cache[token] = (datetime.now(), claims)
        
        # Clean old cache entries
        self._clean_cache()
    
    def _clean_cache(self) -> None:
        """Remove expired cache entries."""
        now = datetime.now()
        expired = []
        
        for token, (cache_time, _) in self._token_cache.items():
            if (now - cache_time).seconds > self._cache_ttl:
                expired.append(token)
        
        for token in expired:
            del self._token_cache[token]


# Global validator instance
_validator = None

def get_mcp_validator() -> MCPKeycloakValidator:
    """Get the global MCP Keycloak validator instance."""
    global _validator
    if _validator is None:
        _validator = MCPKeycloakValidator()
    return _validator


async def validate_mcp_request(authorization: str) -> Optional[Dict[str, Any]]:
    """
    Validate an MCP request authorization header.
    
    Args:
        authorization: Authorization header value (e.g., "Bearer token")
        
    Returns:
        User info if valid, None otherwise
    """
    if not authorization:
        return None
    
    # Extract token from Bearer scheme
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    token = parts[1]
    
    # Validate token
    validator = get_mcp_validator()
    claims = await validator.validate_mcp_token(token)
    
    if claims:
        return validator.extract_user_info(claims)
    
    return None