"""
Migration script to add progress_state field to tasks and subtasks tables
and populate it based on existing status and progress_percentage data.

This migration maintains backward compatibility while introducing the new stepper schema.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List
from sqlalchemy import text, create_engine, MetaData, Table, Column, Enum as SQLEnum
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from ....domain.enums.progress_enums import ProgressState
from ..database_config import get_database_url

logger = logging.getLogger(__name__)


class ProgressStateMigration:
    """Migration class to add progress_state field and populate it from existing data."""

    def __init__(self):
        self.database_url = get_database_url()
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def run_migration(self) -> Dict[str, Any]:
        """
        Run the complete migration process.

        Returns:
            Dict with migration results and statistics
        """
        migration_start = datetime.now()
        results = {
            "started_at": migration_start.isoformat(),
            "tasks_updated": 0,
            "subtasks_updated": 0,
            "errors": [],
            "success": False
        }

        try:
            logger.info("Starting progress_state migration...")

            # Step 1: Add progress_state column to tasks table
            tasks_added = self._add_progress_state_column_to_tasks()
            logger.info(f"Added progress_state column to tasks table: {tasks_added}")

            # Step 2: Add progress_state column to subtasks table
            subtasks_added = self._add_progress_state_column_to_subtasks()
            logger.info(f"Added progress_state column to subtasks table: {subtasks_added}")

            # Step 3: Populate progress_state for existing tasks
            tasks_updated = self._populate_task_progress_states()
            results["tasks_updated"] = tasks_updated
            logger.info(f"Updated {tasks_updated} tasks with progress_state")

            # Step 4: Populate progress_state for existing subtasks
            subtasks_updated = self._populate_subtask_progress_states()
            results["subtasks_updated"] = subtasks_updated
            logger.info(f"Updated {subtasks_updated} subtasks with progress_state")

            results["success"] = True
            results["completed_at"] = datetime.now().isoformat()

            logger.info("Progress_state migration completed successfully")
            return results

        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            results["errors"].append(str(e))
            results["completed_at"] = datetime.now().isoformat()
            return results

    def _add_progress_state_column_to_tasks(self) -> bool:
        """Add progress_state column to tasks table if it doesn't exist."""
        try:
            with self.engine.connect() as connection:
                # Check if column already exists
                inspector = connection.dialect.inspector(connection)
                columns = [col['name'] for col in inspector.get_columns('tasks')]

                if 'progress_state' in columns:
                    logger.info("progress_state column already exists in tasks table")
                    return True

                # Add the column
                connection.execute(text(
                    "ALTER TABLE tasks ADD COLUMN progress_state VARCHAR(20) DEFAULT 'initial' NOT NULL"
                ))
                connection.commit()
                logger.info("Added progress_state column to tasks table")
                return True

        except SQLAlchemyError as e:
            logger.error(f"Failed to add progress_state column to tasks table: {e}")
            raise

    def _add_progress_state_column_to_subtasks(self) -> bool:
        """Add progress_state column to subtasks table if it doesn't exist."""
        try:
            with self.engine.connect() as connection:
                # Check if column already exists
                inspector = connection.dialect.inspector(connection)
                columns = [col['name'] for col in inspector.get_columns('subtasks')]

                if 'progress_state' in columns:
                    logger.info("progress_state column already exists in subtasks table")
                    return True

                # Add the column
                connection.execute(text(
                    "ALTER TABLE subtasks ADD COLUMN progress_state VARCHAR(20) DEFAULT 'initial' NOT NULL"
                ))
                connection.commit()
                logger.info("Added progress_state column to subtasks table")
                return True

        except SQLAlchemyError as e:
            logger.error(f"Failed to add progress_state column to subtasks table: {e}")
            raise

    def _populate_task_progress_states(self) -> int:
        """Populate progress_state for existing tasks based on status and progress_percentage."""
        try:
            updated_count = 0

            with self.engine.connect() as connection:
                # Get all tasks with their current status and progress_percentage
                result = connection.execute(text(
                    "SELECT id, status, progress_percentage FROM tasks"
                ))

                tasks = result.fetchall()

                for task in tasks:
                    task_id, status, progress_percentage = task

                    # Determine progress_state based on existing data
                    progress_state = self._determine_progress_state_from_legacy_data(
                        status, progress_percentage
                    )

                    # Update the task
                    connection.execute(text(
                        "UPDATE tasks SET progress_state = :progress_state WHERE id = :task_id"
                    ), {
                        "progress_state": progress_state.value,
                        "task_id": task_id
                    })

                    updated_count += 1

                connection.commit()
                return updated_count

        except SQLAlchemyError as e:
            logger.error(f"Failed to populate task progress_states: {e}")
            raise

    def _populate_subtask_progress_states(self) -> int:
        """Populate progress_state for existing subtasks based on status and progress_percentage."""
        try:
            updated_count = 0

            with self.engine.connect() as connection:
                # Get all subtasks with their current status and progress_percentage
                result = connection.execute(text(
                    "SELECT id, status, progress_percentage FROM subtasks"
                ))

                subtasks = result.fetchall()

                for subtask in subtasks:
                    subtask_id, status, progress_percentage = subtask

                    # Determine progress_state based on existing data
                    progress_state = self._determine_progress_state_from_legacy_data(
                        status, progress_percentage
                    )

                    # Update the subtask
                    connection.execute(text(
                        "UPDATE subtasks SET progress_state = :progress_state WHERE id = :subtask_id"
                    ), {
                        "progress_state": progress_state.value,
                        "subtask_id": subtask_id
                    })

                    updated_count += 1

                connection.commit()
                return updated_count

        except SQLAlchemyError as e:
            logger.error(f"Failed to populate subtask progress_states: {e}")
            raise

    def _determine_progress_state_from_legacy_data(
        self,
        status: str,
        progress_percentage: int
    ) -> ProgressState:
        """
        Determine progress_state from legacy status and progress_percentage.

        Args:
            status: Current task/subtask status
            progress_percentage: Current progress percentage

        Returns:
            ProgressState enum value
        """
        if not status:
            return ProgressState.INITIAL

        status_lower = status.lower()

        # Check for completed states
        if status_lower in ['done', 'completed', 'finished']:
            return ProgressState.COMPLETE

        # Check for in-progress states
        if status_lower in ['in_progress', 'in-progress', 'active']:
            return ProgressState.IN_PROGRESS

        # Check for initial states
        if status_lower in ['todo', 'pending']:
            # If has progress but still in todo, consider it in_progress
            if progress_percentage and progress_percentage > 0:
                return ProgressState.IN_PROGRESS
            return ProgressState.INITIAL

        # Fallback to progress percentage
        if progress_percentage is not None:
            if progress_percentage >= 100:
                return ProgressState.COMPLETE
            elif progress_percentage > 0:
                return ProgressState.IN_PROGRESS

        # Default to initial
        return ProgressState.INITIAL

    def rollback_migration(self) -> Dict[str, Any]:
        """
        Rollback the migration by removing the progress_state columns.

        Returns:
            Dict with rollback results
        """
        rollback_start = datetime.now()
        results = {
            "started_at": rollback_start.isoformat(),
            "success": False,
            "errors": []
        }

        try:
            logger.info("Starting progress_state migration rollback...")

            with self.engine.connect() as connection:
                # Remove progress_state column from tasks table
                try:
                    connection.execute(text("ALTER TABLE tasks DROP COLUMN progress_state"))
                    logger.info("Removed progress_state column from tasks table")
                except SQLAlchemyError as e:
                    logger.warning(f"Could not remove progress_state from tasks: {e}")

                # Remove progress_state column from subtasks table
                try:
                    connection.execute(text("ALTER TABLE subtasks DROP COLUMN progress_state"))
                    logger.info("Removed progress_state column from subtasks table")
                except SQLAlchemyError as e:
                    logger.warning(f"Could not remove progress_state from subtasks: {e}")

                connection.commit()

            results["success"] = True
            results["completed_at"] = datetime.now().isoformat()
            logger.info("Progress_state migration rollback completed successfully")
            return results

        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}")
            results["errors"].append(str(e))
            results["completed_at"] = datetime.now().isoformat()
            return results


def run_migration():
    """Run the progress_state migration."""
    migration = ProgressStateMigration()
    return migration.run_migration()


def rollback_migration():
    """Rollback the progress_state migration."""
    migration = ProgressStateMigration()
    return migration.rollback_migration()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        print("Running rollback...")
        result = rollback_migration()
    else:
        print("Running migration...")
        result = run_migration()

    print(f"Migration result: {result}")