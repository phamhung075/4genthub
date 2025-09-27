#!/usr/bin/env python3
"""Run database migration to add progress_history columns"""

import psycopg2
from psycopg2 import sql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.dev')

# Database connection parameters
DB_HOST = os.getenv('DATABASE_HOST', 'localhost')
DB_PORT = os.getenv('DATABASE_PORT', '5432')
DB_NAME = os.getenv('DATABASE_NAME', 'postgresdb')
DB_USER = os.getenv('DATABASE_USER', 'agenthub_user')
DB_PASSWORD = os.getenv('DATABASE_PASSWORD', 'agenthub_password')

def run_migration():
    """Execute the migration to add progress_history columns"""
    conn = None
    cur = None
    try:
        # Connect to database
        print(f"Connecting to database {DB_NAME} at {DB_HOST}:{DB_PORT}...")
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        conn.autocommit = True
        cur = conn.cursor()

        print("Adding progress_history column...")
        cur.execute("""
            ALTER TABLE tasks
            ADD COLUMN IF NOT EXISTS progress_history JSON DEFAULT '{}';
        """)

        print("Adding progress_count column...")
        cur.execute("""
            ALTER TABLE tasks
            ADD COLUMN IF NOT EXISTS progress_count INTEGER DEFAULT 0;
        """)

        # Check if details column exists and migrate data
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'tasks' AND column_name = 'details';
        """)

        if cur.fetchone():
            print("Migrating existing details to progress_history...")
            cur.execute("""
                UPDATE tasks
                SET progress_history = jsonb_build_object(
                    'entry_1', jsonb_build_object(
                        'content', CONCAT('=== Progress 1 ===', E'\\n', COALESCE(details, 'Initial task creation')),
                        'timestamp', COALESCE(updated_at::text, created_at::text),
                        'progress_number', 1
                    )
                ),
                progress_count = 1
                WHERE (progress_history::text = '{}' OR progress_history IS NULL)
                AND details IS NOT NULL;
            """)

            print("Dropping old details column...")
            cur.execute("ALTER TABLE tasks DROP COLUMN IF EXISTS details;")

        # Create index
        print("Creating index on progress_count...")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_progress_count ON tasks(progress_count);")

        # Verify migration
        print("\nVerifying migration...")
        cur.execute("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name = 'tasks'
            AND column_name IN ('progress_history', 'progress_count', 'details')
            ORDER BY ordinal_position;
        """)

        results = cur.fetchall()
        if results:
            print("\nCurrent task columns:")
            for row in results:
                print(f"  - {row[0]}: {row[1]} (default: {row[2] or 'none'})")

        # Check if migration was successful
        has_progress_history = any(row[0] == 'progress_history' for row in results)
        has_progress_count = any(row[0] == 'progress_count' for row in results)
        has_details = any(row[0] == 'details' for row in results)

        if has_progress_history and has_progress_count and not has_details:
            print("\n✅ Migration successful! Tasks table now has progress_history system.")
        elif has_details:
            print("\n⚠️ Warning: details column still exists. Manual intervention may be needed.")
        else:
            print("\n❌ Migration may have failed. Please check the table structure.")

    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

    return True

if __name__ == "__main__":
    print("Starting database migration for progress_history system...")
    print("-" * 50)
    if run_migration():
        print("\n✅ Migration completed successfully!")
    else:
        print("\n❌ Migration failed. Please check the error messages above.")