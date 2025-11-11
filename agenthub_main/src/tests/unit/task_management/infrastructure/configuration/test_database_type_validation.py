"""
Phase 6: DATABASE_TYPE Validation Tests

Tests for DATABASE_TYPE enum validation and environment configuration changes.
These tests verify that the tightened DATABASE_TYPE validation correctly:
- Accepts only 'postgresql' and 'supabase' (case-insensitive)
- Rejects 'sqlite', 'mysql', and other invalid values
- Raises clear ValueError messages for invalid types
- Handles missing DATABASE_TYPE configuration
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from fastmcp.task_management.infrastructure.database.database_config import (
    DatabaseConfig,
)


@pytest.fixture(autouse=True)
def mock_db_connection():
    """Mock database connection to prevent actual database authentication."""
    with patch(
        "fastmcp.task_management.infrastructure.database.database_config.create_engine"
    ) as mock_engine:
        # Create a mock engine that behaves like a real one
        mock_engine_instance = MagicMock()
        mock_connection = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = "PostgreSQL 14.0"

        # Setup connection behavior
        mock_connection.execute.return_value = mock_result
        mock_connection.__enter__ = MagicMock(return_value=mock_connection)
        mock_connection.__exit__ = MagicMock(return_value=False)
        mock_engine_instance.connect.return_value = mock_connection

        # Setup pool info (for get_database_info)
        mock_pool = MagicMock()
        mock_pool.size.return_value = 5
        mock_pool.checkedin.return_value = 5
        mock_pool.checkedout.return_value = 0
        mock_pool.overflow.return_value = 0
        mock_engine_instance.pool = mock_pool

        mock_engine.return_value = mock_engine_instance

        # Also mock ensure_ai_columns_exist to prevent column checks
        with patch(
            "fastmcp.task_management.infrastructure.database.database_config.ensure_ai_columns_exist"
        ) as mock_ai_columns:
            mock_ai_columns.return_value = True
            yield mock_engine


class TestDatabaseTypeValidation:
    """Test DATABASE_TYPE environment variable validation with tightened rules."""

    def setup_method(self):
        """Reset database config singleton before each test."""
        DatabaseConfig.reset_instance()

    def teardown_method(self):
        """Clean up after each test."""
        DatabaseConfig.reset_instance()

    @pytest.mark.parametrize(
        "valid_type",
        [
            "postgresql",
            "supabase",
            "PostgreSQL",  # Case insensitive
            "SUPABASE",  # Case insensitive
            "PoStGrEsQl",  # Mixed case
        ],
    )
    def test_valid_database_types_accepted(self, valid_type, mock_db_connection):
        """Test that valid DATABASE_TYPE values are accepted (case-insensitive)."""
        with patch.dict(
            os.environ,
            {
                "DATABASE_TYPE": valid_type,
                "DATABASE_HOST": "localhost",
                "DATABASE_USER": "test_user",
                "DATABASE_PASSWORD": "test_pass",
                "DATABASE_NAME": "test_db",
            },
            clear=True,
        ):
            try:
                config = DatabaseConfig()
                # Should not raise - verify type was normalized to lowercase
                assert config.database_type in ["postgresql", "supabase"]
            except ValueError as e:
                pytest.fail(f"Valid DATABASE_TYPE '{valid_type}' was rejected: {e}")

    @pytest.mark.parametrize(
        "invalid_type,error_substring",
        [
            ("sqlite", "Invalid DATABASE_TYPE: sqlite"),
            ("mysql", "Invalid DATABASE_TYPE: mysql"),
            ("oracle", "Invalid DATABASE_TYPE: oracle"),
            ("mongodb", "Invalid DATABASE_TYPE: mongodb"),
            ("mariadb", "Invalid DATABASE_TYPE: mariadb"),
            ("mssql", "Invalid DATABASE_TYPE: mssql"),
            ("cockroachdb", "Invalid DATABASE_TYPE: cockroachdb"),
            ("invalid", "Invalid DATABASE_TYPE: invalid"),
            ("", "DATABASE_TYPE environment variable is NOT configured"),
            ("   ", "Invalid DATABASE_TYPE"),  # Whitespace only
        ],
    )
    def test_invalid_database_types_rejected(self, invalid_type, error_substring):
        """Test that invalid DATABASE_TYPE values are rejected with clear error messages."""
        with patch.dict(os.environ, {"DATABASE_TYPE": invalid_type}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                DatabaseConfig()

            # Verify error message contains expected substring
            assert error_substring in str(exc_info.value), (
                f"Expected error message to contain '{error_substring}', got: {exc_info.value}"
            )

    def test_missing_database_type_raises_error(self):
        """Test that missing DATABASE_TYPE raises clear error message."""
        # Clear DATABASE_TYPE from environment
        with patch.dict(os.environ, {}, clear=True):
            # Make sure DATABASE_TYPE is not set
            if "DATABASE_TYPE" in os.environ:
                del os.environ["DATABASE_TYPE"]

            with pytest.raises(ValueError) as exc_info:
                DatabaseConfig()

            # Verify error message is informative
            error_msg = str(exc_info.value)
            assert "DATABASE_TYPE environment variable is NOT configured" in error_msg
            assert "postgresql" in error_msg  # Should suggest valid options
            assert "supabase" in error_msg

    def test_none_database_type_raises_error(self):
        """Test that None DATABASE_TYPE (unset) raises error."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                DatabaseConfig()

            assert "DATABASE_TYPE environment variable is NOT configured" in str(
                exc_info.value
            )

    def test_postgresql_requires_connection_details(self):
        """Test that postgresql DATABASE_TYPE requires host, user, password."""
        with patch.dict(
            os.environ,
            {
                "DATABASE_TYPE": "postgresql",
                # Missing DATABASE_HOST, DATABASE_USER, DATABASE_PASSWORD
            },
            clear=True,
        ):
            with pytest.raises(ValueError) as exc_info:
                DatabaseConfig()

            error_msg = str(exc_info.value)
            # Should mention missing configuration
            assert (
                "configuration missing" in error_msg.lower()
                or "required" in error_msg.lower()
            )

    def test_supabase_requires_connection_details(self):
        """Test that supabase DATABASE_TYPE requires host and password."""
        with patch.dict(
            os.environ,
            {
                "DATABASE_TYPE": "supabase",
                # Missing SUPABASE_DB_HOST, SUPABASE_DB_PASSWORD
            },
            clear=True,
        ):
            with pytest.raises(ValueError) as exc_info:
                DatabaseConfig()

            error_msg = str(exc_info.value)
            # Should mention Supabase configuration or missing details
            assert (
                "supabase" in error_msg.lower() or "configuration" in error_msg.lower()
            )

    def test_case_insensitive_normalization(self, mock_db_connection):
        """Test that DATABASE_TYPE is normalized to lowercase."""
        test_cases = [
            ("PostgreSQL", "postgresql"),
            ("POSTGRESQL", "postgresql"),
            ("Supabase", "supabase"),
            ("SUPABASE", "supabase"),
        ]

        for input_type, expected_normalized in test_cases:
            DatabaseConfig.reset_instance()

            with patch.dict(
                os.environ,
                {
                    "DATABASE_TYPE": input_type,
                    "DATABASE_HOST": "localhost",
                    "DATABASE_USER": "test_user",
                    "DATABASE_PASSWORD": "test_pass",
                },
                clear=True,
            ):
                config = DatabaseConfig()
                assert config.database_type == expected_normalized, (
                    f"Expected '{input_type}' to be normalized to '{expected_normalized}', "
                    f"got '{config.database_type}'"
                )


class TestDatabaseTypeErrorMessages:
    """Test that error messages for invalid DATABASE_TYPE are clear and actionable."""

    def setup_method(self):
        """Reset database config singleton before each test."""
        DatabaseConfig.reset_instance()

    def teardown_method(self):
        """Clean up after each test."""
        DatabaseConfig.reset_instance()

    def test_sqlite_rejection_message(self):
        """Test that sqlite rejection provides clear migration guidance."""
        with patch.dict(os.environ, {"DATABASE_TYPE": "sqlite"}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                DatabaseConfig()

            error_msg = str(exc_info.value)
            # Should clearly state sqlite is not supported
            assert "sqlite" in error_msg.lower()
            # Should mention supported types
            assert "postgresql" in error_msg or "supabase" in error_msg

    def test_missing_type_provides_examples(self):
        """Test that missing DATABASE_TYPE error provides configuration examples."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                DatabaseConfig()

            error_msg = str(exc_info.value)
            # Should provide examples of how to configure
            assert (
                "DATABASE_TYPE=postgresql" in error_msg
                or "DATABASE_TYPE=supabase" in error_msg
            )

    def test_error_prevents_fallback(self):
        """Test that invalid DATABASE_TYPE prevents fallback behavior."""
        with patch.dict(os.environ, {"DATABASE_TYPE": "sqlite"}, clear=True):
            with pytest.raises(ValueError):
                DatabaseConfig()

            # Verify no instance was created (no fallback)
            assert DatabaseConfig._instance is None or not DatabaseConfig._initialized


class TestDatabaseConfigurationConstructor:
    """Test DatabaseConfig constructor updates and validation."""

    def setup_method(self):
        """Reset database config singleton before each test."""
        DatabaseConfig.reset_instance()

    def teardown_method(self):
        """Clean up after each test."""
        DatabaseConfig.reset_instance()

    def test_constructor_validates_type_before_connection(self):
        """Test that DATABASE_TYPE is validated before attempting connection."""
        with patch.dict(os.environ, {"DATABASE_TYPE": "invalid_type"}, clear=True):
            # Should fail during type validation, not during connection
            with pytest.raises(ValueError) as exc_info:
                DatabaseConfig()

            # Error should be about invalid type, not connection failure
            error_msg = str(exc_info.value)
            assert "Invalid DATABASE_TYPE" in error_msg

    def test_singleton_pattern_preserved(self, mock_db_connection):
        """Test that singleton pattern still works after validation changes."""
        with patch.dict(
            os.environ,
            {
                "DATABASE_TYPE": "postgresql",
                "DATABASE_HOST": "localhost",
                "DATABASE_USER": "test_user",
                "DATABASE_PASSWORD": "test_pass",
            },
            clear=True,
        ):
            config1 = DatabaseConfig()
            config2 = DatabaseConfig()

            # Should be same instance
            assert config1 is config2

    def test_reset_instance_clears_validation_state(self, mock_db_connection):
        """Test that reset_instance properly clears validation state."""
        # First create with valid config
        with patch.dict(
            os.environ,
            {
                "DATABASE_TYPE": "postgresql",
                "DATABASE_HOST": "localhost",
                "DATABASE_USER": "test_user",
                "DATABASE_PASSWORD": "test_pass",
            },
            clear=True,
        ):
            config1 = DatabaseConfig()
            assert config1 is not None

        # Reset
        DatabaseConfig.reset_instance()

        # Try to create with invalid config - should fail validation
        with patch.dict(os.environ, {"DATABASE_TYPE": "sqlite"}, clear=True):
            with pytest.raises(ValueError):
                DatabaseConfig()


class TestEnvironmentVariableValidation:
    """Test environment variable validation changes for Phase 6."""

    def setup_method(self):
        """Reset database config singleton before each test."""
        DatabaseConfig.reset_instance()

    def teardown_method(self):
        """Clean up after each test."""
        DatabaseConfig.reset_instance()

    def test_explicit_configuration_required(self):
        """Test that explicit DATABASE_TYPE configuration is required (no defaults)."""
        with patch.dict(os.environ, {}, clear=True):
            # Should not fall back to any default type
            with pytest.raises(ValueError) as exc_info:
                DatabaseConfig()

            assert "NOT configured" in str(exc_info.value)

    def test_empty_string_treated_as_missing(self):
        """Test that empty string DATABASE_TYPE is treated as missing."""
        with patch.dict(os.environ, {"DATABASE_TYPE": ""}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                DatabaseConfig()

            # Should indicate DATABASE_TYPE is not configured
            error_msg = str(exc_info.value)
            assert "NOT configured" in error_msg

    def test_whitespace_only_rejected(self):
        """Test that whitespace-only DATABASE_TYPE is rejected."""
        with patch.dict(os.environ, {"DATABASE_TYPE": "   "}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                DatabaseConfig()

            # Should be rejected as invalid type after strip/lower
            error_msg = str(exc_info.value)
            assert "Invalid DATABASE_TYPE" in error_msg or "NOT configured" in error_msg


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
