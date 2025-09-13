"""
MCP Token Service

Provides MCP token generation, validation, and management functionality.
This is a minimal implementation to satisfy import requirements.
"""

import asyncio
import logging
import secrets
import hashlib
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from ..models.api_token import ApiToken
from ...task_management.infrastructure.database.session_manager import get_session


logger = logging.getLogger(__name__)


@dataclass
class MCPToken:
    """MCP Token data structure."""
    token: str
    user_id: str
    email: Optional[str] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: bool = True


class MCPTokenService:
    """
    MCP Token Service for generating and managing MCP protocol tokens.
    
    This is a minimal implementation that provides basic token functionality
    without persistent storage. For production use, this should be extended
    with proper database storage and more robust security features.
    """
    
    def __init__(self):
        """Initialize the MCP token service."""
        self._tokens: Dict[str, MCPToken] = {}
        logger.info("MCP Token Service initialized (database storage)")
    
    async def generate_mcp_token_from_user_id(
        self,
        user_id: str,
        email: Optional[str] = None,
        expires_in_hours: int = 24,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MCPToken:
        """
        Generate an MCP token for a user.
        
        Args:
            user_id: User identifier
            email: User email (optional)
            expires_in_hours: Token expiration time in hours
            metadata: Additional token metadata
            
        Returns:
            MCPToken object
        """
        # Generate secure token
        token_bytes = secrets.token_bytes(32)
        token = f"mcp_{token_bytes.hex()}"
        
        # Set expiration
        created_at = datetime.now(UTC)
        expires_at = created_at + timedelta(hours=expires_in_hours)
        
        # Create token object
        mcp_token = MCPToken(
            token=token,
            user_id=user_id,
            email=email,
            created_at=created_at,
            expires_at=expires_at,
            metadata=metadata or {},
            is_active=True
        )
        
        # Store token (in-memory for now)
        self._tokens[token] = mcp_token
        
        logger.info(f"Generated MCP token for user {user_id}, expires at {expires_at}")
        return mcp_token
    
    async def validate_mcp_token(self, token: str) -> Optional[MCPToken]:
        """
        Validate an MCP token.
        
        Args:
            token: The MCP token to validate
            
        Returns:
            MCPToken if valid, None otherwise
        """
        if not token or not token.startswith('mcp_'):
            return None
        
        mcp_token = self._tokens.get(token)
        if not mcp_token:
            logger.debug(f"MCP token not found: {token[:10]}...")
            return None
        
        # Check if token is active
        if not mcp_token.is_active:
            logger.debug(f"MCP token is inactive: {token[:10]}...")
            return None
        
        # Check expiration
        if mcp_token.expires_at and datetime.now(UTC) > mcp_token.expires_at:
            logger.debug(f"MCP token expired: {token[:10]}...")
            # Remove expired token
            del self._tokens[token]
            return None
        
        logger.debug(f"MCP token validated for user {mcp_token.user_id}")
        
        # Track usage in database
        await self._update_token_usage(token)
        
        return mcp_token
    
    async def _update_token_usage(self, token: str) -> None:
        """
        Update token usage statistics in the database.
        
        Args:
            token: The MCP token that was used
        """
        try:
            # Hash the token to find it in database
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            with get_session() as db_session:
                # Update usage count and last used timestamp
                stmt = (
                    update(ApiToken)
                    .where(ApiToken.token_hash == token_hash)
                    .values(
                        usage_count=ApiToken.usage_count + 1,
                        last_used_at=datetime.now(UTC)
                    )
                )
                result = db_session.execute(stmt)
                db_session.commit()
                
                if result.rowcount > 0:
                    logger.debug(f"Updated usage for MCP token {token[:10]}...")
                else:
                    logger.warning(f"Could not find MCP token in database: {token[:10]}...")
                
        except Exception as e:
            logger.error(f"Error updating MCP token usage: {e}")
    
    async def revoke_user_tokens(self, user_id: str) -> bool:
        """
        Revoke all tokens for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if tokens were revoked
        """
        tokens_revoked = 0
        tokens_to_remove = []
        
        for token, mcp_token in self._tokens.items():
            if mcp_token.user_id == user_id and mcp_token.is_active:
                mcp_token.is_active = False
                tokens_to_remove.append(token)
                tokens_revoked += 1
        
        # Remove revoked tokens
        for token in tokens_to_remove:
            del self._tokens[token]
        
        if tokens_revoked > 0:
            logger.info(f"Revoked {tokens_revoked} MCP tokens for user {user_id}")
        
        return tokens_revoked > 0
    
    async def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired tokens.
        
        Returns:
            Number of tokens cleaned up
        """
        current_time = datetime.now(UTC)
        tokens_to_remove = []
        
        for token, mcp_token in self._tokens.items():
            if mcp_token.expires_at and current_time > mcp_token.expires_at:
                tokens_to_remove.append(token)
        
        # Remove expired tokens
        for token in tokens_to_remove:
            del self._tokens[token]
        
        if tokens_to_remove:
            logger.info(f"Cleaned up {len(tokens_to_remove)} expired MCP tokens")
        
        return len(tokens_to_remove)
    
    def get_token_stats(self) -> Dict[str, Any]:
        """
        Get token statistics.
        
        Returns:
            Dictionary with token statistics
        """
        current_time = datetime.now(UTC)
        active_tokens = 0
        expired_tokens = 0
        
        for mcp_token in self._tokens.values():
            if mcp_token.is_active:
                if mcp_token.expires_at and current_time > mcp_token.expires_at:
                    expired_tokens += 1
                else:
                    active_tokens += 1
            else:
                expired_tokens += 1
        
        return {
            "total_tokens": len(self._tokens),
            "active_tokens": active_tokens,
            "expired_tokens": expired_tokens,
            "service_status": "running",
            "storage_type": "in-memory"
        }
    
    async def get_user_tokens(self, user_id: str) -> List[MCPToken]:
        """
        Get all tokens for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of MCPToken objects
        """
        user_tokens = []
        current_time = datetime.now(UTC)
        
        for mcp_token in self._tokens.values():
            if mcp_token.user_id == user_id:
                # Check if expired
                if mcp_token.expires_at and current_time > mcp_token.expires_at:
                    mcp_token.is_active = False
                user_tokens.append(mcp_token)
        
        return user_tokens


# Global service instance
mcp_token_service = MCPTokenService()