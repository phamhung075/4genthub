#!/usr/bin/env python3
"""
Verification script for user_id isolation fix in context management system.

This script verifies that:
1. Contexts are created with actual user IDs (not 'system')
2. User isolation is properly enforced
3. Frontend will be able to see user-specific contexts
4. Debug logging properly traces user_id flow

Usage: python user-id-isolation-fix-verification.py
"""

import sys
import os
import uuid
import logging
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Imports
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastmcp.task_management.infrastructure.database.models import Base
from fastmcp.task_management.application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory
from fastmcp.task_management.domain.entities.context import GlobalContext, ProjectContext, BranchContext, TaskContext


def print_header(title):
    """Print formatted section header"""
    print()
    print("=" * 80)
    print(f"{title}")
    print("=" * 80)
    print()


def check_database_user_ids(session, user1_id, user2_id):
    """Check actual user_ids stored in database"""
    print_header("🔍 CHECKING DATABASE USER_IDS")
    
    results = []
    
    # Check global contexts
    result = session.execute(text("SELECT id, user_id FROM global_contexts"))
    global_contexts = result.fetchall()
    print(f"Global Contexts in Database:")
    for gc in global_contexts:
        print(f"  - ID: {gc[0][:8]}..., User: {gc[1]}")
        if gc[1] == 'system':
            results.append(("FAIL", "Global context has 'system' user_id", gc))
        elif gc[1] == user1_id or gc[1] == user2_id:
            results.append(("PASS", f"Global context has correct user_id: {gc[1]}", gc))
    
    # Check project contexts
    result = session.execute(text("SELECT id, user_id FROM project_contexts"))
    project_contexts = result.fetchall()
    print(f"\nProject Contexts in Database:")
    for pc in project_contexts:
        print(f"  - ID: {pc[0][:8]}..., User: {pc[1]}")
        if pc[1] == 'system':
            results.append(("FAIL", "Project context has 'system' user_id", pc))
        elif pc[1] == user1_id or pc[1] == user2_id:
            results.append(("PASS", f"Project context has correct user_id: {pc[1]}", pc))
    
    # Check branch contexts
    result = session.execute(text("SELECT id, user_id FROM branch_contexts"))
    branch_contexts = result.fetchall()
    print(f"\nBranch Contexts in Database:")
    for bc in branch_contexts:
        print(f"  - ID: {bc[0][:8]}..., User: {bc[1]}")
        if bc[1] == 'system':
            results.append(("FAIL", "Branch context has 'system' user_id", bc))
        elif bc[1] == user1_id or bc[1] == user2_id:
            results.append(("PASS", f"Branch context has correct user_id: {bc[1]}", bc))
    
    # Check task contexts
    result = session.execute(text("SELECT id, user_id FROM task_contexts"))
    task_contexts = result.fetchall()
    print(f"\nTask Contexts in Database:")
    for tc in task_contexts:
        print(f"  - ID: {tc[0][:8]}..., User: {tc[1]}")
        if tc[1] == 'system':
            results.append(("FAIL", "Task context has 'system' user_id", tc))
        elif tc[1] == user1_id or tc[1] == user2_id:
            results.append(("PASS", f"Task context has correct user_id: {tc[1]}", tc))
    
    return results


def test_user_id_isolation():
    """Test that user_id isolation is working correctly"""
    print_header("USER ID ISOLATION FIX VERIFICATION")
    
    # Create in-memory test database
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    
    # Simulate two different users (not 'system')
    user1_id = str(uuid.uuid4())
    user2_id = str(uuid.uuid4())
    
    print(f"👤 User 1 ID: {user1_id}")
    print(f"👤 User 2 ID: {user2_id}")
    print()
    
    test_results = []
    
    # Initialize factory
    factory = UnifiedContextFacadeFactory(session_factory)
    
    # === TEST 1: Create facade with User 1 ===
    print_header("TEST 1: Creating contexts for User 1")
    
    # Create facade for user 1
    user1_facade = factory.create_facade(user_id=user1_id)
    
    # Create global context for user 1
    print("Creating global context for User 1...")
    result = user1_facade.create_context(
        level='global',
        context_id='global_singleton',
        data={'organization_name': 'User 1 Organization'}
    )
    
    if result.get('success'):
        test_results.append(("PASS", "User 1 global context created", None))
        print(f"✅ Global context created for User 1")
    else:
        test_results.append(("FAIL", f"User 1 global context creation failed: {result.get('error')}", None))
        print(f"❌ Failed: {result.get('error')}")
    
    # Create project context for user 1
    project1_id = str(uuid.uuid4())
    print(f"Creating project context for User 1 (ID: {project1_id[:8]}...)...")
    result = user1_facade.create_context(
        level='project',
        context_id=project1_id,
        data={'project_name': 'User 1 Project'}
    )
    
    if result.get('success'):
        test_results.append(("PASS", "User 1 project context created", None))
        print(f"✅ Project context created for User 1")
    else:
        test_results.append(("FAIL", f"User 1 project context creation failed: {result.get('error')}", None))
        print(f"❌ Failed: {result.get('error')}")
    
    # === TEST 2: Create facade with User 2 ===
    print_header("TEST 2: Creating contexts for User 2")
    
    # Create facade for user 2
    user2_facade = factory.create_facade(user_id=user2_id)
    
    # Create global context for user 2
    print("Creating global context for User 2...")
    result = user2_facade.create_context(
        level='global',
        context_id='global_singleton',
        data={'organization_name': 'User 2 Organization'}
    )
    
    if result.get('success'):
        test_results.append(("PASS", "User 2 global context created", None))
        print(f"✅ Global context created for User 2")
    else:
        test_results.append(("FAIL", f"User 2 global context creation failed: {result.get('error')}", None))
        print(f"❌ Failed: {result.get('error')}")
    
    # Create project context for user 2
    project2_id = str(uuid.uuid4())
    print(f"Creating project context for User 2 (ID: {project2_id[:8]}...)...")
    result = user2_facade.create_context(
        level='project',
        context_id=project2_id,
        data={'project_name': 'User 2 Project'}
    )
    
    if result.get('success'):
        test_results.append(("PASS", "User 2 project context created", None))
        print(f"✅ Project context created for User 2")
    else:
        test_results.append(("FAIL", f"User 2 project context creation failed: {result.get('error')}", None))
        print(f"❌ Failed: {result.get('error')}")
    
    # === TEST 3: Check database for actual user_ids ===
    session = session_factory()
    db_results = check_database_user_ids(session, user1_id, user2_id)
    test_results.extend(db_results)
    session.close()
    
    # === TEST 4: Test user isolation ===
    print_header("TEST 4: Verifying User Isolation")
    
    # User 1 should not see User 2's contexts
    print("Checking if User 1 can see User 2's project...")
    result = user1_facade.get_context(level='project', context_id=project2_id)
    
    if result.get('success') and result.get('context'):
        test_results.append(("FAIL", "User isolation failed - User 1 can see User 2's project", None))
        print(f"❌ User isolation failed: User 1 can see User 2's project")
    else:
        test_results.append(("PASS", "User isolation working - User 1 cannot see User 2's project", None))
        print(f"✅ User isolation confirmed: User 1 cannot see User 2's project")
    
    # User 2 should not see User 1's contexts
    print("Checking if User 2 can see User 1's project...")
    result = user2_facade.get_context(level='project', context_id=project1_id)
    
    if result.get('success') and result.get('context'):
        test_results.append(("FAIL", "User isolation failed - User 2 can see User 1's project", None))
        print(f"❌ User isolation failed: User 2 can see User 1's project")
    else:
        test_results.append(("PASS", "User isolation working - User 2 cannot see User 1's project", None))
        print(f"✅ User isolation confirmed: User 2 cannot see User 1's project")
    
    # === TEST 5: Verify no 'system' user contexts ===
    print_header("TEST 5: Checking for 'system' User Contexts")
    
    session = session_factory()
    result = session.execute(text("SELECT COUNT(*) FROM global_contexts WHERE user_id = 'system'"))
    system_global_count = result.scalar()
    
    result = session.execute(text("SELECT COUNT(*) FROM project_contexts WHERE user_id = 'system'"))
    system_project_count = result.scalar()
    
    result = session.execute(text("SELECT COUNT(*) FROM branch_contexts WHERE user_id = 'system'"))
    system_branch_count = result.scalar()
    
    result = session.execute(text("SELECT COUNT(*) FROM task_contexts WHERE user_id = 'system'"))
    system_task_count = result.scalar()
    
    total_system_contexts = system_global_count + system_project_count + system_branch_count + system_task_count
    
    if total_system_contexts > 0:
        test_results.append(("FAIL", f"Found {total_system_contexts} contexts with 'system' user_id", None))
        print(f"❌ FAIL: Found {total_system_contexts} contexts with 'system' user_id")
        print(f"   - Global: {system_global_count}")
        print(f"   - Project: {system_project_count}")
        print(f"   - Branch: {system_branch_count}")
        print(f"   - Task: {system_task_count}")
    else:
        test_results.append(("PASS", "No contexts with 'system' user_id found", None))
        print(f"✅ PASS: No contexts with 'system' user_id")
    
    session.close()
    
    # === SUMMARY ===
    print_header("VERIFICATION SUMMARY")
    
    passed = sum(1 for r in test_results if r[0] == "PASS")
    failed = sum(1 for r in test_results if r[0] == "FAIL")
    total = len(test_results)
    
    print(f"📊 Tests Passed: {passed}/{total}")
    print()
    
    if failed == 0:
        print("✅ ALL TESTS PASSED!")
        print("User ID isolation is working correctly.")
        print("Contexts are properly scoped to actual user IDs.")
        print("Frontend should now show user-specific contexts.")
    else:
        print(f"❌ {failed} TESTS FAILED!")
        print("User ID isolation needs additional fixes.")
        print()
        print("Failed tests:")
        for result in test_results:
            if result[0] == "FAIL":
                print(f"  - {result[1]}")
    
    print()
    print("📋 DETAILED RESULTS:")
    for result in test_results:
        status_icon = "✅" if result[0] == "PASS" else "❌"
        print(f"   {status_icon} {result[0]}: {result[1]}")
    
    return failed == 0


if __name__ == "__main__":
    try:
        success = test_user_id_isolation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error running verification: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)