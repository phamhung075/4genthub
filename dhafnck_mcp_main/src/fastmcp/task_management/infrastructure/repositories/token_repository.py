"""
Token Repository Implementation

Infrastructure layer implementation of the token repository interface.
This implementation handles all database operations for tokens using SQLAlchemy.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from fastmcp.task_management.domain.repositories.token_repository_interface import ITokenRepository
from fastmcp.task_management.infrastructure.database.models import APIToken
from fastmcp.auth.models.api_token import ApiToken

logger = logging.getLogger(__name__)


class TokenRepository(ITokenRepository):
    """
    Concrete implementation of the token repository interface.
    
    This class handles all database operations for tokens using SQLAlchemy,
    ensuring proper abstraction from upper layers.
    """
    
    def __init__(self, session: Session):
        """
        Initialize the repository with a database session.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
    
    async def create_token(self, token_data: Dict[str, Any]) -> Optional[APIToken]:
        """
        Create a new token in the database.
        
        Args:
            token_data: Dictionary containing token information
            
        Returns:
            Created token object or None if failed
        """
        try:
            # Create new token instance
            db_token = APIToken(
                id=token_data.get('id'),
                user_id=token_data.get('user_id'),
                name=token_data.get('name'),
                token_hash=token_data.get('token_hash'),
                scopes=token_data.get('scopes', []),
                expires_at=token_data.get('expires_at'),
                rate_limit=token_data.get('rate_limit', 1000),
                token_metadata=token_data.get('token_metadata', {})
            )
            
            # Add to session and commit
            self.session.add(db_token)
            self.session.commit()
            self.session.refresh(db_token)
            
            return db_token
            
        except Exception as e:
            logger.error(f"Error creating token: {e}")
            self.session.rollback()
            return None
    
    async def get_token(self, token_id: str, user_id: str) -> Optional[APIToken]:
        """
        Get a specific token for a user.
        
        Args:
            token_id: Token identifier
            user_id: User identifier
            
        Returns:
            Token object or None if not found
        """
        try:
            return self.session.query(APIToken).filter(
                APIToken.id == token_id,
                APIToken.user_id == user_id
            ).first()
            
        except Exception as e:
            logger.error(f"Error getting token: {e}")
            return None
    
    async def get_token_by_id(self, token_id: str) -> Optional[APIToken]:
        """
        Get a token by ID regardless of user.
        
        Args:
            token_id: Token identifier
            
        Returns:
            Token object or None if not found
        """
        try:
            # Try APIToken model first
            token = self.session.query(APIToken).filter(
                APIToken.id == token_id
            ).first()
            
            if token:
                return token
            
            # Fallback to ApiToken model if needed
            token = self.session.query(ApiToken).filter(
                ApiToken.id == token_id
            ).first()
            
            return token
            
        except Exception as e:
            logger.error(f"Error getting token by ID: {e}")
            return None
    
    async def get_user_tokens(self, user_id: str, skip: int = 0, limit: int = 100) -> List[APIToken]:
        """
        Get all tokens for a user with pagination.
        
        Args:
            user_id: User identifier
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of token objects
        """
        try:
            query = self.session.query(APIToken).filter(
                APIToken.user_id == user_id
            ).order_by(desc(APIToken.created_at))
            
            return query.offset(skip).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error getting user tokens: {e}")
            return []
    
    async def count_user_tokens(self, user_id: str) -> int:
        """
        Count total tokens for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Total count of user tokens
        """
        try:
            return self.session.query(APIToken).filter(
                APIToken.user_id == user_id
            ).count()
            
        except Exception as e:
            logger.error(f"Error counting user tokens: {e}")
            return 0
    
    async def revoke_token(self, token_id: str, user_id: str) -> bool:
        """
        Revoke a token (mark as inactive).
        
        Args:
            token_id: Token identifier
            user_id: User identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            token = await self.get_token(token_id, user_id)
            
            if not token:
                return False
            
            token.is_active = False
            self.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error revoking token: {e}")
            self.session.rollback()
            return False
    
    async def reactivate_token(self, token_id: str, user_id: str) -> bool:
        """
        Reactivate a revoked token.
        
        Args:
            token_id: Token identifier
            user_id: User identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Try APIToken model first
            token = self.session.query(APIToken).filter(
                APIToken.id == token_id,
                APIToken.user_id == user_id
            ).first()
            
            if not token:
                # Fallback to ApiToken model
                token = self.session.query(ApiToken).filter(
                    ApiToken.id == token_id,
                    ApiToken.user_id == user_id
                ).first()
            
            if not token:
                return False
            
            token.is_active = True
            self.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error reactivating token: {e}")
            self.session.rollback()
            return False
    
    async def delete_token(self, token_id: str, user_id: str) -> bool:
        """
        Permanently delete a token.
        
        Args:
            token_id: Token identifier
            user_id: User identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Try APIToken model first
            token = self.session.query(APIToken).filter(
                APIToken.id == token_id,
                APIToken.user_id == user_id
            ).first()
            
            if not token:
                # Fallback to ApiToken model
                token = self.session.query(ApiToken).filter(
                    ApiToken.id == token_id,
                    ApiToken.user_id == user_id
                ).first()
            
            if not token:
                return False
            
            self.session.delete(token)
            self.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error deleting token: {e}")
            self.session.rollback()
            return False
    
    async def update_token_usage(self, token_id: str) -> bool:
        """
        Update token usage statistics (last used, usage count).
        
        Args:
            token_id: Token identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Try APIToken model first
            token = self.session.query(APIToken).filter(
                APIToken.id == token_id
            ).first()
            
            if not token:
                # Fallback to ApiToken model
                token = self.session.query(ApiToken).filter(
                    ApiToken.id == token_id
                ).first()
            
            if not token:
                return False
            
            token.last_used_at = datetime.utcnow()
            token.usage_count = (token.usage_count or 0) + 1
            self.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error updating token usage: {e}")
            self.session.rollback()
            return False
    
    async def cleanup_expired_tokens(self, expiry_date: datetime) -> int:
        """
        Remove tokens that have expired before the given date.
        
        Args:
            expiry_date: Cutoff date for expired tokens
            
        Returns:
            Number of tokens cleaned up
        """
        try:
            # Count tokens to be deleted
            count = self.session.query(APIToken).filter(
                APIToken.expires_at < expiry_date
            ).count()
            
            # Delete expired tokens
            self.session.query(APIToken).filter(
                APIToken.expires_at < expiry_date
            ).delete(synchronize_session=False)
            
            self.session.commit()
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired tokens: {e}")
            self.session.rollback()
            return 0