#!/usr/bin/env python3
"""
Test Keycloak Authentication for MCP API Client
Tests both password grant and client credentials grant flows
"""

import requests
import json
import sys
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from environment
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "https://keycloak.92.5.226.7.nip.io")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "mcp")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "mcp-api")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "AuJ07QpbXdSdHxfIhyjnNI6VVRx1sd7P")

# Token endpoint
TOKEN_ENDPOINT = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"


def test_client_credentials() -> Optional[Dict[str, Any]]:
    """Test client credentials grant (service account)"""
    print("\n🔐 Testing Client Credentials Grant (Service Account)...")
    print(f"   URL: {TOKEN_ENDPOINT}")

    data = {
        "grant_type": "client_credentials",
        "client_id": KEYCLOAK_CLIENT_ID,
        "client_secret": KEYCLOAK_CLIENT_SECRET
    }

    try:
        response = requests.post(TOKEN_ENDPOINT, data=data, verify=False)

        if response.status_code == 200:
            token_data = response.json()
            print("   ✅ SUCCESS: Service account token obtained")
            print(f"   Access Token (first 50 chars): {token_data['access_token'][:50]}...")
            print(f"   Token Type: {token_data['token_type']}")
            print(f"   Expires In: {token_data['expires_in']} seconds")
            return token_data
        else:
            print(f"   ❌ FAILED: Status {response.status_code}")
            print(f"   Error: {response.text}")
            return None

    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
        return None


def test_password_grant(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Test password grant (user credentials)"""
    print(f"\n🔐 Testing Password Grant for user: {username}")
    print(f"   URL: {TOKEN_ENDPOINT}")

    data = {
        "grant_type": "password",
        "client_id": KEYCLOAK_CLIENT_ID,
        "client_secret": KEYCLOAK_CLIENT_SECRET,
        "username": username,
        "password": password
    }

    try:
        response = requests.post(TOKEN_ENDPOINT, data=data, verify=False)

        if response.status_code == 200:
            token_data = response.json()
            print("   ✅ SUCCESS: User token obtained")
            print(f"   Access Token (first 50 chars): {token_data['access_token'][:50]}...")
            print(f"   Refresh Token (first 50 chars): {token_data['refresh_token'][:50]}...")
            print(f"   Token Type: {token_data['token_type']}")
            print(f"   Expires In: {token_data['expires_in']} seconds")
            return token_data
        else:
            print(f"   ❌ FAILED: Status {response.status_code}")
            print(f"   Error: {response.text}")
            return None

    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
        return None


def test_token_introspection(token: str) -> Optional[Dict[str, Any]]:
    """Test token introspection"""
    print("\n🔍 Testing Token Introspection...")
    introspect_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token/introspect"

    data = {
        "token": token,
        "client_id": KEYCLOAK_CLIENT_ID,
        "client_secret": KEYCLOAK_CLIENT_SECRET
    }

    try:
        response = requests.post(introspect_url, data=data, verify=False)

        if response.status_code == 200:
            introspection = response.json()
            print(f"   ✅ Token Active: {introspection.get('active', False)}")
            if introspection.get('active'):
                print(f"   Username: {introspection.get('username', 'N/A')}")
                print(f"   Client ID: {introspection.get('client_id', 'N/A')}")
                print(f"   Scope: {introspection.get('scope', 'N/A')}")
            return introspection
        else:
            print(f"   ❌ FAILED: Status {response.status_code}")
            return None

    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
        return None


def test_api_with_token(token: str):
    """Test calling the backend API with token"""
    print("\n🌐 Testing Backend API with Token...")
    api_url = "http://localhost:8000/api/health"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:
        response = requests.get(api_url, headers=headers)

        if response.status_code == 200:
            print(f"   ✅ API Call Successful")
            print(f"   Response: {response.json()}")
        else:
            print(f"   ❌ API Call Failed: Status {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"   ❌ ERROR calling API: {str(e)}")


def main():
    """Main test runner"""
    print("=" * 60)
    print("🚀 Keycloak Authentication Test Suite")
    print("=" * 60)
    print(f"Configuration:")
    print(f"  Keycloak URL: {KEYCLOAK_URL}")
    print(f"  Realm: {KEYCLOAK_REALM}")
    print(f"  Client ID: {KEYCLOAK_CLIENT_ID}")
    print("=" * 60)

    # Test 1: Client Credentials
    service_token = test_client_credentials()
    if service_token:
        # Test introspection
        test_token_introspection(service_token['access_token'])
        # Test API call
        test_api_with_token(service_token['access_token'])

    # Test 2: Password Grant (optional - requires user input)
    print("\n" + "=" * 60)
    test_user = input("Enter username to test password grant (or press Enter to skip): ")
    if test_user:
        test_pass = input("Enter password: ")
        user_token = test_password_grant(test_user, test_pass)
        if user_token:
            # Test introspection
            test_token_introspection(user_token['access_token'])
            # Test API call
            test_api_with_token(user_token['access_token'])

    print("\n" + "=" * 60)
    print("✅ Test Suite Complete")
    print("=" * 60)


if __name__ == "__main__":
    # Suppress SSL warnings for development
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    main()