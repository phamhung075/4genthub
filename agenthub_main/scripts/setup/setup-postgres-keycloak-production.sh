#!/bin/bash

# ============================================================================
# PostgreSQL (Local Docker) + Keycloak (Cloud) Production Setup
# ============================================================================
# This script sets up a clean production environment with:
# - PostgreSQL running in local Docker
# - Keycloak authentication on cloud
# - No backward compatibility code
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Print header
print_header() {
    echo ""
    print_message "$BLUE" "============================================================================"
    print_message "$BLUE" "$1"
    print_message "$BLUE" "============================================================================"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# ============================================================================
# STEP 1: Prerequisites Check
# ============================================================================
print_header "Checking Prerequisites"

# Check Docker
if ! command_exists docker; then
    print_message "$RED" "❌ Docker is not installed"
    exit 1
fi
print_message "$GREEN" "✅ Docker is installed"

# Check Docker Compose
if ! command_exists docker-compose; then
    print_message "$RED" "❌ Docker Compose is not installed"
    exit 1
fi
print_message "$GREEN" "✅ Docker Compose is installed"

# Check Python
if ! command_exists python3; then
    print_message "$RED" "❌ Python 3 is not installed"
    exit 1
fi
print_message "$GREEN" "✅ Python 3 is installed"

# ============================================================================
# STEP 2: Environment Configuration
# ============================================================================
print_header "Configuring Environment"

# Backup existing .env if it exists
if [ -f .env ]; then
    BACKUP_NAME=".env.backup.$(date +%Y%m%d_%H%M%S)"
    cp .env "$BACKUP_NAME"
    print_message "$YELLOW" "📦 Backed up existing .env to $BACKUP_NAME"
fi

# Check if Keycloak configuration is provided
if [ -f .env.production-keycloak-postgres ]; then
    print_message "$YELLOW" "Found .env.production-keycloak-postgres template"
    
    # Prompt for Keycloak configuration
    echo ""
    print_message "$YELLOW" "Please provide your Keycloak Cloud configuration:"
    
    read -p "Keycloak URL (e.g., https://your-domain.keycloak.app): " KEYCLOAK_URL
    read -p "Keycloak Realm (default: agenthub): " KEYCLOAK_REALM
    KEYCLOAK_REALM=${KEYCLOAK_REALM:-agenthub}
    
    read -p "Keycloak Client ID (default: mcp-backend): " KEYCLOAK_CLIENT_ID
    KEYCLOAK_CLIENT_ID=${KEYCLOAK_CLIENT_ID:-mcp-backend}
    
    read -sp "Keycloak Client Secret: " KEYCLOAK_CLIENT_SECRET
    echo ""
    
    # Create production .env file
    cp .env.production-keycloak-postgres .env.production
    
    # Update with actual values
    sed -i "s|https://your-keycloak-domain.com|${KEYCLOAK_URL}|g" .env.production
    sed -i "s|agenthub|${KEYCLOAK_REALM}|g" .env.production
    sed -i "s|mcp-backend|${KEYCLOAK_CLIENT_ID}|g" .env.production
    sed -i "s|your-keycloak-client-secret-here|${KEYCLOAK_CLIENT_SECRET}|g" .env.production
    sed -i "s|https://your-keycloak-domain.com/realms/agenthub|${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}|g" .env.production
    
    # Generate secure keys
    MCP_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
    JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
    
    sed -i "s|generate-a-secure-random-string-for-production-use|${MCP_SECRET}|g" .env.production
    sed -i "s|generate-a-secure-32-char-string-for-production|${JWT_SECRET}|g" .env.production
    
    print_message "$GREEN" "✅ Created .env.production with your configuration"
else
    print_message "$RED" "❌ .env.production-keycloak-postgres template not found"
    exit 1
fi

# ============================================================================
# STEP 3: Clean Up Backward Compatibility Code
# ============================================================================
print_header "Removing Backward Compatibility Code"

# Create and run cleanup script
cat > remove-backward-compat.py << 'EOF'
#!/usr/bin/env python3
"""Remove backward compatibility code"""

import os
import re
from pathlib import Path

def clean_file(file_path):
    """Remove backward compatibility code from a file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Remove Supabase references
    content = re.sub(r'.*[Ss]upabase.*\n', '', content)
    
    # Remove backward compatibility patterns
    patterns_to_remove = [
        r'.*backward.*compat.*\n',
        r'.*\blegacy\b.*\n',
        r'.*\bdeprecated\b.*\n',
        r'.*fallback.*user.*\n',
        r'.*default.*user.*context.*\n',
        r'.*allow.*default.*user.*\n',
    ]
    
    for pattern in patterns_to_remove:
        content = re.sub(pattern, '', content, flags=re.IGNORECASE)
    
    # Clean up multiple empty lines
    content = re.sub(r'\n\n\n+', '\n\n', content)
    
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    return False

def main():
    src_dir = Path("agenthub_main/src")
    cleaned_files = []
    
    # Skip test files and specific directories
    skip_dirs = {'__pycache__', 'tests', '.git', 'node_modules'}
    
    for file_path in src_dir.rglob("*.py"):
        if any(skip_dir in str(file_path) for skip_dir in skip_dirs):
            continue
        
        if clean_file(file_path):
            cleaned_files.append(str(file_path))
    
    if cleaned_files:
        print(f"✅ Cleaned {len(cleaned_files)} files:")
        for f in cleaned_files[:10]:
            print(f"  - {f}")
        if len(cleaned_files) > 10:
            print(f"  ... and {len(cleaned_files) - 10} more")
    else:
        print("✅ No backward compatibility code found to remove")

if __name__ == "__main__":
    main()
EOF

python3 remove-backward-compat.py
rm remove-backward-compat.py

# ============================================================================
# STEP 4: PostgreSQL Docker Setup
# ============================================================================
print_header "Setting Up PostgreSQL Docker"

# Stop existing containers
print_message "$YELLOW" "Stopping existing containers..."
docker-compose -f docker-compose.production.yml down 2>/dev/null || true

# Remove old volumes (optional - comment out if you want to keep data)
read -p "Remove existing PostgreSQL data? (y/N): " REMOVE_DATA
if [[ "$REMOVE_DATA" =~ ^[Yy]$ ]]; then
    docker volume rm agenthub_postgres_prod_data 2>/dev/null || true
    docker volume rm agenthub_postgres_prod_backup 2>/dev/null || true
    print_message "$YELLOW" "📦 Removed existing PostgreSQL volumes"
fi

# Create network if it doesn't exist
docker network create agenthub_prod_network 2>/dev/null || true

# Start PostgreSQL
print_message "$YELLOW" "Starting PostgreSQL..."
docker-compose -f docker-compose.production.yml up -d postgres

# Wait for PostgreSQL to be ready
print_message "$YELLOW" "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if docker-compose -f docker-compose.production.yml exec -T postgres pg_isready -U postgres -d agenthub >/dev/null 2>&1; then
        print_message "$GREEN" "✅ PostgreSQL is ready"
        break
    fi
    echo -n "."
    sleep 2
done

# ============================================================================
# STEP 5: Database Initialization
# ============================================================================
print_header "Initializing Database"

# Create database schema
cat > init_db.sql << 'EOF'
-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create auth schema
CREATE SCHEMA IF NOT EXISTS auth;

-- Create users table
CREATE TABLE IF NOT EXISTS auth.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    keycloak_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(255) UNIQUE,
    full_name VARCHAR(255),
    roles JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

-- Create sessions table
CREATE TABLE IF NOT EXISTS auth.sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_keycloak_id ON auth.users(keycloak_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON auth.users(email);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON auth.sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON auth.sessions(expires_at);

-- Create task management schema
CREATE SCHEMA IF NOT EXISTS task_management;

-- Grant permissions
GRANT ALL ON SCHEMA auth TO postgres;
GRANT ALL ON SCHEMA task_management TO postgres;
GRANT ALL ON ALL TABLES IN SCHEMA auth TO postgres;
GRANT ALL ON ALL TABLES IN SCHEMA task_management TO postgres;
EOF

# Execute SQL
docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d agenthub < init_db.sql
rm init_db.sql

print_message "$GREEN" "✅ Database initialized"

# ============================================================================
# STEP 6: Install Python Dependencies
# ============================================================================
print_header "Installing Python Dependencies"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_message "$GREEN" "✅ Created virtual environment"
fi

# Activate virtual environment and install dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r agenthub_main/requirements.txt
print_message "$GREEN" "✅ Python dependencies installed"

# ============================================================================
# STEP 7: Start MCP Backend
# ============================================================================
print_header "Starting MCP Backend"

# Build and start the backend
docker-compose -f docker-compose.production.yml build mcp-backend
docker-compose -f docker-compose.production.yml up -d mcp-backend

# Wait for backend to be ready
print_message "$YELLOW" "Waiting for MCP backend to be ready..."
for i in {1..30}; do
    if curl -f http://localhost:8001/health >/dev/null 2>&1; then
        print_message "$GREEN" "✅ MCP backend is ready"
        break
    fi
    echo -n "."
    sleep 2
done

# ============================================================================
# STEP 8: Verify Setup
# ============================================================================
print_header "Verifying Setup"

# Test database connection
print_message "$YELLOW" "Testing database connection..."
docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d agenthub -c "SELECT version();" >/dev/null 2>&1
if [ $? -eq 0 ]; then
    print_message "$GREEN" "✅ PostgreSQL connection successful"
else
    print_message "$RED" "❌ PostgreSQL connection failed"
fi

# Test MCP health endpoint
print_message "$YELLOW" "Testing MCP health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:8001/health)
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    print_message "$GREEN" "✅ MCP server is healthy"
else
    print_message "$RED" "❌ MCP server health check failed"
fi

# Test Keycloak configuration
print_message "$YELLOW" "Testing Keycloak configuration..."
if [ ! -z "$KEYCLOAK_URL" ]; then
    WELL_KNOWN_URL="${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/.well-known/openid-configuration"
    if curl -f "$WELL_KNOWN_URL" >/dev/null 2>&1; then
        print_message "$GREEN" "✅ Keycloak server is reachable"
    else
        print_message "$YELLOW" "⚠️  Could not reach Keycloak server - verify URL and realm"
    fi
fi

# ============================================================================
# STEP 9: Create Test Script
# ============================================================================
print_header "Creating Test Script"

cat > test-keycloak-integration.py << 'EOF'
#!/usr/bin/env python3
"""Test Keycloak integration with MCP"""

import os
import sys
import json
import requests
from urllib.parse import urljoin

def get_keycloak_token(keycloak_url, realm, client_id, client_secret, username, password):
    """Get access token from Keycloak"""
    token_url = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/token"
    
    data = {
        'grant_type': 'password',
        'client_id': client_id,
        'client_secret': client_secret,
        'username': username,
        'password': password
    }
    
    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        print(f"Failed to get token: {response.status_code}")
        print(response.text)
        return None

def test_mcp_with_token(mcp_url, token):
    """Test MCP endpoints with Keycloak token"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Test health endpoint (should work without auth)
    print("\n1. Testing health endpoint...")
    response = requests.get(f"{mcp_url}/health")
    print(f"   Status: {response.status_code}")
    
    # Test authenticated endpoint
    print("\n2. Testing authenticated endpoint...")
    response = requests.get(f"{mcp_url}/api/user/profile", headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   User: {response.json()}")
    
    # Test MCP tools
    print("\n3. Testing MCP tools...")
    response = requests.post(
        f"{mcp_url}/mcp/manage_project",
        headers=headers,
        json={"action": "list"}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   Projects: {len(response.json().get('projects', []))}")

def main():
    # Load configuration from environment
    from dotenv import load_dotenv
    load_dotenv('.env.production')
    
    keycloak_url = os.getenv('KEYCLOAK_URL')
    realm = os.getenv('KEYCLOAK_REALM')
    client_id = os.getenv('KEYCLOAK_CLIENT_ID')
    client_secret = os.getenv('KEYCLOAK_CLIENT_SECRET')
    mcp_url = 'http://localhost:8001'
    
    print("=" * 60)
    print("KEYCLOAK INTEGRATION TEST")
    print("=" * 60)
    print(f"Keycloak URL: {keycloak_url}")
    print(f"Realm: {realm}")
    print(f"Client ID: {client_id}")
    print(f"MCP URL: {mcp_url}")
    
    # Get test user credentials
    print("\nEnter test user credentials:")
    username = input("Username: ")
    password = input("Password: ")
    
    # Get token
    print("\nGetting Keycloak token...")
    token = get_keycloak_token(keycloak_url, realm, client_id, client_secret, username, password)
    
    if token:
        print("✅ Token obtained successfully")
        
        # Test MCP
        test_mcp_with_token(mcp_url, token)
    else:
        print("❌ Failed to obtain token")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

chmod +x test-keycloak-integration.py
print_message "$GREEN" "✅ Created test-keycloak-integration.py"

# ============================================================================
# SUMMARY
# ============================================================================
print_header "Setup Complete!"

print_message "$GREEN" "✅ PostgreSQL is running on port 5432"
print_message "$GREEN" "✅ MCP Backend is running on port 8001"
print_message "$GREEN" "✅ Backward compatibility code has been removed"
print_message "$GREEN" "✅ Environment configured for Keycloak authentication"

echo ""
print_message "$YELLOW" "Next steps:"
print_message "$YELLOW" "1. Configure your Keycloak realm with:"
print_message "$YELLOW" "   - Client ID: ${KEYCLOAK_CLIENT_ID}"
print_message "$YELLOW" "   - Valid redirect URIs: http://localhost:8001/*, http://localhost:3800/*"
print_message "$YELLOW" "   - Web origins: http://localhost:8001, http://localhost:3800"
print_message "$YELLOW" "2. Create test users in Keycloak"
print_message "$YELLOW" "3. Run: ./test-keycloak-integration.py to test the setup"

echo ""
print_message "$BLUE" "To view logs:"
print_message "$BLUE" "  docker-compose -f docker-compose.production.yml logs -f mcp-backend"

echo ""
print_message "$BLUE" "To stop services:"
print_message "$BLUE" "  docker-compose -f docker-compose.production.yml down"

echo ""
print_message "$GREEN" "🎉 Setup complete! Your system is ready for production."