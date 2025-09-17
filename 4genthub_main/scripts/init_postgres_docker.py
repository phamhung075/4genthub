#!/usr/bin/env python3
"""
Initialize PostgreSQL Database in Docker Container

This script:
1. Checks PostgreSQL connection
2. Creates database if needed
3. Runs migrations
4. Verifies schema
5. Creates initial data
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Optional
import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PostgreSQLInitializer:
    """Initialize PostgreSQL database for 4genthub"""
    
    def __init__(self):
        self.db_host = os.getenv("DATABASE_HOST", "localhost")
        self.db_port = os.getenv("DATABASE_PORT", "5432")
        self.db_name = os.getenv("DATABASE_NAME", "4genthub_prod")
        self.db_user = os.getenv("DATABASE_USER", "4genthub_user")
        self.db_password = os.getenv("DATABASE_PASSWORD", "postgres")
        self.ssl_mode = os.getenv("DATABASE_SSL_MODE", "prefer")
        
        # Build connection URL
        self.database_url = self._build_database_url()
        self.engine = None
        
    def _build_database_url(self, db_name: Optional[str] = None) -> str:
        """Build PostgreSQL connection URL"""
        db = db_name or self.db_name
        if self.ssl_mode == "disable":
            return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{db}"
        else:
            return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{db}?sslmode={self.ssl_mode}"
    
    def wait_for_postgres(self, max_retries: int = 30) -> bool:
        """Wait for PostgreSQL to be ready"""
        logger.info("⏳ Waiting for PostgreSQL to be ready...")
        
        for i in range(max_retries):
            try:
                conn = psycopg2.connect(
                    host=self.db_host,
                    port=self.db_port,
                    user=self.db_user,
                    password=self.db_password,
                    dbname="postgres",  # Connect to default database
                    connect_timeout=5
                )
                conn.close()
                logger.info("✅ PostgreSQL is ready!")
                return True
            except psycopg2.OperationalError as e:
                if i < max_retries - 1:
                    logger.info(f"   Attempt {i+1}/{max_retries}: PostgreSQL not ready, waiting...")
                    time.sleep(2)
                else:
                    logger.error(f"❌ PostgreSQL not ready after {max_retries} attempts")
                    return False
        
        return False
    
    def create_database_if_not_exists(self) -> bool:
        """Create database if it doesn't exist"""
        logger.info(f"🗄️  Checking database '{self.db_name}'...")
        
        try:
            # Connect to PostgreSQL server (not specific database)
            conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                user=self.db_user,
                password=self.db_password,
                dbname="postgres"
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (self.db_name,)
            )
            exists = cursor.fetchone() is not None
            
            if not exists:
                logger.info(f"   Creating database '{self.db_name}'...")
                cursor.execute(
                    sql.SQL("CREATE DATABASE {}").format(
                        sql.Identifier(self.db_name)
                    )
                )
                logger.info(f"   ✅ Database created successfully!")
            else:
                logger.info(f"   ✅ Database already exists")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating database: {e}")
            return False
    
    def initialize_schema(self) -> bool:
        """Initialize database schema using SQLAlchemy models"""
        logger.info("📋 Initializing database schema...")
        
        try:
            # Import DatabaseConfig to trigger initialization
            from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig
            from fastmcp.task_management.infrastructure.database.database_initializer import DatabaseInitializer
            
            # Create database configuration
            db_config = DatabaseConfig()
            
            # Initialize database
            initializer = DatabaseInitializer(db_config)
            initializer.initialize()
            
            logger.info("   ✅ Schema initialized successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error initializing schema: {e}")
            return False
    
    def verify_tables(self) -> bool:
        """Verify that all required tables exist"""
        logger.info("🔍 Verifying database tables...")
        
        try:
            self.engine = create_engine(self.database_url)
            inspector = inspect(self.engine)
            
            # Get all table names
            tables = inspector.get_table_names()
            
            # Required tables
            required_tables = [
                'tasks',
                'projects',
                'git_branches',
                'agents',
                'subtasks',
                'task_dependencies',
                'global_contexts',
                'project_contexts',
                'branch_contexts',
                'task_contexts',
                'migration_history'
            ]
            
            missing_tables = []
            for table in required_tables:
                if table not in tables:
                    missing_tables.append(table)
                    logger.warning(f"   ⚠️  Missing table: {table}")
                else:
                    logger.info(f"   ✅ Table exists: {table}")
            
            if missing_tables:
                logger.error(f"❌ Missing {len(missing_tables)} required tables")
                return False
            else:
                logger.info("   ✅ All required tables exist!")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error verifying tables: {e}")
            return False
    
    def create_initial_data(self) -> bool:
        """Create initial data (projects, global context, etc.)"""
        logger.info("📝 Creating initial data...")
        
        try:
            if not self.engine:
                self.engine = create_engine(self.database_url)
            
            with self.engine.connect() as conn:
                # Check if we already have data
                result = conn.execute(text("SELECT COUNT(*) FROM projects"))
                project_count = result.scalar()
                
                if project_count > 0:
                    logger.info(f"   ℹ️  Data already exists ({project_count} projects)")
                    return True
                
                # Create default project
                conn.execute(text("""
                    INSERT INTO projects (id, name, description, created_at, updated_at)
                    VALUES (
                        gen_random_uuid(),
                        'Default Project',
                        'Default project for initial setup',
                        NOW(),
                        NOW()
                    )
                    ON CONFLICT DO NOTHING
                """))
                
                # Create global context
                conn.execute(text("""
                    INSERT INTO global_contexts (
                        id, 
                        user_id,
                        team_preferences,
                        technology_stack,
                        project_workflow,
                        local_standards,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        gen_random_uuid(),
                        'system',
                        '{"default_branch": "main"}'::jsonb,
                        '{"backend": ["Python", "FastAPI"], "frontend": ["React", "TypeScript"]}'::jsonb,
                        '{"phases": ["planning", "development", "testing", "deployment"]}'::jsonb,
                        '{"naming": "snake_case", "testing": "pytest"}'::jsonb,
                        NOW(),
                        NOW()
                    )
                    ON CONFLICT DO NOTHING
                """))
                
                conn.commit()
                logger.info("   ✅ Initial data created successfully!")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error creating initial data: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test database connection with a simple query"""
        logger.info("🔌 Testing database connection...")
        
        try:
            if not self.engine:
                self.engine = create_engine(self.database_url)
            
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.scalar()
                logger.info(f"   ✅ Connected to: {version}")
                
                # Test table access
                result = conn.execute(text("SELECT COUNT(*) FROM projects"))
                count = result.scalar()
                logger.info(f"   ✅ Projects in database: {count}")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False
    
    def run(self) -> bool:
        """Run the complete initialization process"""
        logger.info("=" * 60)
        logger.info("POSTGRESQL DOCKER INITIALIZATION")
        logger.info("=" * 60)
        logger.info(f"Host: {self.db_host}:{self.db_port}")
        logger.info(f"Database: {self.db_name}")
        logger.info(f"User: {self.db_user}")
        logger.info(f"SSL Mode: {self.ssl_mode}")
        logger.info("-" * 60)
        
        steps = [
            ("Wait for PostgreSQL", self.wait_for_postgres),
            ("Create Database", self.create_database_if_not_exists),
            ("Initialize Schema", self.initialize_schema),
            ("Verify Tables", self.verify_tables),
            ("Create Initial Data", self.create_initial_data),
            ("Test Connection", self.test_connection)
        ]
        
        results = {}
        
        for step_name, step_func in steps:
            logger.info(f"\n🚀 {step_name}...")
            success = step_func()
            results[step_name] = success
            
            if not success:
                logger.error(f"❌ Step failed: {step_name}")
                break
        
        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("INITIALIZATION SUMMARY")
        logger.info("=" * 60)
        
        for step_name, success in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            logger.info(f"{step_name}: {status}")
        
        all_success = all(results.values())
        
        if all_success:
            logger.info("\n🎉 Database initialization completed successfully!")
            logger.info("\nYou can now:")
            logger.info("1. Access the MCP API at http://localhost:8001")
            logger.info("2. View the database with PgAdmin at http://localhost:5050")
            logger.info("3. Run the Keycloak integration test: python scripts/test_keycloak_integration.py")
        else:
            logger.error("\n⚠️  Database initialization failed. Please check the errors above.")
        
        return all_success

def main():
    """Main entry point"""
    initializer = PostgreSQLInitializer()
    success = initializer.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()