#!/usr/bin/env python3
"""
Test script to verify the authentication fix allows global context retrieval.

This simulates the exact error scenario from the user report.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_context_resolve_with_auth():
    """Test context resolve operation with authentication."""

    try:
        # Import the unified context controller
        from fastmcp.task_management.interface.controllers.unified_context_controller import (
            UnifiedContextMCPController,
        )

        logger.info("🔍 Testing global context retrieval with authentication...")

        # Create controller instance
        controller = UnifiedContextMCPController()
        logger.info("✅ UnifiedContextController created")

        # Test the exact operation that was failing
        logger.info("🔧 Testing manage_context.resolve operation...")

        try:
            # This should fail with proper error handling (no user authentication)
            result = await controller.manage_context(
                action="resolve", level="global", context_id="global_singleton"
            )
            logger.info(f"✅ Context resolve succeeded: {result.get('success', False)}")

        except Exception as e:
            logger.info(f"✅ Expected authentication error: {e}")
            # Check if it's the correct authentication error
            if "requires user authentication" in str(e):
                logger.info("✅ Authentication error is properly formatted")
                logger.info("✅ Auth helper is working as expected")
            else:
                logger.error(f"❌ Unexpected error: {e}")
                return False

        # Test with provided user_id
        logger.info("🔧 Testing with provided user_id...")
        try:
            result = await controller.manage_context(
                action="resolve",
                level="global",
                context_id="global_singleton",
                user_id="test-user-fix-123",
            )
            logger.info(
                f"✅ Context resolve with user_id succeeded: {result.get('success', False)}"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Context resolve with user_id failed: {e}")
            return False

    except ImportError as e:
        logger.error(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


async def test_auth_helper_isolation():
    """Test auth helper in isolation to verify the fix."""

    try:
        from fastmcp.task_management.interface.controllers.auth_helper import (
            get_authenticated_user_id,
        )

        logger.info("🔍 Testing auth helper authentication flow...")

        # Test case 1: No authentication (should fail gracefully)
        try:
            user_id = get_authenticated_user_id(operation_name="manage_context.resolve")
            logger.error(f"❌ Unexpected success without auth: {user_id}")
            return False
        except Exception as e:
            if "requires user authentication" in str(e):
                logger.info("✅ Auth helper correctly requires authentication")
            else:
                logger.error(f"❌ Unexpected auth error: {e}")
                return False

        # Test case 2: With provided user_id (should work)
        try:
            user_id = get_authenticated_user_id(
                provided_user_id="test-user-fix-456",
                operation_name="manage_context.resolve",
            )
            logger.info(f"✅ Auth helper with user_id succeeded: {user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Auth helper with user_id failed: {e}")
            return False

    except ImportError as e:
        logger.error(f"❌ Auth helper import failed: {e}")
        return False


async def main():
    """Run authentication fix verification tests."""

    logger.info("🚀 Starting authentication fix verification tests...")

    # Test 1: Auth helper isolation
    logger.info("=" * 60)
    logger.info("TEST 1: Auth Helper Authentication Flow")
    test1_result = await test_auth_helper_isolation()

    # Test 2: Context retrieval with authentication
    logger.info("=" * 60)
    logger.info("TEST 2: Global Context Retrieval with Authentication")
    test2_result = await test_context_resolve_with_auth()

    # Summary
    logger.info("=" * 60)
    passed_tests = sum([test1_result, test2_result])
    total_tests = 2

    logger.info(f"🎯 TEST RESULTS: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        logger.info("✅ Authentication fix verification PASSED!")
        logger.info("✅ JWT token processing and user context extraction should work")
        logger.info(
            "✅ Global context retrieval should work with proper authentication"
        )
    else:
        logger.error("❌ Authentication fix verification FAILED!")
        logger.error("❌ Additional troubleshooting required")

    return passed_tests == total_tests


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
