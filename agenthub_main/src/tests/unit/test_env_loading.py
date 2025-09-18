"""Test environment file loading functionality."""

import os
import sys
from pathlib import Path
import pytest
from unittest.mock import patch, mock_open

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_env_file_loads_from_project_root():
    """Test that .env file loads correctly from project root."""
    from dotenv import load_dotenv

    # Clear any existing env vars that we'll test
    test_vars = ['DATABASE_HOST', 'DATABASE_PORT', 'DATABASE_NAME', 'DATABASE_USER']
    for var in test_vars:
        os.environ.pop(var, None)

    # Load .env file from project root
    project_root = Path(__file__).parent.parent.parent.parent.parent
    env_file = project_root / ".env"

    assert env_file.exists(), f".env file not found at {env_file}"

    # Load the env file
    load_dotenv(env_file)

    # Verify critical database variables are loaded
    assert os.getenv('DATABASE_HOST') is not None, "DATABASE_HOST not loaded from .env"
    assert os.getenv('DATABASE_PORT') is not None, "DATABASE_PORT not loaded from .env"
    assert os.getenv('DATABASE_NAME') is not None, "DATABASE_NAME not loaded from .env"

    # Verify values match expected format
    db_host = os.getenv('DATABASE_HOST')
    db_port = os.getenv('DATABASE_PORT')
    db_name = os.getenv('DATABASE_NAME')

    assert db_host in ['localhost', '127.0.0.1', 'agenthub-postgres'], f"Unexpected DATABASE_HOST: {db_host}"
    assert db_port.isdigit(), f"DATABASE_PORT should be numeric, got: {db_port}"
    assert len(db_name) > 0, "DATABASE_NAME should not be empty"


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

    # Verify default values
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000


def test_database_config_loads_env_vars():
    """Test that database configuration loads environment variables."""
    from dotenv import load_dotenv

    # Ensure .env is loaded
    project_root = Path(__file__).parent.parent.parent.parent.parent
    env_file = project_root / ".env"
    load_dotenv(env_file, override=True)

    # Import after loading env to ensure vars are available
    from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig

    # Get database configuration
    db_config = DatabaseConfig.get_database_config()

    # Verify configuration is returned
    assert db_config is not None
    assert 'url' in db_config or 'database_url' in db_config

    # Check if it's using PostgreSQL (from .env)
    if 'url' in db_config:
        db_url = db_config['url']
    else:
        db_url = db_config.get('database_url', '')

    # Should be using PostgreSQL from Docker
    assert 'postgresql' in db_url or 'postgres' in db_url, f"Expected PostgreSQL URL, got: {db_url}"


def test_env_file_precedence():
    """Test that .env file takes precedence over .env.dev when both exist."""
    from fastmcp.settings import Settings

    # Settings should use .env as configured
    settings = Settings()

    # Verify model_config uses .env
    assert settings.model_config.get('env_file') == '.env'


def test_env_variables_accessible_in_app():
    """Test that environment variables are accessible throughout the application."""
    from dotenv import load_dotenv
    import os

    # Load .env
    project_root = Path(__file__).parent.parent.parent.parent.parent
    env_file = project_root / ".env"
    load_dotenv(env_file, override=True)

    # Test critical variables
    critical_vars = {
        'DATABASE_TYPE': 'postgresql',
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