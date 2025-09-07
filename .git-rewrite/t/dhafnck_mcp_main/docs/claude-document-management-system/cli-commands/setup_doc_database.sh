#!/bin/bash

# setup_doc_database.sh - Set up PostgreSQL database for Claude document management
# This script creates the database, user, and initial configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Default configuration
DEFAULT_DB_HOST="localhost"
DEFAULT_DB_PORT="5432"
DEFAULT_DB_NAME="claude_docs"
DEFAULT_DB_USER="claude"
DEFAULT_ADMIN_DB="postgres"

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "\n${BOLD}$1${NC}"
    echo "$(printf '%.0s=' {1..60})"
}

# Check if PostgreSQL is installed and running
check_postgresql() {
    if ! command -v psql &> /dev/null; then
        print_error "PostgreSQL is not installed. Please install it first:"
        echo "  Ubuntu/Debian: sudo apt install postgresql postgresql-contrib"
        echo "  CentOS/RHEL: sudo yum install postgresql postgresql-server"
        echo "  macOS: brew install postgresql"
        return 1
    fi
    
    if ! sudo systemctl is-active --quiet postgresql 2>/dev/null; then
        print_warning "PostgreSQL is not running. Starting it..."
        if sudo systemctl start postgresql 2>/dev/null; then
            print_success "PostgreSQL started successfully"
        else
            print_error "Failed to start PostgreSQL. Please start it manually."
            return 1
        fi
    fi
    
    print_success "PostgreSQL is installed and running"
}

# Get configuration from user
get_configuration() {
    print_header "Database Configuration"
    
    read -p "Database host [$DEFAULT_DB_HOST]: " DB_HOST
    DB_HOST=${DB_HOST:-$DEFAULT_DB_HOST}
    
    read -p "Database port [$DEFAULT_DB_PORT]: " DB_PORT
    DB_PORT=${DB_PORT:-$DEFAULT_DB_PORT}
    
    read -p "Database name [$DEFAULT_DB_NAME]: " DB_NAME
    DB_NAME=${DB_NAME:-$DEFAULT_DB_NAME}
    
    read -p "Database user [$DEFAULT_DB_USER]: " DB_USER
    DB_USER=${DB_USER:-$DEFAULT_DB_USER}
    
    while true; do
        read -s -p "Database password for $DB_USER: " DB_PASSWORD
        echo
        read -s -p "Confirm password: " DB_PASSWORD_CONFIRM
        echo
        
        if [ "$DB_PASSWORD" = "$DB_PASSWORD_CONFIRM" ]; then
            break
        else
            print_error "Passwords do not match. Please try again."
        fi
    done
    
    print_info "Configuration:"
    echo "  Host: $DB_HOST"
    echo "  Port: $DB_PORT"
    echo "  Database: $DB_NAME"
    echo "  User: $DB_USER"
}

# Create database and user
create_database() {
    print_header "Creating Database and User"
    
    # Connect as postgres user to create database and user
    print_info "Creating database and user (you may be prompted for postgres password)..."
    
    # Check if database exists
    if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
        print_warning "Database '$DB_NAME' already exists"
    else
        # Create database
        if sudo -u postgres createdb "$DB_NAME"; then
            print_success "Database '$DB_NAME' created"
        else
            print_error "Failed to create database '$DB_NAME'"
            return 1
        fi
    fi
    
    # Check if user exists
    if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
        print_warning "User '$DB_USER' already exists"
        # Update password
        if sudo -u postgres psql -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"; then
            print_success "Password updated for user '$DB_USER'"
        fi
    else
        # Create user
        if sudo -u postgres psql -c "CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASSWORD';"; then
            print_success "User '$DB_USER' created"
        else
            print_error "Failed to create user '$DB_USER'"
            return 1
        fi
    fi
    
    # Grant privileges
    if sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"; then
        print_success "Privileges granted to user '$DB_USER'"
    else
        print_error "Failed to grant privileges"
        return 1
    fi
    
    # Grant schema privileges
    if sudo -u postgres psql -d "$DB_NAME" -c "GRANT USAGE, CREATE ON SCHEMA public TO $DB_USER;"; then
        print_success "Schema privileges granted"
    else
        print_warning "Could not grant schema privileges (may need to run after tables are created)"
    fi
}

# Test database connection
test_connection() {
    print_header "Testing Database Connection"
    
    export PGPASSWORD="$DB_PASSWORD"
    
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT version();" > /dev/null 2>&1; then
        print_success "Database connection successful"
        
        # Get PostgreSQL version
        local version=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT version();" | head -1)
        print_info "PostgreSQL version: $version"
    else
        print_error "Database connection failed"
        print_error "Please check your configuration and try again"
        return 1
    fi
    
    unset PGPASSWORD
}

# Create environment configuration
create_env_config() {
    print_header "Creating Environment Configuration"
    
    local env_file="$HOME/.claude_doc_env"
    
    cat > "$env_file" << EOF
# Claude Document Management Database Configuration
# Source this file in your shell profile: source ~/.claude_doc_env

export CLAUDE_DOC_DB_HOST="$DB_HOST"
export CLAUDE_DOC_DB_PORT="$DB_PORT"
export CLAUDE_DOC_DB_NAME="$DB_NAME"
export CLAUDE_DOC_DB_USER="$DB_USER"
export CLAUDE_DOC_DB_PASSWORD="$DB_PASSWORD"

# PostgreSQL connection string
export CLAUDE_DOC_DB_URL="postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
EOF
    
    chmod 600 "$env_file"
    print_success "Environment configuration saved to: $env_file"
    
    # Add to .bashrc if it exists and doesn't already contain the source
    if [ -f "$HOME/.bashrc" ]; then
        if ! grep -q "source.*\.claude_doc_env" "$HOME/.bashrc"; then
            echo "" >> "$HOME/.bashrc"
            echo "# Claude Document Management Environment" >> "$HOME/.bashrc"
            echo "source ~/.claude_doc_env" >> "$HOME/.bashrc"
            print_success "Added configuration to ~/.bashrc"
        fi
    fi
    
    print_info "To use in current session, run: source $env_file"
}

# Initialize database schema
initialize_schema() {
    print_header "Initializing Database Schema"
    
    if [ -x ".claude/commands/manage_document_md_postgresql" ]; then
        source "$HOME/.claude_doc_env"
        if .claude/commands/manage_document_md_postgresql init; then
            print_success "Database schema initialized"
        else
            print_error "Failed to initialize database schema"
            return 1
        fi
    else
        print_warning "manage_document_md_postgresql not found or not executable"
        print_info "You can initialize the schema manually later with:"
        print_info "  .claude/commands/manage_document_md_postgresql init"
    fi
}

# Create systemd service for auto-sync (optional)
create_sync_service() {
    print_header "Creating Auto-Sync Service (Optional)"
    
    read -p "Create systemd service for automatic document synchronization? [y/N]: " create_service
    
    if [[ "$create_service" =~ ^[Yy]$ ]]; then
        local service_file="/etc/systemd/system/claude-doc-sync.service"
        local timer_file="/etc/systemd/system/claude-doc-sync.timer"
        local script_path="$(pwd)/.claude/commands/manage_document_md_postgresql"
        
        # Create service file
        sudo tee "$service_file" > /dev/null << EOF
[Unit]
Description=Claude Document Synchronization
After=postgresql.service

[Service]
Type=oneshot
User=$USER
WorkingDirectory=$(pwd)
Environment=HOME=$HOME
ExecStart=$script_path sync
StandardOutput=journal
StandardError=journal
EOF
        
        # Create timer file
        sudo tee "$timer_file" > /dev/null << EOF
[Unit]
Description=Run Claude Document Sync every 5 minutes
Requires=claude-doc-sync.service

[Timer]
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
EOF
        
        # Reload systemd and enable timer
        sudo systemctl daemon-reload
        sudo systemctl enable claude-doc-sync.timer
        sudo systemctl start claude-doc-sync.timer
        
        print_success "Auto-sync service created and enabled"
        print_info "Service runs every 5 minutes"
        print_info "Check status: sudo systemctl status claude-doc-sync.timer"
    else
        print_info "Skipping service creation"
    fi
}

# Show post-installation instructions
show_instructions() {
    print_header "Post-Installation Instructions"
    
    cat << EOF
${GREEN}Setup Complete!${NC}

${BOLD}Next Steps:${NC}

1. ${CYAN}Source environment variables:${NC}
   source ~/.claude_doc_env

2. ${CYAN}Test the system:${NC}
   .claude/commands/manage_document_md_postgresql sync
   .claude/commands/manage_document_md_postgresql list

3. ${CYAN}Generate initial index:${NC}
   .claude/commands/manage_document_md_postgresql index

4. ${CYAN}Try searching:${NC}
   .claude/commands/manage_document_md_postgresql search "postgresql"

${BOLD}Useful Commands:${NC}
   ${CYAN}Sync documents:${NC}       .claude/commands/manage_document_md_postgresql sync
   ${CYAN}Search documents:${NC}     .claude/commands/manage_document_md_postgresql search "query"
   ${CYAN}List documents:${NC}       .claude/commands/manage_document_md_postgresql list
   ${CYAN}Show help:${NC}            .claude/commands/manage_document_md_postgresql help

${BOLD}Database Information:${NC}
   ${CYAN}Host:${NC}        $DB_HOST:$DB_PORT
   ${CYAN}Database:${NC}    $DB_NAME
   ${CYAN}User:${NC}        $DB_USER
   ${CYAN}Config file:${NC} ~/.claude_doc_env

${BOLD}Troubleshooting:${NC}
   ${CYAN}Test connection:${NC}  psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME
   ${CYAN}View logs:${NC}         journalctl -u claude-doc-sync.service
   ${CYAN}Manual sync:${NC}       .claude/commands/manage_document_md_postgresql sync --force

For detailed documentation, see:
  dhafnck_mcp_main/docs/claude-document-management-implementation.md
EOF
}

# Main execution
main() {
    print_header "Claude Document Management Database Setup"
    
    # Check prerequisites
    if ! check_postgresql; then
        exit 1
    fi
    
    # Get configuration
    get_configuration
    
    # Create database and user
    if ! create_database; then
        exit 1
    fi
    
    # Test connection
    if ! test_connection; then
        exit 1
    fi
    
    # Create environment configuration
    create_env_config
    
    # Initialize schema
    initialize_schema
    
    # Optional: create sync service
    create_sync_service
    
    # Show final instructions
    show_instructions
    
    print_success "Claude Document Management setup completed successfully!"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Do not run this script as root"
    exit 1
fi

# Check if in correct directory
if [ ! -d ".claude/commands" ]; then
    print_error "This script must be run from the project root directory"
    print_error "Expected to find .claude/commands/ directory"
    exit 1
fi

# Run main function
main "$@"