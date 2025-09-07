#!/usr/bin/env python3
"""
Comprehensive Database Manager for DhafnckMCP
Handles Supabase connection, migration, and data management
"""

import os
import sys
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
from datetime import datetime
import argparse

# Load environment variables
load_dotenv()

# Database connection configuration (uses existing working setup)
DATABASE_URL = os.getenv('DATABASE_URL')  # Primary connection method
SUPABASE_DATABASE_URL = os.getenv('SUPABASE_DATABASE_URL')  # Alternative
DB_HOST = os.getenv('SUPABASE_DB_HOST')
DB_PORT = os.getenv('SUPABASE_DB_PORT', '5432')
DB_NAME = os.getenv('SUPABASE_DB_NAME', 'postgres')
DB_USER = os.getenv('SUPABASE_DB_USER', 'postgres')
DB_PASSWORD = os.getenv('SUPABASE_DB_PASSWORD')


class DatabaseManager:
    """Manages Supabase database operations"""
    
    def __init__(self):
        self.conn = None
        self.connect()
    
    def connect(self):
        """Create a connection to Supabase database using best available method"""
        try:
            # Try DATABASE_URL first (primary method)
            if DATABASE_URL:
                print("📡 Connecting using DATABASE_URL...")
                self.conn = psycopg2.connect(DATABASE_URL)
                print("✅ Connected via DATABASE_URL")
            # Try SUPABASE_DATABASE_URL second
            elif SUPABASE_DATABASE_URL:
                print("📡 Connecting using SUPABASE_DATABASE_URL...")
                self.conn = psycopg2.connect(SUPABASE_DATABASE_URL)
                print("✅ Connected via SUPABASE_DATABASE_URL")
            # Construct from components
            elif DB_HOST and DB_USER and DB_PASSWORD:
                print("📡 Connecting using individual components...")
                self.conn = psycopg2.connect(
                    host=DB_HOST,
                    port=DB_PORT,
                    database=DB_NAME,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    sslmode='require'
                )
                print(f"✅ Connected to {DB_HOST}/{DB_NAME}")
            else:
                raise Exception("No valid database configuration found. Check .env file.")
                
            # Test the connection
            cursor = self.conn.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            print(f"📊 Database version: {version.split(',')[0]}")
            cursor.close()
            
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            print("\n🔧 Troubleshooting:")
            print("1. Check that DATABASE_URL is uncommented in .env")
            print("2. Verify Supabase credentials are correct")
            print("3. Ensure Docker containers are running")
            sys.exit(1)
    
    def clean_database(self, force=False):
        """Clean all data from database (development mode)"""
        print("\n🗑️  DATABASE CLEANUP")
        print("=" * 60)
        
        # Get all tables
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename NOT LIKE 'pg_%' 
            AND tablename NOT IN ('schema_migrations', 'migrations')
            ORDER BY tablename
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        if not tables:
            print("ℹ️  No tables found to clean")
            return
        
        print(f"Found {len(tables)} tables to clean:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  • {table}: {count} rows")
        
        if not force:
            confirm = input("\n⚠️  Delete all data? Type 'YES' to confirm: ")
            if confirm != 'YES':
                print("❌ Cancelled")
                return
        
        # Simpler approach: disable FK checks and truncate
        print("\n🔥 Cleaning database...")
        try:
            # Disable foreign key checks
            cursor.execute("SET session_replication_role = replica")
            
            # Drop unique constraints first (they create dependent indexes)
            cursor.execute("""
                DO $$
                DECLARE r RECORD;
                BEGIN
                    FOR r IN 
                        SELECT conname, conrelid::regclass AS table_name
                        FROM pg_constraint 
                        WHERE contype = 'u' 
                        AND connamespace = 'public'::regnamespace
                    LOOP
                        EXECUTE format('ALTER TABLE %s DROP CONSTRAINT IF EXISTS %I CASCADE', 
                            r.table_name, r.conname);
                    END LOOP;
                END $$;
            """)
            
            # Drop foreign key constraints
            cursor.execute("""
                DO $$
                DECLARE r RECORD;
                BEGIN
                    FOR r IN 
                        SELECT conname, conrelid::regclass AS table_name
                        FROM pg_constraint 
                        WHERE contype = 'f' 
                        AND connamespace = 'public'::regnamespace
                    LOOP
                        EXECUTE format('ALTER TABLE %s DROP CONSTRAINT IF EXISTS %I CASCADE', 
                            r.table_name, r.conname);
                    END LOOP;
                END $$;
            """)
            
            # Truncate all tables
            for table in tables:
                cursor.execute(f"TRUNCATE TABLE {table} CASCADE")
                print(f"  ✅ Cleaned: {table}")
            
            # Re-enable foreign key checks
            cursor.execute("SET session_replication_role = DEFAULT")
            
            self.conn.commit()
            print("\n✅ Database cleaned successfully!")
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error cleaning database: {e}")
            raise
        finally:
            cursor.close()
    
    def init_schema(self):
        """Initialize fresh database schema"""
        print("\n🏗️  SCHEMA INITIALIZATION")
        print("=" * 60)
        
        migration_file = "dhafnck_mcp_main/database/migrations/000_complete_database_wipe_and_fresh_init.sql"
        
        # Check if migration file exists
        if not os.path.exists(migration_file):
            print(f"❌ Migration file not found: {migration_file}")
            print("Creating basic schema instead...")
            self._create_basic_schema()
            return
        
        # Read and execute migration
        print(f"📄 Loading migration: {migration_file}")
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        cursor = self.conn.cursor()
        try:
            print("🚀 Executing migration...")
            cursor.execute(migration_sql)
            self.conn.commit()
            print("✅ Schema initialized successfully!")
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Migration failed: {e}")
            print("\nTrying basic schema creation...")
            self._create_basic_schema()
        finally:
            cursor.close()
    
    def _create_basic_schema(self):
        """Create basic schema if migration fails"""
        cursor = self.conn.cursor()
        try:
            # Create essential tables
            tables = [
                """
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    user_id UUID REFERENCES users(id),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS git_branches (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    git_branch_id UUID REFERENCES git_branches(id) ON DELETE CASCADE,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    status VARCHAR(50) DEFAULT 'todo',
                    priority VARCHAR(50) DEFAULT 'medium',
                    user_id UUID REFERENCES users(id),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS global_contexts (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id),
                    organization_id UUID,
                    autonomous_rules JSONB DEFAULT '{}',
                    security_policies JSONB DEFAULT '{}',
                    coding_standards JSONB DEFAULT '{}',
                    workflow_templates JSONB DEFAULT '{}',
                    delegation_rules JSONB DEFAULT '{}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    version INTEGER DEFAULT 1,
                    UNIQUE(user_id)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS project_contexts (
                    id UUID PRIMARY KEY,
                    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
                    data JSONB DEFAULT '{}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
                """
            ]
            
            for table_sql in tables:
                cursor.execute(table_sql)
                
            # Create indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_tasks_git_branch_id ON tasks(git_branch_id)",
                "CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_global_contexts_user_id ON global_contexts(user_id)"
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
            
            self.conn.commit()
            print("✅ Basic schema created successfully!")
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Failed to create basic schema: {e}")
            raise
        finally:
            cursor.close()
    
    def verify_setup(self):
        """Verify database setup and connection"""
        print("\n🔍 VERIFICATION")
        print("=" * 60)
        
        cursor = self.conn.cursor()
        
        # Check tables
        cursor.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            ORDER BY tablename
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"📋 Tables ({len(tables)}):")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  • {table}: {count} rows")
        
        # Check constraints
        cursor.execute("""
            SELECT conname, conrelid::regclass 
            FROM pg_constraint 
            WHERE contype = 'f' 
            AND connamespace = 'public'::regnamespace
            LIMIT 5
        """)
        constraints = cursor.fetchall()
        
        print(f"\n🔗 Foreign Keys ({len(constraints)} shown):")
        for constraint, table in constraints[:5]:
            print(f"  • {table}: {constraint}")
        
        cursor.close()
        print("\n✅ Database setup verified!")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("🔌 Database connection closed")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='DhafnckMCP Database Manager')
    parser.add_argument('action', choices=['clean', 'init', 'reset', 'verify'],
                        help='Action to perform')
    parser.add_argument('--force', action='store_true',
                        help='Skip confirmation prompts')
    
    args = parser.parse_args()
    
    print("\n🚀 DHAFNCKMCP DATABASE MANAGER")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Action: {args.action}")
    print()
    
    # Create database manager
    db = DatabaseManager()
    
    try:
        if args.action == 'clean':
            db.clean_database(force=args.force)
        elif args.action == 'init':
            db.init_schema()
        elif args.action == 'reset':
            db.clean_database(force=args.force)
            db.init_schema()
        elif args.action == 'verify':
            db.verify_setup()
        
        print("\n🎉 Operation completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Operation failed: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    # If no arguments provided, show help
    if len(sys.argv) == 1:
        print("Usage: python database_manager.py [action]")
        print("\nActions:")
        print("  clean   - Remove all data from database")
        print("  init    - Initialize fresh schema")
        print("  reset   - Clean and reinitialize (fresh start)")
        print("  verify  - Check database setup")
        print("\nOptions:")
        print("  --force - Skip confirmation prompts")
        print("\nExample:")
        print("  python database_manager.py reset --force")
    else:
        main()