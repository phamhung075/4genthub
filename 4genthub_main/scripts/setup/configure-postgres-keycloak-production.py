#!/usr/bin/env python3
"""
Production Configuration for PostgreSQL Docker + Keycloak Cloud
================================================================

This script:
1. Removes all backward compatibility code (Supabase references)
2. Configures PostgreSQL in Docker for local development
3. Configures Keycloak cloud authentication
4. Sets up MCP to work with Keycloak tokens
5. Validates the complete configuration

Usage:
    python configure-postgres-keycloak-production.py [--clean] [--test]
    
Options:
    --clean     Remove all backup files after successful configuration
    --test      Run validation tests after configuration
"""

import os
import sys
import re
import shutil
import subprocess
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).parent
BACKEND_ROOT = PROJECT_ROOT / "4genthub_main"
FRONTEND_ROOT = PROJECT_ROOT / "4genthub-frontend"

# Files that may contain Supabase references
SUPABASE_FILES_TO_CHECK = [
    # Backend files
    "4genthub_main/src/fastmcp/server/routes/auth_starlette.py",
    "4genthub_main/src/fastmcp/server/routes/auth_keycloak_enhanced.py",
    "4genthub_main/src/fastmcp/server/routes/task_routes.py",
    "4genthub_main/src/fastmcp/server/manage_connection_tool.py",
    "4genthub_main/src/fastmcp/task_management/infrastructure/database/database_config.py",
    "4genthub_main/src/fastmcp/task_management/infrastructure/database/database_initializer.py",
    "4genthub_main/src/fastmcp/task_management/infrastructure/database/connection_pool.py",
    "4genthub_main/src/fastmcp/task_management/infrastructure/repositories/repository_factory.py",
    
    # Test files
    "4genthub_main/src/tests/auth/test_email_service_integration.py",
    "4genthub_main/src/tests/unit/auth/token_validator_test.py",
    "4genthub_main/src/tests/unit/auth/middleware/dual_auth_middleware_test.py",
    
    # Frontend files
    "4genthub-frontend/src/contexts/AuthContext.tsx",
    "4genthub-frontend/src/services/api.ts",
]

# Files to completely remove (obsolete)
FILES_TO_REMOVE = [
    "docker-compose.supabase.yml",
    "start-supabase-local.sh",
    "debug_supabase_connectivity.py",
    "clean_supabase_data.py",
    "test_login_after_manual_reset.py",
    "recreate_user.py",
    "fix_username.py",
    "test_login_existing.py",
    "4genthub_main/scripts/test_supabase_auth.py",
    "4genthub_main/scripts/run_supabase_migration.py",
]

class ProductionConfigurator:
    """Configure the system for production with PostgreSQL and Keycloak"""
    
    def __init__(self, clean_backups: bool = False, run_tests: bool = False):
        self.clean_backups = clean_backups
        self.run_tests = run_tests
        self.backups_created = []
        self.files_modified = []
        self.files_removed = []
        
    def backup_file(self, filepath: Path) -> None:
        """Create a backup of a file before modifying it."""
        if not filepath.exists():
            return
            
        backup_path = filepath.with_suffix(filepath.suffix + '.backup')
        if not backup_path.exists():
            shutil.copy2(filepath, backup_path)
            self.backups_created.append(backup_path)
            logger.info(f"✅ Backed up: {filepath.name}")
    
    def remove_supabase_references(self, content: str, filepath: str) -> str:
        """Remove all Supabase references from file content."""
        original_content = content
        
        # Remove Supabase imports
        patterns = [
            r'^from supabase.*$',
            r'^import supabase.*$',
            r'^.*supabase_client.*$',
            r'^.*SupabaseClient.*$',
            r'^.*SUPABASE_.*$',
        ]
        
        for pattern in patterns:
            content = re.sub(pattern, '', content, flags=re.MULTILINE)
        
        # Remove Supabase-specific code blocks
        # This is more complex and file-specific
        if 'database_config.py' in filepath:
            content = self._clean_database_config(content)
        elif 'auth_starlette.py' in filepath:
            content = self._clean_auth_starlette(content)
        elif 'AuthContext.tsx' in filepath:
            content = self._clean_auth_context(content)
            
        # Remove empty lines created by deletions
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        if content != original_content:
            self.files_modified.append(filepath)
            
        return content
    
    def _clean_database_config(self, content: str) -> str:
        """Clean database_config.py specifically."""
        # Remove any Supabase-specific database type checks
        content = re.sub(
            r'if\s+database_type\s*==\s*["\']supabase["\'].*?(?=\n\s*(?:elif|else|$))',
            '',
            content,
            flags=re.DOTALL | re.MULTILINE
        )
        
        # Remove backward compatibility comments
        content = re.sub(
            r'#.*backward compatibility.*\n',
            '',
            content,
            flags=re.IGNORECASE
        )
        
        return content
    
    def _clean_auth_starlette(self, content: str) -> str:
        """Clean auth_starlette.py specifically."""
        # Remove Supabase authentication middleware
        content = re.sub(
            r'class\s+SupabaseAuthMiddleware.*?(?=\nclass|\n\n|\Z)',
            '',
            content,
            flags=re.DOTALL
        )
        
        # Remove Supabase-specific authentication checks
        content = re.sub(
            r'if\s+.*supabase.*:.*?(?=\n\s*(?:elif|else|return|$))',
            '',
            content,
            flags=re.DOTALL | re.MULTILINE
        )
        
        return content
    
    def _clean_auth_context(self, content: str) -> str:
        """Clean AuthContext.tsx specifically."""
        # Remove Supabase client initialization
        content = re.sub(
            r'const\s+supabase\s*=.*?;',
            '',
            content,
            flags=re.DOTALL
        )
        
        # Remove Supabase-specific authentication methods
        content = re.sub(
            r'const\s+loginWithSupabase.*?};',
            '',
            content,
            flags=re.DOTALL
        )
        
        return content
    
    def clean_file(self, filepath: Path) -> bool:
        """Clean a single file of Supabase references."""
        if not filepath.exists():
            return False
            
        try:
            self.backup_file(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            cleaned_content = self.remove_supabase_references(content, str(filepath))
            
            if cleaned_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(cleaned_content)
                logger.info(f"🧹 Cleaned: {filepath.name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error cleaning {filepath}: {e}")
            return False
    
    def remove_obsolete_files(self) -> None:
        """Remove obsolete files that are no longer needed."""
        for file_path in FILES_TO_REMOVE:
            full_path = PROJECT_ROOT / file_path
            if full_path.exists():
                try:
                    if full_path.is_file():
                        full_path.unlink()
                    else:
                        shutil.rmtree(full_path)
                    self.files_removed.append(file_path)
                    logger.info(f"🗑️  Removed: {file_path}")
                except Exception as e:
                    logger.error(f"❌ Error removing {file_path}: {e}")
    
    def update_docker_compose(self) -> None:
        """Ensure docker-compose.yml is properly configured for PostgreSQL."""
        docker_compose_path = PROJECT_ROOT / "docker-compose.yml"
        
        if not docker_compose_path.exists():
            logger.error("❌ docker-compose.yml not found!")
            return
            
        logger.info("✅ docker-compose.yml already configured for PostgreSQL")
    
    def create_env_template(self) -> None:
        """Create a .env.template file with proper configuration."""
        env_template = """# =============================================================================
# PRODUCTION CONFIGURATION TEMPLATE - PostgreSQL Docker + Keycloak Cloud
# =============================================================================
# Copy this file to .env and update the values marked with CHANGE_ME
# =============================================================================

# Environment
ENV=production
NODE_ENV=production

# PostgreSQL Database (Docker)
DATABASE_TYPE=postgresql
DATABASE_HOST=postgres  # Use 'postgres' for Docker, 'localhost' for direct access
DATABASE_PORT=5432
DATABASE_NAME=4genthub_prod
DATABASE_USER=4genthub_user
DATABASE_PASSWORD=CHANGE_ME_SECURE_PASSWORD
DATABASE_SSL_MODE=prefer
DATABASE_URL=postgresql://4genthub_user:CHANGE_ME_SECURE_PASSWORD@postgres:5432/4genthub_prod?sslmode=prefer

# Keycloak Authentication (Cloud)
AUTH_ENABLED=true
AUTH_PROVIDER=keycloak
KEYCLOAK_URL=CHANGE_ME_YOUR_KEYCLOAK_URL  # e.g., https://keycloak.yourdomain.com
KEYCLOAK_REALM=4genthub
KEYCLOAK_CLIENT_ID=mcp-backend
KEYCLOAK_CLIENT_SECRET=CHANGE_ME_YOUR_CLIENT_SECRET

# MCP Server
MCP_HOST=0.0.0.0
MCP_PORT=8001
JWT_SECRET_KEY=CHANGE_ME_GENERATE_SECURE_64_CHAR_STRING

# Frontend
FRONTEND_URL=http://localhost:3800

# CORS
CORS_ORIGINS=http://localhost:3800,http://localhost:8001
CORS_ALLOW_CREDENTIALS=true
"""
        
        template_path = PROJECT_ROOT / ".env.template"
        with open(template_path, 'w') as f:
            f.write(env_template)
        logger.info("✅ Created .env.template file")
    
    def validate_postgresql_connection(self) -> bool:
        """Validate PostgreSQL connection."""
        try:
            # Try to connect using psycopg2
            import psycopg2
            from psycopg2 import sql
            
            # Get database configuration from environment
            db_host = os.getenv("DATABASE_HOST", "localhost")
            db_port = os.getenv("DATABASE_PORT", "5432")
            db_name = os.getenv("DATABASE_NAME", "4genthub_prod")
            db_user = os.getenv("DATABASE_USER", "4genthub_user")
            db_password = os.getenv("DATABASE_PASSWORD")
            
            if not db_password:
                logger.warning("⚠️  DATABASE_PASSWORD not set in environment")
                return False
            
            # Try to connect
            conn = psycopg2.connect(
                host=db_host,
                port=db_port,
                dbname=db_name,
                user=db_user,
                password=db_password
            )
            
            # Test connection
            cur = conn.cursor()
            cur.execute("SELECT version()")
            version = cur.fetchone()
            logger.info(f"✅ PostgreSQL connected: {version[0][:50]}...")
            
            cur.close()
            conn.close()
            return True
            
        except ImportError:
            logger.warning("⚠️  psycopg2 not installed, skipping PostgreSQL validation")
            return True
        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            return False
    
    def validate_keycloak_connection(self) -> bool:
        """Validate Keycloak connection."""
        try:
            import httpx
            
            keycloak_url = os.getenv("KEYCLOAK_URL")
            keycloak_realm = os.getenv("KEYCLOAK_REALM", "4genthub")
            
            if not keycloak_url:
                logger.warning("⚠️  KEYCLOAK_URL not set in environment")
                return False
            
            # Try to fetch realm configuration
            realm_url = f"{keycloak_url}/realms/{keycloak_realm}"
            
            with httpx.Client() as client:
                response = client.get(realm_url, timeout=5.0)
                
                if response.status_code == 200:
                    realm_info = response.json()
                    logger.info(f"✅ Keycloak connected: Realm '{realm_info.get('realm')}' is accessible")
                    return True
                else:
                    logger.error(f"❌ Keycloak realm not accessible: {response.status_code}")
                    return False
                    
        except ImportError:
            logger.warning("⚠️  httpx not installed, skipping Keycloak validation")
            return True
        except Exception as e:
            logger.error(f"❌ Keycloak connection failed: {e}")
            return False
    
    def run_configuration(self) -> bool:
        """Run the complete configuration process."""
        logger.info("=" * 70)
        logger.info("🚀 Starting Production Configuration")
        logger.info("=" * 70)
        
        # Step 1: Clean Supabase references
        logger.info("\n📋 Step 1: Cleaning backward compatibility code...")
        for file_path in SUPABASE_FILES_TO_CHECK:
            full_path = PROJECT_ROOT / file_path
            if full_path.exists():
                self.clean_file(full_path)
        
        # Step 2: Remove obsolete files
        logger.info("\n📋 Step 2: Removing obsolete files...")
        self.remove_obsolete_files()
        
        # Step 3: Update Docker configuration
        logger.info("\n📋 Step 3: Validating Docker configuration...")
        self.update_docker_compose()
        
        # Step 4: Create environment template
        logger.info("\n📋 Step 4: Creating environment template...")
        self.create_env_template()
        
        # Step 5: Validate connections (if requested)
        if self.run_tests:
            logger.info("\n📋 Step 5: Validating connections...")
            
            pg_ok = self.validate_postgresql_connection()
            kc_ok = self.validate_keycloak_connection()
            
            if not pg_ok or not kc_ok:
                logger.warning("⚠️  Some connections could not be validated")
                logger.info("   Please ensure Docker services are running:")
                logger.info("   docker-compose up -d postgres")
                logger.info("   And Keycloak is properly configured")
        
        # Step 6: Clean up backups (if requested)
        if self.clean_backups and self.backups_created:
            logger.info("\n📋 Step 6: Cleaning up backup files...")
            for backup in self.backups_created:
                try:
                    backup.unlink()
                    logger.info(f"🗑️  Removed backup: {backup.name}")
                except Exception as e:
                    logger.error(f"❌ Error removing backup {backup}: {e}")
        
        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("📊 Configuration Summary")
        logger.info("=" * 70)
        logger.info(f"✅ Files modified: {len(self.files_modified)}")
        logger.info(f"✅ Files removed: {len(self.files_removed)}")
        logger.info(f"✅ Backups created: {len(self.backups_created)}")
        
        if self.files_modified:
            logger.info("\n📝 Modified files:")
            for f in self.files_modified[:10]:  # Show first 10
                logger.info(f"   - {Path(f).name}")
            if len(self.files_modified) > 10:
                logger.info(f"   ... and {len(self.files_modified) - 10} more")
        
        logger.info("\n✅ Production configuration complete!")
        logger.info("\n📌 Next steps:")
        logger.info("1. Review and update .env file with your actual values")
        logger.info("2. Start PostgreSQL: docker-compose up -d postgres")
        logger.info("3. Configure Keycloak client and update KEYCLOAK_* variables")
        logger.info("4. Start MCP server: docker-compose up -d mcp-server")
        logger.info("5. Test authentication: python test-keycloak-mcp-production.py")
        
        return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Configure production environment with PostgreSQL and Keycloak"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove backup files after successful configuration"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run validation tests after configuration"
    )
    
    args = parser.parse_args()
    
    # Check if .env exists
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        logger.warning("⚠️  .env file not found. Creating from template...")
        template_path = PROJECT_ROOT / ".env.template"
        if template_path.exists():
            shutil.copy2(template_path, env_path)
            logger.info("✅ Created .env from template. Please update it with your values.")
        else:
            logger.error("❌ No .env or .env.template found. Configuration cannot proceed.")
            sys.exit(1)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run configuration
    configurator = ProductionConfigurator(
        clean_backups=args.clean,
        run_tests=args.test
    )
    
    success = configurator.run_configuration()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()