"""
Token Facade Factory

Application layer factory for creating token facades with proper dependency injection.
Follows DDD principles by properly injecting infrastructure dependencies.
"""

from typing import Optional
from sqlalchemy.orm import Session

from ..facades.token_application_facade import TokenApplicationFacade


class TokenFacadeFactory:
    """
    Factory for creating token application facades with proper DDD dependency injection.
    
    This factory encapsulates the creation logic for token facades, ensuring
    proper dependency injection and separation of concerns.
    
    Implements singleton pattern to avoid expensive repeated initialization.
    """
    
    # Class-level singleton instance
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls):
        """
        Get the singleton instance of the factory.
        
        This is the preferred way to get the factory instance.
        Repository factories are created internally following DDD principles.
            
        Returns:
            TokenFacadeFactory: The singleton instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize the token facade factory"""
        # Skip initialization if already done (singleton pattern)
        if self._initialized:
            return
        
        # Mark as initialized for singleton pattern
        TokenFacadeFactory._initialized = True
    
    def create_token_facade(self, session: Optional[Session] = None) -> TokenApplicationFacade:
        """
        Create a token application facade with proper dependency injection.
        
        This method demonstrates how to properly construct application facades
        with all required dependencies using dependency injection.
        
        Args:
            session: Database session for repository creation (optional)
            
        Returns:
            Configured token application facade
        """
        # Create repository if session is provided
        token_repository = None
        if session:
            # Import repository from infrastructure layer (proper DDD)
            from ...infrastructure.repositories.token_repository import TokenRepository
            token_repository = TokenRepository(session)
        
        # Create and return facade with injected repository
        return TokenApplicationFacade(token_repository)
    
    def create_token_facade_without_repository(self) -> TokenApplicationFacade:
        """
        Create a token facade without repository for operations that don't need DB.
        
        This is used for operations that only use the MCP token service
        which has its own persistence layer.
        
        Returns:
            Token facade without repository
        """
        return TokenApplicationFacade(token_repository=None)