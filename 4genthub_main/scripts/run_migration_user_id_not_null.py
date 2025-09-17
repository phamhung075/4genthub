#!/usr/bin/env python3
"""
Script to run the user_id NOT NULL migration

This script ensures all user_id fields in the database are NOT NULL
by updating any NULL values to a fallback user ID.

Usage:
    python scripts/run_migration_user_id_not_null.py
    
Environment Variables:
    MCP_DB_PATH: Path to database file (default: 4genthub.db)
    MIGRATION_FALLBACK_USER_ID: User ID for NULL records (default: system)
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from fastmcp.task_management.infrastructure.database.migrations.add_user_id_not_null_constraints import run_migration_with_config
import logging

def main():
    """Run the user_id NOT NULL migration"""
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    logger = logging.getLogger(__name__)
    
    print("🔄 Starting user_id NOT NULL migration...")
    print("=" * 60)
    
    # Show current configuration
    db_path = os.getenv("MCP_DB_PATH", "4genthub.db")
    fallback_user_id = os.getenv("MIGRATION_FALLBACK_USER_ID", "system")
    
    print(f"Database path: {db_path}")
    print(f"Fallback user ID: {fallback_user_id}")
    print()
    
    # Check if database exists
    if not Path(db_path).exists():
        print(f"❌ Database file not found: {db_path}")
        print("Please ensure the database exists before running migration")
        return False
    
    # Run migration
    try:
        success = run_migration_with_config()
        
        if success:
            print()
            print("✅ Migration completed successfully!")
            print()
            print("Changes made:")
            print("- All NULL user_id values updated to fallback user ID")
            print("- Application code updated to enforce NOT NULL user_id")
            print("- Database integrity verified")
            print()
            print("Note: For full database constraint enforcement with SQLite,")
            print("consider recreating the database with the new schema.")
            return True
        else:
            print()
            print("❌ Migration failed!")
            print("Check the logs above for details.")
            return False
            
    except Exception as e:
        logger.error(f"Migration error: {e}")
        print(f"❌ Migration failed with error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)