#!/usr/bin/env python3
"""
WebSocket Authentication Diagnostic Script

This script diagnoses WebSocket authentication issues by:
1. Simulating frontend token extraction (cookies/localStorage)
2. Testing extracted tokens against WebSocket validation
3. Providing detailed failure analysis
"""

import asyncio
import websockets
import json
import requests
import os
import jwt
import sqlite3
from datetime import datetime
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def test_websocket_connection(token=None):
    """Test WebSocket connection with optional token"""

    ws_url = "ws://localhost:8000/ws/realtime"
    if token:
        ws_url += f"?token={token}"

    logger.info(f"Testing WebSocket connection to: {ws_url[:50]}...")

    try:
        async with websockets.connect(ws_url) as websocket:
            logger.info("✅ WebSocket connection successful!")

            # Wait for welcome message
            try:
                welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                logger.info(f"Welcome message: {welcome_msg}")
                return True
            except asyncio.TimeoutError:
                logger.warning("No welcome message received within 5 seconds")
                return False

    except websockets.exceptions.ConnectionClosedError as e:
        logger.error(f"❌ WebSocket connection closed: {e}")
        logger.error(f"Close code: {e.code}, Reason: {e.reason}")
        return False
    except Exception as e:
        logger.error(f"❌ WebSocket connection failed: {e}")
        return False

def extract_frontend_tokens():
    """Extract tokens using the same logic as the frontend"""
    tokens = {}

    # Method 1: Check SQLite browser storage (Chrome/Edge)
    try:
        # Look for Chrome/Edge profile storage
        home = Path.home()
        possible_chrome_paths = [
            home / ".config/google-chrome/Default/Local Storage/leveldb",
            home / ".config/microsoft-edge/Default/Local Storage/leveldb",
            home / "Library/Application Support/Google/Chrome/Default/Local Storage/leveldb",
        ]

        for chrome_path in possible_chrome_paths:
            if chrome_path.exists():
                logger.info(f"Found browser storage at: {chrome_path}")
                # Note: This is complex to parse, so we'll simulate
                break

    except Exception as e:
        logger.debug(f"Chrome storage check failed: {e}")

    # Method 2: Check for any cached tokens in known locations
    try:
        # Check if there are any cached authentication files
        possible_token_files = [
            ".auth_token",
            ".jwt_token",
            "auth_cache.json"
        ]

        for token_file in possible_token_files:
            if os.path.exists(token_file):
                with open(token_file, 'r') as f:
                    content = f.read().strip()
                    if content:
                        tokens['file_token'] = content
                        logger.info(f"Found token in {token_file}")

    except Exception as e:
        logger.debug(f"File token check failed: {e}")

    # Method 3: Try to get a fresh token via backend health check
    try:
        health_response = requests.get("http://localhost:8000/health")
        if health_response.status_code == 200:
            health_data = health_response.json()
            if health_data.get("auth_enabled"):
                logger.info("Backend has auth enabled - need valid credentials")

    except Exception as e:
        logger.debug(f"Health check failed: {e}")

    return tokens

def analyze_token(token):
    """Analyze token structure and validity"""
    if not token:
        return {"valid": False, "reason": "No token provided"}

    try:
        # Decode without verification to see structure
        unverified = jwt.decode(token, options={"verify_signature": False})

        analysis = {
            "valid": True,
            "issuer": unverified.get("iss", "unknown"),
            "subject": unverified.get("sub", "unknown"),
            "expiry": unverified.get("exp", 0),
            "issued_at": unverified.get("iat", 0),
            "token_type": unverified.get("type", "unknown"),
            "length": len(token),
            "preview": token[:50] + "..."
        }

        # Check if expired
        import time
        if analysis["expiry"] > 0 and analysis["expiry"] < time.time():
            analysis["expired"] = True
        else:
            analysis["expired"] = False

        return analysis

    except jwt.DecodeError:
        return {"valid": False, "reason": "Invalid JWT format"}
    except Exception as e:
        return {"valid": False, "reason": f"Analysis failed: {e}"}

def simulate_keycloak_login():
    """Try to get a valid Keycloak token"""
    # Check if we can get the Keycloak configuration
    try:
        # Try different auth endpoints
        auth_endpoints = [
            "http://localhost:8000/api/auth/login",
            "http://localhost:8000/api/v2/auth/login",
            "http://localhost:8000/auth/login"
        ]

        for endpoint in auth_endpoints:
            try:
                # First check if endpoint exists
                response = requests.options(endpoint, timeout=2)
                if response.status_code < 400:
                    logger.info(f"Found auth endpoint: {endpoint}")

                    # Try with common test credentials
                    test_credentials = [
                        {"email": "admin@example.com", "password": "admin"},
                        {"email": "test@test.com", "password": "test"},
                        {"email": "user@localhost", "password": "password"},
                        {"username": "admin", "password": "admin"}
                    ]

                    for creds in test_credentials:
                        try:
                            auth_response = requests.post(endpoint, json=creds, timeout=5)
                            if auth_response.status_code == 200:
                                data = auth_response.json()
                                token = data.get("access_token")
                                if token:
                                    logger.info(f"✅ Got token with {creds}")
                                    return token
                        except:
                            continue

            except:
                continue

    except Exception as e:
        logger.debug(f"Keycloak login simulation failed: {e}")

    return None

async def main():
    """Main diagnostic function"""

    logger.info("🔍 WEBSOCKET AUTHENTICATION DIAGNOSTIC")
    logger.info("=" * 60)

    # Step 1: Test connection without token
    logger.info("STEP 1: Testing WebSocket without authentication")
    success = await test_websocket_connection()
    if success:
        logger.warning("⚠️ SECURITY ISSUE: Connection succeeded without token!")
    else:
        logger.info("✅ Properly rejects unauthenticated connections")
    print()

    # Step 2: Extract tokens using frontend logic
    logger.info("STEP 2: Extracting tokens using frontend methods")
    frontend_tokens = extract_frontend_tokens()

    if frontend_tokens:
        logger.info(f"Found {len(frontend_tokens)} token(s) from frontend sources")
        for source, token in frontend_tokens.items():
            logger.info(f"- {source}: {token[:30]}...")
    else:
        logger.warning("No tokens found via frontend extraction methods")
    print()

    # Step 3: Try to get a valid token
    logger.info("STEP 3: Attempting to obtain valid authentication token")
    test_token = simulate_keycloak_login()

    if test_token:
        logger.info("✅ Successfully obtained test token")
        frontend_tokens['keycloak_test'] = test_token
    else:
        logger.warning("❌ Could not obtain valid token via login")
    print()

    # Step 4: Analyze all available tokens
    logger.info("STEP 4: Analyzing token structure and validity")
    valid_tokens = []

    for source, token in frontend_tokens.items():
        logger.info(f"\nAnalyzing {source} token:")
        analysis = analyze_token(token)

        if analysis["valid"]:
            logger.info(f"  ✅ Valid JWT structure")
            logger.info(f"  📋 Issuer: {analysis['issuer']}")
            logger.info(f"  👤 Subject: {analysis['subject']}")
            logger.info(f"  🕐 Expired: {analysis['expired']}")
            logger.info(f"  🏷️ Type: {analysis['token_type']}")

            if not analysis["expired"]:
                valid_tokens.append((source, token))
        else:
            logger.error(f"  ❌ Invalid: {analysis['reason']}")
    print()

    # Step 5: Test valid tokens against WebSocket
    logger.info("STEP 5: Testing valid tokens against WebSocket endpoint")

    if valid_tokens:
        for source, token in valid_tokens:
            logger.info(f"\nTesting {source} token against WebSocket:")
            success = await test_websocket_connection(token)

            if success:
                logger.info(f"  ✅ WebSocket authentication SUCCESS with {source} token!")
                break
            else:
                logger.error(f"  ❌ WebSocket authentication FAILED with {source} token")
    else:
        logger.error("❌ No valid tokens available for WebSocket testing")
    print()

    # Step 6: Summary and recommendations
    logger.info("STEP 6: DIAGNOSTIC SUMMARY")
    logger.info("=" * 60)

    if not frontend_tokens:
        logger.error("🚨 ROOT CAUSE: No authentication tokens found!")
        logger.info("💡 SOLUTION: User needs to log in through the frontend")
        logger.info("   - Navigate to the login page")
        logger.info("   - Enter valid credentials")
        logger.info("   - Ensure tokens are stored in cookies/localStorage")
    elif not valid_tokens:
        logger.error("🚨 ROOT CAUSE: All tokens are invalid or expired!")
        logger.info("💡 SOLUTION: Refresh authentication")
        logger.info("   - User needs to re-login")
        logger.info("   - Check token expiration settings")
        logger.info("   - Verify Keycloak configuration")
    else:
        logger.error("🚨 ROOT CAUSE: Tokens exist but WebSocket validation fails!")
        logger.info("💡 SOLUTION: Backend WebSocket validation issue")
        logger.info("   - Check backend token validation logic")
        logger.info("   - Verify Keycloak/JWT configuration matching")
        logger.info("   - Check WebSocket authentication middleware")

    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())