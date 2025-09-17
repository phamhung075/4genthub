"""Template ID Value Object"""

import uuid
from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class TemplateId:
    """Template ID value object ensuring immutability and validation"""
    
    value: str
    
    def __post_init__(self):
        """Validate template ID"""
        if not self.value:
            raise ValueError("Template ID cannot be empty")
        if not isinstance(self.value, str):
            raise ValueError("Template ID must be a string")
        if len(self.value.strip()) == 0:
            raise ValueError("Template ID cannot be whitespace only")
    
    @classmethod
    def generate(cls) -> 'TemplateId':
        """Generate a new UUID-based template ID"""
        return cls(str(uuid.uuid4()))
    
    @classmethod
    def from_string(cls, value: str) -> 'TemplateId':
        """Create template ID from string"""
        return cls(value.strip())
    
    def __str__(self) -> str:
        """String representation"""
        return self.value
    
    def __repr__(self) -> str:
        """Representation for debugging"""
        return f"TemplateId('{self.value}')"
    
    def __eq__(self, other) -> bool:
        """Equality comparison"""
        if isinstance(other, TemplateId):
            return self.value == other.value
        elif isinstance(other, str):
            return self.value == other
        return False
    
    def __hash__(self) -> int:
        """Hash for use in sets and dictionaries"""
        return hash(self.value) 