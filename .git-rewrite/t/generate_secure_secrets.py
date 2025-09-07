#!/usr/bin/env python3
"""
Generate secure random secrets for JWT and application security.
This script generates cryptographically secure random strings.
"""

import secrets
import base64
import string

def generate_secure_secret(length=64):
    """Generate a secure random secret."""
    # Generate random bytes and encode as base64 for a strong secret
    random_bytes = secrets.token_bytes(length)
    return base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')

def generate_alphanumeric_secret(length=32):
    """Generate a secure alphanumeric secret."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

if __name__ == "__main__":
    print("=" * 60)
    print("SECURE SECRETS GENERATOR")
    print("=" * 60)
    print("\nGenerated secure secrets for your .env file:")
    print("(Copy these to your .env file and NEVER commit them to git)")
    print("\n" + "-" * 60)
    
    # Generate JWT secret (should be long and complex)
    jwt_secret = generate_secure_secret(64)
    print(f"\n# JWT Secret Key (for token signing)")
    print(f"JWT_SECRET_KEY={jwt_secret}")
    
    # Generate app secret key
    app_secret = generate_alphanumeric_secret(64)
    print(f"\n# Application Secret Key")
    print(f"SECRET_KEY={app_secret}")
    
    print("\n" + "-" * 60)
    print("\nIMPORTANT SECURITY NOTES:")
    print("1. Copy these values to your .env file")
    print("2. NEVER commit .env to version control") 
    print("3. Use different secrets for production")
    print("4. Rotate secrets periodically")
    print("5. Store production secrets in a secure vault")
    print("\n" + "=" * 60)