"""Test suite for ComplianceService.

Tests for compliance validation and enforcement functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any
import uuid
from datetime import datetime

from fastmcp.task_management.application.services.compliance_service import ComplianceService
from fastmcp.task_management.domain.enums.compliance_enums import ComplianceLevel, ValidationResult, SecurityLevel
from fastmcp.task_management.domain.value_objects.compliance_objects import ComplianceRule, ValidationReport, SecurityContext
from fastmcp.task_management.infrastructure.validation.document_validator import DocumentValidator
from fastmcp.task_management.infrastructure.security.access_controller import AccessController


class TestComplianceService:
    """Test the ComplianceService class."""

    def test_compliance_service_initialization(self):
        """Test ComplianceService initialization."""
        service = ComplianceService()
        
        assert service._document_validator is not None
        assert service._access_controller is not None
        assert service._user_id is None
        assert len(service._compliance_rules) == 2  # DOC_VALIDATION and SECURITY_VALIDATION

    def test_compliance_service_initialization_with_dependencies(self):
        """Test ComplianceService initialization with injected dependencies."""
        mock_doc_validator = Mock(spec=DocumentValidator)
        mock_access_controller = Mock(spec=AccessController)
        user_id = "test_user_123"
        
        service = ComplianceService(
            document_validator=mock_doc_validator,
            access_controller=mock_access_controller,
            user_id=user_id
        )
        
        assert service._document_validator == mock_doc_validator
        assert service._access_controller == mock_access_controller
        assert service._user_id == user_id

    def test_with_user_method(self):
        """Test with_user method creates new instance with user context."""
        original_service = ComplianceService()
        user_id = "test_user_456"
        
        user_scoped_service = original_service.with_user(user_id)
        
        assert user_scoped_service._user_id == user_id
        assert user_scoped_service is not original_service
        assert isinstance(user_scoped_service, ComplianceService)

    def test_initialize_compliance_rules(self):
        """Test initialization of default compliance rules."""
        service = ComplianceService()
        rules = service.get_compliance_rules()
        
        assert len(rules) == 2
        
        doc_rule = next((r for r in rules if r.rule_id == "DOC_VALIDATION"), None)
        assert doc_rule is not None
        assert doc_rule.name == "Document Validation"
        assert doc_rule.level == ComplianceLevel.HIGH
        assert doc_rule.category == "document_compliance"
        
        security_rule = next((r for r in rules if r.rule_id == "SECURITY_VALIDATION"), None)
        assert security_rule is not None
        assert security_rule.name == "Security Access Control"
        assert security_rule.level == ComplianceLevel.CRITICAL
        assert security_rule.category == "security_compliance"


class TestComplianceRuleManagement:
    """Test compliance rule management functionality."""

    def test_add_compliance_rule(self):
        """Test adding a new compliance rule."""
        service = ComplianceService()
        
        new_rule = ComplianceRule(
            rule_id="TEST_RULE",
            name="Test Rule",
            description="Test rule description",
            level=ComplianceLevel.MEDIUM,
            category="test_compliance"
        )
        
        with patch('fastmcp.task_management.application.services.compliance_service.logger') as mock_logger:
            service.add_compliance_rule(new_rule)
            mock_logger.info.assert_called_with("Added compliance rule: TEST_RULE")
        
        rules = service.get_compliance_rules()
        assert len(rules) == 3
        
        test_rule = next((r for r in rules if r.rule_id == "TEST_RULE"), None)
        assert test_rule is not None
        assert test_rule.name == "Test Rule"

    def test_remove_compliance_rule_existing(self):
        """Test removing an existing compliance rule."""
        service = ComplianceService()
        
        with patch('fastmcp.task_management.application.services.compliance_service.logger') as mock_logger:
            removed = service.remove_compliance_rule("DOC_VALIDATION")
            mock_logger.info.assert_called_with("Removed compliance rule: DOC_VALIDATION")
        
        assert removed is True
        rules = service.get_compliance_rules()
        assert len(rules) == 1
        assert all(r.rule_id != "DOC_VALIDATION" for r in rules)

    def test_remove_compliance_rule_nonexistent(self):
        """Test removing a non-existent compliance rule."""
        service = ComplianceService()
        
        with patch('fastmcp.task_management.application.services.compliance_service.logger') as mock_logger:
            removed = service.remove_compliance_rule("NONEXISTENT_RULE")
            mock_logger.info.assert_not_called()
        
        assert removed is False
        rules = service.get_compliance_rules()
        assert len(rules) == 2  # Original rules unchanged

    def test_get_compliance_rules_returns_copy(self):
        """Test that get_compliance_rules returns a copy of the rules list."""
        service = ComplianceService()
        
        rules1 = service.get_compliance_rules()
        rules2 = service.get_compliance_rules()
        
        # Should be different list objects but same content
        assert rules1 is not rules2
        assert len(rules1) == len(rules2)
        assert rules1[0].rule_id == rules2[0].rule_id


class TestComplianceValidation:
    """Test compliance validation functionality."""

    def test_validate_operation_edit_file_success(self):
        """Test successful validation of edit_file operation."""
        mock_doc_validator = Mock(spec=DocumentValidator)
        mock_access_controller = Mock(spec=AccessController)
        
        # Mock successful document validation
        mock_doc_validator.validate_document_creation.return_value = {
            "success": True,
            "compliance_score": 95.0
        }
        
        # Mock successful security validation
        mock_access_controller.validate_access.return_value = {
            "success": True,
            "access_granted": True
        }
        
        service = ComplianceService(mock_doc_validator, mock_access_controller)
        
        result = service.validate_operation(
            "edit_file",
            file_path="/test/file.py",
            content="print('hello')",
            security_level="public"
        )
        
        assert result["success"] is True
        assert result["operation"] == "edit_file"
        assert result["compliance_score"] == 97.5
        assert len(result["validation_results"]) == 2
        assert "timestamp" in result

    def test_validate_operation_edit_file_document_failure(self):
        """Test validation failure due to document validation."""
        mock_doc_validator = Mock(spec=DocumentValidator)
        mock_access_controller = Mock(spec=AccessController)
        
        # Mock failed document validation
        mock_doc_validator.validate_document_creation.return_value = {
            "success": False,
            "compliance_score": 30.0
        }
        
        # Mock successful security validation
        mock_access_controller.validate_access.return_value = {
            "success": True,
            "access_granted": True
        }
        
        service = ComplianceService(mock_doc_validator, mock_access_controller)
        
        result = service.validate_operation(
            "edit_file",
            file_path="/test/file.py",
            content="malicious_content",
            security_level="public"
        )
        
        assert result["success"] is False
        assert result["compliance_score"] == 65.0  # Average of 30.0 and 100.0

    def test_validate_operation_security_failure(self):
        """Test validation failure due to security validation."""
        mock_doc_validator = Mock(spec=DocumentValidator)
        mock_access_controller = Mock(spec=AccessController)
        
        # Mock successful document validation
        mock_doc_validator.validate_document_creation.return_value = {
            "success": True,
            "compliance_score": 90.0
        }
        
        # Mock failed security validation
        mock_access_controller.validate_access.return_value = {
            "success": False,
            "access_granted": False
        }
        
        service = ComplianceService(mock_doc_validator, mock_access_controller)
        
        result = service.validate_operation(
            "edit_file",
            file_path="/restricted/file.py",
            content="print('hello')",
            security_level="restricted"
        )
        
        assert result["success"] is False
        assert result["compliance_score"] == 45.0  # Average of 90.0 and 0.0

    def test_validate_operation_run_command_security_only(self):
        """Test validation of run_command operation (security validation only)."""
        mock_doc_validator = Mock(spec=DocumentValidator)
        mock_access_controller = Mock(spec=AccessController)
        
        # Mock successful security validation
        mock_access_controller.validate_access.return_value = {
            "success": True,
            "access_granted": True
        }
        
        service = ComplianceService(mock_doc_validator, mock_access_controller)
        
        result = service.validate_operation(
            "run_command",
            resource_path="/bin/ls",
            security_level="public"
        )
        
        assert result["success"] is True
        assert result["compliance_score"] == 100.0
        assert len(result["validation_results"]) == 1  # Only security validation

    def test_validate_operation_invalid_security_level(self):
        """Test validation with invalid security level (defaults to public)."""
        mock_doc_validator = Mock(spec=DocumentValidator)
        mock_access_controller = Mock(spec=AccessController)
        
        mock_access_controller.validate_access.return_value = {
            "success": True,
            "access_granted": True
        }
        
        service = ComplianceService(mock_doc_validator, mock_access_controller)
        
        with patch('fastmcp.task_management.application.services.compliance_service.logger') as mock_logger:
            result = service.validate_operation(
                "run_command",
                resource_path="/bin/ls",
                security_level="invalid_level"
            )
            
            mock_logger.warning.assert_called()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert "Invalid security level" in warning_msg
        
        # Should still succeed with default security level
        assert result["success"] is True

    def test_validate_operation_no_file_operations(self):
        """Test validation of operation without file operations."""
        service = ComplianceService()
        
        result = service.validate_operation("list_tasks")
        
        # No validation rules apply, should succeed with perfect score
        assert result["success"] is True
        assert result["compliance_score"] == 100.0
        assert len(result["validation_results"]) == 0

    def test_validate_operation_exception_handling(self):
        """Test validation operation exception handling."""
        mock_doc_validator = Mock(spec=DocumentValidator)
        mock_doc_validator.validate_document_creation.side_effect = Exception("Validation error")
        
        service = ComplianceService(mock_doc_validator)
        
        result = service.validate_operation(
            "edit_file",
            file_path="/test/file.py",
            content="content"
        )
        
        assert result["success"] is False
        assert result["compliance_score"] == 50.0


class TestDocumentValidation:
    """Test document validation functionality."""

    def test_validate_document_operation_success(self):
        """Test successful document validation."""
        mock_doc_validator = Mock(spec=DocumentValidator)
        mock_doc_validator.validate_document_creation.return_value = {
            "success": True,
            "compliance_score": 88.5
        }
        
        service = ComplianceService(mock_doc_validator)
        
        result = service._validate_document_operation({
            "file_path": "/test/document.md",
            "content": "# Valid Document\n\nContent here."
        })
        
        assert result is not None
        assert result["rule_id"] == "DOC_VALIDATION"
        assert result["rule_name"] == "Document Validation"
        assert result["category"] == "document_compliance"
        assert result["success"] is True
        assert result["compliance_score"] == 88.5
        assert result["result"] == ValidationResult.PASSED

    def test_validate_document_operation_failure(self):
        """Test failed document validation."""
        mock_doc_validator = Mock(spec=DocumentValidator)
        mock_doc_validator.validate_document_creation.return_value = {
            "success": False,
            "compliance_score": 25.0
        }
        
        service = ComplianceService(mock_doc_validator)
        
        result = service._validate_document_operation({
            "file_path": "/test/invalid.md",
            "content": "Invalid content"
        })
        
        assert result is not None
        assert result["success"] is False
        assert result["compliance_score"] == 25.0
        assert result["result"] == ValidationResult.FAILED

    def test_validate_document_operation_missing_data(self):
        """Test document validation with missing file path or content."""
        service = ComplianceService()
        
        # Missing file_path
        result = service._validate_document_operation({
            "content": "content"
        })
        assert result is None
        
        # Missing content
        result = service._validate_document_operation({
            "file_path": "/test/file.md"
        })
        assert result is None
        
        # Both missing
        result = service._validate_document_operation({})
        assert result is None

    def test_validate_document_operation_exception(self):
        """Test document validation exception handling."""
        mock_doc_validator = Mock(spec=DocumentValidator)
        mock_doc_validator.validate_document_creation.side_effect = Exception("Validation failed")
        
        service = ComplianceService(mock_doc_validator)
        
        with patch('fastmcp.task_management.application.services.compliance_service.logger') as mock_logger:
            result = service._validate_document_operation({
                "file_path": "/test/file.md",
                "content": "content"
            })
            
            mock_logger.error.assert_called()
        
        assert result is not None
        assert result["success"] is False
        assert result["compliance_score"] == 0.0
        assert result["result"] == ValidationResult.FAILED
        assert "error" in result["details"]


class TestSecurityValidation:
    """Test security validation functionality."""

    def test_validate_security_operation_success(self):
        """Test successful security validation."""
        mock_access_controller = Mock(spec=AccessController)
        mock_access_controller.validate_access.return_value = {
            "success": True,
            "access_granted": True
        }
        
        service = ComplianceService(access_controller=mock_access_controller)
        
        result = service._validate_security_operation("edit_file", {
            "file_path": "/public/file.py",
            "user_id": "user123",
            "security_level": "public",
            "permissions": ["read", "write"]
        })
        
        assert result is not None
        assert result["rule_id"] == "SECURITY_VALIDATION"
        assert result["rule_name"] == "Security Access Control"
        assert result["category"] == "security_compliance"
        assert result["success"] is True
        assert result["compliance_score"] == 100.0
        assert result["result"] == ValidationResult.PASSED
        
        # Verify SecurityContext was created correctly
        mock_access_controller.validate_access.assert_called_once()
        call_args = mock_access_controller.validate_access.call_args[0][0]
        assert isinstance(call_args, SecurityContext)
        assert call_args.user_id == "user123"
        assert call_args.operation == "edit_file"
        assert call_args.resource_path == "/public/file.py"
        assert call_args.security_level == SecurityLevel.PUBLIC
        assert call_args.permissions == ("read", "write")

    def test_validate_security_operation_access_denied(self):
        """Test security validation with access denied."""
        mock_access_controller = Mock(spec=AccessController)
        mock_access_controller.validate_access.return_value = {
            "success": True,
            "access_granted": False
        }
        
        service = ComplianceService(access_controller=mock_access_controller)
        
        result = service._validate_security_operation("edit_file", {
            "file_path": "/restricted/file.py",
            "security_level": "restricted"
        })
        
        assert result is not None
        assert result["success"] is False
        assert result["compliance_score"] == 0.0
        assert result["result"] == ValidationResult.FAILED

    def test_validate_security_operation_missing_resource_path(self):
        """Test security validation with missing resource path."""
        service = ComplianceService()
        
        result = service._validate_security_operation("edit_file", {
            "user_id": "user123"
            # Missing file_path, target_file, resource_path
        })
        
        assert result is None

    def test_validate_security_operation_alternative_path_keys(self):
        """Test security validation with alternative resource path keys."""
        mock_access_controller = Mock(spec=AccessController)
        mock_access_controller.validate_access.return_value = {
            "success": True,
            "access_granted": True
        }
        
        service = ComplianceService(access_controller=mock_access_controller)
        
        # Test target_file key
        result = service._validate_security_operation("create_file", {
            "target_file": "/test/new_file.py"
        })
        
        assert result is not None
        assert result["success"] is True
        
        # Test resource_path key
        result = service._validate_security_operation("access_resource", {
            "resource_path": "/api/endpoint"
        })
        
        assert result is not None
        assert result["success"] is True

    def test_validate_security_operation_exception(self):
        """Test security validation exception handling."""
        mock_access_controller = Mock(spec=AccessController)
        mock_access_controller.validate_access.side_effect = Exception("Security check failed")
        
        service = ComplianceService(access_controller=mock_access_controller)
        
        with patch('fastmcp.task_management.application.services.compliance_service.logger') as mock_logger:
            result = service._validate_security_operation("edit_file", {
                "file_path": "/test/file.py"
            })
            
            mock_logger.error.assert_called()
        
        assert result is not None
        assert result["success"] is False
        assert result["compliance_score"] == 0.0
        assert result["result"] == ValidationResult.FAILED


class TestComplianceReporting:
    """Test compliance report generation functionality."""

    def test_generate_compliance_report_success(self):
        """Test successful compliance report generation."""
        service = ComplianceService()
        
        report = service.generate_compliance_report()
        
        assert isinstance(report, ValidationReport)
        assert report.report_id is not None
        assert report.timestamp > 0
        assert report.total_rules == 2  # Default rules
        assert report.passed == 2
        assert report.failed == 0
        assert report.overall_compliance == 100.0
        assert "Review compliance rules regularly" in report.recommendations

    def test_generate_compliance_report_exception(self):
        """Test compliance report generation with exception."""
        service = ComplianceService()
        
        # Mock an error in the report generation
        with patch.object(service, '_compliance_rules', side_effect=Exception("Report error")):
            report = service.generate_compliance_report()
        
        assert isinstance(report, ValidationReport)
        assert report.total_rules == 0
        assert report.passed == 0
        assert report.failed == 0
        assert report.overall_compliance == 100.0


class TestComplianceUtilities:
    """Test utility methods in compliance service."""

    def test_calculate_overall_compliance_empty_results(self):
        """Test overall compliance calculation with empty results."""
        service = ComplianceService()
        
        success, score = service._calculate_overall_compliance([])
        
        assert success is True
        assert score == 100.0

    def test_calculate_overall_compliance_mixed_results(self):
        """Test overall compliance calculation with mixed results."""
        service = ComplianceService()
        
        validation_results = [
            {"success": True, "compliance_score": 90.0},
            {"success": True, "compliance_score": 80.0},
            {"success": False, "compliance_score": 60.0}
        ]
        
        success, score = service._calculate_overall_compliance(validation_results)
        
        assert success is False  # Not all successful
        assert abs(score - 76.67) < 0.01  # Average of 90, 80, 60 rounded to 2 decimals

    def test_calculate_overall_compliance_all_successful(self):
        """Test overall compliance calculation with all successful results."""
        service = ComplianceService()
        
        validation_results = [
            {"success": True, "compliance_score": 95.0},
            {"success": True, "compliance_score": 88.0},
            {"success": True, "compliance_score": 92.0}
        ]
        
        success, score = service._calculate_overall_compliance(validation_results)
        
        assert success is True
        assert abs(score - 91.67) < 0.01  # Average of 95, 88, 92

    def test_calculate_overall_compliance_missing_scores(self):
        """Test overall compliance calculation with missing compliance scores."""
        service = ComplianceService()
        
        validation_results = [
            {"success": True},  # Missing compliance_score
            {"success": True, "compliance_score": 80.0},
            {"success": False}  # Missing compliance_score
        ]
        
        success, score = service._calculate_overall_compliance(validation_results)
        
        assert success is False
        assert abs(score - 26.67) < 0.01  # Average of 0, 80, 0