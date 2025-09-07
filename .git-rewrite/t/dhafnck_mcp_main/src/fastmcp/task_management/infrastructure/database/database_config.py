"""
Database Configuration Module using SQLAlchemy ORM

This module provides database configuration for PostgreSQL,
supporting both local PostgreSQL and cloud Supabase deployments.
"""

import os
import logging
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, Engine, event, pool, text
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from sqlalchemy.pool import NullPool, QueuePool

logger = logging.getLogger(__name__)

# Import exception for better error handling
from ...domain.exceptions.base_exceptions import DatabaseException


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
    
    def __init__(self):
        # Skip initialization if already done (singleton pattern)
        if self._initialized:
            return
            
        self.database_type = os.getenv("DATABASE_TYPE", "supabase").lower()
        self.database_url = self._get_secure_database_url()
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker] = None
        
        # Check if we're in test mode
        import sys
        is_test_mode = 'pytest' in sys.modules or 'PYTEST_CURRENT_TEST' in os.environ
        
        # Validate database type
        if self.database_type == "sqlite":
            if not is_test_mode:
                # SQLite not allowed in production
                raise ValueError(
                    "Database configuration error:\n"
                    "PostgreSQL is required for production.\n"
                    "REQUIRED ACTION: Set DATABASE_TYPE=supabase or postgresql in your environment.\n"
                    "Configure your database connection parameters."
                )
            else:
                # SQLite allowed for tests only
                logger.info("📦 Using SQLite for test execution (test mode detected)")
        
        # Only allow PostgreSQL/Supabase/SQLite(test only)
        elif self.database_type not in ["postgresql", "supabase"]:
            logger.error(f"❌ INVALID DATABASE_TYPE: {self.database_type}")
            raise ValueError(
                f"❌ UNSUPPORTED DATABASE_TYPE: {self.database_type}\n"
                "✅ ONLY SUPPORTED: 'supabase' or 'postgresql'\n"
                "🎯 RECOMMENDED: Set DATABASE_TYPE=supabase for best experience"
            )
        
        if self.database_type == "supabase":
            logger.info("🎯 SUPABASE DATABASE SELECTED - Excellent choice for cloud-native applications!")
        elif self.database_type == "postgresql":
            logger.info("✅ POSTGRESQL DATABASE SELECTED - Great choice for production workloads!")
        
        # Initialize database connection
        self._initialize_database()
        
        # Mark as initialized for singleton pattern
        DatabaseConfig._initialized = True
    
    def _get_secure_database_url(self) -> Optional[str]:
        """
        Get database URL securely from environment variables.
        
        Priority:
        1. DATABASE_URL if set (for backward compatibility)
        2. Construct from individual components (more secure)
        
        Returns:
            str: The database connection URL
        """
        import urllib.parse
        
        # First check if DATABASE_URL is explicitly set
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            # Log warning if it contains plaintext password
            if ":" in database_url and "@" in database_url:
                logger.warning("⚠️ DATABASE_URL contains credentials. Consider using individual environment variables for better security.")
            return database_url
        
        # Construct from individual components (more secure approach)
        if self.database_type == "supabase":
            # For Supabase, use the SUPABASE_* variables
            db_host = os.getenv("SUPABASE_DB_HOST")
            db_port = os.getenv("SUPABASE_DB_PORT", "5432")
            db_name = os.getenv("SUPABASE_DB_NAME", "postgres")
            db_user = os.getenv("SUPABASE_DB_USER", "postgres")
            db_password = os.getenv("SUPABASE_DB_PASSWORD")
            
            if db_host and db_password:
                # URL-encode the password to handle special characters
                encoded_password = urllib.parse.quote(db_password)
                database_url = f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}?sslmode=require"
                logger.info("✅ Database URL constructed from secure environment variables")
                return database_url
        
        elif self.database_type == "postgresql":
            # For local PostgreSQL
            db_host = os.getenv("DATABASE_HOST", "localhost")
            db_port = os.getenv("DATABASE_PORT", "5432")
            db_name = os.getenv("DATABASE_NAME", "dhafnck_mcp")
            db_user = os.getenv("DATABASE_USER", "dhafnck_user")
            db_password = os.getenv("DATABASE_PASSWORD")
            
            if db_password:
                encoded_password = urllib.parse.quote(db_password)
                database_url = f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"
                logger.info("✅ Database URL constructed from secure environment variables")
                return database_url
        
        # No valid configuration found
        return None
    
    def _get_database_url(self) -> str:
        """Get the appropriate database URL based on configuration"""
        if self.database_type == "sqlite":
            # SQLite for test mode only
            from .database_source_manager import DatabaseSourceManager
            db_manager = DatabaseSourceManager()
            sqlite_path = db_manager.get_database_path()
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
            
        elif self.database_type == "postgresql" and self.database_url:
            # Use PostgreSQL with provided URL
            logger.info("✅ Using PostgreSQL database with provided URL")
            return self.database_url
        else:
            # NO FALLBACK ALLOWED - FORCE PROPER CONFIGURATION
            raise ValueError(
                "DATABASE CONFIGURATION ERROR!\n"
                f"Current DATABASE_TYPE: {self.database_type}\n"
                f"Current DATABASE_URL: {'SET' if self.database_url else 'NOT SET'}\n\n"
                "✅ REQUIRED ACTIONS:\n"
                "1. Set DATABASE_TYPE=supabase (recommended)\n"
                "2. Configure Supabase environment variables in .env\n"
                "3. OR set DATABASE_TYPE=postgresql with valid DATABASE_URL\n\n"
                "PostgreSQL is required for this system.\n"
                "🎯 Use Supabase for the best experience!"
            )
    
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
                f"INVALID DATABASE URL!\n"
                f"URL must start with 'postgresql://' or 'sqlite:///' but got: {database_url[:20]}...\n"
                "✅ PostgreSQL/Supabase for production, SQLite for tests only!\n"
                "PostgreSQL is required for production."
            )
        
        # PostgreSQL/Supabase configuration optimized for cloud
        logger.info("🔧 Creating PostgreSQL engine with cloud-optimized settings")
        engine = create_engine(
            database_url,
            pool_size=15,  # Optimized for Supabase
            max_overflow=25,
            pool_pre_ping=True,  # Enable connection health checks
            pool_recycle=1800,  # Recycle connections after 30 minutes (good for cloud)
            pool_timeout=30,  # Connection timeout
            echo=os.getenv("SQL_DEBUG", "false").lower() == "true",  # SQL debugging
            future=True,  # Use SQLAlchemy 2.0 style
            # Cloud-optimized connection settings
            connect_args={
                "connect_timeout": 10,
                "application_name": "dhafnck_mcp_supabase",
                "options": "-c timezone=UTC",
            }
        )
        
        # Configure PostgreSQL optimization for Supabase
        @event.listens_for(engine, "connect")
        def set_postgresql_pragma(dbapi_connection, connection_record):
            with dbapi_connection.cursor() as cursor:
                # Set search path to public schema
                cursor.execute("SET search_path TO public")
                # Set statement timeout to prevent long-running queries
                cursor.execute("SET statement_timeout = '30s'")
                # Set lock timeout to prevent blocking
                cursor.execute("SET lock_timeout = '10s'")
                # Optimize for cloud latency
                cursor.execute("SET tcp_keepalives_idle = 600")
                cursor.execute("SET tcp_keepalives_interval = 30")
                cursor.execute("SET tcp_keepalives_count = 3")
        
        logger.info("✅ PostgreSQL engine created successfully")
        return engine
    
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
                with self.engine.connect() as conn:
                    if database_url and database_url.startswith("sqlite"):
                        # SQLite test query
                        result = conn.execute(text("SELECT sqlite_version()"))
                        version = result.scalar()
                        logger.info(f"📦 Connected to SQLite: {version}")
                        DatabaseConfig._connection_info = f"SQLite {version}"
                    else:
                        # PostgreSQL/Supabase test query
                        result = conn.execute(text("SELECT version()"))
                        version = result.scalar()
                        logger.info(f"🎯 Connected to PostgreSQL: {version}")
                        
                        # Check if this is Supabase
                        if database_url and "supabase" in database_url.lower():
                            result = conn.execute(text("SELECT current_database()"))
                            db_name = result.scalar()
                            logger.info(f"🚀 SUPABASE CONNECTION SUCCESSFUL! Database: {db_name}")
                            DatabaseConfig._connection_info = f"Supabase PostgreSQL - Database: {db_name}"
                        else:
                            logger.info("✅ PostgreSQL connection established")
                            DatabaseConfig._connection_info = f"PostgreSQL {version}"
                
                # Mark connection as verified
                DatabaseConfig._connection_verified = True
            else:
                # Use cached connection info
                logger.info(f"✅ Using cached connection: {DatabaseConfig._connection_info}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get a new database session"""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized")
        return self.SessionLocal()
    
    def create_tables(self):
        """Create all tables in the database"""
        if not self.engine:
            raise RuntimeError("Database not initialized")
        
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")
    
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
        return {
            "type": self.database_type,
            "url": self.database_url if self.database_type == "postgresql" else None,
            "engine": str(self.engine.url) if self.engine else None,
            "pool_size": self.engine.pool.size() if self.engine and hasattr(self.engine.pool, 'size') else None,
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
    """Get a new database session"""
    try:
        return get_db_config().get_session()
    except Exception as e:
        logger.error(f"Failed to get database session: {e}")
        raise DatabaseException(
            message=f"Database session unavailable: {str(e)}",
            operation="get_session",
            table="N/A"
        ) from e


def close_db():
    """Close database connections"""
    global _db_config
    if _db_config:
        _db_config.close()
        _db_config = None