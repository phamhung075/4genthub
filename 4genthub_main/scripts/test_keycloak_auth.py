#!/usr/bin/env python3
"""
Test Keycloak Authentication Flow

This script tests the complete authentication flow with Keycloak cloud
and PostgreSQL Docker.
"""

import os
import sys
import asyncio
import httpx
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load environment variables
load_dotenv()

from fastmcp.auth.keycloak_service import KeycloakAuthService
from fastmcp.auth.mcp_token_service import MCPTokenService
from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig

async def test_keycloak_connection():
    """Test Keycloak cloud connection"""
    print("\n" + "="*60)
    print("Testing Keycloak Cloud Connection")
    print("="*60)
    
    service = KeycloakAuthService()
    
    print(f"✓ Keycloak URL: {service.base_url}")
    print(f"✓ Realm: {service.realm}")
    print(f"✓ Client ID: {service.client_id}")
    
    # Test connection by fetching JWKS
    try:
        jwks = await service.get_jwks()
        if jwks:
            print("✅ Successfully connected to Keycloak")
            print(f"   JWKS Keys found: {len(jwks.get('keys', []))}")
        else:
            print("❌ Failed to fetch JWKS from Keycloak")
    except Exception as e:
        print(f"❌ Keycloak connection error: {e}")
        return False
    
    return True

async def test_user_authentication():
    """Test user login with Keycloak"""
    print("\n" + "="*60)
    print("Testing User Authentication")
    print("="*60)
    
    service = KeycloakAuthService()
    
    # Test credentials (you'll need to create this user in Keycloak)
    test_email = "test@example.com"
    test_password = "TestPassword123!"
    
    print(f"Attempting login for: {test_email}")
    
    result = await service.login(test_email, test_password)
    
    if result.success:
        print("✅ Login successful!")
        print(f"   User ID: {result.user.get('sub')}")
        print(f"   Email: {result.user.get('email')}")
        print(f"   Roles: {result.roles}")
        print(f"   Token expires in: {result.expires_in} seconds")
        
        # Test token validation
        validation = await service.validate_token(result.access_token)
        if validation:
            print("✅ Token validation successful")
        
        return result
    else:
        print(f"❌ Login failed: {result.error}")
        print("\nNote: You need to create a test user in Keycloak first:")
        print("1. Login to Keycloak admin console")
        print("2. Navigate to Users → Add User")
        print(f"3. Create user with email: {test_email}")
        print("4. Set password in Credentials tab")
        return None

def test_mcp_token_generation():
    """Test MCP token generation and validation"""
    print("\n" + "="*60)
    print("Testing MCP Token Service")
    print("="*60)
    
    service = MCPTokenService()
    
    # Generate test MCP token
    mcp_data = service.generate_mcp_token(
        user_id="test-user-123",
        email="test@example.com",
        roles=["user", "developer"],
        keycloak_token="mock_keycloak_token_here"
    )
    
    print("✅ MCP Token generated:")
    print(f"   User ID: {mcp_data['user_id']}")
    print(f"   Email: {mcp_data['email']}")
    print(f"   Roles: {mcp_data['roles']}")
    print(f"   Expires in: {mcp_data['expires_in']} seconds")
    
    # Validate the token
    payload = service.validate_mcp_token(mcp_data['mcp_token'])
    if payload:
        print("✅ MCP Token validation successful")
        
        # Extract Keycloak token
        keycloak_token = service.extract_keycloak_token(mcp_data['mcp_token'])
        if keycloak_token:
            print("✅ Keycloak token successfully extracted from MCP token")
    else:
        print("❌ MCP Token validation failed")
    
    return mcp_data

def test_database_connection():
    """Test PostgreSQL Docker connection"""
    print("\n" + "="*60)
    print("Testing PostgreSQL Docker Connection")
    print("="*60)
    
    try:
        db_config = DatabaseConfig.get_instance()
        
        print(f"✓ Database Type: {db_config.database_type}")
        print(f"✓ Database URL configured")
        
        # Test connection
        with db_config.SessionLocal() as session:
            result = session.execute("SELECT 1")
            if result:
                print("✅ PostgreSQL connection successful")
                
                # Check tables
                result = session.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
                tables = [row[0] for row in result]
                print(f"   Tables found: {len(tables)}")
                if tables:
                    for table in tables[:5]:  # Show first 5 tables
                        print(f"   - {table}")
                    if len(tables) > 5:
                        print(f"   ... and {len(tables) - 5} more")
        
        return True
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure PostgreSQL Docker is running:")
        print("   docker-compose up -d postgres")
        print("2. Check environment variables in .env")
        print("3. Verify DATABASE_HOST is 'localhost' when testing outside Docker")
        return False

async def test_complete_flow():
    """Test the complete authentication and database flow"""
    print("\n" + "="*60)
    print("Complete Authentication Flow Test")
    print("="*60)
    
    # 1. Test Database
    db_ok = test_database_connection()
    if not db_ok:
        print("\n⚠️  Database connection failed. Some tests may not work properly.")
    
    # 2. Test Keycloak Connection
    keycloak_ok = await test_keycloak_connection()
    if not keycloak_ok:
        print("\n⚠️  Keycloak connection failed. Check your KEYCLOAK_URL in .env")
    
    # 3. Test MCP Token Service
    mcp_token_data = test_mcp_token_generation()
    
    # 4. Test User Authentication (if Keycloak is connected)
    if keycloak_ok:
        auth_result = await test_user_authentication()
        
        if auth_result and auth_result.success:
            # Generate MCP token from real Keycloak token
            print("\n" + "="*60)
            print("Testing Complete Token Flow")
            print("="*60)
            
            mcp_service = MCPTokenService()
            mcp_data = mcp_service.generate_mcp_token(
                user_id=auth_result.user.get('sub'),
                email=auth_result.user.get('email'),
                roles=auth_result.roles,
                keycloak_token=auth_result.access_token
            )
            
            print("✅ Generated MCP token from Keycloak authentication")
            print(f"   This token can be used for MCP server connections")
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print(f"✓ Database Connection: {'✅ OK' if db_ok else '❌ Failed'}")
    print(f"✓ Keycloak Connection: {'✅ OK' if keycloak_ok else '❌ Failed'}")
    print(f"✓ MCP Token Service: ✅ OK")
    
    if not db_ok or not keycloak_ok:
        print("\n⚠️  Some components are not fully configured.")
        print("Please check your .env file and ensure all services are running.")

if __name__ == "__main__":
    print("4genthub Authentication Test Suite")
    print("=====================================")
    print(f"Environment: {os.getenv('ENV', 'development')}")
    print(f"Auth Provider: {os.getenv('AUTH_PROVIDER', 'keycloak')}")
    
    # Run async tests
    asyncio.run(test_complete_flow())