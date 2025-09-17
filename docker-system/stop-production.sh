#!/bin/bash

# =============================================================================
# 4genthub Production Stop Script
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.production.yml"

echo -e "${BLUE}"
echo "============================================================"
echo "     Stopping 4genthub Production Server"
echo "============================================================"
echo -e "${NC}"

# Stop Docker Compose services
echo -e "${BLUE}Stopping Docker services...${NC}"
docker-compose -f "$COMPOSE_FILE" down

# Stop any local Python MCP server
echo -e "${BLUE}Stopping local MCP server (if running)...${NC}"
pkill -f "mcp_http_server.py" 2>/dev/null || true

# Clean up
echo -e "${BLUE}Cleaning up...${NC}"
docker-compose -f "$COMPOSE_FILE" rm -f 2>/dev/null || true

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}     4genthub Production Server Stopped${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "${YELLOW}To restart, run: ./start-production.sh${NC}"
echo ""