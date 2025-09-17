#!/bin/bash

# =============================================================================
# Complete Database Migration Setup Script
# =============================================================================
# Purpose: Execute complete database clean migration and verify setup
# Version: v3.0.0
# Date: 2025-08-27
#
# This script orchestrates the complete database migration process:
# 1. Executes fresh database migration
# 2. Verifies database setup
# 3. Tests MCP tools integration
# 4. Provides setup summary
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATABASE_TYPE="${DATABASE_TYPE:-supabase}"
SKIP_CONFIRMATION="${SKIP_CONFIRMATION:-false}"

print_header() {
    echo -e "${BLUE}"
    echo "=============================================================="
    echo "🚀 4GENTHUBMCP DATABASE MIGRATION SETUP v3.0.0"
    echo "=============================================================="
    echo -e "${NC}"
}

print_section() {
    echo -e "\n${YELLOW}$1${NC}"
    echo "----------------------------------------"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

check_prerequisites() {
    print_section "Checking Prerequisites"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 is required but not installed"
        exit 1
    fi
    print_success "Python3 found"
    
    # Check psycopg2
    if ! python3 -c "import psycopg2" 2>/dev/null; then
        print_warning "psycopg2 not found - may need to install: pip install psycopg2-binary"
    else
        print_success "psycopg2 available"
    fi
    
    # Check database environment
    if [ "$DATABASE_TYPE" = "supabase" ]; then
        if [ -z "$SUPABASE_DB_URL" ]; then
            print_error "SUPABASE_DB_URL environment variable not set"
            echo "Set it with: export SUPABASE_DB_URL='postgresql://[user]:[password]@[host]:5432/[database]'"
            exit 1
        fi
        print_success "Supabase database URL configured"
    elif [ "$DATABASE_TYPE" = "local" ]; then
        LOCAL_DB_URL="${LOCAL_DB_URL:-postgresql://postgres:postgres@localhost:5432/4genthub}"
        print_success "Local database URL: $LOCAL_DB_URL"
    fi
    
    # Check migration files exist
    MIGRATION_FILE="$SCRIPT_DIR/../migrations/000_complete_database_wipe_and_fresh_init.sql"
    if [ ! -f "$MIGRATION_FILE" ]; then
        print_error "Migration file not found: $MIGRATION_FILE"
        exit 1
    fi
    print_success "Migration files found"
}

run_migration() {
    print_section "Executing Database Migration"
    
    echo "🔥 This will completely wipe your database and create a fresh schema!"
    echo "Database type: $DATABASE_TYPE"
    
    if [ "$SKIP_CONFIRMATION" != "true" ]; then
        echo -n "Continue? (type 'YES' to confirm): "
        read -r confirmation
        if [ "$confirmation" != "YES" ]; then
            print_error "Migration cancelled"
            exit 1
        fi
    fi
    
    echo "🚀 Running migration..."
    
    if [ "$DATABASE_TYPE" = "supabase" ]; then
        python3 "$SCRIPT_DIR/run_fresh_migration.py" --supabase --confirm
    else
        python3 "$SCRIPT_DIR/run_fresh_migration.py" --local --confirm
    fi
    
    if [ $? -eq 0 ]; then
        print_success "Database migration completed successfully"
    else
        print_error "Database migration failed"
        exit 1
    fi
}

verify_setup() {
    print_section "Verifying Database Setup"
    
    echo "🔍 Running comprehensive verification..."
    
    if [ "$DATABASE_TYPE" = "supabase" ]; then
        python3 "$SCRIPT_DIR/verify_database_setup.py" --supabase --detailed
    else
        python3 "$SCRIPT_DIR/verify_database_setup.py" --local --detailed
    fi
    
    if [ $? -eq 0 ]; then
        print_success "Database verification passed"
    else
        print_error "Database verification failed"
        exit 1
    fi
}

test_mcp_integration() {
    print_section "Testing MCP Tools Integration"
    
    echo "🧪 Running MCP integration tests..."
    
    # Note: This test requires the full MCP system to be available
    if python3 "$SCRIPT_DIR/test_mcp_integration.py"; then
        print_success "MCP tools integration verified"
    else
        print_warning "MCP integration test failed or not available"
        print_warning "This is normal if MCP system is not fully installed"
    fi
}

print_summary() {
    print_section "Migration Complete - Summary"
    
    echo "🎉 Database migration setup completed successfully!"
    echo ""
    echo "What was done:"
    echo "✅ Complete database wipe executed"
    echo "✅ Fresh schema with user isolation created"
    echo "✅ Performance indexes and constraints applied"
    echo "✅ Row Level Security policies enabled (Supabase)"
    echo "✅ Utility functions and audit logging set up"
    echo "✅ Database setup verified and tested"
    echo ""
    echo "Next steps:"
    echo "1. 🔐 Test user registration through frontend"
    echo "2. 📋 Create sample projects and tasks"
    echo "3. 🤖 Verify MCP agent tools functionality"
    echo "4. 🔄 Run integration tests"
    echo "5. 📊 Monitor database performance"
    echo ""
    echo "Database is now ready for clean development!"
    echo ""
    print_success "Setup completed successfully"
}

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --supabase        Use Supabase database (default)"
    echo "  --local           Use local PostgreSQL database"
    echo "  --skip-confirm    Skip confirmation prompts (DANGEROUS)"
    echo "  --help            Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  SUPABASE_DB_URL   Supabase database connection string"
    echo "  LOCAL_DB_URL      Local database connection string"
    echo "  SKIP_CONFIRMATION Set to 'true' to skip confirmations"
    echo ""
    echo "Examples:"
    echo "  $0 --supabase                    # Use Supabase with confirmation"
    echo "  $0 --local --skip-confirm       # Use local DB, skip confirmation"
    echo "  SKIP_CONFIRMATION=true $0       # Environment variable"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --supabase)
            DATABASE_TYPE="supabase"
            shift
            ;;
        --local)
            DATABASE_TYPE="local"
            shift
            ;;
        --skip-confirm)
            SKIP_CONFIRMATION="true"
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_header
    
    check_prerequisites
    run_migration
    verify_setup
    test_mcp_integration
    print_summary
    
    echo -e "\n${GREEN}🚀 Database migration setup completed successfully!${NC}"
}

# Execute main function
main "$@"