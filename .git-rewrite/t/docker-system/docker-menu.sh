#!/bin/bash
# docker-menu.sh - DhafnckMCP Docker Management Interface
# Updated for streamlined database configurations

set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="${SCRIPT_DIR}/docker"

# Check and stop conflicting containers on required ports
check_and_free_ports() {
    echo -e "${YELLOW}🔍 Checking for port conflicts...${RESET}"
    
    # Check for containers using port 8000
    local backend_containers=$(docker ps -q --filter "publish=8000" 2>/dev/null)
    if [[ -n "$backend_containers" ]]; then
        echo -e "${YELLOW}⚠️  Stopping containers using port 8000...${RESET}"
        docker stop $backend_containers
    fi
    
    # Check for containers using port 3800  
    local frontend_containers=$(docker ps -q --filter "publish=3800" 2>/dev/null)
    if [[ -n "$frontend_containers" ]]; then
        echo -e "${YELLOW}⚠️  Stopping containers using port 3800...${RESET}"
        docker stop $frontend_containers
    fi
    
    # Clean up stopped containers
    if [[ -n "$backend_containers" ]] || [[ -n "$frontend_containers" ]]; then
        echo -e "${YELLOW}🧹 Cleaning up stopped containers...${RESET}"
        docker container prune -f >/dev/null 2>&1
        echo -e "${GREEN}✅ Ports 8000 and 3800 are now available${RESET}"
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
    echo -e "${YELLOW}🛑 Stopping existing dhafnck containers...${RESET}"
    docker stop dhafnck-backend dhafnck-frontend 2>/dev/null || true
    docker rm dhafnck-backend dhafnck-frontend 2>/dev/null || true
    
    # Remove dhafnck project images to force complete rebuild
    local dhafnck_images=$(docker images -q --filter "reference=*dhafnck*" 2>/dev/null)
    if [[ -n "$dhafnck_images" ]]; then
        echo -e "${YELLOW}🗑️  Removing existing dhafnck images to ensure fresh build...${RESET}"
        docker rmi $dhafnck_images -f >/dev/null 2>&1 || true
    fi
    
    # Remove docker project images from docker-system 
    local docker_images=$(docker images -q --filter "reference=docker-*" 2>/dev/null)
    if [[ -n "$docker_images" ]]; then
        echo -e "${YELLOW}🗑️  Removing existing docker-system images...${RESET}"
        docker rmi $docker_images -f >/dev/null 2>&1 || true
    fi
    
    # Clear Python cache to ensure code changes are picked up
    echo -e "${YELLOW}🐍 Clearing Python cache files...${RESET}"
    find ../dhafnck_mcp_main -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find ../dhafnck_mcp_main -type f -name "*.pyc" -delete 2>/dev/null || true
    
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

# Clear screen and show header
show_header() {
    clear
    echo -e "${CYAN}${BOLD}"
    echo "╔════════════════════════════════════════════════╗"
    echo "║        DhafnckMCP Docker Management            ║"
    echo "║           Build System v3.0                   ║"
    echo "╚════════════════════════════════════════════════╝"
    echo -e "${RESET}"
    echo -e "${YELLOW}Backend: Port 8000 | Frontend: Port 3800${RESET}"
    echo -e "${YELLOW}All builds use --no-cache (provenance optimized)${RESET}"
    echo ""
}

# Show main menu
show_main_menu() {
    echo -e "${MAGENTA}${BOLD}Build Configurations${RESET}"
    echo "────────────────────────────────────────────────"
    echo "  1) 🐘 PostgreSQL Local (Backend + Frontend)"
    echo "  2) ☁️  Supabase Cloud (No Redis)"
    echo "  3) ☁️🔴 Supabase Cloud + Redis (Full Stack)"
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

# Build and start PostgreSQL Local configuration (no Redis)
start_postgresql_local() {
    echo -e "${GREEN}🐘 Starting PostgreSQL Local configuration...${RESET}"
    cd "$DOCKER_DIR"
    
    set_build_optimization
    check_and_free_ports
    clean_existing_builds
    
    echo "Building with --no-cache..."
    DATABASE_TYPE=postgresql docker-compose --env-file ../../.env -f ../docker-compose.yml --profile postgresql build --no-cache
    
    echo "Starting services..."
    DATABASE_TYPE=postgresql docker-compose --env-file ../../.env -f ../docker-compose.yml --profile postgresql up -d
    
    echo -e "${GREEN}✅ Services started!${RESET}"
    echo "Backend: http://localhost:8000"
    echo "Frontend: http://localhost:3000"
    echo "PostgreSQL: localhost:5432"
    
    show_service_status "../docker-compose.yml"
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
    DATABASE_TYPE=supabase docker-compose --env-file ../../.env -f ../docker-compose.yml build --no-cache
    
    echo -e "${CYAN}🚀 Starting services...${RESET}"
    DATABASE_TYPE=supabase docker-compose --env-file ../../.env -f ../docker-compose.yml up -d
    
    # Wait for services to be ready
    echo -e "${YELLOW}⏳ Waiting for services to start (10 seconds)...${RESET}"
    sleep 10
    
    # Health check
    echo -e "${CYAN}🏥 Checking service health...${RESET}"
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is healthy${RESET}"
    else
        echo -e "${YELLOW}⚠️  Backend may still be starting up${RESET}"
    fi
    
    echo -e "${GREEN}✅ Services started!${RESET}"
    echo "Backend: http://localhost:8000"
    echo "Frontend: http://localhost:3800"
    echo "Database: Supabase Cloud (remote)"
    echo ""
    echo -e "${CYAN}💡 Tips:${RESET}"
    echo "  - Your data is stored in Supabase Cloud, not locally"
    echo "  - Check logs: docker logs dhafnck-backend --tail 50"
    echo "  - Verify connection: docker exec dhafnck-backend env | grep SUPABASE"
    
    show_service_status "../docker-compose.yml"
}


# Build and start Redis + Supabase Cloud configuration
start_redis_supabase() {
    echo -e "${GREEN}🔴☁️  Starting Redis + Supabase Cloud configuration...${RESET}"
    cd "$DOCKER_DIR"
    
    set_build_optimization
    check_and_free_ports
    clean_existing_builds
    
    echo "Building with --no-cache..."
    DATABASE_TYPE=supabase ENABLE_REDIS=true docker-compose --env-file ../../.env -f ../docker-compose.yml --profile redis build --no-cache
    
    echo "Starting services..."
    DATABASE_TYPE=supabase ENABLE_REDIS=true docker-compose --env-file ../../.env -f ../docker-compose.yml --profile redis up -d
    
    echo -e "${GREEN}✅ Services started!${RESET}"
    echo "Backend: http://localhost:8000"
    echo "Frontend: http://localhost:3800"
    echo "Database: Supabase Cloud"
    echo "Redis: localhost:6379"
    
    show_service_status "../docker-compose.yml"
}

# Show service status
show_service_status() {
    local compose_file=${1:-""}
    echo ""
    echo -e "${CYAN}Service Status:${RESET}"
    if [[ -n "$compose_file" ]]; then
        docker-compose --env-file ../../.env -f "$compose_file" ps
    else
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    fi
}

# Stop all services
stop_all_services() {
    echo -e "${YELLOW}🛑 Stopping all services...${RESET}"
    cd "$DOCKER_DIR"
    
    # Stop all services using the unified docker-compose
    echo "Stopping services..."
    docker-compose --env-file ../../.env -f ../docker-compose.yml down 2>/dev/null || true
    
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
        1) docker logs -f dhafnck-backend 2>/dev/null || echo "Backend container not found" ;;
        2) docker logs -f dhafnck-frontend 2>/dev/null || echo "Frontend container not found" ;;
        3) docker logs -f dhafnck-postgres 2>/dev/null || echo "PostgreSQL container not found" ;;
        4) docker logs -f dhafnck-redis 2>/dev/null || echo "Redis container not found" ;;
        5) 
            echo "Showing logs for all services..."
            docker logs dhafnck-backend --tail=50 2>/dev/null || true
            docker logs dhafnck-frontend --tail=50 2>/dev/null || true
            docker logs dhafnck-postgres --tail=50 2>/dev/null || true
            docker logs dhafnck-redis --tail=50 2>/dev/null || true
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
            docker exec -it dhafnck-postgres psql -U postgres -d dhafnck_mcp 2>/dev/null || \
            echo "PostgreSQL container not found or not accessible"
            ;;
        2) 
            echo "Connecting to Redis..."
            docker exec -it dhafnck-redis redis-cli 2>/dev/null || \
            echo "Redis container not found or not accessible"
            ;;
        *) echo "Invalid option" ;;
    esac
}

# Force complete rebuild - removes everything and rebuilds from scratch
force_complete_rebuild() {
    echo -e "${RED}${BOLD}🔄 FORCE COMPLETE REBUILD${RESET}"
    echo -e "${YELLOW}This will:${RESET}"
    echo "  - Stop and remove ALL dhafnck containers"
    echo "  - Remove ALL dhafnck Docker images"
    echo "  - Clear all Python cache files"
    echo "  - Remove Docker build cache"
    echo "  - Force rebuild everything from scratch"
    echo ""
    read -p "Are you sure? This will take several minutes. (y/N): " confirm
    
    if [[ $confirm == "y" || $confirm == "Y" ]]; then
        echo -e "${YELLOW}🛑 Stopping all containers...${RESET}"
        docker stop $(docker ps -aq --filter "name=dhafnck") 2>/dev/null || true
        
        echo -e "${YELLOW}🗑️  Removing all containers...${RESET}"
        docker rm $(docker ps -aq --filter "name=dhafnck") 2>/dev/null || true
        
        echo -e "${YELLOW}🗑️  Removing all dhafnck images...${RESET}"
        docker rmi $(docker images -q --filter "reference=*dhafnck*") -f 2>/dev/null || true
        docker rmi $(docker images -q --filter "reference=docker-*") -f 2>/dev/null || true
        
        echo -e "${YELLOW}🐍 Clearing all Python cache...${RESET}"
        find ../dhafnck_mcp_main -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find ../dhafnck_mcp_main -type f -name "*.pyc" -delete 2>/dev/null || true
        
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
    docker-compose -f docker-compose.optimized.yml build \
        --parallel \
        --compress || {
            echo -e "${RED}Build failed, falling back to standard build${RESET}"
            docker-compose -f docker-compose.optimized.yml build
        }
    
    echo -e "${CYAN}🚀 Starting optimized services...${RESET}"
    
    # Start with resource limits
    if [ "$USE_MINIMAL" = "true" ]; then
        # Start only essential services for very low memory
        docker-compose -f docker-compose.optimized.yml up -d postgres backend
        echo -e "${YELLOW}Started minimal services only (no frontend/redis)${RESET}"
    else
        docker-compose -f docker-compose.optimized.yml up -d
    fi
    
    # Wait for services
    echo -e "${YELLOW}⏳ Waiting for services to start...${RESET}"
    local max_wait=30
    local waited=0
    while [ $waited -lt $max_wait ]; do
        if curl -f http://localhost:8000/health &>/dev/null; then
            echo -e "${GREEN}✅ Backend is healthy${RESET}"
            break
        fi
        sleep 2
        waited=$((waited + 2))
        echo -n "."
    done
    echo ""
    
    echo -e "${GREEN}✅ Optimized services started!${RESET}"
    echo "Backend: http://localhost:8000"
    [ "$USE_MINIMAL" != "true" ] && echo "Frontend: http://localhost:3800"
    echo ""
    echo -e "${CYAN}Resource Usage:${RESET}"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
    echo ""
    echo -e "${YELLOW}💡 Tips for better performance:${RESET}"
    echo "  • Close unnecessary browser tabs"
    echo "  • Disable other Docker containers"
    echo "  • Use 'M' option to monitor resource usage"
}

# Create optimized docker-compose file
create_optimized_compose() {
    cat > docker-compose.optimized.yml << 'EOF'
# Auto-generated optimized configuration for low-resource PCs
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: dhafnck-postgres
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
      - "5432:5432"
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
      dockerfile: dhafnck_mcp_main/docker/Dockerfile
      args:
        - ENV=production
    container_name: dhafnck-backend
    environment:
      - DATABASE_TYPE=postgresql
      - DATABASE_URL=postgresql://dhafnck_user:dev_password@postgres:5432/dhafnck_mcp
      - APP_ENV=production
      - APP_DEBUG=false
      - APP_LOG_LEVEL=WARNING
      - PYTHONOPTIMIZE=1
      - WEB_CONCURRENCY=2
    volumes:
      - backend-data:/app/data
    ports:
      - "8000:8000"
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
    container_name: dhafnck-frontend
    environment:
      - NODE_ENV=production
      - VITE_API_URL=http://localhost:8000
    volumes:
      - frontend-static:/usr/share/nginx/html:ro
    ports:
      - "3800:80"
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
    name: dhafnck-network
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
        echo -e "${CYAN}${BOLD}   DhafnckMCP Performance Monitor - $(date +%H:%M:%S)${RESET}"
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

# Clean Docker system
clean_docker() {
    echo -e "${YELLOW}🧹 Docker System Cleanup${RESET}"
    echo "This will remove:"
    echo "- All stopped containers"
    echo "- All unused networks, volumes, and images"
    echo "- All build cache"
    echo "- DhafnckMCP project images (since we rebuild with --no-cache)"
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
    while true; do
        show_header
        show_main_menu
        
        read -p "Select option: " choice
        
        case $choice in
            1) start_postgresql_local ;;
            2) start_supabase_cloud ;;
            3) start_redis_supabase ;;
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

# Run main function
main