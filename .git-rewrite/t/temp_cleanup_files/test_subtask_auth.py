#!/usr/bin/env python3
"""
Test script to verify subtask authentication fix.
This script tests the enhanced dual JWT authentication for subtasks.
"""

import json
import requests
import os

def test_subtask_authentication():
    """Test subtask loading with different authentication methods."""
    
    mcp_url = "http://localhost:8000/mcp/"
    
    # Test data - using a task ID from the system
    test_task_id = "0e6a97e9-b9f7-48f7-bcaf-a57dfed2f5e6"  # From our earlier task list
    
    # Test 1: MCP request with local JWT token (if available)
    print("=" * 60)
    print("🔍 Testing subtask authentication with MCP endpoint")
    print("=" * 60)
    
    # Test payload for manage_subtask
    test_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "manage_subtask",
            "arguments": {
                "action": "list",
                "task_id": test_task_id
            }
        }
    }
    
    print(f"📋 Testing with task_id: {test_task_id}")
    print(f"🔧 MCP Request: {json.dumps(test_payload, indent=2)}")
    
    # Test with no authentication (should fail)
    print("\n🧪 Test 1: No authentication (should fail)")
    try:
        response = requests.post(
            mcp_url, 
            json=test_payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            },
            timeout=10
        )
        print(f"📊 Status: {response.status_code}")
        print(f"📦 Response: {response.text[:500]}...")
        
        if response.status_code == 401:
            print("✅ Expected 401 - authentication is working")
        else:
            print("❌ Unexpected status code")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
    
    # Test 2: With local JWT token (from environment)
    jwt_secret = os.getenv("JWT_SECRET_KEY", "dGhpcyBpcyBhIGR1bW15IGp3dCBzZWNyZXQgZm9yIGRldmVsb3BtZW50")
    if jwt_secret:
        print(f"\n🧪 Test 2: With local JWT secret")
        print(f"🔑 JWT Secret (first 20 chars): {jwt_secret[:20]}...")
        
        # Generate a test token using the local secret
        try:
            import jwt
            import time
            from datetime import datetime, timedelta, timezone
            
            # Create a test payload
            payload = {
                "sub": "test-user-id-123",
                "email": "test@example.com",
                "type": "access",
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
                "iss": "dhafnck-mcp"
            }
            
            token = jwt.encode(payload, jwt_secret, algorithm="HS256")
            print(f"🎟️ Generated test token (first 50 chars): {token[:50]}...")
            
            response = requests.post(
                mcp_url,
                json=test_payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "Authorization": f"Bearer {token}"
                },
                timeout=10
            )
            
            print(f"📊 Status: {response.status_code}")
            print(f"📦 Response: {response.text[:500]}...")
            
            if response.status_code == 200:
                print("✅ Local JWT authentication successful!")
                try:
                    result = response.json()
                    if result.get("result"):
                        print("✅ Subtask listing worked!")
                    else:
                        print("⚠️ Unexpected response format")
                except:
                    print("⚠️ Could not parse JSON response")
            else:
                print(f"❌ Local JWT authentication failed with status {response.status_code}")
                
        except ImportError:
            print("⚠️ PyJWT not available, skipping local JWT test")
        except Exception as e:
            print(f"❌ Local JWT test failed: {e}")
    
    # Test 3: With Supabase JWT token (if available)
    supabase_secret = os.getenv("SUPABASE_JWT_SECRET")
    if supabase_secret:
        print(f"\n🧪 Test 3: With Supabase JWT secret")
        print(f"🔑 Supabase Secret (first 20 chars): {supabase_secret[:20]}...")
        
        try:
            import jwt
            from datetime import datetime, timedelta, timezone
            
            # Create a Supabase-style payload
            payload = {
                "sub": "test-supabase-user-123",
                "email": "test@supabase.com",
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
                "iss": "supabase"
            }
            
            token = jwt.encode(payload, supabase_secret, algorithm="HS256")
            print(f"🎟️ Generated Supabase test token (first 50 chars): {token[:50]}...")
            
            response = requests.post(
                mcp_url,
                json=test_payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "Authorization": f"Bearer {token}"
                },
                timeout=10
            )
            
            print(f"📊 Status: {response.status_code}")
            print(f"📦 Response: {response.text[:500]}...")
            
            if response.status_code == 200:
                print("✅ Supabase JWT authentication successful!")
                try:
                    result = response.json()
                    if result.get("result"):
                        print("✅ Subtask listing with Supabase auth worked!")
                    else:
                        print("⚠️ Unexpected response format")
                except:
                    print("⚠️ Could not parse JSON response")
            else:
                print(f"❌ Supabase JWT authentication failed with status {response.status_code}")
                
        except Exception as e:
            print(f"❌ Supabase JWT test failed: {e}")
    else:
        print("\n⚠️ SUPABASE_JWT_SECRET not available, skipping Supabase test")
    
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print("The subtask authentication system should now:")
    print("  - ✅ Reject unauthenticated requests (401)")
    print("  - ✅ Accept valid local JWT tokens")  
    print("  - ✅ Accept valid Supabase JWT tokens")
    print("  - ✅ Use proper user context for subtask operations")
    print("=" * 60)

if __name__ == "__main__":
    test_subtask_authentication()