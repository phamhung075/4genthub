#!/usr/bin/env python3
"""
Test Keycloak Authentication Flow

This script tests the complete authentication flow:
1. Login with Keycloak
2. Get access token
3. Use token for MCP requests
4. Validate token
"""

import os
import sys
import asyncio
import httpx
from typing import Optional, Dict, Any
import json
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "agenthub_main" / "src"))

# Import Keycloak services
from fastmcp.auth.keycloak_service import KeycloakAuthService
from fastmcp.auth.mcp_keycloak_validator import MCPKeycloakValidator, validate_mcp_request

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

class KeycloakAuthTester:
    """Test Keycloak authentication flow."""
    
    def __init__(self):
        self.keycloak_service = KeycloakAuthService()
        self.mcp_validator = MCPKeycloakValidator()
        self.base_url = os.getenv("MCP_HOST", "http://localhost:8001")
        
    async def test_login(self, username: str, password: str) -> Optional[str]:
        """Test user login with Keycloak."""
        print("\n" + "=" * 60)
        print("TESTING KEYCLOAK LOGIN")
        print("=" * 60)
        
        result = await self.keycloak_service.login(username, password)
        
        if result.success:
            print(f"✅ Login successful!")
            print(f"   User: {result.user.get('email', 'Unknown')}")
            print(f"   Roles: {result.roles}")
            print(f"   Token expires in: {result.expires_in} seconds")
            return result.access_token
        else:
            print(f"❌ Login failed: {result.error}")
            return None
    
    async def test_token_validation(self, token: str) -> bool:
        """Test token validation."""
        print("\n" + "=" * 60)
        print("TESTING TOKEN VALIDATION")
        print("=" * 60)
        
        # Test MCP validator
        claims = await self.mcp_validator.validate_mcp_token(token)
        
        if claims:
            print(f"✅ Token is valid!")
            user_info = self.mcp_validator.extract_user_info(claims)
            print(f"   User ID: {user_info['user_id']}")
            print(f"   Username: {user_info['username']}")
            print(f"   Email: {user_info['email']}")
            print(f"   Roles: {user_info['roles']}")
            print(f"   MCP Permissions: {user_info['mcp_permissions']}")
            return True
        else:
            print(f"❌ Token validation failed")
            return False
    
    async def test_mcp_request(self, token: str) -> bool:
        """Test MCP request with token."""
        print("\n" + "=" * 60)
        print("TESTING MCP REQUEST WITH TOKEN")
        print("=" * 60)
        
        try:
            async with httpx.AsyncClient() as client:
                # Test health endpoint
                response = await client.get(
                    f"{self.base_url}/health",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if response.status_code == 200:
                    print(f"✅ Health check successful!")
                    print(f"   Response: {response.json()}")
                else:
                    print(f"❌ Health check failed: {response.status_code}")
                    return False
                
                # Test MCP tool endpoint
                response = await client.post(
                    f"{self.base_url}/mcp/manage_task",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "action": "list",
                        "include_context": False
                    }
                )
                
                if response.status_code == 200:
                    print(f"✅ MCP tool request successful!")
                    tasks = response.json()
                    print(f"   Found {len(tasks.get('tasks', []))} tasks")
                    return True
                else:
                    print(f"❌ MCP tool request failed: {response.status_code}")
                    if response.status_code == 401:
                        print("   Authentication required - token may be invalid")
                    elif response.status_code == 403:
                        print("   Forbidden - insufficient permissions")
                    return False
                    
        except Exception as e:
            print(f"❌ Request error: {e}")
            return False
    
    async def test_token_refresh(self, refresh_token: str) -> Optional[str]:
        """Test token refresh."""
        print("\n" + "=" * 60)
        print("TESTING TOKEN REFRESH")
        print("=" * 60)
        
        result = await self.keycloak_service.refresh_token(refresh_token)
        
        if result.success:
            print(f"✅ Token refresh successful!")
            print(f"   New token expires in: {result.expires_in} seconds")
            return result.access_token
        else:
            print(f"❌ Token refresh failed: {result.error}")
            return None
    
    async def test_introspection(self, token: str) -> bool:
        """Test token introspection."""
        print("\n" + "=" * 60)
        print("TESTING TOKEN INTROSPECTION")
        print("=" * 60)
        
        result = await self.mcp_validator.introspect_token(token)
        
        if result:
            print(f"✅ Token introspection successful!")
            print(f"   Active: {result.get('active')}")
            print(f"   Username: {result.get('username')}")
            print(f"   Client ID: {result.get('client_id')}")
            print(f"   Scope: {result.get('scope')}")
            return True
        else:
            print(f"❌ Token introspection failed")
            return False
    
    async def run_all_tests(self, username: str, password: str):
        """Run all authentication tests."""
        print("\n" + "=" * 60)
        print("KEYCLOAK AUTHENTICATION TEST SUITE")
        print("=" * 60)
        print(f"Keycloak URL: {os.getenv('KEYCLOAK_URL')}")
        print(f"Realm: {os.getenv('KEYCLOAK_REALM')}")
        print(f"Client ID: {os.getenv('KEYCLOAK_CLIENT_ID')}")
        
        # Test login
        token = await self.test_login(username, password)
        if not token:
            print("\n❌ Cannot proceed without valid token")
            return
        
        # Test token validation
        valid = await self.test_token_validation(token)
        if not valid:
            print("\n⚠️  Token validation failed but continuing tests...")
        
        # Test MCP request
        await self.test_mcp_request(token)
        
        # Test introspection
        await self.test_introspection(token)
        
        print("\n" + "=" * 60)
        print("TEST SUITE COMPLETE")
        print("=" * 60)


async def main():
    """Main test function."""
    # Check if Keycloak is configured
    if not os.getenv("KEYCLOAK_URL") or os.getenv("KEYCLOAK_URL") == "https://your-keycloak.cloud.provider.com":
        print("❌ ERROR: Keycloak is not configured!")
        print("Please update your .env file with:")
        print("  KEYCLOAK_URL=<your-keycloak-url>")
        print("  KEYCLOAK_CLIENT_SECRET=<your-client-secret>")
        sys.exit(1)
    
    # Get test credentials
    print("\n" + "=" * 60)
    print("KEYCLOAK AUTHENTICATION TEST")
    print("=" * 60)
    
    # You can hardcode test credentials here for testing
    # Or get them from environment variables
    username = os.getenv("TEST_USERNAME", "")
    password = os.getenv("TEST_PASSWORD", "")
    
    if not username:
        username = input("Enter username/email: ")
    if not password:
        import getpass
        password = getpass.getpass("Enter password: ")
    
    # Run tests
    tester = KeycloakAuthTester()
    await tester.run_all_tests(username, password)


if __name__ == "__main__":
    asyncio.run(main())