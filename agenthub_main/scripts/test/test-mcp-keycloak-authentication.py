#!/usr/bin/env python3
"""
Test MCP-Keycloak Authentication Flow
Tests the complete authentication and token management flow
"""

import os
import sys
import asyncio
import logging
import httpx
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MCPKeycloakAuthTester:
    """Test MCP-Keycloak authentication integration"""
    
    def __init__(self):
        """Initialize tester with configuration"""
        load_dotenv()
        
        # Keycloak configuration
        self.keycloak_url = os.getenv('KEYCLOAK_URL')
        self.keycloak_realm = os.getenv('KEYCLOAK_REALM', 'agenthub')
        self.keycloak_client_id = os.getenv('KEYCLOAK_CLIENT_ID', 'mcp-backend')
        self.keycloak_client_secret = os.getenv('KEYCLOAK_CLIENT_SECRET')
        
        # MCP Server configuration
        self.mcp_url = f"http://localhost:{os.getenv('MCP_PORT', '8001')}"
        
        # Test user credentials (you'll need to create this user in Keycloak)
        self.test_username = os.getenv('TEST_USERNAME', 'testuser')
        self.test_password = os.getenv('TEST_PASSWORD', 'TestPassword123!')
        
        self.access_token = None
        self.refresh_token = None
        self.mcp_token = None
    
    async def test_keycloak_login(self) -> bool:
        """Test login to Keycloak"""
        logger.info("\n1. Testing Keycloak Login...")
        
        token_url = (
            f"{self.keycloak_url}/realms/{self.keycloak_realm}/"
            f"protocol/openid-connect/token"
        )
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    token_url,
                    data={
                        'grant_type': 'password',
                        'client_id': self.keycloak_client_id,
                        'client_secret': self.keycloak_client_secret,
                        'username': self.test_username,
                        'password': self.test_password,
                        'scope': 'openid email profile'
                    },
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                )
                
                if response.status_code == 200:
                    tokens = response.json()
                    self.access_token = tokens['access_token']
                    self.refresh_token = tokens['refresh_token']
                    
                    logger.info("✓ Keycloak login successful")
                    logger.info(f"  Access token: {self.access_token[:50]}...")
                    logger.info(f"  Token type: {tokens.get('token_type')}")
                    logger.info(f"  Expires in: {tokens.get('expires_in')} seconds")
                    return True
                else:
                    logger.error(f"❌ Login failed: {response.status_code}")
                    logger.error(f"  Response: {response.text}")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Login error: {e}")
                return False
    
    async def test_mcp_authentication(self) -> bool:
        """Test MCP server authentication with Keycloak token"""
        logger.info("\n2. Testing MCP Server Authentication...")
        
        if not self.access_token:
            logger.error("❌ No access token available")
            return False
        
        async with httpx.AsyncClient() as client:
            try:
                # Test authenticated endpoint
                response = await client.get(
                    f"{self.mcp_url}/api/user/profile",
                    headers={
                        'Authorization': f'Bearer {self.access_token}'
                    }
                )
                
                if response.status_code == 200:
                    user_info = response.json()
                    logger.info("✓ MCP authentication successful")
                    logger.info(f"  User ID: {user_info.get('user_id')}")
                    logger.info(f"  Username: {user_info.get('username')}")
                    logger.info(f"  Email: {user_info.get('email')}")
                    return True
                elif response.status_code == 401:
                    logger.error("❌ MCP authentication failed: Unauthorized")
                    return False
                else:
                    logger.error(f"❌ MCP authentication failed: {response.status_code}")
                    logger.error(f"  Response: {response.text}")
                    return False
                    
            except httpx.ConnectError:
                logger.error(f"❌ Cannot connect to MCP server at {self.mcp_url}")
                logger.info("  Make sure the MCP server is running")
                return False
            except Exception as e:
                logger.error(f"❌ MCP authentication error: {e}")
                return False
    
    async def test_create_mcp_token(self) -> bool:
        """Test creating an MCP token"""
        logger.info("\n3. Testing MCP Token Creation...")
        
        if not self.access_token:
            logger.error("❌ No access token available")
            return False
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.mcp_url}/api/tokens/create",
                    headers={
                        'Authorization': f'Bearer {self.access_token}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'name': 'Test Token',
                        'scopes': ['read', 'write'],
                        'expires_in_days': 30
                    }
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    self.mcp_token = token_data.get('token')
                    
                    logger.info("✓ MCP token created successfully")
                    logger.info(f"  Token: {self.mcp_token[:30]}...")
                    logger.info(f"  Token ID: {token_data.get('token_id')}")
                    logger.info(f"  Name: {token_data.get('name')}")
                    logger.info(f"  Scopes: {token_data.get('scopes')}")
                    logger.info(f"  Expires at: {token_data.get('expires_at')}")
                    return True
                else:
                    logger.error(f"❌ Token creation failed: {response.status_code}")
                    logger.error(f"  Response: {response.text}")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Token creation error: {e}")
                return False
    
    async def test_use_mcp_token(self) -> bool:
        """Test using an MCP token for authentication"""
        logger.info("\n4. Testing MCP Token Authentication...")
        
        if not self.mcp_token:
            logger.error("❌ No MCP token available")
            return False
        
        async with httpx.AsyncClient() as client:
            try:
                # Test MCP tools endpoint with token
                response = await client.post(
                    f"{self.mcp_url}/mcp/manage_context",
                    headers={
                        'X-MCP-Token': self.mcp_token,
                        'Content-Type': 'application/json'
                    },
                    json={
                        'action': 'get',
                        'level': 'global',
                        'context_id': 'global'
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("✓ MCP token authentication successful")
                    logger.info(f"  Response: {json.dumps(result, indent=2)[:200]}...")
                    return True
                elif response.status_code == 401:
                    logger.error("❌ MCP token authentication failed: Unauthorized")
                    return False
                else:
                    logger.error(f"❌ MCP token authentication failed: {response.status_code}")
                    logger.error(f"  Response: {response.text}")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ MCP token authentication error: {e}")
                return False
    
    async def test_list_tokens(self) -> bool:
        """Test listing user's MCP tokens"""
        logger.info("\n5. Testing List User Tokens...")
        
        if not self.access_token:
            logger.error("❌ No access token available")
            return False
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.mcp_url}/api/tokens",
                    headers={
                        'Authorization': f'Bearer {self.access_token}'
                    }
                )
                
                if response.status_code == 200:
                    tokens = response.json()
                    logger.info("✓ Token list retrieved successfully")
                    logger.info(f"  Total tokens: {len(tokens)}")
                    
                    for token in tokens[:3]:  # Show first 3 tokens
                        logger.info(f"  - {token.get('name')}: Created {token.get('created_at')}")
                    
                    return True
                else:
                    logger.error(f"❌ Token list failed: {response.status_code}")
                    logger.error(f"  Response: {response.text}")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Token list error: {e}")
                return False
    
    async def test_revoke_token(self) -> bool:
        """Test revoking an MCP token"""
        logger.info("\n6. Testing Token Revocation...")
        
        if not self.access_token or not self.mcp_token:
            logger.error("❌ No tokens available for revocation test")
            return False
        
        async with httpx.AsyncClient() as client:
            try:
                # First get token list to find token ID
                response = await client.get(
                    f"{self.mcp_url}/api/tokens",
                    headers={
                        'Authorization': f'Bearer {self.access_token}'
                    }
                )
                
                if response.status_code != 200:
                    logger.error("❌ Failed to get token list")
                    return False
                
                tokens = response.json()
                test_token = next((t for t in tokens if t['name'] == 'Test Token'), None)
                
                if not test_token:
                    logger.error("❌ Test token not found")
                    return False
                
                # Revoke the token
                response = await client.delete(
                    f"{self.mcp_url}/api/tokens/{test_token['id']}",
                    headers={
                        'Authorization': f'Bearer {self.access_token}'
                    }
                )
                
                if response.status_code == 200:
                    logger.info("✓ Token revoked successfully")
                    
                    # Verify token no longer works
                    response = await client.post(
                        f"{self.mcp_url}/mcp/manage_context",
                        headers={
                            'X-MCP-Token': self.mcp_token,
                            'Content-Type': 'application/json'
                        },
                        json={
                            'action': 'get',
                            'level': 'global',
                            'context_id': 'global'
                        }
                    )
                    
                    if response.status_code == 401:
                        logger.info("✓ Revoked token correctly rejected")
                        return True
                    else:
                        logger.error("❌ Revoked token still accepted!")
                        return False
                else:
                    logger.error(f"❌ Token revocation failed: {response.status_code}")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Token revocation error: {e}")
                return False
    
    async def test_token_refresh(self) -> bool:
        """Test refreshing Keycloak token"""
        logger.info("\n7. Testing Token Refresh...")
        
        if not self.refresh_token:
            logger.error("❌ No refresh token available")
            return False
        
        token_url = (
            f"{self.keycloak_url}/realms/{self.keycloak_realm}/"
            f"protocol/openid-connect/token"
        )
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    token_url,
                    data={
                        'grant_type': 'refresh_token',
                        'client_id': self.keycloak_client_id,
                        'client_secret': self.keycloak_client_secret,
                        'refresh_token': self.refresh_token
                    },
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                )
                
                if response.status_code == 200:
                    tokens = response.json()
                    self.access_token = tokens['access_token']
                    self.refresh_token = tokens['refresh_token']
                    
                    logger.info("✓ Token refresh successful")
                    logger.info(f"  New access token: {self.access_token[:50]}...")
                    return True
                else:
                    logger.error(f"❌ Token refresh failed: {response.status_code}")
                    logger.error(f"  Response: {response.text}")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Token refresh error: {e}")
                return False
    
    async def run_tests(self):
        """Run all authentication tests"""
        logger.info("=" * 60)
        logger.info("MCP-Keycloak Authentication Test Suite")
        logger.info("=" * 60)
        
        # Check configuration
        if not self.keycloak_url:
            logger.error("\n❌ KEYCLOAK_URL not configured in .env")
            logger.info("Please set KEYCLOAK_URL to your Keycloak cloud instance")
            return False
        
        if not self.keycloak_client_secret:
            logger.error("\n❌ KEYCLOAK_CLIENT_SECRET not configured in .env")
            logger.info("Please set KEYCLOAK_CLIENT_SECRET for your client")
            return False
        
        logger.info(f"\nConfiguration:")
        logger.info(f"  Keycloak URL: {self.keycloak_url}")
        logger.info(f"  Realm: {self.keycloak_realm}")
        logger.info(f"  Client ID: {self.keycloak_client_id}")
        logger.info(f"  MCP Server: {self.mcp_url}")
        logger.info(f"  Test User: {self.test_username}")
        
        # Run tests
        results = []
        
        tests = [
            ("Keycloak Login", self.test_keycloak_login),
            ("MCP Authentication", self.test_mcp_authentication),
            ("Create MCP Token", self.test_create_mcp_token),
            ("Use MCP Token", self.test_use_mcp_token),
            ("List Tokens", self.test_list_tokens),
            ("Revoke Token", self.test_revoke_token),
            ("Token Refresh", self.test_token_refresh)
        ]
        
        for test_name, test_func in tests:
            try:
                result = await test_func()
                results.append((test_name, result))
            except Exception as e:
                logger.error(f"\n❌ {test_name} failed with exception: {e}")
                results.append((test_name, False))
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Test Results Summary")
        logger.info("=" * 60)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✓ PASSED" if result else "❌ FAILED"
            logger.info(f"  {test_name:.<30} {status}")
        
        logger.info(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("\n🎉 All tests passed! Authentication is working correctly.")
        else:
            logger.error(f"\n❌ {total - passed} test(s) failed. Please check the configuration.")
        
        return passed == total

async def main():
    """Main entry point"""
    tester = MCPKeycloakAuthTester()
    success = await tester.run_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())