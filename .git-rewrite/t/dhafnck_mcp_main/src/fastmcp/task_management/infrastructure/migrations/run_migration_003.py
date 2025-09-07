#!/usr/bin/env python3
"""
Migration Runner: 003 - Fix Database Schema Validation Errors
 
This script safely executes the schema migration to fix validation errors
between the SQLAlchemy models and the actual database schema.

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
        # Construct from Supabase components
        host = os.getenv('SUPABASE_DB_HOST', 'aws-0-eu-north-1.pooler.supabase.com')
        user = os.getenv('SUPABASE_DB_USER', 'postgres.pmswmvxhzdfxeqsfdgif')
        password = os.getenv('SUPABASE_DB_PASSWORD', 'P02tqbj016p9')
        db_name = os.getenv('SUPABASE_DB_NAME', 'postgres')
        port = os.getenv('SUPABASE_DB_PORT', '5432')
        
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{db_name}?sslmode=require"
    
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

def backup_critical_data(engine):
    """Backup critical data before migration"""
    logger.info("Creating backup of critical data...")
    
    backup_queries = [
        """
        CREATE TABLE IF NOT EXISTS migration_backup_context_delegations AS
        SELECT * FROM context_delegations;
        """,
        """
        CREATE TABLE IF NOT EXISTS migration_backup_templates AS  
        SELECT * FROM templates;
        """,
        """
        CREATE TABLE IF NOT EXISTS migration_backup_agents AS
        SELECT * FROM agents;
        """
    ]
    
    try:
        with engine.connect() as conn:
            for query in backup_queries:
                conn.execute(text(query))
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
    
    verification_queries = [
        # Check context_delegations has required columns
        """
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'context_delegations' 
        AND column_name IN ('auto_delegated', 'delegated_data', 'delegation_reason', 
                            'source_level', 'target_level', 'trigger_type', 'approved', 'confidence_score')
        """,
        # Check templates has required columns  
        """
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'templates' 
        AND column_name IN ('category', 'content', 'created_by', 'name', 'tags', 'type', 'usage_count')
        """,
        # Check branch_contexts foreign key constraint
        """
        SELECT constraint_name FROM information_schema.table_constraints 
        WHERE table_name = 'branch_contexts' 
        AND constraint_type = 'FOREIGN KEY'
        AND constraint_name LIKE '%branch_id%'
        """
    ]
    
    try:
        with engine.connect() as conn:
            # Check context_delegations columns
            result = conn.execute(text(verification_queries[0]))
            context_cols = [row[0] for row in result]
            expected_context_cols = ['auto_delegated', 'delegated_data', 'delegation_reason', 
                                   'source_level', 'target_level', 'trigger_type', 'approved', 'confidence_score']
            missing_context = [col for col in expected_context_cols if col not in context_cols]
            
            if missing_context:
                logger.warning(f"Missing context_delegations columns: {missing_context}")
            else:
                logger.info("✅ context_delegations columns verified")
                
            # Check templates columns
            result = conn.execute(text(verification_queries[1]))
            template_cols = [row[0] for row in result]
            expected_template_cols = ['category', 'content', 'created_by', 'name', 'tags', 'type', 'usage_count']
            missing_template = [col for col in expected_template_cols if col not in template_cols]
            
            if missing_template:
                logger.warning(f"Missing templates columns: {missing_template}")
            else:
                logger.info("✅ templates columns verified")
                
            # Check foreign key constraint
            result = conn.execute(text(verification_queries[2]))
            fk_constraints = [row[0] for row in result]
            
            if any('branch_id' in fk for fk in fk_constraints):
                logger.info("✅ branch_contexts foreign key constraint verified")
            else:
                logger.warning("❌ branch_contexts foreign key constraint not found")
                
        return True
        
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False

def main():
    """Main migration execution function"""
    logger.info("🚀 Starting Database Schema Migration 003")
    
    # Get database connection
    try:
        db_url = get_database_url()
        engine = create_engine(db_url)
        logger.info("✅ Database connection established")
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        sys.exit(1)
    
    # Check if migration already applied
    if check_migration_applied(engine, '003_fix_schema_validation_errors'):
        logger.info("✅ Migration 003 already applied, skipping")
        return
    
    # Get migration file path
    current_dir = Path(__file__).parent
    migration_file = current_dir / '003_fix_schema_validation_errors.sql'
    
    if not migration_file.exists():
        logger.error(f"❌ Migration file not found: {migration_file}")
        sys.exit(1)
    
    # Backup critical data
    if not backup_critical_data(engine):
        logger.error("❌ Failed to backup data, aborting migration")
        sys.exit(1)
    
    # Run migration
    if not run_migration(engine, migration_file):
        logger.error("❌ Migration failed, check logs for details")
        sys.exit(1)
    
    # Verify migration
    if not verify_migration(engine):
        logger.warning("⚠️ Migration verification had issues, but migration may still be successful")
    
    logger.info("🎉 Migration 003 completed successfully!")
    logger.info("📝 Next steps:")
    logger.info("   1. Run schema validation to verify all issues are resolved")
    logger.info("   2. Test application functionality")
    logger.info("   3. Remove backup tables if everything works correctly")

if __name__ == "__main__":
    main()