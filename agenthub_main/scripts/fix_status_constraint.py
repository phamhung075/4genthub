#!/usr/bin/env python3
"""
Fix Status Constraint

This script updates the database constraint to allow both enum names and values.
"""

import os
import logging
import psycopg2

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL from environment variables."""
    return os.getenv("DATABASE_URL")

def fix_status_constraint():
    """Update the status constraint to allow both enum names and values."""
    database_url = get_database_url()
    if not database_url:
        logger.error("DATABASE_URL not found in environment variables")
        return False
    
    logger.info("Connecting to database...")
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        logger.info("Updating status constraint...")
        
        # Drop the existing constraint
        cursor.execute("""
            ALTER TABLE users DROP CONSTRAINT IF EXISTS check_valid_status;
        """)
        
        # Add updated constraint that allows both enum names and values
        cursor.execute("""
            ALTER TABLE users ADD CONSTRAINT check_valid_status 
            CHECK (status IN (
                'active', 'inactive', 'suspended', 'pending_verification',
                'ACTIVE', 'INACTIVE', 'SUSPENDED', 'PENDING_VERIFICATION'
            ));
        """)
        
        logger.info("✅ Status constraint updated successfully!")
        
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
    logger.info("🔧 Fixing status constraint in Supabase")
    
    success = fix_status_constraint()
    
    if success:
        logger.info("🎉 Status constraint fixed!")
        logger.info("🔧 User registration should now work")
    else:
        logger.error("💥 Failed to fix constraint!")