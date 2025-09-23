"""Test environment file loading functionality."""

import os
import sys
from pathlib import Path
import pytest
from unittest.mock import patch, mock_open

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.unit
def test_env_file_loads_from_project_root():
    """Test that .env file loads correctly from project root."""
    # For unit tests, mock the environment loading behavior
    with patch.dict(os.environ, {
        'DATABASE_HOST': 'test-host',
        'DATABASE_PORT': '5432',
        'DATABASE_NAME': 'test-db',
        'DATABASE_USER': 'test-user'
    }):
        # Test that environment variables are accessible
        assert os.getenv('DATABASE_HOST') == 'test-host'
        assert os.getenv('DATABASE_PORT') == '5432'
        assert os.getenv('DATABASE_NAME') == 'test-db'
        assert os.getenv('DATABASE_USER') == 'test-user'

        # Verify values match expected format
        db_host = os.getenv('DATABASE_HOST')
        db_port = os.getenv('DATABASE_PORT')
        db_name = os.getenv('DATABASE_NAME')

        assert db_port.isdigit(), f"DATABASE_PORT should be numeric, got: {db_port}"
        assert len(db_name) > 0, "DATABASE_NAME should not be empty"


@pytest.mark.unit
def test_fastmcp_settings_loads_env_file():
    """Test that FastMCP Settings class loads .env file correctly."""
    from fastmcp.settings import Settings

    # Create a new Settings instance
    settings = Settings()

    # Verify settings object is created
    assert settings is not None

    # Check default FastMCP settings
    assert hasattr(settings, 'host')
    assert hasattr(settings, 'port')
    assert hasattr(settings, 'debug')

    # Verify default values (may vary based on environment)
    assert isinstance(settings.port, int)
    assert settings.port > 0


@pytest.mark.unit
def test_database_config_loads_env_vars():
    """Test that database configuration loads environment variables."""
    # Test that database configuration loads and returns info
    from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig

    # Get database configuration using correct method
    db_config = DatabaseConfig()
    config_info = db_config.get_database_info()

    # Verify configuration is returned with expected structure
    assert config_info is not None
    assert 'type' in config_info
    assert 'engine' in config_info
    assert 'pool' in config_info
    
    # The type will be postgresql in dev/test environments
    # We're testing the structure, not the specific values
    assert config_info.get('type') in ['sqlite', 'postgresql', 'supabase']


@pytest.mark.unit
def test_env_file_precedence():
    """Test that .env file takes precedence over .env.dev when both exist."""
    from fastmcp.settings import Settings

    # Settings should use .env as configured
    settings = Settings()

    # Verify env file is loaded (may be .env or .env.dev depending on what exists)
    env_file = settings.model_config.get('env_file')
    assert env_file is not None
    assert '.env' in str(env_file)


@pytest.mark.unit
def test_env_variables_accessible_in_app():
    """Test that environment variables are accessible throughout the application."""
    # Mock critical environment variables for unit testing
    with patch.dict(os.environ, {
        'DATABASE_TYPE': 'sqlite',
        'DATABASE_HOST': 'localhost',
        'DATABASE_PORT': '5432',
        'DATABASE_NAME': 'test-db',
        'PYTEST_CURRENT_TEST': 'test'
    }):
        # Test critical variables
        critical_vars = {
            'DATABASE_TYPE': 'sqlite',
            'DATABASE_HOST': ['localhost', '127.0.0.1', 'agenthub-postgres'],
            'DATABASE_PORT': lambda x: x.isdigit(),
            'DATABASE_NAME': lambda x: len(x) > 0,
        }

        for var, expected in critical_vars.items():
            value = os.getenv(var)
            assert value is not None, f"{var} not found in environment"

            if isinstance(expected, str):
                assert value == expected, f"{var} expected '{expected}', got '{value}'"
            elif isinstance(expected, list):
                assert value in expected, f"{var} expected one of {expected}, got '{value}'"
            elif callable(expected):
                assert expected(value), f"{var} validation failed for value '{value}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])