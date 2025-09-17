#!/usr/bin/env python3
"""
Test script for Keycloak + MCP integration
Tests authentication flow and MCP tool access with Keycloak tokens
"""

import os
import sys
import json
import asyncio
import httpx
from typing import Dict, Any, Optional

# Configuration
MCP_URL = "http://localhost:8001"
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "https://your-keycloak.cloud.provider.com")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "4genthub")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "mcp-backend")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "")


class TestKeycloakMCPIntegration:
    """Test Keycloak + MCP integration"""
    
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.user_info = None
        
    async def test_keycloak_login(self, username: str, password: str) -> bool:
        """Test Keycloak authentication"""
        print("\n🔐 Testing Keycloak Authentication...")
        
        async with httpx.AsyncClient() as client:
            try:
                # Authenticate with Keycloak
                token_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
                
                data = {
                    "grant_type": "password",
                    "client_id": KEYCLOAK_CLIENT_ID,
                    "client_secret": KEYCLOAK_CLIENT_SECRET,
                    "username": username,
                    "password": password,
                    "scope": "openid email profile"
                }
                
                response = await client.post(token_url, data=data)
                
                if response.status_code == 200:
                    token_data = response.json()
                    self.access_token = token_data.get("access_token")
                    self.refresh_token = token_data.get("refresh_token")
                    print(f"✅ Keycloak authentication successful")
                    print(f"   Access token: {self.access_token[:50]}...")
                    return True
                else:
                    print(f"❌ Keycloak authentication failed: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return False
                    
            except Exception as e:
                print(f"❌ Error during Keycloak authentication: {e}")
                return False
    
    async def test_mcp_health(self) -> bool:
        """Test MCP server health"""
        print("\n🏥 Testing MCP Server Health...")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{MCP_URL}/health")
                
                if response.status_code == 200:
                    health_data = response.json()
                    print(f"✅ MCP server is healthy")
                    print(f"   Status: {health_data.get('status')}")
                    print(f"   Database: {health_data.get('database', {}).get('status')}")
                    return True
                else:
                    print(f"❌ MCP server health check failed: {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"❌ Error checking MCP health: {e}")
                return False
    
    async def test_mcp_auth_with_keycloak_token(self) -> bool:
        """Test MCP authentication with Keycloak token"""
        print("\n🔑 Testing MCP Authentication with Keycloak Token...")
        
        if not self.access_token:
            print("❌ No access token available. Please login first.")
            return False
        
        async with httpx.AsyncClient() as client:
            try:
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
                
                # Test getting user info from MCP
                response = await client.get(
                    f"{MCP_URL}/auth/me",
                    headers=headers
                )
                
                if response.status_code == 200:
                    self.user_info = response.json()
                    print(f"✅ MCP accepted Keycloak token")
                    print(f"   User ID: {self.user_info.get('user_id')}")
                    print(f"   Email: {self.user_info.get('email')}")
                    print(f"   Roles: {self.user_info.get('roles')}")
                    return True
                else:
                    print(f"❌ MCP authentication failed: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return False
                    
            except Exception as e:
                print(f"❌ Error during MCP authentication: {e}")
                return False
    
    async def test_mcp_tool_access(self) -> bool:
        """Test accessing MCP tools with Keycloak token"""
        print("\n🛠️  Testing MCP Tool Access...")
        
        if not self.access_token:
            print("❌ No access token available. Please login first.")
            return False
        
        async with httpx.AsyncClient() as client:
            try:
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
                
                # Test manage_project tool
                print("\n📂 Testing manage_project tool...")
                response = await client.post(
                    f"{MCP_URL}/mcp/manage_project",
                    headers=headers,
                    json={"action": "list"}
                )
                
                if response.status_code == 200:
                    projects = response.json()
                    print(f"✅ Successfully accessed manage_project tool")
                    print(f"   Projects found: {len(projects.get('projects', []))}")
                else:
                    print(f"❌ Failed to access manage_project: {response.status_code}")
                    return False
                
                # Test manage_task tool
                print("\n📋 Testing manage_task tool...")
                response = await client.post(
                    f"{MCP_URL}/mcp/manage_task",
                    headers=headers,
                    json={"action": "list", "limit": 5}
                )
                
                if response.status_code == 200:
                    tasks = response.json()
                    print(f"✅ Successfully accessed manage_task tool")
                    print(f"   Tasks found: {len(tasks.get('tasks', []))}")
                else:
                    print(f"❌ Failed to access manage_task: {response.status_code}")
                    return False
                
                # Test manage_context tool
                print("\n📝 Testing manage_context tool...")
                response = await client.post(
                    f"{MCP_URL}/mcp/manage_context",
                    headers=headers,
                    json={
                        "action": "get",
                        "level": "global",
                        "context_id": "global"
                    }
                )
                
                if response.status_code == 200:
                    context = response.json()
                    print(f"✅ Successfully accessed manage_context tool")
                    print(f"   Context level: {context.get('level')}")
                else:
                    print(f"❌ Failed to access manage_context: {response.status_code}")
                    return False
                
                return True
                    
            except Exception as e:
                print(f"❌ Error accessing MCP tools: {e}")
                return False
    
    async def test_token_refresh(self) -> bool:
        """Test token refresh with Keycloak"""
        print("\n🔄 Testing Token Refresh...")
        
        if not self.refresh_token:
            print("❌ No refresh token available. Please login first.")
            return False
        
        async with httpx.AsyncClient() as client:
            try:
                token_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
                
                data = {
                    "grant_type": "refresh_token",
                    "client_id": KEYCLOAK_CLIENT_ID,
                    "client_secret": KEYCLOAK_CLIENT_SECRET,
                    "refresh_token": self.refresh_token
                }
                
                response = await client.post(token_url, data=data)
                
                if response.status_code == 200:
                    token_data = response.json()
                    self.access_token = token_data.get("access_token")
                    self.refresh_token = token_data.get("refresh_token")
                    print(f"✅ Token refresh successful")
                    print(f"   New access token: {self.access_token[:50]}...")
                    return True
                else:
                    print(f"❌ Token refresh failed: {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"❌ Error during token refresh: {e}")
                return False
    
    async def run_all_tests(self, username: str, password: str):
        """Run all integration tests"""
        print("=" * 80)
        print("KEYCLOAK + MCP INTEGRATION TEST SUITE")
        print("=" * 80)
        
        results = {}
        
        # Test 1: MCP Health
        results['mcp_health'] = await self.test_mcp_health()
        
        # Test 2: Keycloak Login
        results['keycloak_login'] = await self.test_keycloak_login(username, password)
        
        if results['keycloak_login']:
            # Test 3: MCP Auth with Keycloak Token
            results['mcp_auth'] = await self.test_mcp_auth_with_keycloak_token()
            
            # Test 4: MCP Tool Access
            results['mcp_tools'] = await self.test_mcp_tool_access()
            
            # Test 5: Token Refresh
            results['token_refresh'] = await self.test_token_refresh()
            
            # Test 6: MCP Tools with Refreshed Token
            if results['token_refresh']:
                results['mcp_tools_refreshed'] = await self.test_mcp_tool_access()
        
        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name:25} {status}")
        
        all_passed = all(results.values())
        
        if all_passed:
            print("\n🎉 All tests passed! Keycloak + MCP integration is working correctly.")
        else:
            print("\n⚠️  Some tests failed. Please check the configuration.")
        
        return all_passed


async def main():
    """Main function"""
    print("Keycloak + MCP Integration Test")
    print("-" * 40)
    
    # Check if running in interactive mode
    if len(sys.argv) > 2:
        username = sys.argv[1]
        password = sys.argv[2]
    else:
        print("\nPlease provide Keycloak credentials:")
        username = input("Username: ")
        import getpass
        password = getpass.getpass("Password: ")
    
    # Check environment
    if not KEYCLOAK_CLIENT_SECRET:
        print("\n⚠️  Warning: KEYCLOAK_CLIENT_SECRET is not set in environment")
        print("   Please set it in .env.production or as environment variable")
        client_secret = input("Enter Keycloak Client Secret: ")
        os.environ["KEYCLOAK_CLIENT_SECRET"] = client_secret
    
    # Run tests
    tester = TestKeycloakMCPIntegration()
    success = await tester.run_all_tests(username, password)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
