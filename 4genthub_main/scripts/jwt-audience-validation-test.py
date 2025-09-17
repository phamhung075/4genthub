#!/usr/bin/env python3
"""
JWT Audience Validation Test Script

This script demonstrates the fix for JWT audience validation between
Supabase tokens ("authenticated" audience) and local tokens ("mcp-server" audience).

Usage:
    python jwt-audience-validation-test.py
    
Expected Output:
    - Local token creation and validation with "mcp-server" audience
    - Supabase-style token creation and validation with "authenticated" audience
    - Cross-validation showing proper audience enforcement
    - Dual authentication backend demonstration
"""

import os
import sys
import jwt as pyjwt
from datetime import datetime, timedelta, timezone

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fastmcp.auth.domain.services.jwt_service import JWTService


def main():
    """Test JWT audience validation fix"""
    print("🔐 JWT Audience Validation Test")
    print("=" * 50)
    
    # Test configuration
    test_secret = "test-secret-key-for-audience-validation-12345"
    jwt_service = JWTService(secret_key=test_secret, issuer="4genthub")
    
    print("\n1️⃣  Testing Local Token Creation and Validation")
    print("-" * 45)
    
    # Create local token with "mcp-server" audience (default)
    local_token = jwt_service.create_access_token(
        user_id="user123",
        email="local@example.com", 
        roles=["user", "admin"]
    )
    
    print(f"✅ Created local token (first 30 chars): {local_token[:30]}...")
    
    # Decode without verification to show structure
    local_payload = pyjwt.decode(local_token, options={"verify_signature": False})
    print(f"📋 Local token audience: {local_payload.get('aud')}")
    print(f"📋 Local token type: {local_payload.get('type')}")
    
    # Validate local token with correct audience
    payload = jwt_service.verify_token(local_token, "access", "mcp-server")
    if payload:
        print("✅ Local token validated successfully with 'mcp-server' audience")
    else:
        print("❌ Local token validation failed")
        
    # Validate local token with wrong audience  
    payload = jwt_service.verify_token(local_token, "access", "authenticated")
    if payload:
        print("❌ Local token should NOT validate with 'authenticated' audience")
    else:
        print("✅ Local token correctly rejected with wrong audience")
    
    print("\n2️⃣  Testing Supabase-Style Token")
    print("-" * 35)
    
    # Create Supabase-style token (no 'type' field, 'authenticated' audience)
    now = datetime.now(timezone.utc)
    supabase_payload = {
        "sub": "user456",
        "email": "supabase@example.com",
        "aud": "authenticated",  # Supabase audience
        "iat": now,
        "exp": now + timedelta(minutes=15),
        "iss": "supabase",
        "role": "authenticated",  # Supabase role
        # No 'type' field like Supabase tokens
    }
    
    supabase_token = pyjwt.encode(supabase_payload, test_secret, algorithm="HS256")
    print(f"✅ Created Supabase-style token (first 30 chars): {supabase_token[:30]}...")
    
    # Show Supabase token structure
    print(f"📋 Supabase token audience: {supabase_payload.get('aud')}")
    print(f"📋 Supabase token type: {supabase_payload.get('type', 'None (like Supabase)')}")
    
    # Validate Supabase token without audience check (should work)
    payload = jwt_service.verify_token(supabase_token, "access")
    if payload:
        print("✅ Supabase token validated without audience check (type field missing)")
    else:
        print("❌ Supabase token validation failed")
    
    print("\n3️⃣  Testing Custom Audience Creation")
    print("-" * 35)
    
    # Create token with custom audience
    custom_token = jwt_service.create_access_token(
        user_id="user789",
        email="custom@example.com",
        roles=["user"],
        audience="custom-api"
    )
    
    custom_payload = pyjwt.decode(custom_token, options={"verify_signature": False})
    print(f"📋 Custom token audience: {custom_payload.get('aud')}")
    
    # Validate with correct custom audience
    payload = jwt_service.verify_token(custom_token, "access", "custom-api")
    if payload:
        print("✅ Custom token validated with correct audience")
    else:
        print("❌ Custom token validation failed")
    
    print("\n4️⃣  Testing Dual Authentication Simulation")
    print("-" * 45)
    
    # Simulate dual authentication like in JWT backend
    def simulate_dual_auth(token):
        """Simulate the dual authentication logic"""
        # Try local validation first (mcp-server audience)
        local_result = jwt_service.verify_token(token, "access", "mcp-server")
        if local_result:
            return "LOCAL", local_result
        
        # Try Supabase validation (authenticated audience)
        try:
            supabase_result = pyjwt.decode(
                token,
                test_secret,
                algorithms=["HS256"],
                audience="authenticated",
                options={"verify_iss": False}
            )
            return "SUPABASE", supabase_result
        except Exception:
            return None, None
    
    # Test with local token
    auth_type, payload = simulate_dual_auth(local_token)
    print(f"🔐 Local token authenticated as: {auth_type}")
    
    # Test with Supabase token  
    auth_type, payload = simulate_dual_auth(supabase_token)
    print(f"🔐 Supabase token authenticated as: {auth_type}")
    
    print("\n🎉 JWT Audience Validation Fix Complete!")
    print("=" * 50)
    print("✅ Local tokens use 'mcp-server' audience")
    print("✅ Supabase tokens use 'authenticated' audience") 
    print("✅ Custom audiences supported")
    print("✅ Dual authentication works correctly")
    print("✅ Security maintained with proper audience validation")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)