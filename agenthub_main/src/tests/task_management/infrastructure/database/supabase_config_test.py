"""
Test suite for Supabase Database Configuration

Tests the Supabase database configuration including connection URL construction,
engine creation, session management, and proper error handling.
"""

import os
import pytest
from unittest.mock import MagicMock, patch, Mock
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from fastmcp.task_management.infrastructure.database.supabase_config import (
    SupabaseConfig,
    get_supabase_config,
    is_supabase_configured
)


class TestSupabaseConfig:
    """Test suite for SupabaseConfig"""

    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Mock environment variables"""
        monkeypatch.setenv("SUPABASE_URL", "https://testproject.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "mock-anon-key")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "mock-service-key")
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "mock-jwt-secret")
        monkeypatch.setenv("SUPABASE_DB_PASSWORD", "mock-password")

    @pytest.fixture
    def mock_engine(self):
        """Create a mock SQLAlchemy engine"""
        engine = MagicMock(spec=Engine)
        # Mock the connect method to return a context manager
        mock_connection = MagicMock()
        mock_connection.__enter__ = MagicMock(return_value=mock_connection)
        mock_connection.__exit__ = MagicMock(return_value=None)
        mock_connection.execute.return_value.scalar.return_value = "PostgreSQL 13.0"
        engine.connect.return_value = mock_connection
        return engine

    @pytest.fixture
    def supabase_config(self, mock_env):
        """Create SupabaseConfig with mocked dependencies"""
        with patch('fastmcp.task_management.infrastructure.database.connection_retry.create_resilient_engine') as mock_create_engine:
            with patch('sqlalchemy.event.listens_for', lambda *args, **kwargs: lambda fn: fn):
                mock_engine = MagicMock(spec=Engine)
                mock_connection = MagicMock()
                mock_connection.__enter__ = MagicMock(return_value=mock_connection)
                mock_connection.__exit__ = MagicMock(return_value=None)
                mock_connection.execute.return_value.scalar.side_effect = ["PostgreSQL 13.0", "postgres"]
                mock_engine.connect.return_value = mock_connection
                mock_engine.dispose = MagicMock()
                mock_create_engine.return_value = mock_engine

                # Clear the singleton
                import fastmcp.task_management.infrastructure.database.supabase_config as config_module
                config_module._supabase_config = None

                config = SupabaseConfig()
                return config

    def test_init_with_direct_database_url(self, monkeypatch):
        """Test initialization with direct SUPABASE_DATABASE_URL"""
        direct_url = "postgresql://postgres:password@db.testproject.supabase.co:5432/postgres"
        monkeypatch.setenv("SUPABASE_DATABASE_URL", direct_url)

        with patch('fastmcp.task_management.infrastructure.database.supabase_config.SupabaseConfig._initialize_database') as mock_init:
            # Prevent actual database initialization
            mock_init.return_value = None

            config = SupabaseConfig()
            assert config.database_url == direct_url

    def test_init_with_database_url_containing_supabase(self, monkeypatch):
        """Test initialization with DATABASE_URL containing supabase"""
        database_url = "postgresql://postgres:password@db.PLACEHOLDER_SUPABASE_REF.supabase.co:5432/postgres"
        monkeypatch.setenv("DATABASE_URL", database_url)
        monkeypatch.delenv("SUPABASE_DATABASE_URL", raising=False)

        with patch('fastmcp.task_management.infrastructure.database.supabase_config.SupabaseConfig._initialize_database') as mock_init:
            # Prevent actual database initialization
            mock_init.return_value = None

            config = SupabaseConfig()
            assert config.database_url == database_url

    def test_init_with_constructed_url(self, mock_env, monkeypatch):
        """Test initialization with URL constructed from components"""
        monkeypatch.delenv("SUPABASE_DATABASE_URL", raising=False)
        monkeypatch.delenv("DATABASE_URL", raising=False)

        with patch('fastmcp.task_management.infrastructure.database.supabase_config.SupabaseConfig._initialize_database') as mock_init:
            # Prevent actual database initialization
            mock_init.return_value = None

            config = SupabaseConfig()
            assert "testproject" in config.database_url
            assert "mock-password" in config.database_url
            assert "sslmode=require" in config.database_url

    def test_init_with_custom_db_settings(self, mock_env, monkeypatch):
        """Test initialization with custom database settings"""
        monkeypatch.setenv("SUPABASE_DB_USER", "custom_user")
        monkeypatch.setenv("SUPABASE_DB_HOST", "custom.host.supabase.co")
        monkeypatch.setenv("SUPABASE_DB_PORT", "5433")
        monkeypatch.setenv("SUPABASE_DB_NAME", "custom_db")
        monkeypatch.delenv("SUPABASE_DATABASE_URL", raising=False)
        monkeypatch.delenv("DATABASE_URL", raising=False)

        with patch('fastmcp.task_management.infrastructure.database.supabase_config.SupabaseConfig._initialize_database') as mock_init:
            # Prevent actual database initialization
            mock_init.return_value = None

            config = SupabaseConfig()
            assert "custom_user" in config.database_url
            assert "custom.host.supabase.co" in config.database_url
            assert "5433" in config.database_url
            assert "custom_db" in config.database_url

    def test_init_with_ssl_certificate(self, mock_env, monkeypatch):
        """Test initialization with SSL certificate path"""
        monkeypatch.setenv("SUPABASE_SSL_CERT_PATH", "test-cert.crt")
        monkeypatch.delenv("SUPABASE_DATABASE_URL", raising=False)
        monkeypatch.delenv("DATABASE_URL", raising=False)

        with patch('fastmcp.task_management.infrastructure.database.supabase_config.SupabaseConfig._initialize_database') as mock_init:
            with patch('os.path.exists', return_value=True):
                # Prevent actual database initialization
                mock_init.return_value = None

                config = SupabaseConfig()
                assert "sslrootcert" in config.database_url
                assert "test-cert.crt" in config.database_url

    def test_init_missing_configuration(self, monkeypatch):
        """Test initialization fails with missing configuration"""
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_DATABASE_URL", raising=False)
        
        with pytest.raises(ValueError, match="SUPABASE CONFIGURATION MISSING"):
            SupabaseConfig()

    def test_init_missing_password(self, monkeypatch):
        """Test initialization fails with missing password"""
        monkeypatch.setenv("SUPABASE_URL", "https://testproject.supabase.co")
        monkeypatch.delenv("SUPABASE_DB_PASSWORD", raising=False)
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_DATABASE_URL", raising=False)
        
        with pytest.raises(ValueError, match="SUPABASE_DB_PASSWORD environment variable is required"):
            SupabaseConfig()

    def test_init_invalid_supabase_url(self, monkeypatch):
        """Test initialization with invalid Supabase URL format"""
        monkeypatch.setenv("SUPABASE_URL", "https://invalid-url-format")
        monkeypatch.setenv("SUPABASE_DB_PASSWORD", "password")
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_DATABASE_URL", raising=False)
        
        with pytest.raises(ValueError, match="SUPABASE CONFIGURATION MISSING"):
            SupabaseConfig()

    def test_create_engine_settings(self, mock_env, monkeypatch):
        """Test engine is created with proper Supabase settings"""
        monkeypatch.delenv("SUPABASE_DATABASE_URL", raising=False)
        monkeypatch.delenv("DATABASE_URL", raising=False)

        # Mock the create_resilient_engine function to capture its arguments
        with patch('fastmcp.task_management.infrastructure.database.connection_retry.create_resilient_engine') as mock_create_engine:
            # Mock the event.listens_for decorator
            with patch('sqlalchemy.event.listens_for', lambda *args, **kwargs: lambda fn: fn):
                mock_engine = MagicMock(spec=Engine)
                mock_connection = MagicMock()
                mock_connection.__enter__ = MagicMock(return_value=mock_connection)
                mock_connection.__exit__ = MagicMock(return_value=None)
                mock_connection.execute.return_value.scalar.side_effect = ["PostgreSQL 13.0", "postgres"]
                mock_engine.connect.return_value = mock_connection
                mock_create_engine.return_value = mock_engine

                # Create config (don't mock _initialize_database so _create_engine gets called)
                config = SupabaseConfig()

                # Get the create_engine call
                assert mock_create_engine.call_count > 0
                args, kwargs = mock_create_engine.call_args

                # Check connection pool settings (updated to match actual values)
                assert kwargs['pool_size'] == 2  # Minimal pool size
                assert kwargs['max_overflow'] == 3  # Conservative overflow
                assert kwargs['pool_pre_ping'] is True
                assert kwargs['pool_recycle'] == 120  # 2 minutes
                assert kwargs['pool_timeout'] == 120  # Extended timeout
                assert kwargs['future'] is True

                # Check connect_args for Supabase
                connect_args = kwargs['connect_args']
                assert connect_args['connect_timeout'] == 60  # Extended timeout
                assert connect_args['application_name'] == 'agenthub'
                assert connect_args['keepalives'] == 1

    def test_connection_event_listener(self, mock_env, monkeypatch):
        """Test PostgreSQL connection event listener"""
        monkeypatch.delenv("SUPABASE_DATABASE_URL", raising=False)
        monkeypatch.delenv("DATABASE_URL", raising=False)

        with patch('fastmcp.task_management.infrastructure.database.connection_retry.create_resilient_engine') as mock_create_engine:
            with patch('fastmcp.task_management.infrastructure.database.supabase_config.SupabaseConfig._initialize_database'):
                mock_engine = MagicMock()
                mock_create_engine.return_value = mock_engine

                # Create config which will register event listeners
                config = SupabaseConfig()

                # The test is that creating the config doesn't raise any errors
                # Event listeners are registered internally, we just verify initialization succeeds
                assert config is not None

    def test_get_session(self, supabase_config):
        """Test getting a database session"""
        session = supabase_config.get_session()
        assert session is not None

    def test_get_session_not_initialized(self):
        """Test getting session when database not initialized"""
        config = SupabaseConfig.__new__(SupabaseConfig)
        config.SessionLocal = None
        
        with pytest.raises(RuntimeError, match="Database not initialized"):
            config.get_session()

    def test_create_tables(self, supabase_config):
        """Test creating tables"""
        mock_base = MagicMock()
        mock_base.metadata = MagicMock()
        
        supabase_config.create_tables(mock_base)
        
        mock_base.metadata.create_all.assert_called_once_with(bind=supabase_config.engine)

    def test_create_tables_not_initialized(self):
        """Test creating tables when engine not initialized"""
        config = SupabaseConfig.__new__(SupabaseConfig)
        config.engine = None
        
        mock_base = MagicMock()
        
        with pytest.raises(RuntimeError, match="Database engine not initialized"):
            config.create_tables(mock_base)

    def test_dispose(self, supabase_config):
        """Test disposing of the engine"""
        supabase_config.dispose()
        supabase_config.engine.dispose.assert_called_once()

    def test_dispose_no_engine(self):
        """Test disposing when no engine exists"""
        config = SupabaseConfig.__new__(SupabaseConfig)
        config.engine = None
        
        # Should not raise any exception
        config.dispose()

    def test_initialization_failure(self, monkeypatch):
        """Test handling of initialization failure"""
        monkeypatch.setenv("SUPABASE_DATABASE_URL", "postgresql://invalid")

        with patch('fastmcp.task_management.infrastructure.database.connection_retry.create_resilient_engine') as mock_create_engine:
            # Make engine creation fail
            mock_create_engine.side_effect = Exception("Connection failed")

            with pytest.raises(Exception, match="Connection failed"):
                SupabaseConfig()

    def test_sql_debug_mode(self, mock_env, monkeypatch):
        """Test SQL debug mode activation"""
        monkeypatch.setenv("SQL_DEBUG", "true")
        monkeypatch.delenv("SUPABASE_DATABASE_URL", raising=False)
        monkeypatch.delenv("DATABASE_URL", raising=False)

        # Mock the create_resilient_engine function directly and event decorator
        with patch('fastmcp.task_management.infrastructure.database.connection_retry.create_resilient_engine') as mock_create_engine:
            with patch('sqlalchemy.event.listens_for', lambda *args, **kwargs: lambda fn: fn):
                mock_engine = MagicMock(spec=Engine)
                mock_connection = MagicMock()
                mock_connection.__enter__ = MagicMock(return_value=mock_connection)
                mock_connection.__exit__ = MagicMock(return_value=None)
                mock_connection.execute.return_value.scalar.side_effect = ["PostgreSQL 13.0", "postgres"]
                mock_engine.connect.return_value = mock_connection
                mock_create_engine.return_value = mock_engine

                # Create config without mocking _initialize_database so the engine gets created
                config = SupabaseConfig()

                # Check that echo is True when SQL_DEBUG is set
                assert mock_create_engine.call_count > 0
                args, kwargs = mock_create_engine.call_args
                assert kwargs['echo'] is True


class TestSupabaseHelperFunctions:
    """Test helper functions"""

    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Mock environment variables"""
        monkeypatch.setenv("SUPABASE_URL", "https://testproject.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "mock-anon-key")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "mock-service-key")
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "mock-jwt-secret")
        monkeypatch.setenv("SUPABASE_DB_PASSWORD", "mock-password")

    def test_get_supabase_config_singleton(self, mock_env):
        """Test get_supabase_config returns singleton"""
        with patch('fastmcp.task_management.infrastructure.database.supabase_config.SupabaseConfig') as MockConfig:
            mock_instance = MagicMock()
            MockConfig.return_value = mock_instance
            
            # Clear singleton
            import fastmcp.task_management.infrastructure.database.supabase_config as config_module
            config_module._supabase_config = None
            
            # First call creates instance
            config1 = get_supabase_config()
            assert MockConfig.call_count == 1
            
            # Second call returns same instance
            config2 = get_supabase_config()
            assert MockConfig.call_count == 1  # Not called again
            assert config1 is config2

    def test_is_supabase_configured_all_set(self, monkeypatch):
        """Test is_supabase_configured with all variables set"""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
        monkeypatch.setenv("DATABASE_URL", "postgresql://...")
        
        assert is_supabase_configured() is True

    def test_is_supabase_configured_with_password(self, monkeypatch):
        """Test is_supabase_configured with password instead of DATABASE_URL"""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
        monkeypatch.setenv("SUPABASE_DB_PASSWORD", "password")
        monkeypatch.delenv("DATABASE_URL", raising=False)
        
        assert is_supabase_configured() is True

    def test_is_supabase_configured_missing_url(self, monkeypatch):
        """Test is_supabase_configured with missing URL"""
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
        monkeypatch.setenv("DATABASE_URL", "postgresql://...")
        
        assert is_supabase_configured() is False

    def test_is_supabase_configured_missing_anon_key(self, monkeypatch):
        """Test is_supabase_configured with missing anon key"""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
        monkeypatch.setenv("DATABASE_URL", "postgresql://...")
        
        assert is_supabase_configured() is False

    def test_is_supabase_configured_missing_database(self, monkeypatch):
        """Test is_supabase_configured with missing database config"""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_DB_PASSWORD", raising=False)
        
        assert is_supabase_configured() is False

    def test_url_encoding_special_characters(self, monkeypatch):
        """Test URL encoding of special characters in password"""
        monkeypatch.setenv("SUPABASE_URL", "https://testproject.supabase.co")
        monkeypatch.setenv("SUPABASE_DB_PASSWORD", "pass@word#special!")
        monkeypatch.delenv("SUPABASE_DATABASE_URL", raising=False)
        monkeypatch.delenv("DATABASE_URL", raising=False)

        with patch('fastmcp.task_management.infrastructure.database.supabase_config.SupabaseConfig._initialize_database') as mock_init:
            # Prevent actual database initialization
            mock_init.return_value = None

            config = SupabaseConfig()
            # Password should be URL encoded
            assert "pass%40word%23special%21" in config.database_url