#!/bin/bash

# =============================================================================
# PostgreSQL Docker + Keycloak Cloud Setup Script
# =============================================================================
# This script sets up PostgreSQL Docker locally and configures Keycloak cloud
# authentication for the DhafnckMCP system.
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}PostgreSQL Docker + Keycloak Cloud Setup${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    exit 1
fi

# Function to generate secure password
generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-25
}

# =============================================================================
# Step 1: Create production environment file
# =============================================================================
echo -e "\n${YELLOW}Step 1: Setting up environment configuration...${NC}"

if [ ! -f .env.production ]; then
    echo -e "${GREEN}Creating .env.production file...${NC}"
    
    # Generate secure passwords
    DB_PASSWORD=$(generate_password)
    MCP_SECRET=$(generate_password)
    PGADMIN_PASSWORD=$(generate_password)
    
    cat > .env.production <<EOF
# =============================================================================
# PRODUCTION CONFIGURATION - POSTGRESQL DOCKER + KEYCLOAK CLOUD
# =============================================================================
# Generated: $(date)
# =============================================================================

# Environment
ENV=production
NODE_ENV=production
APP_ENV=production
APP_DEBUG=false
APP_LOG_LEVEL=INFO

# PostgreSQL Database (Docker Container)
DATABASE_TYPE=postgresql
DATABASE_HOST=postgres  # Use 'postgres' for Docker Compose
DATABASE_PORT=5432
DATABASE_NAME=dhafnck_mcp_prod
DATABASE_USER=dhafnck_user
DATABASE_PASSWORD=${DB_PASSWORD}
DATABASE_SSL_MODE=prefer

# Connection URL
DATABASE_URL=postgresql://dhafnck_user:${DB_PASSWORD}@postgres:5432/dhafnck_mcp_prod?sslmode=prefer

# Connection Pool
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600

# Keycloak Authentication (UPDATE WITH YOUR CLOUD INSTANCE)
AUTH_ENABLED=true
AUTH_PROVIDER=keycloak
KEYCLOAK_URL=https://your-keycloak.cloud.provider.com  # UPDATE THIS
KEYCLOAK_REALM=dhafnck-mcp
KEYCLOAK_CLIENT_ID=mcp-backend
KEYCLOAK_CLIENT_SECRET=your-client-secret-here  # UPDATE THIS
KEYCLOAK_VERIFY_TOKEN_AUDIENCE=true
KEYCLOAK_TOKEN_CACHE_TTL=300
KEYCLOAK_PUBLIC_KEY_CACHE_TTL=3600
KEYCLOAK_SSL_VERIFY=true

# MCP Server
MCP_HOST=0.0.0.0
MCP_PORT=8001
MCP_SECRET_KEY=${MCP_SECRET}
MCP_WORKERS=4

# Frontend
FRONTEND_URL=http://localhost:3800
FRONTEND_PORT=3800

# CORS
CORS_ORIGINS=http://localhost:3800,http://localhost:8001
CORS_ALLOW_CREDENTIALS=true
CORS_MAX_AGE=3600

# JWT (Keycloak RS256)
JWT_SECRET_KEY=this-is-overridden-by-keycloak-public-key
JWT_ALGORITHM=RS256
JWT_EXPIRATION_MINUTES=60
JWT_REFRESH_EXPIRATION_DAYS=30

# Docker
COMPOSE_PROJECT_NAME=dhafnck-mcp-prod
DOCKER_NETWORK=dhafnck_network

# Features
FEATURE_VISION_SYSTEM=true
FEATURE_HIERARCHICAL_CONTEXT=true
FEATURE_AUTO_COMPACT=true
FEATURE_MULTI_AGENT=true
FEATURE_RATE_LIMITING=true
FEATURE_REQUEST_LOGGING=true

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
RATE_LIMIT_PER_DAY=10000

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
ENABLE_HEALTH_CHECK=true
HEALTH_CHECK_INTERVAL=30

# Logging
LOG_FORMAT=json
LOG_FILE=/var/log/dhafnck-mcp/app.log
LOG_MAX_SIZE=100M
LOG_BACKUP_COUNT=10
LOG_LEVEL=info

# PgAdmin
PGADMIN_EMAIL=admin@dhafnck.com
PGADMIN_PASSWORD=${PGADMIN_PASSWORD}
EOF

    echo -e "${GREEN}Created .env.production with secure passwords${NC}"
    echo -e "${YELLOW}⚠️  IMPORTANT: Update KEYCLOAK_URL and KEYCLOAK_CLIENT_SECRET with your values${NC}"
else
    echo -e "${YELLOW}.env.production already exists, skipping...${NC}"
fi

# =============================================================================
# Step 2: Create Docker network
# =============================================================================
echo -e "\n${YELLOW}Step 2: Creating Docker network...${NC}"

if ! docker network ls | grep -q dhafnck_network; then
    docker network create dhafnck_network
    echo -e "${GREEN}Created Docker network: dhafnck_network${NC}"
else
    echo -e "${YELLOW}Docker network already exists${NC}"
fi

# =============================================================================
# Step 3: Create init.sql script for PostgreSQL
# =============================================================================
echo -e "\n${YELLOW}Step 3: Creating PostgreSQL initialization script...${NC}"

mkdir -p dhafnck_mcp_main/scripts

cat > dhafnck_mcp_main/scripts/init.sql <<'EOF'
-- PostgreSQL Initialization Script
-- Creates database and user if they don't exist

-- Create database (if not exists)
SELECT 'CREATE DATABASE dhafnck_mcp_prod'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'dhafnck_mcp_prod')\gexec

-- Grant all privileges
GRANT ALL PRIVILEGES ON DATABASE dhafnck_mcp_prod TO dhafnck_user;

-- Connect to the database
\c dhafnck_mcp_prod;

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS public;

-- Grant schema permissions
GRANT ALL ON SCHEMA public TO dhafnck_user;
GRANT CREATE ON SCHEMA public TO dhafnck_user;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
EOF

echo -e "${GREEN}Created PostgreSQL initialization script${NC}"

# =============================================================================
# Step 4: Start PostgreSQL container
# =============================================================================
echo -e "\n${YELLOW}Step 4: Starting PostgreSQL Docker container...${NC}"

# Copy .env.production to .env for Docker Compose
cp .env.production .env

# Start PostgreSQL service
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
sleep 5

# Check if PostgreSQL is running
if docker-compose ps postgres | grep -q "Up"; then
    echo -e "${GREEN}PostgreSQL is running${NC}"
    
    # Test connection
    if docker exec dhafnck-postgres pg_isready -U dhafnck_user -d dhafnck_mcp_prod &> /dev/null; then
        echo -e "${GREEN}PostgreSQL connection successful${NC}"
    else
        echo -e "${YELLOW}Waiting for PostgreSQL to accept connections...${NC}"
        sleep 5
    fi
else
    echo -e "${RED}PostgreSQL failed to start${NC}"
    exit 1
fi

# =============================================================================
# Step 5: Display Keycloak configuration instructions
# =============================================================================
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\n${YELLOW}Next Steps for Keycloak Configuration:${NC}"
echo -e "1. Update .env.production with your Keycloak cloud URL and credentials:"
echo -e "   - KEYCLOAK_URL=https://your-keycloak-instance.com"
echo -e "   - KEYCLOAK_CLIENT_SECRET=your-client-secret"
echo -e ""
echo -e "2. In your Keycloak admin console, create:"
echo -e "   - Realm: dhafnck-mcp"
echo -e "   - Client: mcp-backend (confidential)"
echo -e "   - Roles: mcp-user, mcp-tools, mcp-admin, mcp-developer"
echo -e "   - Add roles to users who need MCP access"
echo -e ""
echo -e "3. Configure client settings:"
echo -e "   - Access Type: confidential"
echo -e "   - Valid Redirect URIs: http://localhost:8001/*"
echo -e "   - Web Origins: http://localhost:3800"
echo -e ""
echo -e "4. Start the full stack:"
echo -e "   ${GREEN}docker-compose up -d${NC}"
echo -e ""
echo -e "5. Start with PgAdmin (optional):"
echo -e "   ${GREEN}docker-compose --profile tools up -d${NC}"
echo -e "   Access at: http://localhost:5050"

# =============================================================================
# Display connection info
# =============================================================================
echo -e "\n${GREEN}Database Connection Info:${NC}"
echo -e "Host: localhost"
echo -e "Port: 5432"
echo -e "Database: dhafnck_mcp_prod"
echo -e "User: dhafnck_user"
echo -e "Password: (check .env.production)"

echo -e "\n${GREEN}Services:${NC}"
echo -e "PostgreSQL: localhost:5432"
echo -e "MCP Server: http://localhost:8001"
echo -e "Frontend: http://localhost:3800"
echo -e "PgAdmin: http://localhost:5050 (if started with --profile tools)"

echo -e "\n${YELLOW}To stop services:${NC}"
echo -e "docker-compose down"

echo -e "\n${YELLOW}To view logs:${NC}"
echo -e "docker-compose logs -f [service_name]"

echo -e "\n${GREEN}Setup script completed successfully!${NC}"