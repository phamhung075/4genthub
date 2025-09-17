#!/usr/bin/env python3
"""
Script to run the migration for adding user_id to project_contexts table.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastmcp.task_management.infrastructure.database.database_config import get_db_config
from fastmcp.task_management.infrastructure.database.migrations.add_user_id_to_project_contexts import upgrade

def main():
    """Run the migration."""
    try:
        print("Starting migration: Adding user_id to project_contexts table...")
        
        # Get database configuration
        db_config = get_db_config()
        
        # Get a session
        session = db_config.get_session()
        
        try:
            # Run the upgrade
            upgrade(session)
            print("✅ Migration completed successfully!")
            
        except Exception as e:
            session.rollback()
            print(f"❌ Migration failed: {e}")
            raise
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()