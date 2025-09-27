"""User ID Value Object"""

from dataclasses import dataclass
from typing import Optional
import uuid


@dataclass(frozen=True)
class UserId:
    """User ID value object with validation"""
    
    value: str
    
    def __post_init__(self):
        """Validate user ID format"""
        if not self.value:
            raise ValueError("User ID cannot be empty")
        
        # Validate UUID format
        try:
            uuid.UUID(self.value)
        except ValueError:
            raise ValueError(f"Invalid user ID format: {self.value}")
    
    @classmethod
    def generate(cls) -> "UserId":
        """Generate a new user ID"""
        return cls(str(uuid.uuid4()))
    
    @classmethod
    def from_string(cls, user_id: str) -> "UserId":
        """Create UserId from string"""
        return cls(user_id)
    
    def __str__(self) -> str:
        """String representation"""
        return self.value
    
    def __eq__(self, other) -> bool:
        """Equality comparison"""
        if isinstance(other, UserId):
            return self.value == other.value
        return False
    
    def __hash__(self) -> int:
        """Hash for use in sets and dicts"""
        return hash(self.value)