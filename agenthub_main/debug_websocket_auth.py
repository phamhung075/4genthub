#!/usr/bin/env python3
"""
Emergency WebSocket authentication debugger
Tests token validation logic to identify the exact failure point
"""
import os
import sys
import asyncio
import jwt
from datetime import datetime, timezone

# Add the project path to sys.path
sys.path.insert(0, '/home/daihungpham/__projects__/4genthub/agenthub_main/src')

from fastmcp.auth.keycloak_dependencies import validate_local_token
from fastapi import HTTPException

async def test_token_validation():
    """Test WebSocket token validation with sample data"""

    print("🔍 EMERGENCY WebSocket Authentication Debugger")
    print("=" * 50)

    # Check environment variables
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    auth_provider = os.getenv("AUTH_PROVIDER")
    keycloak_url = os.getenv("KEYCLOAK_URL")

    print(f"✅ JWT_SECRET_KEY: {'Set' if jwt_secret else 'MISSING'}")
    print(f"✅ AUTH_PROVIDER: {auth_provider}")
    print(f"✅ KEYCLOAK_URL: {keycloak_url}")
    print()

    if not jwt_secret:
        print("❌ CRITICAL: JWT_SECRET_KEY not found in environment")
        return

    # Create a test token (simulate what frontend would generate)
    test_payload = {
        "sub": "test-user-123",
        "email": "test@example.com",
        "username": "testuser",
        "exp": int((datetime.now(timezone.utc).timestamp()) + 3600),  # 1 hour from now
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "type": "access"
    }

    try:
        # Generate test token using HS256 (same as local validation)
        test_token = jwt.encode(test_payload, jwt_secret, algorithm="HS256")
        print(f"✅ Generated test token: {test_token[:50]}...")
        print(f"✅ Token payload: {test_payload}")
        print()

        # Decode token to check structure
        print("🔍 Checking token structure...")
        try:
            decoded = jwt.decode(test_token, options={"verify_signature": False})
            issuer = decoded.get("iss", "")
            print(f"   Issuer field: '{issuer}' (empty = no issuer)")
            print(f"   Keycloak URL check: issuer.startswith('{keycloak_url}') = {issuer.startswith(keycloak_url) if keycloak_url else False}")
        except Exception as e:
            print(f"   Failed to decode: {e}")
        print()

        # Test local token validation
        print("🔍 Testing validate_local_token()...")
        try:
            user = validate_local_token(test_token)
            print(f"✅ SUCCESS: Token validated successfully!")
            print(f"   User ID: {user.id}")
            print(f"   Email: {user.email}")
            print(f"   Username: {user.username}")

        except HTTPException as e:
            print(f"❌ FAILURE: HTTPException - {e.detail}")
            print(f"   Status Code: {e.status_code}")

        except Exception as e:
            print(f"❌ FAILURE: {type(e).__name__} - {e}")

        # Test the complete WebSocket validation logic
        print("\n🔍 Testing complete WebSocket validation flow...")
        sys.path.append('/home/daihungpham/__projects__/4genthub/agenthub_main/src/fastmcp/server/routes')
        from websocket_routes import validate_websocket_token

        try:
            result = await validate_websocket_token(test_token)
            if result:
                print(f"✅ SUCCESS: WebSocket validation passed!")
                print(f"   User ID: {result.id}")
                print(f"   Email: {result.email}")
            else:
                print("❌ FAILURE: WebSocket validation returned None")
        except Exception as e:
            print(f"❌ FAILURE: WebSocket validation error - {e}")

    except Exception as e:
        print(f"❌ Failed to generate test token: {e}")

if __name__ == "__main__":
    # Load .env file
    from dotenv import load_dotenv
    load_dotenv('/home/daihungpham/__projects__/4genthub/.env')

    asyncio.run(test_token_validation())