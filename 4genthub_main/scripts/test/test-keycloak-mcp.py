#!/usr/bin/env python3
"""
Test Script for MCP Server with Keycloak Authentication

This script tests the integration between MCP server and Keycloak authentication.
It verifies token validation, MCP tool access, and proper authorization.
"""

import os
import sys
import json
import asyncio
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env.production")

# Configuration
MCP_SERVER_URL = os.getenv("MCP_HOST", "http://localhost") + ":" + os.getenv("MCP_PORT", "8001")
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "https://your-keycloak.cloud.provider.com")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "4genthub")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "mcp-backend")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "")

# Colors for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


class KeycloakMCPTester:
    """Test class for Keycloak and MCP integration"""
    
    def __init__(self):
        self.token = None
        self.headers = {}
        
    def print_header(self, message: str):
        """Print formatted header"""
        print(f"\n{BLUE}{'='*60}{NC}")
        print(f"{BLUE}{message}{NC}")
        print(f"{BLUE}{'='*60}{NC}")
    
    def print_success(self, message: str):
        """Print success message"""
        print(f"{GREEN}✓ {message}{NC}")
    
    def print_error(self, message: str):
        """Print error message"""
        print(f"{RED}✗ {message}{NC}")
    
    def print_warning(self, message: str):
        """Print warning message"""
        print(f"{YELLOW}⚠ {message}{NC}")
    
    def test_keycloak_connection(self) -> bool:
        """Test connection to Keycloak server"""
        self.print_header("Testing Keycloak Connection")
        
        if KEYCLOAK_URL == "https://your-keycloak.cloud.provider.com":
            self.print_error("KEYCLOAK_URL not configured in .env.production")
            self.print_warning("Please update KEYCLOAK_URL with your actual Keycloak instance")
            return False
        
        try:
            # Test Keycloak well-known endpoint
            well_known_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/.well-known/openid-configuration"
            response = requests.get(well_known_url, timeout=5)
            
            if response.status_code == 200:
                self.print_success(f"Connected to Keycloak: {KEYCLOAK_URL}")
                self.print_success(f"Realm: {KEYCLOAK_REALM}")
                
                # Display endpoints
                config = response.json()
                print(f"\nEndpoints discovered:")
                print(f"  Token: {config.get('token_endpoint', 'N/A')}")
                print(f"  Auth: {config.get('authorization_endpoint', 'N/A')}")
                print(f"  JWKS: {config.get('jwks_uri', 'N/A')}")
                return True
            else:
                self.print_error(f"Failed to connect to Keycloak: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.print_error(f"Connection error: {e}")
            return False
    
    def get_keycloak_token(self, username: str, password: str) -> Optional[str]:
        """Get access token from Keycloak"""
        self.print_header("Getting Keycloak Token")
        
        if not KEYCLOAK_CLIENT_SECRET:
            self.print_error("KEYCLOAK_CLIENT_SECRET not configured")
            return None
        
        token_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
        
        data = {
            "grant_type": "password",
            "client_id": KEYCLOAK_CLIENT_ID,
            "client_secret": KEYCLOAK_CLIENT_SECRET,
            "username": username,
            "password": password
        }
        
        try:
            response = requests.post(token_url, data=data, timeout=10)
            
            if response.status_code == 200:
                token_data = response.json()
                self.token = token_data.get("access_token")
                self.headers = {"Authorization": f"Bearer {self.token}"}
                
                self.print_success("Token obtained successfully")
                print(f"  Token type: {token_data.get('token_type', 'N/A')}")
                print(f"  Expires in: {token_data.get('expires_in', 'N/A')} seconds")
                
                # Decode token to show claims (without verification for display)
                import base64
                token_parts = self.token.split('.')
                if len(token_parts) >= 2:
                    # Decode payload (add padding if needed)
                    payload = token_parts[1] + '=' * (4 - len(token_parts[1]) % 4)
                    decoded = base64.b64decode(payload)
                    claims = json.loads(decoded)
                    
                    print(f"\nToken claims:")
                    print(f"  Subject: {claims.get('sub', 'N/A')}")
                    print(f"  Email: {claims.get('email', 'N/A')}")
                    
                    # Extract roles
                    realm_roles = claims.get('realm_access', {}).get('roles', [])
                    client_roles = claims.get('resource_access', {}).get(KEYCLOAK_CLIENT_ID, {}).get('roles', [])
                    
                    print(f"  Realm roles: {', '.join(realm_roles) if realm_roles else 'None'}")
                    print(f"  Client roles: {', '.join(client_roles) if client_roles else 'None'}")
                
                return self.token
            else:
                self.print_error(f"Failed to get token: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            self.print_error(f"Error getting token: {e}")
            return None
    
    def test_mcp_health(self) -> bool:
        """Test MCP server health endpoint"""
        self.print_header("Testing MCP Server Health")
        
        try:
            response = requests.get(f"{MCP_SERVER_URL}/health", timeout=5)
            
            if response.status_code == 200:
                health_data = response.json()
                self.print_success(f"MCP Server is healthy")
                print(f"  Status: {health_data.get('status', 'N/A')}")
                print(f"  Database: {health_data.get('database', 'N/A')}")
                print(f"  Auth enabled: {health_data.get('auth_enabled', 'N/A')}")
                return True
            else:
                self.print_error(f"MCP Server unhealthy: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.print_error(f"Cannot connect to MCP server: {e}")
            self.print_warning(f"Make sure MCP server is running on {MCP_SERVER_URL}")
            return False
    
    def test_mcp_auth(self) -> bool:
        """Test MCP authentication with Keycloak token"""
        self.print_header("Testing MCP Authentication")
        
        if not self.token:
            self.print_warning("No token available, testing without authentication")
            headers = {}
        else:
            headers = self.headers
        
        try:
            # Test authenticated endpoint
            response = requests.post(
                f"{MCP_SERVER_URL}/mcp/manage_project",
                json={"action": "list"},
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.print_success("MCP authentication successful")
                data = response.json()
                
                if "projects" in data:
                    print(f"  Projects accessible: {len(data['projects'])}")
                
                return True
            elif response.status_code == 401:
                self.print_error("Authentication failed - Invalid token")
                return False
            elif response.status_code == 403:
                self.print_error("Authorization failed - Insufficient permissions")
                self.print_warning("User needs 'mcp-user' or 'mcp-tools' role in Keycloak")
                return False
            else:
                self.print_error(f"MCP request failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            self.print_error(f"Error testing MCP auth: {e}")
            return False
    
    def test_mcp_tools(self) -> bool:
        """Test MCP tool execution with authentication"""
        self.print_header("Testing MCP Tool Execution")
        
        if not self.token:
            self.print_warning("Skipping tool test - no token available")
            return False
        
        # Test various MCP tools
        tools_to_test = [
            {
                "name": "manage_context",
                "endpoint": "/mcp/manage_context",
                "payload": {"action": "get", "level": "global", "context_id": "global"}
            },
            {
                "name": "manage_task",
                "endpoint": "/mcp/manage_task",
                "payload": {"action": "list", "limit": 5}
            },
            {
                "name": "call_agent",
                "endpoint": "/mcp/call_agent",
                "payload": {"name_agent": "@general_purpose"}
            }
        ]
        
        all_passed = True
        
        for tool in tools_to_test:
            print(f"\nTesting tool: {tool['name']}")
            
            try:
                response = requests.post(
                    f"{MCP_SERVER_URL}{tool['endpoint']}",
                    json=tool['payload'],
                    headers=self.headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    self.print_success(f"  {tool['name']} - Success")
                else:
                    self.print_error(f"  {tool['name']} - Failed ({response.status_code})")
                    all_passed = False
                    
            except Exception as e:
                self.print_error(f"  {tool['name']} - Error: {e}")
                all_passed = False
        
        return all_passed
    
    def run_tests(self):
        """Run all tests"""
        print(f"{GREEN}{'='*60}{NC}")
        print(f"{GREEN}MCP + Keycloak Integration Test{NC}")
        print(f"{GREEN}{'='*60}{NC}")
        
        # Test results
        results = {}
        
        # 1. Test MCP Health (no auth required)
        results['mcp_health'] = self.test_mcp_health()
        
        # 2. Test Keycloak Connection
        results['keycloak_connection'] = self.test_keycloak_connection()
        
        # 3. Get token if Keycloak is configured
        if results['keycloak_connection']:
            # Prompt for credentials
            print(f"\n{YELLOW}Enter Keycloak credentials to test authentication:{NC}")
            username = input("Username: ")
            password = input("Password: ")
            
            if username and password:
                token = self.get_keycloak_token(username, password)
                results['token_obtained'] = token is not None
            else:
                self.print_warning("Skipping authentication test - no credentials provided")
                results['token_obtained'] = False
        else:
            results['token_obtained'] = False
        
        # 4. Test MCP Authentication
        results['mcp_auth'] = self.test_mcp_auth()
        
        # 5. Test MCP Tools
        if results['token_obtained']:
            results['mcp_tools'] = self.test_mcp_tools()
        else:
            results['mcp_tools'] = False
        
        # Print summary
        self.print_header("Test Summary")
        
        for test, passed in results.items():
            if passed:
                self.print_success(f"{test.replace('_', ' ').title()}: PASSED")
            else:
                self.print_error(f"{test.replace('_', ' ').title()}: FAILED")
        
        # Overall result
        all_passed = all(results.values())
        
        print(f"\n{GREEN if all_passed else RED}{'='*60}{NC}")
        if all_passed:
            print(f"{GREEN}All tests PASSED!{NC}")
            print(f"{GREEN}MCP server is properly configured with Keycloak.{NC}")
        else:
            print(f"{RED}Some tests FAILED.{NC}")
            print(f"{YELLOW}Please check the configuration and try again.{NC}")
        print(f"{GREEN if all_passed else RED}{'='*60}{NC}")
        
        return 0 if all_passed else 1


def main():
    """Main function"""
    tester = KeycloakMCPTester()
    return tester.run_tests()


if __name__ == "__main__":
    sys.exit(main())