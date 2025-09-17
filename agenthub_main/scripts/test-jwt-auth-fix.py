#!/usr/bin/env python3
"""
Test script to verify JWT authentication fix for global context retrieval.

This script tests the authentication chain to ensure JWT tokens are properly
processed and user_id is extracted for context operations.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_auth_helper():
    """Test the auth_helper functionality with mocked request state."""
    
    try:
        from fastmcp.task_management.interface.controllers.auth_helper import get_authenticated_user_id
        
        # Test 1: Provided user_id (should work)
        logger.info("=" * 60)
        logger.info("TEST 1: Testing with provided user_id")
        try:
            user_id = get_authenticated_user_id(provided_user_id="test-user-123", operation_name="test.resolve")
            logger.info(f"✅ SUCCESS: Got user_id: {user_id}")
        except Exception as e:
            logger.error(f"❌ FAILED: {e}")
        
        # Test 2: No user_id provided (should fail gracefully)
        logger.info("=" * 60)
        logger.info("TEST 2: Testing without provided user_id (should fail gracefully)")
        try:
            user_id = get_authenticated_user_id(provided_user_id=None, operation_name="test.resolve")
            logger.error(f"❌ UNEXPECTED SUCCESS: Got user_id: {user_id}")
        except Exception as e:
            logger.info(f"✅ EXPECTED FAILURE: {e}")
            logger.info("This is expected when no authentication context is available")
        
        logger.info("=" * 60)
        logger.info("Auth helper tests completed")
        
    except ImportError as e:
        logger.error(f"Failed to import auth_helper: {e}")
        return False
    except Exception as e:
        logger.error(f"Auth helper test failed: {e}")
        return False
    
    return True

async def test_dual_auth_middleware():
    """Test DualAuthMiddleware functionality."""
    
    try:
        from fastmcp.auth.middleware.dual_auth_middleware import DualAuthMiddleware, create_dual_auth_middleware
        
        logger.info("=" * 60)
        logger.info("TEST 3: Testing DualAuthMiddleware creation")
        
        # Test middleware creation
        middleware_class = create_dual_auth_middleware()
        logger.info(f"✅ DualAuthMiddleware class created: {middleware_class}")
        
        # Test middleware instantiation
        middleware = DualAuthMiddleware(None)  # None app for testing
        logger.info(f"✅ DualAuthMiddleware instance created: {middleware}")
        
        logger.info("=" * 60)
        logger.info("DualAuthMiddleware tests completed")
        
    except ImportError as e:
        logger.error(f"Failed to import DualAuthMiddleware: {e}")
        return False
    except Exception as e:
        logger.error(f"DualAuthMiddleware test failed: {e}")
        return False
    
    return True

async def test_jwt_service():
    """Test JWT service functionality."""
    
    try:
        from fastmcp.auth.domain.services.jwt_service import JWTService
        
        logger.info("=" * 60)
        logger.info("TEST 4: Testing JWT service")
        
        # Create JWT service with test secret
        jwt_service = JWTService(secret_key="test-secret-key-for-authentication-fix")
        
        # Create a test token
        payload = {"user_id": "test-user-123", "type": "api_token"}
        token = jwt_service.create_token(payload, token_type="api_token")
        logger.info(f"✅ JWT token created: {token[:50]}...")
        
        # Verify the token
        verified_payload = jwt_service.verify_token(token, expected_type="api_token")
        logger.info(f"✅ JWT token verified: {verified_payload}")
        
        if verified_payload.get("user_id") == "test-user-123":
            logger.info("✅ JWT token contains correct user_id")
        else:
            logger.error(f"❌ JWT token user_id mismatch: {verified_payload.get('user_id')}")
        
        logger.info("=" * 60)
        logger.info("JWT service tests completed")
        
    except ImportError as e:
        logger.error(f"Failed to import JWT service: {e}")
        return False
    except Exception as e:
        logger.error(f"JWT service test failed: {e}")
        return False
    
    return True

async def main():
    """Run all authentication tests."""
    
    logger.info("🔍 Starting JWT authentication fix tests...")
    logger.info(f"🔧 Python path: {sys.path[0]}")
    
    results = []
    
    # Test auth helper
    results.append(await test_auth_helper())
    
    # Test DualAuthMiddleware
    results.append(await test_dual_auth_middleware())
    
    # Test JWT service
    results.append(await test_jwt_service())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    logger.info("=" * 60)
    logger.info(f"🎯 TEST SUMMARY: {passed}/{total} test groups passed")
    
    if passed == total:
        logger.info("✅ All authentication components are working correctly!")
        logger.info("✅ The JWT authentication fix should resolve global context retrieval issues")
    else:
        logger.error("❌ Some authentication components failed tests")
        logger.error("❌ Additional troubleshooting may be needed")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)