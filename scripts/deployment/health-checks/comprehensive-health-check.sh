#!/bin/bash

# =============================================================================
# Comprehensive Health Check Script - 4genthub Production Deployment
# =============================================================================
# This script performs comprehensive health checks after deployment including:
# - Service availability and responsiveness
# - Database connectivity and migrations
# - Authentication system validation
# - MCP server functionality
# - Performance baseline validation
# 
# Author: DevOps Agent
# Version: 1.0.0
# Date: 2025-09-11
# =============================================================================

set -euo pipefail

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

ENVIRONMENT="production"
TIMEOUT=30
VERBOSE="false"
SKIP_PERFORMANCE="false"

# Health check results
declare -a PASSED_CHECKS=()
declare -a FAILED_CHECKS=()
declare -a WARNING_CHECKS=()

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    PASSED_CHECKS+=("$1")
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    WARNING_CHECKS+=("$1")
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    FAILED_CHECKS+=("$1")
}

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -e, --environment ENV    Target environment (production, staging)
    -t, --timeout SECONDS   Timeout for health checks (default: 30)
    -v, --verbose           Enable verbose output
    -s, --skip-performance  Skip performance baseline checks
    --help                  Show this help message

Examples:
    $0 --environment production
    $0 --verbose --timeout 60 --environment staging

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE="true"
            shift
            ;;
        -s|--skip-performance)
            SKIP_PERFORMANCE="true"
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

get_service_urls() {
    case "$ENVIRONMENT" in
        production)
            BACKEND_URL="${PRODUCTION_BACKEND_URL:-http://localhost:8000}"
            FRONTEND_URL="${PRODUCTION_FRONTEND_URL:-http://localhost:3000}"
            KEYCLOAK_URL="${PRODUCTION_KEYCLOAK_URL:-http://localhost:8080}"
            ;;
        staging)
            BACKEND_URL="${STAGING_BACKEND_URL:-http://localhost:8001}"
            FRONTEND_URL="${STAGING_FRONTEND_URL:-http://localhost:3001}"
            KEYCLOAK_URL="${STAGING_KEYCLOAK_URL:-http://localhost:8081}"
            ;;
        *)
            log_error "Unknown environment: $ENVIRONMENT"
            exit 1
            ;;
    esac
}

check_docker_containers() {
    log_info "Checking Docker container health..."
    
    local compose_file="${PROJECT_ROOT}/docker-system/docker-compose.${ENVIRONMENT}.yml"
    if [[ ! -f "$compose_file" ]]; then
        log_error "Docker compose file not found: $compose_file"
        return 1
    fi
    
    # Check container status
    local unhealthy_containers=()
    
    while IFS= read -r line; do
        local container_name service_status
        container_name=$(echo "$line" | awk '{print $1}')
        service_status=$(echo "$line" | awk '{print $2}')
        
        case "$service_status" in
            "Up"|"Up (healthy)")
                if [[ "$VERBOSE" == "true" ]]; then
                    log_success "Container healthy: $container_name"
                fi
                ;;
            *)
                unhealthy_containers+=("$container_name ($service_status)")
                ;;
        esac
    done < <(docker-compose -f "$compose_file" ps --format "table {{.Name}}\t{{.Status}}" | tail -n +2)
    
    if [[ ${#unhealthy_containers[@]} -eq 0 ]]; then
        log_success "All Docker containers are healthy"
        return 0
    else
        for container in "${unhealthy_containers[@]}"; do
            log_error "Unhealthy container: $container"
        done
        return 1
    fi
}

check_database_connectivity() {
    log_info "Checking database connectivity..."
    
    local compose_file="${PROJECT_ROOT}/docker-system/docker-compose.${ENVIRONMENT}.yml"
    
    # Test database connection
    if docker-compose -f "$compose_file" exec -T postgres pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
        log_success "Database is ready and accepting connections"
    else
        log_error "Database connection failed"
        return 1
    fi
    
    # Check database migrations
    local migration_check
    migration_check=$(docker-compose -f "$compose_file" run --rm backend python -c "
from alembic import command
from alembic.config import Config
config = Config('alembic.ini')
try:
    from alembic.script import ScriptDirectory
    script = ScriptDirectory.from_config(config)
    from alembic.runtime.environment import EnvironmentContext
    from alembic.runtime.migration import MigrationContext
    from sqlalchemy import create_engine
    import os
    
    engine = create_engine(os.getenv('DATABASE_URL'))
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        current_rev = context.get_current_revision()
        head_rev = script.get_current_head()
        
        if current_rev == head_rev:
            print('MIGRATIONS_CURRENT')
        else:
            print(f'MIGRATIONS_OUTDATED: current={current_rev}, head={head_rev}')
except Exception as e:
    print(f'MIGRATIONS_ERROR: {e}')
" 2>&1)
    
    if echo "$migration_check" | grep -q "MIGRATIONS_CURRENT"; then
        log_success "Database migrations are up to date"
        return 0
    elif echo "$migration_check" | grep -q "MIGRATIONS_OUTDATED"; then
        log_error "Database migrations are outdated"
        return 1
    else
        log_error "Migration check failed: $migration_check"
        return 1
    fi
}

check_backend_health() {
    log_info "Checking backend service health..."
    
    # Health endpoint check
    local health_response
    if health_response=$(curl -s -w "\n%{http_code}" --max-time "$TIMEOUT" "$BACKEND_URL/api/v2/health" 2>/dev/null); then
        local http_code
        http_code=$(echo "$health_response" | tail -n1)
        local body
        body=$(echo "$health_response" | head -n -1)
        
        if [[ "$http_code" == "200" ]]; then
            log_success "Backend health endpoint is responding"
            if [[ "$VERBOSE" == "true" ]]; then
                log_info "Health response: $body"
            fi
        else
            log_error "Backend health endpoint returned HTTP $http_code"
            return 1
        fi
    else
        log_error "Backend health endpoint is not accessible"
        return 1
    fi
    
    # Test critical endpoints
    local endpoints=(
        "/api/v2/auth/status"
        "/api/v2/tokens/validate"
        "/api/v2/projects"
    )
    
    for endpoint in "${endpoints[@]}"; do
        local response_code
        response_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$BACKEND_URL$endpoint" 2>/dev/null || echo "000")
        
        case "$response_code" in
            200|401|403) # 200=OK, 401/403=Expected for auth endpoints without token
                if [[ "$VERBOSE" == "true" ]]; then
                    log_success "Endpoint accessible: $endpoint (HTTP $response_code)"
                fi
                ;;
            000)
                log_error "Endpoint not accessible: $endpoint (connection failed)"
                return 1
                ;;
            *)
                log_warning "Endpoint returned unexpected status: $endpoint (HTTP $response_code)"
                ;;
        esac
    done
    
    log_success "Backend service is healthy and responsive"
    return 0
}

check_frontend_availability() {
    log_info "Checking frontend availability..."
    
    local response_code
    response_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$FRONTEND_URL" 2>/dev/null || echo "000")
    
    case "$response_code" in
        200)
            log_success "Frontend is accessible and serving content"
            return 0
            ;;
        000)
            log_error "Frontend is not accessible (connection failed)"
            return 1
            ;;
        *)
            log_error "Frontend returned unexpected status: HTTP $response_code"
            return 1
            ;;
    esac
}

check_keycloak_integration() {
    log_info "Checking Keycloak integration..."
    
    # Check Keycloak health
    local keycloak_health
    keycloak_health=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$KEYCLOAK_URL/health" 2>/dev/null || echo "000")
    
    case "$keycloak_health" in
        200)
            log_success "Keycloak is healthy and accessible"
            ;;
        000)
            log_error "Keycloak is not accessible"
            return 1
            ;;
        *)
            log_warning "Keycloak health check returned HTTP $keycloak_health"
            ;;
    esac
    
    # Test OIDC configuration endpoint
    local oidc_config
    oidc_config=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$KEYCLOAK_URL/realms/4genthub/.well-known/openid_configuration" 2>/dev/null || echo "000")
    
    case "$oidc_config" in
        200)
            log_success "Keycloak OIDC configuration is accessible"
            return 0
            ;;
        000)
            log_error "Keycloak OIDC configuration not accessible"
            return 1
            ;;
        *)
            log_error "Keycloak OIDC configuration returned HTTP $oidc_config"
            return 1
            ;;
    esac
}

check_mcp_server_functionality() {
    log_info "Checking MCP server functionality..."
    
    # Test MCP health endpoint
    local mcp_health
    mcp_health=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$BACKEND_URL/api/v2/mcp/health" 2>/dev/null || echo "000")
    
    case "$mcp_health" in
        200)
            log_success "MCP server is responding to health checks"
            ;;
        000|404)
            log_warning "MCP health endpoint not found (expected if not implemented)"
            ;;
        *)
            log_warning "MCP health endpoint returned HTTP $mcp_health"
            ;;
    esac
    
    # Test basic MCP operations (requires authentication)
    local task_endpoint
    task_endpoint=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$BACKEND_URL/api/v2/tasks" 2>/dev/null || echo "000")
    
    case "$task_endpoint" in
        401|403) # Expected - requires authentication
            log_success "MCP task endpoint is responding (requires auth as expected)"
            return 0
            ;;
        200)
            log_warning "MCP task endpoint accessible without auth (potential security issue)"
            return 0
            ;;
        000)
            log_error "MCP task endpoint not accessible"
            return 1
            ;;
        *)
            log_warning "MCP task endpoint returned unexpected status: HTTP $task_endpoint"
            return 0
            ;;
    esac
}

check_ssl_tls_configuration() {
    log_info "Checking SSL/TLS configuration..."
    
    # Check if services are running with TLS in production
    if [[ "$ENVIRONMENT" == "production" ]]; then
        # Extract hostname from URLs
        local backend_host
        backend_host=$(echo "$BACKEND_URL" | sed 's|https\?://||' | cut -d: -f1)
        
        if [[ "$BACKEND_URL" =~ ^https:// ]]; then
            # Test SSL certificate
            local ssl_check
            if ssl_check=$(echo | openssl s_client -connect "$backend_host:443" -servername "$backend_host" 2>&1); then
                if echo "$ssl_check" | grep -q "Verify return code: 0 (ok)"; then
                    log_success "SSL certificate is valid"
                else
                    log_warning "SSL certificate validation issues detected"
                fi
            else
                log_error "SSL connectivity test failed"
                return 1
            fi
        else
            log_warning "Production deployment not using HTTPS"
        fi
    else
        log_info "SSL/TLS check skipped for non-production environment"
    fi
    
    return 0
}

check_performance_baseline() {
    if [[ "$SKIP_PERFORMANCE" == "true" ]]; then
        log_info "Skipping performance baseline checks"
        return 0
    fi
    
    log_info "Running performance baseline checks..."
    
    # Measure response times for critical endpoints
    local endpoints=(
        "$BACKEND_URL/api/v2/health"
        "$BACKEND_URL/api/v2/auth/status"
    )
    
    for endpoint in "${endpoints[@]}"; do
        local response_time
        response_time=$(curl -o /dev/null -s -w "%{time_total}" --max-time "$TIMEOUT" "$endpoint" 2>/dev/null || echo "999")
        
        if (( $(echo "$response_time < 2.0" | bc -l) )); then
            if [[ "$VERBOSE" == "true" ]]; then
                log_success "Endpoint response time acceptable: $endpoint (${response_time}s)"
            fi
        elif (( $(echo "$response_time < 5.0" | bc -l) )); then
            log_warning "Endpoint response time slow: $endpoint (${response_time}s)"
        else
            log_error "Endpoint response time too slow: $endpoint (${response_time}s)"
            return 1
        fi
    done
    
    log_success "Performance baseline checks completed"
    return 0
}

check_resource_utilization() {
    log_info "Checking resource utilization..."
    
    local compose_file="${PROJECT_ROOT}/docker-system/docker-compose.${ENVIRONMENT}.yml"
    
    # Get container resource usage
    local high_cpu_containers=()
    local high_memory_containers=()
    
    while IFS= read -r line; do
        if [[ "$line" =~ ^(.*)[[:space:]]+([0-9]+\.[0-9]+)%[[:space:]]+/[[:space:]]+([0-9]+\.[0-9]+)%[[:space:]]+ ]]; then
            local container="${BASH_REMATCH[1]// /}"
            local cpu_percent="${BASH_REMATCH[2]}"
            local mem_percent="${BASH_REMATCH[3]}"
            
            if (( $(echo "$cpu_percent > 80.0" | bc -l) )); then
                high_cpu_containers+=("$container ($cpu_percent%)")
            fi
            
            if (( $(echo "$mem_percent > 80.0" | bc -l) )); then
                high_memory_containers+=("$container ($mem_percent%)")
            fi
        fi
    done < <(docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemPerc}}" 2>/dev/null | tail -n +2)
    
    if [[ ${#high_cpu_containers[@]} -eq 0 && ${#high_memory_containers[@]} -eq 0 ]]; then
        log_success "Resource utilization is within acceptable limits"
    else
        if [[ ${#high_cpu_containers[@]} -gt 0 ]]; then
            log_warning "High CPU usage detected: ${high_cpu_containers[*]}"
        fi
        if [[ ${#high_memory_containers[@]} -gt 0 ]]; then
            log_warning "High memory usage detected: ${high_memory_containers[*]}"
        fi
    fi
    
    return 0
}

generate_health_report() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo
    echo "=== HEALTH CHECK REPORT ==="
    echo "Timestamp: $timestamp"
    echo "Environment: $ENVIRONMENT"
    echo "Timeout: ${TIMEOUT}s"
    echo
    
    echo "✅ PASSED CHECKS (${#PASSED_CHECKS[@]}):"
    for check in "${PASSED_CHECKS[@]}"; do
        echo "  - $check"
    done
    echo
    
    if [[ ${#WARNING_CHECKS[@]} -gt 0 ]]; then
        echo "⚠️  WARNING CHECKS (${#WARNING_CHECKS[@]}):"
        for check in "${WARNING_CHECKS[@]}"; do
            echo "  - $check"
        done
        echo
    fi
    
    if [[ ${#FAILED_CHECKS[@]} -gt 0 ]]; then
        echo "❌ FAILED CHECKS (${#FAILED_CHECKS[@]}):"
        for check in "${FAILED_CHECKS[@]}"; do
            echo "  - $check"
        done
        echo
    fi
    
    local total_checks=$((${#PASSED_CHECKS[@]} + ${#WARNING_CHECKS[@]} + ${#FAILED_CHECKS[@]}))
    echo "Summary: ${#PASSED_CHECKS[@]}/$total_checks checks passed"
    
    if [[ ${#FAILED_CHECKS[@]} -eq 0 ]]; then
        if [[ ${#WARNING_CHECKS[@]} -eq 0 ]]; then
            echo "🎉 All health checks passed successfully!"
            return 0
        else
            echo "⚠️  Health checks passed with warnings"
            return 0
        fi
    else
        echo "❌ Health checks failed - deployment requires attention"
        return 1
    fi
}

main() {
    log_info "Starting comprehensive health checks for $ENVIRONMENT environment"
    log_info "Timeout: ${TIMEOUT}s | Verbose: $VERBOSE"
    
    get_service_urls
    
    log_info "Service URLs:"
    log_info "  Backend: $BACKEND_URL"
    log_info "  Frontend: $FRONTEND_URL"
    log_info "  Keycloak: $KEYCLOAK_URL"
    echo
    
    # Run all health checks
    local health_checks=(
        check_docker_containers
        check_database_connectivity
        check_backend_health
        check_frontend_availability
        check_keycloak_integration
        check_mcp_server_functionality
        check_ssl_tls_configuration
        check_performance_baseline
        check_resource_utilization
    )
    
    for check_func in "${health_checks[@]}"; do
        $check_func || true  # Continue even if individual checks fail
        echo
    done
    
    # Generate final report
    generate_health_report
}

# Ensure bc is available for floating point calculations
if ! command -v bc &> /dev/null; then
    echo "Warning: 'bc' command not found. Performance calculations may fail."
fi

main "$@"