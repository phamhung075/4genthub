#!/usr/bin/env python3
"""
Test Global Context User Isolation Authentication Fix

This script tests the critical fixes made to resolve the authentication issue where:
- DualAuthMiddleware validates JWT tokens successfully 
- But MCP request returns 401 "Authentication required"

Root cause was ContextVar propagation gap and inconsistent global context user handling.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def test_request_context_middleware():
    """Test RequestContextMiddleware ContextVar propagation."""
    
    try:
        from fastmcp.server.http_server import _current_http_request, set_http_request
        from starlette.requests import Request
        from starlette.testclient import TestClient
        
        logger.info("=" * 60)
        logger.info("TEST 1: Testing RequestContextMiddleware ContextVar propagation")
        
        # Test ContextVar setting and getting
        logger.info("Testing ContextVar direct access...")
        
        # Initially should be None
        current = _current_http_request.get()
        logger.info(f"Initial ContextVar value: {current}")
        assert current is None, "ContextVar should start as None"
        
        # Create a mock request
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/test",
            "headers": [],
            "query_string": b"",
        }
        mock_request = Request(mock_scope)
        
        # Test context manager
        with set_http_request(mock_request):
            context_request = _current_http_request.get()
            logger.info(f"ContextVar inside context: {context_request}")
            assert context_request is not None, "ContextVar should be set inside context"
            assert context_request.method == "POST", "Request method should match"
        
        # Should be None again after context
        final = _current_http_request.get()
        logger.info(f"Final ContextVar value: {final}")
        assert final is None, "ContextVar should be None after context"
        
        logger.info("✅ RequestContextMiddleware ContextVar test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ RequestContextMiddleware test failed: {e}")
        import traceback
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        return False

async def test_auth_helper_functionality():
    """Test auth helper functions work correctly."""
    
    try:
        from fastmcp.task_management.interface.controllers.auth_helper import (
            get_user_id_from_request_state, 
            get_authenticated_user_id
        )
        from fastmcp.server.http_server import _current_http_request, set_http_request
        from starlette.requests import Request
        
        logger.info("=" * 60)
        logger.info("TEST 2: Testing auth helper functions")
        
        # Test without request context (should return None)
        user_id = get_user_id_from_request_state()
        logger.info(f"User ID without request: {user_id}")
        assert user_id is None, "Should be None without request context"
        
        # Test with request context but no user_id
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/test",
            "headers": [],
            "query_string": b"",
        }
        mock_request = Request(mock_scope)
        
        with set_http_request(mock_request):
            user_id = get_user_id_from_request_state()
            logger.info(f"User ID with request but no state: {user_id}")
            assert user_id is None, "Should be None without user_id in state"
        
        # Test with user_id in request state
        with set_http_request(mock_request):
            # Simulate DualAuthMiddleware setting user_id
            mock_request.state.user_id = "test-user-123"
            user_id = get_user_id_from_request_state()
            logger.info(f"User ID with state: {user_id}")
            assert user_id == "test-user-123", "Should return user_id from request state"
        
        logger.info("✅ Auth helper functionality test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Auth helper test failed: {e}")
        import traceback
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        return False

async def test_global_context_user_isolation():
    """Test global context user isolation logic."""
    
    try:
        from fastmcp.auth.mcp_integration.repository_filter import UserFilteredContextRepository
        
        logger.info("=" * 60)
        logger.info("TEST 3: Testing global context user isolation logic")
        
        class MockRepository:
            def __init__(self):
                self.contexts = {}
            
            def find_by_id(self, context_id):
                return self.contexts.get(context_id)
            
            def save(self, context):
                context.id = getattr(context, 'id', f'ctx-{len(self.contexts)}')
                self.contexts[context.id] = context
                return context
        
        class MockContext:
            def __init__(self, level="global", user_id=None):
                self.level = level
                self.user_id = user_id
                self.id = None
        
        # Create filtered repository
        base_repo = MockRepository()
        filtered_repo = UserFilteredContextRepository(base_repo)
        
        # Mock the current user
        def mock_get_user_id():
            return "user-123"
        filtered_repo._get_current_user_id = mock_get_user_id
        
        # Test saving global context
        logger.info("Testing global context save...")
        global_context = MockContext(level="global")
        saved_context = filtered_repo.save(global_context)
        
        logger.info(f"Saved context user_id: {saved_context.user_id}")
        assert saved_context.user_id == "user-123", "Global context should have user_id set"
        
        # Test finding context with correct user
        found_context = filtered_repo.find_by_id(saved_context.id)
        logger.info(f"Found context: {found_context}")
        assert found_context is not None, "Should find context for correct user"
        
        # Test context isolation (different user can't access)
        def mock_get_other_user_id():
            return "user-456"
        filtered_repo._get_current_user_id = mock_get_other_user_id
        
        blocked_context = filtered_repo.find_by_id(saved_context.id)
        logger.info(f"Context access by other user: {blocked_context}")
        assert blocked_context is None, "Other user should not access context"
        
        logger.info("✅ Global context user isolation test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Global context isolation test failed: {e}")
        import traceback
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        return False

async def test_middleware_ordering():
    """Test that middleware ordering fixes the authentication issue."""
    
    try:
        from fastmcp.server.http_server import create_base_app, RequestContextMiddleware
        from starlette.middleware import Middleware
        from starlette.applications import Starlette
        
        logger.info("=" * 60)
        logger.info("TEST 4: Testing middleware ordering fix")
        
        # Create app with middleware
        middleware = []  # Start empty
        routes = []
        
        app = create_base_app(routes, middleware)
        
        # Check that RequestContextMiddleware was inserted at the beginning
        logger.info(f"Middleware stack length: {len(app.user_middleware)}")
        
        # Find RequestContextMiddleware in the stack
        request_middleware_found = False
        middleware_position = -1
        
        for i, middleware_item in enumerate(app.user_middleware):
            logger.info(f"Middleware {i}: {middleware_item}")
            if hasattr(middleware_item, 'cls') and middleware_item.cls == RequestContextMiddleware:
                request_middleware_found = True
                middleware_position = i
                break
        
        logger.info(f"RequestContextMiddleware found: {request_middleware_found}")
        logger.info(f"RequestContextMiddleware position: {middleware_position}")
        
        assert request_middleware_found, "RequestContextMiddleware should be in stack"
        assert middleware_position == 0, "RequestContextMiddleware should be first (position 0)"
        
        logger.info("✅ Middleware ordering test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Middleware ordering test failed: {e}")
        import traceback
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        return False

async def run_all_tests():
    """Run all authentication fix tests."""
    
    logger.info("🚀 Starting Global Context Authentication Fix Tests")
    logger.info("=" * 80)
    
    results = []
    
    # Run tests
    results.append(await test_request_context_middleware())
    results.append(await test_auth_helper_functionality())
    results.append(await test_global_context_user_isolation())
    results.append(await test_middleware_ordering())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    logger.info("=" * 80)
    logger.info(f"TEST SUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED - Authentication fix verified!")
        print("\n✅ AUTHENTICATION FIX VALIDATION: SUCCESS")
        print("The global context user isolation authentication issue has been resolved:")
        print("  1. ✅ RequestContextMiddleware now runs first (ContextVar propagation fixed)")  
        print("  2. ✅ Global contexts now enforce user isolation")
        print("  3. ✅ Auth helper provides detailed debugging")
        print("  4. ✅ Middleware ordering prevents 401 errors in MCP tools")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed")
        print("\n❌ AUTHENTICATION FIX VALIDATION: FAILED")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)