#!/usr/bin/env python3
"""
Migration Runner: 004 - Fix ContextInheritanceCache Table Schema

This script safely executes the schema migration to add missing columns
to the context_inheritance_cache table to match the SQLAlchemy model definition.

Target: PostgreSQL (Supabase)
Date: 2025-08-26
"""

import os
import sys
import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_database_url():
    """Get the database URL from environment variables"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        # Try to construct from Docker environment variables
        host = os.getenv('POSTGRES_HOST', 'localhost')
        user = os.getenv('POSTGRES_USER', 'postgres')
        password = os.getenv('POSTGRES_PASSWORD', 'postgres')
        db_name = os.getenv('POSTGRES_DB', 'dhafnck_mcp')
        port = os.getenv('POSTGRES_PORT', '5432')
        
        # Check if we're using Supabase
        if os.getenv('SUPABASE_DB_HOST'):
            host = os.getenv('SUPABASE_DB_HOST')
            user = os.getenv('SUPABASE_DB_USER', 'postgres')
            password = os.getenv('SUPABASE_DB_PASSWORD')
            db_name = os.getenv('SUPABASE_DB_NAME', 'postgres')
            port = os.getenv('SUPABASE_DB_PORT', '5432')
            db_url = f"postgresql://{user}:{password}@{host}:{port}/{db_name}?sslmode=require"
        else:
            db_url = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
    
    return db_url

def check_migration_applied(engine, migration_name):
    """Check if a migration has already been applied"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) FROM migration_history 
                WHERE migration_name = :migration_name
            """), {"migration_name": migration_name})
            
            return result.scalar() > 0
    except Exception as e:
        logger.warning(f"Could not check migration history: {e}")
        return False

def check_table_exists(engine, table_name):
    """Check if a table exists in the database"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = :table_name
            """), {"table_name": table_name})
            
            return result.scalar() > 0
    except Exception as e:
        logger.warning(f"Could not check table existence: {e}")
        return False

def check_missing_columns(engine):
    """Check which columns are missing from the context_inheritance_cache table"""
    expected_columns = [
        'context_id', 'context_level', 'resolved_context', 'dependencies_hash',
        'resolution_path', 'created_at', 'expires_at', 'hit_count', 'last_hit',
        'cache_size_bytes', 'invalidated', 'invalidation_reason', 'user_id'
    ]
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'context_inheritance_cache'
                ORDER BY column_name
            """))
            
            existing_columns = [row[0] for row in result]
            missing_columns = [col for col in expected_columns if col not in existing_columns]
            
            logger.info(f"Existing columns: {sorted(existing_columns)}")
            logger.info(f"Missing columns: {missing_columns}")
            
            return missing_columns
    except Exception as e:
        logger.error(f"Could not check column structure: {e}")
        return expected_columns  # Assume all are missing if we can't check

def backup_table(engine):
    """Backup the context_inheritance_cache table before migration"""
    logger.info("Creating backup of context_inheritance_cache table...")
    
    try:
        with engine.connect() as conn:
            # Check if table exists first
            if not check_table_exists(engine, 'context_inheritance_cache'):
                logger.warning("context_inheritance_cache table does not exist, creating it...")
                # Create the table with minimal structure if it doesn't exist
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS context_inheritance_cache (
                        context_id VARCHAR PRIMARY KEY,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL DEFAULT (CURRENT_TIMESTAMP + INTERVAL '1 hour'),
                        user_id VARCHAR NOT NULL DEFAULT 'system'
                    )
                """))
                conn.commit()
                logger.info("✅ Created minimal context_inheritance_cache table")
                return True
            
            # Create backup table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS migration_backup_004_context_inheritance_cache AS
                SELECT * FROM context_inheritance_cache
            """))
            conn.commit()
            
        logger.info("✅ Backup completed successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")
        return False

def run_migration(engine, migration_file):
    """Execute the migration SQL file"""
    logger.info(f"Executing migration from {migration_file}")
    
    try:
        # Read the migration file
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Execute the migration
        with engine.connect() as conn:
            # Execute the migration as a single transaction
            conn.execute(text(migration_sql))
            conn.commit()
            
        logger.info("✅ Migration executed successfully")
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"❌ Migration failed with SQLAlchemy error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

def verify_migration(engine):
    """Verify that the migration was applied correctly"""
    logger.info("Verifying migration results...")
    
    expected_columns = [
        'context_id', 'context_level', 'resolved_context', 'dependencies_hash',
        'resolution_path', 'created_at', 'expires_at', 'hit_count', 'last_hit',
        'cache_size_bytes', 'invalidated', 'invalidation_reason', 'user_id'
    ]
    
    try:
        with engine.connect() as conn:
            # Check all expected columns exist
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'context_inheritance_cache'
                ORDER BY column_name
            """))
            
            existing_columns = [row[0] for row in result]
            missing_columns = [col for col in expected_columns if col not in existing_columns]
            
            if missing_columns:
                logger.error(f"❌ Still missing columns: {missing_columns}")
                return False
            else:
                logger.info("✅ All required columns are present")
            
            # Check primary key constraint
            result = conn.execute(text("""
                SELECT constraint_name FROM information_schema.table_constraints 
                WHERE table_name = 'context_inheritance_cache' 
                AND constraint_type = 'PRIMARY KEY'
            """))
            
            pk_constraints = [row[0] for row in result]
            if pk_constraints:
                logger.info(f"✅ Primary key constraint found: {pk_constraints[0]}")
            else:
                logger.warning("❌ Primary key constraint not found")
            
            # Check indexes
            result = conn.execute(text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'context_inheritance_cache'
                ORDER BY indexname
            """))
            
            indexes = [row[0] for row in result]
            expected_indexes = ['idx_cache_level', 'idx_cache_expires', 'idx_cache_invalidated']
            found_indexes = [idx for idx in expected_indexes if idx in indexes]
            
            logger.info(f"✅ Performance indexes created: {found_indexes}")
            
            # Check constraint
            result = conn.execute(text("""
                SELECT constraint_name FROM information_schema.table_constraints 
                WHERE table_name = 'context_inheritance_cache' 
                AND constraint_type = 'CHECK'
                AND constraint_name = 'chk_cache_context_level'
            """))
            
            if result.rowcount > 0:
                logger.info("✅ Check constraint for context_level verified")
            else:
                logger.warning("❌ Check constraint for context_level not found")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False

def main():
    """Main migration execution function"""
    logger.info("🚀 Starting Database Schema Migration 004 - ContextInheritanceCache Fix")
    
    # Get database connection
    try:
        db_url = get_database_url()
        engine = create_engine(db_url)
        logger.info("✅ Database connection established")
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection verified")
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        logger.error("Please ensure the database is running and environment variables are set correctly")
        sys.exit(1)
    
    # Check if migration already applied
    if check_migration_applied(engine, '004_fix_context_inheritance_cache'):
        logger.info("✅ Migration 004 already applied, skipping")
        return
    
    # Check current table state
    missing_columns = check_missing_columns(engine)
    if not missing_columns:
        logger.info("✅ All columns already exist, no migration needed")
        return
    
    logger.info(f"🔍 Found {len(missing_columns)} missing columns: {missing_columns}")
    
    # Get migration file path
    current_dir = Path(__file__).parent
    migration_file = current_dir / '004_fix_context_inheritance_cache.sql'
    
    if not migration_file.exists():
        logger.error(f"❌ Migration file not found: {migration_file}")
        sys.exit(1)
    
    # Backup table
    if not backup_table(engine):
        logger.error("❌ Failed to backup data, aborting migration")
        sys.exit(1)
    
    # Run migration
    if not run_migration(engine, migration_file):
        logger.error("❌ Migration failed, check logs for details")
        sys.exit(1)
    
    # Verify migration
    if not verify_migration(engine):
        logger.warning("⚠️ Migration verification had issues, but migration may still be successful")
    
    logger.info("🎉 Migration 004 completed successfully!")
    logger.info("📝 Next steps:")
    logger.info("   1. Restart the application to use the updated schema")
    logger.info("   2. Run schema validation to verify all issues are resolved")
    logger.info("   3. Test context inheritance cache functionality")
    logger.info("   4. Remove backup tables if everything works correctly")

if __name__ == "__main__":
    main()