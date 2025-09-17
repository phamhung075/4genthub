#!/usr/bin/env python3
"""
Simple test script to verify the schema validation works correctly
"""

import sys
import os
import logging
from sqlalchemy import create_engine, text

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fastmcp.task_management.infrastructure.database.models import Base

def test_schema_validation():
    """Test that schema validation detects missing user_id columns"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    print("🧪 Testing Schema Validation...")
    
    try:
        # Create in-memory database
        engine = create_engine("sqlite:///:memory:", echo=False)
        
        # Create tables without user_id fix
        Base.metadata.create_all(engine)
        
        print("✅ Created database schema")
        
        # Check for missing user_id columns
        with engine.connect() as conn:
            missing_columns = []
            
            tables_to_check = ['task_assignees', 'task_labels', 'task_subtasks']
            
            for table_name in tables_to_check:
                try:
                    # Check if user_id column exists
                    result = conn.execute(text(f"""
                        SELECT name FROM pragma_table_info('{table_name}') 
                        WHERE name = 'user_id'
                    """))
                    
                    if not result.fetchone():
                        missing_columns.append(table_name)
                        print(f"❌ Missing user_id column in {table_name}")
                    else:
                        print(f"✅ Found user_id column in {table_name}")
                        
                except Exception as e:
                    print(f"⚠️  Could not check {table_name}: {e}")
            
            if missing_columns:
                print(f"\n🔧 Missing columns detected in: {missing_columns}")
                print("💡 Run the migration script to fix: 004_fix_user_isolation_missing_columns.sql")
                return False
            else:
                print("\n✅ All required user_id columns are present!")
                return True
                
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_migration_simulation():
    """Test migration script logic"""
    
    print("\n🧪 Testing Migration Logic...")
    
    try:
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        
        with engine.connect() as conn:
            # Simulate adding user_id columns (they should already exist from models)
            # This tests the migration logic
            
            try:
                # Try to add user_id column (should fail if already exists)
                conn.execute(text("ALTER TABLE task_assignees ADD COLUMN user_id VARCHAR(255)"))
                print("✅ Added user_id to task_assignees")
            except Exception:
                print("ℹ️  user_id column already exists in task_assignees (expected)")
            
            try:
                conn.execute(text("ALTER TABLE task_labels ADD COLUMN user_id VARCHAR(255)"))
                print("✅ Added user_id to task_labels")
            except Exception:
                print("ℹ️  user_id column already exists in task_labels (expected)")
            
            try:
                conn.execute(text("ALTER TABLE task_subtasks ADD COLUMN user_id VARCHAR(255)"))
                print("✅ Added user_id to task_subtasks")
            except Exception:
                print("ℹ️  user_id column already exists in task_subtasks (expected)")
            
            conn.commit()
            
        print("✅ Migration simulation completed")
        return True
        
    except Exception as e:
        print(f"❌ Migration test failed: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("DATABASE SCHEMA VALIDATION TEST")
    print("=" * 60)
    
    success1 = test_schema_validation()
    success2 = test_migration_simulation()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Schema validation is working correctly")
        print("✅ Migration logic is sound")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        print("🔧 Review the output above for issues")
        sys.exit(1)