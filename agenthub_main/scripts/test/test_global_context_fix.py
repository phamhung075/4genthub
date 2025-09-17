#!/usr/bin/env python3
"""
Test script to verify that 'global' as context_id works properly.
Tests the normalization of 'global' to user-specific UUID.
"""

import os
import sys
import logging

# Add the source directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agenthub_main', 'src'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_global_context_normalization():
    """Test that 'global' as context_id gets properly normalized."""
    try:
        # Import the necessary modules
        from fastmcp.task_management.application.services.unified_context_service import UnifiedContextService
        from fastmcp.task_management.application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory
        
        print("\n=== Testing Global Context Normalization ===\n")
        
        # Create a factory
        factory = UnifiedContextFacadeFactory()
        
        # Test user ID
        test_user_id = "test-user-123"
        
        # Create a facade for the test user
        facade = factory.create_facade(user_id=test_user_id)
        
        print(f"1. Testing with user_id: {test_user_id}")
        
        # Test 1: Create global context using "global" as context_id
        print("\n2. Creating global context with 'global' as context_id...")
        result = facade.create_context(
            level="global",
            context_id="global",  # Using "global" instead of UUID
            data={
                "test": "This is a test global context",
                "created_with": "global as context_id"
            }
        )
        
        if result.get("success"):
            print("   ✅ SUCCESS: Global context created with 'global' as context_id")
            print(f"   Actual UUID used: {result.get('context', {}).get('id', 'N/A')}")
        else:
            print(f"   ❌ FAILED: {result.get('error')}")
            return False
        
        # Test 2: Retrieve global context using "global" as context_id
        print("\n3. Retrieving global context with 'global' as context_id...")
        result = facade.get_context(
            level="global",
            context_id="global"  # Using "global" instead of UUID
        )
        
        if result.get("success"):
            print("   ✅ SUCCESS: Global context retrieved with 'global' as context_id")
            context_data = result.get("context", {})
            print(f"   Retrieved data: {context_data.get('global_settings', {}).get('test', 'N/A')}")
        else:
            print(f"   ❌ FAILED: {result.get('error')}")
            return False
        
        # Test 3: Update global context using "global" as context_id
        print("\n4. Updating global context with 'global' as context_id...")
        result = facade.update_context(
            level="global",
            context_id="global",  # Using "global" instead of UUID
            data={
                "updated": "This field was updated using 'global' as context_id"
            }
        )
        
        if result.get("success"):
            print("   ✅ SUCCESS: Global context updated with 'global' as context_id")
        else:
            print(f"   ❌ FAILED: {result.get('error')}")
            return False
        
        # Test 4: Resolve global context using "global" as context_id
        print("\n5. Resolving global context with 'global' as context_id...")
        result = facade.resolve_context(
            level="global",
            context_id="global"  # Using "global" instead of UUID
        )
        
        if result.get("success"):
            print("   ✅ SUCCESS: Global context resolved with 'global' as context_id")
            resolved_data = result.get("resolved_context", {})
            print(f"   Has 'updated' field: {'updated' in resolved_data.get('global_settings', {})}")
        else:
            print(f"   ❌ FAILED: {result.get('error')}")
            return False
        
        print("\n=== All Tests Passed! ===")
        print("\n✅ The fix successfully allows 'global' as a special context_id")
        print("   It gets automatically translated to the user's actual global context UUID")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_global_context_normalization()
    sys.exit(0 if success else 1)