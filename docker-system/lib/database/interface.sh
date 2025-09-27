#!/bin/bash
# database/interface.sh - Database abstraction layer

source "${SCRIPT_DIR}/lib/common.sh"

# Database factory pattern
db_operation() {
    local operation="$1"
    shift
    
    # Currently only PostgreSQL is supported
    local db_type="${DATABASE_TYPE:-postgresql}"
    
    case "$db_type" in
        postgresql)
            source "${SCRIPT_DIR}/lib/database/postgresql.sh"
            postgresql_${operation} "$@"
            ;;
        sqlite)
            error "SQLite support not implemented yet"
            return 1
            ;;
        *)
            error "Unsupported database type: $db_type"
            return 1
            ;;
    esac
}

# Database command dispatcher
db_command() {
    local subcommand="$1"
    shift
    
    case "$subcommand" in
        status)
            db_operation status "$@"
            ;;
        init)
            db_operation init "$@"
            ;;
        migrate)
            db_operation migrate "$@"
            ;;
        backup)
            db_operation backup "$@"
            ;;
        restore)
            db_operation restore "$@"
            ;;
        shell)
            db_operation shell "$@"
            ;;
        reset)
            if confirm "⚠️  This will DELETE ALL DATA. Are you sure?"; then
                db_operation reset "$@"
            else
                info "Operation cancelled"
            fi
            ;;
        test-connection)
            db_operation test_connection "$@"
            ;;
        analyze)
            db_operation analyze "$@"
            ;;
        slow-queries)
            db_operation slow_queries "$@"
            ;;
        optimize)
            db_operation optimize "$@"
            ;;
        health-check)
            db_operation health_check "$@"
            ;;
        *)
            error "Unknown database command: $subcommand"
            echo "Valid commands: status, init, migrate, backup, restore, shell, reset"
            return 1
            ;;
    esac
}

# Export functions
export -f db_operation db_command