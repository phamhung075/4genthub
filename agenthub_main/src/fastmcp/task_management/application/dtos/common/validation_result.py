"""Result of input validation"""

from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of input validation"""
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    
    def add_error(self, error: str):
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        self.warnings.append(warning) 