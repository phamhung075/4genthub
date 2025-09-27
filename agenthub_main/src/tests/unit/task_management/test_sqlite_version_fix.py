#!/usr/bin/env python3
"""
Test to verify the database connection works properly.

This test validates that the database_config.py can create a proper database
connection and execute queries successfully.
"""

import os
import sys
from pathlib import Path

# Add the project to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import after setting environment
from fastmcp.task_management.infrastructure.database.database_config import get_db_config
from sqlalchemy import text

def test_sqlite_connection():
    """Test that database connection works properly"""
    print("🧪 Testing database connection...")
    
    try:
        # 1. Get database configuration
        db = get_db_config()
        print("✅ Database config created successfully")
        
        # 2. Get database info
        db_info = db.get_database_info()
        print(f"Database type: {db_info['type']}")
        # Accept any valid database type (sqlite, postgresql, etc.)
        assert db_info['type'] in ['sqlite', 'postgresql'], f"Unexpected database type: {db_info['type']}"
        
        # 3. Test that we can get a session (this would fail with version() error before fix)
        with db.get_session() as session:
            print("✅ Database session created successfully")
            
            # 4. Test that we can execute a simple query
            result = session.execute(text("SELECT 1 as test")).fetchone()
            assert result[0] == 1, "Simple query failed"
            print("✅ Simple query executed successfully")
        
        print("✅ All database connection tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    print("🚀 Database Connection Test")
    print("=" * 50)
    
    try:
        test_sqlite_connection()
        print("\n🎉 SUCCESS: Database connection is working properly!")
        print("The database_config.py can successfully create connections and execute queries")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 FAILURE: Database connection error - {e}")
        sys.exit(1)