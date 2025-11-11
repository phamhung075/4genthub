"""Unit tests for LabelValidator.

This module tests all validation rules for label creation and updates,
ensuring that business rules are properly enforced at the domain layer.
"""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from fastmcp.task_management.domain.validators.label_validator import (
    LabelValidationError,
    LabelValidator,
)


class TestTimestampValidation:
    """Test cases for timestamp validation."""

    def test_validate_timestamp_utc_aware_success(self):
        """Test that UTC-aware timestamps pass validation."""
        validator = LabelValidator()
        utc_time = datetime.now(UTC)

        # Should not raise any exception
        validator.validate_timestamp(utc_time, "created_at")

    def test_validate_timestamp_none_fails(self):
        """Test that None timestamp fails validation."""
        validator = LabelValidator()

        with pytest.raises(LabelValidationError) as exc_info:
            validator.validate_timestamp(None, "created_at")

        assert "cannot be None" in str(exc_info.value)
        assert exc_info.value.field == "created_at"

    def test_validate_timestamp_naive_fails(self):
        """Test that timezone-naive timestamps fail validation."""
        validator = LabelValidator()
        naive_time = datetime.now()  # No timezone

        with pytest.raises(LabelValidationError) as exc_info:
            validator.validate_timestamp(naive_time, "created_at")

        assert "timezone-aware" in str(exc_info.value)
        assert "datetime.now(UTC)" in str(exc_info.value)

    def test_validate_timestamp_non_utc_fails(self):
        """Test that non-UTC timezones fail validation."""
        validator = LabelValidator()
        # Create a timezone-aware datetime with non-UTC timezone
        from datetime import timedelta

        # Create a timezone offset (e.g., UTC+5)
        eastern = timezone(timedelta(hours=-5))
        non_utc_time = datetime.now(eastern)

        with pytest.raises(LabelValidationError) as exc_info:
            validator.validate_timestamp(non_utc_time, "created_at")

        assert "UTC timezone" in str(exc_info.value)

    def test_validate_timestamps_consistency_success(self):
        """Test that consistent timestamps pass validation."""
        validator = LabelValidator()
        created = datetime.now(UTC)
        updated = created + timedelta(seconds=1)

        # Should not raise any exception
        validator.validate_timestamps_consistency(created, updated)

    def test_validate_timestamps_consistency_same_time(self):
        """Test that equal created_at and updated_at pass validation."""
        validator = LabelValidator()
        timestamp = datetime.now(UTC)

        # Should not raise - updated_at can equal created_at
        validator.validate_timestamps_consistency(timestamp, timestamp)

    def test_validate_timestamps_consistency_fails(self):
        """Test that updated_at earlier than created_at fails."""
        validator = LabelValidator()
        created = datetime.now(UTC)
        updated = created - timedelta(seconds=1)

        with pytest.raises(LabelValidationError) as exc_info:
            validator.validate_timestamps_consistency(created, updated)

        assert "earlier than created_at" in str(exc_info.value)


class TestNameValidation:
    """Test cases for label name validation."""

    def test_validate_name_valid_alphanumeric(self):
        """Test that alphanumeric names pass validation."""
        validator = LabelValidator()

        valid_names = ["backend", "frontend", "api", "Backend123", "test_123"]

        for name in valid_names:
            validator.validate_name(name)  # Should not raise

    def test_validate_name_valid_with_hyphens(self):
        """Test that names with hyphens pass validation."""
        validator = LabelValidator()

        valid_names = [
            "api-integration",
            "frontend-ui",
            "db-optimization",
            "multi-word-label",
        ]

        for name in valid_names:
            validator.validate_name(name)  # Should not raise

    def test_validate_name_valid_with_underscores(self):
        """Test that names with underscores pass validation."""
        validator = LabelValidator()

        valid_names = [
            "api_integration",
            "frontend_ui",
            "db_optimization",
            "multi_word_label",
        ]

        for name in valid_names:
            validator.validate_name(name)  # Should not raise

    def test_validate_name_valid_with_spaces(self):
        """Test that names with spaces pass validation."""
        validator = LabelValidator()

        valid_names = ["API Integration", "Frontend UI", "Database Optimization"]

        for name in valid_names:
            validator.validate_name(name)  # Should not raise

    def test_validate_name_empty_fails(self):
        """Test that empty names fail validation."""
        validator = LabelValidator()

        with pytest.raises(LabelValidationError) as exc_info:
            validator.validate_name("")

        assert "cannot be empty" in str(exc_info.value)
        assert exc_info.value.field == "name"

    def test_validate_name_whitespace_only_fails(self):
        """Test that whitespace-only names fail validation."""
        validator = LabelValidator()

        with pytest.raises(LabelValidationError) as exc_info:
            validator.validate_name("   ")

        assert "cannot be empty" in str(exc_info.value)

    def test_validate_name_too_long_fails(self):
        """Test that names exceeding max length fail validation."""
        validator = LabelValidator()
        long_name = "x" * (LabelValidator.MAX_NAME_LENGTH + 1)

        with pytest.raises(LabelValidationError) as exc_info:
            validator.validate_name(long_name)

        assert "cannot exceed" in str(exc_info.value)
        assert str(LabelValidator.MAX_NAME_LENGTH) in str(exc_info.value)

    def test_validate_name_invalid_characters_fails(self):
        """Test that names with invalid characters fail validation."""
        validator = LabelValidator()

        invalid_names = [
            "label@tag",
            "label#tag",
            "label$tag",
            "label%tag",
            "label!tag",
        ]

        for name in invalid_names:
            with pytest.raises(LabelValidationError) as exc_info:
                validator.validate_name(name)

            assert "invalid characters" in str(exc_info.value)


class TestColorValidation:
    """Test cases for color format validation."""

    def test_validate_color_valid_six_digit(self):
        """Test that 6-digit hex colors pass validation."""
        validator = LabelValidator()

        valid_colors = [
            "#ff0000",
            "#00ff00",
            "#0000ff",
            "#ffffff",
            "#000000",
            "#abc123",
        ]

        for color in valid_colors:
            validator.validate_color(color)  # Should not raise

    def test_validate_color_valid_three_digit(self):
        """Test that 3-digit hex colors pass validation."""
        validator = LabelValidator()

        valid_colors = ["#f00", "#0f0", "#00f", "#fff", "#000", "#abc"]

        for color in valid_colors:
            validator.validate_color(color)  # Should not raise

    def test_validate_color_none_allowed(self):
        """Test that None color is allowed (optional field)."""
        validator = LabelValidator()

        validator.validate_color(None)  # Should not raise

    def test_validate_color_missing_hash_fails(self):
        """Test that colors without # prefix fail validation."""
        validator = LabelValidator()

        with pytest.raises(LabelValidationError) as exc_info:
            validator.validate_color("ff0000")

        assert "must start with '#'" in str(exc_info.value)
        assert "#ff0000" in str(exc_info.value)  # Hint suggests correction

    def test_validate_color_invalid_format_fails(self):
        """Test that invalid hex formats fail validation."""
        validator = LabelValidator()

        invalid_colors = [
            "#ff",  # Too short
            "#ffff",  # Invalid length
            "#fffff",  # Invalid length
            "#fffffff",  # Too long
            "#gggggg",  # Invalid hex characters
            "#zzzzzz",  # Invalid hex characters
        ]

        for color in invalid_colors:
            with pytest.raises(LabelValidationError) as exc_info:
                validator.validate_color(color)

            assert "Invalid hex color format" in str(exc_info.value)

    def test_validate_color_not_string_fails(self):
        """Test that non-string colors fail validation."""
        validator = LabelValidator()

        with pytest.raises(LabelValidationError) as exc_info:
            validator.validate_color(123456)

        assert "must be a string" in str(exc_info.value)


class TestDescriptionValidation:
    """Test cases for description validation."""

    def test_validate_description_valid(self):
        """Test that valid descriptions pass validation."""
        validator = LabelValidator()

        valid_descriptions = [
            "Backend API tasks",
            "Frontend UI components",
            "x" * 100,  # Long but valid
            "Description with special chars: @#$%^&*()",
        ]

        for desc in valid_descriptions:
            validator.validate_description(desc)  # Should not raise

    def test_validate_description_none_allowed(self):
        """Test that None description is allowed (optional field)."""
        validator = LabelValidator()

        validator.validate_description(None)  # Should not raise

    def test_validate_description_empty_allowed(self):
        """Test that empty description is allowed (optional field)."""
        validator = LabelValidator()

        validator.validate_description("")  # Should not raise

    def test_validate_description_too_long_fails(self):
        """Test that descriptions exceeding max length fail validation."""
        validator = LabelValidator()
        long_desc = "x" * (LabelValidator.MAX_DESCRIPTION_LENGTH + 1)

        with pytest.raises(LabelValidationError) as exc_info:
            validator.validate_description(long_desc)

        assert "cannot exceed" in str(exc_info.value)
        assert str(LabelValidator.MAX_DESCRIPTION_LENGTH) in str(exc_info.value)

    def test_validate_description_not_string_fails(self):
        """Test that non-string descriptions fail validation."""
        validator = LabelValidator()

        with pytest.raises(LabelValidationError) as exc_info:
            validator.validate_description(12345)

        assert "must be a string" in str(exc_info.value)


class TestLabelCreationValidation:
    """Test cases for complete label creation validation."""

    def test_validate_label_creation_all_valid(self):
        """Test that valid label data passes creation validation."""
        validator = LabelValidator()

        success, error = validator.validate_label_creation(
            name="backend",
            color="#ff0000",
            description="Backend API tasks",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        assert success is True
        assert error is None

    def test_validate_label_creation_minimal_valid(self):
        """Test that minimal valid label (only name) passes validation."""
        validator = LabelValidator()

        success, error = validator.validate_label_creation(name="backend")

        assert success is True
        assert error is None

    def test_validate_label_creation_invalid_name_fails(self):
        """Test that invalid name fails creation validation."""
        validator = LabelValidator()

        success, error = validator.validate_label_creation(
            name="",  # Empty name
            color="#ff0000",
        )

        assert success is False
        assert error is not None
        assert "cannot be empty" in error

    def test_validate_label_creation_invalid_color_fails(self):
        """Test that invalid color fails creation validation."""
        validator = LabelValidator()

        success, error = validator.validate_label_creation(
            name="backend",
            color="#zzz",  # Invalid hex characters
        )

        assert success is False
        assert error is not None
        assert "Invalid hex color format" in error

    def test_validate_label_creation_inconsistent_timestamps_fails(self):
        """Test that inconsistent timestamps fail creation validation."""
        validator = LabelValidator()

        created = datetime.now(UTC)
        updated = created - timedelta(seconds=1)  # Earlier than created

        success, error = validator.validate_label_creation(
            name="backend", created_at=created, updated_at=updated
        )

        assert success is False
        assert error is not None
        assert "earlier than created_at" in error


class TestLabelUpdateValidation:
    """Test cases for label update validation."""

    def test_validate_label_update_name_only(self):
        """Test that updating only name passes validation."""
        validator = LabelValidator()

        success, error = validator.validate_label_update(name="new-name")

        assert success is True
        assert error is None

    def test_validate_label_update_color_only(self):
        """Test that updating only color passes validation."""
        validator = LabelValidator()

        success, error = validator.validate_label_update(color="#00ff00")

        assert success is True
        assert error is None

    def test_validate_label_update_description_only(self):
        """Test that updating only description passes validation."""
        validator = LabelValidator()

        success, error = validator.validate_label_update(
            description="Updated description"
        )

        assert success is True
        assert error is None

    def test_validate_label_update_all_fields(self):
        """Test that updating all fields passes validation."""
        validator = LabelValidator()

        success, error = validator.validate_label_update(
            name="updated-name", color="#0000ff", description="Updated description"
        )

        assert success is True
        assert error is None

    def test_validate_label_update_invalid_name_fails(self):
        """Test that invalid name fails update validation."""
        validator = LabelValidator()

        success, error = validator.validate_label_update(name="")

        assert success is False
        assert error is not None
        assert "cannot be empty" in error

    def test_validate_label_update_invalid_color_fails(self):
        """Test that invalid color fails update validation."""
        validator = LabelValidator()

        success, error = validator.validate_label_update(color="not-a-color")

        assert success is False
        assert error is not None


class TestLabelValidationError:
    """Test cases for LabelValidationError exception."""

    def test_validation_error_with_field_and_message(self):
        """Test that validation error stores field and message."""
        error = LabelValidationError(field="name", message="Name is invalid")

        assert error.field == "name"
        assert error.message == "Name is invalid"
        assert "name" in str(error)
        assert "Name is invalid" in str(error)

    def test_validation_error_with_hint(self):
        """Test that validation error includes hint when provided."""
        error = LabelValidationError(
            field="color", message="Invalid color", hint="Use hex format like #ff0000"
        )

        assert error.hint == "Use hex format like #ff0000"
        assert "Hint:" in str(error)
        assert "#ff0000" in str(error)
