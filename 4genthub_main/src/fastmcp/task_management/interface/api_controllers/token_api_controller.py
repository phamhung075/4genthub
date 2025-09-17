"""
Token API Controller

This controller handles token management operations following DDD architecture.
It delegates all business logic to the TokenApplicationFacade, ensuring
proper separation of concerns and no direct database access.
"""

import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from ...application.services.facade_service import FacadeService

logger = logging.getLogger(__name__)


class TokenAPIController:
    """
    API Controller for token management operations.
    
    This controller coordinates token operations following DDD principles,
    delegating all business logic to the TokenApplicationFacade via factory.
    """
    
    def __init__(self):
        """Initialize the token controller with facade service"""
        # Use FacadeService for proper DDD layering - no direct factory access
        self.facade_service = FacadeService.get_instance()
        # Don't create token facade at initialization - will be created on demand
        self.token_facade = None
    
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
        
        Delegates to the application facade following DDD principles.
        
        Args:
            user_id: User identifier
            email: User email
            expires_in_hours: Token expiration in hours
            metadata: Optional token metadata
            session: Optional database session
            
        Returns:
            Token data including token string and expiration
        """
        # Get token facade on demand
        if not self.token_facade:
            self.token_facade = self.facade_service.get_token_facade(user_id=user_id)
        
        return await self.token_facade.generate_mcp_token_from_user(
            user_id=user_id,
            email=email,
            expires_in_hours=expires_in_hours,
            metadata=metadata,
            session=session
        )
    
    async def revoke_user_tokens(self, user_id: str) -> Dict[str, Any]:
        """
        Revoke all tokens for a user.
        
        Delegates to the application facade following DDD principles.
        
        Args:
            user_id: User identifier
            
        Returns:
            Result of revocation operation
        """
        # Get token facade on demand
        if not self.token_facade:
            self.token_facade = self.facade_service.get_token_facade(user_id=user_id)
        
        return await self.token_facade.revoke_user_tokens(user_id)
    
    def get_token_stats(self) -> Dict[str, Any]:
        """
        Get token statistics.
        
        Delegates to the application facade following DDD principles.
        
        Returns:
            Token statistics data
        """
        # Get token facade on demand if not already created
        if not self.token_facade:
            self.token_facade = self.facade_service.get_token_facade()
        
        return self.token_facade.get_token_stats()
    
    async def cleanup_expired_tokens(self) -> Dict[str, Any]:
        """
        Clean up expired tokens.
        
        Delegates to the application facade following DDD principles.
        
        Returns:
            Number of tokens cleaned
        """
        # Get token facade on demand if not already created
        if not self.token_facade:
            self.token_facade = self.facade_service.get_token_facade()
        
        return await self.token_facade.cleanup_expired_tokens()
    
    
    
    async def list_user_tokens(
        self,
        user_id: str,
        session: Session,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        List tokens for a user.
        
        Delegates to the application facade following DDD principles.
        
        Args:
            user_id: User identifier
            session: Database session
            skip: Number of records to skip
            limit: Maximum number of records
            
        Returns:
            List of user tokens
        """
        # Get token facade on demand if not already created
        if not self.token_facade:
            self.token_facade = self.facade_service.get_token_facade(user_id=user_id)
        
        return await self.token_facade.list_user_tokens(
            user_id=user_id,
            session=session,
            skip=skip,
            limit=limit
        )
    
    async def get_token_details(
        self,
        token_id: str,
        user_id: str,
        session: Session
    ) -> Dict[str, Any]:
        """
        Get details for a specific token.
        
        Delegates to the application facade following DDD principles.
        
        Args:
            token_id: Token identifier
            user_id: User identifier
            session: Database session
            
        Returns:
            Token details
        """
        # Get token facade on demand if not already created
        if not self.token_facade:
            self.token_facade = self.facade_service.get_token_facade(user_id=user_id)
        
        return await self.token_facade.get_token_details(
            token_id=token_id,
            user_id=user_id,
            session=session
        )
    
    async def revoke_token(
        self,
        token_id: str,
        user_id: str,
        session: Session
    ) -> Dict[str, Any]:
        """
        Revoke a specific token.
        
        Delegates to the application facade following DDD principles.
        
        Args:
            token_id: Token identifier
            user_id: User identifier
            session: Database session
            
        Returns:
            Revocation result
        """
        # Get token facade on demand if not already created
        if not self.token_facade:
            self.token_facade = self.facade_service.get_token_facade(user_id=user_id)
        
        return await self.token_facade.revoke_token(
            token_id=token_id,
            user_id=user_id,
            session=session
        )
    async def generate_api_token(
        self,
        user_id: str,
        name: str,
        scopes: List[str],
        expires_in_days: int,
        rate_limit: Optional[int],
        session: Session
    ) -> Dict[str, Any]:
        """
        Generate a new API token for the user.
        
        Delegates to the application facade following DDD principles.
        
        Args:
            user_id: User identifier
            name: Token name
            scopes: Token scopes
            expires_in_days: Token expiration in days
            rate_limit: Optional rate limit
            session: Database session
            
        Returns:
            Generated token data
        """
        # Get token facade on demand if not already created
        if not self.token_facade:
            self.token_facade = self.facade_service.get_token_facade(user_id=user_id)
        
        result = await self.token_facade.create_api_token(
            user_id=user_id,
            name=name,
            scopes=scopes,
            expires_in_days=expires_in_days,
            rate_limit=rate_limit,
            metadata={},
            session=session
        )
        if result["success"]:
            return {
                "success": True,
                "token_data": result["token"]
            }
        return result
    
    async def delete_token(
        self,
        token_id: str,
        user_id: str,
        session: Session
    ) -> Dict[str, Any]:
        """
        Delete a specific token.
        
        Delegates to the application facade following DDD principles.
        
        Args:
            token_id: Token identifier
            user_id: User identifier
            session: Database session
            
        Returns:
            Deletion result
        """
        # Get token facade on demand if not already created
        if not self.token_facade:
            self.token_facade = self.facade_service.get_token_facade(user_id=user_id)
        
        return await self.token_facade.delete_token(
            token_id=token_id,
            user_id=user_id,
            session=session
        )
    
    async def reactivate_token(
        self,
        token_id: str,
        user_id: str,
        session: Session
    ) -> Dict[str, Any]:
        """
        Reactivate a revoked token.
        
        Delegates to the application facade following DDD principles.
        
        Args:
            token_id: Token identifier
            user_id: User identifier
            session: Database session
            
        Returns:
            Reactivation result
        """
        # Get token facade on demand if not already created
        if not self.token_facade:
            self.token_facade = self.facade_service.get_token_facade(user_id=user_id)
        
        return await self.token_facade.reactivate_token(
            token_id=token_id,
            user_id=user_id,
            session=session
        )
    
    async def rotate_token(
        self,
        token_id: str,
        user_id: str,
        session: Session
    ) -> Dict[str, Any]:
        """
        Rotate a token (revoke old, create new).
        
        Delegates to the application facade following DDD principles.
        
        Args:
            token_id: Token identifier to rotate
            user_id: User identifier
            session: Database session
            
        Returns:
            New token data
        """
        # Get token facade on demand if not already created
        if not self.token_facade:
            self.token_facade = self.facade_service.get_token_facade(user_id=user_id)
        
        return await self.token_facade.rotate_token(
            token_id=token_id,
            user_id=user_id,
            session=session
        )
    
    async def validate_token(
        self,
        token: str,
        session: Session
    ) -> Dict[str, Any]:
        """
        Validate a token and return its claims.
        
        Delegates to the application facade following DDD principles.
        
        Args:
            token: JWT token string
            session: Database session
            
        Returns:
            Token claims if valid
        """
        # Get token facade on demand if not already created
        if not self.token_facade:
            self.token_facade = self.facade_service.get_token_facade()
        
        return await self.token_facade.validate_token(
            token=token,
            session=session
        )
