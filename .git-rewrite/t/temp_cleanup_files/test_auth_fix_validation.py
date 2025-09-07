#!/usr/bin/env python3
"""
Critical Authentication Vulnerability Test Script
Tests JWT token processing and validation after fixes
"""

import requests
import json
import sys
from typing import Dict, Any

# Test configuration
BACKEND_URL = "http://localhost:8000"
TEST_JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzU1OTcwODQ3LCJpYXQiOjE3NTU4ODQ0NDcsImlzcyI6Imh0dHBzOi8vcG1zd212eGh6ZGZ4ZXFzZmRnaWYuc3VwYWJhc2UuY28vYXV0aC92MSIsInN1YiI6IjY1ZDczM2U5LTA0ZDYtNGRkYS05NTM2LTY4OGMzYTU5NDQ4ZSIsImVtYWlsIjoidGVzdHVzZXJAZXhhbXBsZS5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7InVzZXJuYW1lIjoidGVzdHVzZXIiLCJlbWFpbCI6InRlc3R1c2VyQGV4YW1wbGUuY29tIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3NTU4ODQ0NDd9XSwic2Vzc2lvbl9pZCI6IjEyMzQ1Njc4LTEyMzQtMTIzNC0xMjM0LTEyMzQ1Njc4OTAxMiJ9.NRTRq3d4uVM9PHrqvwkvCA9QXdyHtaXWvx_hcH-dai8"

def test_health_endpoint() -> Dict[str, Any]:
    """Test basic server health and authentication status"""
    print("\n=== TESTING HEALTH ENDPOINT ===")
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}...")
        
        if response.status_code == 200:
            data = response.json()
            auth_enabled = data.get("auth_enabled", False)
            print(f"🔐 Authentication Enabled: {auth_enabled}")
            return {"success": True, "auth_enabled": auth_enabled}
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            return {"success": False, "error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return {"success": False, "error": str(e)}

def test_no_token_request() -> Dict[str, Any]:
    """Test that requests without tokens are properly rejected"""
    print("\n=== TESTING NO TOKEN REQUEST (should be rejected) ===")
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/v2/tasks/",
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:300]}...")
        
        if response.status_code == 401 or response.status_code == 403:
            print("✅ NO TOKEN REQUEST PROPERLY REJECTED")
            return {"success": True, "properly_rejected": True}
        else:
            print("🚨 CRITICAL: NO TOKEN REQUEST WAS NOT REJECTED - SECURITY BYPASS!")
            return {"success": False, "security_bypass": True}
            
    except Exception as e:
        print(f"❌ No token test error: {e}")
        return {"success": False, "error": str(e)}

def test_valid_jwt_token() -> Dict[str, Any]:
    """Test that valid JWT tokens are properly processed"""
    print("\n=== TESTING VALID JWT TOKEN REQUEST ===")
    try:
        headers = {"Authorization": f"Bearer {TEST_JWT_TOKEN}", "Content-Type": "application/json"}
        response = requests.get(
            f"{BACKEND_URL}/api/v2/tasks/",
            headers=headers,
            timeout=5
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:300]}...")
        
        if response.status_code == 200:
            print("✅ VALID JWT TOKEN PROPERLY PROCESSED")
            return {"success": True, "jwt_processed": True}
        elif response.status_code == 401:
            print("⚠️ JWT token rejected - may be expired or invalid signature")
            return {"success": False, "jwt_rejected": True}
        else:
            print(f"⚠️ Unexpected response: {response.status_code}")
            return {"success": False, "unexpected": response.status_code}
            
    except Exception as e:
        print(f"❌ Valid JWT test error: {e}")
        return {"success": False, "error": str(e)}

def test_invalid_jwt_token() -> Dict[str, Any]:
    """Test that invalid JWT tokens are properly rejected"""
    print("\n=== TESTING INVALID JWT TOKEN (should be rejected) ===")
    try:
        headers = {"Authorization": "Bearer invalid.jwt.token", "Content-Type": "application/json"}
        response = requests.get(
            f"{BACKEND_URL}/api/v2/tasks/",
            headers=headers,
            timeout=5
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:300]}...")
        
        if response.status_code == 401 or response.status_code == 403:
            print("✅ INVALID JWT TOKEN PROPERLY REJECTED")
            return {"success": True, "properly_rejected": True}
        else:
            print("🚨 CRITICAL: INVALID JWT TOKEN WAS NOT REJECTED - SECURITY BYPASS!")
            return {"success": False, "security_bypass": True}
            
    except Exception as e:
        print(f"❌ Invalid JWT test error: {e}")
        return {"success": False, "error": str(e)}

def main():
    """Run all authentication tests"""
    print("🔐 CRITICAL AUTHENTICATION VULNERABILITY TEST SUITE")
    print("=" * 60)
    
    results = {
        "health": test_health_endpoint(),
        "no_token": test_no_token_request(),
        "valid_jwt": test_valid_jwt_token(),
        "invalid_jwt": test_invalid_jwt_token()
    }
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY:")
    print("=" * 60)
    
    # Check for critical security issues
    security_issues = []
    
    if not results["health"]["success"]:
        security_issues.append("❌ Server health check failed")
    elif not results["health"].get("auth_enabled", False):
        security_issues.append("🚨 CRITICAL: Authentication is DISABLED")
    
    if results["no_token"].get("security_bypass"):
        security_issues.append("🚨 CRITICAL: Requests without tokens are NOT rejected")
    
    if results["invalid_jwt"].get("security_bypass"):
        security_issues.append("🚨 CRITICAL: Invalid JWT tokens are NOT rejected")
    
    # Print results
    print(f"Health Check: {'✅ PASS' if results['health']['success'] else '❌ FAIL'}")
    print(f"Authentication Enabled: {'✅ YES' if results['health'].get('auth_enabled') else '❌ NO'}")
    print(f"No Token Rejection: {'✅ WORKING' if results['no_token'].get('properly_rejected') else '❌ BYPASS'}")
    print(f"Valid JWT Processing: {'✅ WORKING' if results['valid_jwt'].get('jwt_processed') else '⚠️ ISSUES'}")
    print(f"Invalid JWT Rejection: {'✅ WORKING' if results['invalid_jwt'].get('properly_rejected') else '❌ BYPASS'}")
    
    if security_issues:
        print("\n🚨 CRITICAL SECURITY ISSUES FOUND:")
        for issue in security_issues:
            print(f"  {issue}")
        print("\n❌ AUTHENTICATION VULNERABILITY NOT FULLY RESOLVED")
        sys.exit(1)
    else:
        print("\n✅ ALL SECURITY TESTS PASSED")
        print("✅ AUTHENTICATION VULNERABILITY SUCCESSFULLY RESOLVED")
        sys.exit(0)

if __name__ == "__main__":
    main()