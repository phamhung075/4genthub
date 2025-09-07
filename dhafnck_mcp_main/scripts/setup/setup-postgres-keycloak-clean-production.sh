#!/bin/bash

# ==============================================================================
# Clean Production Setup for DhafnckMCP
# PostgreSQL in Docker + Keycloak on Cloud
# ==============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ==============================================================================
# Configuration
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Default values (can be overridden by environment)
DB_NAME="${DATABASE_NAME:-dhafnck_mcp_prod}"
DB_USER="${DATABASE_USER:-dhafnck_user}"
DB_PASSWORD="${DATABASE_PASSWORD:-ChangeThisSecurePassword2025!}"
KEYCLOAK_URL="${KEYCLOAK_URL:-https://your-keycloak.cloud.provider.com}"
KEYCLOAK_REALM="${KEYCLOAK_REALM:-dhafnck-mcp}"
KEYCLOAK_CLIENT_ID="${KEYCLOAK_CLIENT_ID:-mcp-backend}"

# ==============================================================================
# Functions
# ==============================================================================

print_header() {
    echo -e "\n${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}\n"
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

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

check_prerequisites() {
    print_header "Checking Prerequisites"
    
    local missing_tools=()
    
    # Check for required tools
    if ! command -v docker &> /dev/null; then
        missing_tools+=("docker")
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        missing_tools+=("docker-compose")
    fi
    
    if ! command -v python3 &> /dev/null; then
        missing_tools+=("python3")
    fi
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        echo "Please install the missing tools and try again."
        exit 1
    fi
    
    print_success "All prerequisites are installed"
}

validate_keycloak_config() {
    print_header "Validating Keycloak Configuration"
    
    if [ "$KEYCLOAK_URL" == "https://your-keycloak.cloud.provider.com" ]; then
        print_error "Please configure your Keycloak URL in .env file"
        echo "Edit .env and set KEYCLOAK_URL to your actual Keycloak instance"
        exit 1
    fi
    
    if [ -z "$KEYCLOAK_CLIENT_SECRET" ]; then
        print_warning "KEYCLOAK_CLIENT_SECRET is not set"
        echo "Please set it in your .env file for production use"
    fi
    
    print_success "Keycloak configuration validated"
}

setup_environment() {
    print_header "Setting Up Environment"
    
    # Check if .env exists
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        print_info "Creating .env from .env.production-clean template"
        cp "$PROJECT_ROOT/.env.production-clean" "$PROJECT_ROOT/.env"
    fi
    
    # Update .env with clean production settings
    print_info "Updating .env for clean production setup"
    
    # Backup existing .env
    cp "$PROJECT_ROOT/.env" "$PROJECT_ROOT/.env.backup.$(date +%Y%m%d_%H%M%S)"
    
    print_success "Environment configured"
}

cleanup_old_containers() {
    print_header "Cleaning Up Old Containers"
    
    # Stop and remove old containers
    print_info "Stopping existing containers..."
    docker-compose down --remove-orphans 2>/dev/null || true
    
    # Remove old volumes if requested
    if [ "$1" == "--clean-volumes" ]; then
        print_warning "Removing old volumes..."
        docker volume rm dhafnck_postgres_data 2>/dev/null || true
        docker volume rm dhafnck_mcp_logs 2>/dev/null || true
        docker volume rm dhafnck_pgadmin_data 2>/dev/null || true
    fi
    
    print_success "Cleanup completed"
}

start_postgresql() {
    print_header "Starting PostgreSQL Database"
    
    print_info "Starting PostgreSQL container..."
    docker-compose up -d postgres
    
    # Wait for PostgreSQL to be ready
    print_info "Waiting for PostgreSQL to be ready..."
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose exec -T postgres pg_isready -U "$DB_USER" -d "$DB_NAME" &>/dev/null; then
            print_success "PostgreSQL is ready"
            break
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done
    
    if [ $attempt -eq $max_attempts ]; then
        print_error "PostgreSQL failed to start"
        docker-compose logs postgres
        exit 1
    fi
}

initialize_database() {
    print_header "Initializing Database Schema"
    
    print_info "Running database migrations..."
    
    # Run Python migration script
    python3 << 'EOF'
import os
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, 'dhafnck_mcp_main/src')

try:
    from sqlalchemy import create_engine, text
    from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig
    from fastmcp.task_management.infrastructure.database.models import Base
    
    # Create database configuration
    config = DatabaseConfig()
    config.database_type = "postgresql"
    config.database_host = "localhost"  # Use localhost since we're outside Docker
    config.database_port = 5432
    config.database_name = os.getenv("DATABASE_NAME", "dhafnck_mcp_prod")
    config.database_user = os.getenv("DATABASE_USER", "dhafnck_user")
    config.database_password = os.getenv("DATABASE_PASSWORD", "ChangeThisSecurePassword2025!")
    
    # Create engine
    engine = create_engine(config.get_database_url())
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Verify tables were created
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        ))
        table_count = result.scalar()
        print(f"✅ Created {table_count} tables in database")
    
    print("✅ Database schema initialized successfully")
    
except Exception as e:
    print(f"❌ Database initialization failed: {e}")
    sys.exit(1)
EOF
    
    if [ $? -ne 0 ]; then
        print_error "Database initialization failed"
        exit 1
    fi
    
    print_success "Database schema initialized"
}

start_mcp_server() {
    print_header "Starting MCP Server"
    
    print_info "Building MCP server image..."
    docker-compose build mcp-server
    
    print_info "Starting MCP server..."
    docker-compose up -d mcp-server
    
    # Wait for MCP server to be ready
    print_info "Waiting for MCP server to be ready..."
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:8001/health | grep -q "healthy"; then
            print_success "MCP server is ready"
            break
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done
    
    if [ $attempt -eq $max_attempts ]; then
        print_error "MCP server failed to start"
        docker-compose logs mcp-server
        exit 1
    fi
}

test_setup() {
    print_header "Testing Setup"
    
    # Test database connection
    print_info "Testing database connection..."
    docker-compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT version();" &>/dev/null
    if [ $? -eq 0 ]; then
        print_success "Database connection successful"
    else
        print_error "Database connection failed"
        exit 1
    fi
    
    # Test MCP server health
    print_info "Testing MCP server health..."
    response=$(curl -s http://localhost:8001/health)
    if echo "$response" | grep -q "healthy"; then
        print_success "MCP server is healthy"
        
        # Check authentication status
        if echo "$response" | grep -q '"keycloak_auth":true'; then
            print_success "Keycloak authentication is enabled"
        else
            print_warning "Keycloak authentication is not fully configured"
            print_info "Please ensure KEYCLOAK_URL and KEYCLOAK_CLIENT_SECRET are set in .env"
        fi
    else
        print_error "MCP server health check failed"
        exit 1
    fi
    
    # Show running containers
    print_info "Running containers:"
    docker-compose ps
}

print_next_steps() {
    print_header "Setup Complete! 🎉"
    
    echo "Your clean production setup is ready with:"
    echo "  • PostgreSQL database running in Docker"
    echo "  • MCP server configured for Keycloak authentication"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Configure Keycloak connection:"
    echo "   Edit .env and set:"
    echo "   - KEYCLOAK_URL=<your-keycloak-url>"
    echo "   - KEYCLOAK_CLIENT_SECRET=<your-client-secret>"
    echo ""
    echo "2. Test Keycloak authentication:"
    echo "   python test-keycloak-mcp-clean.py"
    echo ""
    echo "3. Access services:"
    echo "   - MCP Server: http://localhost:8001"
    echo "   - PostgreSQL: localhost:5432"
    echo "   - PgAdmin: http://localhost:5050 (if enabled)"
    echo ""
    echo "4. View logs:"
    echo "   docker-compose logs -f mcp-server"
    echo ""
    echo "5. Stop services:"
    echo "   docker-compose down"
    echo ""
    print_warning "Remember to change default passwords in production!"
}

# ==============================================================================
# Main Execution
# ==============================================================================

main() {
    cd "$PROJECT_ROOT"
    
    print_header "DhafnckMCP Clean Production Setup"
    echo "PostgreSQL (Docker) + Keycloak (Cloud) Configuration"
    echo ""
    
    # Parse arguments
    CLEAN_VOLUMES=false
    if [ "$1" == "--clean" ] || [ "$1" == "--clean-volumes" ]; then
        CLEAN_VOLUMES=true
        print_warning "Will clean existing volumes and start fresh"
    fi
    
    # Run setup steps
    check_prerequisites
    validate_keycloak_config
    setup_environment
    
    if [ "$CLEAN_VOLUMES" == true ]; then
        cleanup_old_containers --clean-volumes
    else
        cleanup_old_containers
    fi
    
    start_postgresql
    initialize_database
    start_mcp_server
    test_setup
    print_next_steps
}

# Run main function
main "$@"