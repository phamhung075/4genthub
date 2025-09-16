#!/bin/bash
# DhafnckMCP Deployment Manager
# Enhanced deployment automation with health checks and rollback capability
# Version: 2.1.0 - Phase 6 Production Optimization

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
RESET='\033[0m'
BOLD='\033[1m'

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
DOCKER_DIR="${SCRIPT_DIR}/docker"

# Default configuration
DEFAULT_ENV_FILE="${PROJECT_ROOT}/.env.dev"
DEPLOYMENT_LOG="${PROJECT_ROOT}/logs/deployment-$(date +%Y%m%d-%H%M%S).log"
BACKUP_DIR="${PROJECT_ROOT}/logs/backups"
MAX_ROLLBACK_ATTEMPTS=3
HEALTH_CHECK_TIMEOUT=300
DEPLOYMENT_TIMEOUT=600

# Ensure logs directory exists
mkdir -p "$(dirname "${DEPLOYMENT_LOG}")" "${BACKUP_DIR}"

# Logging functions
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${RESET} $1" | tee -a "${DEPLOYMENT_LOG}"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${RESET} $1" | tee -a "${DEPLOYMENT_LOG}"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${RESET} $1" | tee -a "${DEPLOYMENT_LOG}"
}

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${RESET} $1" | tee -a "${DEPLOYMENT_LOG}"
}

# Load environment configuration
load_env() {
    local env_file="${1:-${DEFAULT_ENV_FILE}}"

    if [[ -f "$env_file" ]]; then
        set -a
        source <(grep -v '^#' "$env_file" | grep -v '^$' | sed 's/\r$//')
        set +a
        log "Loaded configuration from $env_file"
    else
        log_error "Environment file not found: $env_file"
        exit 1
    fi
}

# Health check function
check_service_health() {
    local service_name="$1"
    local health_url="$2"
    local max_attempts="${3:-30}"
    local attempt=1

    log_info "Checking health of $service_name..."

    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$health_url" > /dev/null 2>&1; then
            log "✅ $service_name is healthy"
            return 0
        fi

        if [ $attempt -eq $max_attempts ]; then
            log_error "❌ $service_name health check failed after $max_attempts attempts"
            return 1
        fi

        log_info "  Attempt $attempt/$max_attempts failed, retrying in 10s..."
        sleep 10
        ((attempt++))
    done
}

# Database backup function
backup_database() {
    if [[ -z "${DATABASE_HOST:-}" || -z "${DATABASE_NAME:-}" || -z "${DATABASE_USER:-}" ]]; then
        log_warning "Database configuration not found, skipping backup"
        return 0
    fi

    local backup_file="${BACKUP_DIR}/db_backup_$(date +%Y%m%d_%H%M%S).sql"

    log_info "Creating database backup..."

    if docker exec dhafnck-postgres pg_dump -U "${DATABASE_USER}" -d "${DATABASE_NAME}" > "$backup_file" 2>/dev/null; then
        log "✅ Database backup created: $backup_file"
        return 0
    else
        log_error "❌ Database backup failed"
        return 1
    fi
}

# Docker network setup
setup_docker_network() {
    local network_name="dhafnck-network"

    if ! docker network ls --format '{{.Name}}' | grep -q "^${network_name}$"; then
        log_info "Creating Docker network: $network_name"
        docker network create "$network_name"
        log "✅ Docker network created: $network_name"
    else
        log_info "Docker network already exists: $network_name"
    fi
}

# Clean up function
cleanup_old_containers() {
    log_info "Cleaning up old containers and images..."

    # Stop and remove old containers
    docker container prune -f

    # Remove unused images (keep tagged images)
    docker image prune -f

    # Remove unused volumes (with confirmation)
    if [[ "${FORCE_CLEANUP:-false}" == "true" ]]; then
        docker volume prune -f
    fi

    log "✅ Cleanup completed"
}

# Production deployment function
deploy_production() {
    local compose_file="${DOCKER_DIR}/docker-compose.production.yml"
    local env_file="${PROJECT_ROOT}/.env"

    log "🚀 Starting production deployment..."

    # Ensure environment file exists
    if [[ ! -f "$env_file" ]]; then
        log_error "Production environment file not found: $env_file"
        log_error "Please create .env file with production configuration"
        exit 1
    fi

    # Load production environment
    load_env "$env_file"

    # Setup Docker network
    setup_docker_network

    # Create database backup
    backup_database

    # Build and deploy services
    log_info "Building and deploying services..."

    docker compose -f "$compose_file" --env-file "$env_file" build --no-cache
    docker compose -f "$compose_file" --env-file "$env_file" up -d

    # Health checks
    local backend_url="http://localhost:${MCP_PORT:-8001}/health"

    if check_service_health "Backend" "$backend_url" 30; then
        log "🎉 Production deployment successful!"
        log_info "Backend available at: $backend_url"

        # Optional frontend health check
        if [[ "${DEPLOY_FRONTEND:-false}" == "true" ]]; then
            local frontend_url="http://localhost:${FRONTEND_PORT:-3800}"
            check_service_health "Frontend" "$frontend_url" 15
        fi
    else
        log_error "❌ Production deployment failed health checks"
        log_error "Check logs: docker compose -f $compose_file logs"
        exit 1
    fi
}

# Development deployment function
deploy_development() {
    local compose_file="${DOCKER_DIR}/docker-compose.dev.yml"
    local env_file="${PROJECT_ROOT}/.env.dev"

    log "🛠️ Starting development deployment..."

    # Load development environment
    load_env "$env_file"

    # Setup Docker network
    setup_docker_network

    # Deploy development stack
    log_info "Deploying development stack..."

    docker compose -f "$compose_file" --env-file "$env_file" up -d --build

    # Health checks
    local backend_url="http://localhost:${FASTMCP_PORT:-8000}/health"

    if check_service_health "Backend" "$backend_url" 30; then
        log "🎉 Development deployment successful!"
        log_info "Backend available at: $backend_url"
        log_info "API Documentation: http://localhost:${FASTMCP_PORT:-8000}/docs"
    else
        log_error "❌ Development deployment failed"
        exit 1
    fi
}

# Database-only deployment
deploy_database_only() {
    local compose_file="${DOCKER_DIR}/docker-compose.db-only.yml"
    local env_file="${1:-${DEFAULT_ENV_FILE}}"

    log "🗄️ Starting database-only deployment..."

    load_env "$env_file"
    setup_docker_network

    docker compose -f "$compose_file" --env-file "$env_file" up -d

    # Wait for database to be ready
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker exec dhafnck-postgres pg_isready -U "${DATABASE_USER:-dhafnck_user}" 2>/dev/null; then
            log "✅ Database is ready"
            break
        fi

        if [ $attempt -eq $max_attempts ]; then
            log_error "❌ Database failed to start after $max_attempts attempts"
            exit 1
        fi

        log_info "  Waiting for database... ($attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done

    log "🎉 Database deployment successful!"
}

# Rollback function
rollback_deployment() {
    local backup_file="$1"

    if [[ -z "$backup_file" || ! -f "$backup_file" ]]; then
        log_error "❌ Backup file not found or not specified"
        exit 1
    fi

    log "🔄 Rolling back deployment..."

    # Stop current services
    docker compose -f "${DOCKER_DIR}/docker-compose.production.yml" down

    # Restore database if backup exists
    if [[ "$backup_file" == *.sql ]]; then
        log_info "Restoring database from backup..."
        docker exec -i dhafnck-postgres psql -U "${DATABASE_USER}" -d "${DATABASE_NAME}" < "$backup_file"
    fi

    log "✅ Rollback completed"
}

# Status check function
check_status() {
    log "📊 Checking deployment status..."

    echo -e "\n${BOLD}=== Container Status ===${RESET}"
    docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

    echo -e "\n${BOLD}=== Service Health ===${RESET}"

    # Check backend health
    if curl -s -f "http://localhost:${FASTMCP_PORT:-8000}/health" > /dev/null 2>&1; then
        echo -e "Backend: ${GREEN}✅ Healthy${RESET}"
    else
        echo -e "Backend: ${RED}❌ Unhealthy${RESET}"
    fi

    # Check database
    if docker exec dhafnck-postgres pg_isready -U "${DATABASE_USER:-dhafnck_user}" 2>/dev/null; then
        echo -e "Database: ${GREEN}✅ Ready${RESET}"
    else
        echo -e "Database: ${RED}❌ Not Ready${RESET}"
    fi

    echo -e "\n${BOLD}=== Recent Logs ===${RESET}"
    echo "Deployment log: $DEPLOYMENT_LOG"
}

# Main menu
show_menu() {
    echo -e "\n${BOLD}${CYAN}DhafnckMCP Deployment Manager${RESET}"
    echo -e "${CYAN}================================${RESET}"
    echo -e "${BOLD}1.${RESET} Deploy Production"
    echo -e "${BOLD}2.${RESET} Deploy Development"
    echo -e "${BOLD}3.${RESET} Deploy Database Only"
    echo -e "${BOLD}4.${RESET} Check Status"
    echo -e "${BOLD}5.${RESET} Cleanup Resources"
    echo -e "${BOLD}6.${RESET} Rollback (specify backup file)"
    echo -e "${BOLD}7.${RESET} View Logs"
    echo -e "${BOLD}0.${RESET} Exit"
    echo ""
}

# Main execution
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -p|--production)
                deploy_production
                exit 0
                ;;
            -d|--development)
                deploy_development
                exit 0
                ;;
            --db-only)
                deploy_database_only
                exit 0
                ;;
            -s|--status)
                check_status
                exit 0
                ;;
            -c|--cleanup)
                FORCE_CLEANUP=true
                cleanup_old_containers
                exit 0
                ;;
            --rollback)
                shift
                rollback_deployment "$1"
                exit 0
                ;;
            -h|--help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  -p, --production     Deploy production environment"
                echo "  -d, --development    Deploy development environment"
                echo "  --db-only           Deploy database only"
                echo "  -s, --status        Check deployment status"
                echo "  -c, --cleanup       Cleanup Docker resources"
                echo "  --rollback FILE     Rollback to backup"
                echo "  -h, --help          Show this help"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
        shift
    done

    # Interactive mode
    while true; do
        show_menu
        read -p "Select option [0-7]: " choice

        case $choice in
            1)
                deploy_production
                ;;
            2)
                deploy_development
                ;;
            3)
                deploy_database_only
                ;;
            4)
                check_status
                ;;
            5)
                read -p "Force cleanup volumes? (y/N): " confirm
                if [[ "$confirm" =~ ^[Yy]$ ]]; then
                    FORCE_CLEANUP=true
                fi
                cleanup_old_containers
                ;;
            6)
                read -p "Enter backup file path: " backup_file
                rollback_deployment "$backup_file"
                ;;
            7)
                tail -n 50 "$DEPLOYMENT_LOG"
                ;;
            0)
                log "👋 Goodbye!"
                exit 0
                ;;
            *)
                log_error "Invalid option: $choice"
                ;;
        esac

        echo ""
        read -p "Press Enter to continue..."
    done
}

# Execute main function
main "$@"