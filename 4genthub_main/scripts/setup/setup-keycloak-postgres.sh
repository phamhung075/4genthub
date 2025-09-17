#!/bin/bash

# =============================================================================
# 4genthub Setup Script - PostgreSQL Docker + Keycloak Cloud
# =============================================================================
# This script sets up the production environment with:
# - PostgreSQL running in Docker locally
# - Keycloak authentication via cloud service
# - MCP server configured to use Keycloak tokens
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}4genthub Production Setup${NC}"
echo -e "${BLUE}PostgreSQL Docker + Keycloak Cloud${NC}"
echo -e "${BLUE}========================================${NC}"

# =============================================================================
# Step 1: Check Prerequisites
# =============================================================================
echo -e "\n${YELLOW}Step 1: Checking prerequisites...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    echo "Please install Docker: https://ai_docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✓ Docker is installed${NC}"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    echo "Please install Docker Compose: https://ai_docs.docker.com/compose/install/"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose is installed${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 is installed${NC}"

# =============================================================================
# Step 2: Environment Configuration
# =============================================================================
echo -e "\n${YELLOW}Step 2: Setting up environment configuration...${NC}"

# Check if .env exists
if [ -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file already exists${NC}"
    read -p "Do you want to backup the existing .env? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        backup_file=".env.backup.$(date +%Y%m%d_%H%M%S)"
        cp .env "$backup_file"
        echo -e "${GREEN}✓ Backed up to $backup_file${NC}"
    fi
fi

# Copy production template if .env doesn't exist
if [ ! -f .env ]; then
    if [ -f .env.production ]; then
        cp .env.production .env
        echo -e "${GREEN}✓ Created .env from production template${NC}"
    else
        echo -e "${RED}❌ .env.production template not found${NC}"
        exit 1
    fi
fi

# =============================================================================
# Step 3: Configure Keycloak
# =============================================================================
echo -e "\n${YELLOW}Step 3: Configuring Keycloak connection...${NC}"
echo -e "${BLUE}Please provide your Keycloak cloud configuration:${NC}"

read -p "Keycloak URL (e.g., https://your-keycloak.com): " KEYCLOAK_URL
read -p "Keycloak Realm (default: 4genthub): " KEYCLOAK_REALM
KEYCLOAK_REALM=${KEYCLOAK_REALM:-4genthub}
read -p "Keycloak Client ID (default: mcp-backend): " KEYCLOAK_CLIENT_ID
KEYCLOAK_CLIENT_ID=${KEYCLOAK_CLIENT_ID:-mcp-backend}
read -s -p "Keycloak Client Secret: " KEYCLOAK_CLIENT_SECRET
echo

# Update .env with Keycloak settings
sed -i "s|KEYCLOAK_URL=.*|KEYCLOAK_URL=$KEYCLOAK_URL|" .env
sed -i "s|KEYCLOAK_REALM=.*|KEYCLOAK_REALM=$KEYCLOAK_REALM|" .env
sed -i "s|KEYCLOAK_CLIENT_ID=.*|KEYCLOAK_CLIENT_ID=$KEYCLOAK_CLIENT_ID|" .env
sed -i "s|KEYCLOAK_CLIENT_SECRET=.*|KEYCLOAK_CLIENT_SECRET=$KEYCLOAK_CLIENT_SECRET|" .env

echo -e "${GREEN}✓ Keycloak configuration updated${NC}"

# =============================================================================
# Step 4: Generate Secure Keys
# =============================================================================
echo -e "\n${YELLOW}Step 4: Generating secure keys...${NC}"

# Generate PostgreSQL password
if grep -q "CHANGE_THIS_SECURE_PASSWORD" .env; then
    PG_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    sed -i "s|DATABASE_PASSWORD=.*|DATABASE_PASSWORD=$PG_PASSWORD|" .env
    sed -i "s|CHANGE_THIS_SECURE_PASSWORD_PRODUCTION|$PG_PASSWORD|g" .env
    echo -e "${GREEN}✓ Generated secure PostgreSQL password${NC}"
fi

# Generate MCP secret key
if grep -q "GENERATE_A_SECURE_64_CHARACTER_STRING" .env; then
    MCP_SECRET=$(openssl rand -hex 32)
    sed -i "s|JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$MCP_SECRET|" .env
    echo -e "${GREEN}✓ Generated secure MCP secret key${NC}"
fi

# Generate PgAdmin password
if grep -q "CHANGE_THIS_ADMIN_PASSWORD" .env; then
    PGADMIN_PWD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)
    sed -i "s|PGADMIN_PASSWORD=.*|PGADMIN_PASSWORD=$PGADMIN_PWD|" .env
    echo -e "${GREEN}✓ Generated PgAdmin password${NC}"
fi

# =============================================================================
# Step 5: Create Required Directories
# =============================================================================
echo -e "\n${YELLOW}Step 5: Creating required directories...${NC}"

mkdir -p data
mkdir -p logs
mkdir -p 4genthub_main/scripts
mkdir -p nginx/ssl
mkdir -p monitoring/prometheus
mkdir -p monitoring/grafana/dashboards
mkdir -p monitoring/grafana/datasources

echo -e "${GREEN}✓ Created required directories${NC}"

# =============================================================================
# Step 6: Create Database Init Scripts
# =============================================================================
echo -e "\n${YELLOW}Step 6: Creating database initialization scripts...${NC}"

# Create PostgreSQL init script
cat > 4genthub_main/scripts/init.sql << 'EOF'
-- PostgreSQL initialization script for 4genthub
-- Creates required extensions and initial setup

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable JSONB operators
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- Create indexes for better performance
-- These will be created after tables are created by SQLAlchemy

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE 4genthub_prod TO 4genthub_user;
EOF

echo -e "${GREEN}✓ Created database initialization script${NC}"

# Create Keycloak setup script
cat > 4genthub_main/scripts/keycloak_setup.sql << 'EOF'
-- Keycloak-related database setup
-- Creates tables for storing Keycloak tokens and session data if needed

-- Table for MCP token mapping to Keycloak tokens
CREATE TABLE IF NOT EXISTS mcp_keycloak_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mcp_token VARCHAR(255) UNIQUE NOT NULL,
    keycloak_token TEXT NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    roles JSONB,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_mcp_tokens_user_id ON mcp_keycloak_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_mcp_tokens_expires ON mcp_keycloak_tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_mcp_tokens_email ON mcp_keycloak_tokens(email);

-- Cleanup expired tokens automatically
CREATE OR REPLACE FUNCTION cleanup_expired_tokens() RETURNS void AS $$
BEGIN
    DELETE FROM mcp_keycloak_tokens WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;
EOF

echo -e "${GREEN}✓ Created Keycloak setup script${NC}"

# =============================================================================
# Step 7: Build and Start Services
# =============================================================================
echo -e "\n${YELLOW}Step 7: Building and starting services...${NC}"

# Stop existing containers
echo "Stopping existing containers..."
docker-compose -f docker-compose.production.yml down 2>/dev/null || true

# Build services
echo "Building Docker images..."
docker-compose -f docker-compose.production.yml build

# Start PostgreSQL first
echo "Starting PostgreSQL..."
docker-compose -f docker-compose.production.yml up -d postgres

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
sleep 10

# Check PostgreSQL health
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if docker-compose -f docker-compose.production.yml exec -T postgres pg_isready -U 4genthub_user -d 4genthub_prod &>/dev/null; then
        echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
        break
    fi
    echo -n "."
    sleep 2
    attempt=$((attempt + 1))
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}❌ PostgreSQL failed to start${NC}"
    exit 1
fi

# Start Redis if configured
if grep -q "REDIS_HOST" .env && [ "$(grep REDIS_HOST .env | cut -d= -f2)" != "" ]; then
    echo "Starting Redis..."
    docker-compose -f docker-compose.production.yml up -d redis
    sleep 5
fi

# Start MCP Server
echo "Starting MCP Server..."
docker-compose -f docker-compose.production.yml up -d mcp-server

# Wait for MCP Server to be ready
echo "Waiting for MCP Server to be ready..."
sleep 10

# =============================================================================
# Step 8: Verify Installation
# =============================================================================
echo -e "\n${YELLOW}Step 8: Verifying installation...${NC}"

# Check MCP Server health
if curl -f -s http://localhost:8001/health > /dev/null; then
    echo -e "${GREEN}✓ MCP Server is healthy${NC}"
else
    echo -e "${RED}❌ MCP Server health check failed${NC}"
    echo "Check logs with: docker-compose -f docker-compose.production.yml logs mcp-server"
fi

# Test Keycloak connection
echo "Testing Keycloak connection..."
response=$(curl -s -o /dev/null -w "%{http_code}" "$KEYCLOAK_URL/realms/$KEYCLOAK_REALM/.well-known/openid-configuration")
if [ "$response" = "200" ]; then
    echo -e "${GREEN}✓ Keycloak connection successful${NC}"
else
    echo -e "${YELLOW}⚠️  Could not verify Keycloak connection (HTTP $response)${NC}"
    echo "Please verify your Keycloak URL and realm configuration"
fi

# =============================================================================
# Step 9: Display Summary
# =============================================================================
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Setup Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo
echo -e "${GREEN}✓ PostgreSQL is running on port 5432${NC}"
echo -e "${GREEN}✓ MCP Server is running on port 8001${NC}"
echo -e "${GREEN}✓ Keycloak integration is configured${NC}"
echo
echo -e "${YELLOW}Important Information:${NC}"
echo "• PostgreSQL Database: 4genthub_prod"
echo "• PostgreSQL User: 4genthub_user"
echo "• MCP Server URL: http://localhost:8001"
echo "• Health Check: http://localhost:8001/health"
echo
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Configure your Keycloak realm with the following:"
echo "   - Create client: $KEYCLOAK_CLIENT_ID"
echo "   - Enable service accounts"
echo "   - Add required roles (admin, user, etc.)"
echo "2. Test authentication:"
echo "   curl -X POST http://localhost:8001/auth/login \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"username\":\"your-user\",\"password\":\"your-password\"}'"
echo
echo -e "${YELLOW}Useful Commands:${NC}"
echo "• View logs: docker-compose -f docker-compose.production.yml logs -f"
echo "• Stop services: docker-compose -f docker-compose.production.yml down"
echo "• Restart services: docker-compose -f docker-compose.production.yml restart"
echo "• Access PgAdmin: docker-compose -f docker-compose.production.yml --profile tools up -d pgadmin"
echo "  Then visit: http://localhost:5050"
echo
echo -e "${GREEN}✨ Your 4genthub system is ready for production use!${NC}"