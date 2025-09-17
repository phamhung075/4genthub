"""Email Value Object"""

from dataclasses import dataclass
import re
from typing import Optional


@dataclass(frozen=True)
class Email:
    """Email value object with validation"""
    
    value: str
    
    # Email regex pattern (simplified but effective)
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    def __post_init__(self):
        """Validate email format"""
        if not self.value:
            raise ValueError("Email cannot be empty")
        
        # Normalize email (lowercase)
        object.__setattr__(self, 'value', self.value.lower().strip())
        
        # Validate format
        if not self.EMAIL_PATTERN.match(self.value):
            raise ValueError(f"Invalid email format: {self.value}")
        
        # Check for consecutive dots (invalid in email addresses)
        if '..' in self.value:
            raise ValueError(f"Invalid email format: {self.value}")
        
        # Check that domain doesn't start with a dot
        if '@.' in self.value:
            raise ValueError(f"Invalid email format: {self.value}")
        
        # Additional validation
        if len(self.value) > 254:  # Max email length per RFC
            raise ValueError("Email address too long")
    
    @classmethod
    def from_string(cls, email: str) -> "Email":
        """Create Email from string"""
        return cls(email)
    
    def get_domain(self) -> str:
        """Get the domain part of the email"""
        return self.value.split('@')[1]
    
    def get_local_part(self) -> str:
        """Get the local part of the email (before @)"""
        return self.value.split('@')[0]
    
    def __str__(self) -> str:
        """String representation"""
        return self.value
    
    def __eq__(self, other) -> bool:
        """Equality comparison"""
        if isinstance(other, Email):
            return self.value == other.value
        return False
    
    def __hash__(self) -> int:
        """Hash for use in sets and dicts"""
        return hash(self.value)