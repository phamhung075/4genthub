#!/usr/bin/env python3
"""Simple MCP server test - verify basic functionality."""

import os
import sys
import json
import requests
from datetime import datetime

def test_mcp_server():
    """Test basic MCP server functionality."""
    base_url = "http://localhost:8000"
    
    print("=" * 60)
    print("Simple MCP Server Test")
    print(f"Time: {datetime.now()}")
    print("=" * 60)
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Health Check
    print("\n[TEST 1] Health Check")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed")
            health_data = response.json()
            print(f"   Server: {health_data.get('server', 'Unknown')}")
            print(f"   Version: {health_data.get('version', 'Unknown')}")
            tests_passed += 1
        else:
            print(f"❌ Health check failed: {response.status_code}")
            tests_failed += 1
    except Exception as e:
        print(f"❌ Health check error: {e}")
        tests_failed += 1
    
    # Test 2: API Documentation
    print("\n[TEST 2] API Documentation")
    try:
        response = requests.get(f"{base_url}/ai_docs", timeout=5)
        if response.status_code == 200:
            print("✅ API documentation accessible")
            tests_passed += 1
        else:
            print(f"❌ API documentation not accessible: {response.status_code}")
            tests_failed += 1
    except Exception as e:
        print(f"❌ API documentation error: {e}")
        tests_failed += 1
    
    # Test 3: OpenAPI Schema
    print("\n[TEST 3] OpenAPI Schema")
    try:
        response = requests.get(f"{base_url}/openapi.json", timeout=5)
        if response.status_code == 200:
            schema = response.json()
            print(f"✅ OpenAPI schema retrieved")
            print(f"   Title: {schema.get('info', {}).get('title', 'Unknown')}")
            print(f"   Version: {schema.get('info', {}).get('version', 'Unknown')}")
            tests_passed += 1
        else:
            print(f"❌ OpenAPI schema failed: {response.status_code}")
            tests_failed += 1
    except Exception as e:
        print(f"❌ OpenAPI schema error: {e}")
        tests_failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"✅ Passed: {tests_passed}")
    print(f"❌ Failed: {tests_failed}")
    
    if tests_failed == 0:
        print("\n🎉 All tests passed! MCP server is working correctly.")
    else:
        print(f"\n⚠️ {tests_failed} test(s) failed. Check the server logs.")
    
    print("=" * 60)
    
    return tests_failed == 0

if __name__ == "__main__":
    success = test_mcp_server()
    sys.exit(0 if success else 1)