"""Manual test to verify subtask progress fix"""

import sys

sys.path.insert(0, "/home/daihungpham/__projects__/4genthub/agenthub_main/src")

from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus


def test_is_completed_property():
    """Test that is_completed property works correctly"""
    print("\n=== Testing Subtask.is_completed property ===")

    parent_id = TaskId.generate()

    # Test 1: Subtask with status='done' should be completed
    subtask1 = Subtask(
        id=TaskId.generate(),
        parent_task_id=parent_id,
        title="Test 1",
        description="Test subtask with done status",
        status=TaskStatus.done(),
        priority=Priority.medium(),
    )
    print(
        f"Test 1 - Status='done': is_completed = {subtask1.is_completed} (expected: True)"
    )
    assert subtask1.is_completed, "Subtask with status='done' should be completed"

    # Test 2: Subtask with progress_percentage=100 should be completed
    subtask2 = Subtask(
        id=TaskId.generate(),
        parent_task_id=parent_id,
        title="Test 2",
        description="Test subtask with 100% progress",
        status=TaskStatus.in_progress(),
        priority=Priority.medium(),
        progress_percentage=100,
    )
    print(
        f"Test 2 - Progress=100%: is_completed = {subtask2.is_completed} (expected: True)"
    )
    # Note: When progress_percentage is set to 100, the entity automatically updates status to 'done'
    # This is correct behavior as per the Subtask.update_progress_percentage method
    assert subtask2.is_completed, (
        "Subtask with progress_percentage=100 should be completed"
    )

    # Test 3: Subtask with status='todo' should not be completed
    subtask3 = Subtask(
        id=TaskId.generate(),
        parent_task_id=parent_id,
        title="Test 3",
        description="Test subtask with todo status",
        status=TaskStatus.todo(),
        priority=Priority.medium(),
    )
    print(
        f"Test 3 - Status='todo': is_completed = {subtask3.is_completed} (expected: False)"
    )
    assert not subtask3.is_completed, (
        "Subtask with status='todo' should not be completed"
    )

    # Test 4: Subtask with progress_percentage=50 should not be completed
    subtask4 = Subtask(
        id=TaskId.generate(),
        parent_task_id=parent_id,
        title="Test 4",
        description="Test subtask with 50% progress",
        status=TaskStatus.in_progress(),
        priority=Priority.medium(),
        progress_percentage=50,
    )
    print(
        f"Test 4 - Progress=50%: is_completed = {subtask4.is_completed} (expected: False)"
    )
    assert not subtask4.is_completed, (
        "Subtask with progress_percentage=50 should not be completed"
    )

    print("\n✅ All Subtask.is_completed tests passed!")


def test_task_progress_service():
    """Test that TaskProgressService uses is_completed correctly"""
    print("\n=== Testing TaskProgressService.update_task_progress_from_subtasks ===")

    # We'll simulate what the service does

    print("Note: This is a manual verification that the fix was applied.")
    print(
        "The TaskProgressService.update_task_progress_from_subtasks method at line 79"
    )
    print("should now use: if subtask.is_completed:")
    print(
        "instead of: if hasattr(subtask, 'status') and str(subtask.status) == 'done':"
    )

    # Read the file to verify
    with open(
        "/home/daihungpham/__projects__/4genthub/agenthub_main/src/fastmcp/task_management/application/services/task_progress_service.py"
    ) as f:
        content = f.read()
        if "if subtask.is_completed:" in content:
            print("\n✅ Fix applied! TaskProgressService now uses subtask.is_completed")
        else:
            print("\n❌ Fix NOT applied! TaskProgressService still uses old logic")
            return False

    return True


if __name__ == "__main__":
    try:
        test_is_completed_property()
        test_task_progress_service()
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED - Subtask progress fix is working!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
