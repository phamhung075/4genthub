#!/usr/bin/env python3
"""
Clean Authentication Setup Script
Sets up PostgreSQL Docker + Keycloak Cloud integration
Removes all backward compatibility code
"""

import os
import sys
import json
import logging
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import httpx
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AuthenticationSetup:
    """Clean authentication setup for PostgreSQL + Keycloak"""
    
    def __init__(self):
        """Initialize setup with environment configuration"""
        load_dotenv()
        self.project_root = Path(__file__).parent.parent.parent
        self.env_file = self.project_root / ".env"
        self.docker_compose_file = self.project_root / "docker-compose.yml"
        
    def check_prerequisites(self) -> bool:
        """Check if Docker and Docker Compose are installed"""
        try:
            # Check Docker
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Docker installed: {result.stdout.strip()}")
            
            # Check Docker Compose
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Docker Compose installed: {result.stdout.strip()}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Prerequisites check failed: {e}")
            return False
            
    def validate_keycloak_config(self) -> Dict[str, Any]:
        """Validate Keycloak configuration from environment"""
        required_vars = [
            "KEYCLOAK_URL",
            "KEYCLOAK_REALM",
            "KEYCLOAK_CLIENT_ID",
            "KEYCLOAK_CLIENT_SECRET"
        ]
        
        config = {}
        missing_vars = []
        
        for var in required_vars:
            value = os.getenv(var)
            if not value or value.startswith("your-") or value == "CHANGE THIS":
                missing_vars.append(var)
            else:
                config[var] = value
                
        if missing_vars:
            logger.error(f"Missing or invalid Keycloak configuration: {missing_vars}")
            logger.info("Please update your .env file with actual Keycloak cloud values")
            return {}
            
        logger.info("Keycloak configuration validated successfully")
        return config
        
    async def test_keycloak_connection(self, config: Dict[str, Any]) -> bool:
        """Test connection to Keycloak cloud instance"""
        try:
            keycloak_url = config["KEYCLOAK_URL"]
            realm = config["KEYCLOAK_REALM"]
            
            # Test realm endpoint
            realm_url = f"{keycloak_url}/realms/{realm}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    realm_url,
                    timeout=10.0,
                    follow_redirects=True
                )
                
                if response.status_code == 200:
                    logger.info(f"Successfully connected to Keycloak realm: {realm}")
                    realm_info = response.json()
                    logger.info(f"Realm name: {realm_info.get('realm')}")
                    return True
                else:
                    logger.error(f"Failed to connect to Keycloak: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Keycloak connection test failed: {e}")
            return False
            
    def setup_postgresql_docker(self) -> bool:
        """Setup PostgreSQL using Docker Compose"""
        try:
            logger.info("Starting PostgreSQL container...")
            
            # Stop any existing containers
            subprocess.run(
                ["docker-compose", "down"],
                cwd=self.project_root,
                capture_output=True,
                check=False
            )
            
            # Start PostgreSQL service
            result = subprocess.run(
                ["docker-compose", "up", "-d", "postgres"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info("PostgreSQL container started successfully")
            
            # Wait for PostgreSQL to be ready
            logger.info("Waiting for PostgreSQL to be ready...")
            for _ in range(30):
                result = subprocess.run(
                    ["docker-compose", "exec", "-T", "postgres", 
                     "pg_isready", "-U", os.getenv("DATABASE_USER", "agenthub_user")],
                    cwd=self.project_root,
                    capture_output=True,
                    check=False
                )
                if result.returncode == 0:
                    logger.info("PostgreSQL is ready")
                    return True
                asyncio.sleep(1)
                
            logger.error("PostgreSQL failed to start within timeout")
            return False
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to setup PostgreSQL: {e}")
            return False
            
    def initialize_database(self) -> bool:
        """Initialize database schema and tables"""
        try:
            logger.info("Initializing database schema...")
            
            # Run database initialization script
            init_script = self.project_root / "agenthub_main" / "src" / "fastmcp" / "task_management" / "infrastructure" / "database" / "init_database.py"
            
            if init_script.exists():
                result = subprocess.run(
                    [sys.executable, str(init_script)],
                    capture_output=True,
                    text=True,
                    env={**os.environ, "DATABASE_TYPE": "postgresql"}
                )
                
                if result.returncode == 0:
                    logger.info("Database initialized successfully")
                    return True
                else:
                    logger.error(f"Database initialization failed: {result.stderr}")
                    return False
            else:
                logger.warning("Database init script not found, skipping")
                return True
                
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            return False
            
    def cleanup_backward_compatibility(self) -> None:
        """Remove backward compatibility code and Supabase references"""
        logger.info("Cleaning up backward compatibility code...")
        
        # Files to remove (Supabase-specific)
        files_to_remove = [
            "agenthub_main/src/fastmcp/auth/supabase_service.py",
            "agenthub_main/src/fastmcp/auth/supabase_auth.py",
            "agenthub_main/scripts/setup_supabase.py",
            "agenthub_main/scripts/migrate_to_supabase.py"
        ]
        
        for file_path in files_to_remove:
            full_path = self.project_root / file_path
            if full_path.exists():
                full_path.unlink()
                logger.info(f"Removed: {file_path}")
                
        logger.info("Backward compatibility cleanup completed")
        
    def generate_mcp_config(self, keycloak_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate MCP server configuration"""
        return {
            "auth": {
                "enabled": True,
                "provider": "keycloak",
                "keycloak": {
                    "url": keycloak_config["KEYCLOAK_URL"],
                    "realm": keycloak_config["KEYCLOAK_REALM"],
                    "client_id": keycloak_config["KEYCLOAK_CLIENT_ID"],
                    "verify_audience": True,
                    "token_cache_ttl": 300
                }
            },
            "database": {
                "type": "postgresql",
                "host": "localhost",
                "port": 5432,
                "name": os.getenv("DATABASE_NAME", "agenthub_prod"),
                "user": os.getenv("DATABASE_USER", "agenthub_user")
            },
            "server": {
                "host": "0.0.0.0",
                "port": 8001,
                "cors_origins": ["http://localhost:3800", "http://localhost:8001"]
            }
        }
        
    def save_mcp_config(self, config: Dict[str, Any]) -> None:
        """Save MCP configuration file"""
        config_file = self.project_root / "agenthub_main" / "config" / "mcp_config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
            
        logger.info(f"MCP configuration saved to: {config_file}")
        
    async def run(self) -> bool:
        """Run the complete setup process"""
        logger.info("Starting clean authentication setup...")
        
        # Check prerequisites
        if not self.check_prerequisites():
            logger.error("Prerequisites not met. Please install Docker and Docker Compose.")
            return False
            
        # Validate Keycloak configuration
        keycloak_config = self.validate_keycloak_config()
        if not keycloak_config:
            logger.error("Keycloak configuration invalid. Please update .env file.")
            return False
            
        # Test Keycloak connection
        if not await self.test_keycloak_connection(keycloak_config):
            logger.error("Cannot connect to Keycloak. Please check your configuration.")
            return False
            
        # Setup PostgreSQL
        if not self.setup_postgresql_docker():
            logger.error("PostgreSQL setup failed")
            return False
            
        # Initialize database
        if not self.initialize_database():
            logger.error("Database initialization failed")
            return False
            
        # Clean up backward compatibility
        self.cleanup_backward_compatibility()
        
        # Generate and save MCP configuration
        mcp_config = self.generate_mcp_config(keycloak_config)
        self.save_mcp_config(mcp_config)
        
        logger.info("=" * 60)
        logger.info("✅ Authentication setup completed successfully!")
        logger.info("=" * 60)
        logger.info("Configuration:")
        logger.info(f"  - PostgreSQL: Running on localhost:5432")
        logger.info(f"  - Keycloak: {keycloak_config['KEYCLOAK_URL']}")
        logger.info(f"  - Realm: {keycloak_config['KEYCLOAK_REALM']}")
        logger.info(f"  - Client ID: {keycloak_config['KEYCLOAK_CLIENT_ID']}")
        logger.info("=" * 60)
        logger.info("Next steps:")
        logger.info("  1. Start the MCP server: docker-compose up mcp-server")
        logger.info("  2. Test authentication with: python test_auth_flow.py")
        logger.info("=" * 60)
        
        return True

if __name__ == "__main__":
    setup = AuthenticationSetup()
    success = asyncio.run(setup.run())
    sys.exit(0 if success else 1)