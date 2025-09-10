#!/bin/bash
# Quick Start Script for PostgreSQL Docker + Keycloak Cloud Setup

set -e

echo "=================================================="
echo "DhafnckMCP Quick Start - PostgreSQL + Keycloak"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    echo "Please install Docker from https://ai_docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✅ Docker found${NC}"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    echo "Please install Docker Compose from https://ai_docs.docker.com/compose/install/"
    exit 1
fi
echo -e "${GREEN}✅ Docker Compose found${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    echo "Please install Python 3.11 or higher"
    exit 1
fi
echo -e "${GREEN}✅ Python 3 found${NC}"

echo ""
echo "=================================================="
echo "Step 1: Environment Configuration"
echo "=================================================="

# Check if .env exists
if [ ! -f "../.env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from template...${NC}"
    
    # Create .env file with basic configuration
    cat > ../.env << 'EOF'
# =============================================================================
# PRODUCTION CONFIGURATION - POSTGRESQL DOCKER + KEYCLOAK CLOUD
# =============================================================================
ENV=production
NODE_ENV=production
APP_ENV=production
APP_DEBUG=false
APP_LOG_LEVEL=INFO

# =============================================================================
# POSTGRESQL DATABASE (Docker Container)
# =============================================================================
DATABASE_TYPE=postgresql
DATABASE_HOST=postgres
DATABASE_PORT=5432
DATABASE_NAME=dhafnck_mcp_prod
DATABASE_USER=dhafnck_user
DATABASE_PASSWORD=ChangeThisSecurePassword2025!
DATABASE_SSL_MODE=prefer

DATABASE_URL=postgresql://dhafnck_user:ChangeThisSecurePassword2025!@postgres:5432/dhafnck_mcp_prod?sslmode=prefer

# Connection Pool Settings
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600

# =============================================================================
# KEYCLOAK AUTHENTICATION (Cloud Service)
# =============================================================================
AUTH_ENABLED=false  # Set to true when Keycloak is configured
AUTH_PROVIDER=keycloak

# TODO: Configure these with your Keycloak instance
KEYCLOAK_URL=https://your-keycloak.cloud.provider.com
KEYCLOAK_REALM=dhafnck-mcp
KEYCLOAK_CLIENT_ID=mcp-backend
KEYCLOAK_CLIENT_SECRET=your-client-secret-here

KEYCLOAK_VERIFY_TOKEN_AUDIENCE=true
KEYCLOAK_TOKEN_CACHE_TTL=300
KEYCLOAK_PUBLIC_KEY_CACHE_TTL=3600
KEYCLOAK_SSL_VERIFY=true

# =============================================================================
# MCP SERVER
# =============================================================================
MCP_HOST=0.0.0.0
MCP_PORT=8001
JWT_SECRET_KEY=generate-a-secure-64-char-string-for-production-use-here-1234567890
MCP_WORKERS=4

# =============================================================================
# JWT CONFIGURATION
# =============================================================================
JWT_ALGORITHM=RS256
JWT_EXPIRATION_MINUTES=60
JWT_REFRESH_EXPIRATION_DAYS=30

# =============================================================================
# FRONTEND
# =============================================================================
FRONTEND_URL=http://localhost:3800
FRONTEND_PORT=3800

# =============================================================================
# CORS
# =============================================================================
CORS_ORIGINS=http://localhost:3800,http://localhost:8001
CORS_ALLOW_CREDENTIALS=true
CORS_MAX_AGE=3600

# =============================================================================
# DOCKER
# =============================================================================
COMPOSE_PROJECT_NAME=dhafnck-mcp-prod
DOCKER_NETWORK=dhafnck_network

# =============================================================================
# FEATURES
# =============================================================================
FEATURE_VISION_SYSTEM=true
FEATURE_HIERARCHICAL_CONTEXT=true
FEATURE_AUTO_COMPACT=true
FEATURE_MULTI_AGENT=true
FEATURE_RATE_LIMITING=true
FEATURE_REQUEST_LOGGING=true
EOF
    
    echo -e "${GREEN}✅ .env file created${NC}"
    echo -e "${YELLOW}⚠️  Please edit .env to add your Keycloak configuration${NC}"
else
    echo -e "${GREEN}✅ .env file exists${NC}"
fi

echo ""
echo "=================================================="
echo "Step 2: Start PostgreSQL Docker Container"
echo "=================================================="

cd ..

# Stop any existing containers
echo "Stopping any existing containers..."
docker-compose down 2>/dev/null || true

# Start PostgreSQL
echo "Starting PostgreSQL container..."
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if docker-compose exec postgres pg_isready -U dhafnck_user -d dhafnck_mcp_prod &>/dev/null; then
        echo -e "${GREEN}✅ PostgreSQL is ready!${NC}"
        break
    fi
    echo -n "."
    sleep 2
done

echo ""
echo "=================================================="
echo "Step 3: Initialize Database"
echo "=================================================="

# Run initialization script
echo "Initializing database schema..."
cd dhafnck_mcp_main
python scripts/init_postgres_docker.py

echo ""
echo "=================================================="
echo "Step 4: Start MCP Server"
echo "=================================================="

cd ..
echo "Starting MCP server..."
docker-compose up -d mcp-server

# Wait for MCP server to be ready
echo "Waiting for MCP server to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8001/health &>/dev/null; then
        echo -e "${GREEN}✅ MCP server is ready!${NC}"
        break
    fi
    echo -n "."
    sleep 2
done

echo ""
echo "=================================================="
echo "Step 5: Verify Installation"
echo "=================================================="

# Check health endpoint
echo "Checking MCP server health..."
HEALTH=$(curl -s http://localhost:8001/health)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ MCP server is healthy${NC}"
    echo "$HEALTH" | python3 -m json.tool
else
    echo -e "${RED}❌ MCP server health check failed${NC}"
fi

echo ""
echo "=================================================="
echo "🎉 SETUP COMPLETE!"
echo "=================================================="
echo ""
echo "Services running:"
echo "  - PostgreSQL: localhost:5432"
echo "  - MCP Server: http://localhost:8001"
echo "  - PgAdmin: http://localhost:5050 (if enabled)"
echo ""
echo "Next steps:"
echo "  1. Configure Keycloak:"
echo "     - Edit .env with your Keycloak cloud URL and credentials"
echo "     - Set AUTH_ENABLED=true in .env"
echo ""
echo "  2. Test Keycloak integration:"
echo "     cd dhafnck_mcp_main"
echo "     python scripts/test_keycloak_integration.py"
echo ""
echo "  3. View logs:"
echo "     docker-compose logs -f"
echo ""
echo "  4. Stop services:"
echo "     docker-compose down"
echo ""
echo "=================================================="