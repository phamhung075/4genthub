#!/usr/bin/env python3
"""
Supabase Database Migration Runner

This script connects to Supabase and runs SQL migration files.
Can be used with any migration file by passing the path as an argument.

Usage:
    python run_supabase_migration.py [migration_file_path]
    
Examples:
    python run_supabase_migration.py database/migrations/002_add_authentication_tables.sql
    python run_supabase_migration.py database/migrations/003_add_user_isolation.sql
"""

import os
import sys
import logging
import psycopg2
from pathlib import Path
import argparse

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL from environment variables."""
    # Try direct DATABASE_URL first
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url
    
    # If not found, construct from individual components
    host = os.getenv("DATABASE_HOST")
    port = os.getenv("DATABASE_PORT", "5432")
    user = os.getenv("DATABASE_USER")
    password = os.getenv("DATABASE_PASSWORD")
    dbname = os.getenv("DATABASE_NAME", "postgres")
    
    if host and user and password:
        return f"postgresql://{user}:{password}@{host}:{port}/{dbname}?sslmode=require"
    
    return None

def load_migration_sql(migration_path=None):
    """Load the migration SQL from specified path or default locations."""
    if migration_path:
        # Use the provided migration path
        migration_file = Path(migration_path)
        if not migration_file.is_absolute():
            # Try relative to script location
            migration_file = Path(__file__).parent.parent / migration_path
        
        if migration_file.exists():
            logger.info(f"Found migration file: {migration_file}")
            with open(migration_file, 'r') as f:
                return f.read(), migration_file.name
        else:
            logger.error(f"Migration file not found: {migration_file}")
            return None, None
    
    # Default: Try multiple possible locations for the authentication migration
    possible_paths = [
        Path("/app/002_add_authentication_tables.sql"),  # Copied to container
        Path(__file__).parent.parent / "database" / "migrations" / "002_add_authentication_tables.sql",
        Path("/app/src/database/migrations/002_add_authentication_tables.sql"),
    ]
    
    for migration_file in possible_paths:
        if migration_file.exists():
            logger.info(f"Found migration file: {migration_file}")
            with open(migration_file, 'r') as f:
                return f.read(), migration_file.name
    
    logger.error(f"Migration file not found in any of: {possible_paths}")
    return None, None

def run_migration(migration_path=None):
    """Connect to Supabase and run the specified migration."""
    database_url = get_database_url()
    if not database_url:
        logger.error("DATABASE_URL not found in environment variables")
        return False
    
    logger.info(f"Connecting to database...")
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Load migration SQL
        migration_sql, migration_name = load_migration_sql(migration_path)
        if not migration_sql:
            return False
        
        logger.info(f"Running migration: {migration_name}")
        
        # Execute migration
        cursor.execute(migration_sql)
        
        logger.info(f"✅ Migration {migration_name} completed successfully!")
        
        # Verify tables based on migration type
        if "user_isolation" in str(migration_name).lower() or "003" in str(migration_name):
            # Check for user_id columns in main tables
            cursor.execute("""
                SELECT table_name, column_name
                FROM information_schema.columns 
                WHERE column_name = 'user_id' 
                AND table_schema = 'public'
                AND table_name IN ('tasks', 'projects', 'git_branches', 'agents', 'contexts', 'subtasks', 'task_dependencies', 'cursor_rules')
                ORDER BY table_name;
            """)
            
            columns = cursor.fetchall()
            logger.info(f"✅ Tables with user_id column: {[f'{t[0]}' for t in columns]}")
            
            # Check if user_access_log table was created
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'user_access_log';
            """)
            
            if cursor.fetchone():
                logger.info("✅ user_access_log table created")
                
        elif "authentication" in str(migration_name).lower() or "002" in str(migration_name):
            # Verify authentication tables were created
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('users', 'user_sessions', 'auth_audit_log')
                ORDER BY table_name;
            """)
            
            tables = cursor.fetchall()
            logger.info(f"✅ Created tables: {[table[0] for table in tables]}")
            
            # Check users table structure
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                ORDER BY ordinal_position;
            """)
            
            columns = cursor.fetchall()
            logger.info(f"✅ Users table has {len(columns)} columns")
        else:
            # Generic verification - just show what tables exist
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public';
            """)
            
            count = cursor.fetchone()[0]
            logger.info(f"✅ Database has {count} tables")
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.Error as e:
        logger.error(f"❌ Database error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run Supabase database migrations')
    parser.add_argument('migration_path', nargs='?', default=None,
                        help='Path to the migration SQL file (optional)')
    args = parser.parse_args()
    
    if args.migration_path:
        logger.info(f"🚀 Starting Supabase Migration: {args.migration_path}")
    else:
        logger.info("🚀 Starting Supabase Authentication Migration (default)")
    
    success = run_migration(args.migration_path)
    
    if success:
        logger.info("🎉 Migration completed successfully!")
        if not args.migration_path or "002" in args.migration_path or "authentication" in args.migration_path.lower():
            logger.info("🔧 User registration should now work properly")
        elif "003" in args.migration_path or "user_isolation" in args.migration_path.lower():
            logger.info("🔧 User data isolation is now enabled")
        sys.exit(0)
    else:
        logger.error("💥 Migration failed!")
        sys.exit(1)