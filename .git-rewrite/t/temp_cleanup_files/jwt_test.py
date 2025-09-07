#!/usr/bin/env python3
"""
Quick test to validate JWT emergency fix
Tests that JWT service can use JWT_SECRET_KEY from environment
"""

import os
import sys
sys.path.append('/home/daihungpham/agentic-project/dhafnck_mcp_main/src')

from fastmcp.auth.domain.services.jwt_service import JWTService


def test_jwt_emergency_fix():
    """Test that JWT service works with JWT_SECRET_KEY from environment"""
    
    print("🔍 Testing JWT Emergency Fix...")
    
    # 1. Check environment variable
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    print(f"✅ JWT_SECRET_KEY found: {jwt_secret[:10]}..." if jwt_secret else "❌ JWT_SECRET_KEY not found")
    
    if not jwt_secret:
        print("❌ CRITICAL: JWT_SECRET_KEY environment variable not set")
        return False
    
    try:
        # 2. Initialize JWT service
        jwt_service = JWTService(secret_key=jwt_secret)
        print("✅ JWT Service initialized successfully")
        
        # 3. Test token creation
        access_token = jwt_service.create_access_token(
            user_id="test_user_123",
            email="test@example.com",
            roles=["user"]
        )
        print(f"✅ Access token created: {access_token[:50]}...")
        
        # 4. Test token verification
        payload = jwt_service.verify_access_token(access_token)
        print(f"✅ Token verified successfully: user_id={payload.get('sub')}")
        
        # 5. Test refresh token creation
        refresh_token, family_id = jwt_service.create_refresh_token("test_user_123")
        print(f"✅ Refresh token created: {refresh_token[:50]}...")
        
        # 6. Test refresh token verification
        refresh_payload = jwt_service.verify_refresh_token(refresh_token)
        print(f"✅ Refresh token verified: user_id={refresh_payload.get('sub')}")
        
        print("\n🎉 JWT EMERGENCY FIX VALIDATION: SUCCESS")
        print("   - JWT_SECRET_KEY is correctly loaded from environment")
        print("   - JWT service can create and verify tokens")
        print("   - All JWT operations working properly")
        
        return True
        
    except Exception as e:
        print(f"❌ JWT test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_jwt_emergency_fix()
    sys.exit(0 if success else 1)