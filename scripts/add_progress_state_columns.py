#!/usr/bin/env python3
"""
Script to add missing progress_state columns to tasks and subtasks tables.
"""

import os
import sys
import psycopg2
from psycopg2 import sql

# Database connection details
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "agenthub")
DB_USER = os.getenv("DB_USER", "agenthub_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "agenthub_password")


def add_progress_state_columns():
    """Add progress_state column to tasks and subtasks tables."""

    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()

        # Add progress_state column to tasks table if it doesn't exist
        print("Checking tasks table for progress_state column...")
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'tasks' AND column_name = 'progress_state'
        """)

        if not cur.fetchone():
            print("Adding progress_state column to tasks table...")
            cur.execute("""
                ALTER TABLE tasks
                ADD COLUMN IF NOT EXISTS progress_state VARCHAR(20) DEFAULT 'INITIAL' NOT NULL
            """)
            conn.commit()
            print("✅ Added progress_state column to tasks table")
        else:
            print("✅ progress_state column already exists in tasks table")

        # Add progress_state column to subtasks table if it doesn't exist
        print("Checking subtasks table for progress_state column...")
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'subtasks' AND column_name = 'progress_state'
        """)

        if not cur.fetchone():
            print("Adding progress_state column to subtasks table...")
            cur.execute("""
                ALTER TABLE subtasks
                ADD COLUMN IF NOT EXISTS progress_state VARCHAR(20) DEFAULT 'INITIAL' NOT NULL
            """)
            conn.commit()
            print("✅ Added progress_state column to subtasks table")
        else:
            print("✅ progress_state column already exists in subtasks table")

        # Update existing records to set proper progress_state based on status
        print("Updating existing records...")

        # Update tasks
        cur.execute("""
            UPDATE tasks
            SET progress_state = CASE
                WHEN status = 'done' THEN 'COMPLETE'
                WHEN status IN ('in_progress', 'active') THEN 'IN_PROGRESS'
                ELSE 'INITIAL'
            END
            WHERE progress_state = 'INITIAL'
        """)
        tasks_updated = cur.rowcount

        # Update subtasks
        cur.execute("""
            UPDATE subtasks
            SET progress_state = CASE
                WHEN status = 'done' THEN 'COMPLETE'
                WHEN status IN ('in_progress', 'active') THEN 'IN_PROGRESS'
                ELSE 'INITIAL'
            END
            WHERE progress_state = 'INITIAL'
        """)
        subtasks_updated = cur.rowcount

        conn.commit()
        print(f"✅ Updated {tasks_updated} tasks and {subtasks_updated} subtasks")

        # Close connection
        cur.close()
        conn.close()

        print("\n✅ Migration completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False


if __name__ == "__main__":
    success = add_progress_state_columns()
    sys.exit(0 if success else 1)