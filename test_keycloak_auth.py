#!/usr/bin/env python3
"""
Test Keycloak authentication directly
"""
import os
import sys
from pathlib import Path
import httpx
import asyncio

# Load environment
sys.path.append('agenthub_main/src')
from dotenv import load_dotenv

env_dev = Path('.env.dev')
if env_dev.exists():
    load_dotenv(env_dev, override=True)
    print('✓ Loaded .env.dev')

# Get configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET")

print(f"\n🔧 Configuration:")
print(f"  KEYCLOAK_URL: {KEYCLOAK_URL}")
print(f"  KEYCLOAK_REALM: {KEYCLOAK_REALM}")
print(f"  KEYCLOAK_CLIENT_ID: {KEYCLOAK_CLIENT_ID}")
print(f"  Has CLIENT_SECRET: {bool(KEYCLOAK_CLIENT_SECRET)}")

async def test_login(email, password):
    """Test login with Keycloak"""
    token_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"

    print(f"\n🔑 Testing login for: {email}")
    print(f"  Token URL: {token_url}")

    data = {
        "grant_type": "password",
        "client_id": KEYCLOAK_CLIENT_ID,
        "username": email,
        "password": password,
        "scope": "openid"
    }

    if KEYCLOAK_CLIENT_SECRET:
        data["client_secret"] = KEYCLOAK_CLIENT_SECRET

    try:
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            print(f"\n📤 Sending request...")
            response = await client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            print(f"📥 Response Status: {response.status_code}")

            if response.status_code == 200:
                token_data = response.json()
                print(f"✅ Login successful!")
                print(f"  Access Token (first 50 chars): {token_data.get('access_token', '')[:50]}...")
                print(f"  Token Type: {token_data.get('token_type')}")
                print(f"  Expires In: {token_data.get('expires_in')} seconds")
            else:
                print(f"❌ Login failed!")
                print(f"  Response: {response.text}")

                # Try to parse error
                try:
                    error_data = response.json()
                    print(f"  Error: {error_data.get('error')}")
                    print(f"  Description: {error_data.get('error_description')}")
                except:
                    pass

    except Exception as e:
        print(f"❌ Request failed: {str(e)}")

if __name__ == "__main__":
    # Get test credentials
    email = input("Enter email (or press Enter for test@example.com): ").strip() or "test@example.com"
    password = input("Enter password (or press Enter for 'test'): ").strip() or "test"

    # Run the test
    asyncio.run(test_login(email, password))