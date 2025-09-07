#!/usr/bin/env python3
"""
Test script for Keycloak authentication flow with MCP server

This script tests:
1. Keycloak login
2. MCP token generation
3. Token validation
4. API access with tokens
"""

import os
import sys
import asyncio
import httpx
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dhafnck_mcp_main/src'))

# Load environment variables
load_dotenv()

# Configuration from environment
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "https://your-keycloak.com")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "dhafnck-mcp")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "mcp-backend")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET")
MCP_SERVER_URL = os.getenv("BACKEND_URL", "http://localhost:8001")

# Test colors for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

def print_colored(message: str, color: str = NC):
    """Print colored output"""
    print(f"{color}{message}{NC}")

def print_section(title: str):
    """Print section header"""
    print_colored(f"\n{'='*60}", BLUE)
    print_colored(f"{title}", BLUE)
    print_colored(f"{'='*60}", BLUE)

def print_success(message: str):
    """Print success message"""
    print_colored(f"✓ {message}", GREEN)

def print_error(message: str):
    """Print error message"""
    print_colored(f"✗ {message}", RED)

def print_warning(message: str):
    """Print warning message"""
    print_colored(f"⚠ {message}", YELLOW)

async def test_keycloak_connection():
    """Test connection to Keycloak"""
    print_section("Testing Keycloak Connection")
    
    try:
        async with httpx.AsyncClient() as client:
            # Test OpenID configuration endpoint
            url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/.well-known/openid-configuration"
            print(f"Testing: {url}")
            
            response = await client.get(url)
            
            if response.status_code == 200:
                config = response.json()
                print_success("Connected to Keycloak successfully")
                print(f"  Issuer: {config.get('issuer')}")
                print(f"  Token endpoint: {config.get('token_endpoint')}")
                return True
            else:
                print_error(f"Failed to connect to Keycloak (HTTP {response.status_code})")
                return False
                
    except Exception as e:
        print_error(f"Connection error: {e}")
        return False

async def test_keycloak_login(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Test Keycloak login"""
    print_section("Testing Keycloak Login")
    
    try:
        async with httpx.AsyncClient() as client:
            token_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
            
            data = {
                "grant_type": "password",
                "client_id": KEYCLOAK_CLIENT_ID,
                "username": username,
                "password": password,
                "scope": "openid email profile"
            }
            
            if KEYCLOAK_CLIENT_SECRET:
                data["client_secret"] = KEYCLOAK_CLIENT_SECRET
            
            print(f"Attempting login for user: {username}")
            response = await client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                tokens = response.json()
                print_success("Login successful")
                print(f"  Access token: {tokens['access_token'][:50]}...")
                print(f"  Token type: {tokens.get('token_type')}")
                print(f"  Expires in: {tokens.get('expires_in')} seconds")
                return tokens
            else:
                error_data = response.json()
                print_error(f"Login failed: {error_data.get('error_description', 'Unknown error')}")
                return None
                
    except Exception as e:
        print_error(f"Login error: {e}")
        return None

async def test_mcp_server_health():
    """Test MCP server health"""
    print_section("Testing MCP Server Health")
    
    try:
        async with httpx.AsyncClient() as client:
            url = f"{MCP_SERVER_URL}/health"
            print(f"Testing: {url}")
            
            response = await client.get(url)
            
            if response.status_code == 200:
                health = response.json()
                print_success("MCP Server is healthy")
                print(f"  Status: {health.get('status')}")
                print(f"  Database: {health.get('database', {}).get('status')}")
                return True
            else:
                print_error(f"MCP Server health check failed (HTTP {response.status_code})")
                return False
                
    except Exception as e:
        print_error(f"Cannot connect to MCP Server: {e}")
        return False

async def test_mcp_login(keycloak_tokens: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Test MCP login with Keycloak token"""
    print_section("Testing MCP Token Exchange")
    
    try:
        async with httpx.AsyncClient() as client:
            url = f"{MCP_SERVER_URL}/auth/exchange"
            
            # Exchange Keycloak token for MCP token
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {keycloak_tokens['access_token']}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                mcp_data = response.json()
                print_success("MCP token exchange successful")
                print(f"  MCP Token: {mcp_data['mcp_token'][:50]}...")
                print(f"  User ID: {mcp_data.get('user_id')}")
                print(f"  Email: {mcp_data.get('email')}")
                print(f"  Roles: {mcp_data.get('roles')}")
                return mcp_data
            else:
                print_error(f"MCP token exchange failed (HTTP {response.status_code})")
                if response.text:
                    print(f"  Response: {response.text}")
                return None
                
    except Exception as e:
        print_error(f"MCP exchange error: {e}")
        return None

async def test_api_access(mcp_token: str):
    """Test API access with MCP token"""
    print_section("Testing API Access with MCP Token")
    
    try:
        async with httpx.AsyncClient() as client:
            # Test projects endpoint
            url = f"{MCP_SERVER_URL}/api/v1/projects"
            print(f"Testing protected endpoint: {url}")
            
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {mcp_token}"}
            )
            
            if response.status_code == 200:
                print_success("API access successful")
                data = response.json()
                print(f"  Projects count: {len(data.get('projects', []))}")
                return True
            elif response.status_code == 401:
                print_error("Authentication failed - token invalid")
                return False
            elif response.status_code == 403:
                print_error("Authorization failed - insufficient permissions")
                return False
            else:
                print_error(f"API access failed (HTTP {response.status_code})")
                return False
                
    except Exception as e:
        print_error(f"API access error: {e}")
        return False

async def test_token_refresh(refresh_token: str) -> Optional[Dict[str, Any]]:
    """Test token refresh"""
    print_section("Testing Token Refresh")
    
    try:
        async with httpx.AsyncClient() as client:
            token_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
            
            data = {
                "grant_type": "refresh_token",
                "client_id": KEYCLOAK_CLIENT_ID,
                "refresh_token": refresh_token
            }
            
            if KEYCLOAK_CLIENT_SECRET:
                data["client_secret"] = KEYCLOAK_CLIENT_SECRET
            
            response = await client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                tokens = response.json()
                print_success("Token refresh successful")
                print(f"  New access token: {tokens['access_token'][:50]}...")
                return tokens
            else:
                print_error(f"Token refresh failed (HTTP {response.status_code})")
                return None
                
    except Exception as e:
        print_error(f"Token refresh error: {e}")
        return None

async def test_logout(refresh_token: str):
    """Test logout"""
    print_section("Testing Logout")
    
    try:
        async with httpx.AsyncClient() as client:
            logout_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/logout"
            
            data = {
                "client_id": KEYCLOAK_CLIENT_ID,
                "refresh_token": refresh_token
            }
            
            if KEYCLOAK_CLIENT_SECRET:
                data["client_secret"] = KEYCLOAK_CLIENT_SECRET
            
            response = await client.post(
                logout_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code in [204, 200]:
                print_success("Logout successful")
                return True
            else:
                print_error(f"Logout failed (HTTP {response.status_code})")
                return False
                
    except Exception as e:
        print_error(f"Logout error: {e}")
        return False

async def run_all_tests():
    """Run all authentication tests"""
    print_colored("\n" + "="*60, BLUE)
    print_colored("DhafnckMCP Authentication Test Suite", BLUE)
    print_colored("PostgreSQL Docker + Keycloak Cloud", BLUE)
    print_colored("="*60, BLUE)
    
    # Check configuration
    print_section("Configuration Check")
    print(f"Keycloak URL: {KEYCLOAK_URL}")
    print(f"Keycloak Realm: {KEYCLOAK_REALM}")
    print(f"Keycloak Client: {KEYCLOAK_CLIENT_ID}")
    print(f"MCP Server URL: {MCP_SERVER_URL}")
    
    if not KEYCLOAK_CLIENT_SECRET:
        print_warning("KEYCLOAK_CLIENT_SECRET not set - using public client mode")
    
    # Test results tracking
    results = {
        "keycloak_connection": False,
        "mcp_health": False,
        "keycloak_login": False,
        "mcp_exchange": False,
        "api_access": False,
        "token_refresh": False,
        "logout": False
    }
    
    # Test 1: Keycloak connection
    results["keycloak_connection"] = await test_keycloak_connection()
    if not results["keycloak_connection"]:
        print_error("\nCannot proceed without Keycloak connection")
        return results
    
    # Test 2: MCP server health
    results["mcp_health"] = await test_mcp_server_health()
    if not results["mcp_health"]:
        print_warning("\nMCP Server not available - some tests will fail")
    
    # Get test credentials
    print_section("Enter Test Credentials")
    username = input("Username/Email: ")
    password = input("Password: ")
    
    if not username or not password:
        print_error("Credentials required for testing")
        return results
    
    # Test 3: Keycloak login
    keycloak_tokens = await test_keycloak_login(username, password)
    results["keycloak_login"] = keycloak_tokens is not None
    
    if not keycloak_tokens:
        print_error("\nCannot proceed without successful login")
        return results
    
    # Test 4: MCP token exchange
    if results["mcp_health"]:
        mcp_data = await test_mcp_login(keycloak_tokens)
        results["mcp_exchange"] = mcp_data is not None
        
        # Test 5: API access
        if mcp_data:
            results["api_access"] = await test_api_access(mcp_data["mcp_token"])
    
    # Test 6: Token refresh
    if keycloak_tokens.get("refresh_token"):
        new_tokens = await test_token_refresh(keycloak_tokens["refresh_token"])
        results["token_refresh"] = new_tokens is not None
    
    # Test 7: Logout
    if keycloak_tokens.get("refresh_token"):
        results["logout"] = await test_logout(keycloak_tokens["refresh_token"])
    
    # Print summary
    print_section("Test Summary")
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        color = GREEN if passed else RED
        print_colored(f"{test_name.replace('_', ' ').title()}: {status}", color)
    
    print_colored(f"\n{passed_tests}/{total_tests} tests passed", 
                  GREEN if passed_tests == total_tests else YELLOW)
    
    if passed_tests == total_tests:
        print_colored("\n✨ All tests passed! Your authentication system is working correctly.", GREEN)
    else:
        print_colored("\n⚠ Some tests failed. Please check your configuration.", YELLOW)
    
    return results

async def main():
    """Main entry point"""
    try:
        results = await run_all_tests()
        
        # Exit with appropriate code
        if all(results.values()):
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print_colored("\n\nTest interrupted by user", YELLOW)
        sys.exit(1)
    except Exception as e:
        print_colored(f"\n\nUnexpected error: {e}", RED)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())