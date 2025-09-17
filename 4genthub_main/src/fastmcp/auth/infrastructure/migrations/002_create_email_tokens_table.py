"""
Migration: Create Email Tokens Table

This migration creates the email_tokens table for storing email verification
and password reset tokens with enhanced metadata support.
"""

import logging
from sqlalchemy import text
from sqlalchemy.engine import Engine
from typing import Optional

logger = logging.getLogger(__name__)


def create_email_tokens_table_sqlite(engine: Engine) -> bool:
    """Create email_tokens table for SQLite"""
    try:
        with engine.connect() as conn:
            # Check if table already exists
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='email_tokens'"
            ))
            
            if result.fetchone():
                logger.info("Email tokens table already exists (SQLite)")
                return True
            
            # Create email_tokens table
            conn.execute(text("""
                CREATE TABLE email_tokens (
                    token VARCHAR(255) PRIMARY KEY,
                    email VARCHAR(255) NOT NULL,
                    token_type VARCHAR(50) NOT NULL,
                    token_hash VARCHAR(255) NOT NULL,
                    expires_at DATETIME NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    used_at DATETIME NULL,
                    is_used BOOLEAN DEFAULT 0,
                    token_metadata TEXT NULL,
                    user_id VARCHAR(255) NULL,
                    ip_address VARCHAR(45) NULL,
                    user_agent VARCHAR(500) NULL
                )
            """))
            
            # Create indexes for better performance
            conn.execute(text(
                "CREATE INDEX idx_email_tokens_email ON email_tokens(email)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_email_tokens_type ON email_tokens(token_type)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_email_tokens_expires ON email_tokens(expires_at)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_email_tokens_created ON email_tokens(created_at)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_email_tokens_used ON email_tokens(is_used)"
            ))
            
            conn.commit()
            logger.info("Email tokens table created successfully (SQLite)")
            return True
            
    except Exception as e:
        logger.error(f"Failed to create email tokens table (SQLite): {e}")
        return False


def create_email_tokens_table_postgresql(engine: Engine) -> bool:
    """Create email_tokens table for PostgreSQL"""
    try:
        with engine.connect() as conn:
            # Check if table already exists
            result = conn.execute(text("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public' AND tablename = 'email_tokens'
            """))
            
            if result.fetchone():
                logger.info("Email tokens table already exists (PostgreSQL)")
                return True
            
            # Create email_tokens table
            conn.execute(text("""
                CREATE TABLE email_tokens (
                    token VARCHAR(255) PRIMARY KEY,
                    email VARCHAR(255) NOT NULL,
                    token_type VARCHAR(50) NOT NULL,
                    token_hash VARCHAR(255) NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    used_at TIMESTAMP NULL,
                    is_used BOOLEAN DEFAULT FALSE,
                    token_metadata TEXT NULL,
                    user_id VARCHAR(255) NULL,
                    ip_address VARCHAR(45) NULL,
                    user_agent VARCHAR(500) NULL
                )
            """))
            
            # Create indexes for better performance
            conn.execute(text(
                "CREATE INDEX idx_email_tokens_email ON email_tokens(email)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_email_tokens_type ON email_tokens(token_type)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_email_tokens_expires ON email_tokens(expires_at)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_email_tokens_created ON email_tokens(created_at)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_email_tokens_used ON email_tokens(is_used)"
            ))
            
            # Create composite indexes for common queries
            conn.execute(text(
                "CREATE INDEX idx_email_tokens_email_type ON email_tokens(email, token_type)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_email_tokens_email_used ON email_tokens(email, is_used)"
            ))
            
            conn.commit()
            logger.info("Email tokens table created successfully (PostgreSQL)")
            return True
            
    except Exception as e:
        logger.error(f"Failed to create email tokens table (PostgreSQL): {e}")
        return False


def run_migration(engine: Engine) -> bool:
    """Run the email tokens table migration"""
    try:
        # Detect database type from engine URL
        if 'sqlite' in str(engine.url).lower():
            return create_email_tokens_table_sqlite(engine)
        elif 'postgresql' in str(engine.url).lower():
            return create_email_tokens_table_postgresql(engine)
        else:
            logger.error(f"Unsupported database type: {engine.url}")
            return False
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


def rollback_migration(engine: Engine) -> bool:
    """Rollback the email tokens table migration"""
    try:
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS email_tokens"))
            conn.commit()
            logger.info("Email tokens table dropped successfully")
            return True
            
    except Exception as e:
        logger.error(f"Migration rollback failed: {e}")
        return False


if __name__ == "__main__":
    # Example usage
    import os
    from sqlalchemy import create_engine
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Use environment database URL or default to SQLite
    database_url = os.getenv("DATABASE_URL", "sqlite:///./email_tokens_test.db")
    engine = create_engine(database_url)
    
    print("Running email tokens table migration...")
    if run_migration(engine):
        print("Migration completed successfully!")
    else:
        print("Migration failed!")