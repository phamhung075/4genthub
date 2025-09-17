#!/usr/bin/env python3
"""
Test Keycloak Authentication Integration with MCP

This script tests the complete authentication flow:
1. Authenticate with Keycloak
2. Get access token
3. Use token to access MCP API
4. Verify MCP operations work with Keycloak tokens
"""

import os
import sys
import asyncio
import httpx
import json
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Configuration from environment
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "https://your-keycloak.cloud.provider.com")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "agenthub")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "mcp-backend")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001")

class KeycloakMCPTester:
    """Test Keycloak authentication with MCP"""
    
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.user_info = None
        
    async def authenticate_with_keycloak(self, username: str, password: str) -> bool:
        """Authenticate with Keycloak and get tokens"""
        print(f"\n🔐 Authenticating with Keycloak...")
        print(f"   URL: {KEYCLOAK_URL}")
        print(f"   Realm: {KEYCLOAK_REALM}")
        print(f"   Client: {KEYCLOAK_CLIENT_ID}")
        
        token_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    token_url,
                    data={
                        "grant_type": "password",
                        "client_id": KEYCLOAK_CLIENT_ID,
                        "client_secret": KEYCLOAK_CLIENT_SECRET,
                        "username": username,
                        "password": password,
                        "scope": "openid email profile"
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code == 200:
                    tokens = response.json()
                    self.access_token = tokens.get("access_token")
                    self.refresh_token = tokens.get("refresh_token")
                    print("   ✅ Authentication successful!")
                    print(f"   Token expires in: {tokens.get('expires_in')} seconds")
                    return True
                else:
                    print(f"   ❌ Authentication failed: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return False
                    
            except Exception as e:
                print(f"   ❌ Error authenticating: {e}")
                return False
    
    async def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get user information from Keycloak"""
        if not self.access_token:
            print("❌ No access token available")
            return None
            
        print("\n👤 Getting user information...")
        userinfo_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/userinfo"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    userinfo_url,
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                
                if response.status_code == 200:
                    self.user_info = response.json()
                    print("   ✅ User info retrieved:")
                    print(f"   - Username: {self.user_info.get('preferred_username')}")
                    print(f"   - Email: {self.user_info.get('email')}")
                    print(f"   - Roles: {self.user_info.get('realm_access', {}).get('roles', [])}")
                    return self.user_info
                else:
                    print(f"   ❌ Failed to get user info: {response.status_code}")
                    return None
                    
            except Exception as e:
                print(f"   ❌ Error getting user info: {e}")
                return None
    
    async def test_mcp_health(self) -> bool:
        """Test MCP server health endpoint"""
        print("\n🏥 Testing MCP server health...")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{MCP_SERVER_URL}/health")
                
                if response.status_code == 200:
                    health = response.json()
                    print("   ✅ MCP server is healthy:")
                    print(f"   - Status: {health.get('status')}")
                    print(f"   - Version: {health.get('version')}")
                    print(f"   - MCP Tools: {health.get('mcp_tools')}")
                    print(f"   - Keycloak Auth: {health.get('keycloak_auth')}")
                    print(f"   - Auth Enabled: {health.get('auth_enabled')}")
                    return True
                else:
                    print(f"   ❌ MCP server unhealthy: {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"   ❌ Error checking MCP health: {e}")
                return False
    
    async def test_mcp_authenticated_request(self) -> bool:
        """Test authenticated MCP API request"""
        if not self.access_token:
            print("❌ No access token available")
            return False
            
        print("\n🔧 Testing authenticated MCP request...")
        
        async with httpx.AsyncClient() as client:
            try:
                # Test listing tasks
                response = await client.post(
                    f"{MCP_SERVER_URL}/mcp/manage_task",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    json={"action": "list", "limit": 5}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print("   ✅ MCP request successful!")
                    print(f"   Tasks found: {len(result.get('tasks', []))}")
                    return True
                elif response.status_code == 401:
                    print("   ❌ Authentication failed - token not valid for MCP")
                    print(f"   Response: {response.text}")
                    return False
                else:
                    print(f"   ❌ MCP request failed: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return False
                    
            except Exception as e:
                print(f"   ❌ Error calling MCP API: {e}")
                return False
    
    async def test_token_refresh(self) -> bool:
        """Test token refresh flow"""
        if not self.refresh_token:
            print("❌ No refresh token available")
            return False
            
        print("\n🔄 Testing token refresh...")
        token_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    token_url,
                    data={
                        "grant_type": "refresh_token",
                        "client_id": KEYCLOAK_CLIENT_ID,
                        "client_secret": KEYCLOAK_CLIENT_SECRET,
                        "refresh_token": self.refresh_token
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code == 200:
                    tokens = response.json()
                    self.access_token = tokens.get("access_token")
                    self.refresh_token = tokens.get("refresh_token")
                    print("   ✅ Token refresh successful!")
                    return True
                else:
                    print(f"   ❌ Token refresh failed: {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"   ❌ Error refreshing token: {e}")
                return False
    
    async def test_logout(self) -> bool:
        """Test logout flow"""
        if not self.refresh_token:
            print("❌ No refresh token available for logout")
            return False
            
        print("\n🚪 Testing logout...")
        logout_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/logout"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    logout_url,
                    data={
                        "client_id": KEYCLOAK_CLIENT_ID,
                        "client_secret": KEYCLOAK_CLIENT_SECRET,
                        "refresh_token": self.refresh_token
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code in [204, 200]:
                    print("   ✅ Logout successful!")
                    self.access_token = None
                    self.refresh_token = None
                    return True
                else:
                    print(f"   ❌ Logout failed: {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"   ❌ Error during logout: {e}")
                return False

async def main():
    """Run the complete test suite"""
    print("=" * 60)
    print("KEYCLOAK + MCP INTEGRATION TEST")
    print("=" * 60)
    
    # Check configuration
    if KEYCLOAK_URL == "https://your-keycloak.cloud.provider.com":
        print("\n⚠️  WARNING: KEYCLOAK_URL not configured!")
        print("Please update your .env file with actual Keycloak URL")
        return
    
    if not KEYCLOAK_CLIENT_SECRET:
        print("\n⚠️  WARNING: KEYCLOAK_CLIENT_SECRET not configured!")
        print("Please update your .env file with client secret")
        return
    
    # Get test credentials
    print("\nEnter test user credentials:")
    username = input("Username: ")
    password = input("Password: ")
    
    # Create tester
    tester = KeycloakMCPTester()
    
    # Run tests
    results = {}
    
    # Test MCP health (no auth required)
    results['mcp_health'] = await tester.test_mcp_health()
    
    # Test authentication
    results['authentication'] = await tester.authenticate_with_keycloak(username, password)
    
    if results['authentication']:
        # Test user info retrieval
        results['user_info'] = await tester.get_user_info() is not None
        
        # Test authenticated MCP request
        results['mcp_request'] = await tester.test_mcp_authenticated_request()
        
        # Test token refresh
        results['token_refresh'] = await tester.test_token_refresh()
        
        # Test another MCP request with refreshed token
        if results['token_refresh']:
            results['mcp_after_refresh'] = await tester.test_mcp_authenticated_request()
        
        # Test logout
        results['logout'] = await tester.test_logout()
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    
    print("\n" + "-" * 60)
    print(f"Total: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n🎉 All tests passed! Keycloak integration is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the configuration and logs.")

if __name__ == "__main__":
    asyncio.run(main())