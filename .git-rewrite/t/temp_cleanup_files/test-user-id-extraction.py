#!/usr/bin/env python3
"""
Test User ID Extraction from Context Objects
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'dhafnck_mcp_main/src'))

# Mock the BackwardCompatUserContext object to simulate the issue
class MockBackwardCompatUserContext:
    def __init__(self, user_id: str):
        self.user_id = user_id
    
    def __str__(self):
        return f"<fastmcp.auth.middleware.request_context_middleware.get_current_user_context.<locals>.BackwardCompatUserContext object at {hex(id(self))}>"

# Import the extraction function we just created
from fastmcp.task_management.interface.controllers.auth_helper import _extract_user_id_from_context_object

def test_user_id_extraction():
    print("🚀 Testing User ID Extraction from Context Objects...")
    print("="*60)
    
    # Test 1: String input (should pass through)
    print("\n1️⃣ Testing String Input")
    test_user_id = "test-user-123"
    result = _extract_user_id_from_context_object(test_user_id)
    print(f"   Input: {test_user_id}")
    print(f"   Output: {result}")
    assert result == test_user_id, f"Expected {test_user_id}, got {result}"
    print("   ✅ PASSED")
    
    # Test 2: Mock BackwardCompatUserContext object
    print("\n2️⃣ Testing BackwardCompatUserContext Object")
    mock_context = MockBackwardCompatUserContext("user-456")
    result = _extract_user_id_from_context_object(mock_context)
    print(f"   Input: {mock_context} (user_id = {mock_context.user_id})")
    print(f"   Output: {result}")
    assert result == "user-456", f"Expected 'user-456', got {result}"
    print("   ✅ PASSED")
    
    # Test 3: Dict-like object
    print("\n3️⃣ Testing Dict-like Object")
    dict_context = {"user_id": "user-789", "other_data": "ignored"}
    result = _extract_user_id_from_context_object(dict_context)
    print(f"   Input: {dict_context}")
    print(f"   Output: {result}")
    assert result == "user-789", f"Expected 'user-789', got {result}"
    print("   ✅ PASSED")
    
    # Test 4: None input
    print("\n4️⃣ Testing None Input")
    result = _extract_user_id_from_context_object(None)
    print(f"   Input: None")
    print(f"   Output: {result}")
    assert result is None, f"Expected None, got {result}"
    print("   ✅ PASSED")
    
    # Test 5: Object with 'id' attribute (fallback)
    print("\n5️⃣ Testing Object with 'id' Attribute")
    class MockObject:
        def __init__(self, id_val):
            self.id = id_val
    
    mock_obj = MockObject("user-999")
    result = _extract_user_id_from_context_object(mock_obj)
    print(f"   Input: MockObject(id={mock_obj.id})")
    print(f"   Output: {result}")
    assert result == "user-999", f"Expected 'user-999', got {result}"
    print("   ✅ PASSED")
    
    print("\n" + "="*60)
    print("🎉 ALL TESTS PASSED! User ID extraction function works correctly.")
    print("="*60)

if __name__ == "__main__":
    test_user_id_extraction()