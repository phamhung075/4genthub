#!/usr/bin/env python3
"""
Test Production Setup - PostgreSQL + Keycloak
Verifies that the system is properly configured for production
"""

import os
import sys
import json
import asyncio
import httpx
from typing import Dict, Any

# Add source path
sys.path.insert(0, '4genthub_main/src')

def check_environment():
    """Check environment configuration"""
    print("\n" + "=" * 60)
    print("1. ENVIRONMENT CONFIGURATION CHECK")
    print("=" * 60)
    
    required_vars = {
        "PostgreSQL": [
            "DATABASE_TYPE",
            "DATABASE_HOST", 
            "DATABASE_PORT",
            "DATABASE_NAME",
            "DATABASE_USER",
            "DATABASE_PASSWORD"
        ],
        "Keycloak": [
            "KEYCLOAK_URL",
            "KEYCLOAK_REALM",
            "KEYCLOAK_CLIENT_ID",
            "KEYCLOAK_CLIENT_SECRET"
        ],
        "MCP": [
            "MCP_HOST",
            "MCP_PORT",
            "JWT_SECRET_KEY",
            "AUTH_ENABLED",
            "AUTH_PROVIDER"
        ]
    }
    
    all_configured = True
    
    for category, vars in required_vars.items():
        print(f"\n{category} Configuration:")
        for var in vars:
            value = os.getenv(var)
            if value:
                # Mask sensitive values
                if "PASSWORD" in var or "SECRET" in var:
                    display = f"{value[:3]}...{value[-3:]}" if len(value) > 6 else "***"
                else:
                    display = value
                print(f"  ✅ {var}: {display}")
            else:
                print(f"  ❌ {var}: NOT SET")
                all_configured = False
    
    return all_configured


def test_postgresql_connection():
    """Test PostgreSQL database connection"""
    print("\n" + "=" * 60)
    print("2. POSTGRESQL CONNECTION TEST")
    print("=" * 60)
    
    try:
        from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig
        
        # Initialize database config
        db_config = DatabaseConfig()
        
        # Get database info
        db_info = db_config.get_database_info()
        print(f"Database Type: {db_info['type']}")
        print(f"Connection URL: {db_info['url'][:50]}..." if db_info['url'] else "N/A")
        
        # Test connection
        session = db_config.get_session()
        
        # Run test query
        from sqlalchemy import text
        result = session.execute(text("SELECT current_database(), version()"))
        db_name, version = result.fetchone()
        
        print(f"✅ Connected to PostgreSQL!")
        print(f"   Database: {db_name}")
        print(f"   Version: {version[:50]}...")
        
        # Check tables
        result = session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]
        
        print(f"   Tables: {len(tables)} found")
        if tables:
            for table in tables[:10]:  # Show first 10 tables
                print(f"     - {table}")
            if len(tables) > 10:
                print(f"     ... and {len(tables) - 10} more")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return False


async def test_keycloak_connection():
    """Test Keycloak connection and authentication"""
    print("\n" + "=" * 60)
    print("3. KEYCLOAK CONNECTION TEST")
    print("=" * 60)
    
    keycloak_url = os.getenv("KEYCLOAK_URL")
    realm = os.getenv("KEYCLOAK_REALM")
    client_id = os.getenv("KEYCLOAK_CLIENT_ID")
    client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET")
    
    if not all([keycloak_url, realm, client_id, client_secret]):
        print("❌ Keycloak configuration incomplete")
        return False
    
    try:
        # Remove trailing slash
        keycloak_url = keycloak_url.rstrip("/")
        
        # Build well-known endpoint
        well_known_url = f"{keycloak_url}/realms/{realm}/.well-known/openid-configuration"
        
        print(f"Testing Keycloak at: {keycloak_url}")
        print(f"Realm: {realm}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test well-known endpoint
            print("\nChecking OpenID configuration...")
            response = await client.get(well_known_url)
            
            if response.status_code == 200:
                config = response.json()
                print("✅ Keycloak server reachable")
                print(f"   Issuer: {config.get('issuer')}")
                print(f"   Token endpoint: {config.get('token_endpoint')}")
                
                # Test client credentials
                print("\nTesting client credentials...")
                token_endpoint = config.get('token_endpoint')
                
                data = {
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret
                }
                
                response = await client.post(token_endpoint, data=data)
                
                if response.status_code == 200:
                    token_data = response.json()
                    print("✅ Client credentials valid")
                    print(f"   Access token received (expires in {token_data.get('expires_in')}s)")
                    return True
                else:
                    print(f"❌ Client authentication failed: {response.status_code}")
                    print(f"   Response: {response.text[:200]}")
                    return False
            else:
                print(f"❌ Cannot reach Keycloak server: {response.status_code}")
                return False
                
    except httpx.ConnectError:
        print(f"❌ Cannot connect to Keycloak at {keycloak_url}")
        print("   Please check the URL and network connectivity")
        return False
    except Exception as e:
        print(f"❌ Keycloak test failed: {e}")
        return False


async def test_mcp_server():
    """Test MCP server health"""
    print("\n" + "=" * 60)
    print("4. MCP SERVER HEALTH CHECK")
    print("=" * 60)
    
    mcp_port = os.getenv("MCP_PORT", "8001")
    mcp_url = f"http://localhost:{mcp_port}"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test health endpoint
            response = await client.get(f"{mcp_url}/health")
            
            if response.status_code == 200:
                health = response.json()
                print("✅ MCP Server is running")
                print(f"   Status: {health.get('status')}")
                print(f"   Database: {health.get('database', {}).get('status')}")
                print(f"   Auth enabled: {health.get('auth_enabled')}")
                
                # Test MCP tools endpoint
                response = await client.post(
                    f"{mcp_url}/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "method": "tools/list",
                        "params": {},
                        "id": 1
                    }
                )
                
                if response.status_code == 200:
                    tools = response.json()
                    if "result" in tools:
                        print(f"   MCP Tools: {len(tools['result'].get('tools', []))} available")
                    return True
                    
            else:
                print(f"❌ MCP Server not healthy: {response.status_code}")
                return False
                
    except httpx.ConnectError:
        print(f"❌ Cannot connect to MCP server at {mcp_url}")
        print("   Is the server running?")
        return False
    except Exception as e:
        print(f"❌ MCP server test failed: {e}")
        return False


async def test_mcp_with_keycloak():
    """Test MCP authentication with Keycloak token"""
    print("\n" + "=" * 60)
    print("5. MCP + KEYCLOAK INTEGRATION TEST")
    print("=" * 60)
    
    if os.getenv("AUTH_ENABLED", "false").lower() != "true":
        print("⚠️  Authentication is disabled (AUTH_ENABLED != true)")
        return True  # Not a failure if auth is intentionally disabled
    
    try:
        from fastmcp.auth.keycloak_auth import KeycloakAuth
        
        # Initialize Keycloak auth
        auth = KeycloakAuth()
        
        # Get a token using client credentials
        keycloak_url = os.getenv("KEYCLOAK_URL", "").rstrip("/")
        realm = os.getenv("KEYCLOAK_REALM")
        client_id = os.getenv("KEYCLOAK_CLIENT_ID")
        client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET")
        
        token_endpoint = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/token"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get token
            response = await client.post(
                token_endpoint,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret
                }
            )
            
            if response.status_code != 200:
                print(f"❌ Failed to get Keycloak token: {response.status_code}")
                return False
            
            token_data = response.json()
            access_token = token_data.get("access_token")
            
            # Test MCP with token
            mcp_port = os.getenv("MCP_PORT", "8001")
            mcp_url = f"http://localhost:{mcp_port}"
            
            # Call MCP with authentication
            response = await client.post(
                f"{mcp_url}/mcp",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "params": {},
                    "id": 1
                }
            )
            
            if response.status_code == 200:
                print("✅ MCP accepted Keycloak token")
                result = response.json()
                if "result" in result:
                    print(f"   Authenticated request successful")
                    return True
            else:
                print(f"❌ MCP rejected token: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
                
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("4GENTHUBMCP PRODUCTION SETUP TEST")
    print("PostgreSQL (Docker) + Keycloak (Cloud)")
    print("=" * 60)
    
    # Load environment
    from dotenv import load_dotenv
    if os.path.exists('.env'):
        load_dotenv('.env')
        print("✅ Loaded .env file")
    else:
        print("⚠️  No .env file found - using system environment")
    
    results = {}
    
    # 1. Check environment
    results['environment'] = check_environment()
    
    # 2. Test PostgreSQL
    results['postgresql'] = test_postgresql_connection()
    
    # 3. Test Keycloak
    results['keycloak'] = await test_keycloak_connection()
    
    # 4. Test MCP Server
    results['mcp_server'] = await test_mcp_server()
    
    # 5. Test Integration
    if results['keycloak'] and results['mcp_server']:
        results['integration'] = await test_mcp_with_keycloak()
    else:
        results['integration'] = False
        print("\n⚠️  Skipping integration test (prerequisites not met)")
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test.upper()}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED - System ready for production!")
    else:
        print("❌ SOME TESTS FAILED - Please check configuration")
        print("\nTroubleshooting:")
        print("1. Ensure PostgreSQL is running: docker ps")
        print("2. Check .env file has correct Keycloak settings")
        print("3. Verify MCP server is running: docker-compose ps")
        print("4. Check logs: docker-compose logs")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)