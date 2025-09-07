"""
Token Management Routes for Starlette Integration

This module provides Starlette-compatible routes for token management,
bridging the FastAPI token router with the main MCP server.
"""

from starlette.routing import Route
from starlette.responses import JSONResponse
from starlette.requests import Request
import json
from typing import List

from ...auth.interface.fastapi_auth import get_db
from ...auth.domain.services.jwt_service import JWTService
from ...auth.infrastructure.repositories.user_repository import UserRepository
import os

# Initialize JWT service
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
jwt_service = JWTService(JWT_SECRET_KEY)

async def get_current_user_from_request(request: Request, db):
    """Extract and validate user from Starlette request"""
    # Get Authorization header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        # Validate token
        payload = jwt_service.verify_access_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        # Get user from database
        user_repository = UserRepository(db)
        user = user_repository.find_by_id(user_id)
        return user
    except Exception as e:
        print(f"Token validation error: {e}")
        return None

from .token_router import (
    TokenGenerateRequest,
    TokenListResponse,
    TokenResponse,
    TokenUpdateRequest,
    TokenValidateResponse,
    generate_token as generate_token_handler,
    list_tokens as list_tokens_handler,
    get_token_details as get_token_details_handler,
    revoke_token as revoke_token_handler,
    update_token as update_token_handler,
    rotate_token as rotate_token_handler,
    validate_token as validate_token_handler,
    get_token_usage_stats as get_token_usage_stats_handler,
)


async def handle_generate_token(request: Request) -> JSONResponse:
    """Handle POST /api/v2/tokens - Generate new token"""
    db = None
    try:
        # Get database session
        db = next(get_db())
        
        # Get current user from request
        user = await get_current_user_from_request(request, db)
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        
        # Parse request body
        body = await request.json()
        token_request = TokenGenerateRequest(**body)
        
        # Generate token
        result = await generate_token_handler(token_request, user, db)
        
        return JSONResponse(result.dict())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    finally:
        if db:
            db.close()


async def handle_list_tokens(request: Request) -> JSONResponse:
    """Handle GET /api/v2/tokens - List tokens"""
    db = None
    try:
        # Get database session
        db = next(get_db())
        
        # Get current user from request
        user = await get_current_user_from_request(request, db)
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        
        # Get query parameters
        skip = int(request.query_params.get("skip", 0))
        limit = int(request.query_params.get("limit", 100))
        
        # List tokens
        result = await list_tokens_handler(user, db, skip, limit)
        
        return JSONResponse(result.dict())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    finally:
        if db:
            db.close()


async def handle_get_token_details(request: Request) -> JSONResponse:
    """Handle GET /api/v2/tokens/{token_id} - Get token details"""
    try:
        # Get current user from request
        user = await get_current_user_from_request(request, db)
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        
        # Get token ID from path
        token_id = request.path_params.get("token_id")
        if not token_id:
            return JSONResponse({"error": "Token ID required"}, status_code=400)
        
        # Get database session
        db = next(get_db())
        
        # Get token details
        result = await get_token_details_handler(token_id, user, db)
        
        return JSONResponse(result.dict())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def handle_revoke_token(request: Request) -> JSONResponse:
    """Handle DELETE /api/v2/tokens/{token_id} - Revoke token"""
    try:
        # Get current user from request
        user = await get_current_user_from_request(request, db)
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        
        # Get token ID from path
        token_id = request.path_params.get("token_id")
        if not token_id:
            return JSONResponse({"error": "Token ID required"}, status_code=400)
        
        # Get database session
        db = next(get_db())
        
        # Revoke token
        result = await revoke_token_handler(token_id, user, db)
        
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def handle_update_token(request: Request) -> JSONResponse:
    """Handle PATCH /api/v2/tokens/{token_id} - Update token"""
    try:
        # Get current user from request
        user = await get_current_user_from_request(request, db)
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        
        # Get token ID from path
        token_id = request.path_params.get("token_id")
        if not token_id:
            return JSONResponse({"error": "Token ID required"}, status_code=400)
        
        # Parse request body
        body = await request.json()
        update_request = TokenUpdateRequest(**body)
        
        # Get database session
        db = next(get_db())
        
        # Update token
        result = await update_token_handler(token_id, update_request, user, db)
        
        return JSONResponse(result.dict())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def handle_rotate_token(request: Request) -> JSONResponse:
    """Handle POST /api/v2/tokens/{token_id}/rotate - Rotate token"""
    try:
        # Get current user from request
        user = await get_current_user_from_request(request, db)
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        
        # Get token ID from path
        token_id = request.path_params.get("token_id")
        if not token_id:
            return JSONResponse({"error": "Token ID required"}, status_code=400)
        
        # Get database session
        db = next(get_db())
        
        # Rotate token
        result = await rotate_token_handler(token_id, user, db)
        
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def handle_validate_token(request: Request) -> JSONResponse:
    """Handle POST /api/v2/tokens/validate - Validate token"""
    try:
        # Get authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse({"valid": False}, status_code=200)
        
        # This would need proper implementation with HTTPAuthorizationCredentials
        # For now, return a simple response
        return JSONResponse({"valid": False}, status_code=200)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def handle_get_token_usage(request: Request) -> JSONResponse:
    """Handle GET /api/v2/tokens/{token_id}/usage - Get token usage stats"""
    try:
        # Get current user from request
        user = await get_current_user_from_request(request, db)
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        
        # Get token ID from path
        token_id = request.path_params.get("token_id")
        if not token_id:
            return JSONResponse({"error": "Token ID required"}, status_code=400)
        
        # Get database session
        db = next(get_db())
        
        # Get usage stats
        result = await get_token_usage_stats_handler(token_id, user, db)
        
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


# Create Starlette routes
token_routes: List[Route] = [
    Route("/api/v2/tokens", endpoint=handle_generate_token, methods=["POST"]),
    Route("/api/v2/tokens", endpoint=handle_list_tokens, methods=["GET"]),
    Route("/api/v2/tokens/{token_id}", endpoint=handle_get_token_details, methods=["GET"]),
    Route("/api/v2/tokens/{token_id}", endpoint=handle_revoke_token, methods=["DELETE"]),
    Route("/api/v2/tokens/{token_id}", endpoint=handle_update_token, methods=["PATCH"]),
    Route("/api/v2/tokens/{token_id}/rotate", endpoint=handle_rotate_token, methods=["POST"]),
    Route("/api/v2/tokens/validate", endpoint=handle_validate_token, methods=["POST"]),
    Route("/api/v2/tokens/{token_id}/usage", endpoint=handle_get_token_usage, methods=["GET"]),
]