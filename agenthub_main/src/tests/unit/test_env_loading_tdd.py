"""
TDD Test Suite for Environment File Loading
Written BEFORE implementation to define expected behavior
"""

import os
import sys
import tempfile
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock, mock_open

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestEnvironmentLoading:
    """TDD tests for environment file loading functionality."""

    def test_settings_should_load_env_from_root(self):
        """Settings should load .env file from project root, not from nested paths."""
        from fastmcp.settings import Settings

        # Create settings instance
        settings = Settings()

        # Should use env file from project root
        env_file = settings.model_config.get('env_file')
        assert '.env' in env_file
        assert Path(env_file).exists()

    def test_settings_should_not_use_complex_path_resolution(self):
        """Settings should use simple path resolution for env files."""
        from fastmcp.settings import Settings

        # Read the settings file to check path resolution approach
        settings_file = Path(__file__).parent.parent.parent / "fastmcp" / "settings.py"
        content = settings_file.read_text()

        # Should have project root defined for finding env files
        assert "_project_root" in content
        # Should check for .env.dev existence
        assert ".env.dev" in content

    def test_env_should_load_database_variables(self):
        """Environment should provide all required database variables."""
        from dotenv import load_dotenv

        # Load .env file from project root
        project_root = Path(__file__).parent.parent.parent.parent.parent
        env_file = project_root / ".env"
        load_dotenv(env_file, override=True)

        # All database variables must be present
        required_vars = [
            'DATABASE_TYPE',
            'DATABASE_HOST',
            'DATABASE_PORT',
            'DATABASE_NAME',
            'DATABASE_USER',
            'DATABASE_PASSWORD'
        ]

        for var in required_vars:
            value = os.getenv(var)
            assert value is not None, f"Required variable {var} not loaded from .env"
            assert len(value) > 0, f"Variable {var} should not be empty"

    def test_database_config_should_use_env_variables(self):
        """DatabaseConfig should correctly use environment variables."""
        from dotenv import load_dotenv
        project_root = Path(__file__).parent.parent.parent.parent.parent
        env_file = project_root / ".env"
        load_dotenv(env_file, override=True)

        from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig

        db_config = DatabaseConfig()
        config = db_config.get_database_info()

        # Should return valid config
        assert config is not None

        # Should contain database URL
        db_url = config.get('url') or config.get('database_url')
        assert db_url is not None

        # Should be PostgreSQL (from .env)
        assert 'postgresql' in db_url or 'postgres' in db_url

        # Should contain host and port from env
        assert os.getenv('DATABASE_HOST') in db_url
        assert os.getenv('DATABASE_PORT') in db_url

    def test_env_dev_should_not_interfere(self):
        """Presence of .env.dev should not break .env loading."""
        from fastmcp.settings import Settings

        # Settings should work with either .env.dev or .env
        settings = Settings()
        env_file = settings.model_config.get('env_file')

        # Should use one of the env files
        assert '.env' in env_file
        assert Path(env_file).exists()

    def test_application_should_connect_to_database(self):
        """Application should successfully connect to database using env config."""
        from dotenv import load_dotenv
        project_root = Path(__file__).parent.parent.parent.parent.parent
        env_file = project_root / ".env"
        load_dotenv(env_file, override=True)

        from sqlalchemy import create_engine, text
        from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig

        db_config = DatabaseConfig()
        config = db_config.get_database_info()
        db_url = config.get('url') or config.get('database_url')

        # Should be able to create engine
        engine = create_engine(db_url)

        # Should be able to connect
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

    def test_env_should_override_defaults(self):
        """Environment variables should override default settings."""
        # Set a test env variable
        os.environ['FASTMCP_PORT'] = '9999'

        from fastmcp.settings import Settings
        settings = Settings()

        # Should use env value instead of default
        assert settings.port == 9999

        # Cleanup
        del os.environ['FASTMCP_PORT']

    def test_missing_env_file_should_use_defaults(self):
        """If .env file is missing, should still work with defaults."""
        with patch('pathlib.Path.exists', return_value=False):
            from fastmcp.settings import Settings

            # Should not crash
            settings = Settings()

            # Should have default values
            assert settings.host == "0.0.0.0"
            assert settings.port == 8000

    def test_malformed_env_should_not_crash(self):
        """Malformed .env file should not crash the application."""
        # Create temp .env with malformed content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("INVALID LINE WITHOUT EQUALS\n")
            f.write("=VALUE_WITHOUT_KEY\n")
            f.write("VALID_KEY=valid_value\n")
            temp_env = f.name

        try:
            with patch('fastmcp.settings.Settings.model_config',
                      {'env_file': temp_env, 'env_prefixes': ['FASTMCP_']}):
                from fastmcp.settings import Settings

                # Should not crash
                settings = Settings()
                assert settings is not None
        finally:
            os.unlink(temp_env)

    def test_env_loading_should_be_consistent(self):
        """Environment loading should be consistent across modules."""
        from dotenv import load_dotenv
        import importlib

        # Load env from project root
        project_root = Path(__file__).parent.parent.parent.parent.parent
        env_file = project_root / ".env"
        load_dotenv(env_file, override=True)

        # Get value directly
        direct_host = os.getenv('DATABASE_HOST')

        # Get value through DatabaseConfig
        from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig
        db_config = DatabaseConfig()
        config = db_config.get_database_info()

        # Parse host from URL
        db_url = config.get('url') or config.get('database_url')

        # Both should use same host
        assert direct_host in db_url


class TestEnvironmentPriority:
    """Test environment variable priority and precedence."""

    def test_env_file_priority_order(self):
        """Test that .env.dev takes priority over .env when both exist."""
        # Updated test - .env.dev should be used when it exists
        from fastmcp.settings import Settings

        settings = Settings()
        env_file = settings.model_config.get('env_file')

        project_root = Path(__file__).parent.parent.parent.parent.parent
        env_dev_file = project_root / ".env.dev"

        # If .env.dev exists, it should be used
        if env_dev_file.exists():
            assert '.env.dev' in env_file
        else:
            assert '.env' in env_file

    def test_explicit_env_vars_override_file(self):
        """Explicitly set environment variables should override .env file."""
        # Set explicit env var
        os.environ['DATABASE_HOST'] = 'explicit-host'

        from dotenv import load_dotenv

        # Load .env without override
        project_root = Path(__file__).parent.parent.parent.parent.parent
        env_file = project_root / ".env"
        load_dotenv(env_file, override=False)

        # Should keep explicit value
        assert os.getenv('DATABASE_HOST') == 'explicit-host'

        # Cleanup
        del os.environ['DATABASE_HOST']

    def test_env_var_types_conversion(self):
        """Test that env variables are correctly converted to appropriate types."""
        os.environ['FASTMCP_PORT'] = '8888'
        os.environ['FASTMCP_DEBUG'] = 'true'

        from fastmcp.settings import Settings
        settings = Settings()

        # Should convert to int
        assert isinstance(settings.port, int)
        assert settings.port == 8888

        # Should convert to bool
        assert isinstance(settings.debug, bool)
        assert settings.debug is True

        # Cleanup
        del os.environ['FASTMCP_PORT']
        del os.environ['FASTMCP_DEBUG']


class TestDatabaseConnection:
    """Test database connection with environment configuration."""

    def test_postgresql_connection_string_format(self):
        """Test PostgreSQL connection string is correctly formatted."""
        from dotenv import load_dotenv
        project_root = Path(__file__).parent.parent.parent.parent.parent
        env_file = project_root / ".env"
        load_dotenv(env_file, override=True)

        from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig

        db_config = DatabaseConfig()
        config = db_config.get_database_info()
        db_url = config.get('url') or config.get('database_url')

        # Should have PostgreSQL prefix
        assert db_url.startswith('postgresql://') or db_url.startswith('postgresql+')

        # Should contain all components
        assert '@' in db_url  # user:pass@host
        assert ':' in db_url.split('@')[1]  # host:port
        assert '/' in db_url.split('@')[1]  # port/database

    def test_database_pool_configuration(self):
        """Test database connection pool is properly configured."""
        from dotenv import load_dotenv
        project_root = Path(__file__).parent.parent.parent.parent.parent
        env_file = project_root / ".env"
        load_dotenv(env_file, override=True)

        from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig

        db_config = DatabaseConfig()
        config = db_config.get_database_info()

        # Should have pool settings
        if 'pool_size' in config:
            assert isinstance(config['pool_size'], int)
            assert config['pool_size'] > 0

        if 'max_overflow' in config:
            assert isinstance(config['max_overflow'], int)
            assert config['max_overflow'] >= 0


class TestErrorHandling:
    """Test error handling in environment loading."""

    def test_missing_required_database_vars(self):
        """Test handling of missing required database variables."""
        # Temporarily remove a required var
        original = os.environ.pop('DATABASE_HOST', None)

        try:
            from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig

            # Should handle gracefully (either default or error)
            db_config = DatabaseConfig()
            config = db_config.get_database_info()

            # Should still return config (might use defaults)
            assert config is not None

        finally:
            # Restore
            if original:
                os.environ['DATABASE_HOST'] = original

    def test_invalid_port_number(self):
        """Test handling of invalid port numbers."""
        os.environ['DATABASE_PORT'] = 'not-a-number'

        try:
            from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig

            # Should handle invalid port gracefully
            db_config = DatabaseConfig()
            config = db_config.get_database_info()

            # Should either use default or raise clear error
            assert config is not None

        finally:
            # Restore valid port
            from dotenv import load_dotenv
            project_root = Path(__file__).parent.parent.parent.parent.parent
            env_file = project_root / ".env"
            load_dotenv(env_file, override=True)


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])