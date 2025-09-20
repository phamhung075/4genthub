"""Usage examples for IDValidator domain service.

This module demonstrates how to integrate IDValidator into various parts
of the agenthub system to prevent MCP ID vs Application ID confusion.
"""

import logging
from typing import Optional
from .id_validator import IDValidator, prevent_id_confusion, ValidationResult

logger = logging.getLogger(__name__)


class SubtaskControllerExample:
    """
    Example showing how to fix the critical subtask controller bug using IDValidator.

    This demonstrates the BEFORE and AFTER code for preventing the critical issue
    where MCP task IDs are incorrectly passed as git_branch_ids.
    """

    def __init__(self, facade_service):
        self._facade_service = facade_service
        self.id_validator = IDValidator()

    def _get_facade_for_request_WRONG(self, task_id: str, user_id: str):
        """
        WRONG IMPLEMENTATION - This causes the critical data integrity bug.

        DO NOT USE - This is the problematic code that led to MCP task IDs
        being stored as application task IDs in the database.
        """
        # BUG: Directly passing task_id as git_branch_id without validation
        return self._facade_service.get_subtask_facade(
            user_id=user_id,
            git_branch_id=task_id  # CRITICAL BUG: task_id ≠ git_branch_id
        )

    def _get_facade_for_request_FIXED(self, task_id: str, user_id: str):
        """
        FIXED IMPLEMENTATION - Uses IDValidator to prevent parameter confusion.

        This implementation includes:
        1. Parameter validation using IDValidator
        2. Proper git_branch_id lookup from task
        3. Clear error messages for debugging
        4. Prevention of critical data integrity issues
        """
        # Step 1: Validate parameters using IDValidator
        try:
            prevent_id_confusion(task_id=task_id, user_id=user_id)
        except Exception as e:
            logger.error(f"Parameter validation failed: {e}")
            raise ValueError(f"Invalid parameters: {e}")

        # Step 2: Validate task context specifically
        task_validation = self.id_validator.validate_task_context(task_id)
        if not task_validation.is_valid:
            raise ValueError(f"Task validation failed: {task_validation.error_message}")

        # Step 3: Look up the correct git_branch_id from task
        try:
            # Use task facade to get task details
            task_facade = self._facade_service.get_task_facade(user_id=user_id)
            task_response = task_facade.get_task(task_id=task_id)

            if not task_response or not task_response.get('success'):
                raise ValueError(f"Task {task_id} not found or inaccessible")

            # Extract git_branch_id from task data
            task_data = task_response.get('data', {}).get('task', {})
            git_branch_id = task_data.get('git_branch_id')

            if not git_branch_id:
                raise ValueError(f"Task {task_id} missing git_branch_id")

            # Step 4: Validate that task_id ≠ git_branch_id (critical check)
            context_validation = self.id_validator.validate_task_context(
                task_id=task_id,
                expected_git_branch_id=git_branch_id
            )

            if not context_validation.is_valid:
                # This catches the critical bug where task_id == git_branch_id
                logger.error(f"Critical parameter confusion detected: {context_validation.error_message}")
                raise ValueError(f"Parameter confusion detected: {context_validation.error_message}")

            # Step 5: Final parameter validation before facade creation
            prevent_id_confusion(task_id=task_id, git_branch_id=git_branch_id, user_id=user_id)

            # Step 6: Create facade with CORRECT git_branch_id
            return self._facade_service.get_subtask_facade(
                user_id=user_id,
                git_branch_id=git_branch_id  # FIXED: Use correct git_branch_id
            )

        except Exception as e:
            logger.error(f"Failed to resolve git_branch_id for task {task_id}: {e}")

            # Provide fix suggestions for debugging
            suggestions = self.id_validator.suggest_fix_for_confusion(
                confused_task_id=task_id,
                context="subtask_controller._get_facade_for_request"
            )
            logger.error(f"Fix suggestions: {suggestions}")

            raise ValueError(f"Facade creation failed: {e}")


class FacadeServiceExample:
    """
    Example showing how to add validation to facade service methods.
    """

    def __init__(self):
        self.id_validator = IDValidator()

    def get_subtask_facade_with_validation(self,
                                         user_id: str,
                                         git_branch_id: Optional[str] = None,
                                         project_id: Optional[str] = None):
        """
        Enhanced facade creation with comprehensive ID validation.

        Prevents the critical issues by validating all parameters before
        creating repository contexts.
        """
        # Validate all provided parameters
        validation_result = self.id_validator.validate_parameter_mapping(
            git_branch_id=git_branch_id,
            project_id=project_id,
            user_id=user_id
        )

        if not validation_result.is_valid:
            logger.error(f"Facade parameter validation failed: {validation_result.error_message}")
            raise ValueError(f"Invalid facade parameters: {validation_result.error_message}")

        # Log warnings for monitoring
        if validation_result.warnings:
            for warning in validation_result.warnings:
                logger.warning(f"Facade creation warning: {warning}")

        # Proceed with facade creation...
        logger.info(f"Creating subtask facade with validated parameters: "
                   f"git_branch_id={git_branch_id}, project_id={project_id}, user_id={user_id}")

        # ... actual facade creation logic here ...


class MCPControllerBaseExample:
    """
    Example base class for MCP controllers with built-in ID validation.
    """

    def __init__(self):
        self.id_validator = IDValidator()

    def validate_request_parameters(self, **kwargs) -> ValidationResult:
        """
        Validate all request parameters to prevent ID confusion.

        This method should be called at the beginning of every MCP controller
        method to catch parameter confusion early.
        """
        # Extract ID parameters
        task_id = kwargs.get('task_id')
        git_branch_id = kwargs.get('git_branch_id')
        project_id = kwargs.get('project_id')
        user_id = kwargs.get('user_id')

        # Validate parameter mapping
        result = self.id_validator.validate_parameter_mapping(
            task_id=task_id,
            git_branch_id=git_branch_id,
            project_id=project_id,
            user_id=user_id
        )

        # Log validation results
        if not result.is_valid:
            logger.error(f"MCP controller parameter validation failed: {result.error_message}")
        elif result.warnings:
            for warning in result.warnings:
                logger.warning(f"MCP controller parameter warning: {warning}")

        return result

    def handle_request_with_validation(self, action: str, **kwargs):
        """
        Example request handler with built-in validation.
        """
        # Always validate parameters first
        validation_result = self.validate_request_parameters(**kwargs)

        if not validation_result.is_valid:
            return {
                "success": False,
                "error": "PARAMETER_VALIDATION_FAILED",
                "message": validation_result.error_message,
                "suggestions": self.id_validator.suggest_fix_for_confusion(
                    confused_task_id=kwargs.get('task_id', 'unknown'),
                    context=f"MCP controller {action} action"
                )
            }

        # Proceed with actual request handling...
        logger.info(f"Processing {action} with validated parameters")
        return {"success": True, "message": "Request processed successfully"}


class DatabaseConstraintExample:
    """
    Example showing how to add database-level validation.
    """

    @staticmethod
    def create_id_validation_constraints():
        """
        SQL commands to add database constraints that prevent ID confusion.

        These constraints work at the database level to catch issues that
        slip through application validation.
        """
        return [
            # UUID format validation for task IDs
            """
            ALTER TABLE tasks
            ADD CONSTRAINT chk_task_id_uuid_format
            CHECK (id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$');
            """,

            # UUID format validation for subtask task_id foreign key
            """
            ALTER TABLE task_subtasks
            ADD CONSTRAINT chk_subtask_task_id_uuid_format
            CHECK (task_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$');
            """,

            # Foreign key constraint to prevent orphaned subtasks
            """
            ALTER TABLE task_subtasks
            ADD CONSTRAINT fk_subtask_task_id
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE;
            """,

            # Ensure git_branch_id in tasks table references actual git branches
            """
            ALTER TABLE tasks
            ADD CONSTRAINT fk_task_git_branch_id
            FOREIGN KEY (git_branch_id) REFERENCES git_branches(id) ON DELETE CASCADE;
            """
        ]

    @staticmethod
    def validate_existing_data():
        """
        SQL queries to find and validate existing data for corruption.
        """
        return [
            # Find subtasks with invalid task_id references
            """
            SELECT ts.id as subtask_id, ts.task_id, t.id as actual_task_id
            FROM task_subtasks ts
            LEFT JOIN tasks t ON ts.task_id = t.id
            WHERE t.id IS NULL;
            """,

            # Find tasks with git_branch_id that don't reference actual branches
            """
            SELECT t.id as task_id, t.git_branch_id, gb.id as actual_branch_id
            FROM tasks t
            LEFT JOIN git_branches gb ON t.git_branch_id = gb.id
            WHERE gb.id IS NULL;
            """,

            # Find potential ID confusion (same ID used in multiple contexts)
            """
            SELECT 'task_id_as_branch_id' as issue_type, COUNT(*) as count
            FROM tasks t1
            JOIN git_branches gb ON t1.id = gb.id
            UNION ALL
            SELECT 'branch_id_as_task_id' as issue_type, COUNT(*) as count
            FROM git_branches gb
            JOIN tasks t ON gb.id = t.id;
            """
        ]


# Integration testing examples
def test_integration_example():
    """
    Example of how to test the IDValidator integration.
    """
    # Test the fixed subtask controller
    class MockFacadeService:
        def get_task_facade(self, user_id):
            return MockTaskFacade()

        def get_subtask_facade(self, user_id, git_branch_id):
            return MockSubtaskFacade()

    class MockTaskFacade:
        def get_task(self, task_id):
            return {
                'success': True,
                'data': {
                    'task': {
                        'id': task_id,
                        'git_branch_id': '550e8400-e29b-41d4-a716-446655440001'
                    }
                }
            }

    class MockSubtaskFacade:
        pass

    # Test the fixed implementation
    controller = SubtaskControllerExample(MockFacadeService())

    try:
        facade = controller._get_facade_for_request_FIXED(
            task_id='550e8400-e29b-41d4-a716-446655440000',
            user_id='user-550e8400-e29b-41d4-a716-446655440002'
        )
        print("✅ IDValidator integration successful - no parameter confusion detected")
        return True
    except Exception as e:
        print(f"❌ IDValidator integration failed: {e}")
        return False


if __name__ == "__main__":
    # Run integration test
    test_integration_example()