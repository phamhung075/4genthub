#!/bin/bash

# Database Configuration Switcher
# Easily switch between Supabase (cloud) and Local PostgreSQL

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if PostgreSQL is reachable
check_postgres() {
    local host=$1
    local port=$2
    local user=$3
    local pass=$4
    local db=$5
    
    PGPASSWORD=$pass psql -h $host -p $port -U $user -d $db -c "SELECT 1" > /dev/null 2>&1
    return $?
}

# Function to switch to local database
switch_to_local() {
    print_info "Switching to LOCAL PostgreSQL database..."
    
    # Check if local PostgreSQL is running
    if ! docker ps | grep -q dhafnck-postgres-local; then
        print_warning "Local PostgreSQL container not running. Starting it..."
        docker run -d \
            --name dhafnck-postgres-local \
            -e POSTGRES_PASSWORD=dev123 \
            -e POSTGRES_USER=postgres \
            -e POSTGRES_DB=dhafnck_mcp \
            -p 5432:5432 \
            postgres:15-alpine
        
        print_info "Waiting for PostgreSQL to be ready..."
        sleep 5
    fi
    
    # Check connection
    if check_postgres localhost 5432 postgres dev123 dhafnck_mcp; then
        print_info "✅ Local PostgreSQL is accessible"
    else
        print_error "❌ Cannot connect to local PostgreSQL"
        exit 1
    fi
    
    # Copy local env file
    cp .env.local .env
    
    # Export environment variables
    export DATABASE_TYPE=postgresql
    export DATABASE_URL=postgresql://postgres:dev123@localhost:5432/dhafnck_mcp
    export PERFORMANCE_MODE=true
    
    print_info "✅ Switched to LOCAL database"
    print_info "   URL: postgresql://localhost:5432/dhafnck_mcp"
    print_info "   Performance Mode: ENABLED"
    print_info ""
    print_info "🚀 Expected performance: <100ms for loading tasks"
}

# Function to switch to Supabase
switch_to_supabase() {
    print_info "Switching to SUPABASE cloud database..."
    
    # Check if .env.supabase exists
    if [ ! -f .env.supabase ]; then
        print_error ".env.supabase file not found!"
        print_info "Please create .env.supabase with your Supabase credentials"
        exit 1
    fi
    
    # Copy Supabase env file
    cp .env.supabase .env
    
    # Source the env file to get credentials
    source .env
    
    print_info "✅ Switched to SUPABASE database"
    print_info "   Performance Mode: ${PERFORMANCE_MODE:-false}"
    print_warning "⚠️  Expected latency: 500ms-5s depending on location"
}

# Function to show current configuration
show_current() {
    print_info "Current Database Configuration:"
    
    if [ -f .env ]; then
        source .env
        echo "   DATABASE_TYPE: ${DATABASE_TYPE:-not set}"
        echo "   DATABASE_URL: ${DATABASE_URL:0:50}..."
        echo "   PERFORMANCE_MODE: ${PERFORMANCE_MODE:-false}"
        
        # Test connection
        if [ "$DATABASE_TYPE" = "postgresql" ] && [[ "$DATABASE_URL" == *"localhost"* ]]; then
            if check_postgres localhost 5432 postgres dev123 dhafnck_mcp; then
                print_info "   Connection: ✅ ACTIVE (Local)"
            else
                print_warning "   Connection: ❌ INACTIVE"
            fi
        elif [ "$DATABASE_TYPE" = "supabase" ]; then
            print_info "   Connection: Cloud (Supabase)"
        fi
    else
        print_warning "No .env file found"
    fi
}

# Function to initialize local database
init_local_db() {
    print_info "Initializing local database schema..."
    
    # Run database initialization
    cd /home/daihungpham/agentic-project/dhafnck_mcp_main
    
    # Set environment for local database
    export DATABASE_TYPE=postgresql
    export DATABASE_URL=postgresql://postgres:dev123@localhost:5432/dhafnck_mcp
    
    # Run the database initializer
    python -c "
from src.fastmcp.task_management.infrastructure.database.database_initializer import DatabaseInitializer
initializer = DatabaseInitializer()
initializer.initialize_database()
print('✅ Database schema initialized successfully')
"
}

# Main menu
case "${1:-}" in
    local)
        switch_to_local
        ;;
    supabase)
        switch_to_supabase
        ;;
    status)
        show_current
        ;;
    init)
        init_local_db
        ;;
    *)
        echo "Database Configuration Switcher"
        echo "================================"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  local     - Switch to local PostgreSQL (fast, <100ms)"
        echo "  supabase  - Switch to Supabase cloud (slower, 500ms-5s)"
        echo "  status    - Show current configuration"
        echo "  init      - Initialize local database schema"
        echo ""
        show_current
        ;;
esac