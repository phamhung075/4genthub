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
import os

from ...auth.interface.fastapi_auth import get_db
from ...auth.infrastructure.supabase_auth import SupabaseAuthService
from ...auth.domain.entities.user import User, UserStatus, UserRole
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

# Initialize Supabase auth service
try:
    supabase_auth = SupabaseAuthService()
except Exception as e:
    print(f"Warning: Supabase auth not available: {e}")
    supabase_auth = None

async def get_current_user_from_request(request: Request, db):
    """Extract and validate user from Starlette request using Supabase authentication"""
    if not supabase_auth:
        return None
        
    # Get Authorization header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        # Validate token with Supabase
        auth_result = await supabase_auth.verify_token(token)
        if not auth_result.success or not auth_result.user:
            return None
        
        # Extract user data from Supabase response
        supabase_user = auth_result.user
        
        # Create User entity from Supabase data
        user = User(
            id=supabase_user.id,
            email=supabase_user.email,
            username=supabase_user.user_metadata.get('username', supabase_user.email.split('@')[0]),
            full_name=supabase_user.user_metadata.get('full_name', ''),
            password_hash="", # Not needed for Supabase tokens
            status=UserStatus.ACTIVE if supabase_user.email_confirmed_at else UserStatus.PENDING_VERIFICATION,
            roles=[UserRole.USER],  # Default role
            email_verified=bool(supabase_user.email_confirmed_at),
            email_verified_at=supabase_user.email_confirmed_at,
            last_login_at=supabase_user.last_sign_in_at
        )
        
        return user
    except Exception as e:
        print(f"Token validation error: {e}")
        return None


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
    db = None
    try:
        # Get database session
        db = next(get_db())
        
        # Get current user from request
        user = await get_current_user_from_request(request, db)
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        
        # Get token ID from path
        token_id = request.path_params.get("token_id")
        if not token_id:
            return JSONResponse({"error": "Token ID required"}, status_code=400)
        
        # Get token details
        result = await get_token_details_handler(token_id, user, db)
        
        return JSONResponse(result.dict())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    finally:
        if db:
            db.close()


async def handle_revoke_token(request: Request) -> JSONResponse:
    """Handle DELETE /api/v2/tokens/{token_id} - Revoke token"""
    db = None
    try:
        # Get database session
        db = next(get_db())
        
        # Get current user from request
        user = await get_current_user_from_request(request, db)
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        
        # Get token ID from path
        token_id = request.path_params.get("token_id")
        if not token_id:
            return JSONResponse({"error": "Token ID required"}, status_code=400)
        
        # Revoke token
        result = await revoke_token_handler(token_id, user, db)
        
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    finally:
        if db:
            db.close()


# Create Starlette routes
token_routes: List[Route] = [
    Route("/api/v2/tokens", endpoint=handle_generate_token, methods=["POST"]),
    Route("/api/v2/tokens", endpoint=handle_list_tokens, methods=["GET"]),
    Route("/api/v2/tokens/{token_id}", endpoint=handle_get_token_details, methods=["GET"]),
    Route("/api/v2/tokens/{token_id}", endpoint=handle_revoke_token, methods=["DELETE"]),
]