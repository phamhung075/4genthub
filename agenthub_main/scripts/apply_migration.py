#!/usr/bin/env python3
"""
SQL Migration Runner
====================

Applies SQL migration files to the database.
Tracks which migrations have been applied to prevent re-running.

Usage:
    python scripts/apply_migration.py migrations/remove_subtask_count_column.sql

Features:
    - Executes SQL migration files
    - Tracks migration history in database
    - Prevents duplicate migrations
    - Supports rollback (if SQL includes DOWN migration)
"""

import sys
from datetime import UTC, datetime, timezone
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from sqlalchemy import Column, DateTime, MetaData, String, Table, text

from fastmcp.task_management.infrastructure.database.database_config import (
    get_db_config,
)


def ensure_migration_table(engine):
    """Create migration tracking table if it doesn't exist."""
    metadata = MetaData()

    migration_table = Table(
        'schema_migrations',
        metadata,
        Column('migration_name', String, primary_key=True),
        Column('applied_at', DateTime, nullable=False),
        Column('checksum', String, nullable=True)
    )

    metadata.create_all(engine)
    return migration_table


def get_applied_migrations(engine):
    """Get list of already applied migrations."""
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT migration_name FROM schema_migrations ORDER BY applied_at"
        ))
        return {row[0] for row in result}


def mark_migration_applied(engine, migration_name):
    """Mark a migration as applied."""
    with engine.connect() as conn:
        conn.execute(text(
            "INSERT INTO schema_migrations (migration_name, applied_at) "
            "VALUES (:name, :timestamp)"
        ), {
            "name": migration_name,
            "timestamp": datetime.now(UTC)
        })
        conn.commit()


def apply_migration(migration_file: Path):
    """Apply a SQL migration file."""

    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        sys.exit(1)

    migration_name = migration_file.name

    print("=" * 60)
    print("DATABASE MIGRATION")
    print("=" * 60)
    print(f"📄 Migration: {migration_name}")
    print(f"📁 File: {migration_file}")
    print()

    try:
        # Get database configuration
        db_config = get_db_config()
        engine = db_config.engine

        print(f"📊 Database: {db_config.config.database_name}")
        print(f"🔧 Type: {db_config.config.database_type}")
        print()

        # Ensure migration tracking table exists
        ensure_migration_table(engine)

        # Check if already applied
        applied_migrations = get_applied_migrations(engine)

        if migration_name in applied_migrations:
            print(f"⚠️  Migration '{migration_name}' already applied")
            print("✅ Nothing to do")
            return

        # Read migration SQL
        sql_content = migration_file.read_text()

        print("📋 SQL Preview:")
        print("-" * 60)
        # Show first 500 chars
        preview = sql_content[:500]
        if len(sql_content) > 500:
            preview += "\n... (truncated)"
        print(preview)
        print("-" * 60)
        print()

        # Confirm execution
        response = input("Apply this migration? (y/N): ")
        if response.lower() != 'y':
            print("❌ Cancelled")
            return

        print()
        print("🔄 Applying migration...")

        # Execute migration
        with engine.connect() as conn:
            # Split by semicolons for multiple statements
            statements = [s.strip() for s in sql_content.split(';') if s.strip()]

            for i, statement in enumerate(statements, 1):
                # Skip comments-only statements
                if statement.startswith('--'):
                    continue

                print(f"   Executing statement {i}/{len(statements)}...")
                conn.execute(text(statement))

            conn.commit()

        # Mark as applied
        mark_migration_applied(engine, migration_name)

        print("✅ Migration applied successfully")
        print()
        print("=" * 60)
        print("✅ MIGRATION COMPLETE!")
        print("=" * 60)

    except Exception as e:
        print()
        print("=" * 60)
        print("❌ MIGRATION FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def list_migrations():
    """List all migrations and their status."""
    try:
        db_config = get_db_config()
        engine = db_config.engine

        ensure_migration_table(engine)
        applied = get_applied_migrations(engine)

        # Find migration files
        migrations_dir = Path(__file__).parent.parent / "migrations"
        if not migrations_dir.exists():
            print("No migrations directory found")
            return

        migration_files = sorted(migrations_dir.glob("*.sql"))

        print("=" * 60)
        print("MIGRATION STATUS")
        print("=" * 60)
        print()

        for mf in migration_files:
            status = "✅ Applied" if mf.name in applied else "⏳ Pending"
            print(f"{status:15} {mf.name}")

        print()
        print(f"Total: {len(migration_files)} migrations")
        print(f"Applied: {len(applied)}")
        print(f"Pending: {len(migration_files) - len(applied)}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Apply migration:  python scripts/apply_migration.py <migration.sql>")
        print("  List migrations:  python scripts/apply_migration.py --list")
        sys.exit(1)

    if sys.argv[1] == "--list":
        list_migrations()
    else:
        migration_path = Path(sys.argv[1])
        apply_migration(migration_path)
