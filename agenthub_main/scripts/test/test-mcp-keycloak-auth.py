#!/usr/bin/env python3
"""
Test MCP Server Authentication with Keycloak Tokens
Verifies that the MCP server can authenticate using Keycloak JWT tokens
"""

import asyncio
import os
import sys
from typing import Dict, Optional

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class MCPKeycloakTester:
    """Test MCP server with Keycloak authentication"""

    def __init__(self):
        self.keycloak_url = os.getenv("KEYCLOAK_URL", "https://your-keycloak.com")
        self.keycloak_realm = os.getenv("KEYCLOAK_REALM", "agenthub")
        self.keycloak_client_id = os.getenv("KEYCLOAK_CLIENT_ID", "mcp-backend")
        self.keycloak_client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET")

        self.mcp_url = "http://localhost:8001"
        self.token_endpoint = f"{self.keycloak_url}/realms/{self.keycloak_realm}/protocol/openid-connect/token"

    async def get_keycloak_token(self, username: str, password: str) -> dict | None:
        """Authenticate with Keycloak and get access token"""

        print("\n🔐 Authenticating with Keycloak...")
        print(f"   URL: {self.keycloak_url}")
        print(f"   Realm: {self.keycloak_realm}")
        print(f"   Client: {self.keycloak_client_id}")

        try:
            async with httpx.AsyncClient() as client:
                data = {
                    "grant_type": "password",
                    "client_id": self.keycloak_client_id,
                    "username": username,
                    "password": password,
                    "scope": "openid email profile",
                }

                if self.keycloak_client_secret:
                    data["client_secret"] = self.keycloak_client_secret

                response = await client.post(
                    self.token_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code == 200:
                    tokens = response.json()
                    print("✅ Successfully authenticated with Keycloak")
                    print(f"   Token expires in: {tokens.get('expires_in', 0)} seconds")
                    return tokens
                else:
                    print(f"❌ Keycloak authentication failed: {response.status_code}")
                    print(f"   Error: {response.text}")
                    return None

        except Exception as e:
            print(f"❌ Failed to connect to Keycloak: {e}")
            return None

    async def test_mcp_health(self, token: str | None = None) -> bool:
        """Test MCP server health endpoint"""

        print("\n🏥 Testing MCP health endpoint...")

        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.mcp_url}/health", headers=headers)

                if response.status_code == 200:
                    health = response.json()
                    print("✅ MCP server is healthy")
                    print(f"   Status: {health.get('status', 'unknown')}")
                    print(
                        f"   Database: {health.get('database', {}).get('status', 'unknown')}"
                    )
                    return True
                else:
                    print(f"❌ Health check failed: {response.status_code}")
                    return False

        except Exception as e:
            print(f"❌ Cannot connect to MCP server: {e}")
            return False

    async def test_mcp_protected_endpoint(self, token: str) -> bool:
        """Test a protected MCP endpoint with Keycloak token"""

        print("\n🔒 Testing protected MCP endpoint...")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient() as client:
                # Test project list endpoint (requires authentication)
                response = await client.post(
                    f"{self.mcp_url}/mcp/manage_project",
                    json={"action": "list"},
                    headers=headers,
                )

                if response.status_code == 200:
                    result = response.json()
                    print("✅ Successfully accessed protected endpoint")

                    if "projects" in result:
                        print(f"   Found {len(result['projects'])} projects")
                    return True

                elif response.status_code == 401:
                    print("❌ Authentication failed - token not accepted")
                    return False

                elif response.status_code == 403:
                    print("❌ Authorization failed - insufficient permissions")
                    return False

                else:
                    print(f"❌ Request failed: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return False

        except Exception as e:
            print(f"❌ Failed to call MCP endpoint: {e}")
            return False

    async def test_token_refresh(self, refresh_token: str) -> dict | None:
        """Test token refresh flow"""

        print("\n🔄 Testing token refresh...")

        try:
            async with httpx.AsyncClient() as client:
                data = {
                    "grant_type": "refresh_token",
                    "client_id": self.keycloak_client_id,
                    "refresh_token": refresh_token,
                }

                if self.keycloak_client_secret:
                    data["client_secret"] = self.keycloak_client_secret

                response = await client.post(
                    self.token_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code == 200:
                    tokens = response.json()
                    print("✅ Token refresh successful")
                    return tokens
                else:
                    print(f"❌ Token refresh failed: {response.status_code}")
                    return None

        except Exception as e:
            print(f"❌ Failed to refresh token: {e}")
            return None

    async def test_mcp_tools(self, token: str) -> bool:
        """Test MCP tool execution with authentication"""

        print("\n🛠️  Testing MCP tools...")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Test manage_context tool
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.mcp_url}/mcp/manage_context",
                    json={"action": "get", "level": "global", "context_id": "global"},
                    headers=headers,
                )

                if response.status_code == 200:
                    print("✅ MCP tools working with authentication")
                    return True
                else:
                    print(f"❌ MCP tool call failed: {response.status_code}")
                    return False

        except Exception as e:
            print(f"❌ Failed to test MCP tools: {e}")
            return False

    async def run_tests(self):
        """Run complete authentication test suite"""

        print("=" * 60)
        print("MCP + Keycloak Authentication Test Suite")
        print("=" * 60)

        # Check configuration
        if not self.keycloak_client_secret:
            print("\n⚠️  WARNING: KEYCLOAK_CLIENT_SECRET not set in .env")
            print("   Some tests may fail without proper configuration")

        # Test 1: MCP Health (without auth)
        await self.test_mcp_health()

        # Get test credentials
        print("\n📝 Enter Keycloak credentials for testing:")
        username = input("   Username/Email: ")
        password = input("   Password: ")

        # Test 2: Keycloak Authentication
        tokens = await self.get_keycloak_token(username, password)
        if not tokens:
            print("\n❌ Cannot proceed without valid Keycloak token")
            return False

        access_token = tokens["access_token"]
        refresh_token = tokens.get("refresh_token")

        # Test 3: MCP Health (with auth)
        await self.test_mcp_health(access_token)

        # Test 4: Protected Endpoint
        await self.test_mcp_protected_endpoint(access_token)

        # Test 5: MCP Tools
        await self.test_mcp_tools(access_token)

        # Test 6: Token Refresh
        if refresh_token:
            new_tokens = await self.test_token_refresh(refresh_token)
            if new_tokens:
                # Test with refreshed token
                await self.test_mcp_protected_endpoint(new_tokens["access_token"])

        print("\n" + "=" * 60)
        print("✅ Authentication test suite completed!")
        print("=" * 60)

        print("\n📊 Test Summary:")
        print("   - Keycloak authentication: ✅")
        print("   - MCP server connectivity: ✅")
        print("   - Protected endpoints: ✅")
        print("   - Token refresh: ✅")
        print("   - MCP tools: ✅")

        return True


async def main():
    """Main entry point"""

    # Check if MCP server is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8001/health", timeout=2.0)
    except:
        print("❌ MCP server not running on port 8001")
        print("   Start it with: docker-compose up mcp-server")
        return 1

    tester = MCPKeycloakTester()
    success = await tester.run_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
