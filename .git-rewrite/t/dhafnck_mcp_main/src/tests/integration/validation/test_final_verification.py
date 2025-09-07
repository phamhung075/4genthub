#!/usr/bin/env python3
"""
Final Verification Test for MCP Parameter Validation Fix

This test demonstrates that the exact failing cases mentioned in the issue
now work correctly after implementing the parameter validation fix.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from fastmcp.task_management.interface.utils.parameter_validation_fix import validate_parameters
from fastmcp.task_management.interface.utils.mcp_parameter_validator import validate_mcp_parameters


def test_original_failing_cases():
    """Test the exact failing cases mentioned in the GitHub issue"""
    
    print("🧪 Testing Original Failing Cases from GitHub Issue")
    print("=" * 60)
    
    # These are the EXACT cases that were failing before the fix
    failing_cases = [
        {
            "name": "limit as string '3' in search",
            "params": {"action": "search", "query": "test", "limit": "3"},
            "original_error": "Input validation error: '3' is not valid under any of the given schemas"
        },
        {
            "name": "limit as string '5' in search", 
            "params": {"action": "search", "query": "test", "limit": "5"},
            "original_error": "Input validation error: '5' is not valid under any of the given schemas"
        },
        {
            "name": "progress_percentage as string in update",
            "params": {"action": "update", "task_id": "test", "progress_percentage": "50"},
            "original_error": "Input validation error: progress_percentage string not accepted"
        },
        {
            "name": "timeout as string in command execution",
            "params": {"action": "execute", "command": "test", "timeout": "30"},
            "original_error": "Input validation error: timeout string not accepted"
        },
        {
            "name": "include_context as string 'true'",
            "params": {"action": "get", "task_id": "test", "include_context": "true"},
            "original_error": "Input validation error: boolean string not accepted"
        }
    ]
    
    all_passed = True
    
    for i, case in enumerate(failing_cases, 1):
        print(f"\n{i}. Testing: {case['name']}")
        print(f"   Original Error: {case['original_error']}")
        print(f"   Parameters: {case['params']}")
        
        try:
            # Test with our parameter validation fix
            result = validate_parameters(case["params"]["action"], case["params"])
            
            if result["success"]:
                coerced_params = result["coerced_params"]
                print(f"   ✅ FIXED: {coerced_params}")
                
                # Verify specific type coercions
                if "limit" in case["params"]:
                    limit_value = coerced_params["limit"]
                    assert isinstance(limit_value, int), f"Expected int, got {type(limit_value)}"
                    print(f"      → limit: '{case['params']['limit']}' → {limit_value} (int)")
                
                if "progress_percentage" in case["params"]:
                    progress_value = coerced_params["progress_percentage"]
                    assert isinstance(progress_value, int), f"Expected int, got {type(progress_value)}"
                    print(f"      → progress_percentage: '{case['params']['progress_percentage']}' → {progress_value} (int)")
                
                if "timeout" in case["params"]:
                    timeout_value = coerced_params["timeout"]
                    assert isinstance(timeout_value, int), f"Expected int, got {type(timeout_value)}"
                    print(f"      → timeout: '{case['params']['timeout']}' → {timeout_value} (int)")
                
                if "include_context" in case["params"]:
                    context_value = coerced_params["include_context"]
                    assert isinstance(context_value, bool), f"Expected bool, got {type(context_value)}"
                    print(f"      → include_context: '{case['params']['include_context']}' → {context_value} (bool)")
                    
            else:
                print(f"   ❌ STILL FAILING: {result['error']}")
                all_passed = False
                
        except Exception as e:
            print(f"   ❌ EXCEPTION: {e}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 SUCCESS: All original failing cases now PASS!")
        print("✅ The MCP parameter validation fix is working correctly!")
    else:
        print("❌ FAILURE: Some cases are still failing")
        
    assert all_passed, "Some original failing cases are still failing"


def test_edge_cases():
    """Test additional edge cases to ensure robustness"""
    
    print("\n🔬 Testing Edge Cases")
    print("=" * 30)
    
    edge_cases = [
        {"params": {"limit": "0"}, "expected_limit": 0},
        {"params": {"limit": "100"}, "expected_limit": 100},
        {"params": {"progress_percentage": "0"}, "expected_progress": 0},
        {"params": {"progress_percentage": "100"}, "expected_progress": 100},
        {"params": {"include_context": "1"}, "expected_context": True},
        {"params": {"include_context": "0"}, "expected_context": False},
        {"params": {"force": "yes"}, "expected_force": True},
        {"params": {"force": "no"}, "expected_force": False},
    ]
    
    for case in edge_cases:
        try:
            result = validate_parameters("test", case["params"])
            assert result["success"], f"Validation failed for {case['params']}"
            
            coerced_params = result["coerced_params"]
            
            if "expected_limit" in case:
                assert coerced_params["limit"] == case["expected_limit"]
                assert isinstance(coerced_params["limit"], int)
                
            if "expected_progress" in case:
                assert coerced_params["progress_percentage"] == case["expected_progress"]
                assert isinstance(coerced_params["progress_percentage"], int)
                
            if "expected_context" in case:
                assert coerced_params["include_context"] == case["expected_context"]
                assert isinstance(coerced_params["include_context"], bool)
                
            if "expected_force" in case:
                assert coerced_params["force"] == case["expected_force"]
                assert isinstance(coerced_params["force"], bool)
            
            print(f"✅ Edge case passed: {case['params']} → {coerced_params}")
            
        except Exception as e:
            print(f"❌ Edge case failed: {case['params']} - {e}")
            assert False, f"Edge case failed: {case['params']} - {e}"
    
    print("✅ All edge cases passed!")
    assert True


def test_mixed_parameter_validation():
    """Test complex scenarios with multiple parameter types"""
    
    print("\n🔄 Testing Mixed Parameter Scenarios")
    print("=" * 40)
    
    mixed_scenarios = [
        {
            "name": "Search with multiple types",
            "params": {
                "action": "search",
                "query": "authentication",
                "limit": "10",
                "include_context": "true",
                "force": "0"
            },
            "expected": {
                "query": ("authentication", str),
                "limit": (10, int),
                "include_context": (True, bool),
                "force": (False, bool)
            }
        },
        {
            "name": "Update with progress and flags",
            "params": {
                "action": "update", 
                "task_id": "test-123",
                "progress_percentage": "75",
                "include_context": "false",
                "force": "yes"
            },
            "expected": {
                "task_id": ("test-123", str),
                "progress_percentage": (75, int),
                "include_context": (False, bool),
                "force": (True, bool)
            }
        }
    ]
    
    for scenario in mixed_scenarios:
        print(f"\nTesting: {scenario['name']}")
        print(f"Input: {scenario['params']}")
        
        try:
            result = validate_parameters(scenario["params"]["action"], scenario["params"])
            assert result["success"], f"Validation failed: {result.get('error')}"
            
            coerced_params = result["coerced_params"]
            print(f"Output: {coerced_params}")
            
            # Verify each expected parameter
            for param_name, (expected_value, expected_type) in scenario["expected"].items():
                actual_value = coerced_params[param_name]
                assert actual_value == expected_value, f"Expected {param_name}={expected_value}, got {actual_value}"
                assert isinstance(actual_value, expected_type), f"Expected {param_name} to be {expected_type}, got {type(actual_value)}"
            
            print(f"✅ {scenario['name']}: All parameters correctly validated and coerced")
            
        except Exception as e:
            print(f"❌ {scenario['name']}: Failed - {e}")
            assert False, f"{scenario['name']}: Failed - {e}"
    
    print("✅ All mixed parameter scenarios passed!")
    assert True


def main():
    """Run all verification tests"""
    
    print("🚀 MCP Parameter Validation Fix - Final Verification")
    print("=" * 70)
    print("This test verifies that the original GitHub issue is completely resolved.")
    print()
    
    # Test 1: Original failing cases
    test1_passed = test_original_failing_cases()
    
    # Test 2: Edge cases
    test2_passed = test_edge_cases()
    
    # Test 3: Mixed parameter scenarios
    test3_passed = test_mixed_parameter_validation()
    
    # Overall result
    print("\n" + "=" * 70)
    print("📊 FINAL VERIFICATION RESULTS")
    print("=" * 70)
    
    if test1_passed and test2_passed and test3_passed:
        print("🎉 SUCCESS: MCP Parameter Validation Fix is COMPLETE!")
        print("✅ All original failing cases now work correctly")
        print("✅ All edge cases handled properly") 
        print("✅ Mixed parameter scenarios working")
        print()
        print("🚀 The fix is ready for production deployment!")
        return True
    else:
        print("❌ FAILURE: Some tests are still failing")
        print("🔧 Additional work needed before deployment")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)