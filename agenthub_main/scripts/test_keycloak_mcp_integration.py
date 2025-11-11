#!/usr/bin/env python3
"""
Test Script for Keycloak + MCP Integration

This script tests the complete authentication flow:
1. Login to Keycloak to get access token
2. Exchange Keycloak token for MCP token
3. Use MCP token to access MCP tools
"""

import asyncio
import os
import sys
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# Configuration from environment
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "https://your-keycloak.cloud.provider.com")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "agenthub")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "mcp-backend")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001")


class KeycloakMCPTester:
    """Test Keycloak and MCP integration"""

    def __init__(self):
        self.keycloak_token: str | None = None
        self.mcp_token: str | None = None
        self.user_info: dict[str, Any] | None = None

    async def test_keycloak_login(self, username: str, password: str) -> bool:
        """
        Test Keycloak authentication

        Args:
            username: Keycloak username/email
            password: User password

        Returns:
            True if login successful
        """
        print("\n🔑 Testing Keycloak Login...")
        print(f"   URL: {KEYCLOAK_URL}")
        print(f"   Realm: {KEYCLOAK_REALM}")
        print(f"   Client: {KEYCLOAK_CLIENT_ID}")

        token_endpoint = (
            f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
        )

        try:
            async with httpx.AsyncClient() as client:
                data = {
                    "grant_type": "password",
                    "client_id": KEYCLOAK_CLIENT_ID,
                    "client_secret": KEYCLOAK_CLIENT_SECRET,
                    "username": username,
                    "password": password,
                    "scope": "openid email profile",
                }

                response = await client.post(
                    token_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code == 200:
                    tokens = response.json()
                    self.keycloak_token = tokens["access_token"]
                    print("   ✅ Keycloak login successful!")
                    print(
                        f"   📜 Access token obtained (expires in {tokens.get('expires_in', 0)}s)"
                    )

                    # Get user info
                    await self.get_keycloak_user_info()
                    return True
                else:
                    print(f"   ❌ Login failed: {response.status_code}")
                    print(f"   Error: {response.text}")
                    return False

        except Exception as e:
            print(f"   ❌ Connection error: {e}")
            return False

    async def get_keycloak_user_info(self) -> bool:
        """Get user information from Keycloak"""
        if not self.keycloak_token:
            return False

        userinfo_endpoint = (
            f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/userinfo"
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    userinfo_endpoint,
                    headers={"Authorization": f"Bearer {self.keycloak_token}"},
                )

                if response.status_code == 200:
                    self.user_info = response.json()
                    print(f"   👤 User: {self.user_info.get('email', 'Unknown')}")
                    print(f"   🏷️  Roles: {self.user_info.get('roles', [])}")
                    return True

        except Exception as e:
            print(f"   ⚠️  Could not get user info: {e}")

        return False

    async def test_mcp_token_exchange(self) -> bool:
        """
        Exchange Keycloak token for MCP token

        Returns:
            True if exchange successful
        """
        if not self.keycloak_token:
            print("\n❌ No Keycloak token available")
            return False

        print("\n🔄 Exchanging Keycloak token for MCP token...")

        try:
            async with httpx.AsyncClient() as client:
                # Login to MCP server with Keycloak token
                response = await client.post(
                    f"{MCP_SERVER_URL}/auth/token/exchange",
                    headers={"Authorization": f"Bearer {self.keycloak_token}"},
                    json={"keycloak_token": self.keycloak_token},
                )

                if response.status_code == 200:
                    result = response.json()
                    self.mcp_token = result.get("mcp_token")
                    print("   ✅ MCP token obtained!")
                    print(f"   📜 Token type: {result.get('token_type', 'Bearer')}")
                    print(f"   ⏱️  Expires in: {result.get('expires_in', 0)} seconds")
                    return True
                else:
                    print(f"   ❌ Token exchange failed: {response.status_code}")

                    # Try alternative endpoint
                    print("\n   🔄 Trying alternative login endpoint...")
                    response = await client.post(
                        f"{MCP_SERVER_URL}/auth/login/keycloak",
                        json={"access_token": self.keycloak_token},
                    )

                    if response.status_code == 200:
                        result = response.json()
                        self.mcp_token = result.get(
                            "mcp_token", result.get("access_token")
                        )
                        print("   ✅ MCP token obtained via alternative endpoint!")
                        return True
                    else:
                        print(f"   ❌ Alternative also failed: {response.text}")
                        return False

        except Exception as e:
            print(f"   ❌ Connection error: {e}")
            return False

    async def test_mcp_tool_access(self) -> bool:
        """
        Test accessing MCP tools with token

        Returns:
            True if MCP tools accessible
        """
        token = self.mcp_token or self.keycloak_token
        if not token:
            print("\n❌ No token available for MCP access")
            return False

        print("\n🔧 Testing MCP Tool Access...")
        print(f"   Using token type: {'MCP' if self.mcp_token else 'Keycloak'}")

        # Test various MCP endpoints
        test_endpoints = [
            ("/health", "GET", None),
            ("/mcp/manage_project", "POST", {"action": "list"}),
            (
                "/mcp/manage_context",
                "POST",
                {"action": "get", "level": "global", "context_id": "global"},
            ),
        ]

        success_count = 0

        try:
            async with httpx.AsyncClient() as client:
                for endpoint, method, data in test_endpoints:
                    print(f"\n   📍 Testing {endpoint}...")

                    headers = {"Authorization": f"Bearer {token}"}

                    if method == "GET":
                        response = await client.get(
                            f"{MCP_SERVER_URL}{endpoint}", headers=headers
                        )
                    else:
                        response = await client.post(
                            f"{MCP_SERVER_URL}{endpoint}", headers=headers, json=data
                        )

                    if response.status_code in [200, 201]:
                        print(f"      ✅ Success: {endpoint}")
                        success_count += 1

                        # Show sample response
                        if endpoint == "/health":
                            health = response.json()
                            print(f"      📊 Status: {health.get('status', 'unknown')}")
                            print(
                                f"      🗄️  Database: {health.get('database', {}).get('status', 'unknown')}"
                            )
                    else:
                        print(f"      ❌ Failed: {response.status_code}")
                        if response.status_code == 401:
                            print("      🔒 Authentication required")
                        elif response.status_code == 403:
                            print("      🚫 Permission denied")

        except Exception as e:
            print(f"   ❌ Connection error: {e}")

        print(f"\n   📈 Success rate: {success_count}/{len(test_endpoints)} endpoints")
        return success_count > 0

    async def test_complete_flow(self, username: str, password: str):
        """
        Test the complete authentication flow

        Args:
            username: Keycloak username
            password: User password
        """
        print("\n" + "=" * 60)
        print("🚀 KEYCLOAK + MCP INTEGRATION TEST")
        print("=" * 60)

        # Step 1: Keycloak Login
        if not await self.test_keycloak_login(username, password):
            print("\n❌ Test failed at Keycloak login")
            return

        # Step 2: MCP Token Exchange
        if not await self.test_mcp_token_exchange():
            print("\n⚠️  MCP token exchange failed, trying direct Keycloak token...")

        # Step 3: Test MCP Access
        if await self.test_mcp_tool_access():
            print("\n" + "=" * 60)
            print("✅ INTEGRATION TEST SUCCESSFUL!")
            print("=" * 60)
            print("\n📋 Summary:")
            print("   • Keycloak authentication: ✅")
            print(
                f"   • MCP token exchange: {'✅' if self.mcp_token else '⚠️ Using Keycloak token directly'}"
            )
            print("   • MCP tool access: ✅")
            print(
                f"   • User: {self.user_info.get('email', 'Unknown') if self.user_info else 'Unknown'}"
            )
        else:
            print("\n" + "=" * 60)
            print("❌ INTEGRATION TEST FAILED")
            print("=" * 60)
            print("\n🔍 Troubleshooting:")
            print("   1. Check Keycloak is accessible at:", KEYCLOAK_URL)
            print("   2. Verify client credentials are correct")
            print("   3. Ensure MCP server is running at:", MCP_SERVER_URL)
            print("   4. Check user has appropriate roles in Keycloak")


async def main():
    """Main test function"""

    # Check if credentials are provided
    if len(sys.argv) != 3:
        print(
            "\n📖 Usage: python test_keycloak_mcp_integration.py <username> <password>"
        )
        print("\nExample:")
        print("   python test_keycloak_mcp_integration.py test@example.com mypassword")
        print("\n⚙️  Configuration (via .env or environment):")
        print(f"   KEYCLOAK_URL: {KEYCLOAK_URL}")
        print(f"   KEYCLOAK_REALM: {KEYCLOAK_REALM}")
        print(f"   KEYCLOAK_CLIENT_ID: {KEYCLOAK_CLIENT_ID}")
        print(f"   MCP_SERVER_URL: {MCP_SERVER_URL}")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]

    # Validate configuration
    if KEYCLOAK_URL == "https://your-keycloak.cloud.provider.com":
        print("\n⚠️  WARNING: Using placeholder Keycloak URL")
        print("   Please set KEYCLOAK_URL in your .env file")
        print("\n   Example:")
        print("   KEYCLOAK_URL=https://keycloak.mycompany.com")

    if not KEYCLOAK_CLIENT_SECRET:
        print("\n❌ ERROR: KEYCLOAK_CLIENT_SECRET not set")
        print("   Please set it in your .env file")
        sys.exit(1)

    # Run tests
    tester = KeycloakMCPTester()
    await tester.test_complete_flow(username, password)


if __name__ == "__main__":
    asyncio.run(main())
