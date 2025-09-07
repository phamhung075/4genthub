#!/usr/bin/env python3
"""
Test script to verify the UUID iteration fix.
This tests the normalize_assigned_trees methods to ensure they handle UUID objects correctly.
"""

import uuid
import sys
import os

# Add the path to the agent repository for testing
sys.path.append('/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src')

# Mock the database session to avoid database dependencies
class MockSession:
    def __init__(self):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass

# Mock BaseORMRepository to avoid database dependencies  
class MockBaseORMRepository:
    def __init__(self, *args, **kwargs):
        pass
    def get_db_session(self):
        return MockSession()

# Mock BaseUserScopedRepository to avoid dependencies
class MockBaseUserScopedRepository:
    def __init__(self, *args, **kwargs):
        pass

# Patch the imports
sys.modules['fastmcp.task_management.infrastructure.repositories.base_orm_repository'] = type(sys)('mock')
sys.modules['fastmcp.task_management.infrastructure.repositories.base_orm_repository'].BaseORMRepository = MockBaseORMRepository
sys.modules['fastmcp.task_management.infrastructure.repositories.base_user_scoped_repository'] = type(sys)('mock')  
sys.modules['fastmcp.task_management.infrastructure.repositories.base_user_scoped_repository'].BaseUserScopedRepository = MockBaseUserScopedRepository
sys.modules['fastmcp.task_management.infrastructure.database.models'] = type(sys)('mock')
sys.modules['fastmcp.task_management.infrastructure.database.models'].Agent = object
sys.modules['fastmcp.task_management.domain.entities.agent_entity'] = type(sys)('mock')

# Import our repository class
try:
    from fastmcp.task_management.infrastructure.repositories.orm.agent_repository import ORMAgentRepository
except Exception as e:
    print(f"Error importing ORMAgentRepository: {e}")
    sys.exit(1)

def test_normalize_assigned_trees_to_set():
    """Test the normalize_assigned_trees_to_set method with different input types."""
    print("Testing _normalize_assigned_trees_to_set...")
    
    # Create a repository instance
    repo = ORMAgentRepository()
    
    # Test case 1: Single string UUID
    test_uuid_str = "44d015ac-a84c-4702-8bff-254a8e3d0328"
    result = repo._normalize_assigned_trees_to_set(test_uuid_str)
    assert result == {test_uuid_str}, f"Expected {{{test_uuid_str}}}, got {result}"
    print("✓ Single string UUID test passed")
    
    # Test case 2: Single UUID object (this was causing the original error)
    test_uuid_obj = uuid.UUID(test_uuid_str)
    result = repo._normalize_assigned_trees_to_set(test_uuid_obj)
    assert result == {test_uuid_str}, f"Expected {{{test_uuid_str}}}, got {result}"
    print("✓ Single UUID object test passed")
    
    # Test case 3: List of strings
    test_uuid_list = [test_uuid_str, "11111111-1111-1111-1111-111111111111"]
    result = repo._normalize_assigned_trees_to_set(test_uuid_list)
    expected = set(test_uuid_list)
    assert result == expected, f"Expected {expected}, got {result}"
    print("✓ List of strings test passed")
    
    # Test case 4: List with mixed types (string and UUID objects)
    test_mixed_list = [test_uuid_str, uuid.UUID("11111111-1111-1111-1111-111111111111")]
    result = repo._normalize_assigned_trees_to_set(test_mixed_list)
    expected = {test_uuid_str, "11111111-1111-1111-1111-111111111111"}
    assert result == expected, f"Expected {expected}, got {result}"
    print("✓ Mixed list test passed")
    
    # Test case 5: Empty list
    result = repo._normalize_assigned_trees_to_set([])
    assert result == set(), f"Expected empty set, got {result}"
    print("✓ Empty list test passed")
    
    # Test case 6: None/other types
    result = repo._normalize_assigned_trees_to_set(None)
    assert result == set(), f"Expected empty set, got {result}"
    print("✓ None test passed")

def test_normalize_assigned_trees_to_list():
    """Test the normalize_assigned_trees_to_list method with different input types."""
    print("\nTesting _normalize_assigned_trees_to_list...")
    
    # Create a repository instance
    repo = ORMAgentRepository()
    
    # Test case 1: Single string UUID
    test_uuid_str = "44d015ac-a84c-4702-8bff-254a8e3d0328"
    result = repo._normalize_assigned_trees_to_list(test_uuid_str)
    assert result == [test_uuid_str], f"Expected [{test_uuid_str}], got {result}"
    print("✓ Single string UUID test passed")
    
    # Test case 2: Single UUID object (this was causing the original error)
    test_uuid_obj = uuid.UUID(test_uuid_str)
    result = repo._normalize_assigned_trees_to_list(test_uuid_obj)
    assert result == [test_uuid_str], f"Expected [{test_uuid_str}], got {result}"
    print("✓ Single UUID object test passed")
    
    # Test case 3: List of strings
    test_uuid_list = [test_uuid_str, "11111111-1111-1111-1111-111111111111"]
    result = repo._normalize_assigned_trees_to_list(test_uuid_list)
    assert result == test_uuid_list, f"Expected {test_uuid_list}, got {result}"
    print("✓ List of strings test passed")
    
    # Test case 4: List with mixed types (string and UUID objects)
    test_mixed_list = [test_uuid_str, uuid.UUID("11111111-1111-1111-1111-111111111111")]
    result = repo._normalize_assigned_trees_to_list(test_mixed_list)
    expected = [test_uuid_str, "11111111-1111-1111-1111-111111111111"]
    assert result == expected, f"Expected {expected}, got {result}"
    print("✓ Mixed list test passed")

def test_in_operation():
    """Test that the 'in' operation works correctly with the results."""
    print("\nTesting 'in' operation (the source of the original bug)...")
    
    repo = ORMAgentRepository()
    test_uuid_str = "44d015ac-a84c-4702-8bff-254a8e3d0328"
    
    # Simulate the original problematic scenario where assigned_trees_raw is a UUID object
    test_uuid_obj = uuid.UUID(test_uuid_str)
    
    # This is what was failing before the fix:
    # if git_branch_id in assigned_trees_raw:  # This would fail with "argument of type 'UUID' is not iterable"
    
    # With our fix, this should work:
    normalized = repo._normalize_assigned_trees_to_set(test_uuid_obj)
    
    # Test the 'in' operation
    assert test_uuid_str in normalized, f"UUID string should be found in normalized set"
    assert "other-uuid" not in normalized, f"Other UUID should not be found in normalized set"
    
    print("✓ 'in' operation test passed - original bug is fixed!")

if __name__ == "__main__":
    print("UUID Iteration Fix Test")
    print("=" * 50)
    
    try:
        test_normalize_assigned_trees_to_set()
        test_normalize_assigned_trees_to_list()
        test_in_operation()
        
        print("\n" + "=" * 50)
        print("🎉 All tests passed! The UUID iteration fix is working correctly.")
        print("✅ Fixed: 'argument of type 'UUID' is not iterable' error")
        print("✅ The agent assignment should now work without errors.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)