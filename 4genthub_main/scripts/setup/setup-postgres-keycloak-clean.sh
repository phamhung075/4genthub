#!/bin/bash

# =============================================================================
# Clean PostgreSQL + Keycloak Setup Script
# =============================================================================
# NO backward compatibility - Clean implementation only
# PostgreSQL Docker (local) + Keycloak (cloud)
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Configuration
# =============================================================================
ENV_FILE=".env"
ENV_PRODUCTION=".env.production-keycloak-postgres"
DOCKER_COMPOSE="docker-compose.yml"

# =============================================================================
# Functions
# =============================================================================

print_header() {
    echo -e "${BLUE}=============================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=============================================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    print_success "Docker is installed"
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed"
        exit 1
    fi
    print_success "Docker Compose is installed"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    print_success "Python 3 is installed"
}

setup_environment() {
    print_header "Setting Up Environment Configuration"
    
    # Backup existing .env if it exists
    if [ -f "$ENV_FILE" ]; then
        backup_file="${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$ENV_FILE" "$backup_file"
        print_success "Backed up existing .env to $backup_file"
    fi
    
    # Copy production environment file
    cp "$ENV_PRODUCTION" "$ENV_FILE"
    print_success "Created .env from production template"
    
    # Prompt for Keycloak configuration
    print_warning "Please update the following Keycloak settings in .env:"
    echo "  - KEYCLOAK_URL (your Keycloak cloud URL)"
    echo "  - KEYCLOAK_REALM (your realm name)"
    echo "  - KEYCLOAK_CLIENT_ID (your client ID)"
    echo "  - KEYCLOAK_CLIENT_SECRET (your client secret)"
    echo ""
    read -p "Press Enter after updating .env file..."
}

start_postgres() {
    print_header "Starting PostgreSQL Docker Container"
    
    # Stop any existing containers
    docker-compose down 2>/dev/null || true
    
    # Remove old volumes if clean start requested
    if [ "$1" == "--clean" ]; then
        print_warning "Removing existing PostgreSQL volumes..."
        docker volume rm 4genthub_postgres_data 2>/dev/null || true
        docker volume rm 4genthub_postgres_backup 2>/dev/null || true
        print_success "Volumes removed"
    fi
    
    # Start PostgreSQL only
    docker-compose up -d postgres
    
    # Wait for PostgreSQL to be ready
    print_warning "Waiting for PostgreSQL to be ready..."
    sleep 5
    
    # Check PostgreSQL health
    for i in {1..30}; do
        if docker-compose exec postgres pg_isready -U postgres > /dev/null 2>&1; then
            print_success "PostgreSQL is ready"
            break
        fi
        echo -n "."
        sleep 1
    done
}

initialize_database() {
    print_header "Initializing Database Schema"
    
    # Run database initialization script
    python3 <<EOF
import os
import sys
sys.path.insert(0, '4genthub_main/src')

from sqlalchemy import create_engine, text
from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig

# Load configuration
config = DatabaseConfig()
config.database_type = "postgresql"
config.database_host = os.getenv("DATABASE_HOST", "localhost")
config.database_port = int(os.getenv("DATABASE_PORT", 5432))
config.database_name = os.getenv("DATABASE_NAME", "4genthub")
config.database_user = os.getenv("DATABASE_USER", "postgres")
config.database_password = os.getenv("DATABASE_PASSWORD", "postgres_secure_password_2025")

# Create engine
engine = create_engine(config.get_database_url())

# Initialize tables
from fastmcp.task_management.infrastructure.database.models import Base
Base.metadata.create_all(engine)

print("✅ Database schema initialized")

# Verify tables
with engine.connect() as conn:
    result = conn.execute(text(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
    ))
    tables = [row[0] for row in result]
    print(f"✅ Created {len(tables)} tables: {', '.join(tables)}")
EOF
}

test_keycloak_connection() {
    print_header "Testing Keycloak Connection"
    
    python3 <<EOF
import os
import requests
from urllib.parse import urljoin

keycloak_url = os.getenv("KEYCLOAK_URL")
keycloak_realm = os.getenv("KEYCLOAK_REALM")

if not keycloak_url or keycloak_url == "https://your-keycloak-domain.com":
    print("⚠️  Keycloak URL not configured - skipping test")
    exit(0)

try:
    # Test well-known endpoint
    well_known_url = urljoin(
        keycloak_url,
        f"/realms/{keycloak_realm}/.well-known/openid-configuration"
    )
    
    response = requests.get(well_known_url, timeout=5)
    if response.status_code == 200:
        print(f"✅ Keycloak connection successful")
        config = response.json()
        print(f"   Issuer: {config.get('issuer')}")
        print(f"   Token endpoint: {config.get('token_endpoint')}")
    else:
        print(f"❌ Keycloak returned status {response.status_code}")
except Exception as e:
    print(f"❌ Failed to connect to Keycloak: {e}")
EOF
}

start_mcp_server() {
    print_header "Starting MCP Server"
    
    # Start MCP server
    docker-compose up -d mcp-server
    
    # Wait for server to be ready
    print_warning "Waiting for MCP server to be ready..."
    sleep 5
    
    # Check server health
    for i in {1..30}; do
        if curl -s http://localhost:8001/health > /dev/null 2>&1; then
            print_success "MCP server is ready"
            break
        fi
        echo -n "."
        sleep 1
    done
}

verify_setup() {
    print_header "Verifying Setup"
    
    # Check PostgreSQL
    if docker-compose exec postgres pg_isready -U postgres > /dev/null 2>&1; then
        print_success "PostgreSQL is running"
    else
        print_error "PostgreSQL is not responding"
    fi
    
    # Check MCP Server
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        print_success "MCP server is running"
        
        # Get server info
        response=$(curl -s http://localhost:8001/health)
        echo "   Server health: $response"
    else
        print_error "MCP server is not responding"
    fi
    
    # Check Keycloak configuration
    keycloak_url=$(grep KEYCLOAK_URL .env | cut -d '=' -f2)
    if [ "$keycloak_url" != "https://your-keycloak-domain.com" ]; then
        print_success "Keycloak is configured"
    else
        print_warning "Keycloak configuration needs to be updated"
    fi
}

print_summary() {
    print_header "Setup Complete"
    
    echo -e "${GREEN}Your PostgreSQL + Keycloak setup is ready!${NC}"
    echo ""
    echo "📝 Configuration Summary:"
    echo "   - PostgreSQL: localhost:5432"
    echo "   - MCP Server: http://localhost:8001"
    echo "   - PgAdmin: http://localhost:5050 (if enabled)"
    echo ""
    echo "🔐 Keycloak Configuration:"
    keycloak_url=$(grep KEYCLOAK_URL .env | cut -d '=' -f2)
    keycloak_realm=$(grep KEYCLOAK_REALM .env | cut -d '=' -f2)
    echo "   - URL: $keycloak_url"
    echo "   - Realm: $keycloak_realm"
    echo ""
    echo "📚 Next Steps:"
    echo "   1. Update Keycloak settings in .env if not done"
    echo "   2. Configure Keycloak client with proper redirect URIs"
    echo "   3. Test authentication with: curl -X POST http://localhost:8001/api/auth/login"
    echo ""
    echo "🛠️  Useful Commands:"
    echo "   - View logs: docker-compose logs -f"
    echo "   - Stop services: docker-compose down"
    echo "   - Clean restart: $0 --clean"
}

# =============================================================================
# Main Execution
# =============================================================================

print_header "PostgreSQL + Keycloak Clean Setup"
echo "NO backward compatibility - Clean implementation only"
echo ""

# Parse arguments
CLEAN_START=false
if [ "$1" == "--clean" ]; then
    CLEAN_START=true
    print_warning "Clean start requested - will remove existing data"
fi

# Run setup steps
check_prerequisites
setup_environment

if [ "$CLEAN_START" == true ]; then
    start_postgres --clean
else
    start_postgres
fi

initialize_database
test_keycloak_connection
start_mcp_server
verify_setup
print_summary

print_success "Setup completed successfully!"