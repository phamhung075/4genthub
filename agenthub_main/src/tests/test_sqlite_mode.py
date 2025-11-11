#!/usr/bin/env python
"""
DEPRECATED: SQLite mode test

SQLite is no longer supported as a DATABASE_TYPE.
Only 'postgresql' and 'supabase' are valid DATABASE_TYPE values.

This test file is kept for historical reference but will always skip.
For database tests, use PostgreSQL-based tests instead.
"""

import os
import sys

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

@pytest.mark.skip(reason="SQLite is no longer supported - use PostgreSQL tests instead")
def test_sqlite_configuration_deprecated():
    """DEPRECATED: SQLite is no longer a supported DATABASE_TYPE"""
    pytest.skip("SQLite support removed - DATABASE_TYPE must be 'postgresql' or 'supabase'")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("⚠️  DEPRECATED: SQLite Test Mode")
    print("="*60)
    print("\n❌ SQLite is no longer supported as a DATABASE_TYPE.")
    print("   Valid types: 'postgresql' or 'supabase'")
    print("\n   Use PostgreSQL-based tests instead.")
    print("="*60 + "\n")
    sys.exit(1)