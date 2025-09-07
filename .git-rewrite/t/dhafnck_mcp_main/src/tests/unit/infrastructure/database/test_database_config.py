"""
Test Database Configuration Module

This module provides PostgreSQL test database configuration that respects
the user requirement for separate test databases from dev/prod environments.
"""

import os
import logging
import urllib.parse
from typing import Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseTestConfig:
    """
    Test database configuration that supports PostgreSQL with proper isolation.
    
    Addresses these issues:
    1. PostgreSQL password contains @ characters causing URL parsing failures
    2. Need for separate test database from dev/prod
    3. Proper environment detection and configuration
    """
    
    def __init__(self):
        self.test_db_url: Optional[str] = None
        self.original_env: dict = {}
        
    def setup_postgresql_test_database(self) -> str:
        """
        Setup PostgreSQL test database configuration.
        
        Returns:
            str: Test database URL that can be used safely
        """
        # Check for explicit test database URL first
        test_db_url = os.environ.get("TEST_DATABASE_URL")
        if test_db_url:
            logger.info("Using explicit TEST_DATABASE_URL")
            return self._fix_database_url(test_db_url)
        
        # Get production database URL and modify for testing
        prod_db_url = os.environ.get("DATABASE_URL")
        if not prod_db_url:
            # Fallback to local PostgreSQL test database using actual Docker credentials
            logger.info("No DATABASE_URL found, using local PostgreSQL test database")
            return "postgresql://dhafnck_user:dhafnck_password@localhost:5432/dhafnck_mcp_test"
        
        # Fix malformed URL and create test variant
        fixed_url = self._fix_database_url(prod_db_url)
        test_url = self._create_test_database_url(fixed_url)
        
        logger.info(f"Created test database URL from production URL")
        return test_url
    
    def _fix_database_url(self, database_url: str) -> str:
        """
        Fix malformed database URLs with special characters in passwords.
        
        Args:
            database_url: Original database URL that may have parsing issues
            
        Returns:
            str: Fixed database URL
        """
        # Fix known issue with multiple @ characters in password
        # Note: Using placeholder pattern instead of real password for security
        if "test_password@@@@" in database_url:
            logger.info("Fixing malformed password in database URL")
            fixed_url = database_url.replace("test_password@@@@", "test_password@")
            return fixed_url
        
        # Handle other potential URL encoding issues
        # Check if URL has password parsing issues
        try:
            parsed = urllib.parse.urlparse(database_url)
            # If parsing fails or netloc has multiple @, fix it
            if parsed.netloc.count('@') > 1:
                # Split on last @ to separate auth from host
                auth_host = parsed.netloc.rsplit('@', 1)
                if len(auth_host) == 2:
                    auth, host = auth_host
                    # URL encode the password part if it contains @
                    if ':' in auth:
                        user, password = auth.split(':', 1)
                        # URL encode only the password
                        encoded_password = urllib.parse.quote(password, safe='')
                        fixed_netloc = f"{user}:{encoded_password}@{host}"
                        fixed_url = urllib.parse.urlunparse((
                            parsed.scheme,
                            fixed_netloc,
                            parsed.path,
                            parsed.params,
                            parsed.query,
                            parsed.fragment
                        ))
                        logger.info("Fixed URL encoding for password with special characters")
                        return fixed_url
        except Exception as e:
            logger.warning(f"Could not parse database URL for fixing: {e}")
        
        return database_url
    
    def _create_test_database_url(self, prod_url: str) -> str:
        """
        Create a test database URL from production URL.
        
        Options:
        1. Use test schema in same database (safer for cloud databases)
        2. Use separate test database (if available)
        
        Args:
            prod_url: Fixed production database URL
            
        Returns:
            str: Test database URL
        """
        try:
            parsed = urllib.parse.urlparse(prod_url)
            
            # Option 1: Try to create separate test database URL
            if parsed.path and parsed.path != '/':
                # Extract database name and create test variant
                db_name = parsed.path.lstrip('/')
                test_db_name = f"{db_name}_test"
                
                test_url = urllib.parse.urlunparse((
                    parsed.scheme,
                    parsed.netloc,
                    f"/{test_db_name}",
                    parsed.params,
                    parsed.query,
                    parsed.fragment
                ))
                logger.info(f"Created separate test database URL: {test_db_name}")
                return test_url
            
            # Option 2: Use test schema with same database
            query_params = urllib.parse.parse_qs(parsed.query)
            query_params['options'] = ['--search_path=test_schema']
            new_query = urllib.parse.urlencode(query_params, doseq=True)
            
            test_url = urllib.parse.urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment
            ))
            logger.info("Using test schema in same database")
            return test_url
            
        except Exception as e:
            logger.error(f"Failed to create test database URL: {e}")
            # Fallback to local test database using actual Docker credentials
            return "postgresql://dhafnck_user:dhafnck_password@localhost:5432/dhafnck_mcp_test"
    
    def configure_test_environment(self) -> None:
        """
        Configure environment variables for testing.
        Supports both PostgreSQL/Supabase (preferred) and SQLite (fallback).
        """
        # Save original environment
        self.original_env = {
            'DATABASE_TYPE': os.environ.get('DATABASE_TYPE'),
            'DATABASE_URL': os.environ.get('DATABASE_URL'),
            'DISABLE_AUTH': os.environ.get('DISABLE_AUTH'),
            'DHAFNCK_ENABLE_VISION': os.environ.get('DHAFNCK_ENABLE_VISION'),
        }
        
        # Check what database type is configured
        configured_db_type = os.environ.get('DATABASE_TYPE', 'postgresql').lower()
        
        # Priority order: Supabase > PostgreSQL > SQLite
        if configured_db_type in ['supabase', 'postgresql']:
            # Check if PostgreSQL/Supabase is actually available
            try:
                # Setup test database URL for PostgreSQL/Supabase
                test_url = self.setup_postgresql_test_database()
                
                # Try to connect to verify it's available
                import psycopg2
                from urllib.parse import urlparse
                parsed = urlparse(test_url)
                conn = psycopg2.connect(
                    host=parsed.hostname,
                    port=parsed.port or 5432,
                    database=parsed.path.lstrip('/'),
                    user=parsed.username,
                    password=parsed.password,
                    connect_timeout=3
                )
                conn.close()
                
                # PostgreSQL/Supabase is available, use it
                os.environ['DATABASE_TYPE'] = configured_db_type
                os.environ['DATABASE_URL'] = test_url
                logger.info(f"✅ Test environment configured for {configured_db_type.upper()}")
                logger.info(f"Test database URL: {test_url[:50]}...")
                
            except Exception as e:
                # PostgreSQL/Supabase not available, fall back to SQLite for tests
                logger.warning(f"⚠️ {configured_db_type.upper()} not available for testing: {e}")
                logger.info("📦 Falling back to SQLite for test execution")
                os.environ['DATABASE_TYPE'] = 'sqlite'
                # SQLite will use the path from DatabaseSourceManager
                if 'DATABASE_URL' in os.environ:
                    del os.environ['DATABASE_URL']
                    
        elif configured_db_type == 'sqlite':
            # SQLite explicitly requested, use it
            logger.info("📦 Using SQLite for test execution (as configured)")
            os.environ['DATABASE_TYPE'] = 'sqlite'
            # Remove DATABASE_URL to let SQLite use file path
            if 'DATABASE_URL' in os.environ:
                del os.environ['DATABASE_URL']
        else:
            # Unknown database type, default to SQLite for safety
            logger.warning(f"⚠️ Unknown DATABASE_TYPE: {configured_db_type}, using SQLite for tests")
            os.environ['DATABASE_TYPE'] = 'sqlite'
            if 'DATABASE_URL' in os.environ:
                del os.environ['DATABASE_URL']
        
        # Configure common test environment settings
        os.environ['DISABLE_AUTH'] = 'true'
        os.environ['DHAFNCK_ENABLE_VISION'] = 'true'
        
        # Keep pytest detection for test mode
        # This is needed for DatabaseSourceManager to use test database
        logger.info(f"Test environment configured with {os.environ['DATABASE_TYPE'].upper()}")
    
    def restore_environment(self) -> None:
        """
        Restore original environment variables.
        """
        for key, value in self.original_env.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]
        
        logger.info("Original environment restored")
    
    def create_test_schema_if_using_shared_db(self, engine) -> None:
        """
        Create test schema if using shared database with schema separation.
        
        Args:
            engine: SQLAlchemy engine
        """
        try:
            with engine.connect() as conn:
                # Check if we're using schema separation
                if 'search_path=test_schema' in str(engine.url):
                    conn.execute("CREATE SCHEMA IF NOT EXISTS test_schema")
                    conn.execute("SET search_path TO test_schema")
                    conn.commit()
                    logger.info("Created and set test_schema")
        except Exception as e:
            logger.warning(f"Could not create test schema: {e}")


def get_test_database_config() -> DatabaseTestConfig:
    """
    Get a configured test database instance.
    
    Returns:
        DatabaseTestConfig: Configured instance
    """
    config = DatabaseTestConfig()
    config.configure_test_environment()
    return config


def install_missing_dependencies():
    """
    Install missing dependencies required for testing.
    """
    try:
        import subprocess
        import sys
        
        # Check for docker module
        try:
            import docker
        except ImportError:
            logger.info("Installing missing 'docker' module...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "docker"])
            logger.info("Successfully installed 'docker' module")
            
        # Check for psycopg2
        try:
            import psycopg2
        except ImportError:
            logger.info("Installing missing 'psycopg2-binary' module...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
            logger.info("Successfully installed 'psycopg2-binary' module")
            
    except Exception as e:
        logger.error(f"Failed to install missing dependencies: {e}")
        raise


# Usage example for standalone test files
if __name__ == "__main__":
    print("Test Database Configuration")
    print("=" * 40)
    
    config = DatabaseTestConfig()
    config.configure_test_environment()
    
    print(f"Test database URL: {os.environ.get('DATABASE_URL')}")
    print(f"Database type: {os.environ.get('DATABASE_TYPE')}")
    
    config.restore_environment()
    print("Environment restored")