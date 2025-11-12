#!/usr/bin/env python3
"""
Comprehensive Label Integration Tests

This test suite provides comprehensive integration testing for label functionality.
Based on successful manual test pattern, designed to work immediately without complex fixtures.

Test Coverage:
- Label creation with UTC timestamps
- Multiple label scenarios
- Label-task associations
- Label queries and filtering
- Error handling and validation

Success Criteria:
- 15+ test cases
- >90% code coverage for label operations
- All tests passing
- UTC timestamp validation
"""

import os
import sys

sys.path.append(os.path.dirname(__file__) + "/../..")

import uuid
from datetime import UTC, datetime

from fastmcp.task_management.infrastructure.database.database_adapter import (
    DatabaseAdapter,
)
from fastmcp.task_management.infrastructure.database.database_config import get_session
from fastmcp.task_management.infrastructure.repositories.orm.label_repository import (
    ORMLabelRepository,
)
from fastmcp.task_management.infrastructure.repositories.orm.task_repository import (
    ORMTaskRepository,
)


class LabelIntegrationTestSuite:
    """Comprehensive label integration test suite"""

    def __init__(self):
        self.session = get_session()
        self.user_id = "test_user"

        # Create a real git branch in the database for testing
        from fastmcp.task_management.infrastructure.database.models import (
            Project,
            ProjectGitBranch,
        )

        # Ensure test project and branch exist
        try:
            project = (
                self.session.query(Project)
                .filter(Project.id == "default_project")
                .first()
            )
            if project:
                branch = (
                    self.session.query(ProjectGitBranch)
                    .filter(ProjectGitBranch.project_id == "default_project")
                    .first()
                )
                if branch:
                    self.git_branch_id = branch.id
                else:
                    # Create test branch
                    self.git_branch_id = str(uuid.uuid4())
                    test_branch = ProjectGitBranch(
                        id=self.git_branch_id,
                        project_id="default_project",
                        name="test-branch",
                        description="Test branch for label tests",
                        user_id=self.user_id,
                        created_at=datetime.now(UTC),
                        updated_at=datetime.now(UTC),
                    )
                    self.session.add(test_branch)
                    self.session.commit()
            else:
                # Fallback
                self.git_branch_id = "ea350cd3-8ebc-4cf2-ac57-19282d8c5f13"  # From logs
        except Exception:
            self.git_branch_id = "ea350cd3-8ebc-4cf2-ac57-19282d8c5f13"  # Fallback from initialization logs

        self.task_repo = ORMTaskRepository(session=self.session, user_id=self.user_id)

        # Initialize label repository with DatabaseAdapter
        db_adapter = DatabaseAdapter(self.session.bind)
        self.label_repo = ORMLabelRepository(db_adapter)
        self.label_repo.user_id = self.user_id

        self.test_results = []

    def run_test(self, test_name, test_func):
        """Run a single test and track result"""
        print(f"\n{'=' * 80}")
        print(f"Test: {test_name}")
        print("=" * 80)

        try:
            test_func()
            print(f"✅ PASS: {test_name}")
            self.test_results.append({"name": test_name, "result": "PASS"})
            return True
        except AssertionError as e:
            print(f"❌ FAIL: {test_name}")
            print(f"AssertionError: {str(e)}")
            self.test_results.append(
                {"name": test_name, "result": "FAIL", "error": str(e)}
            )
            return False
        except Exception as e:
            print(f"❌ ERROR: {test_name}")
            print(f"{type(e).__name__}: {str(e)}")
            import traceback

            print(traceback.format_exc())
            self.test_results.append(
                {"name": test_name, "result": "ERROR", "error": str(e)}
            )
            return False

    # ========================================================================
    # Label Creation Tests
    # ========================================================================

    def test_create_single_label(self):
        """Test creating a single label with UTC timestamp"""
        label = self.label_repo.create_label(
            name="test-backend", color="#0066cc", description="Backend tasks"
        )

        assert label is not None, "Label should not be None"
        assert label.name == "test-backend", "Label name mismatch"
        assert label.created_at is not None, "created_at should not be None"
        assert label.updated_at is not None, "updated_at should not be None"
        assert label.created_at.tzinfo == UTC, "created_at must be UTC"
        assert label.updated_at.tzinfo == UTC, "updated_at must be UTC"
        print(f"  ✓ Created label: {label.name}")
        print("  ✓ UTC timestamps verified")

    def test_create_multiple_labels(self):
        """Test creating multiple labels"""
        labels_to_create = ["ml-api", "ml-frontend", "ml-database"]
        created_labels = []

        for name in labels_to_create:
            label = self.label_repo.create_label(name=name)
            created_labels.append(label)

        assert len(created_labels) == 3, "Should create 3 labels"
        for label in created_labels:
            assert (
                label.created_at.tzinfo == UTC
            ), f"{label.name} must have UTC timestamp"
        print(f"  ✓ Created {len(created_labels)} labels with UTC timestamps")

    def test_create_label_with_complex_name(self):
        """Test labels with hyphens and numbers"""
        complex_names = [
            "api-v2-integration",
            "frontend-ui-redesign",
            "db-migration-phase-3",
        ]

        for name in complex_names:
            label = self.label_repo.create_label(name=name)
            assert label.name == name, f"Label name should be {name}"
            assert "-" in label.name, "Hyphen should be preserved"

        print("  ✓ Complex label names handled correctly")

    def test_label_timestamp_precision(self):
        """Test that timestamps are precise and recent"""
        before_create = datetime.now(UTC)
        label = self.label_repo.create_label(name="timestamp-test")
        after_create = datetime.now(UTC)

        assert label.created_at >= before_create, "Timestamp should be after test start"
        assert label.created_at <= after_create, "Timestamp should be before test end"
        assert (
            after_create - label.created_at
        ).total_seconds() < 5, "Timestamp should be very recent"
        print("  ✓ Timestamp precision verified")

    # ========================================================================
    # Label-Task Association Tests
    # ========================================================================

    def test_assign_label_to_task(self):
        """Test assigning a label to a task"""
        # Create task
        task_id = str(uuid.uuid4())
        self.task_repo.create_task(
            task_id=task_id,
            title="Test Task for Label Assignment",
            description="Task to test label assignment",
            git_branch_id=self.git_branch_id,
            assignees="test-orchestrator-agent",
            priority="medium",
            status="todo",
        )

        # Create and assign label
        label = self.label_repo.create_label(name="assign-test")
        result = self.label_repo.assign_label_to_task(
            task_id=task_id, label_id=label.id
        )

        assert result is True, "Label assignment should return True"

        # Verify assignment
        task_labels = self.label_repo.get_labels_by_task(task_id)
        assert len(task_labels) == 1, "Task should have 1 label"
        assert task_labels[0].name == "assign-test", "Label name should match"
        print("  ✓ Label assigned to task successfully")

    def test_assign_multiple_labels_to_task(self):
        """Test assigning multiple labels to one task"""
        task_id = str(uuid.uuid4())
        self.task_repo.create_task(
            task_id=task_id,
            title="Multi-Label Task",
            description="Task with multiple labels",
            git_branch_id=self.git_branch_id,
            assignees="test-orchestrator-agent",
            priority="high",
            status="todo",
        )

        # Create and assign multiple labels
        label_names = ["multi-backend", "multi-security", "multi-critical"]
        for name in label_names:
            label = self.label_repo.create_label(name=name)
            self.label_repo.assign_label_to_task(task_id=task_id, label_id=label.id)

        # Verify all labels assigned
        task_labels = self.label_repo.get_labels_by_task(task_id)
        assert len(task_labels) == 3, "Task should have 3 labels"
        task_label_names = [label.name for label in task_labels]
        for name in label_names:
            assert name in task_label_names, f"{name} should be in task labels"
        print("  ✓ Multiple labels assigned successfully")

    def test_same_label_multiple_tasks(self):
        """Test using same label across multiple tasks"""
        label = self.label_repo.create_label(name="shared-label")

        # Create 3 tasks and assign same label
        task_ids = []
        for i in range(3):
            task_id = str(uuid.uuid4())
            self.task_repo.create_task(
                task_id=task_id,
                title=f"Shared Label Task {i + 1}",
                description=f"Task {i + 1} with shared label",
                git_branch_id=self.git_branch_id,
                assignees="test-orchestrator-agent",
                priority="medium",
                status="todo",
            )
            task_ids.append(task_id)
            self.label_repo.assign_label_to_task(task_id=task_id, label_id=label.id)

        # Verify label is on all tasks
        tasks_with_label = self.label_repo.get_tasks_by_label(label.id)
        assert len(tasks_with_label) == 3, "Label should be on 3 tasks"
        print("  ✓ Same label shared across multiple tasks")

    def test_remove_label_from_task(self):
        """Test removing a label from a task"""
        task_id = str(uuid.uuid4())
        self.task_repo.create_task(
            task_id=task_id,
            title="Label Removal Test",
            description="Test removing label",
            git_branch_id=self.git_branch_id,
            assignees="test-orchestrator-agent",
            priority="medium",
            status="todo",
        )

        label = self.label_repo.create_label(name="temp-label")
        self.label_repo.assign_label_to_task(task_id=task_id, label_id=label.id)

        # Remove label
        result = self.label_repo.remove_label_from_task(
            task_id=task_id, label_id=label.id
        )

        assert result is True, "Label removal should return True"
        task_labels = self.label_repo.get_labels_by_task(task_id)
        assert len(task_labels) == 0, "Task should have no labels after removal"
        print("  ✓ Label removed from task successfully")

    # ========================================================================
    # Label Query Tests
    # ========================================================================

    def test_list_all_labels(self):
        """Test listing all labels"""
        # Create some labels
        for i in range(3):
            self.label_repo.create_label(name=f"list-test-{i}")

        labels = self.label_repo.list_labels()
        assert len(labels) >= 3, "Should have at least 3 labels"
        print(f"  ✓ Listed {len(labels)} labels")

    def test_get_label_by_name(self):
        """Test retrieving a label by name"""
        created_label = self.label_repo.create_label(name="name-search-test")

        found_label = self.label_repo.get_label_by_name("name-search-test")

        assert found_label is not None, "Label should be found"
        assert found_label.id == created_label.id, "IDs should match"
        assert found_label.name == "name-search-test", "Names should match"
        print("  ✓ Label found by name")

    def test_get_label_by_id(self):
        """Test retrieving a label by ID"""
        created_label = self.label_repo.create_label(name="id-search-test")

        found_label = self.label_repo.get_label(created_label.id)

        assert found_label is not None, "Label should be found"
        assert found_label.name == "id-search-test", "Names should match"
        print("  ✓ Label found by ID")

    # ========================================================================
    # Error Handling Tests
    # ========================================================================

    def test_duplicate_label_rejected(self):
        """Test that duplicate label names are rejected"""
        self.label_repo.create_label(name="duplicate-test")

        try:
            self.label_repo.create_label(name="duplicate-test")
            assert False, "Should have raised ValidationError"
        except Exception as e:
            assert "already exists" in str(e).lower(), "Error should mention duplicate"
            print("  ✓ Duplicate label correctly rejected")

    def test_assign_to_nonexistent_task(self):
        """Test assigning label to non-existent task"""
        label = self.label_repo.create_label(name="error-test")
        fake_task_id = str(uuid.uuid4())

        try:
            self.label_repo.assign_label_to_task(
                task_id=fake_task_id, label_id=label.id
            )
            assert False, "Should have raised NotFoundError"
        except Exception as e:
            assert "not found" in str(e).lower() or "Task" in str(
                e
            ), "Error should mention task not found"
            print("  ✓ Assignment to nonexistent task correctly rejected")

    def test_get_nonexistent_label(self):
        """Test getting a label that doesn't exist"""
        fake_label_id = str(uuid.uuid4())  # Use UUID string instead of integer
        label = self.label_repo.get_label(fake_label_id)

        assert label is None, "Should return None for nonexistent label"
        print("  ✓ Nonexistent label returns None")

    # ========================================================================
    # Test Runner
    # ========================================================================

    def run_all_tests(self):
        """Run all tests and print summary"""
        print("\n" + "=" * 80)
        print("COMPREHENSIVE LABEL INTEGRATION TEST SUITE")
        print("=" * 80)
        print(f"User ID: {self.user_id}")
        print(f"Branch ID: {self.git_branch_id}")
        print("=" * 80)

        # Label Creation Tests
        print("\n### LABEL CREATION TESTS ###")
        self.run_test("Create Single Label", self.test_create_single_label)
        self.run_test("Create Multiple Labels", self.test_create_multiple_labels)
        self.run_test(
            "Create Label with Complex Name", self.test_create_label_with_complex_name
        )
        self.run_test("Label Timestamp Precision", self.test_label_timestamp_precision)

        # Label-Task Association Tests
        print("\n### LABEL-TASK ASSOCIATION TESTS ###")
        self.run_test("Assign Label to Task", self.test_assign_label_to_task)
        self.run_test(
            "Assign Multiple Labels to Task", self.test_assign_multiple_labels_to_task
        )
        self.run_test("Same Label Multiple Tasks", self.test_same_label_multiple_tasks)
        self.run_test("Remove Label from Task", self.test_remove_label_from_task)

        # Label Query Tests
        print("\n### LABEL QUERY TESTS ###")
        self.run_test("List All Labels", self.test_list_all_labels)
        self.run_test("Get Label by Name", self.test_get_label_by_name)
        self.run_test("Get Label by ID", self.test_get_label_by_id)

        # Error Handling Tests
        print("\n### ERROR HANDLING TESTS ###")
        self.run_test("Duplicate Label Rejected", self.test_duplicate_label_rejected)
        self.run_test(
            "Assign to Nonexistent Task", self.test_assign_to_nonexistent_task
        )
        self.run_test("Get Nonexistent Label", self.test_get_nonexistent_label)

        # Print Summary
        self.print_summary()

        return self.get_exit_code()

    def print_summary(self):
        """Print test execution summary"""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["result"] == "PASS")
        failed = sum(1 for r in self.test_results if r["result"] == "FAIL")
        errors = sum(1 for r in self.test_results if r["result"] == "ERROR")
        success_rate = (passed / total * 100) if total > 0 else 0

        print(f"Total Tests: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"Errors: {errors} ⚠️")
        print(f"Success Rate: {success_rate:.1f}%")
        print("=" * 80)

        if passed == total:
            print("\n🎉 ALL TESTS PASSED!")
            print(
                "Label integration functionality is working correctly with UTC timestamps."
            )
        else:
            print(f"\n⚠️ {failed + errors} test(s) did not pass.")
            print("\nFailed/Error Tests:")
            for result in self.test_results:
                if result["result"] != "PASS":
                    print(f"  - {result['name']}: {result['result']}")
                    if "error" in result:
                        print(f"    Error: {result['error']}")

    def get_exit_code(self):
        """Get exit code based on test results"""
        failed = sum(1 for r in self.test_results if r["result"] != "PASS")
        return 0 if failed == 0 else 1

    def cleanup(self):
        """Cleanup test resources"""
        try:
            self.session.close()
        except Exception:
            pass


def main():
    """Main test execution"""
    test_suite = LabelIntegrationTestSuite()

    try:
        exit_code = test_suite.run_all_tests()
    finally:
        test_suite.cleanup()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
