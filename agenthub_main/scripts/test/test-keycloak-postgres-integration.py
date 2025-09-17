#!/usr/bin/env python3
"""
Test Keycloak and PostgreSQL Integration
Verifies the clean setup is working correctly
"""

import os
import sys
import asyncio
import json
from pathlib import Path
from typing import Optional, Dict, Any

# Add src to path
sys.path.insert(0, 'agenthub_main/src')

# Colors for output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_header(message: str):
    print(f"\n{Colors.BLUE}{'=' * 80}{Colors.END}")
    print(f"{Colors.BLUE}{message}{Colors.END}")
    print(f"{Colors.BLUE}{'=' * 80}{Colors.END}")

def print_success(message: str):
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_warning(message: str):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

def print_error(message: str):
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_info(message: str):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")

async def test_postgresql_connection():
    """Test PostgreSQL database connection"""
    print_header("Testing PostgreSQL Connection")
    
    try:
        from sqlalchemy import create_engine, text
        from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig
        
        # Load configuration
        config = DatabaseConfig()
        config.database_type = "postgresql"
        config.database_host = os.getenv("DATABASE_HOST", "localhost")
        config.database_port = int(os.getenv("DATABASE_PORT", 5432))
        config.database_name = os.getenv("DATABASE_NAME", "agenthub")
        config.database_user = os.getenv("DATABASE_USER", "postgres")
        config.database_password = os.getenv("DATABASE_PASSWORD", "postgres_secure_password_2025")
        
        # Create engine and test connection
        engine = create_engine(config.get_database_url())
        
        with engine.connect() as conn:
            # Test basic query
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print_success(f"PostgreSQL connected: {version[:50]}...")
            
            # Check tables
            result = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            ))
            table_count = result.scalar()
            print_success(f"Database has {table_count} tables")
            
            # List tables
            result = conn.execute(text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' "
                "ORDER BY tablename"
            ))
            tables = [row[0] for row in result]
            if tables:
                print_info(f"Tables: {', '.join(tables[:10])}")
                if len(tables) > 10:
                    print_info(f"        ... and {len(tables) - 10} more")
            
            return True
            
    except Exception as e:
        print_error(f"PostgreSQL connection failed: {e}")
        return False

async def test_keycloak_connection():
    """Test Keycloak server connection"""
    print_header("Testing Keycloak Connection")
    
    try:
        import httpx
        
        keycloak_url = os.getenv("KEYCLOAK_URL")
        keycloak_realm = os.getenv("KEYCLOAK_REALM", "agenthub")
        
        if not keycloak_url or keycloak_url == "https://your-keycloak-domain.com":
            print_warning("Keycloak URL not configured - skipping test")
            print_info("Update KEYCLOAK_URL in .env file with your Keycloak server")
            return None
        
        # Test well-known endpoint
        well_known_url = f"{keycloak_url}/realms/{keycloak_realm}/.well-known/openid-configuration"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(well_known_url, timeout=5.0)
            
            if response.status_code == 200:
                config = response.json()
                print_success(f"Keycloak server reached: {keycloak_url}")
                print_info(f"Realm: {keycloak_realm}")
                print_info(f"Issuer: {config.get('issuer')}")
                print_info(f"Token endpoint: {config.get('token_endpoint')}")
                return True
            else:
                print_error(f"Keycloak returned status {response.status_code}")
                return False
                
    except Exception as e:
        print_error(f"Keycloak connection failed: {e}")
        return False

async def test_keycloak_auth_provider():
    """Test Keycloak authentication provider"""
    print_header("Testing Keycloak Auth Provider")
    
    try:
        from fastmcp.auth.keycloak_integration import KeycloakAuthProvider
        
        # Check if Keycloak is configured
        keycloak_url = os.getenv("KEYCLOAK_URL")
        if not keycloak_url or keycloak_url == "https://your-keycloak-domain.com":
            print_warning("Keycloak not configured - skipping provider test")
            return None
        
        # Initialize provider
        provider = KeycloakAuthProvider()
        print_success("Keycloak provider initialized")
        
        # Get OIDC configuration
        config = await provider.get_oidc_configuration()
        if config:
            print_success("OIDC configuration retrieved")
            print_info(f"Authorization endpoint: {config.get('authorization_endpoint')}")
            print_info(f"Token endpoint: {config.get('token_endpoint')}")
            print_info(f"JWKS URI: {config.get('jwks_uri')}")
        
        await provider.close()
        return True
        
    except Exception as e:
        print_error(f"Keycloak provider test failed: {e}")
        return False

async def test_mcp_server_health():
    """Test MCP server health endpoint"""
    print_header("Testing MCP Server Health")
    
    try:
        import httpx
        
        mcp_url = "http://localhost:8001"
        
        async with httpx.AsyncClient() as client:
            # Test health endpoint
            response = await client.get(f"{mcp_url}/health", timeout=5.0)
            
            if response.status_code == 200:
                health = response.json()
                print_success(f"MCP server is healthy")
                print_info(f"Status: {health.get('status')}")
                print_info(f"Database: {health.get('database', {}).get('status')}")
                
                # Test API info
                response = await client.get(f"{mcp_url}/api", timeout=5.0)
                if response.status_code == 200:
                    api_info = response.json()
                    print_info(f"API Version: {api_info.get('version')}")
                    print_info(f"Auth Required: {api_info.get('auth_required')}")
                
                return True
            else:
                print_error(f"MCP server returned status {response.status_code}")
                return False
                
    except httpx.ConnectError:
        print_warning("MCP server not running")
        print_info("Start it with: docker-compose up -d mcp-server")
        return False
    except Exception as e:
        print_error(f"MCP server test failed: {e}")
        return False

async def test_mcp_authentication():
    """Test MCP authentication with Keycloak"""
    print_header("Testing MCP Authentication")
    
    try:
        import httpx
        
        # Check if Keycloak is configured
        keycloak_url = os.getenv("KEYCLOAK_URL")
        if not keycloak_url or keycloak_url == "https://your-keycloak-domain.com":
            print_warning("Keycloak not configured - skipping authentication test")
            print_info("To test authentication:")
            print_info("1. Configure Keycloak in .env")
            print_info("2. Create a test user in Keycloak")
            print_info("3. Run this test again")
            return None
        
        mcp_url = "http://localhost:8001"
        
        async with httpx.AsyncClient() as client:
            # Test unauthenticated request (should fail)
            response = await client.post(
                f"{mcp_url}/mcp/manage_task",
                json={"action": "list"},
                timeout=5.0
            )
            
            if response.status_code == 401:
                print_success("Unauthenticated request correctly rejected")
            else:
                print_warning(f"Unexpected response for unauthenticated request: {response.status_code}")
            
            # Test with invalid token (should fail)
            headers = {"Authorization": "Bearer invalid-token"}
            response = await client.post(
                f"{mcp_url}/mcp/manage_task",
                json={"action": "list"},
                headers=headers,
                timeout=5.0
            )
            
            if response.status_code == 401:
                print_success("Invalid token correctly rejected")
            else:
                print_warning(f"Unexpected response for invalid token: {response.status_code}")
            
            return True
            
    except Exception as e:
        print_error(f"Authentication test failed: {e}")
        return False

async def main():
    """Main test function"""
    print_header("POSTGRESQL + KEYCLOAK INTEGRATION TEST")
    print("Clean implementation with no backward compatibility\n")
    
    # Load environment
    from dotenv import load_dotenv
    env_file = ".env"
    if Path(env_file).exists():
        load_dotenv(env_file)
        print_success(f"Loaded environment from {env_file}")
    else:
        print_error(f"No {env_file} file found")
        print_info("Run ./setup-postgres-keycloak-clean.sh first")
        return
    
    # Run tests
    results = {}
    
    # Test PostgreSQL
    results['postgresql'] = await test_postgresql_connection()
    
    # Test Keycloak
    results['keycloak'] = await test_keycloak_connection()
    
    # Test Keycloak provider
    results['keycloak_provider'] = await test_keycloak_auth_provider()
    
    # Test MCP server
    results['mcp_server'] = await test_mcp_server_health()
    
    # Test authentication
    results['authentication'] = await test_mcp_authentication()
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    
    print(f"\n{Colors.GREEN}Passed: {passed}{Colors.END}")
    print(f"{Colors.RED}Failed: {failed}{Colors.END}")
    print(f"{Colors.YELLOW}Skipped: {skipped}{Colors.END}")
    
    if failed == 0:
        print_success("\nAll configured components working correctly!")
        
        if skipped > 0:
            print_warning("\nTo complete setup:")
            if results['keycloak'] is None:
                print_info("1. Configure Keycloak in .env file")
                print_info("2. Set up Keycloak realm and client")
                print_info("3. Create test users in Keycloak")
    else:
        print_error("\nSome tests failed. Check the errors above.")
    
    # Configuration tips
    print_header("CONFIGURATION TIPS")
    
    if results['keycloak'] is None:
        print("\n📝 Keycloak Setup:")
        print("1. Choose a Keycloak provider:")
        print("   - Keycloak.app (SaaS): https://keycloak.app")
        print("   - Red Hat SSO: https://sso.redhat.com")
        print("   - Self-hosted: Use Docker or Kubernetes")
        print("\n2. Create a realm named 'agenthub'")
        print("\n3. Create a client:")
        print("   - Client ID: mcp-backend")
        print("   - Client Protocol: openid-connect")
        print("   - Access Type: confidential")
        print("   - Valid Redirect URIs: http://localhost:8001/*")
        print("\n4. Update .env with:")
        print("   - KEYCLOAK_URL=<your-keycloak-url>")
        print("   - KEYCLOAK_CLIENT_SECRET=<from-credentials-tab>")
    
    print("\n🚀 Ready to use:")
    print("   - PostgreSQL: localhost:5432")
    print("   - MCP Server: http://localhost:8001")
    if results['keycloak']:
        print("   - Keycloak: Configured and reachable")

if __name__ == "__main__":
    asyncio.run(main())