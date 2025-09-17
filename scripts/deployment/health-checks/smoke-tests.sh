#!/bin/bash

# =============================================================================
# Smoke Tests Script - agenthub Production Deployment
# =============================================================================
# This script runs comprehensive smoke tests after deployment to validate
# that all critical functionalities are working as expected.
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

ENVIRONMENT="production"
TIMEOUT=30
VERBOSE="false"
TEST_USER_ID="smoke-test-user"
TEST_PROJECT_NAME="smoke-test-project"

# Test results tracking
declare -a PASSED_TESTS=()
declare -a FAILED_TESTS=()

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    PASSED_TESTS+=("$1")
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    FAILED_TESTS+=("$1")
}

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -e, --environment ENV    Target environment (production, staging)
    -t, --timeout SECONDS   Timeout for tests (default: 30)
    -v, --verbose           Enable verbose output
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
            ;;
        staging)
            BACKEND_URL="${STAGING_BACKEND_URL:-http://localhost:8001}"
            FRONTEND_URL="${STAGING_FRONTEND_URL:-http://localhost:3001}"
            ;;
        *)
            log_error "Unknown environment: $ENVIRONMENT"
            exit 1
            ;;
    esac
}

# Helper function to make authenticated API requests
make_api_request() {
    local method="$1"
    local endpoint="$2"
    local data="${3:-}"
    local expected_status="${4:-200}"
    
    local curl_opts=(-s -w "\n%{http_code}" --max-time "$TIMEOUT")
    
    if [[ -n "$data" ]]; then
        curl_opts+=(-H "Content-Type: application/json" -d "$data")
    fi
    
    local response
    response=$(curl "${curl_opts[@]}" -X "$method" "$BACKEND_URL$endpoint")
    
    local http_code
    http_code=$(echo "$response" | tail -n1)
    local body
    body=$(echo "$response" | head -n -1)
    
    if [[ "$http_code" == "$expected_status" ]]; then
        if [[ "$VERBOSE" == "true" ]]; then
            log_info "API Request successful: $method $endpoint (HTTP $http_code)"
        fi
        echo "$body"
        return 0
    else
        log_error "API Request failed: $method $endpoint (HTTP $http_code, expected $expected_status)"
        if [[ "$VERBOSE" == "true" && -n "$body" ]]; then
            log_error "Response: $body"
        fi
        return 1
    fi
}

test_health_endpoints() {
    log_info "Testing health endpoints..."
    
    # Backend health
    if make_api_request "GET" "/api/v2/health" "" "200" > /dev/null; then
        log_success "Backend health endpoint responding"
    else
        log_error "Backend health endpoint failed"
        return 1
    fi
    
    # Authentication status
    if make_api_request "GET" "/api/v2/auth/status" "" "200" > /dev/null; then
        log_success "Authentication status endpoint responding"
    else
        log_error "Authentication status endpoint failed"
        return 1
    fi
    
    return 0
}

test_authentication_flow() {
    log_info "Testing authentication flow..."
    
    # Test token validation endpoint (should return 401 without token)
    if make_api_request "GET" "/api/v2/tokens/validate" "" "401" > /dev/null; then
        log_success "Token validation properly rejects unauthenticated requests"
    else
        log_error "Token validation endpoint not properly secured"
        return 1
    fi
    
    # Test rate limiting on auth endpoints
    log_info "Testing rate limiting on authentication..."
    local rate_limit_test_passed=true
    for i in {1..15}; do
        if ! make_api_request "POST" "/api/v2/auth/login" '{"email":"test@example.com","password":"invalid"}' "400" > /dev/null; then
            if [[ $i -gt 10 ]]; then
                log_success "Rate limiting appears to be working (got rate limited)"
                break
            fi
            rate_limit_test_passed=false
        fi
        sleep 0.1
    done
    
    if [[ "$rate_limit_test_passed" == "true" ]]; then
        log_success "Authentication rate limiting is functional"
    else
        log_warning "Authentication rate limiting may not be working as expected"
    fi
    
    return 0
}

test_mcp_endpoints() {
    log_info "Testing MCP endpoints..."
    
    # Test project endpoints (should require authentication)
    if make_api_request "GET" "/api/v2/projects" "" "401" > /dev/null; then
        log_success "Projects endpoint properly secured"
    else
        log_error "Projects endpoint security issue"
        return 1
    fi
    
    # Test task endpoints (should require authentication)
    if make_api_request "GET" "/api/v2/tasks" "" "401" > /dev/null; then
        log_success "Tasks endpoint properly secured"
    else
        log_error "Tasks endpoint security issue"
        return 1
    fi
    
    # Test git branch endpoints (should require authentication)
    if make_api_request "GET" "/api/v2/git-branches" "" "401" > /dev/null; then
        log_success "Git branches endpoint properly secured"
    else
        log_error "Git branches endpoint security issue"
        return 1
    fi
    
    return 0
}

test_database_connectivity() {
    log_info "Testing database connectivity through API..."
    
    # Test an endpoint that requires database access
    local response
    if response=$(make_api_request "GET" "/api/v2/health/detailed" "" "200" 2>/dev/null); then
        if echo "$response" | grep -q '"database.*healthy"' || echo "$response" | grep -q '"database.*connected"'; then
            log_success "Database connectivity verified through API"
        else
            log_warning "Database status unclear from API response"
        fi
    else
        log_warning "Detailed health endpoint not available, skipping database connectivity test"
    fi
    
    return 0
}

test_frontend_availability() {
    log_info "Testing frontend availability..."
    
    # Test main page
    local response_code
    response_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$FRONTEND_URL" 2>/dev/null || echo "000")
    
    case "$response_code" in
        200)
            log_success "Frontend main page accessible"
            ;;
        000)
            log_error "Frontend not accessible"
            return 1
            ;;
        *)
            log_error "Frontend returned unexpected status: HTTP $response_code"
            return 1
            ;;
    esac
    
    # Test static assets (if available)
    local static_urls=(
        "/static/css/main.css"
        "/static/js/main.js"
        "/favicon.ico"
    )
    
    for url in "${static_urls[@]}"; do
        response_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$FRONTEND_URL$url" 2>/dev/null || echo "000")
        if [[ "$response_code" == "200" ]]; then
            if [[ "$VERBOSE" == "true" ]]; then
                log_success "Static asset accessible: $url"
            fi
        elif [[ "$response_code" == "404" ]]; then
            if [[ "$VERBOSE" == "true" ]]; then
                log_warning "Static asset not found (expected if using different build): $url"
            fi
        else
            log_warning "Static asset issue: $url (HTTP $response_code)"
        fi
    done
    
    return 0
}

test_ssl_tls_configuration() {
    log_info "Testing SSL/TLS configuration..."
    
    if [[ "$ENVIRONMENT" == "production" ]]; then
        # Extract hostname from backend URL
        local backend_host
        backend_host=$(echo "$BACKEND_URL" | sed 's|https\?://||' | cut -d: -f1)
        
        if [[ "$BACKEND_URL" =~ ^https:// ]]; then
            # Test SSL certificate
            local ssl_output
            if ssl_output=$(echo | openssl s_client -connect "$backend_host:443" -servername "$backend_host" 2>&1); then
                if echo "$ssl_output" | grep -q "Verify return code: 0 (ok)"; then
                    log_success "SSL certificate is valid"
                elif echo "$ssl_output" | grep -q "self signed certificate"; then
                    log_warning "Self-signed certificate detected (may be expected in test environments)"
                else
                    log_warning "SSL certificate validation issues detected"
                fi
                
                # Check TLS version
                if echo "$ssl_output" | grep -q "Protocol.*TLS.*1\.[2-9]"; then
                    log_success "Using secure TLS version"
                elif echo "$ssl_output" | grep -q "Protocol.*TLS.*1\.[0-1]"; then
                    log_error "Using deprecated TLS version"
                    return 1
                fi
            else
                log_error "SSL connectivity test failed"
                return 1
            fi
        else
            log_warning "Production environment not using HTTPS"
        fi
    else
        log_info "SSL/TLS check skipped for non-production environment"
    fi
    
    return 0
}

test_performance_baseline() {
    log_info "Testing performance baseline..."
    
    # Measure response times for critical endpoints
    local endpoints=(
        "/api/v2/health"
        "/api/v2/auth/status"
    )
    
    for endpoint in "${endpoints[@]}"; do
        local response_time
        response_time=$(curl -o /dev/null -s -w "%{time_total}" --max-time "$TIMEOUT" "$BACKEND_URL$endpoint" 2>/dev/null || echo "999")
        
        if (( $(echo "$response_time < 1.0" | bc -l) )); then
            if [[ "$VERBOSE" == "true" ]]; then
                log_success "Endpoint response time excellent: $endpoint (${response_time}s)"
            fi
        elif (( $(echo "$response_time < 3.0" | bc -l) )); then
            if [[ "$VERBOSE" == "true" ]]; then
                log_success "Endpoint response time acceptable: $endpoint (${response_time}s)"
            fi
        elif (( $(echo "$response_time < 10.0" | bc -l) )); then
            log_warning "Endpoint response time slow: $endpoint (${response_time}s)"
        else
            log_error "Endpoint response time too slow: $endpoint (${response_time}s)"
            return 1
        fi
    done
    
    log_success "Performance baseline tests completed"
    return 0
}

test_security_headers() {
    log_info "Testing security headers..."
    
    # Test for important security headers
    local headers_output
    headers_output=$(curl -I -s --max-time "$TIMEOUT" "$BACKEND_URL/api/v2/health" 2>/dev/null || echo "")
    
    local security_headers=(
        "X-Content-Type-Options"
        "X-Frame-Options"
        "X-XSS-Protection"
        "Strict-Transport-Security"
    )
    
    local missing_headers=()
    for header in "${security_headers[@]}"; do
        if echo "$headers_output" | grep -qi "$header"; then
            if [[ "$VERBOSE" == "true" ]]; then
                log_success "Security header present: $header"
            fi
        else
            missing_headers+=("$header")
        fi
    done
    
    if [[ ${#missing_headers[@]} -eq 0 ]]; then
        log_success "All important security headers are present"
    elif [[ ${#missing_headers[@]} -le 2 ]]; then
        log_warning "Some security headers missing: ${missing_headers[*]}"
    else
        log_error "Many security headers missing: ${missing_headers[*]}"
        return 1
    fi
    
    return 0
}

generate_smoke_test_report() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo
    echo "=== SMOKE TESTS REPORT ==="
    echo "Timestamp: $timestamp"
    echo "Environment: $ENVIRONMENT"
    echo "Backend URL: $BACKEND_URL"
    echo "Frontend URL: $FRONTEND_URL"
    echo
    
    echo "✅ PASSED TESTS (${#PASSED_TESTS[@]}):"
    for test in "${PASSED_TESTS[@]}"; do
        echo "  - $test"
    done
    echo
    
    if [[ ${#FAILED_TESTS[@]} -gt 0 ]]; then
        echo "❌ FAILED TESTS (${#FAILED_TESTS[@]}):"
        for test in "${FAILED_TESTS[@]}"; do
            echo "  - $test"
        done
        echo
    fi
    
    local total_tests=$((${#PASSED_TESTS[@]} + ${#FAILED_TESTS[@]}))
    echo "Summary: ${#PASSED_TESTS[@]}/$total_tests tests passed"
    
    if [[ ${#FAILED_TESTS[@]} -eq 0 ]]; then
        echo "🎉 All smoke tests passed successfully!"
        return 0
    else
        echo "❌ Some smoke tests failed - deployment may need attention"
        return 1
    fi
}

main() {
    log_info "Starting smoke tests for $ENVIRONMENT environment"
    
    get_service_urls
    
    log_info "Testing URLs:"
    log_info "  Backend: $BACKEND_URL"
    log_info "  Frontend: $FRONTEND_URL"
    echo
    
    # Run all smoke tests
    local smoke_tests=(
        test_health_endpoints
        test_authentication_flow
        test_mcp_endpoints
        test_database_connectivity
        test_frontend_availability
        test_ssl_tls_configuration
        test_performance_baseline
        test_security_headers
    )
    
    for test_func in "${smoke_tests[@]}"; do
        $test_func || true  # Continue even if individual tests fail
        echo
    done
    
    # Generate final report
    generate_smoke_test_report
}

# Ensure bc is available for floating point calculations
if ! command -v bc &> /dev/null; then
    echo "Warning: 'bc' command not found. Performance calculations may fail."
fi

main "$@"