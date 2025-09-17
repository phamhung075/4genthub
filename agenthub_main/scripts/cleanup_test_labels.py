#!/usr/bin/env python3
"""
Cleanup script to fix label schema in test databases
"""
import sqlite3
import os
import glob
from pathlib import Path

def fix_label_schema(db_path):
    """Fix label schema in a database"""
    print(f"Fixing {db_path}...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if old schema exists
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name='task_labels'
        """)
        result = cursor.fetchone()
        
        if result and 'label TEXT' in result[0]:
            print(f"  Found old schema in {db_path}, applying fix...")
            
            # Apply the migration
            migration_path = Path(__file__).parent.parent / "database" / "migrations" / "003_fix_label_schema_conflict.sql"
            
            if migration_path.exists():
                with open(migration_path, 'r') as f:
                    migration_sql = f.read()
                    conn.executescript(migration_sql)
                print(f"  ✅ Fixed {db_path}")
            else:
                print(f"  ❌ Migration file not found")
        else:
            print(f"  ✓ Schema already correct")
            
        conn.close()
        
    except Exception as e:
        print(f"  ❌ Error: {e}")

def main():
    """Fix all test databases"""
    project_root = Path(__file__).parent.parent
    
    # Find all test databases
    test_dbs = []
    test_dbs.extend(glob.glob(str(project_root / "**" / "*test*.db"), recursive=True))
    test_dbs.extend(glob.glob(str(project_root / "**" / "test_*.db"), recursive=True))
    test_dbs.extend(glob.glob("/tmp/test_*.db"))
    test_dbs.extend(glob.glob("/tmp/*test*.db"))
    
    # Remove duplicates
    test_dbs = list(set(test_dbs))
    
    print(f"Found {len(test_dbs)} test databases")
    
    for db_path in test_dbs:
        if os.path.exists(db_path):
            fix_label_schema(db_path)

if __name__ == "__main__":
    main()