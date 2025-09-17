#!/bin/bash

# =============================================================================
# Quick Start Script for PostgreSQL + Keycloak Setup
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}"
echo "============================================================"
echo "     agenthub Quick Start"
echo "     PostgreSQL Docker + Keycloak Cloud"
echo "============================================================"
echo -e "${NC}"

# Step 1: Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker first.${NC}"
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose not found. Please install Docker Compose first.${NC}"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.8+${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All prerequisites met${NC}"

# Step 2: Setup environment file
echo -e "\n${BLUE}Setting up environment configuration...${NC}"

if [ ! -f ".env.production" ]; then
    if [ -f ".env.production-clean" ]; then
        cp .env.production-clean .env.production
        echo -e "${GREEN}✅ Created .env.production from template${NC}"
    else
        echo -e "${RED}❌ No environment template found${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  .env.production already exists${NC}"
fi

# Step 3: Get Keycloak configuration
echo -e "\n${BLUE}Keycloak Configuration${NC}"
echo "Please provide your Keycloak cloud details:"
echo ""

read -p "Keycloak URL (e.g., https://keycloak.yourdomain.com): " KEYCLOAK_URL
read -p "Keycloak Realm [agenthub]: " KEYCLOAK_REALM
KEYCLOAK_REALM=${KEYCLOAK_REALM:-agenthub}
read -p "Keycloak Client ID [mcp-backend]: " KEYCLOAK_CLIENT_ID
KEYCLOAK_CLIENT_ID=${KEYCLOAK_CLIENT_ID:-mcp-backend}
read -s -p "Keycloak Client Secret: " KEYCLOAK_CLIENT_SECRET
echo ""

# Update environment file
if [ -n "$KEYCLOAK_URL" ] && [ -n "$KEYCLOAK_CLIENT_SECRET" ]; then
    # Backup existing file
    cp .env.production .env.production.backup
    
    # Update Keycloak settings
    sed -i.bak "s|KEYCLOAK_URL=.*|KEYCLOAK_URL=$KEYCLOAK_URL|" .env.production
    sed -i.bak "s|KEYCLOAK_REALM=.*|KEYCLOAK_REALM=$KEYCLOAK_REALM|" .env.production
    sed -i.bak "s|KEYCLOAK_CLIENT_ID=.*|KEYCLOAK_CLIENT_ID=$KEYCLOAK_CLIENT_ID|" .env.production
    sed -i.bak "s|KEYCLOAK_CLIENT_SECRET=.*|KEYCLOAK_CLIENT_SECRET=$KEYCLOAK_CLIENT_SECRET|" .env.production
    sed -i.bak "s|KEYCLOAK_TOKEN_ISSUER=.*|KEYCLOAK_TOKEN_ISSUER=$KEYCLOAK_URL/realms/$KEYCLOAK_REALM|" .env.production
    
    echo -e "${GREEN}✅ Keycloak configuration updated${NC}"
else
    echo -e "${YELLOW}⚠️  Skipping Keycloak configuration (will run without auth)${NC}"
    sed -i.bak "s|AUTH_ENABLED=.*|AUTH_ENABLED=false|" .env.production
fi

# Step 4: Start PostgreSQL
echo -e "\n${BLUE}Starting PostgreSQL Docker container...${NC}"

# Stop existing PostgreSQL if running
docker stop agenthub-postgres 2>/dev/null || true

# Start PostgreSQL
docker-compose -f docker-compose.production.yml up -d postgres

# Wait for PostgreSQL
echo -n "Waiting for PostgreSQL to be ready"
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if docker exec agenthub-postgres pg_isready -U postgres >/dev/null 2>&1; then
        echo -e "\n${GREEN}✅ PostgreSQL is ready${NC}"
        break
    fi
    echo -n "."
    sleep 2
    attempt=$((attempt + 1))
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "\n${RED}❌ PostgreSQL failed to start${NC}"
    docker logs agenthub-postgres
    exit 1
fi

# Step 5: Setup Python environment
echo -e "\n${BLUE}Setting up Python environment...${NC}"

if [ ! -d "agenthub_main/venv" ]; then
    python3 -m venv agenthub_main/venv
    echo -e "${GREEN}✅ Python virtual environment created${NC}"
fi

# Activate and install dependencies
source agenthub_main/venv/bin/activate
pip install -q --upgrade pip
pip install -q -r agenthub_main/requirements.txt
echo -e "${GREEN}✅ Python dependencies installed${NC}"

# Step 6: Start MCP Server
echo -e "\n${BLUE}Starting MCP Server...${NC}"

# Kill existing MCP server if running
pkill -f "mcp_http_server" 2>/dev/null || true

# Create logs directory
mkdir -p logs

# Start MCP server in background
export ENV_FILE=.env.production
export PYTHONPATH="./agenthub_main/src:$PYTHONPATH"
nohup python agenthub_main/src/mcp_http_server.py > logs/mcp-server.log 2>&1 &
MCP_PID=$!

echo "MCP Server started with PID: $MCP_PID"

# Wait for MCP server
echo -n "Waiting for MCP server to be ready"
max_attempts=20
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:8001/health >/dev/null 2>&1; then
        echo -e "\n${GREEN}✅ MCP server is ready${NC}"
        break
    fi
    echo -n "."
    sleep 2
    attempt=$((attempt + 1))
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "\n${RED}❌ MCP server failed to start${NC}"
    tail -n 50 logs/mcp-server.log
    exit 1
fi

# Step 7: Test the setup
echo -e "\n${BLUE}Testing the setup...${NC}"

# Test health endpoint
HEALTH=$(curl -s http://localhost:8001/health)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Health check passed${NC}"
else
    echo -e "${RED}❌ Health check failed${NC}"
fi

# Display status
echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}     Quick Start Complete!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "${BLUE}Services Running:${NC}"
echo -e "  • PostgreSQL:    ${GREEN}localhost:5432${NC}"
echo -e "  • MCP Server:    ${GREEN}http://localhost:8001${NC}"
echo -e "  • API Docs:      ${GREEN}http://localhost:8001/ai_docs${NC}"

if [ -n "$KEYCLOAK_URL" ]; then
    echo -e "  • Keycloak:      ${GREEN}$KEYCLOAK_URL${NC}"
    echo -e "  • Auth Status:   ${GREEN}Enabled${NC}"
else
    echo -e "  • Auth Status:   ${YELLOW}Disabled (Development Mode)${NC}"
fi

echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "  1. Test authentication: python test-keycloak-postgres-setup.py"
echo "  2. View logs: tail -f logs/mcp-server.log"
echo "  3. Stop services: ./stop-production.sh"
echo ""
echo -e "${GREEN}Your agenthub system is ready to use!${NC}"
echo ""

# Save PID for stop script
echo $MCP_PID > .mcp.pid