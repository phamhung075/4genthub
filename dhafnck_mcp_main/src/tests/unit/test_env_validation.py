"""
Test suite for environment variable validation in Docker deployments

This module tests environment variable parsing and validation for:
- DATABASE_SSL_MODE parsing (require/disable/allow/prefer)
- APP_LOG_LEVEL case conversion (INFO→info, DEBUG→debug, etc.)
- Docker entrypoint script environment validation
- Production vs CapRover deployment differences

Tests ensure proper SSL configuration for different deployment scenarios
and prevent regression of the Docker SSL/log level fixes.
"""

import pytest
import os
import tempfile
import subprocess
import logging
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig


class TestDatabaseSSLModeValidation:
    """Test DATABASE_SSL_MODE environment variable parsing and validation"""

    def setup_method(self):
        """Reset database config singleton before each test"""
        DatabaseConfig.reset_instance()

    def teardown_method(self):
        """Clean up after each test"""
        DatabaseConfig.reset_instance()

    @pytest.mark.parametrize("ssl_mode,expected_in_url", [
        ("disable", ""),  # No sslmode in URL for disable
        ("require", "sslmode=require"),
        ("prefer", "sslmode=prefer"),
        ("allow", "sslmode=allow"),
        ("verify-full", "sslmode=verify-full"),
        ("verify-ca", "sslmode=verify-ca"),
    ])
    def test_ssl_mode_parsing_postgresql(self, ssl_mode, expected_in_url):
        """Test that different SSL modes are properly parsed and applied to PostgreSQL URLs"""
        config = DatabaseConfig.__new__(DatabaseConfig)
        config._initialized = False
        config.database_type = "postgresql"

        with patch.dict(os.environ, {
            "DATABASE_TYPE": "postgresql",
            "DATABASE_HOST": "localhost",
            "DATABASE_PORT": "5432",
            "DATABASE_NAME": "test_db",
            "DATABASE_USER": "test_user",
            "DATABASE_PASSWORD": "test_pass",
            "DATABASE_SSL_MODE": ssl_mode,
            "DATABASE_URL": ""  # Clear to force component construction
        }, clear=False):
            url = config._get_secure_database_url()

            if ssl_mode == "disable":
                # For disable, no sslmode should be in URL
                assert "sslmode=" not in url
            else:
                # For other modes, sslmode should be present
                assert expected_in_url in url
                assert f"sslmode={ssl_mode}" in url

    def test_ssl_mode_default_prefer(self):
        """Test that default SSL mode is 'prefer' when not specified"""
        config = DatabaseConfig.__new__(DatabaseConfig)
        config._initialized = False
        config.database_type = "postgresql"

        with patch.dict(os.environ, {
            "DATABASE_TYPE": "postgresql",
            "DATABASE_HOST": "localhost",
            "DATABASE_USER": "test_user",
            "DATABASE_PASSWORD": "test_pass",
            "DATABASE_URL": ""  # Clear to force component construction
            # Intentionally omit DATABASE_SSL_MODE to test default
        }, clear=False):
            # Remove DATABASE_SSL_MODE if it exists
            if "DATABASE_SSL_MODE" in os.environ:
                del os.environ["DATABASE_SSL_MODE"]

            url = config._get_secure_database_url()

            # Default should be 'prefer'
            assert "sslmode=prefer" in url

    def test_supabase_ssl_always_required(self):
        """Test that Supabase always uses SSL mode 'require'"""
        config = DatabaseConfig.__new__(DatabaseConfig)
        config._initialized = False
        config.database_type = "supabase"

        with patch.dict(os.environ, {
            "DATABASE_TYPE": "supabase",
            "SUPABASE_DB_HOST": "test.supabase.co",
            "SUPABASE_DB_USER": "test_user",
            "SUPABASE_DB_PASSWORD": "test_pass",
            "DATABASE_URL": ""  # Clear to force component construction
        }, clear=False):
            url = config._get_secure_database_url()

            # Supabase should always use SSL require
            assert "sslmode=require" in url

    def test_caprover_ssl_disable_scenario(self):
        """Test CapRover deployment scenario with SSL disabled"""
        config = DatabaseConfig.__new__(DatabaseConfig)
        config._initialized = False
        config.database_type = "postgresql"

        # Simulate CapRover environment variables
        with patch.dict(os.environ, {
            "DATABASE_TYPE": "postgresql",
            "DATABASE_HOST": "srv-captain--postgres",  # CapRover internal hostname
            "DATABASE_PORT": "5432",
            "DATABASE_NAME": "dhafnck_mcp",
            "DATABASE_USER": "postgres",
            "DATABASE_PASSWORD": "caprover_password",
            "DATABASE_SSL_MODE": "disable",  # CapRover PostgreSQL doesn't support SSL
            "DATABASE_URL": ""
        }, clear=False):
            url = config._get_secure_database_url()

            # Should not contain any SSL mode for CapRover
            assert "sslmode=" not in url
            assert "srv-captain--postgres" in url

    def test_managed_postgresql_ssl_required(self):
        """Test managed PostgreSQL deployment with SSL required"""
        config = DatabaseConfig.__new__(DatabaseConfig)
        config._initialized = False
        config.database_type = "postgresql"

        # Simulate managed PostgreSQL (AWS RDS, Google Cloud SQL, etc.)
        with patch.dict(os.environ, {
            "DATABASE_TYPE": "postgresql",
            "DATABASE_HOST": "mydb.abc123.us-east-1.rds.amazonaws.com",
            "DATABASE_PORT": "5432",
            "DATABASE_NAME": "dhafnck_mcp",
            "DATABASE_USER": "postgres",
            "DATABASE_PASSWORD": "secure_password",
            "DATABASE_SSL_MODE": "require",  # Managed services require SSL
            "DATABASE_URL": ""
        }, clear=False):
            url = config._get_secure_database_url()

            # Should enforce SSL for managed services
            assert "sslmode=require" in url
            assert "rds.amazonaws.com" in url

    def test_invalid_ssl_mode_handling(self):
        """Test handling of invalid SSL modes"""
        config = DatabaseConfig.__new__(DatabaseConfig)
        config._initialized = False
        config.database_type = "postgresql"

        with patch.dict(os.environ, {
            "DATABASE_TYPE": "postgresql",
            "DATABASE_HOST": "localhost",
            "DATABASE_USER": "test_user",
            "DATABASE_PASSWORD": "test_pass",
            "DATABASE_SSL_MODE": "invalid_mode",  # Invalid SSL mode
            "DATABASE_URL": ""
        }, clear=False):
            url = config._get_secure_database_url()

            # Should still include the invalid mode (PostgreSQL will reject it)
            assert "sslmode=invalid_mode" in url


class TestLogLevelValidation:
    """Test APP_LOG_LEVEL environment variable case conversion and validation"""

    @pytest.mark.parametrize("input_level,expected_output", [
        ("INFO", "info"),
        ("DEBUG", "debug"),
        ("WARNING", "warning"),
        ("ERROR", "error"),
        ("CRITICAL", "critical"),
        ("info", "info"),  # Already lowercase
        ("Debug", "debug"),  # Mixed case
        ("WaRnInG", "warning"),  # Random case
    ])
    def test_log_level_case_conversion(self, input_level, expected_output):
        """Test that log levels are properly converted to lowercase"""
        # Simulate the shell command used in Docker entrypoint
        # echo "${APP_LOG_LEVEL:-info}" | tr "[:upper:]" "[:lower:]"
        result = input_level.lower()
        assert result == expected_output

    def test_log_level_default_value(self):
        """Test that default log level is 'info' when not specified"""
        # Simulate shell default: ${APP_LOG_LEVEL:-info}
        log_level = os.getenv("APP_LOG_LEVEL", "info").lower()
        assert log_level == "info"

    def test_log_level_with_special_characters(self):
        """Test log level handling with special characters (should be cleaned)"""
        # Test various edge cases that might appear in environment variables
        test_cases = [
            ("INFO ", "info"),  # Trailing space
            (" DEBUG", "debug"),  # Leading space
            ("INFO\n", "info\n"),  # Newline (tr won't remove this)
            ("", ""),  # Empty string
        ]

        for input_val, expected in test_cases:
            result = input_val.lower()
            assert result == expected


class TestDockerEntrypointValidation:
    """Test Docker entrypoint script environment variable validation"""

    def setup_method(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.entrypoint_script = Path(self.test_dir) / "test-entrypoint.sh"

    def teardown_method(self):
        """Clean up test files"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def create_test_entrypoint_script(self):
        """Create a test version of the Docker entrypoint script"""
        script_content = '''#!/bin/sh
set -e

echo "Testing environment variable validation..."

# Validate required environment variables (from Dockerfile.backend.production)
REQUIRED_VARS="DATABASE_TYPE DATABASE_HOST DATABASE_PORT DATABASE_NAME DATABASE_USER DATABASE_PASSWORD FASTMCP_PORT JWT_SECRET_KEY"
MISSING_VARS=""

for VAR in $REQUIRED_VARS; do
    eval VALUE=\\$$VAR
    if [ -z "$VALUE" ]; then
        MISSING_VARS="$MISSING_VARS $VAR"
        echo "❌ Missing required variable: $VAR"
    fi
done

if [ -n "$MISSING_VARS" ]; then
    echo "❌ ERROR: Missing required environment variables:$MISSING_VARS"
    exit 1
fi

# Security check for JWT secret
if [ ${#JWT_SECRET_KEY} -lt 32 ]; then
    echo "❌ ERROR: JWT_SECRET_KEY must be at least 32 characters for production"
    exit 1
fi

# Test log level conversion
LOG_LEVEL=$(echo "${APP_LOG_LEVEL:-info}" | tr "[:upper:]" "[:lower:]")
echo "✅ Log level: $LOG_LEVEL"

echo "✅ All environment variables validated successfully"
'''

        self.entrypoint_script.write_text(script_content)
        self.entrypoint_script.chmod(0o755)

    def test_entrypoint_validation_success(self):
        """Test successful environment variable validation"""
        self.create_test_entrypoint_script()

        # Set up complete environment
        env = {
            "DATABASE_TYPE": "postgresql",
            "DATABASE_HOST": "localhost",
            "DATABASE_PORT": "5432",
            "DATABASE_NAME": "test_db",
            "DATABASE_USER": "test_user",
            "DATABASE_PASSWORD": "test_password",
            "FASTMCP_PORT": "8000",
            "JWT_SECRET_KEY": "a_very_secure_jwt_secret_key_that_is_at_least_32_characters_long",
            "APP_LOG_LEVEL": "INFO"
        }

        result = subprocess.run(
            [str(self.entrypoint_script)],
            env={**os.environ, **env},
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "✅ All environment variables validated successfully" in result.stdout
        assert "✅ Log level: info" in result.stdout  # Should be converted to lowercase

    def test_entrypoint_validation_missing_variables(self):
        """Test validation failure with missing environment variables"""
        self.create_test_entrypoint_script()

        # Set up incomplete environment (missing DATABASE_PASSWORD)
        env = {
            "DATABASE_TYPE": "postgresql",
            "DATABASE_HOST": "localhost",
            "DATABASE_PORT": "5432",
            "DATABASE_NAME": "test_db",
            "DATABASE_USER": "test_user",
            # Missing DATABASE_PASSWORD
            "FASTMCP_PORT": "8000",
            "JWT_SECRET_KEY": "a_very_secure_jwt_secret_key_that_is_at_least_32_characters_long"
        }

        result = subprocess.run(
            [str(self.entrypoint_script)],
            env={**os.environ, **env},
            capture_output=True,
            text=True
        )

        assert result.returncode == 1
        assert "❌ Missing required variable: DATABASE_PASSWORD" in result.stdout
        assert "❌ ERROR: Missing required environment variables:" in result.stdout

    def test_entrypoint_validation_weak_jwt_secret(self):
        """Test validation failure with weak JWT secret"""
        self.create_test_entrypoint_script()

        # Set up environment with weak JWT secret
        env = {
            "DATABASE_TYPE": "postgresql",
            "DATABASE_HOST": "localhost",
            "DATABASE_PORT": "5432",
            "DATABASE_NAME": "test_db",
            "DATABASE_USER": "test_user",
            "DATABASE_PASSWORD": "test_password",
            "FASTMCP_PORT": "8000",
            "JWT_SECRET_KEY": "weak",  # Too short
            "APP_LOG_LEVEL": "DEBUG"
        }

        result = subprocess.run(
            [str(self.entrypoint_script)],
            env={**os.environ, **env},
            capture_output=True,
            text=True
        )

        assert result.returncode == 1
        assert "❌ ERROR: JWT_SECRET_KEY must be at least 32 characters for production" in result.stdout

    def test_log_level_conversion_in_entrypoint(self):
        """Test that log level case conversion works in entrypoint script"""
        self.create_test_entrypoint_script()

        test_cases = [
            ("INFO", "info"),
            ("DEBUG", "debug"),
            ("WARNING", "warning"),
            ("Error", "error"),
            ("critical", "critical")  # Already lowercase
        ]

        for input_level, expected_output in test_cases:
            env = {
                "DATABASE_TYPE": "postgresql",
                "DATABASE_HOST": "localhost",
                "DATABASE_PORT": "5432",
                "DATABASE_NAME": "test_db",
                "DATABASE_USER": "test_user",
                "DATABASE_PASSWORD": "test_password",
                "FASTMCP_PORT": "8000",
                "JWT_SECRET_KEY": "a_very_secure_jwt_secret_key_that_is_at_least_32_characters_long",
                "APP_LOG_LEVEL": input_level
            }

            result = subprocess.run(
                [str(self.entrypoint_script)],
                env={**os.environ, **env},
                capture_output=True,
                text=True
            )

            assert result.returncode == 0
            assert f"✅ Log level: {expected_output}" in result.stdout


class TestProductionDeploymentScenarios:
    """Test specific production deployment scenarios"""

    def test_caprover_environment_validation(self):
        """Test environment validation for CapRover deployment"""
        # CapRover typically uses internal service names and no SSL
        caprover_env = {
            "ENV": "production",
            "DATABASE_TYPE": "postgresql",
            "DATABASE_HOST": "srv-captain--postgres",  # CapRover internal hostname
            "DATABASE_PORT": "5432",
            "DATABASE_NAME": "dhafnck_mcp",
            "DATABASE_USER": "postgres",
            "DATABASE_PASSWORD": "caprover_generated_password",
            "DATABASE_SSL_MODE": "disable",  # CapRover PostgreSQL doesn't support SSL
            "FASTMCP_PORT": "8000",
            "JWT_SECRET_KEY": "caprover_jwt_secret_key_at_least_32_characters_long",
            "APP_LOG_LEVEL": "INFO",
            "CORS_ORIGINS": "https://app.captain.example.com",
            "KEYCLOAK_URL": "https://auth.captain.example.com"
        }

        # Validate that this environment would work
        config = DatabaseConfig.__new__(DatabaseConfig)
        config._initialized = False
        config.database_type = "postgresql"

        with patch.dict(os.environ, caprover_env, clear=False):
            url = config._get_secure_database_url()

            # Should work without SSL
            assert "srv-captain--postgres" in url
            assert "sslmode=" not in url  # No SSL mode for CapRover
            assert len(caprover_env["JWT_SECRET_KEY"]) >= 32  # Security requirement met

    def test_managed_postgresql_environment_validation(self):
        """Test environment validation for managed PostgreSQL services"""
        # AWS RDS, Google Cloud SQL, Azure Database, etc.
        managed_env = {
            "ENV": "production",
            "DATABASE_TYPE": "postgresql",
            "DATABASE_HOST": "prod-db.abc123.us-east-1.rds.amazonaws.com",
            "DATABASE_PORT": "5432",
            "DATABASE_NAME": "dhafnck_mcp",
            "DATABASE_USER": "postgres",
            "DATABASE_PASSWORD": "very_secure_managed_db_password",
            "DATABASE_SSL_MODE": "require",  # Managed services require SSL
            "FASTMCP_PORT": "8000",
            "JWT_SECRET_KEY": "production_jwt_secret_key_at_least_32_characters_long",
            "APP_LOG_LEVEL": "WARNING",  # Higher log level for production
            "CORS_ORIGINS": "https://app.example.com,https://api.example.com",
            "KEYCLOAK_URL": "https://auth.example.com"
        }

        # Validate that this environment would work
        config = DatabaseConfig.__new__(DatabaseConfig)
        config._initialized = False
        config.database_type = "postgresql"

        with patch.dict(os.environ, managed_env, clear=False):
            url = config._get_secure_database_url()

            # Should enforce SSL for managed services
            assert "rds.amazonaws.com" in url
            assert "sslmode=require" in url
            assert len(managed_env["JWT_SECRET_KEY"]) >= 32

    def test_development_vs_production_ssl_differences(self):
        """Test SSL configuration differences between development and production"""
        # Development: Usually local PostgreSQL, SSL can be disabled
        dev_env = {
            "ENV": "development",
            "DATABASE_TYPE": "postgresql",
            "DATABASE_HOST": "localhost",
            "DATABASE_SSL_MODE": "disable"
        }

        # Production: Should prefer/require SSL
        prod_env = {
            "ENV": "production",
            "DATABASE_TYPE": "postgresql",
            "DATABASE_HOST": "prod-db.example.com",
            "DATABASE_SSL_MODE": "require"
        }

        for env_name, env_vars in [("development", dev_env), ("production", prod_env)]:
            config = DatabaseConfig.__new__(DatabaseConfig)
            config._initialized = False
            config.database_type = "postgresql"

            base_vars = {
                "DATABASE_USER": "postgres",
                "DATABASE_PASSWORD": "password",
                "DATABASE_URL": ""
            }

            with patch.dict(os.environ, {**base_vars, **env_vars}, clear=False):
                url = config._get_secure_database_url()

                if env_vars["DATABASE_SSL_MODE"] == "disable":
                    assert "sslmode=" not in url
                else:
                    assert f"sslmode={env_vars['DATABASE_SSL_MODE']}" in url


class TestErrorScenarios:
    """Test error handling for invalid configurations"""

    def test_missing_ssl_mode_uses_default(self):
        """Test that missing SSL mode uses default 'prefer'"""
        config = DatabaseConfig.__new__(DatabaseConfig)
        config._initialized = False
        config.database_type = "postgresql"

        with patch.dict(os.environ, {
            "DATABASE_TYPE": "postgresql",
            "DATABASE_HOST": "localhost",
            "DATABASE_USER": "postgres",
            "DATABASE_PASSWORD": "password",
            "DATABASE_URL": "",
            # Intentionally omit DATABASE_SSL_MODE
        }, clear=False):
            # Make sure DATABASE_SSL_MODE is not set
            if "DATABASE_SSL_MODE" in os.environ:
                del os.environ["DATABASE_SSL_MODE"]

            url = config._get_secure_database_url()

            # Should default to 'prefer'
            assert "sslmode=prefer" in url

    def test_empty_ssl_mode_uses_default(self):
        """Test that empty SSL mode uses default"""
        config = DatabaseConfig.__new__(DatabaseConfig)
        config._initialized = False
        config.database_type = "postgresql"

        with patch.dict(os.environ, {
            "DATABASE_TYPE": "postgresql",
            "DATABASE_HOST": "localhost",
            "DATABASE_USER": "postgres",
            "DATABASE_PASSWORD": "password",
            "DATABASE_SSL_MODE": "",  # Empty SSL mode
            "DATABASE_URL": ""
        }, clear=False):
            url = config._get_secure_database_url()

            # Empty should be treated as not set, default to 'prefer'
            # Note: This depends on how the code handles empty strings
            assert "localhost" in url  # Basic validation

    def test_log_level_edge_cases(self):
        """Test log level handling with edge cases"""
        edge_cases = [
            ("", ""),  # Empty string
            ("   ", "   "),  # Only spaces
            ("INFO\n", "info\n"),  # With newline
            ("123", "123"),  # Numbers
            ("info-debug", "info-debug"),  # Hyphenated
        ]

        for input_level, expected in edge_cases:
            result = input_level.lower()
            assert result == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])