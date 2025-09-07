"""Validation Service Interface - Domain Layer"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from enum import Enum


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
    def errors(self) -> List[str]:
        """Get validation errors"""
        pass
    
    @property
    @abstractmethod
    def warnings(self) -> List[str]:
        """Get validation warnings"""
        pass
    
    @property
    @abstractmethod
    def details(self) -> Dict[str, Any]:
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
    def validation_rules(self) -> List[str]:
        """Get the validation rules"""
        pass


class IDocumentValidator(ABC):
    """Domain interface for document validation"""
    
    @abstractmethod
    def validate_document(self, document: Dict[str, Any]) -> IValidationResult:
        """Validate a document"""
        pass
    
    @abstractmethod
    def validate_schema(self, document: Dict[str, Any], schema: Dict[str, Any]) -> IValidationResult:
        """Validate document against schema"""
        pass
    
    @abstractmethod
    def get_schema(self, document_type: str) -> Optional[Dict[str, Any]]:
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
    def validate_all(self, data: Dict[str, Any]) -> Dict[str, IValidationResult]:
        """Validate multiple data items"""
        pass
    
    @abstractmethod
    def get_validator(self, data_type: str) -> Optional[IValidator]:
        """Get validator for data type"""
        pass
    
    @abstractmethod
    def list_validators(self) -> List[str]:
        """List all registered validators"""
        pass