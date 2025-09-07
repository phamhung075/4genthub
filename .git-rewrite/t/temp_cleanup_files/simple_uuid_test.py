#!/usr/bin/env python3
"""
Simple test to demonstrate the UUID iteration fix.
This shows the exact issue and how our fix solves it.
"""

import uuid

def normalize_assigned_trees_to_set(assigned_trees_raw):
    """
    The fix for the UUID iteration error.
    This is the logic I added to handle UUID objects properly.
    """
    if isinstance(assigned_trees_raw, str):
        # Single UUID stored as string
        return {assigned_trees_raw}
    elif isinstance(assigned_trees_raw, uuid.UUID):
        # Single UUID object (convert to string) - THIS IS THE FIX
        return {str(assigned_trees_raw)}
    elif hasattr(assigned_trees_raw, '__iter__') and not isinstance(assigned_trees_raw, str):
        # List or other iterable (but not string or UUID)
        try:
            # Handle mixed types in the iterable (strings and UUID objects)
            result = set()
            for item in assigned_trees_raw:
                if isinstance(item, uuid.UUID):
                    result.add(str(item))
                elif isinstance(item, str):
                    result.add(item)
                else:
                    # Convert other types to string
                    result.add(str(item))
            return result
        except Exception as e:
            print(f"Error converting {assigned_trees_raw} to set: {e}")
            return set()
    else:
        # Fallback to empty set
        return set()

def demonstrate_original_bug():
    """Demonstrate the original bug that caused 'argument of type 'UUID' is not iterable'."""
    print("Demonstrating the original bug...")
    
    # This simulates what was happening in the database:
    # The assigned_trees field contained a UUID object instead of a string
    test_uuid_obj = uuid.UUID("44d015ac-a84c-4702-8bff-254a8e3d0328")
    git_branch_id = "44d015ac-a84c-4702-8bff-254a8e3d0328"
    
    print(f"assigned_trees_raw type: {type(test_uuid_obj)}")
    print(f"assigned_trees_raw value: {test_uuid_obj}")
    
    # The original code was doing something like this:
    # if git_branch_id in test_uuid_obj:  # This causes the error!
    
    try:
        # This will fail with "argument of type 'UUID' is not iterable"
        result = git_branch_id in test_uuid_obj
        print(f"❌ This shouldn't work: {result}")
    except TypeError as e:
        print(f"✅ Expected error (the original bug): {e}")
    
    print("\nNow testing our fix:")
    
    # Our fix normalizes the UUID object to a set of strings
    normalized = normalize_assigned_trees_to_set(test_uuid_obj)
    print(f"Normalized result: {normalized}")
    print(f"Normalized type: {type(normalized)}")
    
    # Now the 'in' operation works correctly
    is_assigned = git_branch_id in normalized
    print(f"✅ Fixed: git_branch_id in normalized = {is_assigned}")

def test_all_cases():
    """Test all the different cases our fix handles."""
    print("\n" + "="*50)
    print("Testing all cases:")
    
    test_cases = [
        ("String UUID", "44d015ac-a84c-4702-8bff-254a8e3d0328"),
        ("UUID object", uuid.UUID("44d015ac-a84c-4702-8bff-254a8e3d0328")),
        ("List of strings", ["44d015ac-a84c-4702-8bff-254a8e3d0328", "11111111-1111-1111-1111-111111111111"]),
        ("Mixed list", ["44d015ac-a84c-4702-8bff-254a8e3d0328", uuid.UUID("11111111-1111-1111-1111-111111111111")]),
        ("Empty list", []),
        ("None", None),
    ]
    
    for case_name, test_input in test_cases:
        try:
            result = normalize_assigned_trees_to_set(test_input)
            print(f"✅ {case_name}: {result}")
            
            # Test the 'in' operation (the source of the original bug)
            test_uuid = "44d015ac-a84c-4702-8bff-254a8e3d0328"
            in_result = test_uuid in result
            print(f"   UUID {test_uuid} in result: {in_result}")
            
        except Exception as e:
            print(f"❌ {case_name} failed: {e}")

if __name__ == "__main__":
    print("UUID Iteration Bug Fix Demonstration")
    print("="*50)
    
    demonstrate_original_bug()
    test_all_cases()
    
    print("\n" + "="*50) 
    print("🎉 Fix Summary:")
    print("✅ Added handling for uuid.UUID objects in assigned_trees")
    print("✅ Convert UUID objects to strings before set operations")
    print("✅ Handle mixed lists with both strings and UUID objects")
    print("✅ The 'argument of type 'UUID' is not iterable' error is now fixed")
    print("\nThe agent assignment should now work without errors!")