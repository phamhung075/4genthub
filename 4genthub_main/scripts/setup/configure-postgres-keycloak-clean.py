#!/usr/bin/env python3
"""
PostgreSQL Docker + Keycloak Cloud Configuration Script
Clean production setup without backward compatibility
"""

import os
import sys
import time
import logging
import subprocess
import json
import psycopg2
from psycopg2 import sql
import httpx
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PostgreSQLKeycloakConfigurator:
    """Configure PostgreSQL Docker and Keycloak Cloud integration"""
    
    def __init__(self):
        """Initialize configurator with environment settings"""
        load_dotenv()
        
        # PostgreSQL configuration
        self.db_config = {
            'host': os.getenv('DATABASE_HOST', 'localhost'),
            'port': os.getenv('DATABASE_PORT', '5432'),
            'database': os.getenv('DATABASE_NAME', '4genthub_prod'),
            'user': os.getenv('DATABASE_USER', '4genthub_user'),
            'password': os.getenv('DATABASE_PASSWORD')
        }
        
        # Keycloak configuration
        self.keycloak_config = {
            'url': os.getenv('KEYCLOAK_URL'),
            'realm': os.getenv('KEYCLOAK_REALM', '4genthub'),
            'client_id': os.getenv('KEYCLOAK_CLIENT_ID', 'mcp-backend'),
            'client_secret': os.getenv('KEYCLOAK_CLIENT_SECRET')
        }
        
        # MCP configuration
        self.mcp_config = {
            'host': os.getenv('MCP_HOST', '0.0.0.0'),
            'port': os.getenv('MCP_PORT', '8001'),
            'secret_key': os.getenv('JWT_SECRET_KEY')
        }
        
        self.project_root = Path(__file__).parent
        
    def verify_environment(self) -> bool:
        """Verify required environment variables are set"""
        logger.info("Verifying environment configuration...")
        
        required_vars = {
            'PostgreSQL': [
                ('DATABASE_PASSWORD', self.db_config['password']),
            ],
            'Keycloak': [
                ('KEYCLOAK_URL', self.keycloak_config['url']),
                ('KEYCLOAK_CLIENT_SECRET', self.keycloak_config['client_secret'])
            ],
            'MCP': [
                ('JWT_SECRET_KEY', self.mcp_config['secret_key'])
            ]
        }
        
        all_valid = True
        for category, vars_list in required_vars.items():
            logger.info(f"\nChecking {category} configuration:")
            for var_name, var_value in vars_list:
                if not var_value:
                    logger.error(f"  ❌ {var_name} is not set")
                    all_valid = False
                else:
                    logger.info(f"  ✓ {var_name} is configured")
        
        return all_valid
    
    def start_postgresql_docker(self) -> bool:
        """Start PostgreSQL in Docker using docker-compose"""
        logger.info("\nStarting PostgreSQL Docker container...")
        
        compose_file = self.project_root / "docker-compose.production.yml"
        
        if not compose_file.exists():
            logger.error(f"Docker compose file not found: {compose_file}")
            return False
        
        try:
            # Stop existing containers
            logger.info("Stopping any existing PostgreSQL containers...")
            subprocess.run(
                ["docker-compose", "-f", str(compose_file), "down"],
                capture_output=True,
                text=True
            )
            
            # Start PostgreSQL service only
            logger.info("Starting PostgreSQL service...")
            result = subprocess.run(
                ["docker-compose", "-f", str(compose_file), "up", "-d", "postgres"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to start PostgreSQL: {result.stderr}")
                return False
            
            # Wait for PostgreSQL to be ready
            logger.info("Waiting for PostgreSQL to be ready...")
            for i in range(30):
                try:
                    conn = psycopg2.connect(**self.db_config)
                    conn.close()
                    logger.info("✓ PostgreSQL is ready")
                    return True
                except psycopg2.OperationalError:
                    if i < 29:
                        time.sleep(2)
                    else:
                        logger.error("PostgreSQL failed to start within timeout")
                        return False
            
        except Exception as e:
            logger.error(f"Error starting PostgreSQL: {e}")
            return False
    
    def initialize_database(self) -> bool:
        """Initialize PostgreSQL database schema"""
        logger.info("\nInitializing PostgreSQL database...")
        
        try:
            conn = psycopg2.connect(**self.db_config)
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Create schema for clean separation
            logger.info("Creating database schema...")
            cursor.execute("""
                CREATE SCHEMA IF NOT EXISTS mcp;
                CREATE SCHEMA IF NOT EXISTS keycloak;
            """)
            
            # Create MCP token storage table
            logger.info("Creating MCP token table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS keycloak.mcp_tokens (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id VARCHAR(255) NOT NULL,
                    token_hash VARCHAR(255) NOT NULL UNIQUE,
                    token_prefix VARCHAR(32) NOT NULL,
                    name VARCHAR(255),
                    scopes TEXT[],
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    revoked_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT true,
                    metadata JSONB DEFAULT '{}',
                    CONSTRAINT unique_active_token_name UNIQUE(user_id, name) 
                        DEFERRABLE INITIALLY DEFERRED
                );
                
                CREATE INDEX IF NOT EXISTS idx_mcp_tokens_user_id 
                    ON keycloak.mcp_tokens(user_id);
                CREATE INDEX IF NOT EXISTS idx_mcp_tokens_token_hash 
                    ON keycloak.mcp_tokens(token_hash);
                CREATE INDEX IF NOT EXISTS idx_mcp_tokens_active 
                    ON keycloak.mcp_tokens(is_active) 
                    WHERE is_active = true;
            """)
            
            # Create session management table
            logger.info("Creating session table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS keycloak.sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    session_id VARCHAR(255) NOT NULL UNIQUE,
                    user_id VARCHAR(255) NOT NULL,
                    access_token TEXT,
                    refresh_token TEXT,
                    id_token TEXT,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB DEFAULT '{}',
                    is_active BOOLEAN DEFAULT true
                );
                
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id 
                    ON keycloak.sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_sessions_active 
                    ON keycloak.sessions(is_active, expires_at);
            """)
            
            # Create audit log table
            logger.info("Creating audit log table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS keycloak.audit_log (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    event_type VARCHAR(100) NOT NULL,
                    user_id VARCHAR(255),
                    session_id VARCHAR(255),
                    ip_address INET,
                    user_agent TEXT,
                    details JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_audit_log_user_id 
                    ON keycloak.audit_log(user_id);
                CREATE INDEX IF NOT EXISTS idx_audit_log_created_at 
                    ON keycloak.audit_log(created_at DESC);
            """)
            
            logger.info("✓ Database initialization complete")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False
    
    def test_keycloak_connection(self) -> bool:
        """Test connection to Keycloak cloud service"""
        logger.info("\nTesting Keycloak cloud connection...")
        
        if not self.keycloak_config['url']:
            logger.error("Keycloak URL not configured")
            return False
        
        try:
            # Test well-known endpoint
            well_known_url = (
                f"{self.keycloak_config['url']}/realms/"
                f"{self.keycloak_config['realm']}/"
                f".well-known/openid-configuration"
            )
            
            response = httpx.get(well_known_url, timeout=10)
            
            if response.status_code == 200:
                config = response.json()
                logger.info("✓ Keycloak connection successful")
                logger.info(f"  Issuer: {config.get('issuer')}")
                logger.info(f"  Token endpoint: {config.get('token_endpoint')}")
                return True
            else:
                logger.error(f"Keycloak returned status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to Keycloak: {e}")
            return False
    
    def clean_supabase_code(self) -> bool:
        """Remove Supabase-related code and backward compatibility"""
        logger.info("\nCleaning up Supabase and backward compatibility code...")
        
        files_to_remove = [
            'clean_supabase_data.py',
            'debug_supabase_connectivity.py',
            '4genthub_main/scripts/run_supabase_migration.py',
            '4genthub_main/scripts/test_supabase_auth.py'
        ]
        
        for file_path in files_to_remove:
            full_path = self.project_root / file_path
            if full_path.exists():
                try:
                    full_path.unlink()
                    logger.info(f"  ✓ Removed: {file_path}")
                except Exception as e:
                    logger.warning(f"  ⚠ Could not remove {file_path}: {e}")
        
        # Clean up imports and references
        logger.info("Cleaning up Supabase references in code...")
        
        # This would be done with proper refactoring tools
        # For now, we'll mark files that need manual review
        files_with_references = [
            '4genthub_main/src/fastmcp/task_management/infrastructure/database/database_initializer.py',
            '4genthub_main/src/fastmcp/server/routes/auth_starlette.py',
            '4genthub_main/src/fastmcp/server/auth/providers/jwt_bearer.py'
        ]
        
        logger.info("\nFiles that may need manual review for Supabase references:")
        for file_path in files_with_references:
            logger.info(f"  - {file_path}")
        
        return True
    
    def create_production_config(self) -> bool:
        """Create clean production configuration files"""
        logger.info("\nCreating production configuration files...")
        
        # Create .env.production for clean setup
        env_production = self.project_root / ".env.production"
        
        env_content = f"""# Production Configuration - PostgreSQL Docker + Keycloak Cloud
# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}

# Environment
ENV=production
NODE_ENV=production

# PostgreSQL Database (Docker)
DATABASE_TYPE=postgresql
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME={self.db_config['database']}
DATABASE_USER={self.db_config['user']}
DATABASE_PASSWORD={self.db_config['password']}
DATABASE_URL=postgresql://{self.db_config['user']}:{self.db_config['password']}@localhost:5432/{self.db_config['database']}

# Keycloak Cloud
AUTH_PROVIDER=keycloak
AUTH_ENABLED=true
KEYCLOAK_URL={self.keycloak_config['url']}
KEYCLOAK_REALM={self.keycloak_config['realm']}
KEYCLOAK_CLIENT_ID={self.keycloak_config['client_id']}
KEYCLOAK_CLIENT_SECRET={self.keycloak_config['client_secret']}
KEYCLOAK_VERIFY_TOKEN_AUDIENCE=true

# MCP Server
MCP_HOST={self.mcp_config['host']}
MCP_PORT={self.mcp_config['port']}
JWT_SECRET_KEY={self.mcp_config['secret_key']}

# Frontend
FRONTEND_URL=http://localhost:3800
CORS_ORIGINS=http://localhost:3800,http://localhost:8001
"""
        
        with open(env_production, 'w') as f:
            f.write(env_content)
        
        logger.info(f"✓ Created {env_production}")
        
        # Create startup script
        startup_script = self.project_root / "start-production.sh"
        
        script_content = """#!/bin/bash
# Production Startup Script

set -e

echo "Starting 4genthub Production Environment..."

# Load environment
export ENV_FILE=.env.production
source $ENV_FILE

# Start PostgreSQL
echo "Starting PostgreSQL..."
docker-compose -f docker-compose.production.yml up -d postgres

# Wait for PostgreSQL
echo "Waiting for PostgreSQL..."
until docker-compose -f docker-compose.production.yml exec postgres pg_isready; do
    sleep 2
done

# Start MCP Backend
echo "Starting MCP Backend..."
docker-compose -f docker-compose.production.yml up -d mcp-backend

# Show status
echo ""
echo "Services Status:"
docker-compose -f docker-compose.production.yml ps

echo ""
echo "Production environment started!"
echo "MCP Server: http://localhost:8001"
echo "Health Check: http://localhost:8001/health"
"""
        
        with open(startup_script, 'w') as f:
            f.write(script_content)
        
        startup_script.chmod(0o755)
        logger.info(f"✓ Created {startup_script}")
        
        return True
    
    def create_mcp_keycloak_integration(self) -> bool:
        """Create MCP-Keycloak token validation integration"""
        logger.info("\nCreating MCP-Keycloak integration...")
        
        integration_file = (
            self.project_root / "4genthub_main" / "src" / 
            "fastmcp" / "auth" / "mcp_keycloak_integration.py"
        )
        
        integration_code = '''"""
MCP-Keycloak Token Integration
Handles MCP token creation and validation with Keycloak authentication
"""

import os
import hashlib
import secrets
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass
import psycopg2
from psycopg2.extras import RealDictCursor
from jose import jwt, JWTError

logger = logging.getLogger(__name__)

@dataclass
class MCPToken:
    """MCP Token data structure"""
    id: str
    user_id: str
    token_hash: str
    token_prefix: str
    name: Optional[str]
    scopes: List[str]
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    metadata: Dict[str, Any]

class MCPKeycloakIntegration:
    """Integration between MCP tokens and Keycloak authentication"""
    
    def __init__(self):
        """Initialize integration with database connection"""
        self.db_config = {
            'host': os.getenv('DATABASE_HOST', 'localhost'),
            'port': os.getenv('DATABASE_PORT', '5432'),
            'database': os.getenv('DATABASE_NAME'),
            'user': os.getenv('DATABASE_USER'),
            'password': os.getenv('DATABASE_PASSWORD')
        }
        
        self.token_prefix = "mcp_"
        self.token_length = 32
        
    def _get_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)
    
    def _hash_token(self, token: str) -> str:
        """Create secure hash of token"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    async def create_mcp_token(
        self,
        user_id: str,
        name: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        expires_in_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a new MCP token for a Keycloak user
        
        Args:
            user_id: Keycloak user ID
            name: Optional token name
            scopes: Optional list of scopes
            expires_in_days: Optional expiration in days
            
        Returns:
            Dictionary with token information
        """
        # Generate secure random token
        raw_token = secrets.token_urlsafe(self.token_length)
        full_token = f"{self.token_prefix}{raw_token}"
        token_hash = self._hash_token(full_token)
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        
        # Store in database
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Deactivate existing token with same name if exists
            if name:
                cursor.execute("""
                    UPDATE keycloak.mcp_tokens 
                    SET is_active = false, revoked_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s AND name = %s AND is_active = true
                """, (user_id, name))
            
            # Insert new token
            cursor.execute("""
                INSERT INTO keycloak.mcp_tokens 
                (user_id, token_hash, token_prefix, name, scopes, expires_at, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, created_at
            """, (
                user_id,
                token_hash,
                self.token_prefix,
                name or f"Token-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                scopes or [],
                expires_at,
                '{}'
            ))
            
            result = cursor.fetchone()
            conn.commit()
            
            return {
                'success': True,
                'token': full_token,
                'token_id': str(result['id']),
                'name': name,
                'scopes': scopes or [],
                'created_at': result['created_at'].isoformat(),
                'expires_at': expires_at.isoformat() if expires_at else None
            }
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create MCP token: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            cursor.close()
            conn.close()
    
    async def validate_mcp_token(self, token: str) -> Optional[MCPToken]:
        """
        Validate an MCP token
        
        Args:
            token: The MCP token to validate
            
        Returns:
            MCPToken object if valid, None otherwise
        """
        if not token or not token.startswith(self.token_prefix):
            return None
        
        token_hash = self._hash_token(token)
        
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM keycloak.mcp_tokens
                WHERE token_hash = %s 
                AND is_active = true
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            """, (token_hash,))
            
            result = cursor.fetchone()
            
            if not result:
                return None
            
            # Update last used timestamp
            cursor.execute("""
                UPDATE keycloak.mcp_tokens
                SET last_used_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (result['id'],))
            
            conn.commit()
            
            return MCPToken(
                id=str(result['id']),
                user_id=result['user_id'],
                token_hash=result['token_hash'],
                token_prefix=result['token_prefix'],
                name=result['name'],
                scopes=result['scopes'] or [],
                created_at=result['created_at'],
                expires_at=result['expires_at'],
                is_active=result['is_active'],
                metadata=result['metadata'] or {}
            )
            
        except Exception as e:
            logger.error(f"Failed to validate MCP token: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    async def revoke_token(self, token_id: str, user_id: str) -> bool:
        """
        Revoke an MCP token
        
        Args:
            token_id: The token ID to revoke
            user_id: The user ID (for verification)
            
        Returns:
            True if revoked successfully
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE keycloak.mcp_tokens
                SET is_active = false, revoked_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
            """, (token_id, user_id))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to revoke token: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    async def list_user_tokens(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all active tokens for a user
        
        Args:
            user_id: The user ID
            
        Returns:
            List of token information
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, scopes, created_at, last_used_at, expires_at
                FROM keycloak.mcp_tokens
                WHERE user_id = %s AND is_active = true
                ORDER BY created_at DESC
            """, (user_id,))
            
            results = cursor.fetchall()
            
            return [
                {
                    'id': str(row['id']),
                    'name': row['name'],
                    'scopes': row['scopes'] or [],
                    'created_at': row['created_at'].isoformat(),
                    'last_used_at': row['last_used_at'].isoformat() if row['last_used_at'] else None,
                    'expires_at': row['expires_at'].isoformat() if row['expires_at'] else None
                }
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"Failed to list user tokens: {e}")
            return []
        finally:
            cursor.close()
            conn.close()

# Export singleton instance
mcp_keycloak_integration = MCPKeycloakIntegration()
'''
        
        integration_file.parent.mkdir(parents=True, exist_ok=True)
        with open(integration_file, 'w') as f:
            f.write(integration_code)
        
        logger.info(f"✓ Created {integration_file}")
        return True
    
    def run(self) -> bool:
        """Run the complete configuration process"""
        logger.info("=" * 60)
        logger.info("PostgreSQL + Keycloak Configuration")
        logger.info("=" * 60)
        
        # Step 1: Verify environment
        if not self.verify_environment():
            logger.error("\n❌ Environment verification failed")
            logger.info("\nPlease configure the following in your .env file:")
            logger.info("  DATABASE_PASSWORD=<secure-password>")
            logger.info("  KEYCLOAK_URL=<your-keycloak-cloud-url>")
            logger.info("  KEYCLOAK_CLIENT_SECRET=<your-client-secret>")
            logger.info("  JWT_SECRET_KEY=<secure-64-char-string>")
            return False
        
        # Step 2: Start PostgreSQL
        if not self.start_postgresql_docker():
            logger.error("\n❌ Failed to start PostgreSQL")
            return False
        
        # Step 3: Initialize database
        if not self.initialize_database():
            logger.error("\n❌ Failed to initialize database")
            return False
        
        # Step 4: Test Keycloak connection
        if not self.test_keycloak_connection():
            logger.error("\n❌ Failed to connect to Keycloak")
            logger.info("\nPlease verify your Keycloak configuration:")
            logger.info(f"  URL: {self.keycloak_config['url']}")
            logger.info(f"  Realm: {self.keycloak_config['realm']}")
            return False
        
        # Step 5: Clean up Supabase code
        if not self.clean_supabase_code():
            logger.warning("\n⚠ Some Supabase cleanup tasks need manual review")
        
        # Step 6: Create production configuration
        if not self.create_production_config():
            logger.error("\n❌ Failed to create production configuration")
            return False
        
        # Step 7: Create MCP-Keycloak integration
        if not self.create_mcp_keycloak_integration():
            logger.error("\n❌ Failed to create MCP-Keycloak integration")
            return False
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ Configuration Complete!")
        logger.info("=" * 60)
        
        logger.info("\nNext steps:")
        logger.info("1. Review and update Keycloak settings in .env.production")
        logger.info("2. Start the production environment:")
        logger.info("   ./start-production.sh")
        logger.info("3. Test MCP token authentication:")
        logger.info("   python test-mcp-keycloak-auth.py")
        logger.info("\nServices:")
        logger.info(f"  PostgreSQL: localhost:{self.db_config['port']}")
        logger.info(f"  MCP Server: http://localhost:{self.mcp_config['port']}")
        logger.info(f"  Keycloak: {self.keycloak_config['url']}")
        
        return True

if __name__ == "__main__":
    configurator = PostgreSQLKeycloakConfigurator()
    success = configurator.run()
    sys.exit(0 if success else 1)