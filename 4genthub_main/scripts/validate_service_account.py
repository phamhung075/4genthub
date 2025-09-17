#!/usr/bin/env python3
"""
Service Account Validation Script

This script validates the Keycloak service account configuration and tests authentication.
Use this to verify your service account setup is working correctly.

Usage:
    python scripts/validate_service_account.py
    
Environment variables required:
    - KEYCLOAK_URL
    - KEYCLOAK_REALM  
    - KEYCLOAK_SERVICE_CLIENT_ID
    - KEYCLOAK_SERVICE_CLIENT_SECRET
"""

import os
import sys
import asyncio
import json
from datetime import datetime
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastmcp.auth.service_account import ServiceAccountAuth, ServiceAccountConfig


class Colors:
    """Console colors for output formatting"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(title: str):
    """Print formatted section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")


def print_success(message: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")


def print_error(message: str):
    """Print error message"""
    print(f"{Colors.RED}❌ {message}{Colors.END}")


def print_warning(message: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")


def print_info(message: str):
    """Print info message"""
    print(f"{Colors.CYAN}ℹ️  {message}{Colors.END}")


def check_environment():
    """Check required environment variables"""
    print_header("Environment Configuration Check")
    
    required_vars = [
        "KEYCLOAK_URL",
        "KEYCLOAK_REALM", 
        "KEYCLOAK_SERVICE_CLIENT_ID",
        "KEYCLOAK_SERVICE_CLIENT_SECRET"
    ]
    
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if "SECRET" in var:
                display_value = "*" * 20 + value[-4:] if len(value) > 4 else "*" * len(value)
            else:
                display_value = value
            print_success(f"{var}: {display_value}")
        else:
            print_error(f"{var}: Not set")
            missing_vars.append(var)
    
    if missing_vars:
        print_error(f"Missing required environment variables: {', '.join(missing_vars)}")
        print_info("Please set these variables in your .env file or environment")
        return False
    
    print_success("All required environment variables are set")
    return True


async def test_service_account_auth():
    """Test service account authentication"""
    print_header("Service Account Authentication Test")
    
    try:
        # Initialize service account
        print_info("Initializing service account...")
        auth = ServiceAccountAuth()
        
        # Test authentication
        print_info("Attempting authentication...")
        token = await auth.authenticate()
        
        if token:
            print_success(f"Authentication successful!")
            print_info(f"Access token received (length: {len(token.access_token)})")
            print_info(f"Token expires in: {token.seconds_until_expiry} seconds")
            print_info(f"Token type: {token.token_type}")
            print_info(f"Scopes: {token.scope}")
            
            # Test token validation
            print_info("Validating token...")
            payload = await auth.validate_token(token.access_token)
            
            if payload:
                print_success("Token validation successful!")
                print_info(f"Subject: {payload.get('sub')}")
                print_info(f"Authorized party: {payload.get('azp')}")
                print_info(f"Expires at: {datetime.fromtimestamp(payload.get('exp', 0))}")
            else:
                print_warning("Token validation failed")
            
            # Test getting service info
            print_info("Getting service account info...")
            service_info = await auth.get_service_info()
            
            if service_info:
                print_success("Service info retrieved!")
                print_info(f"Username: {service_info.get('preferred_username')}")
                print_info(f"Client ID: {service_info.get('client_id', 'N/A')}")
            else:
                print_warning("Could not retrieve service info")
                
        else:
            print_error("Authentication failed - no token received")
            return False
            
        await auth.close()
        return True
        
    except Exception as e:
        print_error(f"Authentication test failed: {e}")
        return False


async def test_health_check():
    """Test service account health check"""
    print_header("Service Account Health Check")
    
    try:
        auth = ServiceAccountAuth()
        health = await auth.health_check()
        
        print_info("Health check results:")
        print(json.dumps(health, indent=2, default=str))
        
        # Evaluate health status
        if health.get("service_account_configured") and health.get("keycloak_reachable"):
            print_success("Service account health check passed!")
            
            if health.get("token_valid"):
                print_success("Active token is valid")
            else:
                print_warning("No active token or token invalid")
                
        else:
            print_error("Service account health check failed!")
            
            if not health.get("service_account_configured"):
                print_error("Service account is not properly configured")
                
            if not health.get("keycloak_reachable"):
                print_error("Keycloak is not reachable")
        
        await auth.close()
        return True
        
    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False


def print_configuration_help():
    """Print configuration help and next steps"""
    print_header("Configuration Help")
    
    print_info("To configure the service account:")
    print("""
1. Set environment variables in your .env file:
   KEYCLOAK_URL=https://your-keycloak-instance.com
   KEYCLOAK_REALM=4genthub
   KEYCLOAK_SERVICE_CLIENT_ID=mcp-service-account
   KEYCLOAK_SERVICE_CLIENT_SECRET=your-client-secret

2. Configure in Keycloak Admin Console:
   - Create client with ID 'mcp-service-account'
   - Enable 'Client authentication' and 'Service accounts roles'
   - Disable standard and implicit flows
   - Generate client secret
   - Assign required roles to service account

3. Reference documentation:
   ai_docs/authentication/keycloak-service-account-setup.md
   4genthub_main/config/keycloak_service_account.sample
""")


async def main():
    """Main validation routine"""
    print(f"{Colors.BOLD}{Colors.CYAN}")
    print("🔐 Keycloak Service Account Validation")
    print("=====================================")
    print(f"{Colors.END}")
    
    # Check environment configuration
    env_ok = check_environment()
    
    if not env_ok:
        print_configuration_help()
        return 1
    
    # Test authentication
    auth_ok = await test_service_account_auth()
    
    # Test health check  
    health_ok = await test_health_check()
    
    # Summary
    print_header("Validation Summary")
    
    if env_ok and auth_ok and health_ok:
        print_success("🎉 All tests passed! Service account is properly configured.")
        print_info("You can now use the service account for MCP hooks authentication.")
        return 0
    else:
        print_error("❌ Some tests failed. Please review the output above.")
        
        if not env_ok:
            print_error("- Environment configuration issues")
        if not auth_ok:
            print_error("- Authentication test failed")
        if not health_ok:
            print_error("- Health check failed")
            
        print_configuration_help()
        return 1


if __name__ == "__main__":
    # Load environment from .env file if it exists
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print_info("Loaded environment from .env file")
    except ImportError:
        print_info("python-dotenv not installed, using system environment")
    
    # Run validation
    exit_code = asyncio.run(main())
    sys.exit(exit_code)