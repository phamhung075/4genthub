#!/usr/bin/env python3
"""
Script to run the branch summaries materialized view migration
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine
from add_branch_summaries_materialized_view import migrate_up, migrate_down
import argparse


async def main():
    parser = argparse.ArgumentParser(description="Run branch summaries materialized view migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    args = parser.parse_args()

    # Get database URL from environment
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/agenthub.db")

    # Convert to async URL if needed
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    elif DATABASE_URL.startswith("sqlite:///"):
        DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")

    print(f"Using database: {DATABASE_URL}")

    engine = create_async_engine(DATABASE_URL, echo=True)

    try:
        if args.rollback:
            print("Rolling back migration...")
            await migrate_down(engine)
            print("Migration rolled back successfully!")
        else:
            print("Running migration...")
            await migrate_up(engine)
            print("Migration completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())