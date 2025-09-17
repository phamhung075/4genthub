#!/usr/bin/env python3
"""
Secure Token Generator for 4genthub
Generates cryptographically secure tokens to replace exposed ones.
"""
import secrets
import string
import base64
import os
from datetime import datetime

def generate_api_token(length=32):
    """Generate a secure API token using alphanumeric characters"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_jwt_secret(length=64):
    """Generate a secure JWT secret (base64 encoded)"""
    secret_bytes = secrets.token_bytes(length)
    return base64.b64encode(secret_bytes).decode('utf-8')

def generate_mcp_token(length=32):
    """Generate a secure MCP token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def main():
    print("🔐 4genthub Secure Token Generator")
    print("=" * 50)
    print(f"Generated on: {datetime.now().isoformat()}")
    print()
    
    # Generate new tokens
    new_4genthub_token = generate_mcp_token()
    new_api_token = generate_api_token()
    new_jwt_secret = generate_jwt_secret()
    
    print("🔑 GENERATED SECURE TOKENS:")
    print("-" * 30)
    print(f"4GENTHUB_TOKEN={new_4genthub_token}")
    print(f"4GENTHUB_API_TOKEN={new_api_token}")  
    print(f"JWT_SECRET_KEY={new_jwt_secret}")
    print()
    
    print("📝 INSTRUCTIONS:")
    print("-" * 15)
    print("1. Add these tokens to your .env file")
    print("2. Update your MCP configuration files to use environment variables")
    print("3. Never commit these tokens to version control")
    print("4. Regenerate tokens periodically for security")
    print()
    
    print("⚠️  SECURITY NOTES:")
    print("-" * 18)
    print("- The exposed tokens should be considered compromised")
    print("- Regenerate these tokens in production environments")
    print("- Use environment variables, never hardcode tokens")
    print("- Store tokens securely (password managers, vaults)")
    
    # Save to a secure file (not committed)
    env_file = ".env.tokens.new"
    with open(env_file, 'w') as f:
        f.write("# Generated secure tokens - DO NOT COMMIT\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n\n")
        f.write(f"4GENTHUB_TOKEN={new_4genthub_token}\n")
        f.write(f"4GENTHUB_API_TOKEN={new_api_token}\n")
        f.write(f"JWT_SECRET_KEY={new_jwt_secret}\n")
    
    print(f"\n💾 Tokens saved to: {env_file}")
    print("   (This file is excluded from git)")

if __name__ == "__main__":
    main()