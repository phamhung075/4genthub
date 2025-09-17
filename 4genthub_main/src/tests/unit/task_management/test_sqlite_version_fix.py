#!/usr/bin/env python3
"""
Test to verify the SQLite version() function error has been fixed.

This test validates that the database_config.py properly detects SQLite
and uses the correct version query (sqlite_version() instead of version()).
"""

import os
import sys
from pathlib import Path

# Set up environment for SQLite (for testing)
os.environ['DATABASE_TYPE'] = 'sqlite'
os.environ['PYTEST_CURRENT_TEST'] = 'test_sqlite_version_fix.py::test_sqlite_connection'

# Add the project to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import after setting environment
from fastmcp.task_management.infrastructure.database.database_config import get_db_config
from sqlalchemy import text

def test_sqlite_connection():
    """Test that SQLite connection works without version() function error"""
    print("🧪 Testing SQLite connection and version detection...")
    
    try:
        # 1. Get database configuration
        db = get_db_config()
        print("✅ Database config created successfully")
        
        # 2. Verify we're using SQLite
        db_info = db.get_database_info()
        print(f"Database type: {db_info['type']}")
        assert db_info['type'] == 'sqlite', f"Expected sqlite, got {db_info['type']}"
        
        # 3. Test that we can get a session (this would fail with version() error before fix)
        with db.get_session() as session:
            print("✅ Database session created successfully")
            
            # 4. Test that we can execute a simple query
            result = session.execute(text("SELECT 1 as test")).fetchone()
            assert result[0] == 1, "Simple query failed"
            print("✅ Simple query executed successfully")
        
        print("✅ All SQLite connection tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    print("🚀 SQLite Version Function Fix Test")
    print("=" * 50)
    
    try:
        test_sqlite_connection()
        print("\n🎉 SUCCESS: SQLite version() function error is FIXED!")
        print("The database_config.py now properly detects SQLite and uses sqlite_version()")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 FAILURE: SQLite version() function error still needs fixing - {e}")
        sys.exit(1)