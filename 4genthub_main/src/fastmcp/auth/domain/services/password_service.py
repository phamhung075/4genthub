"""
Password Service for secure password handling

This service provides password hashing and verification using bcrypt.
"""

import logging
import secrets
import string
from typing import Optional
import bcrypt

logger = logging.getLogger(__name__)


class PasswordService:
    """Service for password hashing and verification"""
    
    # Bcrypt configuration
    DEFAULT_ROUNDS = 12  # Good balance between security and performance
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 128
    
    @classmethod
    def hash_password(cls, password: str) -> str:
        """
        Hash a password using bcrypt
        
        Args:
            password: Plain text password to hash
            
        Returns:
            Hashed password string
            
        Raises:
            ValueError: If password is invalid
        """
        cls._validate_password(password)
        
        # Generate salt and hash password
        salt = bcrypt.gensalt(rounds=cls.DEFAULT_ROUNDS)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        return hashed.decode('utf-8')
    
    @classmethod
    def verify_password(cls, password: str, hashed: str) -> bool:
        """
        Verify a password against a hash
        
        Args:
            password: Plain text password to verify
            hashed: Hashed password to compare against
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            # Ensure both are bytes
            password_bytes = password.encode('utf-8')
            hashed_bytes = hashed.encode('utf-8') if isinstance(hashed, str) else hashed
            
            # Use bcrypt's constant-time comparison
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except Exception as e:
            logger.warning(f"Password verification failed: {e}")
            return False
    
    @classmethod
    def _validate_password(cls, password: str) -> None:
        """
        Validate password meets requirements
        
        Args:
            password: Password to validate
            
        Raises:
            ValueError: If password doesn't meet requirements
        """
        if not password:
            raise ValueError("Password cannot be empty")
        
        if len(password) < cls.MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {cls.MIN_PASSWORD_LENGTH} characters long")
        
        if len(password) > cls.MAX_PASSWORD_LENGTH:
            raise ValueError(f"Password cannot exceed {cls.MAX_PASSWORD_LENGTH} characters")
    
    @classmethod
    def check_password_strength(cls, password: str) -> dict:
        """
        Check password strength and return analysis
        
        Args:
            password: Password to analyze
            
        Returns:
            Dictionary with strength analysis
        """
        analysis = {
            "length": len(password),
            "has_uppercase": any(c.isupper() for c in password),
            "has_lowercase": any(c.islower() for c in password),
            "has_digit": any(c.isdigit() for c in password),
            "has_special": any(c in string.punctuation for c in password),
            "strength": "weak",
            "score": 0,
            "suggestions": []
        }
        
        # Calculate score
        score = 0
        if analysis["length"] >= cls.MIN_PASSWORD_LENGTH:
            score += 1
        if analysis["length"] >= 12:
            score += 1
        if analysis["has_uppercase"]:
            score += 1
        if analysis["has_lowercase"]:
            score += 1
        if analysis["has_digit"]:
            score += 1
        if analysis["has_special"]:
            score += 1
        
        analysis["score"] = score
        
        # Determine strength
        if score <= 2:
            analysis["strength"] = "weak"
        elif score <= 4:
            analysis["strength"] = "medium"
        else:
            analysis["strength"] = "strong"
        
        # Add suggestions
        if not analysis["has_uppercase"]:
            analysis["suggestions"].append("Add uppercase letters")
        if not analysis["has_lowercase"]:
            analysis["suggestions"].append("Add lowercase letters")
        if not analysis["has_digit"]:
            analysis["suggestions"].append("Add numbers")
        if not analysis["has_special"]:
            analysis["suggestions"].append("Add special characters")
        if analysis["length"] < 12:
            analysis["suggestions"].append("Use at least 12 characters for better security")
        
        return analysis
    
    @classmethod
    def generate_secure_password(cls, length: int = 16, 
                                include_uppercase: bool = True,
                                include_lowercase: bool = True,
                                include_digits: bool = True,
                                include_special: bool = True) -> str:
        """
        Generate a secure random password
        
        Args:
            length: Password length (default 16)
            include_uppercase: Include uppercase letters
            include_lowercase: Include lowercase letters
            include_digits: Include digits
            include_special: Include special characters
            
        Returns:
            Secure random password
        """
        if length < cls.MIN_PASSWORD_LENGTH:
            length = cls.MIN_PASSWORD_LENGTH
        if length > cls.MAX_PASSWORD_LENGTH:
            length = cls.MAX_PASSWORD_LENGTH
        
        # Build character set
        chars = ""
        if include_lowercase:
            chars += string.ascii_lowercase
        if include_uppercase:
            chars += string.ascii_uppercase
        if include_digits:
            chars += string.digits
        if include_special:
            chars += string.punctuation
        
        if not chars:
            chars = string.ascii_letters + string.digits  # Fallback
        
        # Generate password
        password = ''.join(secrets.choice(chars) for _ in range(length))
        
        # Ensure it meets requirements if all options were selected
        if include_uppercase and include_lowercase and include_digits and include_special:
            # Ensure at least one of each type
            while True:
                analysis = cls.check_password_strength(password)
                if (analysis["has_uppercase"] and analysis["has_lowercase"] and 
                    analysis["has_digit"] and analysis["has_special"]):
                    break
                password = ''.join(secrets.choice(chars) for _ in range(length))
        
        return password
    
    @classmethod
    def generate_reset_token(cls, length: int = 32) -> str:
        """
        Generate a secure reset token
        
        Args:
            length: Token length (default 32)
            
        Returns:
            Secure random token
        """
        return secrets.token_urlsafe(length)
    
    @classmethod
    def needs_rehash(cls, hashed: str) -> bool:
        """
        Check if a password hash needs to be rehashed
        (e.g., if bcrypt rounds have been increased)
        
        Args:
            hashed: Hashed password to check
            
        Returns:
            True if rehashing is recommended
        """
        try:
            # Extract the cost factor from the hash
            if hashed.startswith('$2b$') or hashed.startswith('$2a$'):
                parts = hashed.split('$')
                if len(parts) >= 3:
                    rounds = int(parts[2])
                    return rounds < cls.DEFAULT_ROUNDS
        except Exception as e:
            logger.warning(f"Could not check if hash needs rehash: {e}")
        
        return False