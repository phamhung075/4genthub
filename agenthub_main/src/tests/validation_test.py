#!/usr/bin/env python3
"""
Simple test script to validate the duplicate name prevention functionality.

This script tests the domain validation services to ensure they work correctly.
"""

import sys
import os
import asyncio
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_project_name_validation():
    """Test the project name validation service"""
    logger.info("Testing project name validation...")

    try:
        from fastmcp.task_management.domain.services.project_name_validator import ProjectNameValidator
        from fastmcp.task_management.domain.exceptions.base_exceptions import ValidationException

        # Create a mock repository for testing
        class MockProjectRepository:
            def __init__(self):
                self.existing_names = ["Test Project", "Another Project"]

            async def find_by_name(self, name: str):
                if name in self.existing_names:
                    # Mock project object
                    class MockProject:
                        def __init__(self):
                            self.id = "test-id"
                            self.name = name
                    return MockProject()
                return None

        # Test the validator
        mock_repo = MockProjectRepository()
        validator = ProjectNameValidator(mock_repo)

        # Test 1: Valid new name should pass
        try:
            await validator.validate_project_name("New Project", "user123")
            logger.info("✅ Test 1 passed: Valid new name accepted")
        except Exception as e:
            logger.error(f"❌ Test 1 failed: {e}")

        # Test 2: Duplicate name should fail
        try:
            await validator.validate_project_name("Test Project", "user123")
            logger.error("❌ Test 2 failed: Duplicate name should have been rejected")
        except ValidationException as e:
            logger.info(f"✅ Test 2 passed: Duplicate name rejected - {e}")
        except Exception as e:
            logger.error(f"❌ Test 2 failed with unexpected error: {e}")

        # Test 3: Empty name should fail
        try:
            await validator.validate_project_name("", "user123")
            logger.error("❌ Test 3 failed: Empty name should have been rejected")
        except ValidationException as e:
            logger.info(f"✅ Test 3 passed: Empty name rejected - {e}")
        except Exception as e:
            logger.error(f"❌ Test 3 failed with unexpected error: {e}")

        # Test 4: Name with forbidden characters should fail
        try:
            await validator.validate_project_name("Test<Project>", "user123")
            logger.error("❌ Test 4 failed: Name with forbidden chars should have been rejected")
        except ValidationException as e:
            logger.info(f"✅ Test 4 passed: Forbidden characters rejected - {e}")
        except Exception as e:
            logger.error(f"❌ Test 4 failed with unexpected error: {e}")

    except ImportError as e:
        logger.error(f"❌ Import error: {e}")


async def test_branch_name_validation():
    """Test the git branch name validation service"""
    logger.info("Testing git branch name validation...")

    try:
        from fastmcp.task_management.domain.services.git_branch_name_validator import GitBranchNameValidator
        from fastmcp.task_management.domain.exceptions.base_exceptions import ValidationException

        # Create a mock repository for testing
        class MockGitBranchRepository:
            def __init__(self):
                self.existing_branches = []

            async def find_all_by_project(self, project_id: str):
                # Mock branches for project123
                if project_id == "project123":
                    class MockBranch:
                        def __init__(self, name):
                            self.id = f"branch-{name}"
                            self.name = name

                    return [MockBranch("main"), MockBranch("develop")]
                return []

        # Test the validator
        mock_repo = MockGitBranchRepository()
        validator = GitBranchNameValidator(mock_repo)

        # Test 1: Valid new branch name should pass
        try:
            await validator.validate_branch_name("feature/new-feature", "project123")
            logger.info("✅ Test 1 passed: Valid new branch name accepted")
        except Exception as e:
            logger.error(f"❌ Test 1 failed: {e}")

        # Test 2: Duplicate branch name should fail
        try:
            await validator.validate_branch_name("main", "project123")
            logger.error("❌ Test 2 failed: Duplicate branch name should have been rejected")
        except ValidationException as e:
            logger.info(f"✅ Test 2 passed: Duplicate branch name rejected - {e}")
        except Exception as e:
            logger.error(f"❌ Test 2 failed with unexpected error: {e}")

        # Test 3: Branch name with spaces should fail
        try:
            await validator.validate_branch_name("my feature", "project123")
            logger.error("❌ Test 3 failed: Branch name with spaces should have been rejected")
        except ValidationException as e:
            logger.info(f"✅ Test 3 passed: Branch name with spaces rejected - {e}")
        except Exception as e:
            logger.error(f"❌ Test 3 failed with unexpected error: {e}")

        # Test 4: Branch name with forbidden git characters should fail
        try:
            await validator.validate_branch_name("feature~with~tildes", "project123")
            logger.error("❌ Test 4 failed: Branch name with forbidden chars should have been rejected")
        except ValidationException as e:
            logger.info(f"✅ Test 4 passed: Forbidden git characters rejected - {e}")
        except Exception as e:
            logger.error(f"❌ Test 4 failed with unexpected error: {e}")

    except ImportError as e:
        logger.error(f"❌ Import error: {e}")


async def main():
    """Run all validation tests"""
    logger.info("Starting validation tests...")

    await test_project_name_validation()
    await test_branch_name_validation()

    logger.info("All validation tests completed!")


if __name__ == "__main__":
    asyncio.run(main())