#!/bin/bash
# docker-menu.sh - agenthub Docker Management Interface
# Updated for streamlined database configurations

set -euo pipefail

# Define colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
RESET='\033[0m'
BOLD='\033[1m'

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="${SCRIPT_DIR}/docker"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

# ALWAYS load .env.dev file at startup for consistency
ENV_DEV_FILE="${PROJECT_ROOT}/.env.dev"
if [[ -f "$ENV_DEV_FILE" ]]; then
    set -a
    source <(grep -v '^#' "$ENV_DEV_FILE" | grep -v '^$' | sed 's/\r$//')
    set +a
    echo -e "${GREEN}✅ Loaded configuration from .env.dev${RESET}"
else
    echo -e "${YELLOW}⚠️ Warning: .env.dev not found, using defaults${RESET}"
fi

# Check and stop conflicting containers on required ports
check_and_free_ports() {
    echo -e "${YELLOW}🔍 Checking for port conflicts...${RESET}"
    
    # Check for containers using backend port
    local backend_containers=$(docker ps -q --filter "publish=${FASTMCP_PORT}" 2>/dev/null)
    if [[ -n "$backend_containers" ]]; then
        echo -e "${YELLOW}⚠️  Stopping containers using port ${FASTMCP_PORT}...${RESET}"
        docker stop $backend_containers
    fi
    
    # Check for containers using frontend port  
    local frontend_containers=$(docker ps -q --filter "publish=${FRONTEND_PORT}" 2>/dev/null)
    if [[ -n "$frontend_containers" ]]; then
        echo -e "${YELLOW}⚠️  Stopping containers using port ${FRONTEND_PORT}...${RESET}"
        docker stop $frontend_containers
    fi
    
    # Clean up stopped containers
    if [[ -n "$backend_containers" ]] || [[ -n "$frontend_containers" ]]; then
        echo -e "${YELLOW}🧹 Cleaning up stopped containers...${RESET}"
        docker container prune -f >/dev/null 2>&1
        echo -e "${GREEN}✅ Ports ${FASTMCP_PORT} and ${FRONTEND_PORT} are now available${RESET}"
    else
        echo -e "${GREEN}✅ Ports are available${RESET}"
    fi
}

# Set Docker build optimization environment variables
set_build_optimization() {
    # Disable slow provenance and SBOM features
    export DOCKER_BUILDKIT_PROVENANCE=false
    export DOCKER_BUILDKIT_SBOM=false  
    export BUILDX_NO_DEFAULT_ATTESTATIONS=true
    
    # Enable BuildKit for better performance
    export DOCKER_BUILDKIT=1
    export COMPOSE_DOCKER_CLI_BUILD=1
    
    echo -e "${GREEN}✅ Build optimization enabled (provenance disabled)${RESET}"
}

# Clean up existing builds and images to save space
clean_existing_builds() {
    echo -e "${YELLOW}🧹 Cleaning up existing builds for fresh rebuild...${RESET}"
    
    # Stop and remove existing containers first
    echo -e "${YELLOW}🛑 Stopping existing agenthub containers...${RESET}"
    docker stop agenthub-backend agenthub-frontend 2>/dev/null || true
    docker rm agenthub-backend agenthub-frontend 2>/dev/null || true
    
    # Remove agenthub project images to force complete rebuild
    local agenthub_images=$(docker images -q --filter "reference=*agenthub*" 2>/dev/null)
    if [[ -n "$agenthub_images" ]]; then
        echo -e "${YELLOW}🗑️  Removing existing agenthub images to ensure fresh build...${RESET}"
        docker rmi $agenthub_images -f >/dev/null 2>&1 || true
    fi
    
    # Remove docker project images from docker-system 
    local docker_images=$(docker images -q --filter "reference=docker-*" 2>/dev/null)
    if [[ -n "$docker_images" ]]; then
        echo -e "${YELLOW}🗑️  Removing existing docker-system images...${RESET}"
        docker rmi $docker_images -f >/dev/null 2>&1 || true
    fi
    
    # Clear Python cache to ensure code changes are picked up
    echo -e "${YELLOW}🐍 Clearing Python cache files...${RESET}"
    find ../agenthub_main -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find ../agenthub_main -type f -name "*.pyc" -delete 2>/dev/null || true
    
    # Clean up dangling images and build cache
    echo -e "${YELLOW}🧽 Cleaning up dangling images and build cache...${RESET}"
    docker image prune -f >/dev/null 2>&1
    docker builder prune -f >/dev/null 2>&1
    
    echo -e "${GREEN}✅ Build cleanup complete - ready for fresh --no-cache builds${RESET}"
}

# ANSI color codes for better UI
readonly CYAN='\033[0;36m'
readonly GREEN='\033[0;32m'
readonly RED='\033[0;31m'
readonly YELLOW='\033[1;33m'
readonly MAGENTA='\033[0;35m'
readonly BOLD='\033[1m'
readonly RESET='\033[0m'

# Validate environment variables
validate_env_variables() {
    local has_errors=false
    local has_warnings=false
    
    # Check required database configuration
    if [[ -z "$DATABASE_TYPE" ]]; then
        echo -e "${RED}❌ ERROR: DATABASE_TYPE is not set${RESET}"
        has_errors=true
    fi
    
    if [[ -z "$DATABASE_HOST" ]]; then
        echo -e "${RED}❌ ERROR: DATABASE_HOST is not set${RESET}"
        has_errors=true
    fi
    
    # Validate port numbers
    if [[ -n "$FASTMCP_PORT" ]] && ! [[ "$FASTMCP_PORT" =~ ^[0-9]+$ ]]; then
        echo -e "${RED}❌ ERROR: FASTMCP_PORT must be a number, got: $FASTMCP_PORT${RESET}"
        has_errors=true
    fi
    
    if [[ -n "$DATABASE_PORT" ]] && ! [[ "$DATABASE_PORT" =~ ^[0-9]+$ ]]; then
        echo -e "${RED}❌ ERROR: DATABASE_PORT must be a number, got: $DATABASE_PORT${RESET}"
        has_errors=true
    fi
    
    if [[ -n "$FRONTEND_PORT" ]] && ! [[ "$FRONTEND_PORT" =~ ^[0-9]+$ ]]; then
        echo -e "${RED}❌ ERROR: FRONTEND_PORT must be a number, got: $FRONTEND_PORT${RESET}"
        has_errors=true
    fi
    
    # Check for port conflicts
    if [[ "$FASTMCP_PORT" == "$FRONTEND_PORT" ]]; then
        echo -e "${RED}❌ ERROR: FASTMCP_PORT and FRONTEND_PORT cannot be the same: $FASTMCP_PORT${RESET}"
        has_errors=true
    fi
    
    # Warn about missing optional but important variables
    if [[ -z "$VITE_API_URL" ]]; then
        echo -e "${YELLOW}⚠️  WARNING: VITE_API_URL is not set (frontend may not connect to backend)${RESET}"
        has_warnings=true
    fi
    
    if [[ -z "$VITE_BACKEND_URL" ]]; then
        echo -e "${YELLOW}⚠️  WARNING: VITE_BACKEND_URL is not set (frontend may not connect to backend)${RESET}"
        has_warnings=true
    fi
    
    # Check if frontend URLs match backend port
    if [[ -n "$VITE_API_URL" ]] && [[ -n "$FASTMCP_PORT" ]]; then
        if ! echo "$VITE_API_URL" | grep -q ":$FASTMCP_PORT"; then
            echo -e "${YELLOW}⚠️  WARNING: VITE_API_URL ($VITE_API_URL) doesn't match FASTMCP_PORT ($FASTMCP_PORT)${RESET}"
            has_warnings=true
        fi
    fi
    
    if [[ "$has_errors" == "true" ]]; then
        echo -e "${RED}❌ Configuration errors detected. Please fix .env.dev file${RESET}"
        return 1
    fi
    
    if [[ "$has_warnings" == "true" ]]; then
        echo -e "${YELLOW}⚠️  Configuration warnings detected. Some features may not work properly${RESET}"
    fi
    
    return 0
}

# Load environment variables from .env.dev file (primary) or .env file (fallback)
load_env_config() {
    local env_dev_file="${PROJECT_ROOT}/.env.dev"
    local env_file="${PROJECT_ROOT}/.env"
    
    # Try .env.dev first (primary development file)
    if [[ -f "$env_dev_file" ]]; then
        # Load .env.dev file, ignoring comments and empty lines
        set -a  # automatically export all variables
        source <(grep -v '^#' "$env_dev_file" | grep -v '^$' | sed 's/\r$//')
        set +a  # stop auto-exporting
        echo -e "${GREEN}✅ Loaded configuration from .env.dev file${RESET}"
        
        # Validate critical variables
        validate_env_variables
        
        # Set defaults for missing variables
        export FASTMCP_PORT=${FASTMCP_PORT:-8000}
        export FRONTEND_PORT=${FRONTEND_PORT:-3800}
        export DATABASE_HOST=${DATABASE_HOST:-localhost}
        export DATABASE_PORT=${DATABASE_PORT:-5432}
        export DATABASE_NAME=${DATABASE_NAME:-agenthub_prod}
        export DATABASE_USER=${DATABASE_USER:-agenthub_user}
        export DATABASE_PASSWORD=${DATABASE_PASSWORD:-ChangeThisSecurePassword2025!}
        export DATABASE_TYPE=${DATABASE_TYPE:-postgresql}
        export AUTH_PROVIDER=${AUTH_PROVIDER:-keycloak}
        export AUTH_ENABLED=${AUTH_ENABLED:-true}
        export EMAIL_VERIFIED_AUTO=${EMAIL_VERIFIED_AUTO:-true}
        
        return 0
    # Try .env as fallback
    elif [[ -f "$env_file" ]]; then
        # Load .env file as fallback
        set -a
        source <(grep -v '^#' "$env_file" | grep -v '^$' | sed 's/\r$//')
        set +a
        echo -e "${GREEN}✅ Loaded configuration from .env file (fallback)${RESET}"
        
        # Set defaults for missing variables
        export FASTMCP_PORT=${FASTMCP_PORT:-8000}
        export FRONTEND_PORT=${FRONTEND_PORT:-3800}
        export DATABASE_HOST=${DATABASE_HOST:-localhost}
        export DATABASE_PORT=${DATABASE_PORT:-5432}
        export DATABASE_NAME=${DATABASE_NAME:-agenthub_prod}
        export DATABASE_USER=${DATABASE_USER:-agenthub_user}
        export DATABASE_PASSWORD=${DATABASE_PASSWORD:-ChangeThisSecurePassword2025!}
        export DATABASE_TYPE=${DATABASE_TYPE:-postgresql}
        export AUTH_PROVIDER=${AUTH_PROVIDER:-keycloak}
        export AUTH_ENABLED=${AUTH_ENABLED:-true}
        export EMAIL_VERIFIED_AUTO=${EMAIL_VERIFIED_AUTO:-true}
        
        return 0
    else
        echo -e "${YELLOW}⚠️  No .env.dev or .env file found${RESET}"
        echo -e "${YELLOW}Using hardcoded default values${RESET}"
        
        # Set hardcoded defaults
        export MCP_PORT=8001
        export FASTMCP_PORT=8000
        export FRONTEND_PORT=3800
        export DATABASE_HOST=localhost
        export DATABASE_PORT=5432
        export DATABASE_NAME=agenthub_prod
        export DATABASE_USER=agenthub_user
        export DATABASE_PASSWORD=ChangeThisSecurePassword2025!
        export DATABASE_TYPE=postgresql
        export AUTH_PROVIDER=keycloak
        export AUTH_ENABLED=true
        
        return 1
    fi
}

# Load environment configuration at startup
load_env_config

# Clear screen and show header
show_header() {
    clear
    echo -e "${CYAN}${BOLD}"
    echo "╔════════════════════════════════════════════════╗"
    echo "║        agenthub Docker Management            ║"
    echo "║           Build System v3.0                   ║"
    echo "╚════════════════════════════════════════════════╝"
    echo -e "${RESET}"
    echo -e "${YELLOW}Backend: Port ${FASTMCP_PORT} | Frontend: Port ${FRONTEND_PORT}${RESET}"
    echo -e "${YELLOW}Database: ${DATABASE_TYPE} (${DATABASE_HOST}:${DATABASE_PORT})${RESET}"
    echo -e "${YELLOW}Auth: ${AUTH_PROVIDER} (enabled: ${AUTH_ENABLED})${RESET}"
    echo -e "${YELLOW}All builds use --no-cache (provenance optimized)${RESET}"
    echo ""
}

# Show main menu
show_main_menu() {
    echo -e "${MAGENTA}${BOLD}Build Configurations${RESET}"
    echo "────────────────────────────────────────────────"
    echo "  1) 🚀 Backend + Frontend Only (requires DB running)"
    echo "  2) ☁️  Supabase Cloud (No Redis)"
    echo "  3) ☁️🔴 Supabase Cloud + Redis (Full Stack)"
    echo ""
    echo -e "${GREEN}${BOLD}Database Management${RESET}"
    echo "────────────────────────────────────────────────"
    echo "  B) 🗄️  Database Only (PostgreSQL standalone)"
    echo "  C) 🎛️  pgAdmin UI Only (requires DB running)"
    echo ""
    echo -e "${CYAN}${BOLD}💻 Development Mode (Non-Docker)${RESET}"
    echo "────────────────────────────────────────────────"
    echo "  D) 🚀 Start Dev Mode (Backend + Frontend locally)"
    echo "  R) 🔄 Restart Dev Mode (Apply new changes)"
    echo ""
    echo -e "${GREEN}${BOLD}⚡ Performance Mode (Low-Resource PC)${RESET}"
    echo "────────────────────────────────────────────────"
    echo "  P) 🚀 Start Optimized Mode (Uses less RAM/CPU)"
    echo "  M) 📊 Monitor Performance (Live stats)"
    echo ""
    echo -e "${MAGENTA}${BOLD}Management Options${RESET}"
    echo "────────────────────────────────────────────────"
    echo "  4) 📊 Show Status"
    echo "  5) 🛑 Stop All Services"
    echo "  6) 📜 View Logs"
    echo "  7) 🗄️  Database Shell"
    echo "  8) 🧹 Clean Docker System"
    echo "  9) 🔄 Force Complete Rebuild (removes all images)"
    echo "  0) 🚪 Exit"
    echo "────────────────────────────────────────────────"
}

# Build and start PostgreSQL Local configuration with Development Dockerfiles
start_postgresql_local() {
    echo -e "${GREEN}🚀 Building and Starting Backend + Frontend Only...${RESET}"
    echo -e "${YELLOW}Note: PostgreSQL should be running separately (use option B first)${RESET}"
    echo -e "${CYAN}Using credentials from .env.dev${RESET}"
    
    cd "$DOCKER_DIR"

    set_build_optimization
    check_and_free_ports

    # Check if PostgreSQL is running
    if ! docker ps | grep -q agenthub-postgres; then
        echo -e "${RED}⚠️  PostgreSQL is not running!${RESET}"
        echo -e "${YELLOW}Please run option B first to start the database.${RESET}"
        return 1
    fi

    # Stop any existing backend/frontend containers only
    echo -e "${YELLOW}Stopping existing backend/frontend containers...${RESET}"
    docker stop agenthub-backend agenthub-frontend 2>/dev/null || true
    docker rm agenthub-backend agenthub-frontend 2>/dev/null || true

    # Create network if it doesn't exist
    docker network create agenthub-network 2>/dev/null || true

    # Use backend-frontend only docker-compose file
    echo -e "${CYAN}Using docker-compose.backend-frontend.yml for backend and frontend only...${RESET}"

    # Validate environment before building
    if ! validate_env_variables; then
        echo -e "${RED}❌ Please fix environment configuration errors before continuing${RESET}"
        return 1
    fi

    echo -e "${CYAN}Building backend and frontend containers in parallel...${RESET}"
    echo -e "${YELLOW}This will be faster as both containers build simultaneously${RESET}"

    # Always use .env.dev for consistency and set CONTAINER_ENV=docker
    CONTAINER_ENV=docker docker-compose --env-file "${ENV_DEV_FILE:-../../.env.dev}" -f docker-compose.backend-frontend.yml build --parallel --no-cache || {
        echo -e "${RED}❌ Build failed. Check error messages above${RESET}"
        return 1
    }

    echo -e "${CYAN}Starting backend and frontend services...${RESET}"
    CONTAINER_ENV=docker docker-compose --env-file "${ENV_DEV_FILE:-../../.env.dev}" -f docker-compose.backend-frontend.yml up -d || {
        echo -e "${RED}❌ Failed to start services. Check error messages above${RESET}"
        return 1
    }
    
    echo -e "${GREEN}✅ Development services started!${RESET}"
    echo "Backend: http://localhost:${FASTMCP_PORT:-8000}"
    echo "Frontend: http://localhost:${FRONTEND_PORT:-3800}"
    echo "PostgreSQL: localhost:${DATABASE_PORT:-5432}"
    echo -e "${YELLOW}📝 Note: Rebuild containers to see code changes${RESET}"
    
    # Show running containers
    echo -e "\n${CYAN}Running containers:${RESET}"
    docker ps --filter "name=agenthub" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}

# Start Database Only (Option B - PostgreSQL standalone)
start_database_only() {
    echo -e "${GREEN}🗄️  Starting PostgreSQL Database Only (Standalone)...${RESET}"
    echo -e "${CYAN}Using credentials from .env.dev:${RESET}"
    echo "  Database: ${DATABASE_NAME}"
    echo "  User: ${DATABASE_USER}"
    echo "  Port: ${DATABASE_PORT}"

    # Ensure network exists
    docker network create agenthub-network 2>/dev/null || true

    # Stop any existing postgres container
    echo -e "${YELLOW}Stopping existing database container if any...${RESET}"
    docker stop agenthub-postgres 2>/dev/null || true
    docker rm agenthub-postgres 2>/dev/null || true

    # Change to docker directory
    cd "$DOCKER_DIR"

    # Start PostgreSQL only (no build required)
    echo -e "${CYAN}Starting PostgreSQL database...${RESET}"
    CONTAINER_ENV=docker docker-compose --env-file "${ENV_DEV_FILE:-../../.env.dev}" -f docker-compose.db-only.yml up -d postgres

    # Wait for database to be ready
    echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${RESET}"
    for i in {1..30}; do
        if docker exec agenthub-postgres pg_isready -U ${DATABASE_USER:-agenthub_user} >/dev/null 2>&1; then
            echo -e "${GREEN}✅ PostgreSQL is ready!${RESET}"
            break
        fi
        echo -n "."
        sleep 1
    done

    echo ""
    echo -e "${GREEN}✅ Database started successfully!${RESET}"
    echo "PostgreSQL: localhost:${DATABASE_PORT}"
    echo "Database: ${DATABASE_NAME}"
    echo "User: ${DATABASE_USER}"
    echo ""
    echo -e "${YELLOW}To connect: psql -h localhost -p ${DATABASE_PORT} -U ${DATABASE_USER} -d ${DATABASE_NAME}${RESET}"
    echo -e "${CYAN}Using credentials from .env.dev${RESET}"
}

# Start pgAdmin UI Only (Option C)
start_postgresql_with_ui() {
    echo -e "${GREEN}🎛️  Starting pgAdmin UI Only...${RESET}"
    echo -e "${YELLOW}Note: PostgreSQL must be running (use option B first)${RESET}"

    # Check if PostgreSQL is running
    if ! docker ps | grep -q agenthub-postgres; then
        echo -e "${RED}⚠️  PostgreSQL is not running!${RESET}"
        echo -e "${YELLOW}Please run option B first to start the database.${RESET}"
        return 1
    fi

    # Check pgAdmin port
    local pgadmin_port=5050
    local pgadmin_containers=$(docker ps -q --filter "publish=${pgadmin_port}" 2>/dev/null)
    if [[ -n "$pgadmin_containers" ]]; then
        echo -e "${YELLOW}⚠️  Stopping containers using port ${pgadmin_port} (pgAdmin)...${RESET}"
        docker stop $pgadmin_containers
    fi
    
    # Stop any existing pgAdmin container
    echo -e "${YELLOW}Stopping existing pgAdmin container...${RESET}"
    docker stop agenthub-pgadmin 2>/dev/null || true
    docker rm agenthub-pgadmin 2>/dev/null || true

    # Network should already exist from PostgreSQL
    docker network create agenthub-network 2>/dev/null || true

    # Change to docker directory
    cd "$DOCKER_DIR"

    # Start pgAdmin only (with profile to include it)
    echo -e "${CYAN}Starting pgAdmin UI...${RESET}"
    CONTAINER_ENV=docker docker-compose -f docker-compose.db-only.yml --profile with-pgadmin up -d pgadmin
    
    echo -e "${GREEN}✅ pgAdmin UI started!${RESET}"
    echo ""
    echo -e "${CYAN}${BOLD}🎛️  pgAdmin UI: http://localhost:5050${RESET}"
    echo -e "${YELLOW}Login Credentials:${RESET}"
    echo "  Email: admin@example.com"
    echo "  Password: admin123"
    echo ""
    echo -e "${MAGENTA}📋 To Connect PostgreSQL in pgAdmin:${RESET}"
    echo "  1. Add New Server"
    echo "  2. Use connection details:"
    echo "     Host: agenthub-postgres"
    echo "     Port: 5432"
    echo "     Database: ${DATABASE_NAME:-agenthub}"
    echo "     Username: ${DATABASE_USER:-agenthub_user}"
    echo "     Password: ${DATABASE_PASSWORD:-dev_password}"
}

# Build and start Supabase Cloud configuration
start_supabase_cloud() {
    echo -e "${GREEN}☁️  Starting Supabase Cloud configuration...${RESET}"
    cd "$DOCKER_DIR"
    
    set_build_optimization
    
    # Verify environment setup
    echo -e "${CYAN}📋 Verifying Supabase configuration...${RESET}"
    
    # Check if env file exists and show Supabase vars
    if [[ -f "../../.env" ]]; then
        echo -e "${GREEN}✓ .env file found${RESET}"
        
        # Check for required Supabase variables
        local required_vars=("SUPABASE_URL" "SUPABASE_ANON_KEY" "DATABASE_TYPE")
        local missing_vars=()
        
        for var in "${required_vars[@]}"; do
            if ! grep -q "^${var}=" ../../.env; then
                missing_vars+=("$var")
            fi
        done
        
        if [[ ${#missing_vars[@]} -gt 0 ]]; then
            echo -e "${RED}❌ Missing required environment variables:${RESET}"
            for var in "${missing_vars[@]}"; do
                echo -e "${RED}   - $var${RESET}"
            done
            echo -e "${YELLOW}Please add these to your .env file and try again.${RESET}"
            return 1
        fi
        
        # Verify DATABASE_TYPE is set to supabase
        if ! grep -q "^DATABASE_TYPE=supabase" ../../.env; then
            echo -e "${YELLOW}⚠️  DATABASE_TYPE is not set to 'supabase'. Setting it now...${RESET}"
            sed -i 's/^DATABASE_TYPE=.*/DATABASE_TYPE=supabase/' ../../.env 2>/dev/null || \
            echo "DATABASE_TYPE=supabase" >> ../../.env
        fi
        
        echo -e "${GREEN}✓ Supabase configuration verified${RESET}"
        echo -e "${CYAN}Found Supabase variables:${RESET}"
        grep "^SUPABASE_" ../../.env | sed 's/=.*/=<configured>/' | head -5
    else
        echo -e "${RED}❌ .env file NOT found at ../../.env${RESET}"
        echo -e "${YELLOW}Please create .env file with Supabase credentials${RESET}"
        return 1
    fi
    
    check_and_free_ports
    clean_existing_builds
    
    echo -e "${CYAN}🔨 Building with --no-cache (this ensures latest code changes)...${RESET}"
    DATABASE_TYPE=supabase CONTAINER_ENV=docker docker-compose --env-file ../../.env.dev -f docker-compose.yml build --no-cache

    echo -e "${CYAN}🚀 Starting services...${RESET}"
    DATABASE_TYPE=supabase CONTAINER_ENV=docker docker-compose --env-file ../../.env.dev -f docker-compose.yml up -d
    
    # Wait for services to be ready
    echo -e "${YELLOW}⏳ Waiting for services to start (10 seconds)...${RESET}"
    sleep 10
    
    # Health check
    echo -e "${CYAN}🏥 Checking service health...${RESET}"
    if curl -s "http://localhost:${FASTMCP_PORT}/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is healthy${RESET}"
    else
        echo -e "${YELLOW}⚠️  Backend may still be starting up${RESET}"
    fi
    
    echo -e "${GREEN}✅ Services started!${RESET}"
    echo "Backend: http://localhost:${FASTMCP_PORT}"
    echo "Frontend: http://localhost:${FRONTEND_PORT}"
    echo "Database: Supabase Cloud (remote)"
    echo ""
    echo -e "${CYAN}💡 Tips:${RESET}"
    echo "  - Your data is stored in Supabase Cloud, not locally"
    echo "  - Check logs: docker logs agenthub-backend --tail 50"
    echo "  - Verify connection: docker exec agenthub-backend env | grep SUPABASE"
    
    show_service_status "docker-compose.yml"
}


# Build and start Redis + Supabase Cloud configuration
start_redis_supabase() {
    echo -e "${GREEN}🔴☁️  Starting Redis + Supabase Cloud configuration...${RESET}"
    cd "$DOCKER_DIR"
    
    set_build_optimization
    check_and_free_ports
    clean_existing_builds
    
    echo "Building with --no-cache..."
    DATABASE_TYPE=supabase ENABLE_REDIS=true CONTAINER_ENV=docker docker-compose --env-file ../../.env.dev -f docker-compose.yml --profile redis build --no-cache

    echo "Starting services..."
    DATABASE_TYPE=supabase ENABLE_REDIS=true CONTAINER_ENV=docker docker-compose --env-file ../../.env.dev -f docker-compose.yml --profile redis up -d
    
    echo -e "${GREEN}✅ Services started!${RESET}"
    echo "Backend: http://localhost:${FASTMCP_PORT}"
    echo "Frontend: http://localhost:${FRONTEND_PORT}"
    echo "Database: Supabase Cloud"
    echo "Redis: localhost:6379"
    
    show_service_status "docker-compose.yml"
}

# Show service status
show_service_status() {
    local compose_file=${1:-""}
    echo ""
    echo -e "${CYAN}Service Status:${RESET}"
    if [[ -n "$compose_file" ]]; then
        CONTAINER_ENV=docker docker-compose --env-file ../../.env.dev -f "$compose_file" ps
    else
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    fi
}

# Stop all services
stop_all_services() {
    echo -e "${YELLOW}🛑 Stopping all services...${RESET}"
    
    # Check if dev mode services are running
    if [[ -f "../dev-backend.pid" ]] || [[ -f "../dev-frontend.pid" ]]; then
        echo "Detected development mode services running..."
        stop_dev_mode
    fi
    
    # Stop Docker services
    cd "$DOCKER_DIR"
    echo "Stopping Docker services..."
    CONTAINER_ENV=docker docker-compose --env-file ../../.env.dev -f docker-compose.yml down 2>/dev/null || true
    
    echo -e "${GREEN}✅ All services stopped${RESET}"
}

# View logs
view_logs() {
    echo -e "${CYAN}📜 Available services for logs:${RESET}"
    echo "1) Backend"
    echo "2) Frontend" 
    echo "3) PostgreSQL"
    echo "4) Redis"
    echo "5) All services"
    
    read -p "Select service: " log_choice
    
    case $log_choice in
        1) docker logs -f agenthub-backend 2>/dev/null || echo "Backend container not found" ;;
        2) docker logs -f agenthub-frontend 2>/dev/null || echo "Frontend container not found" ;;
        3) docker logs -f agenthub-postgres 2>/dev/null || echo "PostgreSQL container not found" ;;
        4) docker logs -f agenthub-redis 2>/dev/null || echo "Redis container not found" ;;
        5) 
            echo "Showing logs for all services..."
            docker logs agenthub-backend --tail=50 2>/dev/null || true
            docker logs agenthub-frontend --tail=50 2>/dev/null || true
            docker logs agenthub-postgres --tail=50 2>/dev/null || true
            docker logs agenthub-redis --tail=50 2>/dev/null || true
            ;;
        *) echo "Invalid option" ;;
    esac
}

# Database shell access
database_shell() {
    echo -e "${CYAN}🗄️  Database Shell Options:${RESET}"
    echo "1) PostgreSQL (if running locally)"
    echo "2) Redis (if running locally)"
    
    read -p "Select database: " db_choice
    
    case $db_choice in
        1) 
            echo "Connecting to PostgreSQL..."
            docker exec -it agenthub-postgres psql -U postgres -d agenthub 2>/dev/null || \
            echo "PostgreSQL container not found or not accessible"
            ;;
        2) 
            echo "Connecting to Redis..."
            docker exec -it agenthub-redis redis-cli 2>/dev/null || \
            echo "Redis container not found or not accessible"
            ;;
        *) echo "Invalid option" ;;
    esac
}

# Force complete rebuild - removes everything and rebuilds from scratch
force_complete_rebuild() {
    echo -e "${RED}${BOLD}🔄 FORCE COMPLETE REBUILD${RESET}"
    echo -e "${YELLOW}This will:${RESET}"
    echo "  - Stop and remove ALL agenthub containers"
    echo "  - Remove ALL agenthub Docker images"
    echo "  - Clear all Python cache files"
    echo "  - Remove Docker build cache"
    echo "  - Force rebuild everything from scratch"
    echo ""
    read -p "Are you sure? This will take several minutes. (y/N): " confirm
    
    if [[ $confirm == "y" || $confirm == "Y" ]]; then
        echo -e "${YELLOW}🛑 Stopping all containers...${RESET}"
        docker stop $(docker ps -aq --filter "name=agenthub") 2>/dev/null || true
        
        echo -e "${YELLOW}🗑️  Removing all containers...${RESET}"
        docker rm $(docker ps -aq --filter "name=agenthub") 2>/dev/null || true
        
        echo -e "${YELLOW}🗑️  Removing all agenthub images...${RESET}"
        docker rmi $(docker images -q --filter "reference=*agenthub*") -f 2>/dev/null || true
        docker rmi $(docker images -q --filter "reference=docker-*") -f 2>/dev/null || true
        
        echo -e "${YELLOW}🐍 Clearing all Python cache...${RESET}"
        find ../agenthub_main -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find ../agenthub_main -type f -name "*.pyc" -delete 2>/dev/null || true
        
        echo -e "${YELLOW}🧹 Pruning Docker system...${RESET}"
        docker system prune -af --volumes 2>/dev/null || true
        docker builder prune -af 2>/dev/null || true
        
        echo -e "${GREEN}✅ Complete cleanup done!${RESET}"
        echo ""
        echo -e "${CYAN}Now select a configuration to rebuild:${RESET}"
        echo "1) 🐘 PostgreSQL Local (Backend + Frontend)"
        echo "2) ☁️  Supabase Cloud (No Redis)"
        echo "3) ☁️🔴 Supabase Cloud + Redis (Full Stack)"
        echo "0) Cancel"
        
        read -p "Select configuration: " rebuild_choice
        
        case $rebuild_choice in
            1) start_postgresql_local ;;
            2) start_supabase_cloud ;;
            3) start_redis_supabase ;;
            0) echo "Cancelled" ;;
            *) echo "Invalid option" ;;
        esac
    else
        echo -e "${YELLOW}Cancelled${RESET}"
    fi
}

# Start Optimized Mode for low-resource PCs
start_optimized_mode() {
    echo -e "${GREEN}${BOLD}🚀 Starting Optimized Mode for Low-Resource PCs${RESET}"
    echo -e "${YELLOW}This mode reduces:${RESET}"
    echo "  • Memory usage by ~60%"
    echo "  • CPU usage by ~40%"
    echo "  • Docker image sizes"
    echo ""
    
    # Check system resources
    echo -e "${CYAN}🔍 Checking system resources...${RESET}"
    if command -v free &> /dev/null; then
        MEM_TOTAL=$(free -m | awk 'NR==2{print $2}')
        MEM_AVAILABLE=$(free -m | awk 'NR==2{print $7}')
        echo -e "  Total Memory: ${MEM_TOTAL}MB"
        echo -e "  Available Memory: ${MEM_AVAILABLE}MB"
        
        if [ "$MEM_AVAILABLE" -lt 2048 ]; then
            echo -e "${YELLOW}⚠️  Low memory detected. Using minimal configuration...${RESET}"
            USE_MINIMAL=true
        fi
    fi
    
    cd "$DOCKER_DIR"
    
    set_build_optimization
    check_and_free_ports
    
    # Check if optimized compose file exists
    if [[ ! -f "docker-compose.optimized.yml" ]]; then
        echo -e "${YELLOW}Creating optimized configuration...${RESET}"
        create_optimized_compose
    fi
    
    echo -e "${CYAN}🔨 Building optimized images...${RESET}"
    
    # Build with optimized settings
    CONTAINER_ENV=docker docker-compose -f docker-compose.optimized.yml build \
        --parallel \
        --compress || {
            echo -e "${RED}Build failed, falling back to standard build${RESET}"
            CONTAINER_ENV=docker docker-compose -f docker-compose.optimized.yml build
        }
    
    echo -e "${CYAN}🚀 Starting optimized services...${RESET}"
    
    # Start with resource limits
    if [ "$USE_MINIMAL" = "true" ]; then
        # Start only essential services for very low memory
        CONTAINER_ENV=docker docker-compose -f docker-compose.optimized.yml up -d postgres backend
        echo -e "${YELLOW}Started minimal services only (no frontend/redis)${RESET}"
    else
        CONTAINER_ENV=docker docker-compose -f docker-compose.optimized.yml up -d
    fi
    
    # Wait for services
    echo -e "${YELLOW}⏳ Waiting for services to start...${RESET}"
    local max_wait=30
    local waited=0
    while [ $waited -lt $max_wait ]; do
        if curl -f "http://localhost:${FASTMCP_PORT}/health" &>/dev/null; then
            echo -e "${GREEN}✅ Backend is healthy${RESET}"
            break
        fi
        sleep 2
        waited=$((waited + 2))
        echo -n "."
    done
    echo ""
    
    echo -e "${GREEN}✅ Optimized services started!${RESET}"
    echo "Backend: http://localhost:${FASTMCP_PORT}"
    [ "$USE_MINIMAL" != "true" ] && echo "Frontend: http://localhost:${FRONTEND_PORT}"
    echo ""
    echo -e "${CYAN}Resource Usage:${RESET}"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
    echo ""
    echo -e "${YELLOW}💡 Tips for better performance:${RESET}"
    echo "  • Close unnecessary browser tabs"
    echo "  • Disable other Docker containers"
    echo "  • Use 'M' option to monitor resource usage"
}

# Create pgAdmin docker-compose overlay
create_pgadmin_compose() {
    cat > ../docker-compose.pgadmin.yml << 'EOF'
# pgAdmin overlay for PostgreSQL management

services:
  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: agenthub-pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@agenthub.local
      PGADMIN_DEFAULT_PASSWORD: admin123
      PGADMIN_CONFIG_SERVER_MODE: 'False'
      PGADMIN_CONFIG_MASTER_PASSWORD_REQUIRED: 'False'
    ports:
      - "5050:80"
    volumes:
      - pgadmin-data:/var/lib/pgadmin
    networks:
      - default
    restart: unless-stopped
    profiles:
      - postgresql

volumes:
  pgadmin-data:
    driver: local
EOF
    echo -e "${GREEN}✅ Created docker-compose.pgadmin.yml${RESET}"
}

# Create optimized docker-compose file
create_optimized_compose() {
    cat > docker-compose.optimized.yml << 'EOF'
# Auto-generated optimized configuration for low-resource PCs
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: agenthub-postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_ROOT_PASSWORD:-postgres}
      POSTGRES_DB: postgres
      POSTGRES_SHARED_BUFFERS: 128MB
      POSTGRES_WORK_MEM: 4MB
      POSTGRES_MAX_CONNECTIONS: 20
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d:ro
    ports:
      - "${DATABASE_PORT:-5432}:5432"
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 30s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  backend:
    build:
      context: ../..
      dockerfile: agenthub_main/docker/Dockerfile
      args:
        - ENV=production
    container_name: agenthub-backend
    environment:
      - DATABASE_TYPE=postgresql
      - DATABASE_URL=postgresql://agenthub_user:dev_password@postgres:5432/agenthub
      - ENV=production
      - APP_DEBUG=false
      - APP_LOG_LEVEL=WARNING
      - PYTHONOPTIMIZE=1
      - WEB_CONCURRENCY=2
    volumes:
      - backend-data:/app/data
    ports:
      - "${FASTMCP_PORT:-8000}:8000"
    depends_on:
      postgres:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '1.0'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 60s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  frontend:
    build:
      context: ../..
      dockerfile: docker-system/docker/frontend.Dockerfile
      args:
        - NODE_ENV=production
    container_name: agenthub-frontend
    environment:
      - NODE_ENV=production
      - VITE_API_URL=http://localhost:${FASTMCP_PORT:-8000}
    volumes:
      - frontend-static:/usr/share/nginx/html:ro
    ports:
      - "${FRONTEND_PORT:-3800}:80"
    depends_on:
      - backend
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.5'
    restart: unless-stopped

volumes:
  postgres-data:
  backend-data:
  frontend-static:

networks:
  default:
    name: agenthub-network
EOF
    echo -e "${GREEN}✅ Created optimized docker-compose.yml${RESET}"
}

# Monitor performance
monitor_performance() {
    echo -e "${CYAN}${BOLD}📊 Performance Monitor${RESET}"
    echo -e "${YELLOW}Press Ctrl+C to stop monitoring${RESET}"
    echo ""
    
    # Check if any containers are running
    if [ -z "$(docker ps -q)" ]; then
        echo -e "${RED}No containers are running!${RESET}"
        return
    fi
    
    # Continuous monitoring
    while true; do
        clear
        echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════${RESET}"
        echo -e "${CYAN}${BOLD}   agenthub Performance Monitor - $(date +%H:%M:%S)${RESET}"
        echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════${RESET}"
        echo ""
        
        # Show container stats
        echo -e "${GREEN}Container Resources:${RESET}"
        docker stats --no-stream --format "table {{.Container}}\t{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}"
        
        echo ""
        echo -e "${GREEN}Container Status:${RESET}"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Size}}"
        
        # Show system resources if available
        if command -v free &> /dev/null; then
            echo ""
            echo -e "${GREEN}System Memory:${RESET}"
            free -h | grep -E "^(Mem|Swap)"
        fi
        
        if command -v df &> /dev/null; then
            echo ""
            echo -e "${GREEN}Docker Disk Usage:${RESET}"
            df -h | grep -E "(^Filesystem|/var/lib/docker)"
        fi
        
        echo ""
        echo -e "${YELLOW}Refreshing in 3 seconds... (Ctrl+C to stop)${RESET}"
        sleep 3
    done
}

# Start Development Mode (Non-Docker)
start_dev_mode() {
    echo -e "${CYAN}${BOLD}💻 Starting Development Mode (Non-Docker)${RESET}"
    echo -e "${YELLOW}This will start:${RESET}"
    echo "  • Backend: Python FastAPI server on port 8000"
    echo "  • Frontend: React dev server on port 3800"
    echo ""
    
    # Check prerequisites
    echo -e "${CYAN}🔍 Checking prerequisites...${RESET}"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python 3 is not installed${RESET}"
        return 1
    fi
    echo -e "${GREEN}✅ Python 3 found: $(python3 --version)${RESET}"
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        echo -e "${RED}❌ Node.js is not installed${RESET}"
        return 1
    fi
    echo -e "${GREEN}✅ Node.js found: $(node --version)${RESET}"
    
    # Check npm
    if ! command -v npm &> /dev/null; then
        echo -e "${RED}❌ npm is not installed${RESET}"
        return 1
    fi
    echo -e "${GREEN}✅ npm found: $(npm --version)${RESET}"
    
    # Check for .env.dev or .env file
    if [[ -f "${PROJECT_ROOT}/.env.dev" ]]; then
        echo -e "${GREEN}✅ .env.dev file found${RESET}"
        # Load .env.dev for development mode
        set -a
        source "${PROJECT_ROOT}/.env.dev"
        set +a
    elif [[ -f "${PROJECT_ROOT}/.env" ]]; then
        echo -e "${GREEN}✅ .env file found (fallback)${RESET}"
        # Load .env as fallback
        set -a
        source "${PROJECT_ROOT}/.env"
        set +a
    else
        echo -e "${RED}❌ No .env.dev or .env file found at project root${RESET}"
        echo -e "${YELLOW}Please create .env.dev file with database configuration${RESET}"
        return 1
    fi
    
    # Kill any existing processes on ports
    echo -e "${YELLOW}🔍 Checking for processes on ports ${FASTMCP_PORT} and ${FRONTEND_PORT}...${RESET}"
    if lsof -Pi :${FASTMCP_PORT} -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Port ${FASTMCP_PORT} is in use. Killing process...${RESET}"
        kill -9 $(lsof -Pi :${FASTMCP_PORT} -sTCP:LISTEN -t) 2>/dev/null || true
    fi
    if lsof -Pi :${FRONTEND_PORT} -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Port ${FRONTEND_PORT} is in use. Killing process...${RESET}"
        kill -9 $(lsof -Pi :${FRONTEND_PORT} -sTCP:LISTEN -t) 2>/dev/null || true
    fi
    echo -e "${GREEN}✅ Ports are available${RESET}"
    
    # Start Backend
    echo ""
    echo -e "${CYAN}🚀 Starting Backend Server...${RESET}"
    echo -e "${YELLOW}Installing Python dependencies...${RESET}"
    
    # Get to the backend directory
    cd "${PROJECT_ROOT}/agenthub_main"
    
    # Check if uv is available (preferred)
    if command -v uv &> /dev/null; then
        echo -e "${GREEN}✅ Using uv for dependency management${RESET}"
        
        # Install dependencies with uv
        if [[ ! -d ".venv" ]]; then
            echo "Creating Python virtual environment with uv..."
            uv venv
        fi
        
        echo "Installing dependencies with uv..."
        uv pip install -e . 2>/dev/null || {
            echo -e "${YELLOW}Installing dependencies (this may take a moment)...${RESET}"
            uv pip install -e .
        }
        
        # Activate uv virtual environment
        source .venv/bin/activate
        export VIRTUAL_ENV="${PROJECT_ROOT}/agenthub_main/.venv"
    else
        # Fallback to regular pip
        echo -e "${YELLOW}uv not found, using pip${RESET}"
        
        # Create virtual environment if it doesn't exist
        if [[ ! -d "venv" ]]; then
            echo "Creating Python virtual environment..."
            python3 -m venv venv
        fi
        
        # Activate virtual environment and install dependencies
        source venv/bin/activate
        
        # Install from pyproject.toml
        pip install -q -e . 2>/dev/null || {
            echo -e "${YELLOW}Installing dependencies (this may take a moment)...${RESET}"
            pip install -e .
        }
    fi
    
    # Create logs directory if it doesn't exist
    mkdir -p "${PROJECT_ROOT}/logs"
    
    # Start backend in background with hot reload
    echo -e "${GREEN}Starting FastAPI backend with hot reload...${RESET}"
    # Use Supabase database for development to access existing projects
    export DATABASE_TYPE=supabase
    export ENV=development
    export APP_DEBUG=true
    export PYTHONDONTWRITEBYTECODE=1
    export PYTHONPATH="${PWD}/src:${PYTHONPATH:-}"
    # Enable MVP mode for authentication bypass
    export AGENTHUB_MVP_MODE=true
    # Ensure we're not in test mode
    unset PYTEST_CURRENT_TEST
    unset TEST_MODE

    # Load environment variables from .env.dev
    if [[ -f "${PROJECT_ROOT}/.env.dev" ]]; then
        echo -e "${YELLOW}📄 Loading environment from .env.dev...${RESET}"
        # Export all variables from .env.dev
        set -a
        source "${PROJECT_ROOT}/.env.dev"
        set +a
        echo -e "${GREEN}✅ Environment loaded from .env.dev${RESET}"
        echo "  DATABASE_TYPE: ${DATABASE_TYPE:-NOT SET}"
        echo "  DATABASE_HOST: ${DATABASE_HOST:-NOT SET}"
        echo "  DATABASE_NAME: ${DATABASE_NAME:-NOT SET}"
    else
        echo -e "${RED}⚠️ Warning: .env.dev not found${RESET}"
    fi

    # Run the same entry point as Docker for consistency
    echo -e "${CYAN}Using MCP entry point (same as Docker)...${RESET}"
    cd src
    # Use the activated virtual environment's Python
    if [[ -f "${PROJECT_ROOT}/agenthub_main/.venv/bin/python" ]]; then
        echo -e "${GREEN}Using virtual environment Python${RESET}"
        nohup "${PROJECT_ROOT}/agenthub_main/.venv/bin/python" -m fastmcp.server.mcp_entry_point > "${PROJECT_ROOT}/logs/backend.log" 2>&1 &
    else
        echo -e "${YELLOW}Using system Python${RESET}"
        nohup python -m fastmcp.server.mcp_entry_point > "${PROJECT_ROOT}/logs/backend.log" 2>&1 &
    fi
    BACKEND_PID=$!
    echo "Backend PID: $BACKEND_PID (with dual auth support)"
    cd ..
    
    # Start Frontend
    echo ""
    echo -e "${CYAN}🚀 Starting Frontend Server...${RESET}"
    
    # Get to the frontend directory
    cd "${PROJECT_ROOT}/agenthub-frontend"
    
    # Install frontend dependencies if needed
    if [[ ! -d "node_modules" ]]; then
        echo -e "${YELLOW}Installing frontend dependencies...${RESET}"
        npm install
    fi
    
    # Start frontend in background with hot reload (Vite has HMR by default)
    echo -e "${GREEN}Starting React development server with hot reload...${RESET}"
    export VITE_API_URL="http://localhost:${FASTMCP_PORT}"
    export CHOKIDAR_USEPOLLING=true
    export WATCHPACK_POLLING=true
    nohup npm start > "${PROJECT_ROOT}/logs/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    echo "Frontend PID: $FRONTEND_PID (with HMR enabled)"
    
    # Save PIDs to file for later stopping
    echo "$BACKEND_PID" > "${PROJECT_ROOT}/dev-backend.pid"
    echo "$FRONTEND_PID" > "${PROJECT_ROOT}/dev-frontend.pid"
    
    # Wait for services to start
    echo ""
    echo -e "${YELLOW}⏳ Waiting for services to start...${RESET}"
    sleep 5
    
    # Check if services are running
    echo -e "${CYAN}🏥 Checking service health...${RESET}"
    
    if kill -0 $BACKEND_PID 2>/dev/null; then
        echo -e "${GREEN}✅ Backend is running (PID: $BACKEND_PID)${RESET}"
    else
        echo -e "${RED}❌ Backend failed to start. Check backend.log for errors${RESET}"
    fi
    
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        echo -e "${GREEN}✅ Frontend is running (PID: $FRONTEND_PID)${RESET}"
    else
        echo -e "${RED}❌ Frontend failed to start. Check frontend.log for errors${RESET}"
    fi
    
    # Try health check
    if curl -s "http://localhost:${FASTMCP_PORT}/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend API is healthy${RESET}"
    else
        echo -e "${YELLOW}⚠️  Backend API not responding yet (may still be starting)${RESET}"
    fi
    
    echo ""
    echo -e "${GREEN}✅ Development servers started!${RESET}"
    echo "Backend: http://localhost:${FASTMCP_PORT}"
    echo "Frontend: http://localhost:${FRONTEND_PORT}"
    echo "Database: SQLite (./agenthub_dev.db)"
    echo ""
    echo -e "${CYAN}🔥 Hot Reload Enabled:${RESET}"
    echo "  • Backend: Auto-reloads on Python changes"
    echo "  • Frontend: HMR (Hot Module Replacement) active"
    echo ""
    echo -e "${CYAN}📝 Logs:${RESET}"
    echo "  Backend log: tail -f logs/backend.log"
    echo "  Frontend log: tail -f logs/frontend.log"
    echo ""
    echo -e "${YELLOW}💡 Quick Commands:${RESET}"
    echo "  Stop: ./docker-menu.sh stop-dev"
    echo "  Restart: ./docker-menu.sh restart-dev (or option R)"
    echo "  Start: ./docker-menu.sh start-dev"
    
    # Return to script directory
    cd "${SCRIPT_DIR}"
}

# Stop Development Mode services
stop_dev_mode() {
    echo -e "${YELLOW}🛑 Stopping Development Mode services...${RESET}"
    
    # Stop backend
    if [[ -f "${PROJECT_ROOT}/dev-backend.pid" ]]; then
        BACKEND_PID=$(cat "${PROJECT_ROOT}/dev-backend.pid")
        if kill -0 $BACKEND_PID 2>/dev/null; then
            echo "Stopping backend (PID: $BACKEND_PID)..."
            kill $BACKEND_PID
            rm "${PROJECT_ROOT}/dev-backend.pid"
        fi
    fi
    
    # Stop frontend
    if [[ -f "${PROJECT_ROOT}/dev-frontend.pid" ]]; then
        FRONTEND_PID=$(cat "${PROJECT_ROOT}/dev-frontend.pid")
        if kill -0 $FRONTEND_PID 2>/dev/null; then
            echo "Stopping frontend (PID: $FRONTEND_PID)..."
            kill $FRONTEND_PID
            rm "${PROJECT_ROOT}/dev-frontend.pid"
        fi
    fi
    
    # Also check for any orphaned processes
    echo "Checking for orphaned processes..."
    pkill -f "uvicorn.*8000" 2>/dev/null || true
    pkill -f "npm.*dev.*3800" 2>/dev/null || true
    pkill -f "vite.*3800" 2>/dev/null || true
    
    echo -e "${GREEN}✅ Development services stopped${RESET}"
}

# Restart Development Mode services
restart_dev_mode() {
    echo -e "${CYAN}${BOLD}🔄 Restarting Development Mode (Clean Rebuild)${RESET}"
    echo -e "${YELLOW}This will:${RESET}"
    echo "  • Stop ALL current development servers"
    echo "  • Clear Python cache and compiled files"
    echo "  • Apply ALL code changes including SSL fixes"
    echo "  • Restart with fresh environment"
    echo ""
    
    # First stop existing services thoroughly
    echo -e "${YELLOW}Stopping all existing services...${RESET}"
    stop_dev_mode
    
    # Kill any remaining Python processes that might be holding connections
    echo -e "${YELLOW}Cleaning up any remaining processes...${RESET}"
    pkill -f "python.*mcp_entry_point" 2>/dev/null || true
    pkill -f "python.*fastmcp" 2>/dev/null || true
    pkill -f "uvicorn" 2>/dev/null || true
    
    # Clear Python cache to ensure new code is loaded
    echo -e "${YELLOW}Clearing Python cache...${RESET}"
    find "${PROJECT_ROOT}/agenthub_main" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "${PROJECT_ROOT}/agenthub_main" -type f -name "*.pyc" -delete 2>/dev/null || true
    find "${PROJECT_ROOT}/agenthub_main" -type f -name "*.pyo" -delete 2>/dev/null || true
    
    # Wait longer for ports to be fully released and connections to close
    echo -e "${YELLOW}Waiting for ports to be released...${RESET}"
    sleep 3
    
    # Ensure ports are free
    if lsof -Pi :${FASTMCP_PORT} -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}Force killing process on port ${FASTMCP_PORT}...${RESET}"
        kill -9 $(lsof -Pi :${FASTMCP_PORT} -sTCP:LISTEN -t) 2>/dev/null || true
        sleep 1
    fi
    if lsof -Pi :${FRONTEND_PORT} -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}Force killing process on port ${FRONTEND_PORT}...${RESET}"
        kill -9 $(lsof -Pi :${FRONTEND_PORT} -sTCP:LISTEN -t) 2>/dev/null || true
        sleep 1
    fi
    
    # Clear any log files that might have SSL errors cached
    echo -e "${YELLOW}Clearing old logs...${RESET}"
    > "${PROJECT_ROOT}/logs/backend.log" 2>/dev/null || true
    > "${PROJECT_ROOT}/logs/frontend.log" 2>/dev/null || true
    
    # Start services again with fresh environment
    echo -e "${GREEN}Starting services with fresh environment...${RESET}"
    start_dev_mode
    
    echo ""
    echo -e "${GREEN}✅ Development services restarted with clean rebuild!${RESET}"
    echo -e "${CYAN}💡 All code changes including SSL fixes have been applied${RESET}"
    echo "  • Backend: Running with new SSL configuration"
    echo "  • Frontend: Ready to connect to self-hosted Supabase"
    echo "  • SSL: Self-signed certificates now properly handled"
}

# Clean Docker system
clean_docker() {
    echo -e "${YELLOW}🧹 Docker System Cleanup${RESET}"
    echo "This will remove:"
    echo "- All stopped containers"
    echo "- All unused networks, volumes, and images"
    echo "- All build cache"
    echo "- agenthub project images (since we rebuild with --no-cache)"
    echo ""
    read -p "Continue? (y/N): " confirm
    
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        echo "Cleaning up Docker system..."
        
        # Clean project-specific builds first
        clean_existing_builds
        
        # Comprehensive system cleanup
        docker system prune -a -f  # More aggressive cleanup
        docker builder prune -a -f  # Remove all build cache
        
        echo -e "${GREEN}✅ Comprehensive Docker cleanup complete${RESET}"
    fi
}

# Main loop
main() {
    # Handle command line arguments for quick actions
    if [[ $# -gt 0 ]]; then
        case $1 in
            stop-dev) stop_dev_mode; exit 0 ;;
            restart-dev) restart_dev_mode; exit 0 ;;
            start-dev) start_dev_mode; exit 0 ;;
            *) echo "Unknown argument: $1"; exit 1 ;;
        esac
    fi
    
    while true; do
        show_header
        show_main_menu
        
        read -p "Select option: " choice
        
        case $choice in
            1) start_postgresql_local ;;
            2) start_supabase_cloud ;;
            3) start_redis_supabase ;;
            [Bb]) start_database_only ;;
            [Cc]) start_postgresql_with_ui ;;
            [Dd]) start_dev_mode ;;
            [Rr]) restart_dev_mode ;;
            [Pp]) start_optimized_mode ;;
            [Mm]) monitor_performance ;;
            4) show_service_status ;;
            5) stop_all_services ;;
            6) view_logs ;;
            7) database_shell ;;
            8) clean_docker ;;
            9) force_complete_rebuild ;;
            0) 
                echo -e "\n${GREEN}👋 Goodbye!${RESET}\n"
                exit 0
                ;;
            *) 
                echo -e "${RED}Invalid option!${RESET}"
                sleep 1
                ;;
        esac
        
        if [[ $choice != "0" && $choice != "5" ]]; then
            echo ""
            read -p "Press Enter to continue..."
        fi
    done
}

# Run main function with all arguments
main "$@"