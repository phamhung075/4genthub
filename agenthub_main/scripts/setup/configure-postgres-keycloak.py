#!/usr/bin/env python3
"""
Configure and validate PostgreSQL Docker + Keycloak Cloud setup for agenthub.

This script:
1. Validates PostgreSQL Docker connection
2. Configures Keycloak cloud authentication
3. Tests MCP connection with Keycloak tokens
4. Validates the complete setup
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import httpx
from dotenv import load_dotenv
import psycopg2
from psycopg2 import OperationalError

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    logger.info(f"✅ Loaded environment from {env_path}")
else:
    logger.warning(f"⚠️  No .env file found at {env_path}")

class PostgresKeycloakConfigurator:
    """Configure and validate PostgreSQL + Keycloak setup"""
    
    def __init__(self):
        """Initialize configurator with environment settings"""
        # PostgreSQL settings
        self.db_host = os.getenv("DATABASE_HOST", "localhost")
        self.db_port = os.getenv("DATABASE_PORT", "5432")
        self.db_name = os.getenv("DATABASE_NAME", "agenthub_prod")
        self.db_user = os.getenv("DATABASE_USER", "agenthub_user")
        self.db_password = os.getenv("DATABASE_PASSWORD", "")
        
        # Keycloak settings
        self.keycloak_url = os.getenv("KEYCLOAK_URL", "")
        self.keycloak_realm = os.getenv("KEYCLOAK_REALM", "agenthub")
        self.keycloak_client_id = os.getenv("KEYCLOAK_CLIENT_ID", "mcp-backend")
        self.keycloak_client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET", "")
        
        # MCP settings
        self.mcp_host = os.getenv("MCP_HOST", "0.0.0.0")
        self.mcp_port = os.getenv("MCP_PORT", "8001")
        self.auth_enabled = os.getenv("AUTH_ENABLED", "true").lower() == "true"
    
    def validate_postgresql_connection(self) -> bool:
        """
        Validate PostgreSQL Docker connection
        
        Returns:
            bool: True if connection successful
        """
        logger.info("=" * 60)
        logger.info("VALIDATING POSTGRESQL CONNECTION")
        logger.info("=" * 60)
        
        try:
            # Build connection string
            conn_string = f"host={self.db_host} port={self.db_port} dbname={self.db_name} user={self.db_user} password={self.db_password}"
            
            logger.info(f"Connecting to PostgreSQL at {self.db_host}:{self.db_port}/{self.db_name}")
            
            # Attempt connection
            conn = psycopg2.connect(conn_string)
            cursor = conn.cursor()
            
            # Test query
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            logger.info(f"✅ PostgreSQL connected: {version}")
            
            # Check if required tables exist
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('tasks', 'projects', 'contexts', 'git_branches')
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            
            if tables:
                logger.info(f"✅ Found {len(tables)} MCP tables:")
                for table in tables:
                    logger.info(f"   - {table[0]}")
            else:
                logger.warning("⚠️  No MCP tables found. Run database initialization.")
            
            cursor.close()
            conn.close()
            
            return True
            
        except OperationalError as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            logger.info("\n📝 Troubleshooting steps:")
            logger.info("1. Ensure Docker is running: docker ps")
            logger.info("2. Start PostgreSQL: docker-compose up -d postgres")
            logger.info("3. Check container logs: docker logs agenthub-postgres")
            logger.info("4. Verify .env DATABASE_* settings")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return False
    
    async def validate_keycloak_connection(self) -> bool:
        """
        Validate Keycloak cloud connection
        
        Returns:
            bool: True if connection successful
        """
        logger.info("\n" + "=" * 60)
        logger.info("VALIDATING KEYCLOAK CONNECTION")
        logger.info("=" * 60)
        
        if not self.keycloak_url:
            logger.error("❌ KEYCLOAK_URL not configured in .env")
            return False
        
        if not self.keycloak_client_secret:
            logger.error("❌ KEYCLOAK_CLIENT_SECRET not configured in .env")
            return False
        
        try:
            # Build realm URL
            realm_url = f"{self.keycloak_url}/realms/{self.keycloak_realm}"
            logger.info(f"Testing Keycloak at: {realm_url}")
            
            async with httpx.AsyncClient(verify=False) as client:
                # Test realm endpoint
                response = await client.get(f"{realm_url}/.well-known/openid-configuration")
                
                if response.status_code == 200:
                    config = response.json()
                    logger.info(f"✅ Keycloak realm '{self.keycloak_realm}' is accessible")
                    logger.info(f"   Token endpoint: {config.get('token_endpoint')}")
                    logger.info(f"   JWKS URI: {config.get('jwks_uri')}")
                    
                    # Test client credentials
                    token_endpoint = config.get('token_endpoint')
                    if token_endpoint:
                        return await self._test_client_credentials(token_endpoint)
                    
                    return True
                else:
                    logger.error(f"❌ Keycloak realm not accessible: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Keycloak connection failed: {e}")
            logger.info("\n📝 Troubleshooting steps:")
            logger.info("1. Verify KEYCLOAK_URL is correct")
            logger.info("2. Check if Keycloak is running and accessible")
            logger.info("3. Verify realm name in KEYCLOAK_REALM")
            logger.info("4. Check network connectivity to Keycloak")
            return False
    
    async def _test_client_credentials(self, token_endpoint: str) -> bool:
        """Test Keycloak client credentials"""
        try:
            async with httpx.AsyncClient(verify=False) as client:
                data = {
                    "grant_type": "client_credentials",
                    "client_id": self.keycloak_client_id,
                    "client_secret": self.keycloak_client_secret
                }
                
                response = await client.post(
                    token_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code == 200:
                    tokens = response.json()
                    logger.info(f"✅ Client credentials valid")
                    logger.info(f"   Access token obtained (expires in {tokens.get('expires_in')}s)")
                    return True
                else:
                    error_data = response.json()
                    logger.error(f"❌ Client authentication failed: {error_data.get('error_description', 'Unknown error')}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Client credential test failed: {e}")
            return False
    
    async def test_mcp_authentication(self) -> bool:
        """
        Test MCP server authentication with Keycloak token
        
        Returns:
            bool: True if MCP accepts Keycloak tokens
        """
        logger.info("\n" + "=" * 60)
        logger.info("TESTING MCP AUTHENTICATION")
        logger.info("=" * 60)
        
        if not self.auth_enabled:
            logger.info("ℹ️  Authentication is disabled (AUTH_ENABLED=false)")
            return True
        
        try:
            # First get a token from Keycloak
            token = await self._get_test_token()
            if not token:
                logger.error("❌ Could not obtain test token from Keycloak")
                return False
            
            # Test MCP health endpoint with token
            mcp_url = f"http://localhost:{self.mcp_port}"
            
            async with httpx.AsyncClient() as client:
                # Test authenticated endpoint
                response = await client.get(
                    f"{mcp_url}/health",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ MCP server accepts Keycloak tokens")
                    health = response.json()
                    logger.info(f"   Status: {health.get('status')}")
                    logger.info(f"   Database: {health.get('database', {}).get('status')}")
                    logger.info(f"   Auth: {health.get('auth', {}).get('provider')}")
                    return True
                else:
                    logger.error(f"❌ MCP authentication failed: {response.status_code}")
                    return False
                    
        except httpx.ConnectError:
            logger.error(f"❌ Cannot connect to MCP server at localhost:{self.mcp_port}")
            logger.info("\n📝 Start MCP server:")
            logger.info("   docker-compose up -d mcp-server")
            logger.info("   or")
            logger.info("   python agenthub_main/src/mcp_http_server.py")
            return False
        except Exception as e:
            logger.error(f"❌ MCP authentication test failed: {e}")
            return False
    
    async def _get_test_token(self) -> Optional[str]:
        """Get a test token from Keycloak using client credentials"""
        try:
            realm_url = f"{self.keycloak_url}/realms/{self.keycloak_realm}"
            token_endpoint = f"{realm_url}/protocol/openid-connect/token"
            
            async with httpx.AsyncClient(verify=False) as client:
                data = {
                    "grant_type": "client_credentials",
                    "client_id": self.keycloak_client_id,
                    "client_secret": self.keycloak_client_secret,
                    "scope": "openid"
                }
                
                response = await client.post(
                    token_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code == 200:
                    tokens = response.json()
                    return tokens.get("access_token")
                    
        except Exception as e:
            logger.error(f"Failed to get test token: {e}")
        
        return None
    
    def generate_config_summary(self) -> None:
        """Generate configuration summary"""
        logger.info("\n" + "=" * 60)
        logger.info("CONFIGURATION SUMMARY")
        logger.info("=" * 60)
        
        logger.info("\n📦 PostgreSQL Docker:")
        logger.info(f"   Host: {self.db_host}")
        logger.info(f"   Port: {self.db_port}")
        logger.info(f"   Database: {self.db_name}")
        logger.info(f"   User: {self.db_user}")
        logger.info(f"   Password: {'*' * len(self.db_password) if self.db_password else '(not set)'}")
        
        logger.info("\n🔐 Keycloak Cloud:")
        logger.info(f"   URL: {self.keycloak_url or '(not set)'}")
        logger.info(f"   Realm: {self.keycloak_realm}")
        logger.info(f"   Client ID: {self.keycloak_client_id}")
        logger.info(f"   Client Secret: {'*' * 10 if self.keycloak_client_secret else '(not set)'}")
        
        logger.info("\n🚀 MCP Server:")
        logger.info(f"   Host: {self.mcp_host}")
        logger.info(f"   Port: {self.mcp_port}")
        logger.info(f"   Auth Enabled: {self.mcp_auth_enabled}")
    
    async def run_validation(self) -> bool:
        """
        Run complete validation
        
        Returns:
            bool: True if all validations pass
        """
        self.generate_config_summary()
        
        results = {
            "postgresql": False,
            "keycloak": False,
            "mcp_auth": False
        }
        
        # Validate PostgreSQL
        results["postgresql"] = self.validate_postgresql_connection()
        
        # Validate Keycloak
        results["keycloak"] = await self.validate_keycloak_connection()
        
        # Test MCP authentication
        if results["keycloak"]:
            results["mcp_auth"] = await self.test_mcp_authentication()
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("VALIDATION RESULTS")
        logger.info("=" * 60)
        
        for component, status in results.items():
            status_icon = "✅" if status else "❌"
            logger.info(f"{status_icon} {component.replace('_', ' ').title()}: {'PASSED' if status else 'FAILED'}")
        
        all_passed = all(results.values())
        
        if all_passed:
            logger.info("\n🎉 All validations passed! Your setup is ready.")
        else:
            logger.info("\n⚠️  Some validations failed. Please fix the issues above.")
        
        return all_passed

async def main():
    """Main entry point"""
    configurator = PostgresKeycloakConfigurator()
    
    try:
        success = await configurator.run_validation()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())