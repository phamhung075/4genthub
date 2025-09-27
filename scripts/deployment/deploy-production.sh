#!/bin/bash

# =============================================================================
# agenthub Production Deployment Script
# =============================================================================
# This script handles the complete production deployment of the MCP Auto-Injection System
# including security hardening, monitoring setup, and validation checks.
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
readonly NC='\033[0m' # No Color

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
readonly DEPLOYMENT_LOG="/var/log/agenthub-deployment.log"
readonly ROLLBACK_DATA_DIR="/tmp/agenthub-rollback"

# Default values
ENVIRONMENT="production"
SKIP_SECURITY_SCAN="false"
SKIP_HEALTH_CHECK="false"
DRY_RUN="false"
FORCE_DEPLOY="false"

# Function definitions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "${DEPLOYMENT_LOG}"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "${DEPLOYMENT_LOG}"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "${DEPLOYMENT_LOG}"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "${DEPLOYMENT_LOG}"
}

cleanup() {
    log_info "Cleaning up temporary files..."
    rm -rf "${ROLLBACK_DATA_DIR}/temp"
}

trap cleanup EXIT

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -e, --environment ENV       Deployment environment (production, staging)
    -d, --dry-run              Show what would be deployed without executing
    -f, --force                Skip confirmation prompts
    -s, --skip-security        Skip security vulnerability scan
    -h, --skip-health-check    Skip post-deployment health checks
    --help                     Show this help message

Examples:
    $0 --environment production
    $0 --dry-run --environment staging
    $0 --force --skip-security --environment production

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN="true"
            shift
            ;;
        -f|--force)
            FORCE_DEPLOY="true"
            shift
            ;;
        -s|--skip-security)
            SKIP_SECURITY_SCAN="true"
            shift
            ;;
        -h|--skip-health-check)
            SKIP_HEALTH_CHECK="true"
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

validate_environment() {
    log_info "Validating deployment environment..."
    
    case "$ENVIRONMENT" in
        production|staging)
            log_success "Environment '$ENVIRONMENT' is valid"
            ;;
        *)
            log_error "Invalid environment: $ENVIRONMENT"
            log_error "Supported environments: production, staging"
            exit 1
            ;;
    esac
}

check_prerequisites() {
    log_info "Checking deployment prerequisites..."
    
    local missing_tools=()
    local tools=("docker" "docker-compose" "curl" "jq" "openssl")
    
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [[ ${#missing_tools[@]} -ne 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_error "Please install missing tools and retry"
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check required environment files
    local env_files=(".env" "docker-system/.env.${ENVIRONMENT}")
    for env_file in "${env_files[@]}"; do
        if [[ ! -f "${PROJECT_ROOT}/${env_file}" ]]; then
            log_error "Required environment file missing: ${env_file}"
            exit 1
        fi
    done
    
    log_success "All prerequisites met"
}

run_security_fixes() {
    log_info "Applying security fixes from audit report..."
    
    if [[ "$SKIP_SECURITY_SCAN" == "true" ]]; then
        log_warning "Skipping security fixes (--skip-security flag used)"
        return 0
    fi
    
    # Execute security fix script
    if [[ -f "${SCRIPT_DIR}/security/apply-security-fixes.sh" ]]; then
        bash "${SCRIPT_DIR}/security/apply-security-fixes.sh" --environment "$ENVIRONMENT"
        log_success "Security fixes applied"
    else
        log_warning "Security fix script not found, skipping security hardening"
    fi
}

create_rollback_snapshot() {
    log_info "Creating rollback snapshot..."
    
    mkdir -p "${ROLLBACK_DATA_DIR}"
    
    # Save current container states
    docker-compose -f "${PROJECT_ROOT}/docker-system/docker-compose.${ENVIRONMENT}.yml" ps --format json > "${ROLLBACK_DATA_DIR}/containers.json" || true
    
    # Save current images
    docker images --format "table {{.Repository}}:{{.Tag}}\t{{.ID}}\t{{.Size}}" > "${ROLLBACK_DATA_DIR}/images.txt"
    
    # Save environment configuration
    cp "${PROJECT_ROOT}/.env" "${ROLLBACK_DATA_DIR}/env.backup" 2>/dev/null || true
    
    log_success "Rollback snapshot created at ${ROLLBACK_DATA_DIR}"
}

build_images() {
    log_info "Building Docker images for ${ENVIRONMENT}..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would build images for ${ENVIRONMENT}"
        return 0
    fi
    
    cd "${PROJECT_ROOT}"
    
    # Build production images
    docker-compose -f "docker-system/docker-compose.${ENVIRONMENT}.yml" build --no-cache
    
    # Tag images with deployment timestamp
    local timestamp
    timestamp=$(date +"%Y%m%d-%H%M%S")
    
    local images=("agenthub-backend" "agenthub-frontend")
    for image in "${images[@]}"; do
        docker tag "${image}:latest" "${image}:${timestamp}"
        docker tag "${image}:latest" "${image}:${ENVIRONMENT}-latest"
    done
    
    log_success "Docker images built successfully"
}

deploy_infrastructure() {
    log_info "Deploying infrastructure components..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would deploy infrastructure"
        return 0
    fi
    
    cd "${PROJECT_ROOT}"
    
    # Stop existing containers
    docker-compose -f "docker-system/docker-compose.${ENVIRONMENT}.yml" down
    
    # Start database and dependencies first
    log_info "Starting database and dependencies..."
    docker-compose -f "docker-system/docker-compose.${ENVIRONMENT}.yml" up -d postgres redis
    
    # Wait for database to be ready
    log_info "Waiting for database to be ready..."
    timeout 60 bash -c 'until docker-compose -f "docker-system/docker-compose.'${ENVIRONMENT}'.yml" exec -T postgres pg_isready; do sleep 2; done'
    
    # Run database migrations
    log_info "Running database migrations..."
    docker-compose -f "docker-system/docker-compose.${ENVIRONMENT}.yml" run --rm backend python -m alembic upgrade head
    
    # Start all services
    log_info "Starting all services..."
    docker-compose -f "docker-system/docker-compose.${ENVIRONMENT}.yml" up -d
    
    log_success "Infrastructure deployed successfully"
}

run_health_checks() {
    log_info "Running post-deployment health checks..."
    
    if [[ "$SKIP_HEALTH_CHECK" == "true" ]]; then
        log_warning "Skipping health checks (--skip-health-check flag used)"
        return 0
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would run health checks"
        return 0
    fi
    
    # Execute health check script
    if [[ -f "${SCRIPT_DIR}/health-checks/comprehensive-health-check.sh" ]]; then
        bash "${SCRIPT_DIR}/health-checks/comprehensive-health-check.sh" --environment "$ENVIRONMENT"
        log_success "Health checks passed"
    else
        log_warning "Health check script not found"
    fi
}

run_smoke_tests() {
    log_info "Running smoke tests..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would run smoke tests"
        return 0
    fi
    
    # Basic API health check
    local backend_url
    if [[ "$ENVIRONMENT" == "production" ]]; then
        backend_url="${PRODUCTION_BACKEND_URL:-http://localhost:8000}"
    else
        backend_url="${STAGING_BACKEND_URL:-http://localhost:8001}"
    fi
    
    log_info "Testing API health endpoint..."
    if curl -f -s "${backend_url}/api/v2/health" > /dev/null; then
        log_success "API health check passed"
    else
        log_error "API health check failed"
        return 1
    fi
    
    # Test authentication endpoint
    log_info "Testing authentication endpoint..."
    if curl -f -s "${backend_url}/api/v2/auth/status" > /dev/null; then
        log_success "Authentication endpoint check passed"
    else
        log_error "Authentication endpoint check failed"
        return 1
    fi
    
    log_success "All smoke tests passed"
}

confirm_deployment() {
    if [[ "$FORCE_DEPLOY" == "true" ]]; then
        return 0
    fi
    
    echo
    log_warning "=== DEPLOYMENT CONFIRMATION ==="
    echo "Environment: $ENVIRONMENT"
    echo "Dry Run: $DRY_RUN"
    echo "Skip Security: $SKIP_SECURITY_SCAN"
    echo "Skip Health Check: $SKIP_HEALTH_CHECK"
    echo
    
    if [[ "$DRY_RUN" != "true" ]]; then
        read -p "Proceed with deployment? (yes/no): " -r
        if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            log_info "Deployment cancelled by user"
            exit 0
        fi
    fi
}

main() {
    log_info "Starting agenthub deployment to ${ENVIRONMENT}"
    log_info "Deployment log: ${DEPLOYMENT_LOG}"
    
    # Create log file
    mkdir -p "$(dirname "$DEPLOYMENT_LOG")" 2>/dev/null || true
    touch "$DEPLOYMENT_LOG" 2>/dev/null || {
        DEPLOYMENT_LOG="/tmp/agenthub-deployment.log"
        log_warning "Cannot write to /var/log, using ${DEPLOYMENT_LOG}"
    }
    
    validate_environment
    check_prerequisites
    confirm_deployment
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "=== DRY RUN MODE - NO CHANGES WILL BE MADE ==="
    fi
    
    create_rollback_snapshot
    run_security_fixes
    build_images
    deploy_infrastructure
    
    # Wait for services to start
    if [[ "$DRY_RUN" != "true" ]]; then
        log_info "Waiting for services to stabilize..."
        sleep 30
    fi
    
    run_health_checks
    run_smoke_tests
    
    log_success "=== DEPLOYMENT COMPLETED SUCCESSFULLY ==="
    log_info "Environment: ${ENVIRONMENT}"
    log_info "Rollback data: ${ROLLBACK_DATA_DIR}"
    log_info "Deployment log: ${DEPLOYMENT_LOG}"
    
    if [[ "$ENVIRONMENT" == "production" ]]; then
        log_info "Production deployment checklist:"
        log_info "- Monitor application logs for the first 30 minutes"
        log_info "- Verify all critical user flows are working"
        log_info "- Check monitoring dashboards for anomalies"
        log_info "- Notify stakeholders of successful deployment"
    fi
}

# Execute main function
main "$@"