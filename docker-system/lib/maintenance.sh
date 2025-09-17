#!/bin/bash
# maintenance.sh - Maintenance commands

source "${SCRIPT_DIR}/lib/common.sh"
source "${SCRIPT_DIR}/lib/backup.sh"

# Maintenance command dispatcher  
maintenance_command() {
    local subcommand="$1"
    shift
    
    case "$subcommand" in
        create|restore|list|verify)
            ${subcommand}_backup "$@"
            ;;
        *)
            error "Unknown maintenance command: $subcommand"
            echo "Valid commands: create, restore, list, verify"
            return 1
            ;;
    esac
}

# Backup command dispatcher
backup_command() {
    local subcommand="$1"
    shift
    
    case "$subcommand" in
        create)
            create_backup "$@"
            ;;
        restore)
            restore_backup "$@"
            ;;
        list)
            list_backups "$@"
            ;;
        verify)
            verify_backup "$@"
            ;;
        *)
            error "Unknown backup command: $subcommand"
            echo "Valid commands: create, restore, list, verify"
            return 1
            ;;
    esac
}

# Cleanup command
cleanup_command() {
    info "🧹 Cleaning up Docker resources..."
    
    # Remove stopped containers
    echo -n "  Removing stopped containers... "
    local removed=$(docker container prune -f 2>&1 | grep -oE "[0-9]+ deleted" || echo "0 deleted")
    echo "$removed"
    
    # Remove unused images
    echo -n "  Removing unused images... "
    removed=$(docker image prune -f 2>&1 | grep -oE "reclaimed [0-9.]+[KMG]?B" || echo "reclaimed 0B")
    echo "$removed"
    
    # Remove unused volumes (careful!)
    if confirm "Remove unused volumes? (This cannot be undone)"; then
        echo -n "  Removing unused volumes... "
        removed=$(docker volume prune -f 2>&1 | grep -oE "reclaimed [0-9.]+[KMG]?B" || echo "reclaimed 0B")
        echo "$removed"
    fi
    
    # Remove unused networks
    echo -n "  Removing unused networks... "
    removed=$(docker network prune -f 2>&1 | grep -oE "[0-9]+ deleted" || echo "0 deleted")
    echo "$removed"
    
    # Clean build cache
    if confirm "Clean build cache?"; then
        echo -n "  Cleaning build cache... "
        removed=$(docker builder prune -f 2>&1 | grep -oE "reclaimed [0-9.]+[KMG]?B" || echo "reclaimed 0B")
        echo "$removed"
    fi
    
    # Clean old backups
    cleanup_old_backups
    
    # Clean logs
    if [[ -d "${PROJECT_ROOT}/logs" ]]; then
        echo -n "  Cleaning old logs... "
        find "${PROJECT_ROOT}/logs" -name "*.log" -mtime +7 -delete
        echo "done"
    fi
    
    success "Cleanup completed"
}

# Update command
update_command() {
    info "🔄 Updating 4genthub system..."
    
    # Check for updates
    echo "  Checking for updates..."
    
    # Pull latest images
    info "Pulling latest Docker images..."
    local compose_args=$(compose_file_args)
    cd "$SCRIPT_DIR"
    
    docker compose $compose_args pull
    
    # Check if running
    if docker compose $compose_args ps -q | grep -q .; then
        warning "Services are running. Update will require restart."
        
        if confirm "Restart services with new images?"; then
            # Create backup first
            info "Creating backup before update..."
            create_backup database
            
            # Restart with new images
            restart_command
            
            # Run migrations
            info "Running database migrations..."
            db_operation migrate
        else
            info "Update downloaded but not applied. Run 'restart' when ready."
        fi
    else
        success "Updates downloaded. Run 'start' to use new versions."
    fi
    
    # Update CLI scripts
    if [[ -d "${SCRIPT_DIR}/.git" ]]; then
        info "Updating CLI scripts..."
        cd "$SCRIPT_DIR"
        git pull origin main || warning "Could not update CLI scripts"
    fi
    
    success "Update completed"
}