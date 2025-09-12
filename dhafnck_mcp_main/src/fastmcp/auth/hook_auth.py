#!/usr/bin/env python3
"""
Hook Authentication System - Separate auth for Claude hooks

This module provides authentication specifically for hook-to-MCP communication,
independent from the main API and MCP authentication systems.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

from jose import jwt, JWTError
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

# Hook-specific JWT configuration from environment
HOOK_JWT_ALGORITHM = os.getenv("HOOK_JWT_ALGORITHM", "HS256")
HOOK_JWT_SECRET = os.getenv("HOOK_JWT_SECRET")

if not HOOK_JWT_SECRET:
    raise ValueError("HOOK_JWT_SECRET environment variable is required for hook authentication")

security = HTTPBearer()


class HookAuthValidator:
    """Validates tokens from Claude hooks (from .mcp.json file)"""
    
    def __init__(self):
        self.algorithm = HOOK_JWT_ALGORITHM
        self.secret = HOOK_JWT_SECRET
        self.logger = logger
        
    def validate_hook_token(self, token: str) -> Dict[str, Any]:
        """
        Validate a hook JWT token
        
        Args:
            token: JWT token from hook request
            
        Returns:
            Decoded token payload if valid
            
        Raises:
            HTTPException: If token is invalid
        """
        try:
            # Decode without verification first to check the structure
            unverified = jwt.get_unverified_claims(token)
            
            # Check if it's a hook/MCP token (has specific fields)
            if unverified.get("type") == "api_token" or unverified.get("iss") == "dhafnck-mcp":
                # This is a hook token, validate with our secret
                try:
                    payload = jwt.decode(
                        token,
                        self.secret,
                        algorithms=[self.algorithm]
                    )
                    
                    # Check expiration
                    if "exp" in payload:
                        exp_timestamp = payload["exp"]
                        if datetime.now().timestamp() > exp_timestamp:
                            raise HTTPException(status_code=401, detail="Token expired")
                    
                    self.logger.info(f"Hook token validated successfully: {payload.get('sub', 'unknown')}")
                    return payload
                    
                except JWTError as e:
                    self.logger.warning(f"Hook token validation failed: {e}")
                    # Token structure is correct but signature invalid
                    # For development, we can be lenient
                    if os.getenv("AUTH_ENABLED", "true").lower() == "false":
                        self.logger.warning("AUTH_ENABLED=false, allowing invalid signature")
                        return unverified
                    raise HTTPException(status_code=401, detail="Invalid hook token signature")
            else:
                raise HTTPException(status_code=401, detail="Not a valid hook token")
                
        except JWTError as e:
            self.logger.error(f"Token decode error: {e}")
            raise HTTPException(status_code=401, detail="Invalid token format")
        except Exception as e:
            self.logger.error(f"Unexpected auth error: {e}")
            raise HTTPException(status_code=500, detail="Authentication error")


# Global validator instance
hook_auth_validator = HookAuthValidator()


async def get_hook_authenticated_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    FastAPI dependency for hook authentication
    
    Returns user data from validated hook token
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="No authentication provided")
    
    token = credentials.credentials
    user_data = hook_auth_validator.validate_hook_token(token)
    
    # Add hook-specific metadata
    user_data["auth_type"] = "hook"
    user_data["auth_method"] = "jwt_token"
    
    return user_data


def is_hook_request(request_headers: dict) -> bool:
    """
    Check if a request is coming from a Claude hook
    
    Args:
        request_headers: Request headers
        
    Returns:
        True if this appears to be a hook request
    """
    # Check for specific headers that hooks might send
    user_agent = request_headers.get("user-agent", "").lower()
    
    # Hooks typically use python requests or similar
    hook_indicators = [
        "python",
        "requests",
        "aiohttp",
        "httpx",
        "claude-hook",
        "mcp-client"
    ]
    
    return any(indicator in user_agent for indicator in hook_indicators)


def get_token_from_mcp_json() -> Optional[str]:
    """
    Extract the Bearer token from .mcp.json file if available
    
    Returns:
        Token string if found, None otherwise
    """
    try:
        # Look for .mcp.json in project root
        project_root = Path(__file__).parent.parent.parent.parent.parent
        mcp_json_path = project_root / ".mcp.json"
        
        if mcp_json_path.exists():
            with open(mcp_json_path, 'r') as f:
                mcp_config = json.load(f)
                
            # Extract token from dhafnck_mcp_http configuration
            dhafnck_config = mcp_config.get("mcpServers", {}).get("dhafnck_mcp_http", {})
            auth_header = dhafnck_config.get("headers", {}).get("Authorization", "")
            
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]  # Remove "Bearer " prefix
                logger.info("Found token in .mcp.json")
                return token
                
    except Exception as e:
        logger.debug(f"Could not read .mcp.json token: {e}")
    
    return None


def create_hook_token(user_id: str = "hook-user", expires_in_days: int = 30) -> str:
    """
    Create a new hook authentication token
    
    Args:
        user_id: User identifier for the hook
        expires_in_days: Token validity period
        
    Returns:
        JWT token string
    """
    now = datetime.utcnow()
    expire = now + timedelta(days=expires_in_days)
    
    payload = {
        "sub": user_id,
        "type": "api_token",
        "iss": "dhafnck-mcp",
        "aud": "mcp-server",
        "iat": now.timestamp(),
        "exp": expire.timestamp(),
        "jti": f"hook_{int(now.timestamp())}",
        "scopes": [
            "mcp-api",
            "tasks:read",
            "tasks:create",
            "tasks:update",
            "contexts:read",
            "projects:read",
            "branches:read"
        ]
    }
    
    # Use environment variables for JWT configuration
    token = jwt.encode(payload, HOOK_JWT_SECRET, algorithm=HOOK_JWT_ALGORITHM)
    logger.info(f"Created hook token for user {user_id} with algorithm {HOOK_JWT_ALGORITHM}")
    return token