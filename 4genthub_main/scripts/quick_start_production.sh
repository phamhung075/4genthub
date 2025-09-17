#!/bin/bash

# Quick Start Script for Production Setup
# PostgreSQL (Docker) + Keycloak (Cloud) + MCP Server

set -e

echo "=================================================="
echo "4genthub Production Quick Start"
echo "PostgreSQL (Docker) + Keycloak (Cloud)"
echo "=================================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Check for .env file
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo ""
    echo "Please create a .env file with the following configuration:"
    echo ""
    cat << 'EOF'
# =============================================================================
# PRODUCTION CONFIGURATION
# =============================================================================
ENV=production
DATABASE_TYPE=postgresql
DATABASE_HOST=postgres
DATABASE_PORT=5432
DATABASE_NAME=4genthub_prod
DATABASE_USER=4genthub_user
DATABASE_PASSWORD=YourSecurePassword2025!  # CHANGE THIS!

# Keycloak Configuration (REQUIRED - Update with your values)
AUTH_PROVIDER=keycloak
KEYCLOAK_URL=https://your-keycloak-instance.com  # CHANGE THIS!
KEYCLOAK_REALM=4genthub
KEYCLOAK_CLIENT_ID=mcp-backend
KEYCLOAK_CLIENT_SECRET=your-client-secret  # CHANGE THIS!

AUTH_ENABLED=true
AUTH_PROVIDER=keycloak
MCP_HOST=0.0.0.0
MCP_PORT=8001
JWT_SECRET_KEY=generate-a-secure-key-here

FRONTEND_URL=http://localhost:3800
CORS_ORIGINS=http://localhost:3800,http://localhost:8001
EOF
    echo ""
    echo "Create the .env file and update the values, then run this script again."
    exit 1
fi

# Load environment variables
source .env

# Check required Keycloak configuration
if [ "$KEYCLOAK_URL" == "https://your-keycloak-instance.com" ] || [ -z "$KEYCLOAK_URL" ]; then
    echo "❌ KEYCLOAK_URL not configured in .env file"
    echo "   Please update KEYCLOAK_URL with your actual Keycloak instance URL"
    exit 1
fi

if [ "$KEYCLOAK_CLIENT_SECRET" == "your-client-secret" ] || [ -z "$KEYCLOAK_CLIENT_SECRET" ]; then
    echo "❌ KEYCLOAK_CLIENT_SECRET not configured in .env file"
    echo "   Please update KEYCLOAK_CLIENT_SECRET with your actual client secret from Keycloak"
    exit 1
fi

echo "✅ Environment configuration found"
echo "   - Keycloak URL: $KEYCLOAK_URL"
echo "   - Keycloak Realm: ${KEYCLOAK_REALM:-4genthub}"
echo "   - Database: PostgreSQL (Docker)"
echo ""

# Stop any running containers
echo "Stopping any existing containers..."
docker-compose down 2>/dev/null || true
echo ""

# Build images
echo "Building Docker images..."
docker-compose build
echo ""

# Start PostgreSQL
echo "Starting PostgreSQL..."
docker-compose up -d postgres
echo ""

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if docker-compose exec postgres pg_isready -U ${DATABASE_USER:-4genthub_user} -d ${DATABASE_NAME:-4genthub_prod} &>/dev/null; then
        echo "✅ PostgreSQL is ready"
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

# Initialize database
echo "Initializing database schema..."
docker-compose run --rm mcp-server python /app/src/fastmcp/task_management/infrastructure/database/init_database.py || {
    echo "⚠️  Database initialization failed. This might be normal if the schema already exists."
}
echo ""

# Start MCP Server
echo "Starting MCP Server..."
docker-compose up -d mcp-server
echo ""

# Wait for MCP Server to be ready
echo "Waiting for MCP Server to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo "✅ MCP Server is ready"
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

# Check health
echo "Checking system health..."
health_response=$(curl -s http://localhost:8001/health)
echo "$health_response" | python -m json.tool 2>/dev/null || echo "$health_response"
echo ""

# Show logs
echo "=================================================="
echo "✅ Production system is running!"
echo "=================================================="
echo ""
echo "Services:"
echo "  - PostgreSQL: localhost:5432"
echo "  - MCP Server: http://localhost:8001"
echo "  - PgAdmin: http://localhost:5050 (optional - run with --profile tools)"
echo ""
echo "Next steps:"
echo "  1. Test Keycloak authentication:"
echo "     python 4genthub_main/scripts/test_keycloak_mcp_integration.py"
echo ""
echo "  2. View logs:"
echo "     docker-compose logs -f mcp-server"
echo ""
echo "  3. Access PostgreSQL:"
echo "     docker-compose exec postgres psql -U ${DATABASE_USER:-4genthub_user} -d ${DATABASE_NAME:-4genthub_prod}"
echo ""
echo "  4. Stop services:"
echo "     docker-compose down"
echo ""
echo "For detailed setup instructions, see:"
echo "  ai_docs/setup-guides/PRODUCTION_POSTGRESQL_KEYCLOAK_SETUP.md"
echo ""