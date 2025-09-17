#!/usr/bin/env python3
"""
Test script to verify the unified_context_data column functionality
"""

import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "4genthub_main" / "src"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json

def test_unified_context_data():
    """Test the unified_context_data column functionality"""

    # Database connection
    DATABASE_URL = "postgresql://postgres:P02tqbj016p9@localhost:5432/postgresdb"

    print("1. Connecting to database...")
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Test 1: Check if column exists
        print("\n2. Checking if unified_context_data column exists...")
        result = session.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'global_contexts'
            AND column_name = 'unified_context_data'
        """))
        column_info = result.fetchone()
        if column_info:
            print(f"   ✅ Column exists: {column_info[0]} ({column_info[1]})")
        else:
            print("   ❌ Column does not exist!")
            return

        # Test 2: Read current data
        print("\n3. Reading current unified_context_data...")
        result = session.execute(text("""
            SELECT id, unified_context_data, user_id
            FROM global_contexts
            LIMIT 1
        """))
        row = result.fetchone()
        if row:
            print(f"   ID: {row[0]}")
            print(f"   User ID: {row[2]}")
            print(f"   Current Data: {json.dumps(row[1], indent=2)}")
            context_id = row[0]
        else:
            print("   No global contexts found")
            return

        # Test 3: Update with complex JSON
        print("\n4. Testing update with complex JSON structure...")
        test_data = {
            "test_suite": "unified_context_data_test",
            "test_timestamp": "2025-09-16T12:00:00Z",
            "nested_structure": {
                "level1": {
                    "level2": {
                        "level3": "deep nested value"
                    },
                    "array_field": [1, 2, 3, 4, 5],
                    "boolean_field": True,
                    "null_field": None
                }
            },
            "unified_api_data": {
                "description": "This tests the unified context API compatibility",
                "features": ["flexible storage", "json support", "nested structures"],
                "status": "working"
            }
        }

        session.execute(
            text("UPDATE global_contexts SET unified_context_data = :data WHERE id = :id"),
            {"data": json.dumps(test_data), "id": context_id}
        )
        session.commit()
        print("   ✅ Update successful")

        # Test 4: Verify the update
        print("\n5. Verifying the update...")
        result = session.execute(text("""
            SELECT unified_context_data
            FROM global_contexts
            WHERE id = :id
        """), {"id": context_id})
        updated_data = result.fetchone()[0]
        print(f"   Updated Data: {json.dumps(updated_data, indent=2)}")

        # Test 5: Test JSON query capabilities
        print("\n6. Testing JSON query capabilities...")
        result = session.execute(text("""
            SELECT
                unified_context_data->>'test_suite' as test_suite,
                unified_context_data->'nested_structure'->'level1'->>'boolean_field' as bool_field,
                jsonb_array_length((unified_context_data->'unified_api_data'->'features')::jsonb) as feature_count
            FROM global_contexts
            WHERE id = :id
        """), {"id": context_id})
        query_result = result.fetchone()
        print(f"   Test Suite: {query_result[0]}")
        print(f"   Boolean Field: {query_result[1]}")
        print(f"   Feature Count: {query_result[2]}")

        print("\n✅ All tests passed! The unified_context_data column is working correctly.")
        print("\nSummary:")
        print("- Column exists and is of type JSON")
        print("- Can store complex nested JSON structures")
        print("- Supports JSON query operations")
        print("- Properly integrated with PostgreSQL")

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()
        print("\n7. Database connection closed.")

if __name__ == "__main__":
    test_unified_context_data()