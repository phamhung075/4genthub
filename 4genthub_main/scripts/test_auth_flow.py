#!/usr/bin/env python3
"""
Test Authentication Flow
Verifies the complete authentication flow with Keycloak and MCP tokens
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any
import httpx
from dotenv import load_dotenv

# Add parent directory to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastmcp.auth.keycloak_service import KeycloakAuthService
from fastmcp.auth.mcp_token_service import MCPTokenService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AuthenticationTester:
    """Test authentication flow with Keycloak and MCP"""
    
    def __init__(self):
        """Initialize services"""
        load_dotenv()
        self.keycloak_service = KeycloakAuthService()
        self.mcp_token_service = MCPTokenService()
        self.mcp_server_url = f"http://localhost:{os.getenv('MCP_PORT', '8001')}"
        
    async def test_keycloak_login(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Test Keycloak login"""
        logger.info(f"Testing Keycloak login for user: {username}")
        
        result = await self.keycloak_service.login(username, password)
        
        if result.success:
            logger.info("✅ Keycloak login successful")
            logger.info(f"  - User ID: {result.user.get('sub')}")
            logger.info(f"  - Email: {result.user.get('email')}")
            logger.info(f"  - Roles: {result.roles}")
            logger.info(f"  - Access Token: {result.access_token[:50]}...")
            return {
                "access_token": result.access_token,
                "refresh_token": result.refresh_token,
                "user": result.user,
                "roles": result.roles
            }
        else:
            logger.error(f"❌ Keycloak login failed: {result.error}")
            return None
            
    async def test_mcp_token_generation(self, keycloak_data: Dict[str, Any]) -> Optional[str]:
        """Test MCP token generation from Keycloak token"""
        logger.info("Testing MCP token generation...")
        
        try:
            mcp_result = self.mcp_token_service.generate_mcp_token(
                user_id=keycloak_data["user"]["sub"],
                email=keycloak_data["user"]["email"],
                roles=keycloak_data["roles"],
                keycloak_token=keycloak_data["access_token"]
            )
            
            logger.info("✅ MCP token generated successfully")
            logger.info(f"  - Token: {mcp_result['mcp_token'][:50]}...")
            logger.info(f"  - Expires in: {mcp_result['expires_in']} seconds")
            
            return mcp_result["mcp_token"]
            
        except Exception as e:
            logger.error(f"❌ MCP token generation failed: {e}")
            return None
            
    async def test_mcp_server_connection(self, mcp_token: str) -> bool:
        """Test connection to MCP server with token"""
        logger.info("Testing MCP server connection...")
        
        try:
            async with httpx.AsyncClient() as client:
                # Test health endpoint with authentication
                response = await client.get(
                    f"{self.mcp_server_url}/health",
                    headers={"Authorization": f"Bearer {mcp_token}"},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info("✅ MCP server connection successful")
                    health_data = response.json()
                    logger.info(f"  - Status: {health_data.get('status')}")
                    logger.info(f"  - Database: {health_data.get('database', {}).get('status')}")
                    return True
                else:
                    logger.error(f"❌ MCP server returned status: {response.status_code}")
                    return False
                    
        except httpx.ConnectError:
            logger.error("❌ Cannot connect to MCP server. Is it running?")
            return False
        except Exception as e:
            logger.error(f"❌ MCP server connection failed: {e}")
            return False
            
    async def test_mcp_tool_call(self, mcp_token: str) -> bool:
        """Test calling an MCP tool with authentication"""
        logger.info("Testing MCP tool call...")
        
        try:
            async with httpx.AsyncClient() as client:
                # Test manage_project tool
                response = await client.post(
                    f"{self.mcp_server_url}/mcp/manage_project",
                    headers={"Authorization": f"Bearer {mcp_token}"},
                    json={"action": "list"},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info("✅ MCP tool call successful")
                    data = response.json()
                    logger.info(f"  - Projects found: {len(data.get('projects', []))}")
                    return True
                elif response.status_code == 401:
                    logger.error("❌ Authentication failed for MCP tool")
                    return False
                else:
                    logger.error(f"❌ MCP tool returned status: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ MCP tool call failed: {e}")
            return False
            
    async def test_token_refresh(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Test token refresh flow"""
        logger.info("Testing token refresh...")
        
        result = await self.keycloak_service.refresh_token(refresh_token)
        
        if result.success:
            logger.info("✅ Token refresh successful")
            logger.info(f"  - New access token: {result.access_token[:50]}...")
            return {
                "access_token": result.access_token,
                "refresh_token": result.refresh_token
            }
        else:
            logger.error(f"❌ Token refresh failed: {result.error}")
            return None
            
    async def test_logout(self, refresh_token: str) -> bool:
        """Test logout flow"""
        logger.info("Testing logout...")
        
        success = await self.keycloak_service.logout(refresh_token)
        
        if success:
            logger.info("✅ Logout successful")
        else:
            logger.error("❌ Logout failed")
            
        return success
        
    async def run_full_test(self, username: str, password: str) -> bool:
        """Run complete authentication flow test"""
        logger.info("=" * 60)
        logger.info("Starting Full Authentication Flow Test")
        logger.info("=" * 60)
        
        all_tests_passed = True
        
        # Test 1: Keycloak Login
        keycloak_data = await self.test_keycloak_login(username, password)
        if not keycloak_data:
            logger.error("Keycloak login failed - stopping tests")
            return False
            
        # Test 2: MCP Token Generation
        mcp_token = await self.test_mcp_token_generation(keycloak_data)
        if not mcp_token:
            all_tests_passed = False
            
        # Test 3: MCP Server Connection
        if mcp_token:
            if not await self.test_mcp_server_connection(mcp_token):
                all_tests_passed = False
                
        # Test 4: MCP Tool Call
        if mcp_token:
            if not await self.test_mcp_tool_call(mcp_token):
                all_tests_passed = False
                
        # Test 5: Token Refresh
        refresh_result = await self.test_token_refresh(keycloak_data["refresh_token"])
        if not refresh_result:
            all_tests_passed = False
            
        # Test 6: Logout
        if not await self.test_logout(keycloak_data["refresh_token"]):
            all_tests_passed = False
            
        logger.info("=" * 60)
        if all_tests_passed:
            logger.info("✅ All authentication tests PASSED")
        else:
            logger.info("⚠️ Some authentication tests FAILED")
        logger.info("=" * 60)
        
        return all_tests_passed
        
    async def run_connection_test(self) -> bool:
        """Test basic connectivity without authentication"""
        logger.info("=" * 60)
        logger.info("Testing Basic Connectivity")
        logger.info("=" * 60)
        
        # Test Keycloak connectivity
        logger.info("Testing Keycloak server...")
        keycloak_url = os.getenv("KEYCLOAK_URL")
        realm = os.getenv("KEYCLOAK_REALM")
        
        if not keycloak_url or keycloak_url.startswith("your-"):
            logger.error("❌ Keycloak URL not configured in .env")
            return False
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{keycloak_url}/realms/{realm}",
                    timeout=10.0
                )
                if response.status_code == 200:
                    logger.info(f"✅ Keycloak server reachable at: {keycloak_url}")
                else:
                    logger.error(f"❌ Keycloak returned status: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"❌ Cannot reach Keycloak: {e}")
            return False
            
        # Test MCP server connectivity
        logger.info("Testing MCP server...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.mcp_server_url}/",
                    timeout=10.0
                )
                logger.info(f"✅ MCP server reachable at: {self.mcp_server_url}")
        except Exception as e:
            logger.error(f"❌ Cannot reach MCP server: {e}")
            logger.info("  Start it with: docker-compose up mcp-server")
            return False
            
        logger.info("=" * 60)
        logger.info("✅ Basic connectivity tests PASSED")
        logger.info("=" * 60)
        return True

async def main():
    """Main test function"""
    tester = AuthenticationTester()
    
    # First test basic connectivity
    if not await tester.run_connection_test():
        logger.error("Basic connectivity failed. Please check your setup.")
        return
        
    # Get test credentials
    print("\nEnter test credentials (or press Enter to skip full test):")
    username = input("Username/Email: ").strip()
    
    if username:
        password = input("Password: ").strip()
        await tester.run_full_test(username, password)
    else:
        logger.info("Skipping full authentication test")

if __name__ == "__main__":
    asyncio.run(main())