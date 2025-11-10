#!/usr/bin/env python3
"""
Comprehensive Label Creation Test - Verify UTC Timestamp Fix

Tests all label scenarios to verify the fix for timestamp constraint violations.
"""

import os
import sys

sys.path.append(os.path.dirname(__file__) + '/..')

import uuid
from datetime import datetime

from fastmcp.task_management.infrastructure.database.database_config import get_session
from fastmcp.task_management.infrastructure.repositories.orm.task_repository import (
    ORMTaskRepository,
)


def test_label_creation():
    """Test all label creation scenarios"""

    test_results = []

    # Test configuration
    git_branch_id = "187670f5-0b5c-414d-8819-a9a1df8b2879"  # test-flow branch
    user_id = "test_user"

    test_cases = [
        {
            "name": "Single Label",
            "labels": "backend"
        },
        {
            "name": "Multiple Labels (comma-separated)",
            "labels": "backend,security,critical"
        },
        {
            "name": "Complex Labels (with hyphens)",
            "labels": "api-integration,frontend-ui,database-optimization"
        },
        {
            "name": "Mixed Case Labels",
            "labels": "API,Backend,Frontend,Testing"
        },
        {
            "name": "Labels with Numbers",
            "labels": "v1-api,backend-v2,test-phase-3"
        }
    ]

    print("\n" + "="*80)
    print("LABEL CREATION FIX VERIFICATION TEST")
    print("="*80)
    print(f"Test Branch: test-flow ({git_branch_id})")
    print(f"User ID: {user_id}")
    print(f"Total Test Cases: {len(test_cases)}")
    print("="*80 + "\n")

    session = get_session()
    repo = ORMTaskRepository(session=session, user_id=user_id)

    try:

        for idx, test_case in enumerate(test_cases, 1):
            print(f"\nTest Case #{idx}: {test_case['name']}")
            print(f"Labels: {test_case['labels']}")
            print("-" * 80)

            try:
                # Create task with labels
                task_id = str(uuid.uuid4())
                task_orm = repo.create_task(
                    task_id=task_id,
                    title=f"Test {test_case['name']} - {datetime.now().isoformat()}",
                    description=f"Testing label creation: {test_case['labels']}",
                    git_branch_id=git_branch_id,
                    labels=test_case['labels'],
                    assignees="test-orchestrator-agent",
                    priority="medium",
                    status="todo",
                    details="Automated test for label creation fix"
                )

                # Verify labels were created
                label_count = len(task_orm.labels)
                expected_count = len(test_case['labels'].split(','))

                # Verify timestamps
                all_have_timestamps = all(
                    label.created_at is not None and
                    label.updated_at is not None and
                    label.created_at.tzinfo is not None  # UTC aware
                    for label in task_orm.labels
                )

                if label_count == expected_count and all_have_timestamps:
                    result = "✅ PASS"
                    test_results.append(True)
                    print(f"Status: {result}")
                    print(f"  ✓ Created {label_count} labels (expected {expected_count})")
                    print("  ✓ All labels have UTC timestamps")
                    print(f"  ✓ Task ID: {task_id}")

                    # Show label details
                    for label in task_orm.labels:
                        print(f"    - {label.name}: created_at={label.created_at}, updated_at={label.updated_at}")
                else:
                    result = "⚠️ PARTIAL"
                    test_results.append(False)
                    print(f"Status: {result}")
                    print(f"  ! Created {label_count} labels (expected {expected_count})")
                    print(f"  ! Timestamp check: {all_have_timestamps}")

            except Exception as e:
                result = "❌ FAIL"
                test_results.append(False)
                print(f"Status: {result}")
                print(f"Error: {type(e).__name__}: {str(e)}")
                import traceback
                print(traceback.format_exc())

    finally:
        session.close()

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    total = len(test_results)
    passed = sum(test_results)
    failed = total - passed
    success_rate = (passed / total * 100) if total > 0 else 0

    print(f"Total Tests: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    print(f"Success Rate: {success_rate:.1f}%")
    print("="*80)

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Label creation fix is working correctly.")
        return 0
    else:
        print(f"\n⚠️ {failed} test(s) failed. Review errors above.")
        return 1

if __name__ == "__main__":
    exit_code = test_label_creation()
    sys.exit(exit_code)
