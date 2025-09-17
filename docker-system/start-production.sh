#!/bin/bash

# =============================================================================
# agenthub Production Startup Script
# PostgreSQL Docker + Keycloak Cloud
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENV_FILE="${ENV_FILE:-.env.production}"
COMPOSE_FILE="docker-compose.production.yml"
LOG_DIR="./logs"

# Banner
echo -e "${BLUE}"
echo "============================================================"
echo "     agenthub Production Server"
echo "     PostgreSQL Docker + Keycloak Cloud"
echo "============================================================"
echo -e "${NC}"

# Check environment file
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ Error: Environment file $ENV_FILE not found${NC}"
    echo -e "${YELLOW}Please copy .env.example to .env.production and configure your settings${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Using environment: $ENV_FILE${NC}"

# Load environment variables
export $(grep -v '^#' "$ENV_FILE" | xargs)

# Validate required Keycloak configuration
if [ -z "$KEYCLOAK_URL" ] || [ "$KEYCLOAK_URL" = "https://your-keycloak.cloud.provider.com" ]; then
    echo -e "${YELLOW}⚠️  Warning: KEYCLOAK_URL not configured${NC}"
    echo "Please set KEYCLOAK_URL in $ENV_FILE to your Keycloak cloud instance"
    echo "Example: KEYCLOAK_URL=https://keycloak.yourdomain.com"
    echo ""
    read -p "Continue without Keycloak? (development mode only) [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    export AUTH_ENABLED=false
    export AUTH_PROVIDER=none
fi

# Create log directory
mkdir -p "$LOG_DIR"

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Check required ports
echo -e "${BLUE}Checking ports...${NC}"

if check_port 5432; then
    echo -e "${YELLOW}⚠️  Port 5432 (PostgreSQL) is already in use${NC}"
    read -p "Stop existing PostgreSQL? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker stop agenthub-postgres-prod 2>/dev/null || true
        sleep 2
    fi
fi

if check_port 8001; then
    echo -e "${YELLOW}⚠️  Port 8001 (MCP Server) is already in use${NC}"
    read -p "Stop existing MCP server? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pkill -f "mcp_server" 2>/dev/null || true
        docker stop agenthub-backend 2>/dev/null || true
        sleep 2
    fi
fi

# Start PostgreSQL with Docker Compose
echo -e "${BLUE}Starting PostgreSQL database...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d postgres

# Wait for PostgreSQL to be ready
echo -e "${BLUE}Waiting for PostgreSQL to be ready...${NC}"
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U "$DATABASE_USER" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
        break
    fi
    echo -n "."
    sleep 2
    attempt=$((attempt + 1))
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}❌ PostgreSQL failed to start${NC}"
    docker-compose -f "$COMPOSE_FILE" logs postgres
    exit 1
fi

# Initialize database schema (if needed)
echo -e "${BLUE}Checking database schema...${NC}"
if [ -f "./agenthub_main/src/fastmcp/task_management/infrastructure/migrations/001_initial_schema.sql" ]; then
    echo "Applying database migrations..."
    docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U "$DATABASE_USER" -d "$DATABASE_NAME" \
        -f /docker-entrypoint-initdb.d/001_initial_schema.sql 2>/dev/null || true
fi

# Choose how to run MCP server
echo -e "${BLUE}Select MCP server mode:${NC}"
echo "1) Docker container (recommended for production)"
echo "2) Local Python (for development/debugging)"
read -p "Choice [1]: " server_mode
server_mode=${server_mode:-1}

if [ "$server_mode" = "1" ]; then
    # Run MCP server in Docker
    echo -e "${BLUE}Building MCP server Docker image...${NC}"
    docker-compose -f "$COMPOSE_FILE" build mcp-backend
    
    echo -e "${BLUE}Starting MCP server in Docker...${NC}"
    docker-compose -f "$COMPOSE_FILE" up -d mcp-backend
    
    # Wait for MCP server to be ready
    echo -e "${BLUE}Waiting for MCP server to be ready...${NC}"
    max_attempts=20
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:8001/health >/dev/null 2>&1; then
            echo -e "${GREEN}✅ MCP server is ready${NC}"
            break
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    if [ $attempt -eq $max_attempts ]; then
        echo -e "${RED}❌ MCP server failed to start${NC}"
        docker-compose -f "$COMPOSE_FILE" logs mcp-backend
        exit 1
    fi
else
    # Run MCP server locally
    echo -e "${BLUE}Starting MCP server locally...${NC}"
    
    # Check Python environment
    if [ ! -d "./agenthub_main/venv" ]; then
        echo -e "${YELLOW}Creating Python virtual environment...${NC}"
        python3 -m venv ./agenthub_main/venv
        source ./agenthub_main/venv/bin/activate
        pip install -r ./agenthub_main/requirements.txt
    else
        source ./agenthub_main/venv/bin/activate
    fi
    
    # Start MCP server
    export PYTHONPATH="./agenthub_main/src:$PYTHONPATH"
    export ENV_FILE="$ENV_FILE"
    nohup python ./agenthub_main/src/mcp_http_server.py > "$LOG_DIR/mcp-server.log" 2>&1 &
    MCP_PID=$!
    echo "MCP server started with PID: $MCP_PID"
    
    # Wait for server to be ready
    echo -e "${BLUE}Waiting for MCP server to be ready...${NC}"
    sleep 5
    if ! curl -s http://localhost:8001/health >/dev/null 2>&1; then
        echo -e "${RED}❌ MCP server failed to start${NC}"
        tail -n 50 "$LOG_DIR/mcp-server.log"
        exit 1
    fi
fi

# Optional: Start PgAdmin
read -p "Start PgAdmin for database management? [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Starting PgAdmin...${NC}"
    docker-compose -f "$COMPOSE_FILE" --profile tools up -d pgadmin
    echo -e "${GREEN}✅ PgAdmin available at: http://localhost:5050${NC}"
    echo "   Email: ${PGADMIN_EMAIL:-admin@agenthub.com}"
fi

# Display status
echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}     agenthub Production Server Started Successfully${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "${BLUE}Services:${NC}"
echo -e "  • MCP Server:    ${GREEN}http://localhost:8001${NC}"
echo -e "  • API Docs:      ${GREEN}http://localhost:8001/docs${NC}"
echo -e "  • Health Check:  ${GREEN}http://localhost:8001/health${NC}"

if [ "$AUTH_ENABLED" = "true" ]; then
    echo -e "  • Keycloak:      ${GREEN}$KEYCLOAK_URL${NC}"
    echo -e "  • Auth Status:   ${GREEN}Enabled (Keycloak)${NC}"
else
    echo -e "  • Auth Status:   ${YELLOW}Disabled (Development Mode)${NC}"
fi

echo ""
echo -e "${BLUE}Database:${NC}"
echo -e "  • PostgreSQL:    ${GREEN}localhost:5432${NC}"
echo -e "  • Database:      ${GREEN}$DATABASE_NAME${NC}"

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "  • PgAdmin:       ${GREEN}http://localhost:5050${NC}"
fi

echo ""
echo -e "${BLUE}Logs:${NC}"
if [ "$server_mode" = "1" ]; then
    echo "  • View logs: docker-compose -f $COMPOSE_FILE logs -f"
else
    echo "  • MCP logs: tail -f $LOG_DIR/mcp-server.log"
fi

echo ""
echo -e "${YELLOW}To stop all services:${NC}"
echo "  ./stop-production.sh"
echo ""