#!/usr/bin/env python3
"""
Setup Script: PostgreSQL Docker + Keycloak Cloud Configuration
===============================================================
This script configures the 4genthub system to use:
- PostgreSQL in Docker for local database
- Keycloak on cloud for authentication
- Removes all backward compatibility code
"""

import os
import sys
import json
import subprocess
import time
import shutil
from pathlib import Path

class SetupManager:
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.src_dir = self.root_dir / "4genthub_main" / "src"
        self.test_dir = self.src_dir / "tests"
        self.errors = []
        self.warnings = []
        
    def print_header(self, title):
        """Print a formatted header"""
        print("\n" + "=" * 80)
        print(f" {title}")
        print("=" * 80)
        
    def print_step(self, step, status="🔄"):
        """Print a step with status"""
        print(f"{status} {step}")
        
    def check_docker(self):
        """Check if Docker is installed and running"""
        self.print_header("Checking Docker Installation")
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            self.print_step("Docker is installed", "✅")
            
            # Check if Docker daemon is running
            result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                text=True,
                check=True
            )
            self.print_step("Docker daemon is running", "✅")
            return True
        except subprocess.CalledProcessError:
            self.print_step("Docker is not running or not installed", "❌")
            self.errors.append("Docker must be installed and running")
            return False
    
    def remove_supabase_references(self):
        """Remove all Supabase references from the codebase"""
        self.print_header("Removing Backward Compatibility Code")
        
        files_modified = 0
        replacements = {
            # Environment variable replacements
            "SUPABASE_URL": "KEYCLOAK_URL",
            "SUPABASE_ANON_KEY": "KEYCLOAK_CLIENT_SECRET",
            "SUPABASE_SERVICE_KEY": "KEYCLOAK_CLIENT_SECRET",
            "supabase_url": "keycloak_url",
            "supabase_anon_key": "keycloak_client_secret",
            
            # Import replacements
            "from supabase import create_client": "# Removed Supabase import",
            "import supabase": "# Removed Supabase import",
            "from supabase.client import Client": "# Removed Supabase import",
            
            # Comment out Supabase-specific code
            "self.supabase_client": "# self.supabase_client  # Removed",
            "supabase.create_client": "# supabase.create_client  # Removed",
        }
        
        # Find all Python files
        python_files = list(self.src_dir.rglob("*.py"))
        
        for file_path in python_files:
            if "__pycache__" in str(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # Apply replacements
                for old, new in replacements.items():
                    if old in content:
                        content = content.replace(old, new)
                
                # Remove entire lines containing Supabase if they're imports or standalone
                lines = content.split('\n')
                new_lines = []
                for line in lines:
                    if 'supabase' in line.lower() and ('import' in line or 'from' in line):
                        new_lines.append(f"# {line}  # Removed Supabase dependency")
                    elif 'SUPABASE' in line and '=' in line:
                        # Comment out Supabase environment variable usage
                        new_lines.append(f"# {line}  # Removed Supabase dependency")
                    else:
                        new_lines.append(line)
                
                content = '\n'.join(new_lines)
                
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    files_modified += 1
                    
            except Exception as e:
                self.warnings.append(f"Could not process {file_path}: {e}")
        
        self.print_step(f"Modified {files_modified} files to remove Supabase references", "✅")
        return files_modified > 0
    
    def create_env_file(self):
        """Create a clean .env file for PostgreSQL + Keycloak"""
        self.print_header("Creating Clean Environment Configuration")
        
        env_content = """# =============================================================================
# CLEAN PRODUCTION CONFIGURATION - POSTGRESQL + KEYCLOAK
# =============================================================================
# Created by setup-clean-postgres-keycloak.py
# PostgreSQL Docker (local) + Keycloak (cloud)
# =============================================================================

# =============================================================================
# ENVIRONMENT
# =============================================================================
ENV=production
NODE_ENV=production
APP_DEBUG=false
APP_LOG_LEVEL=info

# =============================================================================
# POSTGRESQL DATABASE (Local Docker)
# =============================================================================
DATABASE_TYPE=postgresql
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=4genthub
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres_secure_password_2025
DATABASE_SSL_MODE=disable

# PostgreSQL Connection URL
DATABASE_URL=postgresql://postgres:postgres_secure_password_2025@localhost:5432/4genthub

# PostgreSQL Docker Configuration
POSTGRES_CONTAINER_NAME=4genthub-postgres
POSTGRES_DATA_VOLUME=4genthub_postgres_data
POSTGRES_BACKUP_VOLUME=4genthub_postgres_backup

# =============================================================================
# KEYCLOAK AUTHENTICATION (Cloud)
# =============================================================================
# Enable authentication
AUTH_ENABLED=true
AUTH_PROVIDER=keycloak

# Keycloak Server Configuration
# TODO: Update these with your actual Keycloak cloud instance
KEYCLOAK_URL=https://your-keycloak-domain.com
KEYCLOAK_REALM=4genthub
KEYCLOAK_CLIENT_ID=mcp-backend
KEYCLOAK_CLIENT_SECRET=your-keycloak-client-secret-here

# Keycloak Token Configuration
KEYCLOAK_TOKEN_ALGORITHM=RS256
KEYCLOAK_TOKEN_AUDIENCE=mcp-backend
KEYCLOAK_TOKEN_ISSUER=https://your-keycloak-domain.com/realms/4genthub

# =============================================================================
# MCP SERVER
# =============================================================================
MCP_HOST=0.0.0.0
MCP_PORT=8001
JWT_SECRET_KEY=generate-a-secure-random-string-for-production-use

# =============================================================================
# FRONTEND
# =============================================================================
FRONTEND_URL=http://localhost:3800
FRONTEND_PORT=3800

# =============================================================================
# CORS
# =============================================================================
CORS_ORIGINS=http://localhost:3800,http://localhost:8001

# =============================================================================
# JWT CONFIGURATION (For internal use)
# =============================================================================
JWT_SECRET_KEY=generate-a-secure-32-char-string-for-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440

# =============================================================================
# DOCKER
# =============================================================================
COMPOSE_PROJECT_NAME=4genthub-clean
DOCKER_NETWORK=4genthub_clean_network

# =============================================================================
# FEATURES
# =============================================================================
FEATURE_VISION_SYSTEM=true
FEATURE_HIERARCHICAL_CONTEXT=true
FEATURE_AUTO_COMPACT=true
FEATURE_MULTI_AGENT=true

# =============================================================================
# PGADMIN (Optional - Database Management)
# =============================================================================
PGADMIN_EMAIL=admin@4genthub.com
PGADMIN_PASSWORD=PgAdminSecure2025!
PGADMIN_PORT=5050

# =============================================================================
# TEST DATABASE (SQLite for faster tests)
# =============================================================================
TEST_DATABASE_TYPE=sqlite
TEST_DATABASE_NAME=4genthub_test
"""
        
        env_path = self.root_dir / ".env.clean"
        with open(env_path, 'w') as f:
            f.write(env_content)
        
        self.print_step(f"Created clean environment file: .env.clean", "✅")
        self.print_step("Please update the Keycloak settings with your actual cloud instance", "⚠️")
        return env_path
    
    def create_docker_compose(self):
        """Create Docker Compose file for PostgreSQL only"""
        self.print_header("Creating Docker Compose Configuration")
        
        compose_content = """version: '3.8'

services:
  # PostgreSQL Database (Local)
  postgres:
    image: postgres:16-alpine
    container_name: ${POSTGRES_CONTAINER_NAME:-4genthub-postgres}
    environment:
      POSTGRES_DB: ${DATABASE_NAME:-4genthub}
      POSTGRES_USER: ${DATABASE_USER:-postgres}
      POSTGRES_PASSWORD: ${DATABASE_PASSWORD:-postgres_secure_password_2025}
      POSTGRES_INITDB_ARGS: "--encoding=UTF8"
    ports:
      - "${DATABASE_PORT:-5432}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - postgres_backup:/backup
    networks:
      - 4genthub_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DATABASE_USER:-postgres} -d ${DATABASE_NAME:-4genthub}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # PgAdmin (Optional - Database Management UI)
  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: 4genthub-pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: ${PGADMIN_EMAIL:-admin@4genthub.com}
      PGADMIN_DEFAULT_PASSWORD: ${PGADMIN_PASSWORD:-PgAdminSecure2025!}
      PGADMIN_CONFIG_SERVER_MODE: 'False'
      PGADMIN_CONFIG_MASTER_PASSWORD_REQUIRED: 'False'
    ports:
      - "${PGADMIN_PORT:-5050}:80"
    volumes:
      - pgadmin_data:/var/lib/pgadmin
    networks:
      - 4genthub_network
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

  # Backend Application
  backend:
    build:
      context: ./4genthub_main
      dockerfile: Dockerfile
    container_name: 4genthub-backend
    environment:
      # Database
      DATABASE_TYPE: postgresql
      DATABASE_HOST: postgres
      DATABASE_PORT: 5432
      DATABASE_NAME: ${DATABASE_NAME:-4genthub}
      DATABASE_USER: ${DATABASE_USER:-postgres}
      DATABASE_PASSWORD: ${DATABASE_PASSWORD:-postgres_secure_password_2025}
      DATABASE_URL: postgresql://${DATABASE_USER:-postgres}:${DATABASE_PASSWORD:-postgres_secure_password_2025}@postgres:5432/${DATABASE_NAME:-4genthub}
      
      # Keycloak (Cloud)
      AUTH_ENABLED: ${AUTH_ENABLED:-true}
      AUTH_PROVIDER: ${AUTH_PROVIDER:-keycloak}
      KEYCLOAK_URL: ${KEYCLOAK_URL}
      KEYCLOAK_REALM: ${KEYCLOAK_REALM:-4genthub}
      KEYCLOAK_CLIENT_ID: ${KEYCLOAK_CLIENT_ID:-mcp-backend}
      KEYCLOAK_CLIENT_SECRET: ${KEYCLOAK_CLIENT_SECRET}
      
      # Application
      MCP_HOST: 0.0.0.0
      MCP_PORT: 8001
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
      CORS_ORIGINS: ${CORS_ORIGINS:-http://localhost:3800,http://localhost:8001}
    ports:
      - "${MCP_PORT:-8001}:8001"
    volumes:
      - ./4genthub_main:/app
      - ./data:/data
    networks:
      - 4genthub_network
    depends_on:
      postgres:
        condition: service_healthy
    command: python src/mcp_http_server.py
    restart: unless-stopped

  # Frontend Application
  frontend:
    build:
      context: ./4genthub-frontend
      dockerfile: Dockerfile
    container_name: 4genthub-frontend
    environment:
      REACT_APP_API_URL: http://localhost:${MCP_PORT:-8001}
      REACT_APP_KEYCLOAK_URL: ${KEYCLOAK_URL}
      REACT_APP_KEYCLOAK_REALM: ${KEYCLOAK_REALM:-4genthub}
      REACT_APP_KEYCLOAK_CLIENT_ID: ${KEYCLOAK_CLIENT_ID:-mcp-frontend}
    ports:
      - "${FRONTEND_PORT:-3800}:3800"
    volumes:
      - ./4genthub-frontend:/app
      - /app/node_modules
    networks:
      - 4genthub_network
    restart: unless-stopped

networks:
  4genthub_network:
    driver: bridge
    name: ${DOCKER_NETWORK:-4genthub_clean_network}

volumes:
  postgres_data:
    name: ${POSTGRES_DATA_VOLUME:-4genthub_postgres_data}
  postgres_backup:
    name: ${POSTGRES_BACKUP_VOLUME:-4genthub_postgres_backup}
  pgadmin_data:
    name: 4genthub_pgadmin_data
"""
        
        compose_path = self.root_dir / "docker-compose.clean.yml"
        with open(compose_path, 'w') as f:
            f.write(compose_content)
        
        self.print_step(f"Created Docker Compose file: docker-compose.clean.yml", "✅")
        return compose_path
    
    def create_startup_script(self):
        """Create a startup script for the clean setup"""
        self.print_header("Creating Startup Script")
        
        script_content = """#!/bin/bash
# =============================================================================
# CLEAN STARTUP SCRIPT - PostgreSQL Docker + Keycloak Cloud
# =============================================================================

set -e

echo "=========================================="
echo " Starting 4genthub Clean Setup"
echo "=========================================="

# Check if .env.clean exists
if [ ! -f .env.clean ]; then
    echo "❌ .env.clean not found. Please run setup-clean-postgres-keycloak.py first"
    exit 1
fi

# Check if Keycloak settings are configured
if grep -q "your-keycloak-domain.com" .env.clean; then
    echo "⚠️  WARNING: Keycloak settings not configured!"
    echo "Please update KEYCLOAK_URL and KEYCLOAK_CLIENT_SECRET in .env.clean"
    echo ""
    read -p "Do you want to continue anyway? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Use clean environment
cp .env.clean .env
echo "✅ Using clean environment configuration"

# Stop any existing containers
echo "🔄 Stopping existing containers..."
docker-compose -f docker-compose.clean.yml down 2>/dev/null || true

# Start PostgreSQL first
echo "🔄 Starting PostgreSQL..."
docker-compose -f docker-compose.clean.yml up -d postgres

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if docker-compose -f docker-compose.clean.yml exec postgres pg_isready -U postgres >/dev/null 2>&1; then
        echo "✅ PostgreSQL is ready"
        break
    fi
    echo -n "."
    sleep 1
done

# Initialize database
echo "🔄 Initializing database..."
docker-compose -f docker-compose.clean.yml exec postgres psql -U postgres -c "CREATE DATABASE 4genthub;" 2>/dev/null || echo "Database already exists"

# Start PgAdmin (optional)
echo "🔄 Starting PgAdmin..."
docker-compose -f docker-compose.clean.yml up -d pgadmin

# Start backend
echo "🔄 Starting backend..."
docker-compose -f docker-compose.clean.yml up -d backend

# Start frontend
echo "🔄 Starting frontend..."
docker-compose -f docker-compose.clean.yml up -d frontend

echo ""
echo "=========================================="
echo " Clean Setup Started Successfully!"
echo "=========================================="
echo ""
echo "Services:"
echo "  📦 PostgreSQL:  http://localhost:5432"
echo "  🔧 PgAdmin:     http://localhost:5050"
echo "  🚀 Backend:     http://localhost:8001"
echo "  🎨 Frontend:    http://localhost:3800"
echo ""
echo "Database:"
echo "  Host: localhost"
echo "  Port: 5432"
echo "  Database: 4genthub"
echo "  User: postgres"
echo ""
echo "⚠️  Remember to configure your Keycloak cloud instance!"
echo ""
echo "To view logs: docker-compose -f docker-compose.clean.yml logs -f"
echo "To stop: docker-compose -f docker-compose.clean.yml down"
"""
        
        script_path = self.root_dir / "start-clean.sh"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make executable
        os.chmod(script_path, 0o755)
        
        self.print_step(f"Created startup script: start-clean.sh", "✅")
        return script_path
    
    def run(self):
        """Run the complete setup process"""
        self.print_header("4genthub Clean Setup - PostgreSQL + Keycloak")
        
        print("\nThis script will:")
        print("1. Remove all Supabase backward compatibility code")
        print("2. Configure PostgreSQL Docker for local database")
        print("3. Set up Keycloak cloud authentication")
        print("4. Create clean configuration files")
        print("")
        
        response = input("Do you want to continue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Setup cancelled.")
            return False
        
        # Check Docker
        if not self.check_docker():
            print("\n❌ Docker is required. Please install Docker and try again.")
            return False
        
        # Remove Supabase references
        self.remove_supabase_references()
        
        # Create configuration files
        env_path = self.create_env_file()
        compose_path = self.create_docker_compose()
        script_path = self.create_startup_script()
        
        # Print summary
        self.print_header("Setup Complete!")
        
        print("\n✅ Clean setup completed successfully!")
        print("\nNext steps:")
        print("1. Update Keycloak settings in .env.clean:")
        print("   - KEYCLOAK_URL")
        print("   - KEYCLOAK_CLIENT_SECRET")
        print("   - KEYCLOAK_REALM (if different)")
        print("")
        print("2. Start the system:")
        print("   ./start-clean.sh")
        print("")
        print("3. Access the services:")
        print("   - Backend:  http://localhost:8001")
        print("   - Frontend: http://localhost:3800")
        print("   - PgAdmin:  http://localhost:5050")
        print("")
        
        if self.warnings:
            print("\n⚠️  Warnings:")
            for warning in self.warnings:
                print(f"   - {warning}")
        
        if self.errors:
            print("\n❌ Errors:")
            for error in self.errors:
                print(f"   - {error}")
            return False
        
        return True

if __name__ == "__main__":
    manager = SetupManager()
    success = manager.run()
    sys.exit(0 if success else 1)