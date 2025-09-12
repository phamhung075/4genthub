"""
Token Application Facade

This facade handles all token-related operations following DDD architecture.
It provides a clean interface between the API controllers and the domain/infrastructure layers,
ensuring proper separation of concerns and no direct database access from controllers.
"""

import logging
import os
import secrets
import hashlib
import jwt
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from fastmcp.auth.domain.services.jwt_service import JWTService
from fastmcp.auth.services.mcp_token_service import mcp_token_service
from fastmcp.task_management.domain.repositories.token_repository_interface import ITokenRepository
# Repository is injected via factory - no direct infrastructure import

logger = logging.getLogger(__name__)


class TokenApplicationFacade:
    """
    Application facade for token management operations.
    
    This facade orchestrates token operations across domain services and repositories,
    ensuring proper DDD layering and no direct database access from upper layers.
    """
    
    def __init__(self, token_repository: Optional[ITokenRepository] = None):
        """
        Initialize the token facade with required services and repositories.
        
        Args:
            token_repository: Token repository instance (injected dependency)
        """
        # Get JWT secret from environment
        jwt_secret = os.getenv("JWT_SECRET_KEY")
        if not jwt_secret:
            logger.error("JWT_SECRET_KEY not configured in environment")
            raise ValueError("JWT_SECRET_KEY must be set in environment")
            
        self.jwt_service = JWTService(secret_key=jwt_secret)
        self.mcp_token_service = mcp_token_service
        self._token_repository = token_repository
    
    def _get_repository(self, session: Session) -> ITokenRepository:
        """
        Get or create a token repository instance.
        
        Note: This method should be removed once proper factory injection is set up.
        Currently creates a repository if none was injected.
        """
        if self._token_repository is None and session:
            # Import repository from infrastructure layer
            from ...infrastructure.repositories.token_repository import TokenRepository
            self._token_repository = TokenRepository(session)
        return self._token_repository
    
    async def generate_mcp_token_from_user(
        self,
        user_id: str,
        email: str,
        expires_in_hours: int,
        metadata: Optional[Dict[str, Any]] = None,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Generate an MCP token for a user.
        
        Delegates to the MCP token service for actual token generation.
        """
        try:
            # Delegate to MCP token service
            mcp_token_obj = await self.mcp_token_service.generate_mcp_token_from_user_id(
                user_id=user_id,
                email=email,
                expires_in_hours=expires_in_hours,
                metadata=metadata or {}
            )
            
            return {
                "success": True,
                "token": mcp_token_obj.token,
                "expires_at": mcp_token_obj.expires_at.isoformat() if mcp_token_obj.expires_at else None,
                "token_id": mcp_token_obj.token_id
            }
            
        except Exception as e:
            logger.error(f"Error generating MCP token for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def revoke_user_tokens(self, user_id: str) -> Dict[str, Any]:
        """
        Revoke all tokens for a user.
        
        Delegates to the MCP token service.
        """
        try:
            success = await self.mcp_token_service.revoke_user_tokens(user_id)
            
            return {
                "success": success,
                "revoked": success,
                "message": "All tokens revoked successfully" if success else "No tokens found to revoke"
            }
            
        except Exception as e:
            logger.error(f"Error revoking tokens for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_token_stats(self) -> Dict[str, Any]:
        """
        Get token statistics.
        
        Delegates to the MCP token service.
        """
        try:
            stats = self.mcp_token_service.get_token_stats()
            
            return {
                "success": True,
                "stats": stats
            }
            
        except Exception as e:
            logger.error(f"Error getting token stats: {e}")
            return {
                "success": False,
                "error": str(e),
                "stats": {}
            }
    
    async def cleanup_expired_tokens(self) -> Dict[str, Any]:
        """
        Clean up expired tokens.
        
        Delegates to the MCP token service.
        """
        try:
            cleaned_count = await self.mcp_token_service.cleanup_expired_tokens()
            
            return {
                "success": True,
                "cleaned_count": cleaned_count,
                "message": f"Cleaned up {cleaned_count} expired tokens"
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up tokens: {e}")
            return {
                "success": False,
                "error": str(e),
                "cleaned_count": 0
            }
    
    async def create_api_token(
        self,
        user_id: str,
        name: str,
        scopes: List[str],
        expires_in_days: int,
        rate_limit: Optional[int],
        metadata: Optional[Dict[str, Any]],
        session: Session
    ) -> Dict[str, Any]:
        """
        Create an API token with database persistence.
        
        Uses repository pattern for database operations.
        """
        try:
            repository = self._get_repository(session)
            
            # Generate unique token ID
            token_id = f"tok_{secrets.token_hex(8)}"
            
            # Generate JWT token
            jwt_token = self.jwt_service.generate_token(
                user_id=user_id,
                scopes=scopes,
                expires_in_days=expires_in_days,
                token_id=token_id
            )
            
            # Calculate expiration
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
            
            # Hash token for secure storage
            token_hash = hashlib.sha256(jwt_token.encode()).hexdigest()
            
            # Create token via repository
            token_data = {
                "id": token_id,
                "user_id": user_id,
                "name": name,
                "token_hash": token_hash,
                "scopes": scopes,
                "expires_at": expires_at,
                "rate_limit": rate_limit or 1000,
                "token_metadata": metadata or {}
            }
            
            created_token = await repository.create_token(token_data)
            
            if created_token:
                return {
                    "success": True,
                    "token": {
                        "id": created_token.id,
                        "name": created_token.name,
                        "token": jwt_token,  # Include JWT token (only shown once)
                        "scopes": created_token.scopes,
                        "created_at": created_token.created_at.isoformat() if created_token.created_at else None,
                        "expires_at": created_token.expires_at.isoformat() if created_token.expires_at else None,
                        "rate_limit": created_token.rate_limit,
                        "is_active": created_token.is_active
                    }
                }
            
            return {
                "success": False,
                "error": "Failed to create token"
            }
            
        except Exception as e:
            logger.error(f"Error creating API token: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_user_tokens(
        self,
        user_id: str,
        session: Session,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        List tokens for a user.
        
        Uses repository pattern for database operations.
        """
        try:
            repository = self._get_repository(session)
            
            tokens = await repository.get_user_tokens(user_id, skip, limit)
            total = await repository.count_user_tokens(user_id)
            
            # Convert to response format (without exposing actual tokens)
            token_list = [
                {
                    "id": token.id,
                    "name": token.name,
                    "scopes": token.scopes,
                    "created_at": token.created_at.isoformat() if token.created_at else None,
                    "expires_at": token.expires_at.isoformat() if token.expires_at else None,
                    "last_used_at": token.last_used_at.isoformat() if token.last_used_at else None,
                    "usage_count": token.usage_count,
                    "rate_limit": token.rate_limit,
                    "is_active": token.is_active
                }
                for token in tokens
            ]
            
            return {
                "success": True,
                "tokens": token_list,
                "total": total
            }
            
        except Exception as e:
            logger.error(f"Error listing user tokens: {e}")
            return {
                "success": False,
                "error": str(e),
                "tokens": [],
                "total": 0
            }
    
    async def get_token_details(
        self,
        token_id: str,
        user_id: str,
        session: Session
    ) -> Dict[str, Any]:
        """
        Get details for a specific token.
        
        Uses repository pattern for database operations.
        """
        try:
            repository = self._get_repository(session)
            
            token = await repository.get_token(token_id, user_id)
            
            if not token:
                return {
                    "success": False,
                    "error": "Token not found"
                }
            
            return {
                "success": True,
                "token": {
                    "id": token.id,
                    "name": token.name,
                    "scopes": token.scopes,
                    "created_at": token.created_at.isoformat() if token.created_at else None,
                    "expires_at": token.expires_at.isoformat() if token.expires_at else None,
                    "last_used_at": token.last_used_at.isoformat() if token.last_used_at else None,
                    "usage_count": token.usage_count,
                    "rate_limit": token.rate_limit,
                    "is_active": token.is_active,
                    "metadata": token.token_metadata if hasattr(token, 'token_metadata') else {}
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting token details: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def revoke_token(
        self,
        token_id: str,
        user_id: str,
        session: Session
    ) -> Dict[str, Any]:
        """
        Revoke a specific token.
        
        Uses repository pattern for database operations.
        """
        try:
            repository = self._get_repository(session)
            
            success = await repository.revoke_token(token_id, user_id)
            
            if success:
                return {
                    "success": True,
                    "message": "Token revoked successfully"
                }
            
            return {
                "success": False,
                "error": "Token not found or could not be revoked"
            }
            
        except Exception as e:
            logger.error(f"Error revoking token: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def delete_token(
        self,
        token_id: str,
        user_id: str,
        session: Session
    ) -> Dict[str, Any]:
        """
        Delete a specific token.
        
        Uses repository pattern for database operations.
        """
        try:
            repository = self._get_repository(session)
            
            success = await repository.delete_token(token_id, user_id)
            
            if success:
                return {
                    "success": True,
                    "message": "Token deleted successfully"
                }
            
            return {
                "success": False,
                "error": "Token not found or could not be deleted"
            }
            
        except Exception as e:
            logger.error(f"Error deleting token: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def reactivate_token(
        self,
        token_id: str,
        user_id: str,
        session: Session
    ) -> Dict[str, Any]:
        """
        Reactivate a revoked token.
        
        Uses repository pattern for database operations.
        """
        try:
            repository = self._get_repository(session)
            
            success = await repository.reactivate_token(token_id, user_id)
            
            if success:
                return {
                    "success": True,
                    "message": "Token reactivated successfully"
                }
            
            return {
                "success": False,
                "error": "Token not found or could not be reactivated"
            }
            
        except Exception as e:
            logger.error(f"Error reactivating token: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def rotate_token(
        self,
        token_id: str,
        user_id: str,
        session: Session
    ) -> Dict[str, Any]:
        """
        Rotate a token (revoke old, create new).
        
        Uses repository pattern and delegation to other methods.
        """
        try:
            repository = self._get_repository(session)
            
            # Get the old token
            old_token = await repository.get_token(token_id, user_id)
            
            if not old_token:
                return {
                    "success": False,
                    "error": "Token not found"
                }
            
            # Revoke the old token
            await repository.revoke_token(token_id, user_id)
            
            # Create a new token with the same properties
            new_result = await self.create_api_token(
                user_id=user_id,
                name=f"{old_token.name} (rotated)",
                scopes=old_token.scopes,
                expires_in_days=30,  # Default to 30 days
                rate_limit=old_token.rate_limit,
                metadata={"rotated_from": old_token.id},
                session=session
            )
            
            if new_result["success"]:
                return {
                    "success": True,
                    "token_data": new_result["token"]
                }
            
            return new_result
            
        except Exception as e:
            logger.error(f"Error rotating token: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def validate_token(
        self,
        token: str,
        session: Session
    ) -> Dict[str, Any]:
        """
        Validate a token and return its claims.
        
        Uses JWT service and repository for validation.
        """
        try:
            # Decode the token
            payload = self.jwt_service.decode_token(token)
            
            if not payload:
                return {
                    "success": False,
                    "error": "Invalid token format"
                }
            
            # Check if token exists and is active
            repository = self._get_repository(session)
            db_token = await repository.get_token_by_id(payload.get("token_id"))
            
            if not db_token or not db_token.is_active:
                return {
                    "success": False,
                    "error": "Token is invalid or revoked"
                }
            
            # Update usage statistics
            await repository.update_token_usage(payload.get("token_id"))
            
            return {
                "success": True,
                "claims": payload
            }
            
        except jwt.ExpiredSignatureError:
            return {
                "success": False,
                "error": "Token has expired"
            }
        except jwt.InvalidTokenError as e:
            return {
                "success": False,
                "error": f"Invalid token: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return {
                "success": False,
                "error": str(e)
            }