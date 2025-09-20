"""Unit tests for IDValidator domain service."""

import pytest
from fastmcp.utilities.id_validator import (
    IDValidator,
    IDType,
    ValidationResult,
    IDValidationError,
    validate_uuid,
    prevent_id_confusion,
    is_mcp_task_id
)


class TestIDValidator:
    """Test suite for IDValidator domain service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = IDValidator(strict_uuid_validation=True)
        self.relaxed_validator = IDValidator(strict_uuid_validation=False)

        # Test UUIDs
        self.valid_uuid_v4 = "550e8400-e29b-41d4-a716-446655440000"
        self.valid_uuid_v1 = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        self.invalid_uuid = "not-a-uuid"
        self.empty_uuid = ""
        self.malformed_uuid = "550e8400-e29b-41d4-a716"

    def test_validate_uuid_format_valid_v4(self):
        """Test validation of valid UUID v4 format."""
        result = self.validator.validate_uuid_format(self.valid_uuid_v4)

        assert result.is_valid is True
        assert result.id_type == IDType.UUID
        assert result.original_value == self.valid_uuid_v4
        assert result.normalized_value == self.valid_uuid_v4.lower()
        assert result.error_message is None
        assert result.metadata["uuid_version"] == "v4"

    def test_validate_uuid_format_valid_v1_strict_mode(self):
        """Test that UUID v1 fails in strict mode."""
        result = self.validator.validate_uuid_format(self.valid_uuid_v1)

        assert result.is_valid is False
        assert result.id_type == IDType.UNKNOWN
        assert "Invalid UUID format" in result.error_message

    def test_validate_uuid_format_valid_v1_relaxed_mode(self):
        """Test that UUID v1 passes in relaxed mode."""
        result = self.relaxed_validator.validate_uuid_format(self.valid_uuid_v1)

        assert result.is_valid is True
        assert result.id_type == IDType.UUID
        assert result.metadata["uuid_version"] == "any"

    def test_validate_uuid_format_invalid(self):
        """Test validation of invalid UUID format."""
        result = self.validator.validate_uuid_format(self.invalid_uuid)

        assert result.is_valid is False
        assert result.id_type == IDType.UNKNOWN
        assert result.original_value == self.invalid_uuid
        assert "Invalid UUID format" in result.error_message

    def test_validate_uuid_format_empty(self):
        """Test validation of empty UUID."""
        result = self.validator.validate_uuid_format(self.empty_uuid)

        assert result.is_valid is False
        assert result.id_type == IDType.UNKNOWN
        assert "cannot be empty" in result.error_message

    def test_validate_uuid_format_none(self):
        """Test validation of None UUID."""
        result = self.validator.validate_uuid_format(None)

        assert result.is_valid is False
        assert result.id_type == IDType.UNKNOWN
        assert "cannot be empty" in result.error_message

    def test_detect_id_type_no_context(self):
        """Test ID type detection without context hints."""
        result = self.validator.detect_id_type(self.valid_uuid_v4)

        assert result.is_valid is True
        assert result.id_type == IDType.UUID
        assert result.warnings is None

    def test_detect_id_type_task_context(self):
        """Test ID type detection with task context."""
        result = self.validator.detect_id_type(self.valid_uuid_v4, "task_id")

        assert result.is_valid is True
        assert result.id_type == IDType.APPLICATION_TASK_ID
        assert result.metadata["context_hint"] == "task_id"

    def test_detect_id_type_mcp_task_context(self):
        """Test ID type detection with MCP task context."""
        result = self.validator.detect_id_type(self.valid_uuid_v4, "mcp_task_id")

        assert result.is_valid is True
        assert result.id_type == IDType.MCP_TASK_ID
        assert result.warnings is not None
        assert any("MCP task ID detected" in warning for warning in result.warnings)

    def test_detect_id_type_git_branch_context(self):
        """Test ID type detection with git branch context."""
        result = self.validator.detect_id_type(self.valid_uuid_v4, "git_branch_id")

        assert result.is_valid is True
        assert result.id_type == IDType.GIT_BRANCH_ID

    def test_detect_id_type_project_context(self):
        """Test ID type detection with project context."""
        result = self.validator.detect_id_type(self.valid_uuid_v4, "project_id")

        assert result.is_valid is True
        assert result.id_type == IDType.PROJECT_ID

    def test_detect_id_type_user_context(self):
        """Test ID type detection with user context."""
        result = self.validator.detect_id_type(self.valid_uuid_v4, "user_id")

        assert result.is_valid is True
        assert result.id_type == IDType.USER_ID

    def test_validate_parameter_mapping_valid_single(self):
        """Test parameter mapping validation with single valid parameter."""
        result = self.validator.validate_parameter_mapping(task_id=self.valid_uuid_v4)

        assert result.is_valid is True
        assert result.error_message is None
        assert result.metadata["parameter_count"] == 1

    def test_validate_parameter_mapping_valid_multiple(self):
        """Test parameter mapping validation with multiple valid parameters."""
        task_id = "550e8400-e29b-41d4-a716-446655440001"
        git_branch_id = "550e8400-e29b-41d4-a716-446655440002"

        result = self.validator.validate_parameter_mapping(
            task_id=task_id,
            git_branch_id=git_branch_id
        )

        assert result.is_valid is True
        assert result.error_message is None
        assert result.metadata["parameter_count"] == 2

    def test_validate_parameter_mapping_no_parameters(self):
        """Test parameter mapping validation with no parameters."""
        result = self.validator.validate_parameter_mapping()

        assert result.is_valid is False
        assert "At least one parameter must be provided" in result.error_message

    def test_validate_parameter_mapping_invalid_uuid(self):
        """Test parameter mapping validation with invalid UUID."""
        result = self.validator.validate_parameter_mapping(task_id="invalid-uuid")

        assert result.is_valid is False
        assert "Invalid UUID format" in result.error_message

    def test_validate_parameter_mapping_critical_confusion(self):
        """Test detection of critical MCP ID confusion."""
        # Simulate the critical bug: MCP task ID passed as git_branch_id
        mcp_task_id = self.valid_uuid_v4

        # Mock the scenario where detect_id_type would return MCP_TASK_ID
        # for git_branch_id parameter (this would happen in real scenario)
        class MockValidator(IDValidator):
            def detect_id_type(self, value, context_hint=None):
                result = super().detect_id_type(value, context_hint)
                if context_hint == "git_branch_id" and value == mcp_task_id:
                    result.id_type = IDType.MCP_TASK_ID
                return result

        mock_validator = MockValidator()
        result = mock_validator.validate_parameter_mapping(git_branch_id=mcp_task_id)

        assert result.is_valid is False
        assert "CRITICAL" in result.error_message
        assert "MCP task ID" in result.error_message
        assert "data integrity issues" in result.error_message

    def test_validate_parameter_mapping_duplicate_ids(self):
        """Test detection of duplicate IDs across parameters."""
        same_id = self.valid_uuid_v4

        result = self.validator.validate_parameter_mapping(
            task_id=same_id,
            git_branch_id=same_id
        )

        # Should be valid but with warnings
        assert result.is_valid is True
        assert result.warnings is not None
        assert any("Same ID value used for multiple parameters" in warning
                  for warning in result.warnings)

    def test_validate_task_context_valid(self):
        """Test task context validation with valid IDs."""
        task_id = "550e8400-e29b-41d4-a716-446655440001"
        git_branch_id = "550e8400-e29b-41d4-a716-446655440002"

        result = self.validator.validate_task_context(
            task_id=task_id,
            expected_git_branch_id=git_branch_id
        )

        assert result.is_valid is True
        assert result.metadata["validation_type"] == "task_context"
        assert result.metadata["git_branch_id_validated"] is True

    def test_validate_task_context_invalid_task_id(self):
        """Test task context validation with invalid task ID."""
        result = self.validator.validate_task_context(task_id="invalid-task-id")

        assert result.is_valid is False
        assert "Invalid UUID format" in result.error_message

    def test_validate_task_context_invalid_git_branch_id(self):
        """Test task context validation with invalid git branch ID."""
        result = self.validator.validate_task_context(
            task_id=self.valid_uuid_v4,
            expected_git_branch_id="invalid-branch-id"
        )

        assert result.is_valid is False
        assert "Invalid git_branch_id" in result.error_message

    def test_validate_task_context_critical_same_ids(self):
        """Test detection of critical error when task_id equals git_branch_id."""
        same_id = self.valid_uuid_v4

        result = self.validator.validate_task_context(
            task_id=same_id,
            expected_git_branch_id=same_id
        )

        assert result.is_valid is False
        assert "CRITICAL" in result.error_message
        assert "task_id and git_branch_id are identical" in result.error_message
        assert "parameter confusion" in result.error_message

    def test_validate_task_context_mcp_warning(self):
        """Test warning when task ID appears to be MCP task ID."""
        # Mock scenario where task_id is detected as MCP_TASK_ID
        class MockValidator(IDValidator):
            def detect_id_type(self, value, context_hint=None):
                result = super().detect_id_type(value, context_hint)
                if context_hint == "task_id":
                    result.id_type = IDType.MCP_TASK_ID
                return result

        mock_validator = MockValidator()
        result = mock_validator.validate_task_context(task_id=self.valid_uuid_v4)

        assert result.is_valid is True
        assert result.warnings is not None
        assert any("MCP task ID" in warning for warning in result.warnings)

    def test_suggest_fix_for_confusion(self):
        """Test fix suggestions for ID confusion."""
        suggestions = self.validator.suggest_fix_for_confusion(
            confused_task_id=self.valid_uuid_v4,
            context="subtask_controller"
        )

        assert "issue" in suggestions
        assert "confused_id" in suggestions
        assert "root_cause" in suggestions
        assert "immediate_fix" in suggestions
        assert "code_example" in suggestions
        assert "prevention" in suggestions

        assert suggestions["confused_id"] == self.valid_uuid_v4
        assert "subtask_controller" in suggestions["issue"]
        assert "WRONG" in suggestions["code_example"]
        assert "CORRECT" in suggestions["code_example"]


class TestConvenienceFunctions:
    """Test suite for convenience functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
        self.invalid_uuid = "not-a-uuid"

    def test_validate_uuid_strict_true(self):
        """Test validate_uuid convenience function with strict mode."""
        assert validate_uuid(self.valid_uuid, strict=True) is True
        assert validate_uuid(self.invalid_uuid, strict=True) is False

    def test_validate_uuid_strict_false(self):
        """Test validate_uuid convenience function with relaxed mode."""
        uuid_v1 = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        assert validate_uuid(uuid_v1, strict=False) is True
        assert validate_uuid(self.invalid_uuid, strict=False) is False

    def test_prevent_id_confusion_valid(self):
        """Test prevent_id_confusion with valid parameters."""
        task_id = "550e8400-e29b-41d4-a716-446655440001"
        git_branch_id = "550e8400-e29b-41d4-a716-446655440002"

        # Should not raise exception
        prevent_id_confusion(task_id=task_id, git_branch_id=git_branch_id)

    def test_prevent_id_confusion_invalid(self):
        """Test prevent_id_confusion with invalid parameters."""
        with pytest.raises(IDValidationError) as exc_info:
            prevent_id_confusion(task_id="invalid-uuid")

        assert "Invalid UUID format" in str(exc_info.value)
        assert exc_info.value.id_value == "{'task_id': 'invalid-uuid'}"

    def test_prevent_id_confusion_no_parameters(self):
        """Test prevent_id_confusion with no parameters."""
        with pytest.raises(IDValidationError) as exc_info:
            prevent_id_confusion()

        assert "At least one parameter must be provided" in str(exc_info.value)

    def test_is_mcp_task_id_valid_uuid(self):
        """Test is_mcp_task_id returns True for valid UUIDs."""
        # Since we can't distinguish MCP vs application task IDs by format alone,
        # the function validates UUID format only
        assert is_mcp_task_id(self.valid_uuid) is True

    def test_is_mcp_task_id_invalid_uuid(self):
        """Test is_mcp_task_id returns False for invalid UUIDs."""
        assert is_mcp_task_id(self.invalid_uuid) is False


class TestValidationResult:
    """Test suite for ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test ValidationResult creation with all fields."""
        result = ValidationResult(
            is_valid=True,
            id_type=IDType.UUID,
            original_value="test-value",
            normalized_value="normalized-value",
            error_message=None,
            warnings=["warning1", "warning2"],
            metadata={"key": "value"}
        )

        assert result.is_valid is True
        assert result.id_type == IDType.UUID
        assert result.original_value == "test-value"
        assert result.normalized_value == "normalized-value"
        assert result.error_message is None
        assert result.warnings == ["warning1", "warning2"]
        assert result.metadata == {"key": "value"}

    def test_validation_result_minimal(self):
        """Test ValidationResult creation with minimal fields."""
        result = ValidationResult(
            is_valid=False,
            id_type=IDType.UNKNOWN,
            original_value="test-value"
        )

        assert result.is_valid is False
        assert result.id_type == IDType.UNKNOWN
        assert result.original_value == "test-value"
        assert result.normalized_value is None
        assert result.error_message is None
        assert result.warnings is None
        assert result.metadata is None


class TestIDValidationError:
    """Test suite for IDValidationError exception."""

    def test_id_validation_error_creation(self):
        """Test IDValidationError creation."""
        error = IDValidationError(
            message="Test error",
            id_value="test-id",
            expected_type=IDType.UUID
        )

        assert str(error) == "Test error"
        assert error.id_value == "test-id"
        assert error.expected_type == IDType.UUID

    def test_id_validation_error_minimal(self):
        """Test IDValidationError creation with minimal parameters."""
        error = IDValidationError(
            message="Test error",
            id_value="test-id"
        )

        assert str(error) == "Test error"
        assert error.id_value == "test-id"
        assert error.expected_type is None


class TestIDType:
    """Test suite for IDType enum."""

    def test_id_type_values(self):
        """Test IDType enum values."""
        assert IDType.UUID.value == "uuid"
        assert IDType.MCP_TASK_ID.value == "mcp_task_id"
        assert IDType.APPLICATION_TASK_ID.value == "application_task_id"
        assert IDType.GIT_BRANCH_ID.value == "git_branch_id"
        assert IDType.PROJECT_ID.value == "project_id"
        assert IDType.USER_ID.value == "user_id"
        assert IDType.CONTEXT_ID.value == "context_id"
        assert IDType.UNKNOWN.value == "unknown"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])