"""
Supabase Database Configuration Module

This module extends the database configuration to support Supabase as a database backend.
Supabase provides a PostgreSQL database with additional features like real-time subscriptions,
authentication, and storage.
"""

import os
import logging
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, Engine, event, pool, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import urllib.parse

logger = logging.getLogger(__name__)


class SupabaseConfig:
    """
    Supabase database configuration manager.
    
    Supabase is a Backend-as-a-Service that provides a PostgreSQL database
    with additional features like authentication, real-time subscriptions,
    and storage.
    """
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        self.supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.supabase_jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
        
        # Database connection URL
        self.database_url = self._get_supabase_database_url()
        
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker] = None
        
        # Initialize database connection
        self._initialize_database()
    
    def _get_supabase_database_url(self) -> str:
        """
        Get Supabase PostgreSQL connection URL.
        Priority order:
        1. SUPABASE_DATABASE_URL (direct connection string)
        2. DATABASE_URL (if contains supabase)
        3. Construct from Supabase components
        """
        # First priority: Direct Supabase database URL
        supabase_db_url = os.getenv("SUPABASE_DATABASE_URL")
        if supabase_db_url:
            logger.info("🎯 Using SUPABASE_DATABASE_URL (direct connection)")
            return supabase_db_url
        
        # Second priority: Check if DATABASE_URL is Supabase
        database_url = os.getenv("DATABASE_URL")
        if database_url and ("supabase" in database_url.lower() or "PLACEHOLDER_SUPABASE_REF" in database_url):
            logger.info("🎯 Using DATABASE_URL (contains Supabase)")
            return database_url
        
        # Third priority: Construct from individual Supabase variables
        if self.supabase_url:
            # Extract project reference from Supabase URL
            # Format: https://[project-ref].supabase.co
            import re
            match = re.match(r'https://([a-zA-Z0-9]+)\.supabase\.co', self.supabase_url)
            if match:
                project_ref = match.group(1)
                
                # Use the password from env variables
                db_password = os.getenv("SUPABASE_DB_PASSWORD")
                if not db_password:
                    raise ValueError("SUPABASE_DB_PASSWORD environment variable is required")
                db_user = os.getenv("SUPABASE_DB_USER", "postgres")
                db_host = os.getenv("SUPABASE_DB_HOST", f"db.{project_ref}.supabase.co")
                db_port = os.getenv("SUPABASE_DB_PORT", "5432")
                db_name = os.getenv("SUPABASE_DB_NAME", "postgres")
                
                # Construct direct connection string
                database_url = f"postgresql://{db_user}:{urllib.parse.quote(db_password)}@{db_host}:{db_port}/{db_name}"
                
                # Add SSL mode for Supabase
                # Check if this is self-hosted (IP address in URL)
                import re
                is_self_hosted = bool(re.search(r'\d+\.\d+\.\d+\.\d+', self.supabase_url or ''))
                
                if is_self_hosted:
                    # For self-hosted with self-signed certificates, use prefer mode
                    database_url += "?sslmode=prefer"
                    logger.info(f"🔒 Self-hosted Supabase detected, using sslmode=prefer for self-signed certificate")
                else:
                    # For cloud Supabase, always require SSL
                    ssl_cert_env = os.getenv("SUPABASE_SSL_CERT_PATH", "prod-ca-2021.crt")
                    ssl_cert_path = os.path.abspath(ssl_cert_env)
                    if os.path.exists(ssl_cert_path):
                        database_url += f"?sslmode=require&sslrootcert={ssl_cert_path}"
                        logger.info(f"🔒 Using SSL certificate: {ssl_cert_path}")
                    else:
                        database_url += "?sslmode=require"
                        logger.warning(f"⚠️ SSL certificate not found at {ssl_cert_path}, using sslmode=require without certificate")
                
                logger.info(f"🔧 Constructed Supabase connection for project: {project_ref}")
                return database_url
        
        # No valid Supabase configuration found
        raise ValueError(
            "🚫 SUPABASE CONFIGURATION MISSING! 🚫\n"
            "Required: One of the following configurations:\n"
            "1. SUPABASE_DATABASE_URL=postgresql://postgres:password@db.project.supabase.co:5432/postgres\n"
            "2. DATABASE_URL with Supabase connection string\n"
            "3. Individual Supabase variables: SUPABASE_URL, SUPABASE_DB_PASSWORD, etc.\n"
            f"Current SUPABASE_URL: {'SET' if self.supabase_url else 'NOT SET'}\n"
            f"Current DATABASE_URL: {'SET' if database_url else 'NOT SET'}"
        )
    
    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine optimized for Supabase"""
        if not self.database_url:
            raise ValueError("Database URL not configured. Please set SUPABASE_URL or DATABASE_URL")
        
        # Import the resilient engine creation function
        from .connection_retry import create_resilient_engine
        
        # Supabase PostgreSQL configuration with enhanced resilience
        engine = create_resilient_engine(
            self.database_url,
            # Connection pool settings optimized for Supabase
            pool_size=2,  # Minimal pool size for better stability
            max_overflow=3,  # Very conservative overflow 
            pool_pre_ping=True,  # Enable connection health checks
            pool_recycle=120,  # Recycle connections every 2 minutes
            pool_timeout=120,  # Extended timeout for cloud latency
            echo=os.getenv("SQL_DEBUG", "false").lower() == "true",
            future=True,  # Use SQLAlchemy 2.0 style
            poolclass=QueuePool,  # Explicit pool class for better control
            # Supabase-specific settings with enhanced resilience
            connect_args={
                "connect_timeout": 60,  # Extended connection timeout
                "application_name": "agenthub",
                # Connection keepalive settings for cloud stability
                "keepalives": 1,
                "keepalives_idle": 15,  # More aggressive keepalive
                "keepalives_interval": 3,  # Check every 3 seconds
                "keepalives_count": 15,  # More retries
                "tcp_user_timeout": 60000,  # 60 seconds TCP timeout
                # Additional resilience settings with extended timeouts
                "options": "-c statement_timeout=120000 -c idle_in_transaction_session_timeout=90000",
            } if "supabase" in self.database_url else {}
        )
        
        # Add event listener for connection initialization
        @event.listens_for(engine, "connect")
        def set_postgresql_search_path(dbapi_connection, connection_record):
            """Set PostgreSQL search path and optimize for Supabase"""
            with dbapi_connection.cursor() as cursor:
                # Set search path to public schema
                cursor.execute("SET search_path TO public")
                
                # Set statement timeout to prevent long-running queries
                cursor.execute("SET statement_timeout = '60s'")  # Increased for cloud latency
                
                # Set lock timeout to prevent blocking
                cursor.execute("SET lock_timeout = '30s'")  # Increased for cloud latency
                
                # Enable auto-explain for slow queries (if available)
                try:
                    cursor.execute("SET auto_explain.log_min_duration = '1s'")
                except:
                    pass  # auto_explain may not be available
        
        return engine
    
    def _initialize_database(self):
        """Initialize Supabase database connection"""
        try:
            self.engine = self._create_engine()
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine,
                expire_on_commit=False  # Don't expire objects after commit
            )
            
            # Test connection
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.scalar()
                logger.info(f"Connected to Supabase PostgreSQL: {version}")
                
                # Check if we're connected to Supabase
                result = conn.execute(text("SELECT current_database()"))
                db_name = result.scalar()
                if "supabase" in self.database_url:
                    logger.info(f"✅ Connected to Supabase database: {db_name}")
                
        except Exception as e:
            logger.error(f"Failed to initialize Supabase database: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get a new database session with retry logic"""
        from .connection_retry import with_connection_retry, DEFAULT_RETRY_CONFIG
        
        @with_connection_retry(DEFAULT_RETRY_CONFIG)
        def _get_session_with_retry():
            if not self.SessionLocal:
                raise RuntimeError("Database not initialized")
            
            session = self.SessionLocal()
            
            # Test the session with a simple query to ensure it's working
            try:
                from sqlalchemy import text
                session.execute(text("SELECT 1"))
            except Exception as e:
                session.close()
                raise
            
            return session
        
        return _get_session_with_retry()
    
    def create_tables(self, base):
        """Create all tables in the Supabase database"""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        
        logger.info("Creating tables in Supabase database...")
        base.metadata.create_all(bind=self.engine)
        logger.info("✅ Tables created successfully in Supabase")
    
    def dispose(self):
        """Dispose of the engine and close all connections"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")


# Singleton instance
_supabase_config: Optional[SupabaseConfig] = None


def get_supabase_config() -> SupabaseConfig:
    """Get or create Supabase configuration singleton"""
    global _supabase_config
    if _supabase_config is None:
        _supabase_config = SupabaseConfig()
    return _supabase_config


def is_supabase_configured() -> bool:
    """Check if Supabase is properly configured"""
    return bool(
        os.getenv("SUPABASE_URL") and 
        os.getenv("SUPABASE_ANON_KEY") and
        (os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_PASSWORD"))
    )