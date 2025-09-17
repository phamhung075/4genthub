#!/bin/bash
# docker-cli.sh - Unified Docker CLI Interface for 4genthub
# PostgreSQL-first architecture with no backward compatibility

set -euo pipefail

# Constants
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly LIB_DIR="${SCRIPT_DIR}/lib"
readonly ENV_DIR="${SCRIPT_DIR}/environments"
readonly DEFAULT_ENV="${ENV:-dev}"

# Export for child scripts
export PROJECT_ROOT
export SCRIPT_DIR

# Source common functions
source "${LIB_DIR}/common.sh"

# Load default environment from project root
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    set -a
    source "${PROJECT_ROOT}/.env"
    set +a
fi

# Global variables
COMMAND="${1:-}"
shift 1 2>/dev/null || shift $# 2>/dev/null
SUBCOMMAND="${1:-}"
shift 1 2>/dev/null || shift $# 2>/dev/null

# Display help
show_help() {
    cat << EOF
🐳 4genthub Docker CLI - PostgreSQL Edition

USAGE: ./docker-cli.sh [command] [subcommand] [options]

CORE COMMANDS:
  start                    Start all services
  stop                     Stop all services  
  restart                  Restart all services
  status                   Show service status
  logs [service]           View service logs
  shell [service]          Access service shell

DATABASE COMMANDS:
  db status                Show database status
  db init                  Initialize database
  db migrate               Run migrations
  db backup                Create database backup
  db restore [file]        Restore from backup
  db shell                 Access database shell
  db reset                 Reset database (WARNING: destructive)

DEVELOPMENT COMMANDS:
  dev setup                Setup development environment
  dev reset                Reset development data
  dev seed                 Seed development data
  build [service]          Build service images
  test [type]              Run tests (unit|integration|e2e|all)

DEPLOYMENT COMMANDS:
  deploy [env]             Deploy to environment (staging|production)
  scale [service] [count]  Scale service replicas
  health                   System health check
  monitor                  Real-time monitoring dashboard

MAINTENANCE COMMANDS:
  backup create [type]     Create backup (full|database|volumes|configs)
  backup restore [file]    Restore from backup
  backup list              List available backups
  cleanup                  Clean unused resources
  update                   Update system components

CONFIGURATION COMMANDS:
  config show              Show current configuration
  config set [key] [val]   Set configuration value
  config validate          Validate configuration
  env [environment]        Switch environment (dev|staging|production)

TROUBLESHOOTING COMMANDS:
  diagnose                 Run system diagnostics
  fix-permissions          Fix file permissions
  emergency-backup         Create emergency backup
  support-bundle           Generate support bundle

WORKFLOW COMMANDS:
  workflow dev-setup       Complete development setup
  workflow prod-deploy     Production deployment workflow
  workflow backup-restore  Backup and restore workflow

OPTIONS:
  -h, --help              Show this help message
  -v, --verbose           Verbose output
  -q, --quiet             Quiet mode
  --dry-run               Show what would be done
  --force                 Force operation without confirmation

EXAMPLES:
  ./docker-cli.sh start                    # Start all services
  ./docker-cli.sh db backup                # Backup database
  ./docker-cli.sh logs backend --tail 50   # View backend logs
  ./docker-cli.sh deploy production        # Deploy to production
  ./docker-cli.sh workflow dev-setup       # Full dev environment setup

For detailed help on a specific command:
  ./docker-cli.sh help [command]

EOF
}

# Environment loading is handled by common.sh

# Command routing
case "$COMMAND" in
    # Core commands
    start|stop|restart|status|logs|shell)
        source "${LIB_DIR}/core.sh"
        # For commands that take a service parameter, pass SUBCOMMAND as first argument
        if [[ "$COMMAND" == "logs" || "$COMMAND" == "shell" || "$COMMAND" == "restart" ]] && [[ -n "$SUBCOMMAND" ]]; then
            ${COMMAND}_command "$SUBCOMMAND" "$@"
        else
            ${COMMAND}_command "$@"
        fi
        ;;
    
    # Database commands
    db)
        source "${LIB_DIR}/database/interface.sh"
        db_command "$SUBCOMMAND" "$@"
        ;;
    
    # Development commands
    dev|build|test)
        source "${LIB_DIR}/development.sh"
        ${COMMAND}_command "$SUBCOMMAND" "$@"
        ;;
    
    # Special case for monitor-snapshot
    monitor-snapshot)
        source "${LIB_DIR}/monitoring.sh"
        monitor_snapshot_command
        ;;
    
    # Deployment commands
    deploy|scale|health|monitor)
        source "${LIB_DIR}/deployment.sh"
        ${COMMAND}_command "$@"
        ;;
    
    # Maintenance commands
    backup|cleanup|update)
        source "${LIB_DIR}/maintenance.sh"
        ${COMMAND}_command "$SUBCOMMAND" "$@"
        ;;
    
    # Configuration commands
    config|env)
        source "${LIB_DIR}/configuration.sh"
        ${COMMAND}_command "$SUBCOMMAND" "$@"
        ;;
    
    # Troubleshooting commands
    diagnose|fix-permissions|emergency-backup|support-bundle)
        source "${LIB_DIR}/troubleshooting.sh"
        # Convert dashes to underscores for function names
        FUNCTION_NAME="${COMMAND//-/_}_command"
        $FUNCTION_NAME "$@"
        ;;
    
    # Workflow commands
    workflow)
        source "${LIB_DIR}/workflows.sh"
        workflow_command "$SUBCOMMAND" "$@"
        ;;
    
    # Help
    help|-h|--help|"")
        if [[ -n "${SUBCOMMAND:-}" ]]; then
            show_command_help "$SUBCOMMAND"
        else
            show_help
        fi
        ;;
    
    # Unknown command
    *)
        error "Unknown command: $COMMAND"
        echo "Run './docker-cli.sh help' for usage information"
        exit 1
        ;;
esac