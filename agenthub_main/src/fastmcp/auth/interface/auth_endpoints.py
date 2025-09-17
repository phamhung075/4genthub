"""
Authentication Endpoints for Keycloak/Supabase

This module provides authentication endpoints that handle login
with Keycloak or Supabase based on configuration.
"""

import os
import httpx
import logging
import time
import asyncio
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Get auth provider from environment
AUTH_PROVIDER = os.getenv("AUTH_PROVIDER", "keycloak").lower()
EMAIL_VERIFIED_AUTO = os.getenv("EMAIL_VERIFIED_AUTO", "false").lower() == "true"
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "agenthub")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "agenthub-client")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "")

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    user_id: Optional[str] = None
    email: Optional[str] = None

class RegisterRequest(BaseModel):
    email: str
    password: str
    username: Optional[str] = None
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Validate password meets Keycloak policy requirements"""
        import re
        
        errors = []
        
        # Check all requirements and collect all errors
        if len(v) < 8:
            errors.append('at least 8 characters')
        if not re.search(r'[A-Z]', v):
            errors.append('at least 1 uppercase letter (A-Z)')
        if not re.search(r'[a-z]', v):
            errors.append('at least 1 lowercase letter (a-z)')
        if not re.search(r'\d', v):
            errors.append('at least 1 number (0-9)')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>\-_+=\[\]\\/;`~]', v):
            errors.append('at least 1 special character (!@#$%^&*()-_+=)')
        
        if errors:
            # Create a detailed error message
            error_msg = f"Password does not meet requirements. It must contain: {', '.join(errors)}. "
            error_msg += f"Your password has {len(v)} characters."
            
            # Add helpful example
            if len(errors) == 1 and 'special character' in errors[0]:
                error_msg += " Try adding a special character like ! or @ to your password."
            elif len(errors) == 1 and 'uppercase' in errors[0]:
                error_msg += " Try capitalizing the first letter of your password."
            elif len(errors) > 1:
                error_msg += " Example of a valid password: Password123!"
            
            raise ValueError(error_msg)
        
        return v
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Validate email format"""
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Please enter a valid email address (e.g., user@example.com)')
        return v.lower()  # Normalize email to lowercase
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """Validate username if provided"""
        if v:
            if len(v) < 3:
                raise ValueError('Username must be at least 3 characters long')
            if len(v) > 20:
                raise ValueError('Username must not exceed 20 characters')
            # Check for valid characters
            import re
            if not re.match(r'^[a-zA-Z0-9_-]+$', v):
                raise ValueError('Username can only contain letters, numbers, underscore (_) and hyphen (-)')
        return v

class RegisterResponse(BaseModel):
    success: bool = True
    user_id: str
    email: str
    username: Optional[str] = None
    message: str = "User registered successfully"
    message_type: str = "success"  # success, error, warning, info
    display_color: str = "green"  # green for success
    next_steps: Optional[List[str]] = None

async def get_keycloak_admin_token():
    """
    Get an admin access token for Keycloak management operations.
    """
    token_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
    
    # Try client credentials first
    data = {
        "grant_type": "client_credentials",
        "client_id": KEYCLOAK_CLIENT_ID,
        "client_secret": KEYCLOAK_CLIENT_SECRET
    }
    
    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                token_data = response.json()
                return token_data.get("access_token")
            
            # If client credentials fail, try admin username/password
            logger.warning("Client credentials failed, trying admin credentials")
            admin_data = {
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": "admin",
                "password": os.getenv("KEYCLOAK_ADMIN_PASSWORD", "")  # Use environment variable
            }
            
            admin_response = await client.post(
                token_url.replace(f"/realms/{KEYCLOAK_REALM}", "/realms/master"),
                data=admin_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if admin_response.status_code == 200:
                token_data = admin_response.json()
                return token_data.get("access_token")
                
    except Exception as e:
        logger.error(f"Failed to get admin token: {e}")
    
    return None

@router.post("/register")
async def register(request: RegisterRequest):
    """
    Register endpoint that creates a new user in Keycloak.
    
    Returns detailed error messages to help users fix registration issues.
    """
    # Log registration attempt
    logger.info(f"Registration attempt for email: {request.email}, username: {request.username or 'not provided'}")
    if AUTH_PROVIDER == "keycloak":
        # Create user in Keycloak
        admin_url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users"
        
        # First, get an admin token (you'll need admin credentials for this)
        # For now, we'll use the client credentials grant if the client has admin permissions
        token_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
        
        try:
            # Get admin token using client credentials
            async with httpx.AsyncClient(verify=False) as client:
                # Try to get admin token
                token_response = await client.post(
                    token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": KEYCLOAK_CLIENT_ID,
                        "client_secret": KEYCLOAK_CLIENT_SECRET
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if token_response.status_code != 200:
                    # If client credentials don't work, try to use direct admin access
                    # This is a fallback for development/demo purposes
                    logger.warning(f"Client credentials failed: {token_response.status_code} - {token_response.text}")
                    
                    # For development, we can try to create user without admin token
                    # This will work if Keycloak allows public registration
                    if KEYCLOAK_CLIENT_SECRET:
                        # Try alternative: use password grant with admin user
                        admin_token_response = await client.post(
                            token_url,
                            data={
                                "grant_type": "password",
                                "client_id": KEYCLOAK_CLIENT_ID,
                                "client_secret": KEYCLOAK_CLIENT_SECRET,
                                "username": "admin",
                                "password": os.getenv("KEYCLOAK_ADMIN_PASSWORD", ""),
                                "scope": "openid"
                            },
                            headers={"Content-Type": "application/x-www-form-urlencoded"}
                        )
                        
                        if admin_token_response.status_code == 200:
                            admin_token = admin_token_response.json().get("access_token")
                        else:
                            logger.error(f"Admin login failed: {admin_token_response.status_code}")
                            raise HTTPException(
                                status_code=503,
                                detail="Registration service not available. Admin credentials may need to be configured."
                            )
                    else:
                        raise HTTPException(
                            status_code=503,
                            detail="Registration service not properly configured. Please contact administrator."
                        )
                else:
                    admin_token = token_response.json().get("access_token")
                
                admin_token = token_response.json().get("access_token")
                
                # Create the user
                user_data = {
                    "username": request.username or request.email,
                    "email": request.email,
                    "enabled": True,
                    "emailVerified": EMAIL_VERIFIED_AUTO,  # Configurable email verification
                    "credentials": [{
                        "type": "password",
                        "value": request.password,
                        "temporary": False
                    }]
                }
                
                # Add required actions if email verification is needed
                if not EMAIL_VERIFIED_AUTO:
                    user_data["requiredActions"] = ["VERIFY_EMAIL"]
                    logger.info(f"Email verification will be required for user: {request.email}")
                
                create_response = await client.post(
                    admin_url,
                    json=user_data,
                    headers={
                        "Authorization": f"Bearer {admin_token}",
                        "Content-Type": "application/json"
                    }
                )
                
                if create_response.status_code == 201:
                    # User created successfully in Keycloak!
                    logger.info(f"✅ User successfully registered in Keycloak: {request.email}")
                    
                    # Extract user ID from Location header
                    location = create_response.headers.get("Location", "")
                    user_id = location.split("/")[-1] if location else "new-user"
                    
                    # ✅ CRITICAL: Setup proper grants/roles for the user BEFORE login
                    if user_id and user_id != "new-user":
                        try:
                            await setup_user_roles(client, admin_token, user_id, request.email)
                            # Add a small delay to ensure Keycloak processes the changes
                            await asyncio.sleep(0.5)
                        except Exception as e:
                            logger.warning(f"Role setup failed for {request.email}: {e} - proceeding with login attempt")
                    
                    # Try to automatically log the user in after registration
                    auto_login_token = None
                    max_login_attempts = 3
                    login_attempt = 0
                    
                    while login_attempt < max_login_attempts and not auto_login_token:
                        try:
                            # Add delay between attempts
                            if login_attempt > 0:
                                await asyncio.sleep(1)
                            
                            # Attempt to get a token for the newly created user
                            login_response = await client.post(
                                token_url,
                                data={
                                    "grant_type": "password",
                                    "client_id": KEYCLOAK_CLIENT_ID,
                                    "client_secret": KEYCLOAK_CLIENT_SECRET if KEYCLOAK_CLIENT_SECRET else None,
                                    "username": request.email,
                                    "password": request.password,
                                    "scope": "openid"
                                },
                                headers={"Content-Type": "application/x-www-form-urlencoded"}
                            )
                        
                            if login_response.status_code == 200:
                                token_data = login_response.json()
                                auto_login_token = token_data.get("access_token")
                                logger.info(f"Auto-login successful for newly registered user: {request.email} (attempt {login_attempt + 1})")
                                break
                            elif login_response.status_code == 400:
                                error_detail = login_response.json().get("error_description", "")
                                if "Account is not fully set up" in error_detail:
                                    logger.info(f"Account not ready yet, attempt {login_attempt + 1}/{max_login_attempts}")
                                    login_attempt += 1
                                else:
                                    break
                            else:
                                break
                        except Exception as e:
                            logger.warning(f"Auto-login attempt {login_attempt + 1} failed: {e}")
                            login_attempt += 1
                    
                    if not auto_login_token:
                        logger.warning(f"Auto-login failed after {max_login_attempts} attempts for {request.email}")
                        # Not critical - user can still log in manually
                    
                    # Return detailed success response
                    if not EMAIL_VERIFIED_AUTO:
                        # Email verification is required
                        response = RegisterResponse(
                            success=True,
                            user_id=user_id,
                            email=request.email,
                            username=request.username or request.email,
                            message="📧 Account created! Please check your email to verify your account before logging in.",
                            message_type="warning",
                            display_color="yellow",
                            next_steps=[
                                "Check your email for the verification link",
                                "Click the verification link to activate your account",
                                "After verification, you can log in with your credentials"
                            ]
                        )
                    else:
                        # Email verification is auto-enabled
                        response = RegisterResponse(
                            success=True,
                            user_id=user_id,
                            email=request.email,
                            username=request.username or request.email,
                            message="🎉 SUCCESS: Your account has been created successfully!",
                            message_type="success",
                            display_color="green",
                            next_steps=[
                                "You can now log in with your email and password" if not auto_login_token else "You have been automatically logged in",
                                "Check your email for verification (if enabled)",
                                "Complete your profile settings"
                            ]
                        )
                    
                    # Add the auto-login token if we got one
                    if auto_login_token:
                        response_dict = response.dict()
                        response_dict["auto_login_token"] = auto_login_token
                        response_dict["message"] = "🎉 SUCCESS: Account created and you have been automatically logged in!"
                        response_dict["message_type"] = "success"
                        response_dict["display_color"] = "green"
                        return response_dict
                    
                    return response
                elif create_response.status_code == 409:
                    # User already exists - try to cleanup incomplete account
                    logger.info(f"User already exists, attempting cleanup for: {request.email}")
                    
                    cleanup_result = await cleanup_incomplete_account_internal(request.email)
                    
                    if cleanup_result.get("success") and cleanup_result.get("can_register"):
                        # Cleanup successful, retry registration
                        logger.info(f"Cleanup successful, retrying registration for: {request.email}")
                        
                        # Retry user creation after cleanup
                        retry_response = await client.post(
                            admin_url,
                            json=user_data,
                            headers={
                                "Authorization": f"Bearer {admin_token}",
                                "Content-Type": "application/json"
                            }
                        )
                        
                        if retry_response.status_code == 201:
                            logger.info(f"✅ Registration successful after cleanup: {request.email}")
                            
                            # Extract user ID from Location header
                            location = retry_response.headers.get("Location", "")
                            user_id = location.split("/")[-1] if location else "new-user"
                            
                            # ✅ CRITICAL: Setup proper grants/roles for the user BEFORE login
                            if user_id and user_id != "new-user":
                                try:
                                    await setup_user_roles(client, admin_token, user_id, request.email)
                                except Exception as e:
                                    logger.warning(f"Role setup failed for {request.email}: {e} - proceeding with login attempt")
                            
                            # Try auto-login after successful registration
                            auto_login_token = None
                            try:
                                login_response = await client.post(
                                    token_url,
                                    data={
                                        "grant_type": "password",
                                        "client_id": KEYCLOAK_CLIENT_ID,
                                        "client_secret": KEYCLOAK_CLIENT_SECRET if KEYCLOAK_CLIENT_SECRET else None,
                                        "username": request.email,
                                        "password": request.password,
                                        "scope": "openid"
                                    },
                                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                                )
                                
                                if login_response.status_code == 200:
                                    token_data = login_response.json()
                                    auto_login_token = token_data.get("access_token")
                            except Exception as e:
                                logger.warning(f"Auto-login failed after cleanup registration: {e}")
                            
                            # Return success response
                            response = RegisterResponse(
                                success=True,
                                user_id=user_id,
                                email=request.email,
                                username=request.username or request.email,
                                message="🎉 SUCCESS: Account issue resolved and registration completed!",
                                message_type="success",
                                display_color="green",
                                next_steps=[
                                    "Previous account issue has been resolved",
                                    "You can now log in with your credentials" if not auto_login_token else "You have been automatically logged in",
                                    "Your account is fully set up and ready to use"
                                ]
                            )
                            
                            if auto_login_token:
                                response_dict = response.dict()
                                response_dict["auto_login_token"] = auto_login_token
                                response_dict["message"] = "🎉 SUCCESS: Account fixed and you're now logged in!"
                                return response_dict
                            
                            return response
                        else:
                            # Retry also failed
                            logger.error(f"Registration retry failed: {retry_response.status_code} - {retry_response.text}")
                            raise HTTPException(
                                status_code=409,
                                detail="Account exists but could not be fixed automatically. Please contact support."
                            )
                    else:
                        # Cleanup failed or account is complete
                        if "complete" in cleanup_result.get("message", "").lower():
                            raise HTTPException(
                                status_code=409,
                                detail="An account with this email already exists and appears to be set up correctly. Please try logging in instead."
                            )
                        else:
                            raise HTTPException(
                                status_code=409,
                                detail="An account with this email already exists but could not be automatically resolved. Please contact support or try a different email."
                            )
                elif create_response.status_code == 400:
                    # Parse Keycloak error response
                    try:
                        error_data = create_response.json()
                        error_msg = error_data.get("error_description", error_data.get("error", "Invalid input"))
                    except:
                        error_msg = create_response.text
                    
                    logger.error(f"Failed to create user: {create_response.status_code} - {error_msg}")
                    
                    # Create detailed error response
                    error_detail = {"error": "validation_failed"}
                    
                    # Check for password policy errors
                    if "password" in error_msg.lower():
                        requirements = []
                        if "special" in error_msg.lower():
                            requirements.append("at least 1 special character (!@#$%^&*())")
                        if "uppercase" in error_msg.lower():
                            requirements.append("at least 1 uppercase letter (A-Z)")
                        if "lowercase" in error_msg.lower():
                            requirements.append("at least 1 lowercase letter (a-z)")
                        if "digit" in error_msg.lower() or "number" in error_msg.lower():
                            requirements.append("at least 1 number (0-9)")
                        if "length" in error_msg.lower():
                            requirements.append("at least 8 characters")
                        
                        error_detail["message"] = "Password does not meet security requirements"
                        error_detail["requirements"] = requirements
                        error_detail["example"] = "Example: MyPassword123!"
                        error_detail["current_password_length"] = len(request.password)
                    elif "email" in error_msg.lower():
                        error_detail["message"] = "Invalid email address"
                        error_detail["suggestions"] = [
                            "Check for typos in the email address",
                            "Ensure email format is correct (user@domain.com)",
                            "Email may already be registered"
                        ]
                    elif "username" in error_msg.lower():
                        error_detail["message"] = "Invalid username"
                        error_detail["requirements"] = [
                            "3-20 characters long",
                            "Only letters, numbers, underscore (_) and hyphen (-)",
                            "Must be unique"
                        ]
                    else:
                        error_detail["message"] = error_msg
                        error_detail["suggestions"] = [
                            "Check all fields are filled correctly",
                            "Ensure password meets all requirements",
                            "Try a different username/email"
                        ]
                    
                    # For frontend compatibility, send error as string with structured info
                    if "password" in error_msg.lower() and requirements:
                        detail_msg = f"Password does not meet security requirements. Missing: {', '.join(requirements)}. Example: Password123!"
                    elif "email" in error_msg.lower():
                        detail_msg = "Invalid email address. Please check the format (user@domain.com)"
                    elif "username" in error_msg.lower():
                        detail_msg = "Invalid username. Use 3-20 characters, only letters, numbers, underscore and hyphen"
                    else:
                        detail_msg = error_msg
                    
                    raise HTTPException(status_code=400, detail=detail_msg)
                else:
                    logger.error(f"Failed to create user: {create_response.status_code} - {create_response.text}")
                    raise HTTPException(
                        status_code=create_response.status_code,
                        detail="Failed to register user"
                    )
                    
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Keycloak: {e}")
            raise HTTPException(
                status_code=503, 
                detail="Registration service is temporarily unavailable. Please try again in a few moments."
            )
        except ValueError as e:
            # This catches validation errors from Pydantic validators
            logger.warning(f"Validation error during registration: {str(e)}")
            # Return validation error as string for frontend
            raise HTTPException(status_code=422, detail=str(e))
    
    elif AUTH_PROVIDER == "supabase":
        # For Supabase, you would implement Supabase registration here
        raise HTTPException(
            status_code=501, 
            detail="Supabase registration is not yet implemented. Please contact administrator."
        )
    
    else:
        # Test mode - create a dummy user but still validate password
        import uuid
        logger.info(f"Test mode registration for {request.email}")
        
        # Even in test mode, ensure password meets requirements
        # The validator will have already run, so if we're here, it's valid
        
        user_id = str(uuid.uuid4())
        
        return RegisterResponse(
            success=True,
            user_id=user_id,
            email=request.email,
            username=request.username or request.email,
            message="✅ SUCCESS: Registration completed! (Test Mode)",
            message_type="success",
            display_color="green",
            next_steps=[
                "This is test mode - no real account was created",
                "Configure Keycloak for real registration",
                f"Test User ID: {user_id}"
            ]
        )

@router.post("/login")
async def login(request: LoginRequest):
    """
    Login endpoint that authenticates with Keycloak and returns tokens.
    """
    if AUTH_PROVIDER == "keycloak":
        # Authenticate with Keycloak using Resource Owner Password Credentials Grant
        token_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
        
        # Prepare the request data
        data = {
            "grant_type": "password",
            "client_id": KEYCLOAK_CLIENT_ID,
            "username": request.email,
            "password": request.password,
            "scope": "openid"
        }
        
        # Add client secret if configured
        if KEYCLOAK_CLIENT_SECRET:
            data["client_secret"] = KEYCLOAK_CLIENT_SECRET
        
        try:
            # Log the authentication attempt
            logger.info(f"Attempting Keycloak login for user: {request.email}")
            logger.debug(f"Token URL: {token_url}")
            logger.debug(f"Client ID: {KEYCLOAK_CLIENT_ID}")
            logger.debug(f"Has client secret: {bool(KEYCLOAK_CLIENT_SECRET)}")
            
            async with httpx.AsyncClient(verify=False) as client:  # verify=False for self-signed certs
                response = await client.post(
                    token_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                logger.debug(f"Keycloak response status: {response.status_code}")
                
                if response.status_code == 200:
                    token_data = response.json()
                    
                    # Parse the JWT to get user info (without validation, just for user_id)
                    import jwt
                    decoded = jwt.decode(token_data["access_token"], options={"verify_signature": False})
                    
                    return LoginResponse(
                        access_token=token_data["access_token"],
                        refresh_token=token_data.get("refresh_token"),
                        expires_in=token_data.get("expires_in"),
                        user_id=decoded.get("sub"),
                        email=decoded.get("email", request.email)
                    )
                elif response.status_code == 401:
                    error_details = response.text
                    logger.error(f"Keycloak authentication failed for {request.email}: {error_details}")
                    raise HTTPException(status_code=401, detail="Invalid credentials")
                elif response.status_code == 400:
                    # Handle bad request errors (like invalid scope)
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error_description", error_data.get("error", "Bad request"))
                    except:
                        error_msg = response.text
                    
                    logger.error(f"Keycloak login failed: {response.status_code} - {response.text}")
                    
                    # Check for different error types
                    if "invalid_grant" in str(error_msg).lower() and "not fully set up" in str(error_msg).lower():
                        # Account exists but needs completion - provide clear instructions
                        logger.warning(f"Account not fully set up for user: {request.email}")
                        raise HTTPException(
                            status_code=400,
                            detail="Your account is incomplete. Please try registering again with this email address. The system will handle any existing account issues automatically."
                        )
                    elif "invalid_scope" in str(error_msg).lower() or "scope" in str(error_msg).lower():
                        logger.info("Retrying login with minimal scope (openid only)")
                        # Try again with just openid scope
                        data["scope"] = "openid"
                        retry_response = await client.post(
                            token_url,
                            data=data,
                            headers={"Content-Type": "application/x-www-form-urlencoded"}
                        )
                        
                        if retry_response.status_code == 200:
                            token_data = retry_response.json()
                            
                            # Parse the JWT to get user info
                            import jwt
                            decoded = jwt.decode(token_data["access_token"], options={"verify_signature": False})
                            
                            return LoginResponse(
                                access_token=token_data["access_token"],
                                refresh_token=token_data.get("refresh_token"),
                                expires_in=token_data.get("expires_in"),
                                user_id=decoded.get("sub"),
                                email=decoded.get("email", request.email)
                            )
                        else:
                            raise HTTPException(status_code=401, detail="Invalid credentials")
                    elif "invalid_grant" in str(error_msg).lower():
                        # Generic invalid grant error
                        raise HTTPException(
                            status_code=401,
                            detail="Invalid email or password. Please check your credentials and try again."
                        )
                    else:
                        raise HTTPException(status_code=400, detail=f"Authentication failed: {error_msg}")
                else:
                    logger.error(f"Keycloak login failed: {response.status_code} - {response.text}")
                    raise HTTPException(status_code=response.status_code, detail="Authentication failed")
                    
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Keycloak: {e}")
            raise HTTPException(status_code=503, detail="Authentication service unavailable")
    
    elif AUTH_PROVIDER == "supabase":
        # For Supabase, you would implement Supabase authentication here
        # This is a placeholder
        raise HTTPException(status_code=501, detail="Supabase authentication not implemented")
    
    else:
        # Test mode - return a dummy token
        return LoginResponse(
            access_token="test-token-12345",
            user_id="test-user-001",
            email=request.email,
            expires_in=3600
        )

@router.post("/refresh")
async def refresh_token(request: Request):
    """
    Refresh access token using refresh token.
    Accepts refresh_token in JSON body.
    """
    # Handle JSON body
    try:
        body = await request.json()
        refresh_token = body.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=422, detail="refresh_token is required")
    except Exception as e:
        logger.error(f"Failed to parse request body: {e}")
        raise HTTPException(status_code=422, detail="Invalid request body")
    
    if AUTH_PROVIDER == "keycloak":
        token_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
        
        data = {
            "grant_type": "refresh_token",
            "client_id": KEYCLOAK_CLIENT_ID,
            "refresh_token": refresh_token
        }
        
        if KEYCLOAK_CLIENT_SECRET:
            data["client_secret"] = KEYCLOAK_CLIENT_SECRET
        
        try:
            logger.info(f"Attempting to refresh token for client: {KEYCLOAK_CLIENT_ID}")
            logger.debug(f"Refresh token URL: {token_url}")
            
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.post(
                    token_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                logger.debug(f"Keycloak refresh response status: {response.status_code}")
                
                if response.status_code == 200:
                    token_data = response.json()
                    
                    # Parse the JWT to get user info (without validation, just for user_id)
                    import jwt
                    decoded = jwt.decode(token_data["access_token"], options={"verify_signature": False})
                    
                    return {
                        "access_token": token_data["access_token"],
                        "refresh_token": token_data.get("refresh_token", refresh_token),  # Return same refresh token if not provided
                        "expires_in": token_data.get("expires_in"),
                        "user_id": decoded.get("sub"),
                        "email": decoded.get("email")
                    }
                elif response.status_code == 400:
                    # Handle specific Keycloak errors
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error_description", error_data.get("error", ""))
                        logger.error(f"Keycloak refresh token failed: {error_msg}")
                        
                        if "invalid_grant" in str(error_msg).lower():
                            if "token is not active" in str(error_msg).lower() or "token expired" in str(error_msg).lower():
                                raise HTTPException(
                                    status_code=401, 
                                    detail="Refresh token has expired. Please log in again."
                                )
                            else:
                                raise HTTPException(
                                    status_code=401,
                                    detail="Invalid refresh token. Please log in again."
                                )
                        else:
                            raise HTTPException(status_code=401, detail=f"Token refresh failed: {error_msg}")
                    except:
                        logger.error(f"Keycloak refresh token failed with status {response.status_code}: {response.text}")
                        raise HTTPException(status_code=401, detail="Invalid refresh token")
                else:
                    logger.error(f"Unexpected response from Keycloak: {response.status_code} - {response.text}")
                    raise HTTPException(status_code=401, detail="Invalid refresh token")
                    
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Keycloak for token refresh: {e}")
            raise HTTPException(status_code=503, detail="Authentication service unavailable")
    
    elif AUTH_PROVIDER == "supabase":
        # For Supabase, implement refresh token logic here
        raise HTTPException(
            status_code=501, 
            detail="Supabase token refresh is not yet implemented"
        )
    
    else:
        # Test mode - return a dummy refreshed token
        logger.info("Test mode: Returning dummy refreshed token")
        return {
            "access_token": "test-refreshed-token-" + str(int(time.time())),
            "refresh_token": refresh_token,  # Return the same refresh token
            "expires_in": 3600,
            "user_id": "test-user-001",
            "email": "test@example.com"
        }

async def cleanup_incomplete_account_internal(email: str) -> dict:
    """
    Internal function to remove an incomplete account from Keycloak to allow re-registration.
    This is used internally when registration fails due to incomplete accounts.
    """
    if AUTH_PROVIDER == "keycloak":
        logger.info(f"Attempting to clean up incomplete account for: {email}")
        
        # Get admin token to manage users
        admin_token = await get_keycloak_admin_token()
        if not admin_token:
            return {"success": False, "message": "Unable to obtain admin access"}
        
        try:
            async with httpx.AsyncClient(verify=False) as client:
                # First, find the user by email
                users_url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users"
                search_response = await client.get(
                    users_url,
                    params={"email": email, "exact": "true"},
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
                
                if search_response.status_code == 200:
                    users = search_response.json()
                    if users and len(users) > 0:
                        user = users[0]
                        user_id = user.get("id")
                        
                        # STRICT CLEANUP CRITERIA - Only remove accounts that are clearly incomplete
                        # DO NOT remove users who are verified and have correct grants
                        email_verified = user.get("emailVerified", False)
                        account_enabled = user.get("enabled", True) 
                        required_actions = user.get("requiredActions", [])
                        
                        # Additional checks for account completeness
                        has_credentials = user.get("credentials", [])  # Check if user has set password
                        user_created_recently = False  # Could add timestamp check if needed
                        
                        # Log current account state for debugging
                        logger.info(f"Account analysis for {email}: verified={email_verified}, enabled={account_enabled}, required_actions={required_actions}, has_credentials={bool(has_credentials)}")
                        
                        # ONLY remove account if ALL of these problematic conditions are met:
                        # 1. Email is NOT verified AND
                        # 2. Account has required actions (like email verification) AND  
                        # 3. Account is disabled OR has no credentials set
                        should_cleanup = (
                            not email_verified and  # Email not verified
                            required_actions and    # Has pending required actions
                            (not account_enabled or not has_credentials)  # And either disabled or no password set
                        )
                        
                        if should_cleanup:
                            logger.warning(f"🗑️ CLEANUP JUSTIFIED: Account {email} is incomplete (unverified={not email_verified}, required_actions={required_actions}, enabled={account_enabled}, has_credentials={bool(has_credentials)})")
                            # Delete the incomplete user
                            delete_url = f"{users_url}/{user_id}"
                            delete_response = await client.delete(
                                delete_url,
                                headers={"Authorization": f"Bearer {admin_token}"}
                            )
                            
                            if delete_response.status_code == 204:
                                logger.info(f"Successfully cleaned up incomplete account: {email}")
                                return {
                                    "success": True,
                                    "message": "Incomplete account removed. Ready for registration.",
                                    "can_register": True
                                }
                            else:
                                logger.error(f"Failed to delete user: {delete_response.status_code}")
                                return {"success": False, "message": "Failed to clean up account"}
                        else:
                            # Account is verified and complete - DO NOT DELETE
                            logger.info(f"✅ ACCOUNT PROTECTED: {email} is verified and complete (verified={email_verified}, enabled={account_enabled}, no_required_actions={not bool(required_actions)}, has_credentials={bool(has_credentials)})")
                            return {
                                "success": False,
                                "message": "Account is verified and properly set up. Please use the login page instead.",
                                "can_register": False,
                                "reason": "account_complete_and_verified"
                            }
                    else:
                        return {
                            "success": False,
                            "message": "No account found with this email address.",
                            "can_register": True
                        }
                else:
                    return {"success": False, "message": "Failed to search for user"}
                    
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Keycloak: {e}")
            return {"success": False, "message": "Authentication service unavailable"}
    else:
        return {"success": False, "message": "Account cleanup not supported for this provider"}

async def setup_user_roles(client, admin_token: str, user_id: str, user_email: str):
    """
    Setup proper Keycloak roles/grants for a newly created user to prevent 'Account is not fully set up' errors.
    This function assigns essential realm roles that enable proper authentication.
    """
    logger.info(f"Setting up roles for user {user_email} (ID: {user_id})")
    
    # First, get the current user data to preserve username
    user_url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users/{user_id}"
    try:
        user_response = await client.get(
            user_url,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if user_response.status_code == 200:
            current_user = user_response.json()
            username = current_user.get("username", user_email)
            
            # Clear ALL required actions and set email verified if needed
            logger.info(f"Clearing required actions and setting up user {user_email}")
            
            update_data = {
                "username": username,
                "email": current_user.get("email", user_email),
                "enabled": True,
                "emailVerified": EMAIL_VERIFIED_AUTO,  # Set based on environment variable
                "requiredActions": [],  # CRITICAL: Clear ALL required actions
                "attributes": {
                    **current_user.get("attributes", {}),
                    "account_setup_complete": ["true"],
                    "email_verified_auto": [str(EMAIL_VERIFIED_AUTO).lower()],
                    "registration_complete": ["true"]
                }
            }
            
            update_response = await client.put(
                user_url,
                json=update_data,
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if update_response.status_code == 204:
                logger.info(f"✅ User setup completed: email_verified={EMAIL_VERIFIED_AUTO}, required_actions=cleared")
            else:
                logger.warning(f"Failed to update user setup: {update_response.status_code} - {update_response.text}")
                
    except Exception as e:
        logger.warning(f"Could not complete user setup: {e}")
    
    # Assign client-specific roles if the client has Authorization enabled
    try:
        # First find the mcp-api client ID
        clients_url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/clients"
        clients_response = await client.get(
            clients_url,
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"clientId": KEYCLOAK_CLIENT_ID}
        )
        
        if clients_response.status_code == 200:
            clients = clients_response.json()
            if clients and len(clients) > 0:
                client_uuid = clients[0]["id"]
                logger.info(f"Found client {KEYCLOAK_CLIENT_ID} with UUID: {client_uuid}")
                
                # Get available client roles
                client_roles_url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/clients/{client_uuid}/roles"
                client_roles_response = await client.get(
                    client_roles_url,
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
                
                if client_roles_response.status_code == 200:
                    client_roles = client_roles_response.json()
                    if client_roles:
                        logger.info(f"Found {len(client_roles)} client roles to assign")
                        # Assign all client roles to the user
                        user_client_roles_url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users/{user_id}/role-mappings/clients/{client_uuid}"
                        assign_client_roles_response = await client.post(
                            user_client_roles_url,
                            json=client_roles,
                            headers={
                                "Authorization": f"Bearer {admin_token}",
                                "Content-Type": "application/json"
                            }
                        )
                        
                        if assign_client_roles_response.status_code == 204:
                            logger.info(f"✅ Successfully assigned client roles to user {user_email}")
                        else:
                            logger.warning(f"Could not assign client roles: {assign_client_roles_response.status_code}")
                    else:
                        logger.info("No client-specific roles found to assign")
                else:
                    logger.warning(f"Could not fetch client roles: {client_roles_response.status_code}")
            else:
                logger.warning(f"Client {KEYCLOAK_CLIENT_ID} not found")
        else:
            logger.warning(f"Could not fetch clients: {clients_response.status_code}")
            
    except Exception as e:
        logger.warning(f"Could not assign client roles: {e}")
    
    try:
        # Get available realm roles
        realm_roles_url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/roles"
        roles_response = await client.get(
            realm_roles_url,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if roles_response.status_code != 200:
            logger.error(f"Failed to fetch realm roles: {roles_response.status_code}")
            return
        
        available_roles = roles_response.json()
        
        # Define required roles for proper account setup based on realm-config-keycloak.json
        required_roles = [
            "user",               # Standard user access role (from realm config)
            "offline_access",     # Required for refresh tokens  
            "uma_authorization"   # User Managed Access permissions
        ]
        
        # Find roles that exist in the realm
        roles_to_assign = []
        for role_name in required_roles:
            for role in available_roles:
                if role.get("name") == role_name:
                    roles_to_assign.append({
                        "id": role.get("id"),
                        "name": role.get("name"),
                        "description": role.get("description", "")
                    })
                    break
        
        if roles_to_assign:
            # Assign roles to the user
            user_roles_url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users/{user_id}/role-mappings/realm"
            assign_response = await client.post(
                user_roles_url,
                json=roles_to_assign,
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if assign_response.status_code == 204:
                logger.info(f"✅ Successfully assigned {len(roles_to_assign)} roles to user {user_email}")
                for role in roles_to_assign:
                    logger.info(f"   - Assigned role: {role['name']}")
            else:
                logger.error(f"❌ Failed to assign roles: {assign_response.status_code} - {assign_response.text}")
        else:
            logger.warning(f"⚠️ No required roles found in realm {KEYCLOAK_REALM}")
            
    except Exception as e:
        logger.error(f"❌ Error setting up user roles for {user_email}: {e}")
        raise

@router.post("/logout")
async def logout(refresh_token: Optional[str] = None):
    """
    Logout endpoint that revokes tokens if supported.
    """
    if AUTH_PROVIDER == "keycloak" and refresh_token:
        logout_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/logout"
        
        data = {
            "client_id": KEYCLOAK_CLIENT_ID,
            "refresh_token": refresh_token
        }
        
        if KEYCLOAK_CLIENT_SECRET:
            data["client_secret"] = KEYCLOAK_CLIENT_SECRET
        
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.post(
                    logout_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code in [204, 200]:
                    return {"message": "Logged out successfully"}
                else:
                    logger.warning(f"Logout returned status {response.status_code}")
                    return {"message": "Logout completed"}
                    
        except httpx.RequestError as e:
            logger.error(f"Failed to logout: {e}")
            # Don't fail on logout errors
            return {"message": "Logout completed (local)"}
    
    return {"message": "Logged out successfully"}

@router.get("/provider")
async def get_auth_provider():
    """Get the current authentication provider configuration"""
    return {
        "provider": AUTH_PROVIDER,
        "keycloak_url": KEYCLOAK_URL if AUTH_PROVIDER == "keycloak" else None,
        "keycloak_realm": KEYCLOAK_REALM if AUTH_PROVIDER == "keycloak" else None,
        "keycloak_client_id": KEYCLOAK_CLIENT_ID if AUTH_PROVIDER == "keycloak" else None
    }

@router.post("/registration-success")
async def handle_registration_success(user_id: str, email: str):
    """
    Handle post-registration tasks and provide onboarding information.
    Called after successful registration to set up user profile, send welcome email, etc.
    """
    logger.info(f"🎆 Processing post-registration for user: {email} (ID: {user_id})")
    
    # Here you can add post-registration logic like:
    # - Creating user profile in your database
    # - Sending welcome email
    # - Setting up default preferences
    # - Adding to mailing lists
    # - Creating initial workspace/projects
    
    onboarding_info = {
        "success": True,
        "user_id": user_id,
        "email": email,
        "welcome_message": f"🎆 Welcome to MCP Platform, {email}!",
        "onboarding_steps": [
            {
                "step": 1,
                "title": "Verify Your Email",
                "description": "Check your inbox for a verification email",
                "status": "pending",
                "optional": False
            },
            {
                "step": 2,
                "title": "Complete Your Profile",
                "description": "Add your name, avatar, and preferences",
                "status": "pending",
                "optional": False
            },
            {
                "step": 3,
                "title": "Create Your First Project",
                "description": "Start by creating a new project or importing an existing one",
                "status": "pending",
                "optional": True
            },
            {
                "step": 4,
                "title": "Explore Features",
                "description": "Check out our documentation and tutorials",
                "status": "pending",
                "optional": True
            }
        ],
        "quick_links": [
            {"title": "Documentation", "url": "/ai_docs"},
            {"title": "Profile Settings", "url": "/settings/profile"},
            {"title": "Create Project", "url": "/projects/new"},
            {"title": "Support", "url": "/support"}
        ],
        "tips": [
            "Your password is securely encrypted and never stored in plain text",
            "Enable two-factor authentication for extra security",
            "You can change your email and username in profile settings",
            "Join our community forum to connect with other users"
        ]
    }
    
    # Log successful registration for analytics
    logger.info(f"✅ Registration complete for {email}. Onboarding information prepared.")

    return onboarding_info

@router.get("/verify")
async def verify_auth():
    """Verify that authentication endpoints are working"""
    return {"status": "ok", "provider": AUTH_PROVIDER}

@router.get("/password-requirements")
async def get_password_requirements():
    """Get password requirements for registration"""
    return {
        "requirements": [
            {"rule": "min_length", "value": 8, "description": "At least 8 characters"},
            {"rule": "uppercase", "value": 1, "description": "At least 1 uppercase letter (A-Z)"},
            {"rule": "lowercase", "value": 1, "description": "At least 1 lowercase letter (a-z)"},
            {"rule": "digits", "value": 1, "description": "At least 1 number (0-9)"},
            {"rule": "special", "value": 1, "description": "At least 1 special character (!@#$%^&*()-_+=)"}
        ],
        "example_passwords": [
            "Password123!",
            "SecurePass@2024",
            "MyP@ssw0rd"
        ],
        "tips": [
            "Use a mix of uppercase and lowercase letters",
            "Include numbers and special characters",
            "Avoid using personal information",
            "Make it memorable but hard to guess"
        ]
    }

@router.post("/validate-password")
async def validate_password(password: str):
    """Validate a password against requirements without registering"""
    import re
    
    issues = []
    suggestions = []
    
    # Check each requirement
    if len(password) < 8:
        issues.append("Too short - needs at least 8 characters")
        suggestions.append(f"Add {8 - len(password)} more characters")
    
    if not re.search(r'[A-Z]', password):
        issues.append("Missing uppercase letter")
        suggestions.append("Try capitalizing the first letter")
    
    if not re.search(r'[a-z]', password):
        issues.append("Missing lowercase letter")
        suggestions.append("Add some lowercase letters")
    
    if not re.search(r'\d', password):
        issues.append("Missing number")
        suggestions.append("Add a number like your birth year or favorite number")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>\-_+=\[\]\\/;`~]', password):
        issues.append("Missing special character")
        suggestions.append("Add a special character like ! or @")
    
    # Check password strength
    strength = "weak"
    strength_score = 0
    
    if len(password) >= 8:
        strength_score += 1
    if len(password) >= 12:
        strength_score += 1
    if re.search(r'[A-Z]', password) and re.search(r'[a-z]', password):
        strength_score += 1
    if re.search(r'\d', password):
        strength_score += 1
    if re.search(r'[!@#$%^&*(),.?":{}|<>\-_+=\[\]\\/;`~]', password):
        strength_score += 1
    
    if strength_score >= 5:
        strength = "strong"
    elif strength_score >= 3:
        strength = "medium"
    
    return {
        "valid": len(issues) == 0,
        "strength": strength,
        "score": strength_score,
        "max_score": 5,
        "issues": issues,
        "suggestions": suggestions,
        "length": len(password),
        "has_uppercase": bool(re.search(r'[A-Z]', password)),
        "has_lowercase": bool(re.search(r'[a-z]', password)),
        "has_digits": bool(re.search(r'\d', password)),
        "has_special": bool(re.search(r'[!@#$%^&*(),.?":{}|<>\-_+=\[\]\\/;`~]', password))
    }

# ==================== TOKEN MANAGEMENT ENDPOINTS ====================
# All token management has been moved to dedicated router at /api/v2/tokens
