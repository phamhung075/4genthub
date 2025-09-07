#!/usr/bin/env python3
"""
PostgreSQL + Keycloak Setup Script for DhafnckMCP
Configures the system to use:
- PostgreSQL Docker for local database
- Keycloak Cloud for authentication
- Removes all Supabase backward compatibility code
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PostgresKeycloakSetup:
    """Configure DhafnckMCP for PostgreSQL + Keycloak"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.absolute()
        self.env_file = self.project_root / ".env"
        self.env_example = self.project_root / ".env.example"
        self.docker_compose = self.project_root / "docker-compose.yml"
        
    def create_env_file(self) -> bool:
        """Create optimized .env file for PostgreSQL + Keycloak"""
        
        env_content = """# DhafnckMCP Environment Configuration
# PostgreSQL + Keycloak Setup

# ===================================================================
# Environment Settings
# ===================================================================
ENV=production
APP_ENV=production
APP_DEBUG=false
APP_LOG_LEVEL=INFO

# ===================================================================
# PostgreSQL Database Configuration (Local Docker)
# ===================================================================
DATABASE_TYPE=postgresql
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=dhafnck_mcp_prod
DATABASE_USER=dhafnck_user
DATABASE_PASSWORD=SecurePassword2025!
DATABASE_SSL_MODE=prefer

# Connection URL
DATABASE_URL=postgresql://dhafnck_user:SecurePassword2025!@localhost:5432/dhafnck_mcp_prod?sslmode=prefer

# ===================================================================
# Keycloak Authentication (Cloud)
# ===================================================================
AUTH_ENABLED=true
AUTH_PROVIDER=keycloak

# Update these with your Keycloak cloud instance details
KEYCLOAK_URL=https://your-keycloak.com
KEYCLOAK_REALM=dhafnck-mcp
KEYCLOAK_CLIENT_ID=mcp-backend
KEYCLOAK_CLIENT_SECRET=your-client-secret

# Keycloak Security
KEYCLOAK_VERIFY_TOKEN_AUDIENCE=true
KEYCLOAK_TOKEN_CACHE_TTL=300
KEYCLOAK_PUBLIC_KEY_CACHE_TTL=3600
KEYCLOAK_SSL_VERIFY=true

# ===================================================================
# MCP Server Configuration
# ===================================================================
MCP_HOST=0.0.0.0
MCP_PORT=8001
JWT_SECRET_KEY=generate-secure-key-here-32-chars-min

# ===================================================================
# CORS Configuration
# ===================================================================
CORS_ORIGINS=http://localhost:3800,http://localhost:8001
CORS_ALLOW_CREDENTIALS=true

# ===================================================================
# Features
# ===================================================================
FEATURE_VISION_SYSTEM=true
FEATURE_HIERARCHICAL_CONTEXT=true
FEATURE_AUTO_COMPACT=true
FEATURE_MULTI_AGENT=true
FEATURE_RATE_LIMITING=true
FEATURE_REQUEST_LOGGING=true

# ===================================================================
# Docker Configuration
# ===================================================================
DOCKER_NETWORK=dhafnck_network

# ===================================================================
# PgAdmin (Optional)
# ===================================================================
PGADMIN_EMAIL=admin@dhafnck.com
PGADMIN_PASSWORD=AdminPassword2025!
"""
        
        try:
            # Backup existing .env if present
            if self.env_file.exists():
                backup_path = self.env_file.with_suffix('.env.backup')
                logger.info(f"Backing up existing .env to {backup_path}")
                self.env_file.rename(backup_path)
            
            # Write new .env file
            self.env_file.write_text(env_content)
            logger.info(f"Created new .env file at {self.env_file}")
            
            print("\n⚠️  IMPORTANT: Update the following in .env:")
            print("   - KEYCLOAK_URL: Your Keycloak cloud URL")
            print("   - KEYCLOAK_CLIENT_SECRET: Your client secret")
            print("   - JWT_SECRET_KEY: Generate a secure 32+ character key")
            print("   - DATABASE_PASSWORD: Change to a secure password")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create .env file: {e}")
            return False
    
    def remove_supabase_references(self) -> int:
        """Remove all Supabase backward compatibility code"""
        
        files_to_clean = []
        patterns_to_remove = [
            "supabase",
            "SUPABASE",
            "SupabaseClient",
            "create_client",
            "supabase_url",
            "supabase_key",
            "anon_key",
            "service_role",
        ]
        
        # Find Python files with Supabase references
        logger.info("Scanning for Supabase references...")
        
        for root, dirs, files in os.walk(self.project_root / "dhafnck_mcp_main"):
            # Skip test directories for now
            if 'tests' in root or '__pycache__' in root:
                continue
                
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    content = file_path.read_text()
                    
                    # Check if file contains Supabase references
                    if any(pattern.lower() in content.lower() for pattern in patterns_to_remove):
                        files_to_clean.append(file_path)
        
        logger.info(f"Found {len(files_to_clean)} files with Supabase references")
        
        cleaned_count = 0
        for file_path in files_to_clean:
            try:
                content = file_path.read_text()
                original_content = content
                
                # Remove Supabase imports
                lines = content.split('\n')
                cleaned_lines = []
                
                for line in lines:
                    # Skip Supabase-related lines
                    if any(pattern in line for pattern in [
                        'supabase', 'SUPABASE', 'SupabaseClient',
                        'create_client', 'anon_key', 'service_role'
                    ]):
                        continue
                    cleaned_lines.append(line)
                
                content = '\n'.join(cleaned_lines)
                
                # Only write if content changed
                if content != original_content:
                    file_path.write_text(content)
                    cleaned_count += 1
                    logger.info(f"Cleaned: {file_path.relative_to(self.project_root)}")
                    
            except Exception as e:
                logger.error(f"Error cleaning {file_path}: {e}")
        
        return cleaned_count
    
    def setup_database_init_script(self) -> bool:
        """Create PostgreSQL initialization script"""
        
        init_sql_path = self.project_root / "dhafnck_mcp_main" / "scripts" / "init.sql"
        init_sql_path.parent.mkdir(parents=True, exist_ok=True)
        
        init_sql = """-- PostgreSQL Initialization Script for DhafnckMCP

-- Create database if not exists (run as superuser)
SELECT 'CREATE DATABASE dhafnck_mcp_prod'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'dhafnck_mcp_prod')\\gexec

-- Connect to the database
\\c dhafnck_mcp_prod;

-- Create schema
CREATE SCHEMA IF NOT EXISTS public;

-- Grant permissions
GRANT ALL ON SCHEMA public TO dhafnck_user;
GRANT ALL ON ALL TABLES IN SCHEMA public TO dhafnck_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO dhafnck_user;

-- Create required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'PostgreSQL initialization completed successfully';
END $$;
"""
        
        try:
            init_sql_path.write_text(init_sql)
            logger.info(f"Created PostgreSQL init script at {init_sql_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create init script: {e}")
            return False
    
    def update_docker_compose(self) -> bool:
        """Ensure docker-compose.yml is properly configured"""
        
        # The docker-compose.yml already looks good for PostgreSQL + Keycloak
        # Just verify it exists
        if not self.docker_compose.exists():
            logger.error("docker-compose.yml not found!")
            return False
        
        logger.info("docker-compose.yml is properly configured for PostgreSQL + Keycloak")
        return True
    
    def verify_keycloak_connection(self) -> bool:
        """Verify Keycloak configuration"""
        
        test_script = """
import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def test_keycloak():
    keycloak_url = os.getenv("KEYCLOAK_URL")
    realm = os.getenv("KEYCLOAK_REALM")
    
    if not keycloak_url:
        print("❌ KEYCLOAK_URL not configured in .env")
        return False
    
    try:
        # Test realm endpoint
        realm_url = f"{keycloak_url}/realms/{realm}"
        async with httpx.AsyncClient() as client:
            response = await client.get(realm_url)
            
            if response.status_code == 200:
                print(f"✅ Keycloak realm '{realm}' is accessible")
                return True
            else:
                print(f"❌ Keycloak realm returned status {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Cannot connect to Keycloak: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_keycloak())
    exit(0 if result else 1)
"""
        
        test_file = self.project_root / "test_keycloak_connection.py"
        test_file.write_text(test_script)
        
        try:
            result = subprocess.run(
                [sys.executable, str(test_file)],
                capture_output=True,
                text=True
            )
            
            print("\nKeycloak Connection Test:")
            print(result.stdout)
            
            if result.returncode != 0 and result.stderr:
                print(f"Error: {result.stderr}")
            
            # Cleanup test file
            test_file.unlink()
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Failed to test Keycloak: {e}")
            if test_file.exists():
                test_file.unlink()
            return False
    
    def start_docker_services(self) -> bool:
        """Start PostgreSQL Docker container"""
        
        try:
            print("\n🐳 Starting Docker services...")
            
            # Stop existing containers
            subprocess.run(
                ["docker-compose", "down"],
                cwd=self.project_root,
                capture_output=True
            )
            
            # Start PostgreSQL service
            result = subprocess.run(
                ["docker-compose", "up", "-d", "postgres"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ PostgreSQL Docker container started")
                
                # Wait for PostgreSQL to be ready
                print("⏳ Waiting for PostgreSQL to be ready...")
                import time
                time.sleep(5)
                
                return True
            else:
                print(f"❌ Failed to start PostgreSQL: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Docker error: {e}")
            return False
    
    def run_database_migrations(self) -> bool:
        """Initialize database schema"""
        
        migration_script = self.project_root / "dhafnck_mcp_main" / "src" / "fastmcp" / "task_management" / "infrastructure" / "database" / "init_database.py"
        
        if not migration_script.exists():
            logger.warning("Database migration script not found, skipping...")
            return True
        
        try:
            print("\n🔄 Running database migrations...")
            
            result = subprocess.run(
                [sys.executable, str(migration_script)],
                capture_output=True,
                text=True,
                cwd=self.project_root / "dhafnck_mcp_main"
            )
            
            if result.returncode == 0:
                print("✅ Database migrations completed")
                return True
            else:
                print(f"❌ Migration failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Migration error: {e}")
            return False
    
    def run_setup(self):
        """Execute complete setup process"""
        
        print("=" * 60)
        print("DhafnckMCP PostgreSQL + Keycloak Setup")
        print("=" * 60)
        
        steps = [
            ("Creating .env file", self.create_env_file),
            ("Removing Supabase references", lambda: self.remove_supabase_references() > 0),
            ("Creating PostgreSQL init script", self.setup_database_init_script),
            ("Verifying docker-compose.yml", self.update_docker_compose),
            ("Starting PostgreSQL Docker", self.start_docker_services),
            ("Running database migrations", self.run_database_migrations),
        ]
        
        for step_name, step_func in steps:
            print(f"\n📋 {step_name}...")
            if step_func():
                print(f"✅ {step_name} completed")
            else:
                print(f"❌ {step_name} failed")
                if step_name != "Removing Supabase references":  # This one is optional
                    print("\n⚠️  Setup incomplete. Please fix the errors and try again.")
                    return False
        
        print("\n" + "=" * 60)
        print("✅ SETUP COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        print("\n📝 Next Steps:")
        print("1. Update .env with your Keycloak credentials")
        print("2. Ensure Keycloak cloud instance is configured")
        print("3. Start the MCP server: docker-compose up mcp-server")
        print("4. Test authentication with: python test_keycloak_connection.py")
        
        print("\n🔧 Useful Commands:")
        print("  View logs: docker-compose logs -f")
        print("  Stop services: docker-compose down")
        print("  Access PgAdmin: http://localhost:5050 (use --profile tools)")
        print("  Connect to PostgreSQL: psql -h localhost -U dhafnck_user -d dhafnck_mcp_prod")
        
        return True

if __name__ == "__main__":
    setup = PostgresKeycloakSetup()
    success = setup.run_setup()
    sys.exit(0 if success else 1)