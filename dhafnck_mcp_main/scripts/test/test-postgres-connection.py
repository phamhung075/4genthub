#!/usr/bin/env python3
"""Test PostgreSQL connection for production setup"""

import os
import sys
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_connection():
    """Test PostgreSQL connection with production settings."""
    
    # Get configuration from environment
    db_host = os.getenv("DATABASE_HOST", "localhost")
    db_port = os.getenv("DATABASE_PORT", "5432")
    db_name = os.getenv("DATABASE_NAME", "dhafnck_mcp_prod")
    db_user = os.getenv("DATABASE_USER", "dhafnck_user")
    db_password = os.getenv("DATABASE_PASSWORD", "ChangeThisSecurePassword2025!")
    
    print(f"Testing PostgreSQL connection...")
    print(f"  Host: {db_host}:{db_port}")
    print(f"  Database: {db_name}")
    print(f"  User: {db_user}")
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password
        )
        
        print("✅ Connected successfully!")
        
        # Test query
        cur = conn.cursor()
        
        # Get version
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
        print(f"\nPostgreSQL Version:\n  {version}")
        
        # Check extensions
        cur.execute("SELECT extname FROM pg_extension WHERE extname IN ('uuid-ossp', 'pgcrypto')")
        extensions = cur.fetchall()
        print(f"\nInstalled Extensions:")
        for ext in extensions:
            print(f"  - {ext[0]}")
        
        # Check tables
        cur.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
        """)
        table_count = cur.fetchone()[0]
        print(f"\nTables in public schema: {table_count}")
        
        # Test UUID generation
        cur.execute("SELECT uuid_generate_v4()")
        test_uuid = cur.fetchone()[0]
        print(f"\nUUID generation test: {test_uuid}")
        
        cur.close()
        conn.close()
        
        print("\n✅ All tests passed! PostgreSQL is properly configured.")
        return True
        
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)