#!/bin/bash

# =============================================================================
# Production Rollback Script - agenthub
# =============================================================================
# This script performs a complete rollback of the production deployment,
# restoring the previous stable version with minimal downtime.
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
readonly ROLLBACK_LOG="/var/log/agenthub-rollback.log"
readonly ROLLBACK_DATA_DIR="/tmp/agenthub-rollback"

ENVIRONMENT="production"
AUTO_CONFIRM="false"
ROLLBACK_TO_VERSION=""
DRY_RUN="false"

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "${ROLLBACK_LOG}"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "${ROLLBACK_LOG}"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "${ROLLBACK_LOG}"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "${ROLLBACK_LOG}"
}

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -e, --environment ENV       Target environment (production, staging)
    -v, --version VERSION       Specific version to rollback to
    -a, --auto-confirm         Skip confirmation prompts
    -d, --dry-run              Show rollback plan without executing
    --help                     Show this help message

Examples:
    $0 --environment production
    $0 --version v1.2.3 --environment production
    $0 --auto-confirm --environment production
    $0 --dry-run --environment staging

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -v|--version)
            ROLLBACK_TO_VERSION="$2"
            shift 2
            ;;
        -a|--auto-confirm)
            AUTO_CONFIRM="true"
            shift
            ;;
        -d|--dry-run)
            DRY_RUN="true"
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
    case "$ENVIRONMENT" in
        production|staging)
            log_success "Environment '$ENVIRONMENT' is valid"
            ;;
        *)
            log_error "Invalid environment: $ENVIRONMENT"
            exit 1
            ;;
    esac
}

check_rollback_data() {
    log_info "Checking rollback data availability..."
    
    if [[ ! -d "$ROLLBACK_DATA_DIR" ]]; then
        log_error "Rollback data directory not found: $ROLLBACK_DATA_DIR"
        log_error "Cannot perform rollback without snapshot data"
        exit 1
    fi
    
    local required_files=(
        "containers.json"
        "images.txt"
        "env.backup"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "${ROLLBACK_DATA_DIR}/${file}" ]]; then
            log_error "Missing rollback file: $file"
            exit 1
        fi
    done
    
    log_success "Rollback data is available"
}

detect_current_version() {
    log_info "Detecting current deployment version..."
    
    local compose_file="${PROJECT_ROOT}/docker-system/docker-compose.${ENVIRONMENT}.yml"
    
    # Try to get version from running containers
    local current_version
    current_version=$(docker-compose -f "$compose_file" ps --format json 2>/dev/null | \
                      jq -r '.[0].Labels."org.opencontainers.image.version" // "unknown"' 2>/dev/null || echo "unknown")
    
    if [[ "$current_version" != "unknown" && -n "$current_version" ]]; then
        log_info "Current version: $current_version"
        echo "$current_version"
    else
        log_warning "Could not detect current version"
        echo "unknown"
    fi
}

detect_previous_version() {
    log_info "Detecting previous stable version..."
    
    if [[ -n "$ROLLBACK_TO_VERSION" ]]; then
        log_info "Using specified rollback version: $ROLLBACK_TO_VERSION"
        echo "$ROLLBACK_TO_VERSION"
        return 0
    fi
    
    # Try to find previous version from git tags
    local previous_version
    if previous_version=$(git tag --sort=-version:refname | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | head -2 | tail -1 2>/dev/null); then
        log_info "Detected previous version from git: $previous_version"
        echo "$previous_version"
    else
        log_warning "Could not automatically detect previous version"
        echo "latest-backup"
    fi
}

confirm_rollback() {
    if [[ "$AUTO_CONFIRM" == "true" ]]; then
        return 0
    fi
    
    local current_version
    local previous_version
    current_version=$(detect_current_version)
    previous_version=$(detect_previous_version)
    
    echo
    log_warning "=== ROLLBACK CONFIRMATION ==="
    echo "Environment: $ENVIRONMENT"
    echo "Current Version: $current_version"
    echo "Rollback To: $previous_version"
    echo "Dry Run: $DRY_RUN"
    echo
    
    if [[ "$DRY_RUN" != "true" ]]; then
        log_warning "⚠️  This will rollback the $ENVIRONMENT deployment!"
        log_warning "⚠️  This action may cause temporary service interruption!"
        echo
        read -p "Are you sure you want to proceed with rollback? (yes/no): " -r
        if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            log_info "Rollback cancelled by user"
            exit 0
        fi
    fi
}

stop_current_services() {
    log_info "Stopping current services..."
    
    local compose_file="${PROJECT_ROOT}/docker-system/docker-compose.${ENVIRONMENT}.yml"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would stop services using: $compose_file"
        return 0
    fi
    
    cd "$PROJECT_ROOT"
    
    # Graceful shutdown with timeout
    timeout 60 docker-compose -f "$compose_file" down --timeout 30 || {
        log_warning "Graceful shutdown timed out, forcing stop..."
        docker-compose -f "$compose_file" kill
        docker-compose -f "$compose_file" down --volumes
    }
    
    log_success "Services stopped"
}

restore_previous_images() {
    log_info "Restoring previous Docker images..."
    
    local previous_version
    previous_version=$(detect_previous_version)
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would restore images for version: $previous_version"
        return 0
    fi
    
    # Pull or restore previous images
    local images=("agenthub-backend" "agenthub-frontend")
    
    for image in "${images[@]}"; do
        local previous_image_tag="${image}:${previous_version}"
        
        # Try to find previous image locally first
        if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "$previous_image_tag"; then
            log_info "Previous image found locally: $previous_image_tag"
            docker tag "$previous_image_tag" "${image}:latest"
        else
            log_warning "Previous image not found locally, attempting to pull..."
            if docker pull "$previous_image_tag" 2>/dev/null; then
                docker tag "$previous_image_tag" "${image}:latest"
                log_success "Pulled and tagged: $previous_image_tag"
            else
                log_error "Failed to restore image: $previous_image_tag"
                return 1
            fi
        fi
    done
    
    log_success "Previous images restored"
}

restore_configuration() {
    log_info "Restoring previous configuration..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would restore configuration from backup"
        return 0
    fi
    
    # Restore environment configuration
    if [[ -f "${ROLLBACK_DATA_DIR}/env.backup" ]]; then
        cp "${ROLLBACK_DATA_DIR}/env.backup" "${PROJECT_ROOT}/.env"
        log_success "Environment configuration restored"
    else
        log_warning "No environment backup found, keeping current configuration"
    fi
    
    # Restore any other configuration files as needed
    # Add specific configuration restoration logic here
    
    return 0
}

start_rollback_services() {
    log_info "Starting services with rollback version..."
    
    local compose_file="${PROJECT_ROOT}/docker-system/docker-compose.${ENVIRONMENT}.yml"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would start services using: $compose_file"
        return 0
    fi
    
    cd "$PROJECT_ROOT"
    
    # Start database and dependencies first
    log_info "Starting database and dependencies..."
    docker-compose -f "$compose_file" up -d postgres redis
    
    # Wait for database to be ready
    log_info "Waiting for database to be ready..."
    timeout 60 bash -c 'until docker-compose -f "'$compose_file'" exec -T postgres pg_isready; do sleep 2; done'
    
    # Start all services
    log_info "Starting all services..."
    docker-compose -f "$compose_file" up -d
    
    log_success "Services started with rollback version"
}

verify_rollback() {
    log_info "Verifying rollback deployment..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would verify rollback deployment"
        return 0
    fi
    
    # Wait for services to stabilize
    sleep 30
    
    # Run health checks
    if [[ -f "${PROJECT_ROOT}/scripts/deployment/health-checks/comprehensive-health-check.sh" ]]; then
        log_info "Running rollback health checks..."
        if bash "${PROJECT_ROOT}/scripts/deployment/health-checks/comprehensive-health-check.sh" --environment "$ENVIRONMENT" --timeout 60; then
            log_success "Rollback health checks passed"
        else
            log_error "Rollback health checks failed"
            return 1
        fi
    else
        log_warning "Health check script not found, performing basic verification..."
        
        # Basic API health check
        local backend_url
        if [[ "$ENVIRONMENT" == "production" ]]; then
            backend_url="${PRODUCTION_BACKEND_URL:-http://localhost:8000}"
        else
            backend_url="${STAGING_BACKEND_URL:-http://localhost:8001}"
        fi
        
        if curl -f -s "${backend_url}/api/v2/health" > /dev/null; then
            log_success "Basic health check passed"
        else
            log_error "Basic health check failed"
            return 1
        fi
    fi
    
    return 0
}

cleanup_failed_deployment() {
    log_info "Cleaning up failed deployment artifacts..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would clean up failed deployment"
        return 0
    fi
    
    # Remove failed deployment containers
    docker container prune -f
    
    # Remove dangling images from failed deployment
    docker image prune -f
    
    log_success "Cleanup completed"
}

generate_rollback_report() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    local current_version
    local rollback_version
    current_version=$(detect_current_version)
    rollback_version=$(detect_previous_version)
    
    echo
    echo "=== ROLLBACK REPORT ==="
    echo "Timestamp: $timestamp"
    echo "Environment: $ENVIRONMENT"
    echo "Previous Version: $current_version"
    echo "Rolled Back To: $rollback_version"
    echo "Dry Run: $DRY_RUN"
    echo
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "🔍 DRY RUN COMPLETED - No changes were made"
        echo
        echo "Rollback Plan:"
        echo "1. Stop current services"
        echo "2. Restore previous Docker images ($rollback_version)"
        echo "3. Restore previous configuration"
        echo "4. Start services with rollback version"
        echo "5. Verify deployment health"
        echo "6. Clean up failed deployment artifacts"
    else
        echo "✅ ROLLBACK COMPLETED SUCCESSFULLY"
        echo
        echo "Post-Rollback Actions:"
        echo "- Monitor application logs for the next 30 minutes"
        echo "- Verify all critical user flows are working"
        echo "- Check monitoring dashboards for anomalies"
        echo "- Notify stakeholders of rollback completion"
    fi
    
    echo
    echo "Rollback Log: $ROLLBACK_LOG"
    echo "Rollback Data: $ROLLBACK_DATA_DIR"
}

main() {
    log_info "Starting rollback process for $ENVIRONMENT environment"
    log_info "Rollback log: $ROLLBACK_LOG"
    
    # Create log file
    mkdir -p "$(dirname "$ROLLBACK_LOG")" 2>/dev/null || true
    touch "$ROLLBACK_LOG" 2>/dev/null || {
        ROLLBACK_LOG="/tmp/agenthub-rollback.log"
        log_warning "Cannot write to /var/log, using ${ROLLBACK_LOG}"
    }
    
    validate_environment
    check_rollback_data
    confirm_rollback
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "=== DRY RUN MODE - NO CHANGES WILL BE MADE ==="
    fi
    
    # Execute rollback steps
    stop_current_services
    restore_previous_images
    restore_configuration
    start_rollback_services
    
    # Wait for services to stabilize before verification
    if [[ "$DRY_RUN" != "true" ]]; then
        log_info "Waiting for services to stabilize..."
        sleep 30
    fi
    
    verify_rollback
    cleanup_failed_deployment
    
    generate_rollback_report
    
    if [[ "$DRY_RUN" != "true" ]]; then
        log_success "=== ROLLBACK COMPLETED SUCCESSFULLY ==="
        log_info "Environment: $ENVIRONMENT"
        log_info "Services have been rolled back to previous stable version"
        
        if [[ "$ENVIRONMENT" == "production" ]]; then
            log_warning "IMPORTANT: Production has been rolled back!"
            log_warning "- Investigate the cause of the deployment failure"
            log_warning "- Fix issues before attempting next deployment"
            log_warning "- Monitor system stability for the next hour"
        fi
    fi
}

# Execute main function
main "$@"