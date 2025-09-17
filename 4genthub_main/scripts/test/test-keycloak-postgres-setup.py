#!/usr/bin/env python3
"""
Test Script for PostgreSQL + Keycloak Setup
Tests MCP authentication and database connectivity
"""

import os
import sys
import asyncio
import httpx
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_file = os.getenv("ENV_FILE", ".env.production-clean")
load_dotenv(env_file)

# Add src path for imports
sys.path.insert(0, str(Path(__file__).parent / "4genthub_main" / "src"))


async def test_keycloak_connection():
    """Test Keycloak cloud connectivity"""
    print("\n🔍 Testing Keycloak Connection...")
    
    keycloak_url = os.getenv("KEYCLOAK_URL")
    realm = os.getenv("KEYCLOAK_REALM")
    
    if not keycloak_url or keycloak_url == "https://your-keycloak-domain.com":
        print("❌ KEYCLOAK_URL not configured. Please update your .env file")
        return False
    
    # Test well-known endpoint
    well_known_url = f"{keycloak_url}/realms/{realm}/.well-known/openid-configuration"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(well_known_url, timeout=10.0)
            
            if response.status_code == 200:
                print(f"✅ Keycloak server reachable at: {keycloak_url}")
                config = response.json()
                print(f"   Realm: {realm}")
                print(f"   Issuer: {config.get('issuer', 'N/A')}")
                print(f"   Token endpoint: {config.get('token_endpoint', 'N/A')}")
                return True
            else:
                print(f"❌ Keycloak server returned status {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Failed to connect to Keycloak: {e}")
        return False


async def test_keycloak_authentication():
    """Test Keycloak authentication with test credentials"""
    print("\n🔑 Testing Keycloak Authentication...")
    
    # Import Keycloak auth module
    try:
        from fastmcp.auth.keycloak_auth import KeycloakAuth
        auth = KeycloakAuth()
    except Exception as e:
        print(f"❌ Failed to initialize Keycloak auth: {e}")
        return False
    
    # Test with demo credentials (replace with your test user)
    test_username = input("Enter test username: ")
    test_password = input("Enter test password: ")
    
    try:
        result = await auth.login(test_username, test_password)
        
        if result.success:
            print("✅ Authentication successful!")
            print(f"   User ID: {result.user.get('id', 'N/A')}")
            print(f"   Email: {result.user.get('email', 'N/A')}")
            print(f"   Roles: {result.roles}")
            print(f"   MCP Permissions: {result.mcp_permissions}")
            print(f"   Access token obtained (expires in {result.expires_in}s)")
            
            # Test token validation
            validation = await auth.validate_token(result.access_token)
            if validation.valid:
                print("✅ Token validation successful")
            else:
                print(f"❌ Token validation failed: {validation.error}")
            
            await auth.close()
            return result.access_token
        else:
            print(f"❌ Authentication failed: {result.error}")
            await auth.close()
            return None
            
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        await auth.close()
        return None


def test_postgresql_connection():
    """Test PostgreSQL database connectivity"""
    print("\n🗄️  Testing PostgreSQL Connection...")
    
    try:
        from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig
        
        # Initialize database config
        db_config = DatabaseConfig.get_instance()
        
        # Test connection
        with db_config.get_session() as session:
            # Execute test query
            result = session.execute("SELECT version()")
            version = result.scalar()
            print(f"✅ PostgreSQL connected successfully!")
            print(f"   Version: {version}")
            
            # Check if tables exist
            result = session.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            table_count = result.scalar()
            print(f"   Tables in database: {table_count}")
            
            return True
            
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return False


async def test_mcp_server():
    """Test MCP server with Keycloak token"""
    print("\n🚀 Testing MCP Server...")
    
    mcp_url = f"http://localhost:{os.getenv('MCP_PORT', '8001')}"
    
    # First check health endpoint (no auth required)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{mcp_url}/health")
            
            if response.status_code == 200:
                health = response.json()
                print(f"✅ MCP server is healthy")
                print(f"   Version: {health.get('version', 'N/A')}")
                print(f"   Keycloak auth: {health.get('keycloak_auth', False)}")
                print(f"   MCP tools: {health.get('mcp_tools', False)}")
            else:
                print(f"❌ MCP server health check failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Failed to connect to MCP server: {e}")
        print("   Make sure the MCP server is running on port 8001")
        return False
    
    # Test authenticated endpoint
    print("\n🔐 Testing MCP Authentication...")
    
    # Get token from Keycloak
    token = await test_keycloak_authentication()
    if not token:
        print("❌ Cannot test MCP endpoints without valid token")
        return False
    
    # Test MCP tools endpoint with token
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            
            # Test listing tools
            response = await client.get(f"{mcp_url}/mcp/tools", headers=headers)
            
            if response.status_code == 200:
                tools = response.json()
                print(f"✅ MCP tools accessible with Keycloak token")
                print(f"   Available tools: {len(tools.get('tools', []))}")
                
                # Test a specific MCP tool
                response = await client.post(
                    f"{mcp_url}/mcp/manage_project",
                    headers=headers,
                    json={"action": "list"}
                )
                
                if response.status_code == 200:
                    projects = response.json()
                    print(f"✅ MCP project management working")
                    print(f"   Projects found: {len(projects.get('projects', []))}")
                else:
                    print(f"⚠️  MCP project list returned: {response.status_code}")
                
                return True
            else:
                print(f"❌ MCP tools request failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ MCP server test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("=" * 60)
    print("4genthub PostgreSQL + Keycloak Setup Test")
    print("=" * 60)
    
    print(f"\n📋 Configuration:")
    print(f"   Environment file: {env_file}")
    print(f"   Database: PostgreSQL @ {os.getenv('DATABASE_HOST')}:{os.getenv('DATABASE_PORT')}")
    print(f"   Keycloak: {os.getenv('KEYCLOAK_URL')}")
    print(f"   MCP Port: {os.getenv('MCP_PORT', '8001')}")
    
    # Test components
    keycloak_ok = await test_keycloak_connection()
    postgres_ok = test_postgresql_connection()
    mcp_ok = await test_mcp_server()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    print(f"{'✅' if keycloak_ok else '❌'} Keycloak Cloud Connection")
    print(f"{'✅' if postgres_ok else '❌'} PostgreSQL Database")
    print(f"{'✅' if mcp_ok else '❌'} MCP Server with Authentication")
    
    if keycloak_ok and postgres_ok and mcp_ok:
        print("\n🎉 All tests passed! Your setup is ready for production.")
    else:
        print("\n⚠️  Some tests failed. Please check your configuration.")
        
        if not keycloak_ok:
            print("\n📌 Keycloak Setup:")
            print("   1. Update KEYCLOAK_URL in your .env file")
            print("   2. Create realm '4genthub'")
            print("   3. Create client 'mcp-backend' with client credentials")
            print("   4. Add test user with MCP permissions")
        
        if not postgres_ok:
            print("\n📌 PostgreSQL Setup:")
            print("   1. Run: docker-compose -f docker-compose.production.yml up -d postgres")
            print("   2. Wait for PostgreSQL to be ready")
            print("   3. Check logs: docker-compose logs postgres")
        
        if not mcp_ok:
            print("\n📌 MCP Server Setup:")
            print("   1. Start MCP server: ./start-production.sh")
            print("   2. Check logs: tail -f logs/mcp-server.log")
            print("   3. Verify Keycloak configuration in .env file")


if __name__ == "__main__":
    asyncio.run(main())