"""
Keycloak Service Account Authentication for MCP Hooks

This module provides service account authentication for MCP hooks and automated processes.
It handles client credentials flow, token caching, and automatic refresh.
"""

import os
import logging
import asyncio
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from functools import lru_cache
import httpx
import jwt
from jwt import PyJWKClient
import hashlib
import threading
import time

logger = logging.getLogger(__name__)

@dataclass
class ServiceAccountConfig:
    """Service account configuration"""
    keycloak_url: str
    realm: str
    client_id: str
    client_secret: str
    scopes: List[str] = None
    
    def __post_init__(self):
        if not self.scopes:
            self.scopes = ["openid", "profile", "email", "mcp:read", "mcp:write"]

@dataclass
class ServiceToken:
    """Service account token data"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int = 300
    scope: str = ""
    created_at: datetime = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow()
    
    @property
    def expires_at(self) -> datetime:
        """Calculate token expiration time"""
        return self.created_at + timedelta(seconds=self.expires_in)
    
    @property
    def is_expired(self) -> bool:
        """Check if token has expired (with 30 second buffer)"""
        buffer_seconds = 30
        expiry_with_buffer = self.expires_at - timedelta(seconds=buffer_seconds)
        return datetime.utcnow() >= expiry_with_buffer
    
    @property
    def seconds_until_expiry(self) -> int:
        """Get seconds until token expires"""
        delta = self.expires_at - datetime.utcnow()
        return max(0, int(delta.total_seconds()))

class ServiceAccountAuth:
    """
    Keycloak Service Account Authentication for MCP.
    
    Handles client credentials flow for service-to-service authentication,
    token caching, automatic refresh, and secure credential management.
    """
    
    def __init__(self, config: Optional[ServiceAccountConfig] = None):
        """Initialize service account authentication"""
        self.config = config or self._load_config_from_env()
        self._validate_config()
        
        # Build endpoint URLs
        self.realm_url = f"{self.config.keycloak_url}/realms/{self.config.realm}"
        self.token_endpoint = f"{self.realm_url}/protocol/openid-connect/token"
        self.userinfo_endpoint = f"{self.realm_url}/protocol/openid-connect/userinfo"
        self.jwks_endpoint = f"{self.realm_url}/protocol/openid-connect/certs"
        
        # HTTP client configuration
        self.client = httpx.AsyncClient(
            timeout=30.0,
            verify=True,  # Always verify SSL in production
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
        
        # Token management
        self._current_token: Optional[ServiceToken] = None
        self._token_lock = threading.RLock()
        self._refresh_task: Optional[asyncio.Task] = None
        
        # JWKS client for token validation
        self._jwks_client: Optional[PyJWKClient] = None
        
        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 1  # 1 second between requests
        
        logger.info(f"✅ Service account auth initialized for client: {self.config.client_id}")
    
    def _load_config_from_env(self) -> ServiceAccountConfig:
        """Load service account configuration from environment variables"""
        return ServiceAccountConfig(
            keycloak_url=os.getenv("KEYCLOAK_URL"),
            realm=os.getenv("KEYCLOAK_REALM", "dhafnck-mcp"),
            client_id=os.getenv("KEYCLOAK_SERVICE_CLIENT_ID", "mcp-service-account"),
            client_secret=os.getenv("KEYCLOAK_SERVICE_CLIENT_SECRET"),
            scopes=os.getenv("KEYCLOAK_SERVICE_SCOPES", "openid profile email mcp:read mcp:write").split()
        )
    
    def _validate_config(self):
        """Validate service account configuration"""
        required_fields = ['keycloak_url', 'realm', 'client_id', 'client_secret']
        
        for field in required_fields:
            value = getattr(self.config, field)
            if not value:
                raise ValueError(
                    f"Missing required service account configuration: {field.upper()}. "
                    f"Please set KEYCLOAK_{field.upper()} environment variable."
                )
        
        # Remove trailing slash from URL
        self.config.keycloak_url = self.config.keycloak_url.rstrip("/")
    
    @property
    def jwks_client(self) -> PyJWKClient:
        """Get or create JWKS client for token validation"""
        if self._jwks_client is None:
            self._jwks_client = PyJWKClient(
                self.jwks_endpoint,
                cache_keys=True,
                lifespan=3600  # 1 hour
            )
        return self._jwks_client
    
    async def _rate_limit(self):
        """Simple rate limiting to prevent overwhelming Keycloak"""
        now = time.time()
        elapsed = now - self._last_request_time
        
        if elapsed < self._min_request_interval:
            sleep_time = self._min_request_interval - elapsed
            await asyncio.sleep(sleep_time)
        
        self._last_request_time = time.time()
    
    async def authenticate(self, force_refresh: bool = False) -> Optional[ServiceToken]:
        """
        Authenticate service account and get access token.
        
        Args:
            force_refresh: Force token refresh even if current token is valid
            
        Returns:
            ServiceToken if successful, None otherwise
        """
        async with asyncio.Lock():
            # Check if current token is still valid
            if not force_refresh and self._current_token and not self._current_token.is_expired:
                logger.debug("Using cached service account token")
                return self._current_token
            
            # Rate limiting
            await self._rate_limit()
            
            try:
                # Prepare client credentials request
                data = {
                    "grant_type": "client_credentials",
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "scope": " ".join(self.config.scopes)
                }
                
                logger.debug(f"Requesting service account token for client: {self.config.client_id}")
                
                response = await self.client.post(
                    self.token_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    
                    # Create service token
                    self._current_token = ServiceToken(
                        access_token=token_data["access_token"],
                        refresh_token=token_data.get("refresh_token"),
                        token_type=token_data.get("token_type", "Bearer"),
                        expires_in=token_data.get("expires_in", 300),
                        scope=token_data.get("scope", ""),
                        created_at=datetime.utcnow()
                    )
                    
                    logger.info(f"✅ Service account authenticated successfully. Token expires in {self._current_token.expires_in}s")
                    
                    # Start automatic refresh if not already running
                    self._start_token_refresh_task()
                    
                    return self._current_token
                
                else:
                    error_data = response.json() if response.content else {}
                    error_msg = error_data.get("error_description", f"HTTP {response.status_code}")
                    logger.error(f"Service account authentication failed: {error_msg}")
                    return None
                    
            except Exception as e:
                logger.error(f"Service account authentication error: {e}")
                return None
    
    def _start_token_refresh_task(self):
        """Start background task to refresh tokens automatically"""
        if self._refresh_task and not self._refresh_task.done():
            return  # Already running
        
        self._refresh_task = asyncio.create_task(self._token_refresh_loop())
    
    async def _token_refresh_loop(self):
        """Background loop to refresh tokens before expiry"""
        try:
            while self._current_token:
                if self._current_token.is_expired:
                    logger.info("Token expired, refreshing...")
                    await self.authenticate(force_refresh=True)
                
                # Sleep until 30 seconds before expiry
                sleep_seconds = max(30, self._current_token.seconds_until_expiry - 30)
                await asyncio.sleep(sleep_seconds)
                
        except asyncio.CancelledError:
            logger.debug("Token refresh task cancelled")
        except Exception as e:
            logger.error(f"Error in token refresh loop: {e}")
    
    async def get_valid_token(self) -> Optional[str]:
        """
        Get a valid access token, refreshing if necessary.
        
        Returns:
            Valid access token string or None
        """
        token = await self.authenticate()
        return token.access_token if token else None
    
    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate a service account token.
        
        Args:
            token: JWT token to validate
            
        Returns:
            Token payload if valid, None otherwise
        """
        try:
            # Get signing key
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            
            # Validate token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.config.client_id,
                issuer=f"{self.realm_url}"
            )
            
            # Additional service account validation
            if payload.get("typ") != "Bearer":
                logger.warning("Token is not a Bearer token")
                return None
            
            if payload.get("azp") != self.config.client_id:
                logger.warning(f"Token not authorized for client: {self.config.client_id}")
                return None
                
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.debug("Service account token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid service account token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return None
    
    async def get_service_info(self) -> Optional[Dict[str, Any]]:
        """
        Get service account information from Keycloak.
        
        Returns:
            Service account info or None
        """
        token = await self.get_valid_token()
        if not token:
            return None
        
        try:
            response = await self.client.get(
                self.userinfo_endpoint,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                return response.json()
            
            logger.warning(f"Failed to get service info: HTTP {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get service info: {e}")
            return None
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authorization headers for authenticated requests.
        
        Note: This is a sync method for convenience, but it won't refresh expired tokens.
        Use get_valid_token() for async token management.
        
        Returns:
            Dictionary with Authorization header
        """
        if self._current_token and not self._current_token.is_expired:
            return {"Authorization": f"Bearer {self._current_token.access_token}"}
        return {}
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check service account authentication health.
        
        Returns:
            Health status information
        """
        health = {
            "service_account_configured": bool(self.config.client_id and self.config.client_secret),
            "token_available": bool(self._current_token),
            "token_valid": False,
            "token_expires_in": 0,
            "keycloak_reachable": False,
            "last_auth_success": None,
            "configuration": {
                "keycloak_url": self.config.keycloak_url,
                "realm": self.config.realm,
                "client_id": self.config.client_id,
                "scopes": self.config.scopes
            }
        }
        
        # Check token status
        if self._current_token:
            health["token_valid"] = not self._current_token.is_expired
            health["token_expires_in"] = self._current_token.seconds_until_expiry
            health["last_auth_success"] = self._current_token.created_at.isoformat()
        
        # Check Keycloak connectivity
        try:
            response = await self.client.get(f"{self.realm_url}/.well-known/openid-configuration")
            health["keycloak_reachable"] = response.status_code == 200
        except Exception as e:
            health["keycloak_error"] = str(e)
        
        return health
    
    async def close(self):
        """Clean up resources"""
        # Cancel refresh task
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
        
        # Close HTTP client
        await self.client.aclose()
        
        logger.info("Service account auth closed")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.authenticate()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


# Singleton instance for easy access
_service_auth_instance: Optional[ServiceAccountAuth] = None

def get_service_account_auth() -> ServiceAccountAuth:
    """
    Get or create singleton service account auth instance.
    
    Returns:
        ServiceAccountAuth instance
    """
    global _service_auth_instance
    if _service_auth_instance is None:
        _service_auth_instance = ServiceAccountAuth()
    return _service_auth_instance

async def authenticate_service_request(authorization_header: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Authenticate a service request using service account token.
    
    Args:
        authorization_header: Authorization header from request
        
    Returns:
        Service account context if valid, None otherwise
    """
    if not authorization_header:
        return None
    
    # Extract token from header
    parts = authorization_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    token = parts[1]
    
    # Validate with service account auth
    auth = get_service_account_auth()
    payload = await auth.validate_token(token)
    
    if not payload:
        return None
    
    # Build service context
    return {
        "service_account": True,
        "client_id": payload.get("azp"),
        "subject": payload.get("sub"),
        "scopes": payload.get("scope", "").split(),
        "authenticated": True,
        "auth_provider": "keycloak_service_account",
        "token_exp": payload.get("exp"),
        "permissions": ["mcp:*"]  # Service accounts have full permissions
    }