#!/usr/bin/env python3
"""
Fresh Database Migration Script
===============================

Executes the complete database wipe and fresh initialization for clean development setup.

Usage:
    python run_fresh_migration.py [--confirm] [--supabase] [--local]
    
Arguments:
    --confirm: Skip confirmation prompt (DANGEROUS - auto-confirms wipe)
    --supabase: Run against Supabase database
    --local: Run against local PostgreSQL database
    
Environment Variables:
    DATABASE_URL: Full database connection string
    SUPABASE_DB_URL: Supabase database connection string
    LOCAL_DB_URL: Local database connection string
"""

import os
import sys
import argparse
import psycopg2
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse


def confirm_wipe(database_info: dict) -> bool:
    """Confirm database wipe with user"""
    print("\n" + "="*60)
    print("⚠️  EXTREME WARNING: COMPLETE DATABASE WIPE ⚠️")
    print("="*60)
    print(f"Database: {database_info['host']}")
    print(f"Database Name: {database_info['database']}")
    print(f"User: {database_info['user']}")
    print("\nThis will:")
    print("❌ DELETE ALL DATA from every table")
    print("❌ DROP ALL tables, functions, and indexes")  
    print("❌ REMOVE ALL user data and contexts")
    print("✅ CREATE fresh schema with user isolation")
    print("✅ SET UP proper indexes and constraints")
    print("✅ PREPARE for clean development")
    print("\n" + "="*60)
    
    response = input("Type 'WIPE_EVERYTHING' to confirm (anything else cancels): ")
    return response == "WIPE_EVERYTHING"


def parse_database_url(db_url: str) -> dict:
    """Parse database URL into components"""
    parsed = urlparse(db_url)
    return {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'database': parsed.path.lstrip('/'),
        'user': parsed.username,
        'password': parsed.password
    }


def get_migration_file_path() -> Path:
    """Get path to the migration file"""
    script_dir = Path(__file__).parent
    migration_file = script_dir.parent / "migrations" / "000_complete_database_wipe_and_fresh_init.sql"
    
    if not migration_file.exists():
        raise FileNotFoundError(f"Migration file not found: {migration_file}")
    
    return migration_file


def execute_migration(db_config: dict, migration_file: Path) -> bool:
    """Execute the migration file"""
    try:
        # Connect to database
        conn = psycopg2.connect(**db_config)
        conn.autocommit = True
        
        print(f"📡 Connected to {db_config['host']}")
        
        # Read migration file
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        print(f"📄 Loaded migration file: {migration_file.name}")
        
        # Execute migration
        with conn.cursor() as cursor:
            print("🚀 Executing complete database wipe and fresh initialization...")
            cursor.execute(migration_sql)
            
            # Get any notices/output from the migration
            notices = conn.notices
            for notice in notices:
                print(f"📋 {notice.strip()}")
        
        print("✅ Migration completed successfully!")
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()


def verify_migration(db_config: dict) -> bool:
    """Verify the migration was successful"""
    try:
        conn = psycopg2.connect(**db_config)
        
        with conn.cursor() as cursor:
            # Check database status
            cursor.execute("SELECT status, migration_version, notes FROM database_status ORDER BY wiped_at DESC LIMIT 1")
            status_result = cursor.fetchone()
            
            if status_result:
                status, version, notes = status_result
                print(f"📊 Database Status: {status}")
                print(f"📦 Migration Version: {version}")
                print(f"📝 Notes: {notes}")
            
            # Count tables
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """)
            table_count = cursor.fetchone()[0]
            
            # Count indexes
            cursor.execute("SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public'")
            index_count = cursor.fetchone()[0]
            
            print(f"📋 Tables: {table_count}")
            print(f"🔍 Indexes: {index_count}")
            
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Verification error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()


def main():
    parser = argparse.ArgumentParser(description="Execute fresh database migration")
    parser.add_argument("--confirm", action="store_true", 
                       help="Skip confirmation prompt (DANGEROUS)")
    parser.add_argument("--supabase", action="store_true", 
                       help="Use Supabase database")
    parser.add_argument("--local", action="store_true", 
                       help="Use local database") 
    
    args = parser.parse_args()
    
    # Determine database URL
    if args.supabase:
        db_url = os.getenv("SUPABASE_DB_URL")
        if not db_url:
            print("❌ SUPABASE_DB_URL environment variable not set")
            sys.exit(1)
    elif args.local:
        db_url = os.getenv("LOCAL_DB_URL", "postgresql://postgres:postgres@localhost:5432/agenthub")
    else:
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print("❌ DATABASE_URL environment variable not set")
            print("Use --supabase or --local flag, or set DATABASE_URL")
            sys.exit(1)
    
    # Parse database configuration
    try:
        db_config = parse_database_url(db_url)
    except Exception as e:
        print(f"❌ Invalid database URL: {e}")
        sys.exit(1)
    
    # Confirm wipe unless --confirm flag
    if not args.confirm:
        if not confirm_wipe(db_config):
            print("❌ Migration cancelled")
            sys.exit(0)
    
    # Get migration file
    try:
        migration_file = get_migration_file_path()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    
    # Execute migration
    print("\n🚀 Starting fresh database migration...")
    start_time = datetime.now()
    
    success = execute_migration(db_config, migration_file)
    
    if success:
        print("\n🔍 Verifying migration...")
        verify_migration(db_config)
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n✅ Fresh migration completed in {duration.total_seconds():.2f} seconds")
        print("🚀 Database is now ready for clean development!")
        print("\n📋 Next steps:")
        print("1. Test user registration through frontend")
        print("2. Create sample projects and tasks")  
        print("3. Verify MCP tools functionality")
        print("4. Run integration tests")
    else:
        print("❌ Migration failed - check logs above")
        sys.exit(1)


if __name__ == "__main__":
    main()