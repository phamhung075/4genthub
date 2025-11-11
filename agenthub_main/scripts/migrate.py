#!/usr/bin/env python3
"""
Database Migration Manager
===========================

Comprehensive migration tool supporting both Alembic and raw SQL migrations.

Usage:
    # Alembic migrations (recommended for production)
    python scripts/migrate.py create "remove subtask_count column"
    python scripts/migrate.py upgrade head
    python scripts/migrate.py downgrade -1
    python scripts/migrate.py history
    python scripts/migrate.py current

    # Raw SQL migrations (simple, for development)
    python scripts/migrate.py apply migrations/remove_subtask_count_column.sql
    python scripts/migrate.py list

    # Auto-generate migration from model changes
    python scripts/migrate.py auto "detected changes"
"""

import subprocess
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


def run_alembic(args):
    """Run Alembic command."""
    alembic_dir = Path(__file__).parent.parent
    cmd = ["alembic"] + args

    print(f"🔧 Running: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, cwd=alembic_dir, capture_output=False)

    return result.returncode


def show_help():
    """Show usage help."""
    print("""
╔════════════════════════════════════════════════════════════════╗
║           Database Migration Manager - Help                   ║
╚════════════════════════════════════════════════════════════════╝

ALEMBIC COMMANDS (Production-Grade Migrations):
------------------------------------------------

  Create new migration:
    python scripts/migrate.py create "description"
    Example: python scripts/migrate.py create "remove subtask_count column"

  Auto-generate from model changes:
    python scripts/migrate.py auto "description"
    Example: python scripts/migrate.py auto "add new fields"

  Apply migrations:
    python scripts/migrate.py upgrade head        # Apply all pending
    python scripts/migrate.py upgrade +1          # Apply next one
    python scripts/migrate.py upgrade <revision>  # Apply to specific

  Rollback migrations:
    python scripts/migrate.py downgrade -1        # Rollback one
    python scripts/migrate.py downgrade base      # Rollback all
    python scripts/migrate.py downgrade <revision># Rollback to specific

  View migration info:
    python scripts/migrate.py history            # Show all migrations
    python scripts/migrate.py current            # Show current version
    python scripts/migrate.py show <revision>    # Show migration details

RAW SQL COMMANDS (Simple, Development):
----------------------------------------

  Apply SQL migration:
    python scripts/migrate.py apply migrations/file.sql

  List migrations:
    python scripts/migrate.py list


WORKFLOW EXAMPLES:
------------------

1. Create and apply new migration:
   python scripts/migrate.py create "add user preferences table"
   # Edit the generated file in alembic/versions/
   python scripts/migrate.py upgrade head

2. Auto-generate from ORM changes:
   # First, update your ORM models
   python scripts/migrate.py auto "updated Task model"
   # Review the generated migration
   python scripts/migrate.py upgrade head

3. Rollback last migration:
   python scripts/migrate.py downgrade -1

4. View migration history:
   python scripts/migrate.py history


BEST PRACTICES:
---------------

✅ DO:
  • Review auto-generated migrations before applying
  • Test migrations in development first
  • Write descriptive migration messages
  • Always create down migrations (rollback support)
  • Commit migration files to version control

❌ DON'T:
  • Edit applied migrations (create new one instead)
  • Skip migration testing
  • Use auto-migrations blindly
  • Forget to backup production data


TROUBLESHOOTING:
----------------

Q: "Target database is not up to date"
A: Run: python scripts/migrate.py upgrade head

Q: "Can't locate revision"
A: Check: python scripts/migrate.py history

Q: Migration conflicts
A: Run: python scripts/migrate.py current
   Then resolve manually or downgrade

Q: Want to start fresh
A: Run: python scripts/reset_database.py
   Then: python scripts/migrate.py upgrade head

""")


def main():
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)

    command = sys.argv[1]

    # Alembic commands
    if command == "create":
        if len(sys.argv) < 3:
            print("❌ Error: Migration message required")
            print('Usage: python scripts/migrate.py create "message"')
            sys.exit(1)
        message = sys.argv[2]
        return run_alembic(["revision", "-m", message])

    elif command == "auto":
        if len(sys.argv) < 3:
            print("❌ Error: Migration message required")
            print('Usage: python scripts/migrate.py auto "message"')
            sys.exit(1)
        message = sys.argv[2]
        print("🔍 Auto-detecting changes from ORM models...")
        return run_alembic(["revision", "--autogenerate", "-m", message])

    elif command == "upgrade":
        target = sys.argv[2] if len(sys.argv) > 2 else "head"
        return run_alembic(["upgrade", target])

    elif command == "downgrade":
        target = sys.argv[2] if len(sys.argv) > 2 else "-1"
        return run_alembic(["downgrade", target])

    elif command == "history":
        return run_alembic(["history", "--verbose"])

    elif command == "current":
        return run_alembic(["current", "--verbose"])

    elif command == "show":
        if len(sys.argv) < 3:
            print("❌ Error: Revision required")
            print("Usage: python scripts/migrate.py show <revision>")
            sys.exit(1)
        revision = sys.argv[2]
        return run_alembic(["show", revision])

    elif command == "apply":
        # Raw SQL migration
        if len(sys.argv) < 3:
            print("❌ Error: Migration file required")
            print("Usage: python scripts/migrate.py apply migrations/file.sql")
            sys.exit(1)
        from apply_migration import apply_migration

        migration_path = Path(sys.argv[2])
        apply_migration(migration_path)

    elif command == "list":
        # List raw SQL migrations
        from apply_migration import list_migrations

        list_migrations()

    elif command == "help" or command == "--help" or command == "-h":
        show_help()

    else:
        print(f"❌ Unknown command: {command}")
        print()
        show_help()
        sys.exit(1)


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code or 0)
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
