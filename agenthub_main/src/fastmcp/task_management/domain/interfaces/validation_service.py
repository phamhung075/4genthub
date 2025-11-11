"""Validation Service Interface - Domain Layer"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class ValidationSeverity(Enum):
    """Validation error severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class IValidationResult(ABC):
    """Domain interface for validation results"""

    @property
    @abstractmethod
    def is_valid(self) -> bool:
        """Check if validation passed"""
        pass

    @property
    @abstractmethod
    def errors(self) -> list[str]:
        """Get validation errors"""
        pass

    @property
    @abstractmethod
    def warnings(self) -> list[str]:
        """Get validation warnings"""
        pass

    @property
    @abstractmethod
    def details(self) -> dict[str, Any]:
        """Get detailed validation information"""
        pass


class IValidator(ABC):
    """Domain interface for validators"""

    @abstractmethod
    def validate(self, data: Any) -> IValidationResult:
        """Validate data"""
        pass

    @property
    @abstractmethod
    def validation_rules(self) -> list[str]:
        """Get the validation rules"""
        pass


class IDocumentValidator(ABC):
    """Domain interface for document validation"""

    @abstractmethod
    def validate_document(self, document: dict[str, Any]) -> IValidationResult:
        """Validate a document"""
        pass

    @abstractmethod
    def validate_schema(
        self, document: dict[str, Any], schema: dict[str, Any]
    ) -> IValidationResult:
        """Validate document against schema"""
        pass

    @abstractmethod
    def get_schema(self, document_type: str) -> dict[str, Any] | None:
        """Get schema for document type"""
        pass


class IValidationService(ABC):
    """Domain interface for validation operations"""

    @abstractmethod
    def register_validator(self, data_type: str, validator: IValidator) -> None:
        """Register a validator for a data type"""
        pass

    @abstractmethod
    def unregister_validator(self, data_type: str) -> bool:
        """Unregister a validator"""
        pass

    @abstractmethod
    def validate(self, data_type: str, data: Any) -> IValidationResult:
        """Validate data using registered validator"""
        pass

    @abstractmethod
    def validate_all(self, data: dict[str, Any]) -> dict[str, IValidationResult]:
        """Validate multiple data items"""
        pass

    @abstractmethod
    def get_validator(self, data_type: str) -> IValidator | None:
        """Get validator for data type"""
        pass

    @abstractmethod
    def list_validators(self) -> list[str]:
        """List all registered validators"""
        pass
