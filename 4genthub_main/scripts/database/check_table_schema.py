#!/usr/bin/env python3
"""Check the actual database table schema"""

import os
import sys
from pathlib import Path

# Set up environment for PostgreSQL
os.environ['DATABASE_TYPE'] = 'postgresql'
os.environ['DATABASE_URL'] = 'postgresql://4genthub_user:4genthub_password@localhost:5432/4genthub'

# Add the project to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from 4genthub_main.src.fastmcp.task_management.infrastructure.database.database_config import get_db_config
from sqlalchemy import text

def check_table_schema():
    """Check the actual database table schema"""
    print("🔍 Checking database table schema...")
    
    try:
        # Get database configuration
        db = get_db_config()
        print("✅ Database connection established")
        
        with db.get_session() as session:
            # Check project_git_branchs table schema
            print("\n📋 Checking project_git_branchs table schema:")
            result = session.execute(text("""
                SELECT column_name, data_type, character_maximum_length, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'project_git_branchs' 
                ORDER BY ordinal_position
            """))
            
            for row in result.fetchall():
                print(f"  {row[0]}: {row[1]}" + (f"({row[2]})" if row[2] else "") + f" {'NULL' if row[3] == 'YES' else 'NOT NULL'}")
            
            # Check projects table schema
            print("\n📋 Checking projects table schema:")
            result = session.execute(text("""
                SELECT column_name, data_type, character_maximum_length, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'projects' 
                ORDER BY ordinal_position
            """))
            
            for row in result.fetchall():
                print(f"  {row[0]}: {row[1]}" + (f"({row[2]})" if row[2] else "") + f" {'NULL' if row[3] == 'YES' else 'NOT NULL'}")
            
            # Check tasks table schema  
            print("\n📋 Checking tasks table schema:")
            result = session.execute(text("""
                SELECT column_name, data_type, character_maximum_length, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'tasks' 
                ORDER BY ordinal_position
            """))
            
            for row in result.fetchall():
                print(f"  {row[0]}: {row[1]}" + (f"({row[2]})" if row[2] else "") + f" {'NULL' if row[3] == 'YES' else 'NOT NULL'}")
                
        return True
        
    except Exception as e:
        print(f"❌ Failed to check schema: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Database Schema Checker")
    print("=" * 50)
    
    success = check_table_schema()
    
    if success:
        print("\n✅ Schema check completed")
        sys.exit(0)
    else:
        print("\n💥 Schema check failed")
        sys.exit(1)