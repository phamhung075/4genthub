"""
Supabase Auth Integration for MCP Server

This module integrates the Supabase authentication endpoints into the main MCP server,
allowing the Supabase auth API to be served on port 8000 alongside the MCP server.
"""

import logging
from typing import List
from starlette.routing import Mount, Route
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


def create_supabase_auth_app() -> Starlette:
    """
    Create a Starlette sub-application with the Supabase auth endpoints.
    This will be mounted as a sub-app in the main MCP server.
    """
    try:
        # Import the Supabase auth router
        from ...auth.api.supabase_endpoints import router as supabase_router
        from ...auth.api.dev_endpoints import router as dev_router
        from fastapi import FastAPI
        from fastapi.routing import APIRoute
        import os
        
        # Create a minimal FastAPI app just for the auth endpoints
        auth_app = FastAPI()
        
        # Add the Supabase router
        auth_app.include_router(supabase_router)
        
        # Add dev router if in development mode
        if os.getenv("ENVIRONMENT", "development") == "development":
            auth_app.include_router(dev_router)
            logger.warning("⚠️  Development auth endpoints enabled at /auth/dev/*")
        
        # Convert FastAPI app to Starlette app for mounting
        # We'll manually convert the routes
        routes = []
        
        for route in auth_app.routes:
            if isinstance(route, APIRoute):
                # Convert FastAPI route to Starlette route
                routes.append(
                    Route(
                        path=route.path,
                        endpoint=route.endpoint,
                        methods=route.methods or ["GET"]
                    )
                )
        
        # Create Starlette app with CORS middleware
        middleware = [
            Middleware(
                CORSMiddleware,
                allow_origins=["http://localhost:3000", "http://localhost:3800"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        ]
        
        starlette_app = Starlette(routes=routes, middleware=middleware)
        logger.info(f"Created Supabase auth app with {len(routes)} routes")
        
        return starlette_app
        
    except ImportError as e:
        logger.error(f"Failed to import Supabase auth modules: {e}")
        # Return empty app if imports fail
        return Starlette(routes=[])
    except Exception as e:
        logger.error(f"Failed to create Supabase auth app: {e}")
        return Starlette(routes=[])


def create_supabase_auth_integration_routes() -> List:
    """
    Create Supabase auth routes that integrate with the MCP server.
    These routes will be served at /auth/supabase/* on the main server.
    
    This function creates Starlette-compatible routes that can be added
    to the main MCP server's route list.
    """
    try:
        # Import necessary modules
        from starlette.responses import JSONResponse
        from starlette.requests import Request
        import json
        
        # Import the Supabase service and models
        from ...auth.infrastructure.supabase_auth import SupabaseAuthService
        from ...auth.api.supabase_endpoints import (
            SignUpRequest, 
            SignInRequest,
            PasswordResetRequest,
            UpdatePasswordRequest,
            ResendVerificationRequest,
            format_auth_response
        )
        
        # Initialize Supabase service
        supabase_service = SupabaseAuthService()
        
        routes = []
        
        # Sign up endpoint
        async def signup_endpoint(request: Request) -> JSONResponse:
            """Handle user signup with Supabase."""
            try:
                data = await request.json()
                logger.info(f"Signup request received for email: {data.get('email')}")
                
                # Prepare metadata
                metadata = {}
                if data.get("username"):
                    metadata["username"] = data["username"]
                if data.get("full_name"):
                    metadata["full_name"] = data["full_name"]
                
                # Sign up with Supabase
                result = await supabase_service.sign_up(
                    email=data["email"],
                    password=data["password"],
                    metadata=metadata
                )
                
                if not result.success:
                    logger.error(f"Signup failed: {result.error_message}")
                    return JSONResponse(
                        {"detail": result.error_message or "Signup failed"},
                        status_code=400
                    )
                
                # Format response
                response_data = {
                    "success": result.success,
                    "message": result.error_message or "Please check your email to verify your account",
                    "requires_email_verification": result.requires_email_verification
                }
                
                if result.user:
                    response_data["user"] = {
                        "id": getattr(result.user, "id", None),
                        "email": getattr(result.user, "email", None),
                        "email_confirmed": getattr(result.user, "confirmed_at", None) is not None
                    }
                
                if result.session:
                    response_data["access_token"] = getattr(result.session, "access_token", None)
                    response_data["refresh_token"] = getattr(result.session, "refresh_token", None)
                
                logger.info(f"Signup successful for {data.get('email')}")
                return JSONResponse(response_data)
                
            except Exception as e:
                logger.error(f"Signup endpoint error: {e}")
                return JSONResponse(
                    {"detail": str(e)},
                    status_code=500
                )
        
        # Sign in endpoint
        async def signin_endpoint(request: Request) -> JSONResponse:
            """Handle user signin with Supabase."""
            try:
                data = await request.json()
                logger.info(f"Signin request received for email: {data.get('email')}")
                
                # Sign in with Supabase
                result = await supabase_service.sign_in(
                    email=data["email"],
                    password=data["password"]
                )
                
                if not result.success:
                    if result.requires_email_verification:
                        return JSONResponse(
                            {"detail": "Please verify your email before signing in"},
                            status_code=403
                        )
                    return JSONResponse(
                        {"detail": result.error_message or "Invalid credentials"},
                        status_code=401
                    )
                
                # Format response
                response_data = {
                    "success": result.success,
                    "message": "Signin successful",
                    "requires_email_verification": result.requires_email_verification
                }
                
                if result.session:
                    response_data["access_token"] = getattr(result.session, "access_token", None)
                    response_data["refresh_token"] = getattr(result.session, "refresh_token", None)
                
                if result.user:
                    response_data["user"] = {
                        "id": getattr(result.user, "id", None),
                        "email": getattr(result.user, "email", None)
                    }
                
                logger.info(f"Signin successful for {data.get('email')}")
                return JSONResponse(response_data)
                
            except Exception as e:
                logger.error(f"Signin endpoint error: {e}")
                return JSONResponse(
                    {"detail": str(e)},
                    status_code=500
                )
        
        # Password reset endpoint
        async def password_reset_endpoint(request: Request) -> JSONResponse:
            """Handle password reset request."""
            try:
                data = await request.json()
                
                result = await supabase_service.reset_password_request(
                    email=data["email"]
                )
                
                if not result.success:
                    return JSONResponse(
                        {"detail": result.error_message or "Password reset failed"},
                        status_code=400
                    )
                
                return JSONResponse({
                    "success": True,
                    "message": "Password reset email sent"
                })
                
            except Exception as e:
                logger.error(f"Password reset endpoint error: {e}")
                return JSONResponse(
                    {"detail": str(e)},
                    status_code=500
                )
        
        # Resend verification endpoint
        async def resend_verification_endpoint(request: Request) -> JSONResponse:
            """Handle resend verification email request."""
            try:
                data = await request.json()
                
                result = await supabase_service.resend_verification_email(
                    email=data["email"]
                )
                
                if not result.success:
                    return JSONResponse(
                        {"detail": result.error_message or "Failed to resend verification email"},
                        status_code=400
                    )
                
                return JSONResponse({
                    "success": True,
                    "message": "Verification email sent"
                })
                
            except Exception as e:
                logger.error(f"Resend verification endpoint error: {e}")
                return JSONResponse(
                    {"detail": str(e)},
                    status_code=500
                )
        
        # Sign out endpoint
        async def signout_endpoint(request: Request) -> JSONResponse:
            """Handle user signout."""
            try:
                # Get bearer token from header
                auth_header = request.headers.get("authorization", "")
                if not auth_header.startswith("Bearer "):
                    return JSONResponse(
                        {"detail": "Missing authorization header"},
                        status_code=401
                    )
                
                token = auth_header.split(" ")[1]
                success = await supabase_service.sign_out(access_token=token)
                
                if not success:
                    return JSONResponse(
                        {"detail": "Failed to sign out"},
                        status_code=400
                    )
                
                return JSONResponse({
                    "success": True,
                    "message": "Signed out successfully"
                })
                
            except Exception as e:
                logger.error(f"Signout endpoint error: {e}")
                return JSONResponse(
                    {"detail": str(e)},
                    status_code=500
                )
        
        # Health check endpoint
        async def health_endpoint(request: Request) -> JSONResponse:
            """Health check for Supabase auth."""
            return JSONResponse({
                "status": "healthy",
                "service": "supabase_auth",
                "endpoints": [
                    "/auth/supabase/signup",
                    "/auth/supabase/signin",
                    "/auth/supabase/signout",
                    "/auth/supabase/password-reset",
                    "/auth/supabase/resend-verification"
                ]
            })
        
        # Add routes with /auth/supabase prefix
        routes.append(Route("/auth/supabase/signup", endpoint=signup_endpoint, methods=["POST"]))
        routes.append(Route("/auth/supabase/signin", endpoint=signin_endpoint, methods=["POST"]))
        routes.append(Route("/auth/supabase/signout", endpoint=signout_endpoint, methods=["POST"]))
        routes.append(Route("/auth/supabase/password-reset", endpoint=password_reset_endpoint, methods=["POST"]))
        routes.append(Route("/auth/supabase/resend-verification", endpoint=resend_verification_endpoint, methods=["POST"]))
        routes.append(Route("/auth/supabase/health", endpoint=health_endpoint, methods=["GET"]))
        
        logger.info(f"Created {len(routes)} Supabase auth integration routes")
        return routes
        
    except ImportError as e:
        logger.error(f"Failed to import Supabase auth modules: {e}")
        logger.warning("Supabase auth endpoints will not be available")
        return []
    except Exception as e:
        logger.error(f"Failed to create Supabase auth integration routes: {e}")
        return []