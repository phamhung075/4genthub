#!/usr/bin/env python3
"""
Test Script for PostgreSQL Docker + Keycloak Cloud Setup
Verifies the clean setup without Supabase backward compatibility
"""

import os
import sys
import asyncio
import subprocess
from pathlib import Path

# Add project to path
sys.path.insert(0, 'dhafnck_mcp_main/src')

def check_environment():
    """Check if environment is properly configured"""
    print("=" * 60)
    print("Checking Environment Configuration")
    print("=" * 60)
    
    required_vars = [
        'DATABASE_TYPE',
        'DATABASE_HOST',
        'DATABASE_PORT',
        'DATABASE_NAME',
        'KEYCLOAK_URL',
        'KEYCLOAK_REALM',
        'KEYCLOAK_CLIENT_ID',
        'KEYCLOAK_CLIENT_SECRET'
    ]
    
    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Hide secrets
            if 'SECRET' in var or 'PASSWORD' in var:
                display_value = value[:4] + '***' + value[-4:] if len(value) > 8 else '***'
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: Not set")
            missing.append(var)
    
    if missing:
        print(f"\n⚠️  Missing environment variables: {', '.join(missing)}")
        print("Please configure these in your .env file")
        return False
    
    # Check for Supabase variables (should not exist)
    supabase_vars = ['SUPABASE_URL', 'SUPABASE_KEY', 'SUPABASE_DB_URL']
    found_supabase = []
    for var in supabase_vars:
        if os.getenv(var):
            found_supabase.append(var)
    
    if found_supabase:
        print(f"\n⚠️  Found Supabase variables (should be removed): {', '.join(found_supabase)}")
        print("These are no longer needed and should be removed from .env")
    else:
        print("\n✅ No Supabase variables found (good!)")
    
    return not missing

def check_docker_services():
    """Check if Docker services are running"""
    print("\n" + "=" * 60)
    print("Checking Docker Services")
    print("=" * 60)
    
    try:
        # Check if Docker is running
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Docker is not running")
            return False
        
        # Check for PostgreSQL container
        if 'postgres' in result.stdout or 'dhafnck-postgres' in result.stdout:
            print("✅ PostgreSQL container is running")
        else:
            print("❌ PostgreSQL container not found")
            print("   Run: docker-compose up -d postgres")
            return False
        
        # Check for MCP server (optional, might run locally)
        if 'mcp-server' in result.stdout or 'dhafnck-mcp' in result.stdout:
            print("✅ MCP server container is running")
        else:
            print("ℹ️  MCP server container not found (might be running locally)")
        
        return True
        
    except FileNotFoundError:
        print("❌ Docker not found. Please install Docker.")
        return False

def check_postgresql_connection():
    """Test PostgreSQL connection"""
    print("\n" + "=" * 60)
    print("Testing PostgreSQL Connection")
    print("=" * 60)
    
    try:
        from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig
        
        config = DatabaseConfig()
        print(f"Database Type: {config.database_type}")
        print(f"Database URL: {config.database_url[:30]}...")
        
        # Try to connect
        from sqlalchemy import create_engine, text
        engine = create_engine(config.database_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ Connected to PostgreSQL: {version}")
            
            # Check tables
            result = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            ))
            table_count = result.scalar()
            print(f"   Tables in database: {table_count}")
            
            return True
            
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return False

async def check_keycloak_connection():
    """Test Keycloak connection"""
    print("\n" + "=" * 60)
    print("Testing Keycloak Connection")
    print("=" * 60)
    
    keycloak_url = os.getenv("KEYCLOAK_URL")
    realm = os.getenv("KEYCLOAK_REALM")
    
    if not keycloak_url or not realm:
        print("❌ Keycloak configuration missing")
        return False
    
    try:
        import httpx
        
        # Test well-known endpoint
        well_known_url = f"{keycloak_url}/realms/{realm}/.well-known/openid-configuration"
        print(f"Testing: {well_known_url}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(well_known_url)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Keycloak realm accessible")
                print(f"   Issuer: {data.get('issuer')}")
                print(f"   Token endpoint: {data.get('token_endpoint')}")
                return True
            else:
                print(f"❌ Keycloak returned status {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Keycloak connection failed: {e}")
        print("   Make sure KEYCLOAK_URL is correct and accessible")
        return False

def check_code_cleanliness():
    """Check if Supabase references have been removed"""
    print("\n" + "=" * 60)
    print("Checking Code Cleanliness")
    print("=" * 60)
    
    # Check key files for Supabase references
    files_to_check = [
        'dhafnck_mcp_main/src/fastmcp/server/http_server.py',
        'dhafnck_mcp_main/src/fastmcp/server/mcp_entry_point.py',
        'dhafnck_mcp_main/src/fastmcp/task_management/infrastructure/database/database_config.py'
    ]
    
    found_references = False
    for file_path in files_to_check:
        path = Path(file_path)
        if path.exists():
            content = path.read_text()
            if 'supabase' in content.lower():
                print(f"⚠️  Found Supabase reference in {file_path}")
                found_references = True
    
    if not found_references:
        print("✅ No Supabase references found in key files")
    else:
        print("\n⚠️  Supabase references still exist")
        print("   Run: python3 cleanup-supabase-references.py")
    
    return not found_references

async def test_mcp_health():
    """Test MCP server health endpoint"""
    print("\n" + "=" * 60)
    print("Testing MCP Server Health")
    print("=" * 60)
    
    try:
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8001/health")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ MCP Server is healthy")
                print(f"   Status: {data.get('status')}")
                print(f"   Auth enabled: {data.get('auth_enabled')}")
                print(f"   Auth provider: {data.get('auth_provider')}")
                print(f"   Database: {data.get('database')}")
                
                # Check for correct configuration
                if data.get('auth_provider') == 'keycloak':
                    print("   ✅ Using Keycloak authentication")
                else:
                    print(f"   ⚠️  Expected Keycloak, got {data.get('auth_provider')}")
                
                if data.get('database') == 'postgresql':
                    print("   ✅ Using PostgreSQL database")
                else:
                    print(f"   ⚠️  Expected PostgreSQL, got {data.get('database')}")
                
                return True
            else:
                print(f"❌ MCP Server returned status {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ MCP Server not accessible: {e}")
        print("   Make sure the server is running on port 8001")
        return False

async def main():
    """Run all tests"""
    print("=" * 60)
    print("PostgreSQL + Keycloak Clean Setup Test")
    print("=" * 60)
    
    results = {
        "Environment": check_environment(),
        "Docker Services": check_docker_services(),
        "PostgreSQL": check_postgresql_connection(),
        "Code Cleanliness": check_code_cleanliness(),
    }
    
    # Async tests
    results["Keycloak"] = await check_keycloak_connection()
    results["MCP Server"] = await test_mcp_health()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    all_passed = True
    for test, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test:20} : {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 All tests passed! Your setup is ready.")
        print("\nNext steps:")
        print("1. Test authentication: python3 test-keycloak-auth.py")
        print("2. Start frontend: cd dhafnck-frontend && npm start")
        print("3. Access the application at http://localhost:3800")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        print("\nTroubleshooting:")
        print("1. Check your .env file configuration")
        print("2. Ensure Docker services are running")
        print("3. Verify Keycloak is accessible and configured")
        print("4. Check logs: docker-compose logs -f")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)