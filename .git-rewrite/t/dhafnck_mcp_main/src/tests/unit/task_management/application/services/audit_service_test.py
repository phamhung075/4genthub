"""Test suite for AuditService.

Tests for audit trail management and compliance monitoring functionality.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from typing import Dict, Any

from fastmcp.task_management.application.services.audit_service import AuditService
from fastmcp.task_management.domain.enums.compliance_enums import ComplianceLevel, ValidationResult
from fastmcp.task_management.domain.value_objects.compliance_objects import ValidationReport


class TestAuditService:
    """Test the AuditService class."""

    def test_audit_service_initialization(self):
        """Test AuditService initialization."""
        service = AuditService()
        
        assert service._audit_log == []
        assert service._compliance_metrics["total_operations"] == 0
        assert service._compliance_metrics["compliant_operations"] == 0
        assert service._compliance_metrics["violations"] == 0
        assert service._compliance_metrics["last_audit"] is None

    def test_audit_service_initialization_with_user(self):
        """Test AuditService initialization with user context."""
        user_id = "test_user_123"
        service = AuditService(user_id=user_id)
        
        assert service._user_id == user_id
        assert service._audit_log == []

    def test_with_user_method(self):
        """Test with_user method creates new instance with user context."""
        original_service = AuditService()
        user_id = "test_user_456"
        
        user_scoped_service = original_service.with_user(user_id)
        
        assert user_scoped_service._user_id == user_id
        assert user_scoped_service is not original_service
        assert isinstance(user_scoped_service, AuditService)

    def test_get_user_scoped_repository_with_with_user_method(self):
        """Test _get_user_scoped_repository with repository that has with_user method."""
        service = AuditService(user_id="test_user")
        mock_repo = Mock()
        mock_user_scoped_repo = Mock()
        mock_repo.with_user.return_value = mock_user_scoped_repo
        
        result = service._get_user_scoped_repository(mock_repo)
        
        assert result == mock_user_scoped_repo
        mock_repo.with_user.assert_called_once_with("test_user")


    def test_get_user_scoped_repository_no_user_context(self):
        """Test _get_user_scoped_repository returns original repo when no user context."""
        service = AuditService()  # No user_id
        mock_repo = Mock()
        
        result = service._get_user_scoped_repository(mock_repo)
        
        assert result == mock_repo

    def test_get_user_scoped_repository_none_repo(self):
        """Test _get_user_scoped_repository handles None repository."""
        service = AuditService(user_id="test_user")
        
        result = service._get_user_scoped_repository(None)
        
        assert result is None


class TestAuditServiceLogging:
    """Test audit logging functionality."""

    def test_log_operation_with_compliance_level_enum(self):
        """Test logging operation with ComplianceLevel enum."""
        service = AuditService()
        operation = "test_operation"
        result = {"success": True, "compliance_score": 90.0}
        
        service.log_operation(operation, result, ComplianceLevel.HIGH)
        
        assert len(service._audit_log) == 1
        audit_entry = service._audit_log[0]
        assert audit_entry["operation"] == operation
        assert audit_entry["compliance_level"] == "high"
        assert audit_entry["success"] is True
        assert audit_entry["compliance_score"] == 90.0
        assert "timestamp" in audit_entry

    def test_log_operation_with_string_compliance_level(self):
        """Test logging operation with string compliance level (backwards compatibility)."""
        service = AuditService()
        operation = "test_operation"
        result = {"success": True, "compliance_score": 85.0}
        
        with patch('fastmcp.task_management.application.services.audit_service.logger') as mock_logger:
            service.log_operation(operation, result, "medium")
            
            # Should log warning about string usage
            mock_logger.warning.assert_called()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "string compliance level" in warning_call

        assert len(service._audit_log) == 1
        audit_entry = service._audit_log[0]
        assert audit_entry["compliance_level"] == "medium"

    def test_log_operation_with_invalid_string_compliance_level(self):
        """Test logging operation with invalid string compliance level."""
        service = AuditService()
        operation = "test_operation"
        result = {"success": True, "compliance_score": 85.0}
        
        with patch('fastmcp.task_management.application.services.audit_service.logger') as mock_logger:
            service.log_operation(operation, result, "invalid_level")
            
            # Should log warnings about invalid level and default usage
            assert mock_logger.warning.call_count == 2

        assert len(service._audit_log) == 1
        audit_entry = service._audit_log[0]
        assert audit_entry["compliance_level"] == "low"  # Default value

    def test_log_operation_updates_metrics_compliant(self):
        """Test that logging compliant operation updates metrics correctly."""
        service = AuditService()
        operation = "test_operation"
        result = {"success": True, "compliance_score": 90.0}
        
        service.log_operation(operation, result, ComplianceLevel.HIGH)
        
        metrics = service.get_compliance_metrics()
        assert metrics["total_operations"] == 1
        assert metrics["compliant_operations"] == 1
        assert metrics["violations"] == 0
        assert metrics["last_audit"] is not None

    def test_log_operation_updates_metrics_violation(self):
        """Test that logging violation updates metrics correctly."""
        service = AuditService()
        operation = "test_operation"
        result = {"success": False, "compliance_score": 60.0}
        
        service.log_operation(operation, result, ComplianceLevel.HIGH)
        
        metrics = service.get_compliance_metrics()
        assert metrics["total_operations"] == 1
        assert metrics["compliant_operations"] == 0
        assert metrics["violations"] == 1

    def test_log_operation_low_compliance_score(self):
        """Test that low compliance score counts as violation."""
        service = AuditService()
        operation = "test_operation"
        result = {"success": True, "compliance_score": 80.0}  # Below 85 threshold
        
        service.log_operation(operation, result, ComplianceLevel.HIGH)
        
        metrics = service.get_compliance_metrics()
        assert metrics["violations"] == 1
        assert metrics["compliant_operations"] == 0

    def test_get_audit_log(self):
        """Test retrieving audit log entries."""
        service = AuditService()
        
        # Add multiple entries
        for i in range(5):
            service.log_operation(f"operation_{i}", {"success": True}, ComplianceLevel.MEDIUM)
        
        # Test default limit
        log_entries = service.get_audit_log()
        assert len(log_entries) == 5
        
        # Test custom limit
        log_entries = service.get_audit_log(limit=3)
        assert len(log_entries) == 3
        
        # Test getting all entries
        log_entries = service.get_audit_log(limit=0)
        assert len(log_entries) == 5

    def test_get_audit_log_recent_entries(self):
        """Test that get_audit_log returns most recent entries."""
        service = AuditService()
        
        # Add many entries to test limit functionality
        for i in range(150):
            service.log_operation(f"operation_{i}", {"success": True}, ComplianceLevel.MEDIUM)
        
        log_entries = service.get_audit_log(limit=100)
        assert len(log_entries) == 100
        
        # Should get the last 100 entries (50-149)
        assert log_entries[0]["operation"] == "operation_50"
        assert log_entries[-1]["operation"] == "operation_149"


class TestAuditServiceReporting:
    """Test audit reporting functionality."""

    def test_generate_compliance_report_empty_log(self):
        """Test generating compliance report with empty audit log."""
        service = AuditService()
        
        report = service.generate_compliance_report()
        
        assert "report_id" in report
        assert report["overall_compliance_rate"] == 0.0
        assert report["total_operations"] == 0
        assert report["compliant_operations"] == 0
        assert report["violations"] == 0
        assert report["recent_violations"] == []
        assert "generated_at" in report

    def test_generate_compliance_report_with_data(self):
        """Test generating compliance report with audit data."""
        service = AuditService()
        
        # Add compliant operations
        for i in range(8):
            service.log_operation(f"good_op_{i}", {"success": True, "compliance_score": 90}, ComplianceLevel.HIGH)
        
        # Add violations
        for i in range(2):
            service.log_operation(f"bad_op_{i}", {"success": False, "compliance_score": 50}, ComplianceLevel.HIGH)
        
        report = service.generate_compliance_report()
        
        assert report["overall_compliance_rate"] == 80.0  # 8 compliant out of 10
        assert report["total_operations"] == 10
        assert report["compliant_operations"] == 8
        assert report["violations"] == 2
        assert len(report["recent_violations"]) == 2

    def test_generate_compliance_report_error_handling(self):
        """Test compliance report generation handles errors gracefully."""
        service = AuditService()
        
        # Mock an error in the metrics calculation
        with patch.object(service, '_compliance_metrics', side_effect=Exception("Test error")):
            report = service.generate_compliance_report()
            
            assert "error" in report
            assert report["overall_compliance_rate"] == 0.0

    def test_calculate_compliance_trend_insufficient_data(self):
        """Test compliance trend calculation with insufficient data."""
        service = AuditService()
        
        # Add less than 20 entries
        for i in range(15):
            service.log_operation(f"op_{i}", {"success": True}, ComplianceLevel.HIGH)
        
        trend = service._calculate_compliance_trend()
        assert trend == "insufficient_data"

    def test_calculate_compliance_trend_improving(self):
        """Test compliance trend calculation showing improvement."""
        service = AuditService()
        
        # Add 10 failing operations
        for i in range(10):
            service.log_operation(f"bad_op_{i}", {"success": False}, ComplianceLevel.HIGH)
        
        # Add 10 successful operations
        for i in range(10):
            service.log_operation(f"good_op_{i}", {"success": True}, ComplianceLevel.HIGH)
        
        trend = service._calculate_compliance_trend()
        assert trend == "improving"

    def test_calculate_compliance_trend_declining(self):
        """Test compliance trend calculation showing decline."""
        service = AuditService()
        
        # Add 10 successful operations
        for i in range(10):
            service.log_operation(f"good_op_{i}", {"success": True}, ComplianceLevel.HIGH)
        
        # Add 10 failing operations
        for i in range(10):
            service.log_operation(f"bad_op_{i}", {"success": False}, ComplianceLevel.HIGH)
        
        trend = service._calculate_compliance_trend()
        assert trend == "declining"

    def test_calculate_compliance_trend_stable(self):
        """Test compliance trend calculation showing stable performance."""
        service = AuditService()
        
        # Add mixed operations with similar success rates
        for i in range(20):
            success = i % 2 == 0  # 50% success rate throughout
            service.log_operation(f"op_{i}", {"success": success}, ComplianceLevel.HIGH)
        
        trend = service._calculate_compliance_trend()
        assert trend == "stable"

    def test_generate_recommendations_good_compliance(self):
        """Test recommendations generation for good compliance."""
        service = AuditService()
        
        # Add compliant operations
        for i in range(10):
            service.log_operation(f"op_{i}", {"success": True, "compliance_score": 95}, ComplianceLevel.HIGH)
        
        recommendations = service._generate_recommendations()
        
        assert "Compliance is on track" in recommendations[0]

    def test_generate_recommendations_poor_compliance(self):
        """Test recommendations generation for poor compliance."""
        service = AuditService()
        
        # Add non-compliant operations (>10 to trigger high violations warning)
        for i in range(11):
            service.log_operation(f"op_{i}", {"success": False, "compliance_score": 50}, ComplianceLevel.HIGH)
        
        recommendations = service._generate_recommendations()
        
        assert any("compliance below target" in rec for rec in recommendations)
        assert any("High number of violations detected" in rec for rec in recommendations)
        assert any("Frequent failures detected" in rec for rec in recommendations)


class TestAuditServiceManagement:
    """Test audit service management functionality."""

    def test_get_compliance_metrics(self):
        """Test getting compliance metrics."""
        service = AuditService()
        
        # Add some operations
        service.log_operation("op1", {"success": True, "compliance_score": 90}, ComplianceLevel.HIGH)
        service.log_operation("op2", {"success": False, "compliance_score": 40}, ComplianceLevel.HIGH)
        
        metrics = service.get_compliance_metrics()
        
        assert metrics["total_operations"] == 2
        assert metrics["compliant_operations"] == 1
        assert metrics["violations"] == 1
        assert metrics["last_audit"] is not None
        
        # Should be a copy, not the original
        metrics["total_operations"] = 999
        assert service._compliance_metrics["total_operations"] == 2

    def test_clear_audit_log(self):
        """Test clearing audit log and resetting metrics."""
        service = AuditService()
        
        # Add some data
        service.log_operation("op1", {"success": True}, ComplianceLevel.HIGH)
        service.log_operation("op2", {"success": False}, ComplianceLevel.HIGH)
        
        assert len(service._audit_log) == 2
        assert service._compliance_metrics["total_operations"] == 2
        
        # Clear the log
        with patch('fastmcp.task_management.application.services.audit_service.logger') as mock_logger:
            service.clear_audit_log()
            mock_logger.info.assert_called_with("Audit log cleared")
        
        assert len(service._audit_log) == 0
        assert service._compliance_metrics["total_operations"] == 0
        assert service._compliance_metrics["compliant_operations"] == 0
        assert service._compliance_metrics["violations"] == 0
        assert service._compliance_metrics["last_audit"] is None

    def test_audit_entry_structure(self):
        """Test that audit entries have correct structure."""
        service = AuditService()
        operation = "test_operation"
        result = {"success": True, "compliance_score": 88.5, "custom_field": "value"}
        
        service.log_operation(operation, result, ComplianceLevel.MEDIUM)
        
        audit_entry = service._audit_log[0]
        
        # Required fields
        assert "timestamp" in audit_entry
        assert "operation" in audit_entry
        assert "compliance_level" in audit_entry
        assert "success" in audit_entry
        assert "compliance_score" in audit_entry
        assert "details" in audit_entry
        
        # Values
        assert audit_entry["operation"] == operation
        assert audit_entry["compliance_level"] == "medium"
        assert audit_entry["success"] is True
        assert audit_entry["compliance_score"] == 88.5
        assert audit_entry["details"] == result
        
        # Timestamp should be ISO format
        datetime.fromisoformat(audit_entry["timestamp"])  # Should not raise

    def test_logging_with_partial_result_data(self):
        """Test logging operations with partial result data."""
        service = AuditService()
        
        # Test with minimal result data
        minimal_result = {}
        service.log_operation("minimal_op", minimal_result, ComplianceLevel.LOW)
        
        audit_entry = service._audit_log[0]
        assert audit_entry["success"] is False  # Default value
        assert audit_entry["compliance_score"] == 0  # Default value
        
        # Test with partial result data
        partial_result = {"success": True}  # Missing compliance_score
        service.log_operation("partial_op", partial_result, ComplianceLevel.HIGH)
        
        audit_entry = service._audit_log[1]
        assert audit_entry["success"] is True
        assert audit_entry["compliance_score"] == 0  # Default value