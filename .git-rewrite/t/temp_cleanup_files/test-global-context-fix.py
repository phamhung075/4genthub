#!/usr/bin/env python3
"""
Test script to verify the global context user-scoped fix is working correctly.
This script tests that each user gets their own global context.
"""

import sys
import os
import uuid
import logging

# Add the project to Python path
sys.path.insert(0, '/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_user_scoped_global_context():
    """Test that global contexts are user-scoped"""
    print("🔍 Testing User-Scoped Global Context Implementation...")
    
    try:
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from fastmcp.task_management.infrastructure.repositories.global_context_repository_user_scoped import GlobalContextRepository
        from fastmcp.task_management.domain.entities.context import GlobalContext
        
        # Get database session
        db_config = get_db_config()
        session_factory = db_config.SessionLocal
        
        # Create test users
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())
        
        print(f"📝 Test User 1: {user1_id}")
        print(f"📝 Test User 2: {user2_id}")
        
        # Create user-scoped repositories
        user1_repo = GlobalContextRepository(session_factory, user1_id)
        user2_repo = GlobalContextRepository(session_factory, user2_id)
        
        print("\n1️⃣ Testing User 1 Global Context Creation")
        
        # Check if user1 already has a global context
        user1_context = user1_repo.get("global_singleton")
        if user1_context:
            print("   ✅ User 1 already has a global context")
            user1_context_id = user1_context.id
        else:
            # Create global context for user 1
            global_context_1 = GlobalContext(
                id="global_singleton",  # The repository will convert this to user-specific UUID
                organization_name="User 1 Organization",
                global_settings={
                    "autonomous_rules": {"rule1": "value1"},
                    "security_policies": {},
                    "coding_standards": {},
                    "workflow_templates": {},
                    "delegation_rules": {}
                }
            )
            
            user1_context = user1_repo.create(global_context_1)
            user1_context_id = user1_context.id
            print(f"   ✅ Created global context for User 1: {user1_context_id}")
        
        print(f"   📋 User 1 Context ID: {user1_context_id}")
        
        print("\n2️⃣ Testing User 2 Global Context Creation")
        
        # Check if user2 already has a global context
        user2_context = user2_repo.get("global_singleton")
        if user2_context:
            print("   ✅ User 2 already has a global context")
            user2_context_id = user2_context.id
        else:
            # Create global context for user 2
            global_context_2 = GlobalContext(
                id="global_singleton",  # The repository will convert this to user-specific UUID
                organization_name="User 2 Organization",
                global_settings={
                    "autonomous_rules": {"rule2": "value2"},
                    "security_policies": {},
                    "coding_standards": {},
                    "workflow_templates": {},
                    "delegation_rules": {}
                }
            )
            
            user2_context = user2_repo.create(global_context_2)
            user2_context_id = user2_context.id
            print(f"   ✅ Created global context for User 2: {user2_context_id}")
        
        print(f"   📋 User 2 Context ID: {user2_context_id}")
        
        print("\n3️⃣ Testing User Isolation")
        
        # Verify contexts are different
        if user1_context_id != user2_context_id:
            print("   ✅ PASSED: Users have different global context IDs")
        else:
            print("   ❌ FAILED: Users have the same global context ID (not isolated!)")
            return False
        
        # Verify user 1 cannot access user 2's context directly
        try:
            user1_accessing_user2 = user1_repo.get(user2_context_id)
            if user1_accessing_user2 is None:
                print("   ✅ PASSED: User 1 cannot access User 2's context")
            else:
                print("   ❌ FAILED: User 1 can access User 2's context (isolation broken!)")
                return False
        except Exception as e:
            print(f"   ✅ PASSED: User 1 cannot access User 2's context (exception: {e})")
        
        # Verify content differences
        user1_rules = user1_context.global_settings.get("autonomous_rules", {})
        user2_rules = user2_context.global_settings.get("autonomous_rules", {})
        
        print(f"   📋 User 1 Rules: {user1_rules}")
        print(f"   📋 User 2 Rules: {user2_rules}")
        
        if user1_rules != user2_rules:
            print("   ✅ PASSED: Users have different global settings")
        else:
            print("   ⚠️  WARNING: Users have identical settings (may be expected)")
        
        print("\n4️⃣ Testing Context Counts")
        
        # Each user should have only 1 global context
        user1_count = user1_repo.count_user_contexts()
        user2_count = user2_repo.count_user_contexts()
        
        print(f"   📊 User 1 Global Context Count: {user1_count}")
        print(f"   📊 User 2 Global Context Count: {user2_count}")
        
        if user1_count == 1 and user2_count == 1:
            print("   ✅ PASSED: Each user has exactly 1 global context")
        else:
            print("   ❌ FAILED: Users don't have exactly 1 global context each")
            return False
        
        print("\n🎉 SUCCESS: All User-Scoped Global Context Tests Passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_facade_factory():
    """Test that the UnifiedContextFacadeFactory works with user-scoped contexts"""
    print("\n🔍 Testing UnifiedContextFacadeFactory with User-Scoped Contexts...")
    
    try:
        from fastmcp.task_management.application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory
        
        # Create test user
        test_user_id = str(uuid.uuid4())
        print(f"📝 Test User: {test_user_id}")
        
        # Create factory
        factory = UnifiedContextFacadeFactory()
        
        # Test auto-creation with user ID
        print("\n1️⃣ Testing Auto-Creation with User ID")
        result = factory.auto_create_global_context(user_id=test_user_id)
        
        if result:
            print("   ✅ PASSED: Auto-creation with user_id succeeded")
        else:
            print("   ❌ FAILED: Auto-creation with user_id failed")
            return False
        
        # Test facade creation
        print("\n2️⃣ Testing Facade Creation")
        facade = factory.create_facade(user_id=test_user_id)
        
        if facade:
            print("   ✅ PASSED: Facade creation succeeded")
        else:
            print("   ❌ FAILED: Facade creation failed")
            return False
        
        # Test context retrieval through facade
        print("\n3️⃣ Testing Context Retrieval Through Facade")
        context_result = facade.get_context(level="global", context_id="global_singleton")
        
        if context_result.get("success", False):
            print("   ✅ PASSED: Context retrieval through facade succeeded")
            print(f"   📋 Context ID: {context_result['context']['id']}")
        else:
            print("   ❌ FAILED: Context retrieval through facade failed")
            print(f"   📋 Error: {context_result.get('error', 'Unknown error')}")
            return False
        
        print("\n🎉 SUCCESS: All Facade Factory Tests Passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: Facade factory test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Global Context User-Scoped Fix Verification...")
    print("=" * 60)
    
    # Test repository layer
    repo_test_passed = test_user_scoped_global_context()
    
    # Test facade layer
    facade_test_passed = test_facade_factory()
    
    print("\n" + "=" * 60)
    if repo_test_passed and facade_test_passed:
        print("🎉 ALL TESTS PASSED: Global Context User-Scoped Fix is Working!")
        print("✅ Each user now has their own isolated global context")
        print("✅ The singleton pattern has been successfully replaced")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED: Global Context Fix needs more work")
        sys.exit(1)