#!/usr/bin/env python3
"""
Migration to update api_tokens table to match ORM model.
The ORM is the source of truth for database schema.
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "dhafnck_mcp_prod")
    DB_USER = os.getenv("DB_USER", "dhafnck_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "dhafnck_pass123")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def migrate_api_tokens_table():
    """
    Update api_tokens table to match ORM model:
    - Change scopes column from JSON to ARRAY(VARCHAR)
    - Remove token_metadata column if exists (not in ORM)
    """
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        
        try:
            # Step 1: Drop the old table and recreate with correct schema
            logger.info("Dropping old api_tokens table...")
            conn.execute(text("DROP TABLE IF EXISTS api_tokens CASCADE"))
            
            # Step 2: Create table with ORM-defined schema
            logger.info("Creating api_tokens table with ORM schema...")
            conn.execute(text("""
                CREATE TABLE api_tokens (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    token_hash VARCHAR(255) NOT NULL UNIQUE,
                    scopes VARCHAR[] NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    last_used_at TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    rate_limit INTEGER DEFAULT 1000,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """))
            
            # Step 3: Create indexes as defined in ORM
            logger.info("Creating indexes...")
            conn.execute(text("CREATE INDEX idx_api_tokens_user_id ON api_tokens(user_id)"))
            conn.execute(text("CREATE INDEX idx_api_tokens_token_hash ON api_tokens(token_hash)"))
            conn.execute(text("CREATE INDEX idx_api_tokens_is_active ON api_tokens(is_active)"))
            
            trans.commit()
            logger.info("Migration completed successfully!")
            
        except Exception as e:
            trans.rollback()
            logger.error(f"Migration failed: {e}")
            raise

if __name__ == "__main__":
    try:
        migrate_api_tokens_table()
        logger.info("✅ Database migration successful - ORM is now the source of truth")
    except Exception as e:
        logger.error(f"❌ Database migration failed: {e}")
        sys.exit(1)