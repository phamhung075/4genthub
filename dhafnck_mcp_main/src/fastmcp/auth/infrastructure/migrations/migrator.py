"""
Email Token Database Migrator

Simple migrator to handle email token table creation and management.
"""

import logging
import os
from typing import Optional
from sqlalchemy import create_engine, Engine
from dotenv import load_dotenv

from . import __init__
import importlib.util

# Import the migration file dynamically to handle numeric prefix
migration_file = os.path.join(os.path.dirname(__file__), "002_create_email_tokens_table.py")
spec = importlib.util.spec_from_file_location("email_tokens_migration", migration_file)
email_tokens_migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(email_tokens_migration)
run_migration = email_tokens_migration.run_migration
rollback_migration = email_tokens_migration.rollback_migration

load_dotenv()
logger = logging.getLogger(__name__)


class EmailTokenMigrator:
    """Simple migrator for email token database schema"""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize migrator with database connection"""
        if database_url is None:
            # Try different database URL environment variables
            database_url = (
                os.getenv("DATABASE_URL") or 
                os.getenv("SUPABASE_DATABASE_URL") or
                "sqlite:///./email_tokens.db"
            )
        
        self.database_url = database_url
        self.engine = create_engine(database_url)
        logger.info(f"Email token migrator initialized with database: {database_url}")
    
    async def run_migrations(self) -> bool:
        """Run email token migrations"""
        try:
            logger.info("Running email token migrations...")
            
            # Run the email tokens table migration
            success = run_migration(self.engine)
            
            if success:
                logger.info("Email token migrations completed successfully")
            else:
                logger.error("Email token migrations failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Migration error: {e}")
            return False
    
    async def rollback_migrations(self) -> bool:
        """Rollback email token migrations"""
        try:
            logger.info("Rolling back email token migrations...")
            
            success = rollback_migration(self.engine)
            
            if success:
                logger.info("Email token migrations rolled back successfully")
            else:
                logger.error("Email token migration rollback failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Migration rollback error: {e}")
            return False
    
    def check_migration_status(self) -> dict:
        """Check current migration status"""
        try:
            # Check if email_tokens table exists
            from sqlalchemy import text
            
            with self.engine.connect() as conn:
                # For SQLite
                if 'sqlite' in str(self.engine.url).lower():
                    result = conn.execute(text(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='email_tokens'"
                    ))
                    table_exists = result.fetchone() is not None
                
                # For PostgreSQL
                elif 'postgresql' in str(self.engine.url).lower():
                    result = conn.execute(text("""
                        SELECT tablename FROM pg_tables 
                        WHERE schemaname = 'public' AND tablename = 'email_tokens'
                    """))
                    table_exists = result.fetchone() is not None
                
                else:
                    # Generic approach
                    try:
                        conn.execute(text("SELECT 1 FROM email_tokens LIMIT 1"))
                        table_exists = True
                    except:
                        table_exists = False
            
            return {
                "email_tokens_table_exists": table_exists,
                "database_url": str(self.engine.url),
                "database_type": str(self.engine.url).split(':')[0]
            }
            
        except Exception as e:
            logger.error(f"Migration status check error: {e}")
            return {
                "error": str(e),
                "email_tokens_table_exists": False
            }


# Convenience function
async def run_email_migrations(database_url: Optional[str] = None) -> bool:
    """Run email token migrations"""
    migrator = EmailTokenMigrator(database_url)
    return await migrator.run_migrations()


if __name__ == "__main__":
    # Example usage
    import asyncio
    
    async def main():
        migrator = EmailTokenMigrator()
        
        print("Checking migration status...")
        status = migrator.check_migration_status()
        print(f"Status: {status}")
        
        if not status.get("email_tokens_table_exists"):
            print("Running migrations...")
            success = await migrator.run_migrations()
            print(f"Migration result: {success}")
        else:
            print("Email tokens table already exists")
    
    asyncio.run(main())