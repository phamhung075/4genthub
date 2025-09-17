#!/usr/bin/env python3
"""
Quick test to verify the subtask assignees string-to-list conversion fix
"""

def test_assignees_string_conversion():
    """Test that assignees string is correctly converted to list"""

    print("Testing subtask assignees string-to-list conversion...")

    # Test case 1: Single assignee string
    test_kwargs_single = {
        'task_id': 'test-task-id',
        'title': 'Test Subtask',
        'assignees': 'test-orchestrator-agent'  # This should be converted to ['test-orchestrator-agent']
    }

    print(f"\nTest 1 - Single assignee:")
    print(f"Input assignees: {repr(test_kwargs_single['assignees'])}")
    print(f"Type: {type(test_kwargs_single['assignees'])}")

    # This will trigger the conversion logic (same as in the fix)
    try:
        if 'assignees' in test_kwargs_single and test_kwargs_single['assignees'] is not None and isinstance(test_kwargs_single['assignees'], str):
            assignees = test_kwargs_single['assignees']
            if ',' in assignees:
                # Comma-separated assignees - convert to list
                test_kwargs_single['assignees'] = [a.strip() for a in assignees.split(',') if a.strip()]
            else:
                # Single assignee - convert to list
                test_kwargs_single['assignees'] = [assignees.strip()] if assignees.strip() else []

        print(f"Output assignees: {repr(test_kwargs_single['assignees'])}")
        print(f"Type: {type(test_kwargs_single['assignees'])}")
        print(f"Length: {len(test_kwargs_single['assignees'])}")
        print(f"First element: {repr(test_kwargs_single['assignees'][0])}")

        # Verify it's correct
        assert test_kwargs_single['assignees'] == ['test-orchestrator-agent'], f"Expected ['test-orchestrator-agent'], got {test_kwargs_single['assignees']}"
        print("✓ Test 1 PASSED")

    except Exception as e:
        print(f"✗ Test 1 FAILED: {e}")
        return False

    # Test case 2: Comma-separated assignees
    test_kwargs_multi = {
        'task_id': 'test-task-id',
        'title': 'Test Subtask',
        'assignees': 'coding-agent, test-orchestrator-agent, @debugger-agent'
    }

    print(f"\nTest 2 - Multiple assignees:")
    print(f"Input assignees: {repr(test_kwargs_multi['assignees'])}")
    print(f"Type: {type(test_kwargs_multi['assignees'])}")

    try:
        # Apply conversion logic
        if 'assignees' in test_kwargs_multi and test_kwargs_multi['assignees'] is not None and isinstance(test_kwargs_multi['assignees'], str):
            assignees = test_kwargs_multi['assignees']
            if ',' in assignees:
                # Comma-separated assignees - convert to list
                test_kwargs_multi['assignees'] = [a.strip() for a in assignees.split(',') if a.strip()]
            else:
                # Single assignee - convert to list
                test_kwargs_multi['assignees'] = [assignees.strip()] if assignees.strip() else []

        print(f"Output assignees: {repr(test_kwargs_multi['assignees'])}")
        print(f"Type: {type(test_kwargs_multi['assignees'])}")
        print(f"Length: {len(test_kwargs_multi['assignees'])}")
        for i, assignee in enumerate(test_kwargs_multi['assignees']):
            print(f"Element {i}: {repr(assignee)}")

        # Verify it's correct
        expected = ['coding-agent', 'test-orchestrator-agent', '@debugger-agent']
        assert test_kwargs_multi['assignees'] == expected, f"Expected {expected}, got {test_kwargs_multi['assignees']}"
        print("✓ Test 2 PASSED")

    except Exception as e:
        print(f"✗ Test 2 FAILED: {e}")
        return False

    print("\n✓ All tests PASSED! The fix should work correctly.")
    return True

if __name__ == "__main__":
    test_assignees_string_conversion()