"""
Auth API Integration for MCP Server

This module integrates the authentication endpoints into the main MCP server,
allowing the auth API to be served on the same port as the MCP server.
"""

import logging
from starlette.routing import Route
from starlette.responses import JSONResponse
from starlette.requests import Request

logger = logging.getLogger(__name__)

def create_auth_integration_routes():
    """
    Create auth routes that integrate with the MCP server.
    These routes will be mounted at /api/auth/* on the main server.
    """
    try:
        # Import auth services directly without FastAPI dependency
        from ...auth.application.services.auth_service import AuthService
        from ...auth.infrastructure.repositories.user_repository import UserRepository
        from ...auth.domain.services.jwt_service import JWTService
        import os
        
        # Initialize JWT service
        JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        jwt_service = JWTService(JWT_SECRET_KEY)
        
        routes = []
        
        # Register endpoint
        async def register_endpoint(request: Request) -> JSONResponse:
            """Handle user registration."""
            try:
                data = await request.json()
                
                # Get database session
                from ...task_management.infrastructure.database.database_config import get_db_config
                db_config = get_db_config()
                db = db_config.get_session()
                
                try:
                    # Create auth service
                    user_repository = UserRepository(db)
                    auth_service = AuthService(user_repository, jwt_service)
                    
                    # Register user
                    result = await auth_service.register_user(
                        email=data.get("email"),
                        username=data.get("username"),
                        password=data.get("password")
                    )
                    
                    if result.success and result.user:
                        db.commit()  # Commit successful registration
                        return JSONResponse({
                            "message": f"User {result.user.username} registered successfully",
                            "success": True
                        })
                    else:
                        db.rollback()  # Rollback on registration failure
                        return JSONResponse({
                            "message": result.error_message or "Registration failed",
                            "success": False
                        }, status_code=400)
                    
                except Exception as e:
                    logger.error(f"Registration error: {e}")
                    db.rollback()  # Rollback on exception
                    return JSONResponse({
                        "detail": str(e),
                        "success": False
                    }, status_code=400)
                finally:
                    db.close()
                    
            except Exception as e:
                logger.error(f"Request processing error: {e}")
                return JSONResponse({
                    "detail": "Invalid request",
                    "success": False
                }, status_code=400)
        
        # Login endpoint
        async def login_endpoint(request: Request) -> JSONResponse:
            """Handle user login."""
            try:
                data = await request.json()
                
                # Get database session
                from ...task_management.infrastructure.database.database_config import get_db_config
                db_config = get_db_config()
                db = db_config.get_session()
                
                try:
                    # Create auth service
                    user_repository = UserRepository(db)
                    auth_service = AuthService(user_repository, jwt_service)
                    
                    # Authenticate user
                    result = await auth_service.login(
                        email_or_username=data.get("email"),
                        password=data.get("password")
                    )
                    
                    if result.success:
                        db.commit()  # Commit successful login
                        return JSONResponse({
                            "access_token": result.access_token,
                            "refresh_token": result.refresh_token,
                            "token_type": "bearer"
                        })
                    else:
                        db.rollback()  # Rollback on login failure
                        return JSONResponse({
                            "detail": result.error_message or "Invalid credentials"
                        }, status_code=401)
                        
                except Exception as e:
                    logger.error(f"Login error: {e}")
                    db.rollback()  # Rollback on exception
                    return JSONResponse({
                        "detail": str(e)
                    }, status_code=400)
                finally:
                    db.close()
                    
            except Exception as e:
                logger.error(f"Request processing error: {e}")
                return JSONResponse({
                    "detail": "Invalid request"
                }, status_code=400)
        
        # Refresh token endpoint
        async def refresh_endpoint(request: Request) -> JSONResponse:
            """Handle token refresh."""
            try:
                data = await request.json()
                refresh_token = data.get("refresh_token")
                
                if not refresh_token:
                    return JSONResponse({
                        "detail": "Refresh token required"
                    }, status_code=400)
                
                # Validate and refresh token
                payload = jwt_service.verify_refresh_token(refresh_token)
                if not payload:
                    return JSONResponse({
                        "detail": "Invalid refresh token"
                    }, status_code=401)
                
                # Generate new tokens
                user_id = payload.get("sub")
                new_access_token = jwt_service.create_access_token({"sub": user_id})
                new_refresh_token = jwt_service.create_refresh_token({"sub": user_id})
                
                return JSONResponse({
                    "access_token": new_access_token,
                    "refresh_token": new_refresh_token,
                    "token_type": "bearer"
                })
                
            except Exception as e:
                logger.error(f"Token refresh error: {e}")
                return JSONResponse({
                    "detail": "Invalid refresh token"
                }, status_code=401)
        
        # Add routes
        routes.append(Route("/api/auth/register", endpoint=register_endpoint, methods=["POST"]))
        routes.append(Route("/api/auth/login", endpoint=login_endpoint, methods=["POST"]))
        routes.append(Route("/api/auth/refresh", endpoint=refresh_endpoint, methods=["POST"]))
        
        # Health check for auth API
        async def auth_health(request: Request) -> JSONResponse:
            """Auth API health check."""
            return JSONResponse({
                "status": "healthy",
                "service": "auth_api",
                "endpoints": [
                    "/api/auth/register",
                    "/api/auth/login",
                    "/api/auth/refresh"
                ]
            })
        
        routes.append(Route("/api/auth/health", endpoint=auth_health, methods=["GET"]))
        
        logger.info("Auth integration routes created successfully")
        return routes
        
    except ImportError as e:
        logger.error(f"Failed to import auth modules: {e}")
        logger.warning("Auth endpoints will not be available")
        return []
    except Exception as e:
        logger.error(f"Failed to create auth integration routes: {e}")
        return []