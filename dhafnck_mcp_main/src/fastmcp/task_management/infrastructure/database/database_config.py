"""
Database Configuration Module using SQLAlchemy ORM

This module provides database configuration for PostgreSQL,
supporting both local PostgreSQL and cloud Supabase deployments.
"""

# Load environment variables BEFORE any configuration
from pathlib import Path
try:
    from dotenv import load_dotenv
    project_root = Path(__file__).parent.parent.parent.parent.parent.parent

    # Try to load .env.dev first in development, then .env
    env_dev_path = project_root / ".env.dev"
    env_path = project_root / ".env"

    if env_dev_path.exists():
        load_dotenv(env_dev_path, override=True)
    elif env_path.exists():
        load_dotenv(env_path, override=True)
    else:
        load_dotenv(override=True)
except ImportError:
    pass

import os
import logging
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, Engine, event, pool, text
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from sqlalchemy.pool import NullPool, QueuePool

logger = logging.getLogger(__name__)

# Import exception for better error handling
from ...domain.exceptions.base_exceptions import DatabaseException
# Import retry logic for connection resilience
from .connection_retry import with_connection_retry, create_resilient_engine, DEFAULT_RETRY_CONFIG


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""
    pass


class DatabaseConfig:
    """
    Database configuration manager for PostgreSQL.
    
    Uses DATABASE_TYPE and DATABASE_URL environment variables to configure
    PostgreSQL connection (local or Supabase).
    
    Implements singleton pattern and connection caching for performance.
    """
    
    # Class-level singleton instance
    _instance = None
    _initialized = False
    _connection_verified = False
    _connection_info = None
    
    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls):
        """
        Get the singleton instance of DatabaseConfig.
        
        This is the preferred way to get the database configuration.
        
        Returns:
            DatabaseConfig: The singleton instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """
        Reset the singleton instance - useful for testing.
        
        This method clears the singleton state, forcing a new instance 
        to be created on the next call to get_instance().
        """
        if cls._instance:
            try:
                cls._instance.close()
            except Exception as e:
                logger.warning(f"Error closing database instance during reset: {e}")
        
        cls._instance = None
        cls._initialized = False
        cls._connection_verified = False
        cls._connection_info = None
    
    def __init__(self):
        # Skip initialization if already done (singleton pattern)
        if self._initialized:
            return

        # Prevent re-entrant initialization
        if hasattr(self, '_initializing') and self._initializing:
            return

        self._initializing = True
        try:
            # Check if we're in test mode
            import sys
            is_test_mode = 'pytest' in sys.modules or 'PYTEST_CURRENT_TEST' in os.environ

            # Default to PostgreSQL, but allow SQLite for tests
            self.database_type = os.getenv("DATABASE_TYPE", "postgresql").lower()

            # Validate database type
            if self.database_type == "sqlite":
                if not is_test_mode:
                    raise ValueError(
                        "SQLite is only allowed for test execution.\n"
                        "Use DATABASE_TYPE=postgresql or supabase for development/production."
                    )
                logger.info("📦 SQLite mode for test execution")
                self.database_url = None  # Will be set in _get_database_url

            elif self.database_type in ["postgresql", "supabase"]:
                # Get database URL from environment variables
                self.database_url = self._get_secure_database_url()
                if not self.database_url:
                    raise ValueError(
                        f"Database configuration missing for {self.database_type}.\n"
                        "Required environment variables:\n"
                        f"{'DATABASE_HOST, DATABASE_USER, DATABASE_PASSWORD' if self.database_type == 'postgresql' else 'SUPABASE_DB_HOST, SUPABASE_DB_PASSWORD'}"
                    )
            else:
                raise ValueError(
                    f"Invalid DATABASE_TYPE: {self.database_type}\n"
                    "Supported types: 'postgresql', 'supabase', or 'sqlite' (tests only)"
                )

            logger.info(f"Database type: {self.database_type}")
            self.engine: Optional[Engine] = None
            self.SessionLocal: Optional[sessionmaker] = None

            if self.database_type == "supabase":
                logger.info("🎯 SUPABASE DATABASE SELECTED - Excellent choice for cloud-native applications!")
            elif self.database_type == "postgresql":
                logger.info("✅ POSTGRESQL DATABASE SELECTED - Great choice for production workloads!")

            # Initialize database connection
            self._initialize_database()

            # Mark as initialized for singleton pattern
            DatabaseConfig._initialized = True
        finally:
            self._initializing = False
    
    def _get_secure_database_url(self) -> Optional[str]:
        """
        Get database URL from individual environment variables.

        Returns:
            str: The database connection URL or None if not configured
        """
        import urllib.parse

        if self.database_type == "postgresql":
            # PostgreSQL - use individual DATABASE_* variables
            db_host = os.getenv("DATABASE_HOST")
            db_port = os.getenv("DATABASE_PORT", "5432")
            db_name = os.getenv("DATABASE_NAME", "dhafnck_mcp")
            db_user = os.getenv("DATABASE_USER", "postgres")
            db_password = os.getenv("DATABASE_PASSWORD")
            ssl_mode = os.getenv("DATABASE_SSL_MODE", "prefer")

            # Require all necessary components
            if not (db_host and db_user and db_password):
                logger.error("PostgreSQL configuration incomplete. Required: DATABASE_HOST, DATABASE_USER, DATABASE_PASSWORD")
                return None

            encoded_password = urllib.parse.quote(db_password)
            database_url = f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"
            if ssl_mode and ssl_mode != "disable":
                database_url += f"?sslmode={ssl_mode}"
            logger.info("✅ PostgreSQL URL constructed from environment variables")
            return database_url

        elif self.database_type == "supabase":
            # Supabase - use SUPABASE_* variables
            db_host = os.getenv("SUPABASE_DB_HOST")
            db_port = os.getenv("SUPABASE_DB_PORT", "5432")
            db_name = os.getenv("SUPABASE_DB_NAME", "postgres")
            db_user = os.getenv("SUPABASE_DB_USER", "postgres")
            db_password = os.getenv("SUPABASE_DB_PASSWORD")

            if not (db_host and db_password):
                logger.error("Supabase configuration incomplete. Required: SUPABASE_DB_HOST, SUPABASE_DB_PASSWORD")
                return None

            encoded_password = urllib.parse.quote(db_password)
            database_url = f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}?sslmode=require"
            logger.info("✅ Supabase URL constructed from environment variables")
            return database_url

        return None
    
    def _get_database_url(self) -> str:
        """Get the appropriate database URL based on configuration"""
        if self.database_type == "sqlite":
            # SQLite for test mode only
            import tempfile
            sqlite_path = os.path.join(tempfile.gettempdir(), "dhafnck_mcp_test.db")
            logger.info(f"📦 Using SQLite database for tests: {sqlite_path}")
            return f"sqlite:///{sqlite_path}"

        elif self.database_type == "supabase":
            # Use Supabase configuration (PostgreSQL cloud)
            logger.info("🎯 Using Supabase PostgreSQL database (cloud-native)")
            from .supabase_config import get_supabase_config, is_supabase_configured
            
            if not is_supabase_configured():
                raise ValueError(
                    "SUPABASE NOT PROPERLY CONFIGURED!\n"
                    "Required environment variables:\n"
                    "✅ SUPABASE_URL (your project URL)\n"
                    "✅ SUPABASE_ANON_KEY (from Supabase dashboard)\n"
                    "✅ SUPABASE_DATABASE_URL (direct connection string)\n"
                    "OR set SUPABASE_DB_PASSWORD with project credentials\n"
                    "🔧 Check your .env file and ensure all Supabase variables are set."
                )
            
            supabase_config = get_supabase_config()
            logger.info(f"✅ Supabase connection established: {supabase_config.database_url[:50]}...")
            return supabase_config.database_url
            
        elif self.database_type == "postgresql":
            # Use PostgreSQL with constructed URL
            logger.info("✅ Using PostgreSQL database")
            return self.database_url
        else:
            # This should never happen due to validation in __init__
            raise ValueError(f"Unsupported database type: {self.database_type}")
    
    def _create_engine(self, database_url: str) -> Engine:
        """Create SQLAlchemy engine for database connection"""
        if database_url.startswith("sqlite"):
            # SQLite engine for test mode
            logger.info("📦 Creating SQLite engine for test execution")
            engine = create_engine(
                database_url,
                echo=os.getenv("SQL_DEBUG", "false").lower() == "true",
                future=True,
                poolclass=pool.StaticPool,  # Use StaticPool for SQLite in tests
                connect_args={"check_same_thread": False}  # Allow multi-threaded access for tests
            )

            # Configure SQLite for better test performance
            @event.listens_for(engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")  # Enable foreign keys
                cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for better concurrency
                cursor.execute("PRAGMA synchronous=NORMAL")  # Faster writes for tests
                cursor.close()

            logger.info("✅ SQLite engine created for tests")
            return engine

        elif not database_url.startswith("postgresql"):
            raise ValueError(
                f"Invalid database URL. Expected PostgreSQL or SQLite URL but got: {database_url[:20]}..."
            )
        
        # PostgreSQL/Supabase configuration optimized for cloud
        logger.info("🔧 Creating PostgreSQL engine with cloud-optimized settings")
        
        # Load pool settings from environment variables with defaults
        pool_size = int(os.getenv("DATABASE_POOL_SIZE", "50"))  # Use env var
        max_overflow = int(os.getenv("DATABASE_MAX_OVERFLOW", "100"))  # Use env var
        pool_timeout = int(os.getenv("DATABASE_POOL_TIMEOUT", "60"))  # Use env var
        pool_recycle = int(os.getenv("DATABASE_POOL_RECYCLE", "1800"))  # Use env var
        pool_pre_ping = os.getenv("DATABASE_POOL_PRE_PING", "true").lower() in ["true", "1", "yes"]
        
        logger.info(f"📊 Database Pool Configuration:")
        logger.info(f"  - Pool Size: {pool_size}")
        logger.info(f"  - Max Overflow: {max_overflow}")
        logger.info(f"  - Pool Timeout: {pool_timeout}s")
        logger.info(f"  - Pool Recycle: {pool_recycle}s")
        logger.info(f"  - Pre-ping: {pool_pre_ping}")
        
        engine = create_engine(
            database_url,
            pool_size=pool_size,  # Now uses environment variable
            max_overflow=max_overflow,  # Now uses environment variable
            pool_pre_ping=pool_pre_ping,  # Now uses environment variable
            pool_recycle=pool_recycle,  # Now uses environment variable
            pool_timeout=pool_timeout,  # Now uses environment variable
            echo=os.getenv("SQL_DEBUG", "false").lower() == "true",  # SQL debugging
            future=True,  # Use SQLAlchemy 2.0 style
            # Cloud-optimized connection settings
            connect_args={
                "connect_timeout": 30,  # Increased for better cloud reliability
                "application_name": "dhafnck_mcp_supabase",
                "options": "-c timezone=UTC",
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
            }
        )
        
        # Configure PostgreSQL optimization for Supabase
        @event.listens_for(engine, "connect")
        def set_postgresql_pragma(dbapi_connection, connection_record):
            with dbapi_connection.cursor() as cursor:
                # Set search path to public schema
                cursor.execute("SET search_path TO public")
                # Set statement timeout to prevent long-running queries
                cursor.execute("SET statement_timeout = '60s'")  # Increased for cloud latency
                # Set lock timeout to prevent blocking
                cursor.execute("SET lock_timeout = '30s'")  # Increased for cloud latency
                # Optimize for cloud latency
                cursor.execute("SET tcp_keepalives_idle = 600")
                cursor.execute("SET tcp_keepalives_interval = 30")
                cursor.execute("SET tcp_keepalives_count = 3")
        
        logger.info("✅ PostgreSQL engine created successfully")
        return engine
    
    @with_connection_retry(DEFAULT_RETRY_CONFIG)
    def _test_connection(self, database_url: str):
        """Test database connection with retry logic"""
        with self.engine.connect() as conn:
            if database_url.startswith("sqlite"):
                # SQLite test query
                result = conn.execute(text("SELECT sqlite_version()"))
                version = result.scalar()
                logger.info(f"📦 Connected to SQLite: {version}")
                DatabaseConfig._connection_info = f"SQLite {version}"
            else:
                # PostgreSQL test query
                result = conn.execute(text("SELECT version()"))
                version = result.scalar()
                logger.info(f"✅ Connected to PostgreSQL: {version}")

                # Check if this is Supabase
                if database_url and "supabase" in database_url.lower():
                    result = conn.execute(text("SELECT current_database()"))
                    db_name = result.scalar()
                    logger.info(f"🚀 Supabase connection successful! Database: {db_name}")
                    DatabaseConfig._connection_info = f"Supabase PostgreSQL - Database: {db_name}"
                else:
                    DatabaseConfig._connection_info = f"PostgreSQL {version}"
    
    def _initialize_database(self):
        """Initialize database connection and create session factory"""
        try:
            database_url = self._get_database_url()
            self.engine = self._create_engine(database_url)
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine,
                expire_on_commit=False  # Don't expire objects after commit
            )
            
            # Test connection only if not already verified (caching for performance)
            if not DatabaseConfig._connection_verified:
                self._test_connection(database_url)
                
                # Ensure AI columns exist after first connection
                from .ensure_ai_columns import ensure_ai_columns_exist
                logger.info("Ensuring AI columns exist in database...")
                if ensure_ai_columns_exist(self.engine):
                    logger.info("✅ AI columns verified in database")
                
                # Mark connection as verified
                DatabaseConfig._connection_verified = True
            else:
                # Use cached connection info
                logger.info(f"✅ Using cached connection: {DatabaseConfig._connection_info}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    @with_connection_retry(DEFAULT_RETRY_CONFIG)
    def get_session(self) -> Session:
        """Get a new database session with retry logic"""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized")
        
        session = self.SessionLocal()
        
        # Test the session with a simple query to ensure it's working
        try:
            session.execute(text("SELECT 1"))
        except Exception as e:
            session.close()
            raise
        
        return session
    
    def create_tables(self):
        """Create all tables in the database and ensure AI columns exist"""
        if not self.engine:
            raise RuntimeError("Database not initialized")
        
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")
        
        # Ensure AI columns exist (for existing databases)
        from .ensure_ai_columns import ensure_ai_columns_exist
        logger.info("Ensuring AI columns exist in database...")
        if ensure_ai_columns_exist(self.engine):
            logger.info("✅ AI columns verified/created successfully")
        else:
            logger.warning("⚠️ Could not verify AI columns - they will be created with new tables")
    
    def get_engine(self) -> Engine:
        """Get the SQLAlchemy engine"""
        if not self.engine:
            raise RuntimeError("Database not initialized")
        return self.engine
    
    def close(self):
        """Close database connections"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get information about the current database configuration"""
        pool_info = {}
        if self.engine and hasattr(self.engine.pool, 'size'):
            try:
                pool_info = {
                    "size": self.engine.pool.size(),
                    "checked_in": self.engine.pool.checkedin(),
                    "checked_out": self.engine.pool.checkedout(),
                    "overflow": self.engine.pool.overflow(),
                    "total": self.engine.pool.checkedout() + self.engine.pool.checkedin()
                }
            except Exception as e:
                logger.warning(f"Could not get pool info: {e}")
                pool_info = {"error": str(e)}
        
        return {
            "type": self.database_type,
            "url": self.database_url if self.database_type == "postgresql" else None,
            "engine": str(self.engine.url) if self.engine else None,
            "pool": pool_info,
            "configured_pool_size": int(os.getenv("DATABASE_POOL_SIZE", "50")),
            "configured_max_overflow": int(os.getenv("DATABASE_MAX_OVERFLOW", "100"))
        }


# Global instance
_db_config: Optional[DatabaseConfig] = None


def get_db_config() -> DatabaseConfig:
    """Get or create the global database configuration"""
    global _db_config
    if _db_config is None:
        try:
            # Use singleton instance
            _db_config = DatabaseConfig.get_instance()
        except Exception as e:
            logger.error(f"Failed to initialize database configuration: {e}")
            raise
    return _db_config


def get_session() -> Session:
    """Get a new database session with automatic retry and recovery"""
    max_attempts = 3
    last_error = None
    
    for attempt in range(max_attempts):
        try:
            return get_db_config().get_session()
        except Exception as e:
            last_error = e
            logger.warning(f"Failed to get database session (attempt {attempt + 1}/{max_attempts}): {e}")
            
            # If this is a connection error, try to reset the connection pool
            if attempt < max_attempts - 1:
                try:
                    db_config = get_db_config()
                    if hasattr(db_config, 'engine') and db_config.engine:
                        logger.info("Attempting to reset connection pool...")
                        db_config.engine.dispose()
                        db_config._initialize_database()
                        logger.info("Connection pool reset successful")
                except Exception as reset_error:
                    logger.error(f"Failed to reset connection pool: {reset_error}")
                
                # Wait before retrying with exponential backoff
                import time
                wait_time = (2 ** attempt) * 1.0
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
    
    # All attempts failed
    logger.error(f"Failed to get database session after {max_attempts} attempts: {last_error}")
    raise DatabaseException(
        message=f"Database session unavailable after {max_attempts} attempts: {str(last_error)}",
        operation="get_session",
        table="N/A"
    ) from last_error


def close_db():
    """Close database connections and reset singleton instances"""
    global _db_config
    if _db_config:
        _db_config.close()
        _db_config = None
    
    # Also reset the class-level singleton
    DatabaseConfig.reset_instance()