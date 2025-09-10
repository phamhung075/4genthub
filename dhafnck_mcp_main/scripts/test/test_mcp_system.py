#!/usr/bin/env python3
"""
MCP System Test Script
Tests various components of the DhafnckMCP system to identify issues
"""

import requests
import json
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test if the server is running"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Health check passed:", response.json())
            return True
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_api_endpoints():
    """Test various API endpoints"""
    endpoints = [
        ("/", "GET"),
        ("/ai_docs", "GET"),
        ("/mcp/manage_task", "POST"),
        ("/mcp/manage_context", "POST"),
        ("/mcp/manage_project", "POST"),
    ]
    
    results = []
    for endpoint, method in endpoints:
        try:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}")
            else:
                response = requests.post(f"{BASE_URL}{endpoint}", json={})
            
            if response.status_code in [200, 422]:  # 422 is expected for empty POST
                print(f"✅ {method} {endpoint}: Status {response.status_code}")
                results.append(True)
            else:
                print(f"❌ {method} {endpoint}: Status {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ {method} {endpoint}: Error {e}")
            results.append(False)
    
    return all(results)

def test_database_connection():
    """Test if database is properly initialized"""
    import subprocess
    
    try:
        # Check if tables exist
        result = subprocess.run(
            ["docker", "exec", "dhafnck-postgres", "psql", "-U", "dhafnck_user", 
             "-d", "dhafnck_mcp", "-c", "\\dt"],
            capture_output=True,
            text=True
        )
        
        if "Did not find any relations" in result.stdout:
            print("⚠️ Database exists but has no tables - needs initialization")
            return False
        elif result.returncode == 0:
            print("✅ Database tables found")
            return True
        else:
            print(f"❌ Database error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Database test error: {e}")
        return False

def test_mcp_tools_availability():
    """Test if MCP tools are properly exposed"""
    try:
        # Try to list MCP tools
        result = subprocess.run(
            ["mcp", "list-servers"],
            capture_output=True,
            text=True
        )
        
        if "dhafnck_mcp_http" in result.stdout:
            print("✅ MCP server 'dhafnck_mcp_http' is configured")
            return True
        else:
            print("⚠️ MCP server 'dhafnck_mcp_http' not found in configured servers")
            print("Available servers:", result.stdout)
            return False
    except Exception as e:
        print(f"❌ MCP tools test error: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("DhafnckMCP System Test")
    print("=" * 60)
    
    all_passed = True
    
    # Test 1: Health Check
    print("\n1. Testing server health...")
    if not test_health_check():
        all_passed = False
    
    # Test 2: API Endpoints
    print("\n2. Testing API endpoints...")
    if not test_api_endpoints():
        all_passed = False
    
    # Test 3: Database
    print("\n3. Testing database...")
    if not test_database_connection():
        all_passed = False
        print("   → Issue: Database needs initialization")
        print("   → Solution: Run database migration/init scripts")
    
    # Test 4: MCP Tools
    print("\n4. Testing MCP tools availability...")
    if not test_mcp_tools_availability():
        all_passed = False
        print("   → Issue: MCP server not properly configured")
        print("   → Solution: Check MCP server configuration")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed - see issues above")
        print("\nIdentified Issues:")
        print("1. Database has no tables - needs schema initialization")
        print("2. MCP tools not available through standard interface")
        print("\nRecommended Actions:")
        print("1. Run database initialization script")
        print("2. Check MCP server configuration and registration")
        print("3. Verify backend is properly exposing MCP endpoints")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    import subprocess
    sys.exit(main())