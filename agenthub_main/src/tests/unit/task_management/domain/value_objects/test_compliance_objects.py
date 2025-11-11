"""Unit tests for compliance and document value objects."""

from datetime import UTC, datetime

import pytest

from fastmcp.task_management.domain.value_objects.compliance_objects import (
    ComplianceStatus,
    DocumentInfo,
    DocumentType,
    ValidationReport,
    ValidationResult,
)


class TestDocumentInfo:
    """Test cases for DocumentInfo value object."""

    def test_create_document_info_valid(self):
        """Test creating document info with valid data."""
        now = datetime.now(UTC)
        metadata = {"author": "test_user", "version": "1.0"}

        doc_info = DocumentInfo(
            path="/docs/test.md",
            type=DocumentType.DOCUMENT,
            content="Test content",
            metadata=metadata,
            created_at=now,
            updated_at=now,
            hash="abc123",
        )

        assert doc_info.path == "/docs/test.md"
        assert doc_info.type == DocumentType.DOCUMENT
        assert doc_info.content == "Test content"
        assert doc_info.metadata == metadata
        assert doc_info.created_at == now
        assert doc_info.updated_at == now
        assert doc_info.hash == "abc123"

    def test_create_document_info_minimal(self):
        """Test creating document info with minimal required fields."""
        now = datetime.now(UTC)

        doc_info = DocumentInfo(
            path="/config/settings.json",
            type=DocumentType.CONFIG,
            content='{"key": "value"}',
            metadata={},
            created_at=now,
        )

        assert doc_info.path == "/config/settings.json"
        assert doc_info.type == DocumentType.CONFIG
        assert doc_info.content == '{"key": "value"}'
        assert doc_info.metadata == {}
        assert doc_info.created_at == now
        assert doc_info.updated_at is None
        assert doc_info.hash is None

    def test_document_info_empty_path_validation(self):
        """Test that empty path raises ValueError."""
        with pytest.raises(ValueError, match="Document path cannot be empty"):
            DocumentInfo(
                path="",
                type=DocumentType.DOCUMENT,
                content="Content",
                metadata={},
                created_at=datetime.now(UTC),
            )

    def test_document_info_empty_content_validation(self):
        """Test that empty content raises ValueError."""
        with pytest.raises(ValueError, match="Document content cannot be empty"):
            DocumentInfo(
                path="/test.md",
                type=DocumentType.DOCUMENT,
                content="",
                metadata={},
                created_at=datetime.now(UTC),
            )

    def test_document_type_enum_values(self):
        """Test DocumentType enum values."""
        assert DocumentType.CONFIG.value == "config"
        assert DocumentType.TEMPLATE.value == "template"
        assert DocumentType.DOCUMENT.value == "document"
        assert DocumentType.AUDIT.value == "audit"
        assert DocumentType.REPORT.value == "report"

    def test_document_info_immutable(self):
        """Test that DocumentInfo is immutable (frozen)."""
        doc_info = DocumentInfo(
            path="/test.md",
            type=DocumentType.DOCUMENT,
            content="Test",
            metadata={},
            created_at=datetime.now(UTC),
        )

        with pytest.raises(AttributeError):
            doc_info.path = "/new/path.md"

        with pytest.raises(AttributeError):
            doc_info.content = "New content"


class TestComplianceStatus:
    """Test cases for ComplianceStatus value object."""

    def test_create_compliance_status(self):
        """Test creating compliance status with valid data."""
        now = datetime.now(UTC)
        issues = ["Missing signature", "Outdated template"]
        metadata = {"reviewed_by": "auditor1", "review_type": "quarterly"}

        status = ComplianceStatus(
            is_compliant=False,
            validation_date=now,
            validator="compliance_system",
            issues=issues,
            metadata=metadata,
        )

        assert status.is_compliant is False
        assert status.validation_date == now
        assert status.validator == "compliance_system"
        assert status.issues == issues
        assert len(status.issues) == 2
        assert status.metadata == metadata

    def test_compliant_status_no_issues(self):
        """Test compliant status with empty issues list."""
        status = ComplianceStatus(
            is_compliant=True,
            validation_date=datetime.now(UTC),
            validator="auto_validator",
            issues=[],
            metadata={"status": "approved"},
        )

        assert status.is_compliant is True
        assert len(status.issues) == 0
        assert status.metadata["status"] == "approved"

    def test_compliance_status_immutable(self):
        """Test that ComplianceStatus is immutable."""
        status = ComplianceStatus(
            is_compliant=True,
            validation_date=datetime.now(UTC),
            validator="test",
            issues=[],
            metadata={},
        )

        with pytest.raises(AttributeError):
            status.is_compliant = False


class TestValidationResult:
    """Test cases for ValidationResult value object."""

    def test_create_validation_result_with_errors(self):
        """Test creating validation result with errors."""
        errors = ["Field 'name' is required", "Invalid date format"]
        warnings = ["Field 'description' is recommended"]
        metadata = {"validator_version": "2.0", "rules_applied": 5}

        result = ValidationResult(
            is_valid=False, errors=errors, warnings=warnings, metadata=metadata
        )

        assert result.is_valid is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
        assert result.metadata["validator_version"] == "2.0"

    def test_create_validation_result_valid(self):
        """Test creating valid validation result."""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Consider adding more documentation"],
            metadata={"confidence": 0.95},
        )

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 1
        assert result.metadata["confidence"] == 0.95

    def test_validation_result_immutable(self):
        """Test that ValidationResult is immutable."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[], metadata={})

        with pytest.raises(AttributeError):
            result.is_valid = False


class TestValidationReport:
    """Test cases for ValidationReport value object."""

    def test_create_validation_report(self):
        """Test creating validation report with multiple results."""
        now = datetime.now(UTC)

        results = [
            ValidationResult(
                is_valid=False,
                errors=["Error 1", "Error 2"],
                warnings=["Warning 1"],
                metadata={},
            ),
            ValidationResult(
                is_valid=True,
                errors=[],
                warnings=["Warning 2", "Warning 3"],
                metadata={},
            ),
            ValidationResult(
                is_valid=False, errors=["Error 3"], warnings=[], metadata={}
            ),
        ]

        recommendations = [
            "Fix all validation errors",
            "Review warning messages",
            "Update documentation",
        ]

        report = ValidationReport(
            validation_id="val-123",
            entity_id="entity-456",
            entity_type="document",
            validation_timestamp=now,
            results=results,
            overall_status=False,
            summary="3 validation checks performed, 2 failed",
            recommendations=recommendations,
            metadata={"validator": "doc_validator_v2"},
        )

        assert report.validation_id == "val-123"
        assert report.entity_id == "entity-456"
        assert report.entity_type == "document"
        assert report.validation_timestamp == now
        assert len(report.results) == 3
        assert report.overall_status is False
        assert report.summary == "3 validation checks performed, 2 failed"
        assert len(report.recommendations) == 3

    def test_validation_report_total_errors(self):
        """Test calculating total errors across all results."""
        results = [
            ValidationResult(False, ["E1", "E2"], [], {}),
            ValidationResult(False, ["E3"], [], {}),
            ValidationResult(True, [], ["W1"], {}),
        ]

        report = ValidationReport(
            validation_id="val-1",
            entity_id="ent-1",
            entity_type="config",
            validation_timestamp=datetime.now(UTC),
            results=results,
            overall_status=False,
            summary="Validation failed",
            recommendations=[],
            metadata={},
        )

        assert report.total_errors == 3

    def test_validation_report_total_warnings(self):
        """Test calculating total warnings across all results."""
        results = [
            ValidationResult(True, [], ["W1", "W2"], {}),
            ValidationResult(True, [], ["W3"], {}),
            ValidationResult(False, ["E1"], ["W4", "W5"], {}),
        ]

        report = ValidationReport(
            validation_id="val-2",
            entity_id="ent-2",
            entity_type="template",
            validation_timestamp=datetime.now(UTC),
            results=results,
            overall_status=True,
            summary="Validation passed with warnings",
            recommendations=[],
            metadata={},
        )

        assert report.total_warnings == 5

    def test_validation_report_has_issues(self):
        """Test checking if report has any issues."""
        # Report with errors
        report_with_errors = ValidationReport(
            validation_id="val-3",
            entity_id="ent-3",
            entity_type="audit",
            validation_timestamp=datetime.now(UTC),
            results=[ValidationResult(False, ["Error"], [], {})],
            overall_status=False,
            summary="Has errors",
            recommendations=[],
            metadata={},
        )

        assert report_with_errors.has_issues is True

        # Report with warnings only
        report_with_warnings = ValidationReport(
            validation_id="val-4",
            entity_id="ent-4",
            entity_type="report",
            validation_timestamp=datetime.now(UTC),
            results=[ValidationResult(True, [], ["Warning"], {})],
            overall_status=True,
            summary="Has warnings",
            recommendations=[],
            metadata={},
        )

        assert report_with_warnings.has_issues is True

        # Clean report
        clean_report = ValidationReport(
            validation_id="val-5",
            entity_id="ent-5",
            entity_type="document",
            validation_timestamp=datetime.now(UTC),
            results=[ValidationResult(True, [], [], {})],
            overall_status=True,
            summary="All clear",
            recommendations=[],
            metadata={},
        )

        assert clean_report.has_issues is False

    def test_validation_report_empty_results(self):
        """Test validation report with no results."""
        report = ValidationReport(
            validation_id="val-6",
            entity_id="ent-6",
            entity_type="config",
            validation_timestamp=datetime.now(UTC),
            results=[],
            overall_status=True,
            summary="No validations performed",
            recommendations=[],
            metadata={},
        )

        assert report.total_errors == 0
        assert report.total_warnings == 0
        assert report.has_issues is False

    def test_validation_report_immutable(self):
        """Test that ValidationReport is immutable."""
        report = ValidationReport(
            validation_id="val-7",
            entity_id="ent-7",
            entity_type="template",
            validation_timestamp=datetime.now(UTC),
            results=[],
            overall_status=True,
            summary="Test",
            recommendations=[],
            metadata={},
        )

        with pytest.raises(AttributeError):
            report.validation_id = "new-id"

        with pytest.raises(AttributeError):
            report.overall_status = False
