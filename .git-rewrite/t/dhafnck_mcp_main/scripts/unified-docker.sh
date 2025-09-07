#!/bin/bash

# =============================================================================
# DhafnckMCP Unified Docker Management Script
# Handles both Supabase (production) and PostgreSQL Docker (local development)
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_ROOT/docker"
CONTAINER_NAME="dhafnck-mcp-server"
FRONTEND_CONTAINER="dhafnck-frontend"
POSTGRES_CONTAINER="dhafnck-postgres"
REDIS_CONTAINER="dhafnck-redis"

# Environment detection
DEFAULT_MODE="local"
DETACHED=false
VERBOSE=false

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

print_banner() {
    echo -e "${CYAN}=================================================${NC}"
    echo -e "${CYAN}🚀 DhafnckMCP Unified Docker Manager${NC}"
    echo -e "${CYAN}=================================================${NC}"
    echo ""
}

print_usage() {
    print_banner
    echo "Usage: $0 [OPTIONS] <COMMAND> [MODE]"
    echo ""
    echo -e "${YELLOW}COMMANDS:${NC}"
    echo "  start        Start the Docker environment"
    echo "  stop         Stop the Docker environment"
    echo "  restart      Restart the Docker environment"
    echo "  status       Show system status"
    echo "  logs         Show container logs"
    echo "  shell        Open shell in MCP container"
    echo "  health       Perform health checks"
    echo "  clean        Clean up containers and volumes"
    echo "  rebuild      Full rebuild (stop, clean, build, start)"
    echo ""
    echo -e "${YELLOW}MODES:${NC}"
    echo "  local        Local development with PostgreSQL Docker (default)"
    echo "  production   Production mode with Supabase"
    echo "  dev          Development mode with live reload"
    echo ""
    echo -e "${YELLOW}OPTIONS:${NC}"
    echo "  -d, --detached    Run in detached mode (background)"
    echo "  -v, --verbose     Enable verbose output"
    echo "  -h, --help        Show this help message"
    echo ""
    echo -e "${YELLOW}EXAMPLES:${NC}"
    echo "  $0 start                    # Start local development environment"
    echo "  $0 start production         # Start production environment with Supabase"
    echo "  $0 -d start local          # Start local development in background"
    echo "  $0 logs -f                 # Follow live logs"
    echo "  $0 health                  # Check system health"
    echo "  $0 rebuild production      # Full production rebuild"
    echo ""
    echo -e "${YELLOW}DATABASE CONFIGURATIONS:${NC}"
    echo "  Local Mode:      PostgreSQL + Redis in Docker containers"
    echo "  Production Mode: External Supabase + Redis in Docker"
    echo "  Dev Mode:        PostgreSQL + Redis with live code reload"
}

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${CYAN}🔍 $1${NC}"
    fi
}

# =============================================================================
# SYSTEM CHECKS
# =============================================================================

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        log_error "Docker is not running"
        exit 1
    fi
    
    log_success "All prerequisites met"
}

check_environment_file() {
    local env_file="$PROJECT_ROOT/.env"
    if [ ! -f "$env_file" ]; then
        log_warning "Environment file not found at $env_file"
        log_info "Creating default environment file..."
        cp "$PROJECT_ROOT/env.example" "$env_file" || {
            log_error "Failed to create environment file"
            exit 1
        }
        log_success "Environment file created from template"
    fi
}

# =============================================================================
# CONTAINER MANAGEMENT
# =============================================================================

check_container_exists() {
    docker ps -a --format "table {{.Names}}" | grep -q "^${1}$"
}

check_container_running() {
    docker ps --format "table {{.Names}}" | grep -q "^${1}$"
}

get_compose_files() {
    local mode="$1"
    local compose_files="-f $DOCKER_DIR/docker-compose.yml"
    
    case "$mode" in
        "local")
            compose_files="$compose_files -f $DOCKER_DIR/docker-compose.local.yml"
            ;;
        "production")
            # Production uses base configuration with Supabase
            # Environment variables handle the Supabase connection
            ;;
        "dev")
            compose_files="$compose_files -f $DOCKER_DIR/docker-compose.dev.yml"
            ;;
        *)
            log_error "Unknown mode: $mode"
            exit 1
            ;;
    esac
    
    echo "$compose_files"
}

prepare_environment() {
    local mode="$1"
    
    log_info "Preparing environment for $mode mode..."
    
    # Create data directories
    mkdir -p "$PROJECT_ROOT/data/tasks" "$PROJECT_ROOT/data/projects" "$PROJECT_ROOT/data/rules" "$PROJECT_ROOT/logs"
    
    # Set permissions (skip if fails in WSL)
    if grep -qi microsoft /proc/version 2>/dev/null; then
        log_verbose "WSL detected - skipping permission setup"
        chmod -R 755 "$PROJECT_ROOT/data" "$PROJECT_ROOT/logs" 2>/dev/null || true
    else
        chmod -R 755 "$PROJECT_ROOT/data" "$PROJECT_ROOT/logs"
    fi
    
    # Set environment variables based on mode
    case "$mode" in
        "production")
            export DATABASE_TYPE="supabase"
            export DHAFNCK_AUTH_ENABLED="true"
            export DHAFNCK_MVP_MODE="false"
            ;;
        "local"|"dev")
            export DATABASE_TYPE="postgresql"
            export DHAFNCK_AUTH_ENABLED="false"
            export DHAFNCK_MVP_MODE="true"
            ;;
    esac
    
    log_success "Environment prepared for $mode mode"
}

# =============================================================================
# MAIN COMMANDS
# =============================================================================

cmd_start() {
    local mode="${1:-$DEFAULT_MODE}"
    
    print_banner
    log_info "Starting DhafnckMCP in $mode mode..."
    
    check_prerequisites
    check_environment_file
    prepare_environment "$mode"
    
    cd "$PROJECT_ROOT"
    
    # Check if containers are already running
    if check_container_running "$CONTAINER_NAME"; then
        log_warning "Container '$CONTAINER_NAME' is already running"
        log_info "Server URL: http://localhost:8000"
        return 0
    fi
    
    # Get compose files for the mode
    local compose_files
    compose_files=$(get_compose_files "$mode")
    
    log_info "Using compose configuration: $compose_files"
    
    # Start containers
    if [ "$DETACHED" = true ]; then
        log_info "Starting containers in detached mode..."
        eval "docker-compose $compose_files up --build -d"
        log_success "Containers started successfully!"
        log_info "Server URL: http://localhost:8000"
        log_info "View logs: $0 logs"
    else
        log_info "Starting containers in interactive mode..."
        eval "docker-compose $compose_files up --build"
    fi
}

cmd_stop() {
    local mode="${1:-$DEFAULT_MODE}"
    
    log_info "Stopping DhafnckMCP containers..."
    
    cd "$PROJECT_ROOT"
    local compose_files
    compose_files=$(get_compose_files "$mode")
    
    eval "docker-compose $compose_files down"
    log_success "Containers stopped"
}

cmd_restart() {
    local mode="${1:-$DEFAULT_MODE}"
    
    log_info "Restarting DhafnckMCP..."
    cmd_stop "$mode"
    sleep 2
    cmd_start "$mode"
}

cmd_status() {
    print_banner
    log_info "System Status Report"
    echo ""
    
    # Container status
    echo -e "${YELLOW}📦 Container Status:${NC}"
    if check_container_running "$CONTAINER_NAME"; then
        echo -e "${GREEN}🟢 MCP Server: RUNNING${NC}"
        docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    else
        echo -e "${RED}🔴 MCP Server: STOPPED${NC}"
    fi
    
    if check_container_running "$FRONTEND_CONTAINER"; then
        echo -e "${GREEN}🟢 Frontend: RUNNING${NC}"
    else
        echo -e "${RED}🔴 Frontend: STOPPED${NC}"
    fi
    
    if check_container_running "$POSTGRES_CONTAINER"; then
        echo -e "${GREEN}🟢 PostgreSQL: RUNNING${NC}"
    else
        echo -e "${RED}🔴 PostgreSQL: STOPPED${NC}"
    fi
    
    if check_container_running "$REDIS_CONTAINER"; then
        echo -e "${GREEN}🟢 Redis: RUNNING${NC}"
    else
        echo -e "${RED}🔴 Redis: STOPPED${NC}"
    fi
    
    echo ""
    
    # Resource usage
    if check_container_running "$CONTAINER_NAME"; then
        echo -e "${YELLOW}💾 Resource Usage:${NC}"
        docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" \
            $CONTAINER_NAME $POSTGRES_CONTAINER $REDIS_CONTAINER 2>/dev/null || true
    fi
    
    # URLs and endpoints
    echo ""
    echo -e "${YELLOW}🌐 Service URLs:${NC}"
    echo "  MCP Server:   http://localhost:8000"
    echo "  Health Check: http://localhost:8000/health"
    echo "  Capabilities: http://localhost:8000/capabilities"
    echo "  Frontend:     http://localhost:3800"
    echo "  PostgreSQL:   localhost:5432"
    echo "  Redis:        localhost:6379"
}

cmd_logs() {
    local container="$CONTAINER_NAME"
    local follow_flag=""
    
    # Check for follow flag
    for arg in "$@"; do
        if [[ "$arg" == "-f" || "$arg" == "--follow" ]]; then
            follow_flag="-f"
            break
        fi
    done
    
    log_info "Showing logs for $container $follow_flag"
    
    if check_container_exists "$container"; then
        docker logs $follow_flag "$container"
    else
        log_error "Container $container does not exist"
        exit 1
    fi
}

cmd_shell() {
    log_info "Opening shell in MCP container..."
    
    if check_container_running "$CONTAINER_NAME"; then
        docker exec -it "$CONTAINER_NAME" /bin/bash
    else
        log_error "Container $CONTAINER_NAME is not running"
        exit 1
    fi
}

cmd_health() {
    print_banner
    log_info "Performing health checks..."
    
    local healthy=true
    
    # Check container health
    if check_container_running "$CONTAINER_NAME"; then
        log_success "MCP Server container is running"
        
        # Check HTTP endpoint
        if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
            log_success "MCP Server HTTP endpoint is healthy"
        else
            log_error "MCP Server HTTP endpoint is not responding"
            healthy=false
        fi
        
        # Check database connectivity (if local PostgreSQL)
        if check_container_running "$POSTGRES_CONTAINER"; then
            if docker exec $POSTGRES_CONTAINER pg_isready -U dhafnck_user -d dhafnck_mcp > /dev/null 2>&1; then
                log_success "PostgreSQL database is healthy"
            else
                log_error "PostgreSQL database is not healthy"
                healthy=false
            fi
        fi
        
        # Check Redis
        if check_container_running "$REDIS_CONTAINER"; then
            if docker exec $REDIS_CONTAINER redis-cli ping | grep -q PONG; then
                log_success "Redis cache is healthy"
            else
                log_error "Redis cache is not healthy"
                healthy=false
            fi
        fi
        
    else
        log_error "MCP Server container is not running"
        healthy=false
    fi
    
    echo ""
    if [ "$healthy" = true ]; then
        log_success "All health checks passed!"
        return 0
    else
        log_error "Some health checks failed!"
        return 1
    fi
}

cmd_clean() {
    local mode="${1:-$DEFAULT_MODE}"
    
    log_warning "This will remove all containers and volumes!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Cleaning up Docker environment..."
        
        cd "$PROJECT_ROOT"
        local compose_files
        compose_files=$(get_compose_files "$mode")
        
        # Stop and remove containers
        eval "docker-compose $compose_files down -v --remove-orphans"
        
        # Remove specific volumes
        docker volume rm dhafnck_data dhafnck_logs postgres_data redis_data 2>/dev/null || true
        
        # Remove images (optional)
        read -p "Remove Docker images too? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker rmi dhafnck/mcp-server:latest dhafnck/frontend:latest 2>/dev/null || true
            log_success "Images removed"
        fi
        
        log_success "Cleanup completed"
    else
        log_info "Cleanup cancelled"
    fi
}

cmd_rebuild() {
    local mode="${1:-$DEFAULT_MODE}"
    
    log_info "Rebuilding DhafnckMCP environment..."
    
    # Clean up
    cmd_clean "$mode"
    
    # Wait a moment
    sleep 2
    
    # Start fresh
    cmd_start "$mode"
}

# =============================================================================
# ARGUMENT PARSING
# =============================================================================

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--detached)
                DETACHED=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                print_usage
                exit 0
                ;;
            -f|--follow)
                # This will be handled by cmd_logs
                shift
                ;;
            start|stop|restart|status|logs|shell|health|clean|rebuild)
                COMMAND="$1"
                shift
                ;;
            local|production|dev)
                MODE="$1"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                print_usage
                exit 1
                ;;
        esac
    done
}

# =============================================================================
# MAIN SCRIPT EXECUTION
# =============================================================================

main() {
    # Default values
    COMMAND=""
    MODE="$DEFAULT_MODE"
    
    # Parse arguments
    parse_arguments "$@"
    
    # Validate command
    if [ -z "$COMMAND" ]; then
        log_error "No command specified"
        print_usage
        exit 1
    fi
    
    # Execute command
    case "$COMMAND" in
        start)
            cmd_start "$MODE"
            ;;
        stop)
            cmd_stop "$MODE"
            ;;
        restart)
            cmd_restart "$MODE"
            ;;
        status)
            cmd_status
            ;;
        logs)
            cmd_logs "$@"
            ;;
        shell)
            cmd_shell
            ;;
        health)
            cmd_health
            ;;
        clean)
            cmd_clean "$MODE"
            ;;
        rebuild)
            cmd_rebuild "$MODE"
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            print_usage
            exit 1
            ;;
    esac
}

# Execute main function with all arguments
main "$@"