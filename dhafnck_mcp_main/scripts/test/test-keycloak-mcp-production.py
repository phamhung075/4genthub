#!/usr/bin/env python3
"""
Test Keycloak MCP Integration for Production Setup
Tests the clean configuration without backward compatibility
"""

import os
import sys
import asyncio
import json
import httpx
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Add src to path
sys.path.insert(0, 'dhafnck_mcp_main/src')

# Colors for output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'

def print_header(message: str):
    print(f"\n{Colors.BLUE}{'=' * 80}{Colors.END}")
    print(f"{Colors.BLUE}{message}{Colors.END}")
    print(f"{Colors.BLUE}{'=' * 80}{Colors.END}")

def print_success(message: str):
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_warning(message: str):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

def print_error(message: str):
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_info(message: str):
    print(f"{Colors.CYAN}ℹ️  {message}{Colors.END}")

class KeycloakMCPTester:
    """Test Keycloak and MCP integration"""
    
    def __init__(self):
        self.mcp_url = "http://localhost:8001"
        self.keycloak_url = os.getenv("KEYCLOAK_URL", "https://your-keycloak.cloud.provider.com")
        self.keycloak_realm = os.getenv("KEYCLOAK_REALM", "dhafnck-mcp")
        self.keycloak_client_id = os.getenv("KEYCLOAK_CLIENT_ID", "mcp-backend")
        self.keycloak_client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET", "")
        self.access_token = None
        self.refresh_token = None
        
    async def test_mcp_health(self) -> bool:
        """Test MCP server health endpoint"""
        print_header("Testing MCP Server Health")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.mcp_url}/health")
                
                if response.status_code == 200:
                    data = response.json()
                    print_success(f"MCP server is {data.get('status', 'unknown')}")
                    
                    # Check components
                    if data.get('mcp_tools'):
                        print_success("MCP tools initialized")
                    else:
                        print_warning("MCP tools not initialized")
                    
                    if data.get('keycloak_auth'):
                        print_success("Keycloak authentication enabled")
                    else:
                        print_warning("Keycloak authentication not configured")
                    
                    if data.get('auth_enabled'):
                        print_info("Authentication is required for MCP endpoints")
                    else:
                        print_warning("Authentication is disabled (development mode)")
                    
                    return True
                else:
                    print_error(f"Health check failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            print_error(f"Failed to connect to MCP server: {e}")
            return False
    
    async def test_keycloak_connection(self) -> bool:
        """Test Keycloak server connection"""
        print_header("Testing Keycloak Connection")
        
        if self.keycloak_url == "https://your-keycloak.cloud.provider.com":
            print_warning("Keycloak URL not configured")
            print_info("Using mock authentication for development")
            return False
        
        try:
            # Test Keycloak well-known configuration
            well_known_url = f"{self.keycloak_url}/realms/{self.keycloak_realm}/.well-known/openid-configuration"
            
            async with httpx.AsyncClient(verify=False) as client:  # Disable SSL verify for testing
                response = await client.get(well_known_url)
                
                if response.status_code == 200:
                    config = response.json()
                    print_success(f"Connected to Keycloak realm: {self.keycloak_realm}")
                    print_info(f"Token endpoint: {config.get('token_endpoint', 'N/A')}")
                    print_info(f"Authorization endpoint: {config.get('authorization_endpoint', 'N/A')}")
                    return True
                else:
                    print_error(f"Failed to get Keycloak configuration: {response.status_code}")
                    return False
                    
        except Exception as e:
            print_error(f"Failed to connect to Keycloak: {e}")
            print_info("Make sure KEYCLOAK_URL is correctly configured in .env")
            return False
    
    async def test_keycloak_login(self, username: str = None, password: str = None) -> bool:
        """Test login through Keycloak"""
        print_header("Testing Keycloak Login")
        
        if not username or not password:
            print_warning("No test credentials provided")
            print_info("Skipping login test")
            return False
        
        try:
            async with httpx.AsyncClient(verify=False) as client:
                # Try login through MCP endpoint
                response = await client.post(
                    f"{self.mcp_url}/auth/login",
                    json={
                        "username": username,
                        "password": password
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data.get("access_token")
                    self.refresh_token = data.get("refresh_token")
                    
                    print_success(f"Login successful for user: {username}")
                    print_info(f"Access token received (expires in {data.get('expires_in', 'N/A')} seconds)")
                    
                    # Display user info
                    if "user" in data:
                        user = data["user"]
                        print_info(f"User ID: {user.get('id', 'N/A')}")
                        print_info(f"Email: {user.get('email', 'N/A')}")
                    
                    # Display roles
                    if "roles" in data:
                        roles = data["roles"]
                        print_info(f"Roles: {', '.join(roles)}")
                        
                        # Check for MCP roles
                        mcp_roles = [r for r in roles if 'mcp' in r.lower()]
                        if mcp_roles:
                            print_success(f"MCP roles found: {', '.join(mcp_roles)}")
                        else:
                            print_warning("No MCP-specific roles found")
                    
                    return True
                    
                elif response.status_code == 503:
                    print_warning("Authentication service unavailable")
                    print_info("Keycloak might not be configured")
                    return False
                    
                else:
                    print_error(f"Login failed: {response.status_code}")
                    if response.text:
                        print_error(f"Error: {response.text}")
                    return False
                    
        except Exception as e:
            print_error(f"Login error: {e}")
            return False
    
    async def test_mcp_authenticated_call(self) -> bool:
        """Test authenticated MCP tool call"""
        print_header("Testing Authenticated MCP Call")
        
        if not self.access_token:
            print_warning("No access token available")
            print_info("Attempting call without authentication")
        
        try:
            headers = {}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            
            async with httpx.AsyncClient() as client:
                # Test listing MCP tools
                response = await client.get(
                    f"{self.mcp_url}/mcp/tools",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print_success("Successfully accessed MCP tools")
                    
                    if isinstance(data, list):
                        print_info(f"Available tools: {len(data)}")
                        # Show first few tools
                        for tool in data[:5]:
                            if isinstance(tool, dict):
                                print_info(f"  - {tool.get('name', 'Unknown')}")
                        if len(data) > 5:
                            print_info(f"  ... and {len(data) - 5} more")
                    
                    return True
                    
                elif response.status_code == 401:
                    print_error("Authentication required")
                    print_info("Access token might be invalid or expired")
                    return False
                    
                elif response.status_code == 403:
                    print_error("Insufficient permissions")
                    print_info("User might not have required MCP roles")
                    return False
                    
                else:
                    print_error(f"Failed to access MCP tools: {response.status_code}")
                    return False
                    
        except Exception as e:
            print_error(f"MCP call error: {e}")
            return False
    
    async def test_token_refresh(self) -> bool:
        """Test token refresh"""
        print_header("Testing Token Refresh")
        
        if not self.refresh_token:
            print_warning("No refresh token available")
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.mcp_url}/auth/refresh",
                    json={"refresh_token": self.refresh_token}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data.get("access_token")
                    
                    print_success("Token refreshed successfully")
                    print_info(f"New token expires in {data.get('expires_in', 'N/A')} seconds")
                    return True
                    
                else:
                    print_error(f"Token refresh failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            print_error(f"Token refresh error: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all integration tests"""
        print_header("DhafnckMCP Keycloak Integration Test Suite")
        print_info(f"Testing at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print_info(f"MCP URL: {self.mcp_url}")
        print_info(f"Keycloak URL: {self.keycloak_url}")
        
        results = {
            "mcp_health": False,
            "keycloak_connection": False,
            "keycloak_login": False,
            "authenticated_call": False,
            "token_refresh": False
        }
        
        # Run tests
        results["mcp_health"] = await self.test_mcp_health()
        
        if results["mcp_health"]:
            results["keycloak_connection"] = await self.test_keycloak_connection()
            
            # Only test login if Keycloak is configured
            if results["keycloak_connection"]:
                # You can provide test credentials here
                # results["keycloak_login"] = await self.test_keycloak_login("testuser", "testpass")
                pass
            
            # Test authenticated call (will work with or without auth depending on config)
            results["authenticated_call"] = await self.test_mcp_authenticated_call()
            
            if results["keycloak_login"] and self.refresh_token:
                results["token_refresh"] = await self.test_token_refresh()
        
        # Print summary
        print_header("Test Summary")
        
        total_tests = len(results)
        passed_tests = sum(1 for v in results.values() if v)
        
        for test_name, passed in results.items():
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
        
        print()
        if passed_tests == total_tests:
            print_success(f"All {total_tests} tests passed! 🎉")
        elif passed_tests > 0:
            print_warning(f"{passed_tests}/{total_tests} tests passed")
        else:
            print_error("All tests failed")
        
        # Provide guidance based on results
        print_header("Configuration Status")
        
        if not results["keycloak_connection"]:
            print_warning("Keycloak is not configured or unreachable")
            print_info("To enable Keycloak authentication:")
            print_info("1. Edit .env file")
            print_info("2. Set KEYCLOAK_URL to your Keycloak instance")
            print_info("3. Set KEYCLOAK_CLIENT_SECRET")
            print_info("4. Restart the MCP server")
        elif not results["keycloak_login"]:
            print_info("Login test was skipped or failed")
            print_info("Create a test user in Keycloak with MCP roles")
        else:
            print_success("Keycloak integration is fully configured!")
        
        return passed_tests == total_tests

async def main():
    """Main test function"""
    tester = KeycloakMCPTester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Test suite error: {e}")
        sys.exit(1)