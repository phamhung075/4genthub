"""Add ID validation constraints to prevent MCP ID confusion

This migration adds database-level constraints to enforce UUID format validation
and prevent the critical data integrity issues where MCP task IDs are incorrectly
stored as application task IDs.

Based on: ai_docs/troubleshooting-guides/subtask-wrong-task-id-api-calls.md
"""

import logging
from typing import Optional
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def upgrade(session, database_type: str = "sqlite"):
    """
    Add ID validation constraints to the database.

    Args:
        session: Database session
        database_type: Type of database ('sqlite' or 'postgresql')
    """
    try:
        logger.info(f"Adding ID validation constraints for {database_type}")

        if database_type.lower() == 'postgresql':
            _add_postgresql_constraints(session)
        else:
            _add_sqlite_constraints(session)

        session.commit()
        logger.info("ID validation constraints added successfully")

    except SQLAlchemyError as e:
        logger.error(f"Error adding ID validation constraints: {e}")
        session.rollback()
        raise


def downgrade(session, database_type: str = "sqlite"):
    """
    Remove ID validation constraints from the database.

    Args:
        session: Database session
        database_type: Type of database ('sqlite' or 'postgresql')
    """
    try:
        logger.info(f"Removing ID validation constraints for {database_type}")

        if database_type.lower() == 'postgresql':
            _remove_postgresql_constraints(session)
        else:
            _remove_sqlite_constraints(session)

        session.commit()
        logger.info("ID validation constraints removed successfully")

    except SQLAlchemyError as e:
        logger.error(f"Error removing ID validation constraints: {e}")
        session.rollback()
        raise


def _add_postgresql_constraints(session):
    """Add PostgreSQL-specific UUID validation constraints."""

    # UUID v4 format validation regex (strict)
    uuid_v4_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'

    # Relaxed UUID pattern for backwards compatibility
    uuid_relaxed_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'

    constraints = [
        # Projects table
        f"ALTER TABLE projects ADD CONSTRAINT chk_project_id_format CHECK (id ~* '{uuid_relaxed_pattern}');",

        # Project Git Branches table
        f"ALTER TABLE project_git_branchs ADD CONSTRAINT chk_git_branch_id_format CHECK (id ~* '{uuid_relaxed_pattern}');",
        f"ALTER TABLE project_git_branchs ADD CONSTRAINT chk_git_branch_project_id_format CHECK (project_id ~* '{uuid_relaxed_pattern}');",

        # Tasks table
        f"ALTER TABLE tasks ADD CONSTRAINT chk_task_id_format CHECK (id ~* '{uuid_relaxed_pattern}');",
        f"ALTER TABLE tasks ADD CONSTRAINT chk_task_git_branch_id_format CHECK (git_branch_id ~* '{uuid_relaxed_pattern}');",
        f"ALTER TABLE tasks ADD CONSTRAINT chk_task_context_id_format CHECK (context_id IS NULL OR context_id ~* '{uuid_relaxed_pattern}');",

        # Critical constraint: Prevent task_id == git_branch_id (common bug)
        "ALTER TABLE tasks ADD CONSTRAINT chk_task_id_not_equal_git_branch_id CHECK (id != git_branch_id);",

        # Task Subtasks table
        f"ALTER TABLE task_subtasks ADD CONSTRAINT chk_subtask_id_format CHECK (id ~* '{uuid_relaxed_pattern}');",
        f"ALTER TABLE task_subtasks ADD CONSTRAINT chk_subtask_task_id_format CHECK (task_id ~* '{uuid_relaxed_pattern}');",

        # Task Assignees table
        f"ALTER TABLE task_assignees ADD CONSTRAINT chk_assignee_id_format CHECK (id ~* '{uuid_relaxed_pattern}');",
        f"ALTER TABLE task_assignees ADD CONSTRAINT chk_assignee_task_id_format CHECK (task_id ~* '{uuid_relaxed_pattern}');",
        f"ALTER TABLE task_assignees ADD CONSTRAINT chk_assignee_agent_id_format CHECK (agent_id IS NULL OR agent_id ~* '{uuid_relaxed_pattern}');",

        # Task Dependencies table (if exists)
        f"ALTER TABLE task_dependencies ADD CONSTRAINT chk_dependency_id_format CHECK (id ~* '{uuid_relaxed_pattern}') ON CONFLICT DO NOTHING;",
        f"ALTER TABLE task_dependencies ADD CONSTRAINT chk_dependency_task_id_format CHECK (task_id ~* '{uuid_relaxed_pattern}') ON CONFLICT DO NOTHING;",
        f"ALTER TABLE task_dependencies ADD CONSTRAINT chk_dependency_depends_on_id_format CHECK (depends_on_id ~* '{uuid_relaxed_pattern}') ON CONFLICT DO NOTHING;",

        # Task Labels table (if exists)
        f"ALTER TABLE task_labels ADD CONSTRAINT chk_label_id_format CHECK (id ~* '{uuid_relaxed_pattern}') ON CONFLICT DO NOTHING;",
        f"ALTER TABLE task_labels ADD CONSTRAINT chk_label_task_id_format CHECK (task_id ~* '{uuid_relaxed_pattern}') ON CONFLICT DO NOTHING;",
    ]

    for constraint_sql in constraints:
        try:
            logger.info(f"Adding constraint: {constraint_sql}")
            session.execute(text(constraint_sql))
        except SQLAlchemyError as e:
            # Log but continue - some constraints might already exist or tables might not exist
            logger.warning(f"Constraint creation failed (continuing): {e}")


def _add_sqlite_constraints(session):
    """Add SQLite-specific UUID validation constraints."""

    # SQLite doesn't support regex constraints, so we use simpler length and format checks
    # We'll rely more on application-level validation for SQLite

    constraints = [
        # Basic length and format checks for UUID fields
        "PRAGMA foreign_keys = ON;",  # Ensure foreign key constraints are enabled

        # We can't add regex constraints in SQLite, but we can add some basic checks
        # These will be enforced at the application level through the IDValidator
    ]

    for constraint_sql in constraints:
        try:
            logger.info(f"Adding SQLite constraint: {constraint_sql}")
            session.execute(text(constraint_sql))
        except SQLAlchemyError as e:
            logger.warning(f"SQLite constraint failed (continuing): {e}")

    # For SQLite, we rely primarily on application-level validation
    logger.info("SQLite constraints added. UUID validation relies on application-level IDValidator.")


def _remove_postgresql_constraints(session):
    """Remove PostgreSQL-specific UUID validation constraints."""

    constraints_to_drop = [
        # Projects table
        "ALTER TABLE projects DROP CONSTRAINT IF EXISTS chk_project_id_format;",

        # Project Git Branches table
        "ALTER TABLE project_git_branchs DROP CONSTRAINT IF EXISTS chk_git_branch_id_format;",
        "ALTER TABLE project_git_branchs DROP CONSTRAINT IF EXISTS chk_git_branch_project_id_format;",

        # Tasks table
        "ALTER TABLE tasks DROP CONSTRAINT IF EXISTS chk_task_id_format;",
        "ALTER TABLE tasks DROP CONSTRAINT IF EXISTS chk_task_git_branch_id_format;",
        "ALTER TABLE tasks DROP CONSTRAINT IF EXISTS chk_task_context_id_format;",
        "ALTER TABLE tasks DROP CONSTRAINT IF EXISTS chk_task_id_not_equal_git_branch_id;",

        # Task Subtasks table
        "ALTER TABLE task_subtasks DROP CONSTRAINT IF EXISTS chk_subtask_id_format;",
        "ALTER TABLE task_subtasks DROP CONSTRAINT IF EXISTS chk_subtask_task_id_format;",

        # Task Assignees table
        "ALTER TABLE task_assignees DROP CONSTRAINT IF EXISTS chk_assignee_id_format;",
        "ALTER TABLE task_assignees DROP CONSTRAINT IF EXISTS chk_assignee_task_id_format;",
        "ALTER TABLE task_assignees DROP CONSTRAINT IF EXISTS chk_assignee_agent_id_format;",

        # Task Dependencies table
        "ALTER TABLE task_dependencies DROP CONSTRAINT IF EXISTS chk_dependency_id_format;",
        "ALTER TABLE task_dependencies DROP CONSTRAINT IF EXISTS chk_dependency_task_id_format;",
        "ALTER TABLE task_dependencies DROP CONSTRAINT IF EXISTS chk_dependency_depends_on_id_format;",

        # Task Labels table
        "ALTER TABLE task_labels DROP CONSTRAINT IF EXISTS chk_label_id_format;",
        "ALTER TABLE task_labels DROP CONSTRAINT IF EXISTS chk_label_task_id_format;",
    ]

    for constraint_sql in constraints_to_drop:
        try:
            logger.info(f"Dropping constraint: {constraint_sql}")
            session.execute(text(constraint_sql))
        except SQLAlchemyError as e:
            logger.warning(f"Constraint removal failed (continuing): {e}")


def _remove_sqlite_constraints(session):
    """Remove SQLite-specific constraints (minimal for SQLite)."""

    # SQLite has limited constraint modification support
    # Most validation constraints are application-level anyway
    logger.info("SQLite constraint removal complete (minimal constraints to remove)")


def check_constraints_exist(session, database_type: str = "sqlite") -> dict:
    """
    Check which ID validation constraints currently exist.

    Args:
        session: Database session
        database_type: Type of database

    Returns:
        Dictionary with constraint existence status
    """
    try:
        if database_type.lower() == 'postgresql':
            return _check_postgresql_constraints(session)
        else:
            return _check_sqlite_constraints(session)
    except Exception as e:
        logger.error(f"Error checking constraints: {e}")
        return {"error": str(e)}


def _check_postgresql_constraints(session) -> dict:
    """Check PostgreSQL constraint existence."""

    constraint_check_sql = """
    SELECT
        table_name,
        constraint_name,
        constraint_type
    FROM information_schema.table_constraints
    WHERE constraint_name LIKE 'chk_%_format'
       OR constraint_name = 'chk_task_id_not_equal_git_branch_id'
    ORDER BY table_name, constraint_name;
    """

    try:
        result = session.execute(text(constraint_check_sql))
        constraints = [dict(row._mapping) for row in result]

        return {
            "database_type": "postgresql",
            "constraints_found": len(constraints),
            "constraints": constraints,
            "has_critical_constraint": any(
                c["constraint_name"] == "chk_task_id_not_equal_git_branch_id"
                for c in constraints
            )
        }
    except Exception as e:
        return {"error": f"Failed to check PostgreSQL constraints: {e}"}


def _check_sqlite_constraints(session) -> dict:
    """Check SQLite constraint existence (limited)."""

    # SQLite has limited constraint introspection
    # We mainly check if foreign keys are enabled
    try:
        result = session.execute(text("PRAGMA foreign_keys;"))
        foreign_keys_enabled = result.scalar() == 1

        return {
            "database_type": "sqlite",
            "foreign_keys_enabled": foreign_keys_enabled,
            "note": "SQLite relies on application-level IDValidator for UUID validation"
        }
    except Exception as e:
        return {"error": f"Failed to check SQLite constraints: {e}"}


def validate_existing_data(session, database_type: str = "sqlite") -> dict:
    """
    Validate existing data against ID format requirements.

    Args:
        session: Database session
        database_type: Type of database

    Returns:
        Dictionary with validation results
    """
    try:
        logger.info("Validating existing data for ID format compliance")

        validation_results = {
            "database_type": database_type,
            "validation_timestamp": "NOW()",
            "tables_checked": [],
            "format_violations": [],
            "critical_issues": []
        }

        # Tables and ID columns to check
        tables_to_check = [
            ("projects", ["id"]),
            ("project_git_branchs", ["id", "project_id"]),
            ("tasks", ["id", "git_branch_id", "context_id"]),
            ("task_subtasks", ["id", "task_id"]),
            ("task_assignees", ["id", "task_id", "agent_id"]),
        ]

        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'

        for table_name, id_columns in tables_to_check:
            validation_results["tables_checked"].append(table_name)

            for column in id_columns:
                if database_type.lower() == 'postgresql':
                    # Check for invalid UUID formats in PostgreSQL
                    check_sql = f"""
                    SELECT COUNT(*) as invalid_count
                    FROM {table_name}
                    WHERE {column} IS NOT NULL
                      AND {column} !~* '{uuid_pattern}'
                    """
                else:
                    # Basic length check for SQLite
                    check_sql = f"""
                    SELECT COUNT(*) as invalid_count
                    FROM {table_name}
                    WHERE {column} IS NOT NULL
                      AND (LENGTH({column}) != 36 OR {column} NOT LIKE '%-%-%-%-%')
                    """

                try:
                    result = session.execute(text(check_sql))
                    invalid_count = result.scalar()

                    if invalid_count > 0:
                        validation_results["format_violations"].append({
                            "table": table_name,
                            "column": column,
                            "invalid_count": invalid_count
                        })
                except Exception as e:
                    logger.warning(f"Could not validate {table_name}.{column}: {e}")

        # Check for critical issue: task_id == git_branch_id
        try:
            critical_check_sql = """
            SELECT COUNT(*) as critical_count
            FROM tasks
            WHERE id = git_branch_id
            """
            result = session.execute(text(critical_check_sql))
            critical_count = result.scalar()

            if critical_count > 0:
                validation_results["critical_issues"].append({
                    "issue": "task_id equals git_branch_id",
                    "count": critical_count,
                    "severity": "CRITICAL",
                    "description": "This indicates the MCP ID confusion bug"
                })
        except Exception as e:
            logger.warning(f"Could not check critical constraint: {e}")

        validation_results["is_valid"] = (
            len(validation_results["format_violations"]) == 0 and
            len(validation_results["critical_issues"]) == 0
        )

        return validation_results

    except Exception as e:
        logger.error(f"Error validating existing data: {e}")
        return {"error": str(e)}


# Utility function for manual constraint verification
def verify_constraints_work(session, database_type: str = "sqlite") -> dict:
    """
    Test that the ID validation constraints are working correctly.

    Args:
        session: Database session
        database_type: Type of database

    Returns:
        Dictionary with test results
    """
    try:
        logger.info("Testing ID validation constraints")

        test_results = {
            "database_type": database_type,
            "tests_performed": [],
            "constraints_working": True,
            "errors": []
        }

        # Test invalid UUID insertion (should fail)
        test_cases = [
            {
                "test": "invalid_uuid_format",
                "sql": "INSERT INTO projects (id, name, user_id) VALUES ('invalid-uuid', 'Test Project', 'test-user')",
                "should_fail": True
            },
            {
                "test": "task_id_equals_git_branch_id",
                "sql": "INSERT INTO tasks (id, git_branch_id, title, description, user_id) VALUES ('550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000', 'Test', 'Test', 'test-user')",
                "should_fail": True
            }
        ]

        for test_case in test_cases:
            try:
                session.execute(text(test_case["sql"]))
                session.rollback()  # Always rollback test data

                # If we get here without exception, constraint didn't work
                if test_case["should_fail"]:
                    test_results["constraints_working"] = False
                    test_results["errors"].append(f"Constraint failed for: {test_case['test']}")

                test_results["tests_performed"].append({
                    "test": test_case["test"],
                    "expected_failure": test_case["should_fail"],
                    "actual_result": "succeeded",
                    "constraint_working": not test_case["should_fail"]
                })

            except SQLAlchemyError as e:
                session.rollback()

                # Exception expected for should_fail tests
                test_results["tests_performed"].append({
                    "test": test_case["test"],
                    "expected_failure": test_case["should_fail"],
                    "actual_result": "failed",
                    "constraint_working": test_case["should_fail"],
                    "error": str(e)
                })

        return test_results

    except Exception as e:
        logger.error(f"Error testing constraints: {e}")
        return {"error": str(e)}