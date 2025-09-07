"""
Email Authentication Integration

This module integrates the enhanced email authentication system with the
main FastAPI application and sets up the necessary services and routes.
"""

import logging
from typing import Optional
from fastapi import FastAPI
from contextlib import asynccontextmanager

from ..api.enhanced_auth_endpoints import router as enhanced_auth_router
from ..infrastructure.enhanced_auth_service import get_enhanced_auth_service
from ..infrastructure.email_service import get_email_service
from ..infrastructure.repositories.email_token_repository import get_email_token_repository
from ..infrastructure.migrations.migrator import run_email_migrations

logger = logging.getLogger(__name__)


class EmailAuthIntegration:
    """Integration class for email authentication system"""
    
    def __init__(self, app: Optional[FastAPI] = None):
        """Initialize email auth integration"""
        self.app = app
        self.is_initialized = False
    
    async def initialize(self) -> bool:
        """Initialize email authentication system"""
        try:
            logger.info("Initializing email authentication system...")
            
            # Run database migrations for email tokens
            migration_success = await self._run_migrations()
            if not migration_success:
                logger.warning("Email token migrations failed, some features may not work")
            
            # Initialize services (this validates configurations)
            email_service = get_email_service()
            token_repository = get_email_token_repository()
            enhanced_auth_service = get_enhanced_auth_service()
            
            # Test email service connection
            connection_test = await email_service.test_connection()
            if connection_test.success:
                logger.info("SMTP email service connected successfully")
            else:
                logger.warning(f"SMTP email service connection failed: {connection_test.error_message}")
            
            # Register routes if app is provided
            if self.app:
                self.register_routes()
            
            self.is_initialized = True
            logger.info("Email authentication system initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize email authentication system: {e}")
            return False
    
    async def _run_migrations(self) -> bool:
        """Run email token database migrations"""
        try:
            from ..infrastructure.migrations.migrator import EmailTokenMigrator
            
            migrator = EmailTokenMigrator()
            success = await migrator.run_migrations()
            
            if success:
                logger.info("Email token migrations completed successfully")
            else:
                logger.error("Email token migrations failed")
            
            return success
            
        except ImportError:
            logger.warning("Email token migrator not found, skipping migrations")
            return False
        except Exception as e:
            logger.error(f"Migration error: {e}")
            return False
    
    def register_routes(self):
        """Register email authentication routes"""
        if not self.app:
            raise RuntimeError("FastAPI app not provided")
        
        # Include enhanced auth routes
        self.app.include_router(enhanced_auth_router)
        logger.info("Enhanced authentication routes registered")
    
    async def cleanup(self):
        """Cleanup email authentication system"""
        try:
            if self.is_initialized:
                # Cleanup expired tokens
                enhanced_auth_service = get_enhanced_auth_service()
                await enhanced_auth_service.cleanup_expired_tokens()
                logger.info("Email authentication system cleanup completed")
                
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    async def health_check(self) -> dict:
        """Check email authentication system health"""
        try:
            if not self.is_initialized:
                return {
                    "status": "not_initialized",
                    "message": "Email authentication system not initialized"
                }
            
            enhanced_auth_service = get_enhanced_auth_service()
            
            # Test email service
            email_test = await enhanced_auth_service.test_email_service()
            
            # Get token stats
            stats_result = await enhanced_auth_service.get_email_stats()
            
            return {
                "status": "healthy" if email_test["success"] else "degraded",
                "email_service": {
                    "status": "healthy" if email_test["success"] else "unhealthy",
                    "error": email_test.get("error_message")
                },
                "token_repository": {
                    "status": "healthy" if stats_result["success"] else "unhealthy",
                    "stats": stats_result.get("stats", {})
                },
                "initialized": self.is_initialized
            }
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return {
                "status": "error",
                "message": str(e),
                "initialized": self.is_initialized
            }


# Global integration instance
_email_auth_integration: Optional[EmailAuthIntegration] = None


def get_email_auth_integration() -> EmailAuthIntegration:
    """Get global email auth integration instance"""
    global _email_auth_integration
    if _email_auth_integration is None:
        _email_auth_integration = EmailAuthIntegration()
    return _email_auth_integration


def setup_email_auth_integration(app: FastAPI) -> EmailAuthIntegration:
    """Setup email authentication integration with FastAPI app"""
    integration = EmailAuthIntegration(app)
    
    # Add startup event
    @app.on_event("startup")
    async def startup_email_auth():
        await integration.initialize()
    
    # Add shutdown event
    @app.on_event("shutdown")
    async def shutdown_email_auth():
        await integration.cleanup()
    
    return integration


@asynccontextmanager
async def email_auth_lifespan(app: FastAPI):
    """Async context manager for email authentication lifecycle"""
    integration = EmailAuthIntegration(app)
    
    # Startup
    await integration.initialize()
    
    try:
        yield integration
    finally:
        # Shutdown
        await integration.cleanup()


# Convenience function for FastAPI setup
def include_email_auth_routes(app: FastAPI, run_startup: bool = True) -> EmailAuthIntegration:
    """
    Include email authentication routes and setup integration
    
    Args:
        app: FastAPI application instance
        run_startup: Whether to run startup initialization
        
    Returns:
        EmailAuthIntegration instance
    """
    integration = EmailAuthIntegration(app)
    integration.register_routes()
    
    if run_startup:
        @app.on_event("startup")
        async def startup_email_auth():
            await integration.initialize()
        
        @app.on_event("shutdown")
        async def shutdown_email_auth():
            await integration.cleanup()
    
    return integration