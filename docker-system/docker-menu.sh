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

    ensure_single_backend
}

# Only ONE backend may exist at a time.
# Stops whichever backend is running so the one about to start owns the port.
ensure_single_backend() {
    local want="Go"
    local port="${FASTMCP_PORT:-8000}"

    # 1) Docker container named agenthub-backend (either runtime shares this name)
    local image
    image=$(docker ps -a --filter "name=^agenthub-backend$" --format '{{.Image}}' 2>/dev/null | head -1)
    if [[ -n "$image" ]]; then
        echo -e "${YELLOW}⚠️  A backend container exists; stopping it (only one backend may run, starting ${want})...${RESET}"
        docker stop agenthub-backend >/dev/null 2>&1 || true
        docker rm agenthub-backend >/dev/null 2>&1 || true
    fi

    # 2) Any other known backend process still listening on the backend port.
    #    Unknown processes are never killed: report and stop instead.
    local pid cmd
    for pid in $(ss -H -ltnp "sport = :${port}" 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u); do
        cmd=$(tr '\0' ' ' < "/proc/${pid}/cmdline" 2>/dev/null)
        if [[ "$cmd" =~ (agenthub) ]]; then
            echo -e "${YELLOW}⚠️  Backend process on port ${port} (PID ${pid}); stopping it (starting ${want})...${RESET}"
            kill "$pid" 2>/dev/null || true
        else
            echo -e "${RED}❌ Port ${port} is held by another process (PID ${pid}: ${cmd:0:80}). Not killing it; free the port and retry.${RESET}"
            return 1
        fi
    done

    # Wait up to ~10s for the port to be released
    local i
    for i in $(seq 1 20); do
        ss -H -ltn "sport = :${port}" 2>/dev/null | grep -q . || return 0
        sleep 0.5
    done
    echo -e "${RED}❌ Port ${port} is still in use after stopping the backend.${RESET}"
    return 1
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
        export MCP_PORT=${MCP_PORT:-${FASTMCP_PORT:-8000}}
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
        export MCP_PORT=${MCP_PORT:-${FASTMCP_PORT:-8000}}
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
        export FASTMCP_PORT=8000
        export MCP_PORT=8000
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

# Function to display all loaded environment variables
display_env_config() {
    echo ""
    echo -e "${CYAN}${BOLD}📋 Loaded Environment Configuration:${RESET}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"

    # Database Configuration
    echo -e "${YELLOW}🗄️  Database Configuration:${RESET}"
    echo -e "  DATABASE_TYPE: ${BLUE}${DATABASE_TYPE:-not set}${RESET}"
    echo -e "  DATABASE_HOST: ${BLUE}${DATABASE_HOST:-not set}${RESET}"
    echo -e "  DATABASE_PORT: ${BLUE}${DATABASE_PORT:-not set}${RESET}"
    echo -e "  DATABASE_NAME: ${BLUE}${DATABASE_NAME:-not set}${RESET}"
    echo -e "  DATABASE_USER: ${BLUE}${DATABASE_USER:-not set}${RESET}"
    if [[ -n "$DATABASE_PASSWORD" ]]; then
        echo -e "  DATABASE_PASSWORD: ${BLUE}[SET]${RESET}"
    else
        echo -e "  DATABASE_PASSWORD: ${RED}[NOT SET]${RESET}"
    fi

    # Service Ports
    echo ""
    echo -e "${YELLOW}🚀 Service Ports:${RESET}"
    echo -e "  FASTMCP_PORT: ${BLUE}${FASTMCP_PORT:-not set}${RESET}"
    echo -e "  FRONTEND_PORT: ${BLUE}${FRONTEND_PORT:-not set}${RESET}"
    echo -e "  MCP_PORT: ${BLUE}${MCP_PORT:-${FASTMCP_PORT:-not set}}${RESET}"

    # Authentication Settings
    echo ""
    echo -e "${YELLOW}🔐 Authentication Settings:${RESET}"
    echo -e "  AUTH_PROVIDER: ${BLUE}${AUTH_PROVIDER:-not set}${RESET}"
    echo -e "  AUTH_ENABLED: ${BLUE}${AUTH_ENABLED:-not set}${RESET}"
    echo -e "  EMAIL_VERIFIED_AUTO: ${BLUE}${EMAIL_VERIFIED_AUTO:-not set}${RESET}"

    # API URLs
    echo ""
    echo -e "${YELLOW}🌐 API URLs:${RESET}"
    echo -e "  VITE_API_URL: ${BLUE}${VITE_API_URL:-not set}${RESET}"
    echo -e "  VITE_BACKEND_URL: ${BLUE}${VITE_BACKEND_URL:-not set}${RESET}"

    # Supabase Configuration (if applicable)
    if [[ "$DATABASE_TYPE" == "supabase" ]] || [[ -n "${SUPABASE_URL:-}" ]]; then
        echo ""
        echo -e "${YELLOW}☁️  Supabase Configuration:${RESET}"
        echo -e "  SUPABASE_URL: ${BLUE}${SUPABASE_URL:-not set}${RESET}"
        if [[ -n "${SUPABASE_ANON_KEY:-}" ]]; then
            echo -e "  SUPABASE_ANON_KEY: ${BLUE}[SET]${RESET}"
        else
            echo -e "  SUPABASE_ANON_KEY: ${RED}[NOT SET]${RESET}"
        fi
    fi

    # Additional Environment Variables
    echo ""
    echo -e "${YELLOW}⚙️  Additional Settings:${RESET}"
    echo -e "  CONTAINER_ENV: ${BLUE}${CONTAINER_ENV:-not set}${RESET}"
    echo -e "  ENV: ${BLUE}${ENV:-not set}${RESET}"
    echo -e "  PYTHONDONTWRITEBYTECODE: ${BLUE}${PYTHONDONTWRITEBYTECODE:-not set}${RESET}"

    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo ""
}

# Clear screen and show header
show_header() {
    clear
    echo -e "${CYAN}${BOLD}"
    echo "╔════════════════════════════════════════════════╗"
    echo "║        agenthub Docker Management            ║"
    echo "║           Build System v3.0                   ║"
    echo "╚════════════════════════════════════════════════╝"
    echo -e "${RESET}"
    echo -e "${YELLOW}Backend: Port ${FASTMCP_PORT:-8000} | Frontend: Port ${FRONTEND_PORT:-3800}${RESET}"
    echo -e "${YELLOW}Database: ${DATABASE_TYPE:-postgresql} (${DATABASE_HOST:-localhost}:${DATABASE_PORT:-5432})${RESET}"

    # Enhanced auth status display with bypass indicator
    if [[ "${AUTH_ENABLED:-true}" == "false" ]]; then
        echo -e "${GREEN}🔓 Auth: BYPASSED for Development (No Keycloak needed)${RESET}"
        echo -e "${CYAN}   → Backend: Using DEFAULT_USER_ID=${DEFAULT_USER_ID:-dev-user-*}${RESET}"
        echo -e "${CYAN}   → Frontend: VITE_DISABLE_AUTH=${VITE_DISABLE_AUTH:-true}${RESET}"
    else
        echo -e "${YELLOW}🔐 Auth: ${AUTH_PROVIDER:-keycloak} (enabled: ${AUTH_ENABLED:-true})${RESET}"
    fi

    echo -e "${YELLOW}All builds use --no-cache (provenance optimized)${RESET}"
    echo ""
}

# Show authentication bypass help
show_auth_help() {
    clear
    echo -e "${CYAN}${BOLD}"
    echo "╔════════════════════════════════════════════════════════════════════╗"
    echo "║          Authentication Bypass - Development Mode Setup         ║"
    echo "╚════════════════════════════════════════════════════════════════════╝"
    echo -e "${RESET}"
    echo ""
    echo -e "${GREEN}${BOLD}📖 Overview${RESET}"
    echo "────────────────────────────────────────────────────────────────────"
    echo "When working locally, you can bypass Keycloak authentication to develop"
    echo "without needing an external authentication server running."
    echo ""
    echo -e "${CYAN}${BOLD}🔧 How to Enable Auth Bypass${RESET}"
    echo "────────────────────────────────────────────────────────────────────"
    echo "1. Edit your .env or .env.dev file and set:"
    echo ""
    echo -e "   ${YELLOW}# Backend: Bypass all authentication${RESET}"
    echo -e "   ${GREEN}AUTH_ENABLED=false${RESET}"
    echo ""
    echo -e "   ${YELLOW}# Frontend: Disable auth UI${RESET}"
    echo -e "   ${GREEN}VITE_DISABLE_AUTH=true${RESET}"
    echo ""
    echo "2. Restart your development environment:"
    echo -e "   ${CYAN}./docker-menu.sh${RESET} → Option ${BOLD}R${RESET} (Restart Dev Mode)"
    echo ""
    echo -e "${MAGENTA}${BOLD}⚙️  What Happens When Bypassed${RESET}"
    echo "────────────────────────────────────────────────────────────────────"
    echo -e "${YELLOW}Backend (AUTH_ENABLED=false):${RESET}"
    echo "  ✅ All API requests bypass authentication middleware"
    echo "  ✅ Default user context injected automatically:"
    echo -e "     • User ID: ${CYAN}${DEFAULT_USER_ID:-dev-user-00000000-0000-0000-0000-000000000000}${RESET}"
    echo -e "     • Email: ${CYAN}${DEFAULT_USER_EMAIL:-dev@localhost}${RESET}"
    echo -e "     • Username: ${CYAN}${DEFAULT_USERNAME:-developer}${RESET}"
    echo "  ✅ No Keycloak connection required"
    echo "  ✅ Logs will show: 🔓 AUTH_ENABLED=false - Bypassing authentication"
    echo ""
    echo -e "${YELLOW}Frontend (VITE_DISABLE_AUTH=true):${RESET}"
    echo "  ✅ Login/signup forms hidden"
    echo "  ✅ Direct access to all features"
    echo "  ✅ No token management needed"
    echo ""
    echo -e "${RED}${BOLD}🔐 Production Configuration${RESET}"
    echo "────────────────────────────────────────────────────────────────────"
    echo "⚠️  For production deployment, always use:"
    echo -e "   ${GREEN}AUTH_ENABLED=true${RESET}"
    echo -e "   ${GREEN}VITE_DISABLE_AUTH=false${RESET}"
    echo ""
    echo -e "${CYAN}${BOLD}📋 Environment Variables Reference${RESET}"
    echo "────────────────────────────────────────────────────────────────────"
    echo -e "${YELLOW}Backend Auth Control:${RESET}"
    echo "  AUTH_ENABLED=false          → Bypass authentication"
    echo "  DEFAULT_USER_ID=<uuid>      → Custom dev user ID"
    echo "  DEFAULT_USER_EMAIL=<email>  → Custom dev user email"
    echo "  DEFAULT_USERNAME=<name>     → Custom dev username"
    echo ""
    echo -e "${YELLOW}Frontend Auth Control:${RESET}"
    echo "  VITE_DISABLE_AUTH=true      → Hide login UI"
    echo ""
    echo -e "${GREEN}${BOLD}✅ Current Configuration${RESET}"
    echo "────────────────────────────────────────────────────────────────────"
    if [[ "${AUTH_ENABLED:-true}" == "false" ]]; then
        echo -e "  Backend Auth: ${GREEN}BYPASSED ✓${RESET}"
        echo -e "  Default User: ${CYAN}${DEFAULT_USER_ID:-dev-user-*} (${DEFAULT_USER_EMAIL:-dev@localhost})${RESET}"
    else
        echo -e "  Backend Auth: ${YELLOW}ENABLED (Keycloak required)${RESET}"
    fi

    if [[ "${VITE_DISABLE_AUTH:-false}" == "true" ]]; then
        echo -e "  Frontend Auth: ${GREEN}BYPASSED ✓${RESET}"
    else
        echo -e "  Frontend Auth: ${YELLOW}ENABLED (Login required)${RESET}"
    fi
    echo ""
    echo -e "${CYAN}💡 Tip: This is perfect for local development, testing, and demos!${RESET}"
    echo ""
    echo "────────────────────────────────────────────────────────────────────"
    echo -e "Press ${BOLD}Enter${RESET} to return to main menu..."
    read
}

# Show main menu
show_main_menu() {
    echo -e "${MAGENTA}${BOLD}Build Configurations${RESET}"
    echo "────────────────────────────────────────────────"
    echo "  1) 🐹 Backend (Go) + Frontend Only (requires DB running)"
    echo "  R) 🔄 Rebuild Backend (Go) + Frontend (apply new changes)"
    echo ""
    echo -e "${GREEN}${BOLD}Database Management${RESET}"
    echo "────────────────────────────────────────────────"
    echo "  B) 🗄️  Database Only (PostgreSQL standalone)"
    echo "  C) 🔍 Check PostgreSQL Connection (automatic test)"
    echo "  G) 🎛️  pgAdmin UI Only (requires DB running)"
    echo "  X) 🗑️  Clean Database Volume (Fresh Schema)"
    echo ""
    echo -e "${CYAN}${BOLD}Development${RESET}"
    echo "────────────────────────────────────────────────"
    echo "  A) 🔓 Auth Bypass Help (Local dev without Keycloak)"
    echo ""
    echo -e "${MAGENTA}${BOLD}Management Options${RESET}"
    echo "────────────────────────────────────────────────"
    echo "  4) 📊 Show Status"
    echo "  5) 🛑 Stop All Services"
    echo "  6) 📜 View Logs"
    echo "  7) 🗄️  Database Shell"
    echo "  8) 🧹 Clean Docker System"
    echo "  9) 🔄 Force Complete Rebuild (removes all images)"
    echo "  E) 📋 Show Environment Configuration"
    echo "  0) 🚪 Exit"
    echo "────────────────────────────────────────────────"
}

# Build and start the Go backend and the frontend (PostgreSQL runs separately, option B)
start_postgresql_local() {
    local compose_file="docker-compose.backend-go-frontend.yml"
    local runtime_label="Go"
    echo -e "${GREEN}🚀 Building and Starting Backend (${runtime_label}) + Frontend Only...${RESET}"
    echo -e "${YELLOW}Note: PostgreSQL should be running separately (use option B first)${RESET}"
    echo -e "${CYAN}Using credentials from .env.dev${RESET}"

    cd "$DOCKER_DIR"

    set_build_optimization
    check_and_free_ports || return 1

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

    echo -e "${CYAN}Using ${compose_file} for backend and frontend only...${RESET}"

    # Validate environment before building
    if ! validate_env_variables; then
        echo -e "${RED}❌ Please fix environment configuration errors before continuing${RESET}"
        return 1
    fi

    echo -e "${CYAN}Building backend and frontend containers in parallel...${RESET}"
    echo -e "${YELLOW}This will be faster as both containers build simultaneously${RESET}"

    # Always use .env.dev for consistency and set CONTAINER_ENV=docker
    CONTAINER_ENV=docker docker-compose --env-file "${ENV_DEV_FILE:-../../.env.dev}" -f "$compose_file" build --parallel --no-cache || {
        echo -e "${RED}❌ Build failed. Check error messages above${RESET}"
        return 1
    }

    echo -e "${CYAN}Starting backend and frontend services...${RESET}"
    CONTAINER_ENV=docker docker-compose --env-file "${ENV_DEV_FILE:-../../.env.dev}" -f "$compose_file" up -d || {
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
    echo -e "${CYAN}📝 Note: Tables will be created automatically by the ORM when backend starts${RESET}"
    echo "PostgreSQL: localhost:${DATABASE_PORT}"
    echo "Database: ${DATABASE_NAME}"
    echo "User: ${DATABASE_USER}"
    echo ""
    echo -e "${YELLOW}To connect: psql -h localhost -p ${DATABASE_PORT} -U ${DATABASE_USER} -d ${DATABASE_NAME}${RESET}"
    echo -e "${CYAN}Using credentials from .env.dev${RESET}"
}

# Check PostgreSQL Connection (Option C)
check_postgresql_connection() {
    echo -e "${CYAN}🔍 Checking PostgreSQL Connection...${RESET}"
    echo ""

    # Display connection parameters
    echo -e "${YELLOW}Connection Parameters:${RESET}"
    echo "  Host: ${DATABASE_HOST:-localhost} (Docker: agenthub-postgres)"
    echo "  Port: ${DATABASE_PORT:-5432}"
    echo "  Database: ${DATABASE_NAME:-agenthub}"
    echo "  User: ${DATABASE_USER:-agenthub_user}"
    echo ""

    # Try both Docker internal and localhost connections
    local connection_success=false

    # Test 1: Docker internal connection (if PostgreSQL container is running)
    if docker ps | grep -q agenthub-postgres; then
        echo -e "${CYAN}🐳 Testing Docker internal connection...${RESET}"

        # Use pg_isready for quick connection test
        if PGPASSWORD="${DATABASE_PASSWORD}" docker exec agenthub-postgres pg_isready -h localhost -p 5432 -U "${DATABASE_USER:-agenthub_user}" -d "${DATABASE_NAME:-agenthub}" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Docker internal connection: SUCCESS${RESET}"

            # Test actual SQL query
            echo -e "${CYAN}   Testing SQL query execution...${RESET}"
            if PGPASSWORD="${DATABASE_PASSWORD}" docker exec agenthub-postgres psql -h localhost -p 5432 -U "${DATABASE_USER:-agenthub_user}" -d "${DATABASE_NAME:-agenthub}" -c "SELECT version();" >/dev/null 2>&1; then
                echo -e "${GREEN}   ✅ SQL query execution: SUCCESS${RESET}"
                connection_success=true
            else
                echo -e "${RED}   ❌ SQL query execution: FAILED${RESET}"
            fi
        else
            echo -e "${RED}❌ Docker internal connection: FAILED${RESET}"
        fi
    else
        echo -e "${YELLOW}⚠️  PostgreSQL container not running, skipping Docker internal test${RESET}"
    fi

    echo ""

    # Test 2: Host connection (from outside Docker)
    echo -e "${CYAN}🌐 Testing host connection (localhost:${DATABASE_PORT})...${RESET}"

    # Check if psql is available on host
    if command -v psql >/dev/null 2>&1; then
        if PGPASSWORD="${DATABASE_PASSWORD}" pg_isready -h localhost -p "${DATABASE_PORT:-5432}" -U "${DATABASE_USER:-agenthub_user}" -d "${DATABASE_NAME:-agenthub}" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Host connection (pg_isready): SUCCESS${RESET}"

            # Test actual SQL connection
            echo -e "${CYAN}   Testing SQL connection from host...${RESET}"
            if PGPASSWORD="${DATABASE_PASSWORD}" psql -h localhost -p "${DATABASE_PORT:-5432}" -U "${DATABASE_USER:-agenthub_user}" -d "${DATABASE_NAME:-agenthub}" -c "SELECT current_database(), current_user;" >/dev/null 2>&1; then
                echo -e "${GREEN}   ✅ Host SQL connection: SUCCESS${RESET}"
                connection_success=true
            else
                echo -e "${RED}   ❌ Host SQL connection: FAILED${RESET}"
            fi
        else
            echo -e "${RED}❌ Host connection (pg_isready): FAILED${RESET}"
        fi
    else
        echo -e "${YELLOW}⚠️  psql not available on host, using Docker exec for testing${RESET}"

        # Fallback: use Docker exec if container is running
        if docker ps | grep -q agenthub-postgres; then
            if PGPASSWORD="${DATABASE_PASSWORD}" docker exec agenthub-postgres psql -h agenthub-postgres -p 5432 -U "${DATABASE_USER:-agenthub_user}" -d "${DATABASE_NAME:-agenthub}" -c "SELECT 'Connection test successful' as status;" 2>/dev/null; then
                echo -e "${GREEN}✅ Docker exec connection test: SUCCESS${RESET}"
                connection_success=true
            else
                echo -e "${RED}❌ Docker exec connection test: FAILED${RESET}"
            fi
        fi
    fi

    echo ""
    echo "────────────────────────────────────────────────"

    # Final status
    if [ "$connection_success" = true ]; then
        echo -e "${GREEN}${BOLD}🎉 PostgreSQL Connection: OPERATIONAL${RESET}"
        echo -e "${CYAN}You can now use option 7 for automatic database shell access${RESET}"
    else
        echo -e "${RED}${BOLD}❌ PostgreSQL Connection: FAILED${RESET}"
        echo -e "${YELLOW}Troubleshooting tips:${RESET}"
        echo "  1. Make sure PostgreSQL is running (use option B)"
        echo "  2. Check if ports are available: netstat -tulpn | grep :${DATABASE_PORT:-5432}"
        echo "  3. Verify environment variables in .env.dev"
        echo "  4. Check Docker logs: docker logs agenthub-postgres"
    fi

    echo ""
}

# Start pgAdmin UI Only (Option G)
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

    # Remove old pgAdmin data volume to ensure clean configuration
    echo -e "${YELLOW}Removing old pgAdmin data to ensure fresh configuration...${RESET}"
    docker volume rm pgadmin-data 2>/dev/null || true

    # Pull latest pgAdmin image
    echo -e "${CYAN}Pulling latest pgAdmin image...${RESET}"
    docker pull dpage/pgadmin4:latest

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
    echo "     Password: ${DATABASE_PASSWORD:-P02tqbj016p9}"
}

# Clean Database Volume (Option X - Remove PostgreSQL data for fresh schema)
clean_database_volume() {
    echo -e "${RED}${BOLD}🗑️  Clean Database Volume${RESET}"
    echo ""

    # First, detect which volume is actually being used
    local actual_volume=""
    if docker ps -a | grep -q agenthub-postgres; then
        echo -e "${CYAN}🔍 Detecting PostgreSQL volume...${RESET}"
        actual_volume=$(docker inspect agenthub-postgres 2>/dev/null | grep -A 5 '"Mounts"' | grep '"Name"' | sed 's/.*"Name": "\(.*\)".*/\1/' | head -1)
        if [[ -n "$actual_volume" ]]; then
            echo -e "${GREEN}Found volume: ${BLUE}${actual_volume}${RESET}"
        fi
    fi

    echo ""
    echo -e "${YELLOW}This will:${RESET}"
    echo "  - Stop and remove PostgreSQL container"
    if [[ -n "$actual_volume" ]]; then
        echo "  - Remove PostgreSQL volume: ${actual_volume}"
    else
        echo "  - Remove PostgreSQL volumes (will search for postgres-related volumes)"
    fi
    echo "  - ⚠️  ALL DATABASE DATA WILL BE LOST"
    echo "  - Next start will create fresh database with current schema"
    echo ""
    echo -e "${RED}${BOLD}USE CASE:${RESET} ${CYAN}When you've added new columns/tables in code and need fresh schema${RESET}"
    echo ""
    read -p "Are you sure you want to delete all database data? Type 'yes' to confirm: " confirm

    if [[ "$confirm" == "yes" ]]; then
        echo -e "${YELLOW}🛑 Stopping PostgreSQL container...${RESET}"
        docker stop agenthub-postgres 2>/dev/null || true

        echo -e "${YELLOW}🗑️  Removing PostgreSQL container...${RESET}"
        docker rm agenthub-postgres 2>/dev/null || true

        # Remove the detected volume or search for postgres volumes
        if [[ -n "$actual_volume" ]]; then
            echo -e "${YELLOW}🗑️  Removing PostgreSQL volume (${actual_volume})...${RESET}"
            if docker volume rm "$actual_volume" 2>/dev/null; then
                echo -e "${GREEN}✅ Volume removed successfully!${RESET}"
            else
                echo -e "${RED}⚠️  Failed to remove volume (may be in use)${RESET}"
            fi
        else
            echo -e "${YELLOW}🔍 Searching for postgres-related volumes...${RESET}"
            local postgres_volumes=$(docker volume ls -q | grep -E "(postgres|agenthub)" 2>/dev/null)
            if [[ -n "$postgres_volumes" ]]; then
                echo -e "${YELLOW}Found volumes:${RESET}"
                echo "$postgres_volumes"
                read -p "Remove these volumes? (y/N): " remove_all
                if [[ "$remove_all" =~ ^[Yy]$ ]]; then
                    for vol in $postgres_volumes; do
                        echo "  Removing $vol..."
                        docker volume rm "$vol" 2>/dev/null || echo "    (skipped - may be in use)"
                    done
                    echo -e "${GREEN}✅ Volumes removed${RESET}"
                fi
            else
                echo -e "${YELLOW}No postgres volumes found${RESET}"
            fi
        fi

        echo ""
        echo -e "${GREEN}✅ Database cleanup complete!${RESET}"
        echo ""
        echo -e "${CYAN}${BOLD}Next Steps:${RESET}"
        echo "  1. Use option B to start PostgreSQL"
        echo "  2. ORM will create tables with current schema automatically"
        echo "  3. Start backend (dev mode or Docker)"
        echo ""
        echo -e "${YELLOW}💡 TIP: This is useful after adding new columns like 'subtask_count'${RESET}"
    else
        echo -e "${YELLOW}Cancelled - database volume preserved${RESET}"
    fi
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

    # Stop Docker services
    cd "$DOCKER_DIR"
    echo "Stopping Docker services..."
    CONTAINER_ENV=docker docker-compose --env-file ../../.env.dev -f docker-compose.backend-go-frontend.yml down 2>/dev/null || true

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

# Database shell access with automatic connection
database_shell() {
    echo -e "${CYAN}🗄️  Database Shell Options:${RESET}"
    echo "1) PostgreSQL (automatic connection)"
    echo "2) Redis (if running locally)"

    read -p "Select database: " db_choice

    case $db_choice in
        1)
            echo -e "${CYAN}Connecting to PostgreSQL with automatic authentication...${RESET}"
            echo ""

            # Check if PostgreSQL container is running
            if docker ps | grep -q agenthub-postgres; then
                echo -e "${GREEN}✅ PostgreSQL container found${RESET}"
                echo -e "${YELLOW}Connection details:${RESET}"
                echo "  Host: agenthub-postgres (Docker internal)"
                echo "  Database: dhafnck_mcp"
                echo "  User: dhafnck_user"
                echo ""

                # Use Docker exec with automatic password
                echo -e "${CYAN}Connecting via Docker exec (no password required)...${RESET}"
                echo -e "${YELLOW}Type \\q to exit, \\l to list databases, \\dt to list tables${RESET}"
                echo "────────────────────────────────────────────────"

                PGPASSWORD="${DATABASE_PASSWORD}" docker exec -it agenthub-postgres psql -U dhafnck_user -d dhafnck_mcp 2>/dev/null || {
                    echo -e "${RED}❌ Failed to connect via Docker exec${RESET}"
                    echo -e "${YELLOW}Trying alternative connection method...${RESET}"

                    # Fallback: try external connection if psql is available
                    if command -v psql >/dev/null 2>&1; then
                        echo -e "${CYAN}Connecting via external psql...${RESET}"
                        PGPASSWORD="${DATABASE_PASSWORD}" psql -h localhost -p "${DATABASE_PORT:-5432}" -U dhafnck_user -d dhafnck_mcp
                    else
                        echo -e "${RED}❌ psql not available on host. Install PostgreSQL client tools.${RESET}"
                    fi
                }

            else
                echo -e "${YELLOW}⚠️  PostgreSQL container not running. Trying external connection...${RESET}"

                # Try external connection if PostgreSQL container is not running
                if command -v psql >/dev/null 2>&1; then
                    echo -e "${CYAN}Attempting external connection to localhost:${DATABASE_PORT:-5432}...${RESET}"
                    echo -e "${YELLOW}Connection details:${RESET}"
                    echo "  Host: localhost"
                    echo "  Port: ${DATABASE_PORT:-5432}"
                    echo "  Database: dhafnck_mcp"
                    echo "  User: dhafnck_user"
                    echo ""
                    echo -e "${YELLOW}Type \\q to exit, \\l to list databases, \\dt to list tables${RESET}"
                    echo "────────────────────────────────────────────────"

                    PGPASSWORD="${DATABASE_PASSWORD}" psql -h localhost -p "${DATABASE_PORT:-5432}" -U dhafnck_user -d dhafnck_mcp || {
                        echo -e "${RED}❌ Connection failed. Please check:${RESET}"
                        echo "  1. PostgreSQL is running (use option B to start)"
                        echo "  2. Connection parameters in .env.dev are correct"
                        echo "  3. Database port ${DATABASE_PORT:-5432} is accessible"
                    }
                else
                    echo -e "${RED}❌ PostgreSQL not accessible. Please:${RESET}"
                    echo "  1. Start PostgreSQL container (option B)"
                    echo "  2. Or install PostgreSQL client tools (psql)"
                fi
            fi
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


        echo -e "${YELLOW}🧹 Pruning Docker system...${RESET}"
        docker system prune -af --volumes 2>/dev/null || true
        docker builder prune -af 2>/dev/null || true

        echo -e "${GREEN}✅ Complete cleanup done!${RESET}"
        echo ""
        echo -e "${CYAN}Now select a configuration to rebuild:${RESET}"
        echo "1) 🐹 Backend (Go) + Frontend"
        echo "0) Cancel"

        read -p "Select configuration: " rebuild_choice

        case $rebuild_choice in
            1) start_postgresql_local ;;
            0) echo "Cancelled" ;;
            *) echo "Invalid option" ;;
        esac
    else
        echo -e "${YELLOW}Cancelled${RESET}"
    fi
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
            auth-help) show_auth_help; exit 0 ;;
            0) exit 0 ;;  # Quick exit without menu
            *) echo "Unknown argument: $1"; exit 1 ;;
        esac
    fi

    while true; do
        show_header
        show_main_menu

        read -p "Select option: " choice

        case $choice in
            1|[Rr]) start_postgresql_local ;;
            [Bb]) start_database_only ;;
            [Cc]) check_postgresql_connection ;;
            [Gg]) start_postgresql_with_ui ;;
            [Xx]) clean_database_volume ;;
            [Aa]) show_auth_help ;;
            4) show_service_status ;;
            5) stop_all_services ;;
            6) view_logs ;;
            7) database_shell ;;
            8) clean_docker ;;
            9) force_complete_rebuild ;;
            [Ee]) display_env_config ;;
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
