"""
Advanced edge case tests for IDValidator domain service.
Tests complex scenarios and edge cases to ensure robust ID validation
that prevents MCP ID vs Application ID confusion.
"""

import pytest
from unittest.mock import patch
from uuid import uuid4, UUID
from fastmcp.utilities.id_validator import (
    IDValidator,
    IDType,
    ValidationResult,
    IDValidationError,
    validate_uuid,
    prevent_id_confusion,
    is_mcp_task_id
)


class TestIDValidatorEdgeCases:
    """Advanced edge case tests for IDValidator domain service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = IDValidator(strict_uuid_validation=True)
        self.relaxed_validator = IDValidator(strict_uuid_validation=False)

    def test_uuid_case_sensitivity_handling(self):
        """Test that UUID validation handles case sensitivity correctly."""
        # Mixed case UUID
        mixed_case_uuid = "550E8400-E29B-41D4-A716-446655440000"
        result = self.validator.validate_uuid_format(mixed_case_uuid)

        assert result.is_valid is True
        assert result.normalized_value == mixed_case_uuid.lower()

        # All uppercase
        upper_uuid = "550E8400-E29B-41D4-A716-446655440000"
        result = self.validator.validate_uuid_format(upper_uuid)
        assert result.is_valid is True
        assert result.normalized_value == upper_uuid.lower()

    def test_uuid_with_whitespace_handling(self):
        """Test UUID validation with leading/trailing whitespace."""
        uuid_with_spaces = "  550e8400-e29b-41d4-a716-446655440000  "
        result = self.validator.validate_uuid_format(uuid_with_spaces)

        assert result.is_valid is True
        assert result.normalized_value == "550e8400-e29b-41d4-a716-446655440000"
        assert result.original_value == uuid_with_spaces

    def test_malformed_uuid_patterns(self):
        """Test various malformed UUID patterns."""
        malformed_uuids = [
            "550e8400-e29b-41d4-a716",  # Too short
            "550e8400-e29b-41d4-a716-446655440000-extra",  # Too long
            "550e8400e29b41d4a716446655440000",  # No hyphens
            "550e8400-e29b-41d4-a716-44665544000g",  # Invalid character
            "550e8400-e29b-31d4-a716-446655440000",  # Wrong version (3 instead of 4)
            "550e8400-e29b-41d4-c716-446655440000",  # Wrong variant (c instead of 8/9/a/b)
        ]

        for malformed_uuid in malformed_uuids:
            result = self.validator.validate_uuid_format(malformed_uuid)
            assert result.is_valid is False, f"Should reject malformed UUID: {malformed_uuid}"
            assert "Invalid UUID format" in result.error_message

    def test_uuid_version_validation_strict_mode(self):
        """Test UUID version validation in strict mode."""
        # UUID v1 (should fail in strict mode)
        uuid_v1 = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        result = self.validator.validate_uuid_format(uuid_v1)
        assert result.is_valid is False

        # UUID v3 (should fail in strict mode)
        uuid_v3 = "6fa459ea-ee8a-3ca4-894e-db77e160355e"
        result = self.validator.validate_uuid_format(uuid_v3)
        assert result.is_valid is False

        # UUID v5 (should fail in strict mode)
        uuid_v5 = "886313e1-3b8a-5372-9b90-0c9aee199e5d"
        result = self.validator.validate_uuid_format(uuid_v5)
        assert result.is_valid is False

    def test_uuid_version_validation_relaxed_mode(self):
        """Test UUID version validation in relaxed mode."""
        # All valid UUID versions should pass in relaxed mode
        valid_uuids = [
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8",  # v1
            "550e8400-e29b-41d4-a716-446655440000",  # v4
            "6fa459ea-ee8a-3ca4-894e-db77e160355e",  # v3
            "886313e1-3b8a-5372-9b90-0c9aee199e5d",  # v5
        ]

        for uuid_str in valid_uuids:
            result = self.relaxed_validator.validate_uuid_format(uuid_str)
            assert result.is_valid is True, f"Should accept UUID in relaxed mode: {uuid_str}"

    def test_context_hint_edge_cases(self):
        """Test context hint detection with edge cases."""
        valid_uuid = "550e8400-e29b-41d4-a716-446655440000"

        # Case variations
        context_hints = [
            "TASK_ID",  # Uppercase
            "Task_Id",  # Mixed case
            "task_id_extra_suffix",  # With suffix
            "prefix_task_id",  # With prefix
            "mcp_task_id_v2",  # MCP with version
            "git_branch_id_main",  # Git branch with name
        ]

        for hint in context_hints:
            result = self.validator.detect_id_type(valid_uuid, hint)
            assert result.is_valid is True
            assert result.id_type != IDType.UNKNOWN, f"Should detect type for hint: {hint}"

    def test_parameter_mapping_complex_scenarios(self):
        """Test parameter mapping with complex real-world scenarios."""
        task_id = str(uuid4())
        git_branch_id = str(uuid4())
        project_id = str(uuid4())
        user_id = str(uuid4())

        # Test all parameters provided
        result = self.validator.validate_parameter_mapping(
            task_id=task_id,
            git_branch_id=git_branch_id,
            project_id=project_id,
            user_id=user_id
        )
        assert result.is_valid is True
        assert result.metadata["parameter_count"] == 4

    def test_parameter_mapping_duplicate_detection(self):
        """Test detection of duplicate IDs across parameters."""
        same_id = str(uuid4())

        # Use same ID for multiple parameters
        result = self.validator.validate_parameter_mapping(
            task_id=same_id,
            git_branch_id=same_id,
            project_id=same_id
        )

        # Should be valid but with warnings
        assert result.is_valid is True
        assert result.warnings is not None
        assert any("Same ID value used for multiple parameters" in warning
                  for warning in result.warnings)

    def test_critical_mcp_confusion_detection(self):
        """Test detection of critical MCP task ID confusion scenarios."""
        # Simulate the exact bug scenario from subtask_mcp_controller.py:270
        task_id = str(uuid4())

        # Mock scenario where task_id gets incorrectly passed as git_branch_id
        class MockValidator(IDValidator):
            def detect_id_type(self, value, context_hint=None):
                result = super().detect_id_type(value, context_hint)
                # Simulate MCP task ID detection
                if context_hint == "git_branch_id" and value == task_id:
                    result.id_type = IDType.MCP_TASK_ID
                    result.warnings = ["MCP task ID detected"]
                return result

        mock_validator = MockValidator()

        # This should trigger the critical error
        result = mock_validator.validate_parameter_mapping(
            task_id=task_id,
            git_branch_id=task_id  # BUG: Same ID used incorrectly
        )

        assert result.is_valid is False
        assert "CRITICAL" in result.error_message
        assert "MCP task ID" in result.error_message
        assert "data integrity" in result.error_message

    def test_task_context_validation_edge_cases(self):
        """Test task context validation with edge cases."""
        task_id = str(uuid4())
        git_branch_id = str(uuid4())

        # Test with None git_branch_id (valid scenario)
        result = self.validator.validate_task_context(task_id=task_id)
        assert result.is_valid is True

        # Test with same IDs (critical error)
        result = self.validator.validate_task_context(
            task_id=task_id,
            expected_git_branch_id=task_id
        )
        assert result.is_valid is False
        assert "CRITICAL" in result.error_message
        assert "identical" in result.error_message

    def test_unicode_and_special_characters(self):
        """Test handling of Unicode and special characters in IDs."""
        # Unicode characters
        unicode_id = "550e8400-e29b-41d4-a716-44665544000ü"
        result = self.validator.validate_uuid_format(unicode_id)
        assert result.is_valid is False

        # Special characters
        special_char_id = "550e8400-e29b-41d4-a716-44665544000@"
        result = self.validator.validate_uuid_format(special_char_id)
        assert result.is_valid is False

    def test_null_and_empty_string_handling(self):
        """Test handling of null, empty, and whitespace-only strings."""
        test_values = [
            None,
            "",
            " ",
            "\t",
            "\n",
            "   \t\n   ",
        ]

        for value in test_values:
            result = self.validator.validate_uuid_format(value)
            assert result.is_valid is False
            assert "cannot be empty" in result.error_message

    def test_very_long_string_handling(self):
        """Test handling of extremely long strings."""
        # Very long string that might cause memory issues
        very_long_string = "a" * 10000
        result = self.validator.validate_uuid_format(very_long_string)
        assert result.is_valid is False
        assert "Invalid UUID format" in result.error_message

    def test_boundary_value_analysis(self):
        """Test boundary values for UUID validation."""
        # Exact UUID length but invalid format
        exact_length_invalid = "x" * 36
        result = self.validator.validate_uuid_format(exact_length_invalid)
        assert result.is_valid is False

        # One character short
        one_short = "550e8400-e29b-41d4-a716-44665544000"
        result = self.validator.validate_uuid_format(one_short)
        assert result.is_valid is False

        # One character long
        one_long = "550e8400-e29b-41d4-a716-446655440000x"
        result = self.validator.validate_uuid_format(one_long)
        assert result.is_valid is False

    def test_sql_injection_patterns(self):
        """Test that malicious SQL injection patterns are rejected."""
        sql_injection_patterns = [
            "550e8400'; DROP TABLE tasks; --",
            "550e8400' OR '1'='1",
            "550e8400-e29b-41d4-a716-446655440000; DELETE FROM users;",
            "550e8400-e29b-41d4-a716-446655440000' UNION SELECT * FROM sensitive_data --",
        ]

        for pattern in sql_injection_patterns:
            result = self.validator.validate_uuid_format(pattern)
            assert result.is_valid is False, f"Should reject SQL injection pattern: {pattern}"

    def test_fix_suggestions_comprehensive(self):
        """Test comprehensive fix suggestions for different contexts."""
        confused_id = str(uuid4())

        contexts = [
            "subtask_controller",
            "task_facade",
            "mcp_handler",
            "database_query",
            "api_endpoint"
        ]

        for context in contexts:
            suggestions = self.validator.suggest_fix_for_confusion(confused_id, context)

            # Verify all expected keys are present
            expected_keys = [
                "issue", "confused_id", "root_cause",
                "immediate_fix", "code_example", "prevention"
            ]
            for key in expected_keys:
                assert key in suggestions, f"Missing key '{key}' in suggestions for {context}"

            # Verify content quality
            assert context in suggestions["issue"]
            assert suggestions["confused_id"] == confused_id
            assert "WRONG" in suggestions["code_example"]
            assert "CORRECT" in suggestions["code_example"]

    def test_concurrent_validation_safety(self):
        """Test that validator is thread-safe for concurrent use."""
        import threading
        import time

        results = []
        errors = []

        def validate_worker():
            try:
                for _ in range(100):
                    uuid_val = str(uuid4())
                    result = self.validator.validate_uuid_format(uuid_val)
                    results.append(result.is_valid)
                    time.sleep(0.001)  # Small delay to encourage race conditions
            except Exception as e:
                errors.append(e)

        # Run multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=validate_worker)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify no errors and all validations succeeded
        assert len(errors) == 0, f"Concurrent validation errors: {errors}"
        assert all(results), "Some concurrent validations failed"
        assert len(results) == 500  # 5 threads * 100 iterations

    def test_memory_efficiency_large_batch(self):
        """Test memory efficiency with large batch of validations."""
        import gc
        import sys

        # Get initial memory usage
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Perform large batch of validations
        for i in range(1000):
            uuid_val = str(uuid4())
            result = self.validator.validate_uuid_format(uuid_val)
            assert result.is_valid is True

            # Periodically check memory isn't growing excessively
            if i % 100 == 0:
                gc.collect()
                current_objects = len(gc.get_objects())
                # Allow some growth but not excessive
                assert current_objects < initial_objects * 2, f"Memory usage grew too much: {current_objects} vs {initial_objects}"

    def test_validator_state_isolation(self):
        """Test that different validator instances don't share state."""
        # Create two validators with different settings
        strict_validator = IDValidator(strict_uuid_validation=True)
        relaxed_validator = IDValidator(strict_uuid_validation=False)

        # UUID v1 that should behave differently
        uuid_v1 = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"

        strict_result = strict_validator.validate_uuid_format(uuid_v1)
        relaxed_result = relaxed_validator.validate_uuid_format(uuid_v1)

        # Results should be different
        assert strict_result.is_valid is False
        assert relaxed_result.is_valid is True

        # Verify internal state didn't change
        assert strict_validator.strict_uuid_validation is True
        assert relaxed_validator.strict_uuid_validation is False

    def test_error_message_localization_ready(self):
        """Test that error messages are structured for potential localization."""
        result = self.validator.validate_uuid_format("invalid")

        # Error message should contain specific information
        assert result.error_message is not None
        assert "Invalid UUID format" in result.error_message
        assert "Expected:" in result.error_message

        # Should contain the invalid value for debugging
        assert "invalid" in result.error_message


class TestConvenienceFunctionsEdgeCases:
    """Edge case tests for convenience functions."""

    def test_prevent_id_confusion_with_all_none(self):
        """Test prevent_id_confusion with all None parameters."""
        with pytest.raises(IDValidationError) as exc_info:
            prevent_id_confusion()

        assert "At least one parameter must be provided" in str(exc_info.value)

    def test_prevent_id_confusion_exception_details(self):
        """Test that prevent_id_confusion provides detailed exception information."""
        invalid_id = "not-a-uuid"

        with pytest.raises(IDValidationError) as exc_info:
            prevent_id_confusion(task_id=invalid_id)

        # Verify exception contains useful information
        error = exc_info.value
        assert error.id_value is not None
        assert "Invalid UUID format" in str(error)

    def test_is_mcp_task_id_edge_cases(self):
        """Test is_mcp_task_id with various edge cases."""
        # Valid UUID (should return True since format is valid)
        assert is_mcp_task_id(str(uuid4())) is True

        # Invalid formats
        assert is_mcp_task_id("not-a-uuid") is False
        assert is_mcp_task_id("") is False
        assert is_mcp_task_id(None) is False

        # Edge cases
        assert is_mcp_task_id("  " + str(uuid4()) + "  ") is True  # With whitespace

    def test_validate_uuid_function_consistency(self):
        """Test that validate_uuid function behaves consistently."""
        test_uuid = str(uuid4())

        # Should be consistent across calls
        result1 = validate_uuid(test_uuid, strict=True)
        result2 = validate_uuid(test_uuid, strict=True)
        assert result1 == result2

        # Different strict settings should give different results for v1 UUIDs
        uuid_v1 = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        strict_result = validate_uuid(uuid_v1, strict=True)
        relaxed_result = validate_uuid(uuid_v1, strict=False)

        assert strict_result is False
        assert relaxed_result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])