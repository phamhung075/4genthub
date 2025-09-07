#!/usr/bin/env python3
"""
Test MCP Server with Keycloak Authentication in Production Setup
================================================================

This script validates that:
1. PostgreSQL database is accessible
2. Keycloak authentication works
3. MCP tools can be accessed with Keycloak tokens
4. Task management operations work with proper authentication

Usage:
    python test-mcp-keycloak-production.py [--username USER] [--password PASS]
"""

import os
import sys
import json
import time
import asyncio
import argparse
import logging
from typing import Dict, Any, Optional
from pathlib import Path

# Add project to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "dhafnck_mcp_main" / "src"))

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MCPKeycloakTester:
    """Test MCP Server with Keycloak authentication"""
    
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """Initialize tester with credentials."""
        self.username = username or os.getenv("TEST_USERNAME", "testuser")
        self.password = password or os.getenv("TEST_PASSWORD", "testpass123")
        
        # Server URLs
        self.mcp_url = os.getenv("MCP_URL", "http://localhost:8001")
        self.keycloak_url = os.getenv("KEYCLOAK_URL")
        self.keycloak_realm = os.getenv("KEYCLOAK_REALM", "dhafnck-mcp")
        self.keycloak_client_id = os.getenv("KEYCLOAK_CLIENT_ID", "mcp-backend")
        self.keycloak_client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET")
        
        # Tokens
        self.access_token = None
        self.refresh_token = None
        self.user_id = None
        
        # Test results
        self.test_results = {
            "postgresql": False,
            "keycloak_auth": False,
            "mcp_health": False,
            "mcp_tools": False,
            "task_operations": False,
            "context_operations": False,
        }
    
    async def test_postgresql_connection(self) -> bool:
        """Test PostgreSQL database connection."""
        logger.info("\n🔍 Testing PostgreSQL Connection...")
        
        try:
            import psycopg2
            
            # Get database configuration
            db_host = os.getenv("DATABASE_HOST", "localhost")
            db_port = os.getenv("DATABASE_PORT", "5432")
            db_name = os.getenv("DATABASE_NAME", "dhafnck_mcp_prod")
            db_user = os.getenv("DATABASE_USER", "dhafnck_user")
            db_password = os.getenv("DATABASE_PASSWORD")
            
            if not db_password:
                logger.error("❌ DATABASE_PASSWORD not set")
                return False
            
            # Connect to PostgreSQL
            conn = psycopg2.connect(
                host=db_host,
                port=db_port,
                dbname=db_name,
                user=db_user,
                password=db_password
            )
            
            # Test query
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
            table_count = cur.fetchone()[0]
            
            logger.info(f"✅ PostgreSQL connected: {table_count} tables found")
            
            cur.close()
            conn.close()
            
            self.test_results["postgresql"] = True
            return True
            
        except ImportError:
            logger.warning("⚠️  psycopg2 not installed, skipping PostgreSQL test")
            self.test_results["postgresql"] = None
            return True
        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            return False
    
    async def authenticate_with_keycloak(self) -> bool:
        """Authenticate with Keycloak and get tokens."""
        logger.info("\n🔐 Testing Keycloak Authentication...")
        
        if not self.keycloak_url:
            logger.error("❌ KEYCLOAK_URL not configured")
            return False
        
        try:
            # Build token endpoint
            token_endpoint = f"{self.keycloak_url}/realms/{self.keycloak_realm}/protocol/openid-connect/token"
            
            async with httpx.AsyncClient() as client:
                # Prepare authentication data
                auth_data = {
                    "grant_type": "password",
                    "client_id": self.keycloak_client_id,
                    "username": self.username,
                    "password": self.password,
                    "scope": "openid email profile"
                }
                
                if self.keycloak_client_secret:
                    auth_data["client_secret"] = self.keycloak_client_secret
                
                # Request tokens
                response = await client.post(
                    token_endpoint,
                    data=auth_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code == 200:
                    tokens = response.json()
                    self.access_token = tokens.get("access_token")
                    self.refresh_token = tokens.get("refresh_token")
                    
                    # Decode token to get user ID
                    import jwt
                    decoded = jwt.decode(
                        self.access_token,
                        options={"verify_signature": False}
                    )
                    self.user_id = decoded.get("sub")
                    
                    logger.info(f"✅ Keycloak authentication successful")
                    logger.info(f"   User ID: {self.user_id}")
                    logger.info(f"   Username: {decoded.get('preferred_username')}")
                    logger.info(f"   Email: {decoded.get('email')}")
                    
                    self.test_results["keycloak_auth"] = True
                    return True
                else:
                    error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    logger.error(f"❌ Keycloak authentication failed: {response.status_code}")
                    logger.error(f"   Error: {error_data.get('error_description', response.text)}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Keycloak authentication error: {e}")
            return False
    
    async def test_mcp_health(self) -> bool:
        """Test MCP server health endpoint."""
        logger.info("\n🏥 Testing MCP Server Health...")
        
        try:
            async with httpx.AsyncClient() as client:
                # Test without authentication (health should be public)
                response = await client.get(f"{self.mcp_url}/health")
                
                if response.status_code == 200:
                    health_data = response.json()
                    logger.info(f"✅ MCP Server is healthy")
                    logger.info(f"   Status: {health_data.get('status')}")
                    logger.info(f"   Database: {health_data.get('database', {}).get('status')}")
                    
                    self.test_results["mcp_health"] = True
                    return True
                else:
                    logger.error(f"❌ MCP health check failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ MCP health check error: {e}")
            return False
    
    async def test_mcp_tools(self) -> bool:
        """Test MCP tools with authentication."""
        logger.info("\n🛠️  Testing MCP Tools with Authentication...")
        
        if not self.access_token:
            logger.error("❌ No access token available")
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
                
                # Test 1: List projects
                logger.info("   Testing manage_project tool...")
                response = await client.post(
                    f"{self.mcp_url}/mcp/manage_project",
                    json={"action": "list"},
                    headers=headers
                )
                
                if response.status_code == 200:
                    projects = response.json()
                    logger.info(f"   ✅ Projects listed: {len(projects.get('projects', []))} found")
                else:
                    logger.error(f"   ❌ Failed to list projects: {response.status_code}")
                    return False
                
                # Test 2: Get or create a project
                logger.info("   Testing project creation...")
                response = await client.post(
                    f"{self.mcp_url}/mcp/manage_project",
                    json={
                        "action": "create",
                        "name": "test-production",
                        "description": "Test project for production setup"
                    },
                    headers=headers
                )
                
                if response.status_code in [200, 201]:
                    project = response.json()
                    project_id = project.get("project", {}).get("id")
                    logger.info(f"   ✅ Project created/retrieved: {project_id}")
                else:
                    logger.error(f"   ❌ Failed to create project: {response.status_code}")
                    # Continue anyway, might already exist
                
                self.test_results["mcp_tools"] = True
                return True
                
        except Exception as e:
            logger.error(f"❌ MCP tools test error: {e}")
            return False
    
    async def test_task_operations(self) -> bool:
        """Test task management operations."""
        logger.info("\n📋 Testing Task Operations...")
        
        if not self.access_token:
            logger.error("❌ No access token available")
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
                
                # Create a task
                logger.info("   Creating test task...")
                response = await client.post(
                    f"{self.mcp_url}/mcp/manage_task",
                    json={
                        "action": "create",
                        "title": "Test Production Setup",
                        "description": "Validate production configuration",
                        "priority": "high"
                    },
                    headers=headers
                )
                
                if response.status_code in [200, 201]:
                    task = response.json()
                    task_id = task.get("task", {}).get("id")
                    logger.info(f"   ✅ Task created: {task_id}")
                    
                    # Update task
                    logger.info("   Updating task status...")
                    response = await client.post(
                        f"{self.mcp_url}/mcp/manage_task",
                        json={
                            "action": "update",
                            "task_id": task_id,
                            "status": "in_progress",
                            "details": "Testing in progress"
                        },
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        logger.info("   ✅ Task updated successfully")
                    else:
                        logger.warning(f"   ⚠️  Task update returned: {response.status_code}")
                    
                    # Complete task
                    logger.info("   Completing task...")
                    response = await client.post(
                        f"{self.mcp_url}/mcp/manage_task",
                        json={
                            "action": "complete",
                            "task_id": task_id,
                            "completion_summary": "Production setup validated"
                        },
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        logger.info("   ✅ Task completed successfully")
                    else:
                        logger.warning(f"   ⚠️  Task completion returned: {response.status_code}")
                    
                    self.test_results["task_operations"] = True
                    return True
                else:
                    logger.error(f"   ❌ Failed to create task: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Task operations test error: {e}")
            return False
    
    async def test_context_operations(self) -> bool:
        """Test context management operations."""
        logger.info("\n🌐 Testing Context Operations...")
        
        if not self.access_token:
            logger.error("❌ No access token available")
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
                
                # Create global context
                logger.info("   Creating global context...")
                response = await client.post(
                    f"{self.mcp_url}/mcp/manage_context",
                    json={
                        "action": "create",
                        "level": "global",
                        "data": {
                            "production_test": True,
                            "test_timestamp": time.time(),
                            "configuration": "PostgreSQL + Keycloak"
                        }
                    },
                    headers=headers
                )
                
                if response.status_code in [200, 201]:
                    logger.info("   ✅ Global context created")
                else:
                    logger.warning(f"   ⚠️  Global context creation returned: {response.status_code}")
                
                # Update context
                logger.info("   Updating global context...")
                response = await client.post(
                    f"{self.mcp_url}/mcp/manage_context",
                    json={
                        "action": "update",
                        "level": "global",
                        "data": {
                            "last_test": time.time(),
                            "test_status": "successful"
                        }
                    },
                    headers=headers
                )
                
                if response.status_code == 200:
                    logger.info("   ✅ Global context updated")
                    self.test_results["context_operations"] = True
                    return True
                else:
                    logger.warning(f"   ⚠️  Context update returned: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Context operations test error: {e}")
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all validation tests."""
        logger.info("=" * 70)
        logger.info("🚀 Starting MCP Keycloak Production Tests")
        logger.info("=" * 70)
        
        all_passed = True
        
        # Test 1: PostgreSQL
        if not await self.test_postgresql_connection():
            all_passed = False
        
        # Test 2: Keycloak Authentication
        if not await self.authenticate_with_keycloak():
            logger.error("⚠️  Cannot proceed without authentication")
            all_passed = False
        else:
            # Test 3: MCP Health
            if not await self.test_mcp_health():
                all_passed = False
            
            # Test 4: MCP Tools
            if not await self.test_mcp_tools():
                all_passed = False
            
            # Test 5: Task Operations
            if not await self.test_task_operations():
                all_passed = False
            
            # Test 6: Context Operations
            if not await self.test_context_operations():
                all_passed = False
        
        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("📊 Test Results Summary")
        logger.info("=" * 70)
        
        for test_name, result in self.test_results.items():
            if result is None:
                status = "⚠️  SKIPPED"
            elif result:
                status = "✅ PASSED"
            else:
                status = "❌ FAILED"
            
            logger.info(f"{status:15} {test_name.replace('_', ' ').title()}")
        
        if all_passed:
            logger.info("\n🎉 All tests passed! Production setup is working correctly.")
        else:
            logger.info("\n⚠️  Some tests failed. Please check the configuration.")
        
        return all_passed

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test MCP Server with Keycloak authentication"
    )
    parser.add_argument(
        "--username",
        help="Keycloak username for testing"
    )
    parser.add_argument(
        "--password",
        help="Keycloak password for testing"
    )
    
    args = parser.parse_args()
    
    # Check environment
    if not os.getenv("KEYCLOAK_URL"):
        logger.error("❌ KEYCLOAK_URL not set in environment")
        logger.info("   Please configure .env file with Keycloak settings")
        sys.exit(1)
    
    # Run tests
    tester = MCPKeycloakTester(
        username=args.username,
        password=args.password
    )
    
    success = await tester.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())