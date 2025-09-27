#!/usr/bin/env python3
"""
Run the project summaries migration using existing infrastructure
"""

import sys
import os
import asyncio
from pathlib import Path

# Add the src directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "agenthub_main" / "src"))

# Load environment from .env.dev
from dotenv import load_dotenv
load_dotenv(project_root / ".env.dev")

async def run_migration():
    """Run the project summaries migration"""
    try:
        from fastmcp.task_management.infrastructure.database.migration_runner import AutoMigrationRunner

        print("🔧 Starting migration runner...")
        runner = AutoMigrationRunner()

        print("🚀 Running project summaries migration...")
        await runner.run_migrations()

        print("✅ Migration completed successfully!")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_migration())