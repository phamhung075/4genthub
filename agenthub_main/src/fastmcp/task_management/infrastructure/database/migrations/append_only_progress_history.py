"""
Migration: Replace details field with append-only progress history
Date: 2025-09-21
Description: Convert existing task details to progress_history format with NO backward compatibility
"""

import json
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.orm import Session
from ..database_config import get_engine


def migrate_details_to_progress_history():
    """
    Migrate existing task details to new progress_history format.
    This is a ONE-WAY migration with NO rollback support.
    """
    engine = get_engine()

    with Session(engine) as session:
        print("Starting migration: details -> progress_history")

        # Step 1: Add new columns if they don't exist
        try:
            session.execute(text("ALTER TABLE tasks ADD COLUMN progress_history JSON DEFAULT '{}'"))
            print("✅ Added progress_history column")
        except Exception as e:
            print(f"ℹ️  progress_history column may already exist: {e}")

        try:
            session.execute(text("ALTER TABLE tasks ADD COLUMN progress_count INTEGER DEFAULT 0"))
            print("✅ Added progress_count column")
        except Exception as e:
            print(f"ℹ️  progress_count column may already exist: {e}")

        session.commit()

        # Step 2: Migrate existing data
        tasks_result = session.execute(text("SELECT id, details FROM tasks WHERE details IS NOT NULL AND details != ''"))
        migrated_count = 0

        for task in tasks_result:
            task_id = task[0]
            details = task[1]

            if details and details.strip():
                # Create progress_history entry
                progress_entry = {
                    "progress_1": {
                        "content": f"=== Progress 1 ===\n{details}",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "progress_number": 1
                    }
                }

                # Update task with new fields
                session.execute(
                    text("UPDATE tasks SET progress_history = :progress_history, progress_count = 1 WHERE id = :task_id"),
                    {"progress_history": json.dumps(progress_entry), "task_id": task_id}
                )
                migrated_count += 1

        session.commit()
        print(f"✅ Migrated {migrated_count} tasks from details to progress_history")

        # Step 3: Remove old details column (NO BACKWARD COMPATIBILITY)
        try:
            session.execute(text("ALTER TABLE tasks DROP COLUMN details"))
            print("✅ Removed old details column - NO ROLLBACK POSSIBLE")
        except Exception as e:
            print(f"⚠️  Could not remove details column: {e}")

        session.commit()
        print("🎉 Migration completed successfully!")


def rollback_migration():
    """
    NO ROLLBACK SUPPORT - This migration is designed for clean breaks only.
    """
    raise NotImplementedError(
        "NO ROLLBACK SUPPORT: This migration implements a clean break with no backward compatibility. "
        "Rolling back would require manual database restoration from backup."
    )


if __name__ == "__main__":
    print("🚨 WARNING: This migration will permanently remove the details column!")
    print("🚨 NO ROLLBACK SUPPORT - Clean break implementation only!")

    confirm = input("Type 'CONFIRM' to proceed with migration: ")
    if confirm == "CONFIRM":
        migrate_details_to_progress_history()
    else:
        print("Migration cancelled.")