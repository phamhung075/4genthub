"""
Token Repository Interface

Domain layer repository interface for token operations.
This interface defines the contract that infrastructure implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime


class ITokenRepository(ABC):
    """
    Interface for token repository operations.
    
    This interface defines the contract for all token-related database operations,
    ensuring proper abstraction between domain and infrastructure layers.
    """
    
    @abstractmethod
    async def create_token(self, token_data: Dict[str, Any]) -> Optional[Any]:
        """
        Create a new token in the database.
        
        Args:
            token_data: Dictionary containing token information
            
        Returns:
            Created token object or None if failed
        """
        pass
    
    @abstractmethod
    async def get_token(self, token_id: str, user_id: str) -> Optional[Any]:
        """
        Get a specific token for a user.
        
        Args:
            token_id: Token identifier
            user_id: User identifier
            
        Returns:
            Token object or None if not found
        """
        pass
    
    @abstractmethod
    async def get_token_by_id(self, token_id: str) -> Optional[Any]:
        """
        Get a token by ID regardless of user.
        
        Args:
            token_id: Token identifier
            
        Returns:
            Token object or None if not found
        """
        pass
    
    @abstractmethod
    async def get_user_tokens(self, user_id: str, skip: int = 0, limit: int = 100) -> List[Any]:
        """
        Get all tokens for a user with pagination.
        
        Args:
            user_id: User identifier
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of token objects
        """
        pass
    
    @abstractmethod
    async def count_user_tokens(self, user_id: str) -> int:
        """
        Count total tokens for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Total count of user tokens
        """
        pass
    
    @abstractmethod
    async def revoke_token(self, token_id: str, user_id: str) -> bool:
        """
        Revoke a token (mark as inactive).
        
        Args:
            token_id: Token identifier
            user_id: User identifier
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def reactivate_token(self, token_id: str, user_id: str) -> bool:
        """
        Reactivate a revoked token.
        
        Args:
            token_id: Token identifier
            user_id: User identifier
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def delete_token(self, token_id: str, user_id: str) -> bool:
        """
        Permanently delete a token.
        
        Args:
            token_id: Token identifier
            user_id: User identifier
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def update_token_usage(self, token_id: str) -> bool:
        """
        Update token usage statistics (last used, usage count).
        
        Args:
            token_id: Token identifier
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def cleanup_expired_tokens(self, expiry_date: datetime) -> int:
        """
        Remove tokens that have expired before the given date.
        
        Args:
            expiry_date: Cutoff date for expired tokens
            
        Returns:
            Number of tokens cleaned up
        """
        pass