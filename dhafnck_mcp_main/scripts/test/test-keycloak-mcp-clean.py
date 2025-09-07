#!/usr/bin/env python3
"""
Test Script: Verify MCP Connection with Keycloak Tokens
========================================================
This script tests the MCP server's ability to authenticate using Keycloak tokens.
"""

import os
import sys
import json
import requests
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_file = Path(".env.clean") if Path(".env.clean").exists() else Path(".env")
load_dotenv(env_file)

class MCPKeycloakTester:
    def __init__(self):
        self.keycloak_url = os.getenv("KEYCLOAK_URL", "")
        self.keycloak_realm = os.getenv("KEYCLOAK_REALM", "dhafnck-mcp")
        self.keycloak_client_id = os.getenv("KEYCLOAK_CLIENT_ID", "mcp-backend")
        self.keycloak_client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET", "")
        self.mcp_url = f"http://localhost:{os.getenv('MCP_PORT', '8001')}"
        self.access_token = None
        self.refresh_token = None
        
    def print_header(self, title):
        """Print a formatted header"""
        print("\n" + "=" * 60)
        print(f" {title}")
        print("=" * 60)
        
    def test_mcp_health(self):
        """Test MCP server health endpoint"""
        self.print_header("Testing MCP Server Health")
        try:
            response = requests.get(f"{self.mcp_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ MCP Server is healthy")
                print(f"   - Version: {data.get('version', 'unknown')}")
                print(f"   - MCP Tools: {data.get('mcp_tools', False)}")
                print(f"   - Keycloak Auth: {data.get('keycloak_auth', False)}")
                print(f"   - Auth Enabled: {data.get('auth_enabled', False)}")
                return True
            else:
                print(f"❌ MCP Server returned status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Cannot connect to MCP server: {e}")
            return False
    
    def test_keycloak_connection(self):
        """Test connection to Keycloak server"""
        self.print_header("Testing Keycloak Connection")
        
        if not self.keycloak_url or "your-keycloak-domain.com" in self.keycloak_url:
            print("⚠️  Keycloak URL not configured")
            print("   Please update KEYCLOAK_URL in your .env file")
            return False
        
        try:
            # Test Keycloak well-known endpoint
            well_known_url = f"{self.keycloak_url}/realms/{self.keycloak_realm}/.well-known/openid-configuration"
            response = requests.get(well_known_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Connected to Keycloak server")
                print(f"   - Realm: {self.keycloak_realm}")
                print(f"   - Issuer: {data.get('issuer', 'unknown')}")
                return True
            else:
                print(f"❌ Keycloak returned status {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Cannot connect to Keycloak: {e}")
            return False
    
    def get_keycloak_token(self, username=None, password=None):
        """Get access token from Keycloak"""
        self.print_header("Getting Keycloak Token")
        
        if not self.keycloak_url or "your-keycloak-domain.com" in self.keycloak_url:
            print("⚠️  Keycloak not configured - using mock token for testing")
            self.access_token = "mock-token-for-testing"
            return True
        
        token_url = f"{self.keycloak_url}/realms/{self.keycloak_realm}/protocol/openid-connect/token"
        
        # Try client credentials flow first
        data = {
            "grant_type": "client_credentials",
            "client_id": self.keycloak_client_id,
            "client_secret": self.keycloak_client_secret
        }
        
        try:
            response = requests.post(token_url, data=data, timeout=10)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                self.refresh_token = token_data.get("refresh_token")
                print(f"✅ Got access token using client credentials")
                return True
            else:
                print(f"⚠️  Client credentials flow failed: {response.status_code}")
                
                # Try password flow if credentials provided
                if username and password:
                    data = {
                        "grant_type": "password",
                        "client_id": self.keycloak_client_id,
                        "client_secret": self.keycloak_client_secret,
                        "username": username,
                        "password": password
                    }
                    
                    response = requests.post(token_url, data=data, timeout=10)
                    if response.status_code == 200:
                        token_data = response.json()
                        self.access_token = token_data.get("access_token")
                        self.refresh_token = token_data.get("refresh_token")
                        print(f"✅ Got access token using password flow")
                        return True
                    else:
                        print(f"❌ Password flow failed: {response.status_code}")
                        return False
                        
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to get token: {e}")
            return False
    
    def test_mcp_auth(self):
        """Test MCP authentication with Keycloak token"""
        self.print_header("Testing MCP Authentication")
        
        if not self.access_token:
            print("❌ No access token available")
            return False
        
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        # Test a protected MCP endpoint
        try:
            response = requests.get(
                f"{self.mcp_url}/mcp/tools",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ MCP authentication successful")
                tools = response.json().get("tools", [])
                print(f"   - Available tools: {len(tools)}")
                return True
            elif response.status_code == 401:
                print(f"❌ Authentication failed: Invalid token")
                return False
            elif response.status_code == 503:
                print(f"⚠️  Authentication service unavailable")
                if os.getenv("AUTH_ENABLED", "true").lower() == "false":
                    print("   Auth is disabled - this is expected")
                    return True
                return False
            else:
                print(f"❌ Unexpected status: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return False
    
    def test_mcp_operations(self):
        """Test MCP operations with authentication"""
        self.print_header("Testing MCP Operations")
        
        if not self.access_token:
            print("⚠️  No token - skipping authenticated operations")
            return True
        
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        # Test project listing
        try:
            response = requests.post(
                f"{self.mcp_url}/mcp/manage_project",
                headers=headers,
                json={"action": "list"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Project listing successful")
                projects = data.get("projects", [])
                print(f"   - Found {len(projects)} projects")
                
                # Test task operations if we have a project
                if projects:
                    project_id = projects[0].get("id")
                    response = requests.post(
                        f"{self.mcp_url}/mcp/manage_task",
                        headers=headers,
                        json={
                            "action": "list",
                            "project_id": project_id
                        },
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        tasks = data.get("tasks", [])
                        print(f"✅ Task listing successful")
                        print(f"   - Found {len(tasks)} tasks")
                    else:
                        print(f"⚠️  Task listing failed: {response.status_code}")
                
                return True
            else:
                print(f"❌ Project listing failed: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Operation failed: {e}")
            return False
    
    def run_tests(self):
        """Run all tests"""
        self.print_header("MCP Keycloak Integration Test")
        
        results = {
            "mcp_health": self.test_mcp_health(),
            "keycloak_connection": self.test_keycloak_connection(),
            "keycloak_token": False,
            "mcp_auth": False,
            "mcp_operations": False
        }
        
        # Only test authentication if MCP and Keycloak are available
        if results["mcp_health"]:
            results["keycloak_token"] = self.get_keycloak_token()
            
            if results["keycloak_token"]:
                results["mcp_auth"] = self.test_mcp_auth()
                results["mcp_operations"] = self.test_mcp_operations()
        
        # Print summary
        self.print_header("Test Summary")
        
        for test, passed in results.items():
            status = "✅" if passed else "❌"
            test_name = test.replace("_", " ").title()
            print(f"{status} {test_name}")
        
        all_passed = all(results.values())
        
        if all_passed:
            print("\n🎉 All tests passed!")
        else:
            print("\n⚠️  Some tests failed. Please check the configuration.")
            
            if not results["keycloak_connection"]:
                print("\nTo configure Keycloak:")
                print("1. Set up a Keycloak instance (cloud or local)")
                print("2. Create a realm called 'dhafnck-mcp'")
                print("3. Create a client called 'mcp-backend' with:")
                print("   - Client authentication: ON")
                print("   - Service accounts roles: ON")
                print("   - Valid redirect URIs: http://localhost:8001/*")
                print("4. Update .env with:")
                print("   - KEYCLOAK_URL")
                print("   - KEYCLOAK_CLIENT_SECRET")
        
        return all_passed

def main():
    """Main entry point"""
    tester = MCPKeycloakTester()
    success = tester.run_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()