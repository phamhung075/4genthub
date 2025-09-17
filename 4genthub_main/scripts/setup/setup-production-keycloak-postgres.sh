#!/bin/bash

# ============================================================================
# PRODUCTION SETUP SCRIPT - PostgreSQL Docker + Keycloak Cloud
# ============================================================================
# This script sets up 4genthub with:
# - PostgreSQL running in Docker container locally
# - Keycloak running on cloud service
# - Clean configuration without backward compatibility
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENV_FILE=".env.production"
DOCKER_COMPOSE_FILE="docker-compose.production.yml"

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}4genthub Production Setup - PostgreSQL Docker + Keycloak Cloud${NC}"
echo -e "${BLUE}============================================================================${NC}"

# Step 1: Check prerequisites
echo -e "\n${YELLOW}Step 1: Checking prerequisites...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker found${NC}"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker Compose found${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed. Please install Python 3 first.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python 3 found${NC}"

# Step 2: Stop any existing containers
echo -e "\n${YELLOW}Step 2: Stopping existing containers...${NC}"
docker-compose -f docker-compose.production.yml down 2>/dev/null || true
docker-compose down 2>/dev/null || true
echo -e "${GREEN}✅ Existing containers stopped${NC}"

# Step 3: Configure environment
echo -e "\n${YELLOW}Step 3: Configuring environment...${NC}"

# Check if .env.production exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ $ENV_FILE not found. Creating from template...${NC}"
    cp .env.production-keycloak-postgres "$ENV_FILE" 2>/dev/null || {
        echo -e "${RED}❌ Template file not found. Please create $ENV_FILE manually.${NC}"
        exit 1
    }
fi

# Prompt for Keycloak configuration
echo -e "\n${BLUE}Please provide your Keycloak cloud configuration:${NC}"
echo -e "${YELLOW}(Press Enter to keep existing values)${NC}"

# Read current values
current_keycloak_url=$(grep "^KEYCLOAK_URL=" "$ENV_FILE" | cut -d'=' -f2)
current_keycloak_realm=$(grep "^KEYCLOAK_REALM=" "$ENV_FILE" | cut -d'=' -f2)
current_keycloak_client_id=$(grep "^KEYCLOAK_CLIENT_ID=" "$ENV_FILE" | cut -d'=' -f2)

# Prompt for new values
read -p "Keycloak URL [$current_keycloak_url]: " keycloak_url
keycloak_url=${keycloak_url:-$current_keycloak_url}

read -p "Keycloak Realm [$current_keycloak_realm]: " keycloak_realm
keycloak_realm=${keycloak_realm:-$current_keycloak_realm}

read -p "Keycloak Client ID [$current_keycloak_client_id]: " keycloak_client_id
keycloak_client_id=${keycloak_client_id:-$current_keycloak_client_id}

read -sp "Keycloak Client Secret (hidden): " keycloak_client_secret
echo

# Update .env.production file
if [ ! -z "$keycloak_url" ] && [ "$keycloak_url" != "$current_keycloak_url" ]; then
    sed -i "s|^KEYCLOAK_URL=.*|KEYCLOAK_URL=$keycloak_url|" "$ENV_FILE"
fi

if [ ! -z "$keycloak_realm" ] && [ "$keycloak_realm" != "$current_keycloak_realm" ]; then
    sed -i "s|^KEYCLOAK_REALM=.*|KEYCLOAK_REALM=$keycloak_realm|" "$ENV_FILE"
fi

if [ ! -z "$keycloak_client_id" ] && [ "$keycloak_client_id" != "$current_keycloak_client_id" ]; then
    sed -i "s|^KEYCLOAK_CLIENT_ID=.*|KEYCLOAK_CLIENT_ID=$keycloak_client_id|" "$ENV_FILE"
fi

if [ ! -z "$keycloak_client_secret" ]; then
    sed -i "s|^KEYCLOAK_CLIENT_SECRET=.*|KEYCLOAK_CLIENT_SECRET=$keycloak_client_secret|" "$ENV_FILE"
fi

echo -e "${GREEN}✅ Environment configured${NC}"

# Step 4: Create necessary directories
echo -e "\n${YELLOW}Step 4: Creating necessary directories...${NC}"
mkdir -p 4genthub_main/logs
mkdir -p config/pgadmin
mkdir -p config/nginx/sites
echo -e "${GREEN}✅ Directories created${NC}"

# Step 5: Create PgAdmin server configuration
echo -e "\n${YELLOW}Step 5: Creating PgAdmin configuration...${NC}"
cat > config/pgadmin/servers.json << 'EOF'
{
    "Servers": {
        "1": {
            "Name": "4genthub PostgreSQL",
            "Group": "Servers",
            "Host": "postgres",
            "Port": 5432,
            "MaintenanceDB": "postgres",
            "Username": "4genthub_user",
            "SSLMode": "prefer",
            "Comment": "4genthub Production Database"
        }
    }
}
EOF
echo -e "${GREEN}✅ PgAdmin configuration created${NC}"

# Step 6: Build and start services
echo -e "\n${YELLOW}Step 6: Starting services...${NC}"
echo -e "${BLUE}Starting PostgreSQL...${NC}"
docker-compose -f "$DOCKER_COMPOSE_FILE" up -d postgres

# Wait for PostgreSQL to be ready
echo -e "${BLUE}Waiting for PostgreSQL to be ready...${NC}"
for i in {1..30}; do
    if docker-compose -f "$DOCKER_COMPOSE_FILE" exec postgres pg_isready -U 4genthub_user -d 4genthub_prod &>/dev/null; then
        echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
        break
    fi
    echo -n "."
    sleep 2
done

# Start MCP Backend
echo -e "${BLUE}Building and starting MCP Backend...${NC}"
docker-compose -f "$DOCKER_COMPOSE_FILE" up -d --build mcp-backend

# Wait for backend to be ready
echo -e "${BLUE}Waiting for MCP Backend to be ready...${NC}"
for i in {1..30}; do
    if curl -f http://localhost:8001/health &>/dev/null; then
        echo -e "${GREEN}✅ MCP Backend is ready${NC}"
        break
    fi
    echo -n "."
    sleep 2
done

# Step 7: Initialize database
echo -e "\n${YELLOW}Step 7: Initializing database...${NC}"
docker-compose -f "$DOCKER_COMPOSE_FILE" exec mcp-backend python -c "
from 4genthub_main.src.fastmcp.task_management.infrastructure.database.database_initializer import DatabaseInitializer
from 4genthub_main.src.fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig
config = DatabaseConfig()
initializer = DatabaseInitializer(config)
initializer.initialize()
print('✅ Database initialized successfully')
" || echo -e "${YELLOW}⚠️  Database may already be initialized${NC}"

# Step 8: Optional - Start additional services
echo -e "\n${YELLOW}Step 8: Optional services...${NC}"
read -p "Start PgAdmin? (y/n): " start_pgadmin
if [ "$start_pgadmin" = "y" ]; then
    docker-compose -f "$DOCKER_COMPOSE_FILE" --profile tools up -d pgadmin
    echo -e "${GREEN}✅ PgAdmin started at http://localhost:5050${NC}"
fi

read -p "Start Frontend? (y/n): " start_frontend
if [ "$start_frontend" = "y" ]; then
    docker-compose -f "$DOCKER_COMPOSE_FILE" --profile with-frontend up -d frontend
    echo -e "${GREEN}✅ Frontend started at http://localhost:3800${NC}"
fi

# Step 9: Display status
echo -e "\n${BLUE}============================================================================${NC}"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo -e "${BLUE}============================================================================${NC}"

echo -e "\n${YELLOW}Service Status:${NC}"
docker-compose -f "$DOCKER_COMPOSE_FILE" ps

echo -e "\n${YELLOW}Service URLs:${NC}"
echo -e "  MCP Backend:  ${GREEN}http://localhost:8001${NC}"
echo -e "  Health Check: ${GREEN}http://localhost:8001/health${NC}"
echo -e "  API Docs:     ${GREEN}http://localhost:8001/ai_docs${NC}"

if [ "$start_pgadmin" = "y" ]; then
    echo -e "  PgAdmin:      ${GREEN}http://localhost:5050${NC}"
    echo -e "                Email: admin@4genthub.com"
    echo -e "                Password: Check .env.production file"
fi

if [ "$start_frontend" = "y" ]; then
    echo -e "  Frontend:     ${GREEN}http://localhost:3800${NC}"
fi

echo -e "\n${YELLOW}Keycloak Configuration:${NC}"
echo -e "  URL:          ${GREEN}$keycloak_url${NC}"
echo -e "  Realm:        ${GREEN}$keycloak_realm${NC}"
echo -e "  Client ID:    ${GREEN}$keycloak_client_id${NC}"

echo -e "\n${YELLOW}Quick Commands:${NC}"
echo -e "  View logs:    ${BLUE}docker-compose -f $DOCKER_COMPOSE_FILE logs -f${NC}"
echo -e "  Stop all:     ${BLUE}docker-compose -f $DOCKER_COMPOSE_FILE down${NC}"
echo -e "  Restart:      ${BLUE}docker-compose -f $DOCKER_COMPOSE_FILE restart${NC}"
echo -e "  DB shell:     ${BLUE}docker-compose -f $DOCKER_COMPOSE_FILE exec postgres psql -U 4genthub_user -d 4genthub_prod${NC}"

echo -e "\n${YELLOW}Next Steps:${NC}"
echo -e "  1. Ensure your Keycloak instance is configured with the correct client"
echo -e "  2. Test authentication: ${BLUE}curl -X POST http://localhost:8001/auth/login${NC}"
echo -e "  3. Configure any additional MCP clients to use Keycloak tokens"

echo -e "\n${GREEN}✨ Production environment is ready!${NC}"
