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
declare -a WARNING_TESTS=()
declare -a SKIPPED_TESTS=()

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    PASSED_TESTS+=("$1")
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    WARNING_TESTS+=("$1")
}

log_skip() {
    echo -e "${BLUE}[SKIP]${NC} $1"
    SKIPPED_TESTS+=("$1")
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
    if make_api_request "GET" "/health" "" "200" > /dev/null; then
        log_success "Backend health endpoint responding"
    else
        log_error "Backend health endpoint failed"
        return 1
    fi

    # Authentication provider config (the real auth mount; /api/v2/auth/status does not exist)
    if make_api_request "GET" "/api/auth/provider" "" "200" > /dev/null; then
        log_success "Authentication provider endpoint responding"
    else
        log_error "Authentication provider endpoint failed"
        return 1
    fi

    return 0
}

test_authentication_flow() {
    log_info "Testing authentication flow..."

    # Test token validation endpoint (POST only; the token is a query parameter and an
    # invalid one must be rejected with 401)
    if make_api_request "POST" "/api/v2/tokens/validate?token=probe" "" "401" > /dev/null; then
        log_success "Token validation properly rejects invalid tokens"
    else
        log_error "Token validation endpoint not properly secured"
        return 1
    fi

    # Credential rejection: an invalid login must be rejected. With a reachable
    # identity provider the handler maps an upstream 401 (or a 400 "invalid_grant")
    # to HTTP 401 "Invalid credentials"; with none reachable it answers 503. A 503
    # is not a credential-rejection verdict, so it is recorded as not verified
    # rather than passed. The old expectation of 400 was wrong on every path this
    # JSON probe can take, so it failed on healthy deployments.
    log_info "Testing credential rejection on authentication..."
    local login_code
    login_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" \
        -d '{"email":"test@example.com","password":"invalid"}' --max-time "$TIMEOUT" \
        "$BACKEND_URL/api/auth/login" 2>/dev/null || echo "000")

    case "$login_code" in
        401)
            log_success "Login rejects invalid credentials (HTTP 401)"
            ;;
        503)
            log_skip "Credential rejection not verified: no identity provider reachable (HTTP 503)"
            ;;
        000)
            log_error "Login endpoint not accessible (connection failed)"
            return 1
            ;;
        *)
            log_error "Login returned HTTP $login_code for invalid credentials (expected 401)"
            return 1
            ;;
    esac

    # Rate limiting on the login surface is NOT asserted here. The Go server mounts
    # only CORS middleware (httpapp/app.go Handler returns withCORS(mux)); it has no
    # HTTP rate limiter, and the RateLimit* symbols elsewhere in the API are
    # per-token metadata (server/routes/token_router.go), not request throttling.
    # A proxy or ingress in front of the server could rate limit, but that is not
    # observable from this script, so the property is recorded as not verified -
    # never as "rate limiting is functional". The previous loop inferred rate
    # limiting from its own failed 400 expectation (i>10), which passed on healthy
    # deployments that never rate limited anything.
    log_skip "Authentication rate limiting not verified: no server-side HTTP rate limiter is observable from this script"

    return 0
}

test_mcp_endpoints() {
    log_info "Testing MCP endpoints..."

    # Test project endpoints (should require authentication; the Go server answers 403
    # "Not authenticated" when the bearer header is missing)
    if make_api_request "GET" "/api/v2/projects/" "" "403" > /dev/null; then
        log_success "Projects endpoint properly secured"
    else
        log_error "Projects endpoint security issue"
        return 1
    fi

    # Test task endpoints (should require authentication)
    if make_api_request "GET" "/api/v2/tasks/" "" "403" > /dev/null; then
        log_success "Tasks endpoint properly secured"
    else
        log_error "Tasks endpoint security issue"
        return 1
    fi

    # Test branch endpoints (should require authentication). There is no GET collection
    # mount for branches; POST /api/v2/branches/ is the real collection route.
    if make_api_request "POST" "/api/v2/branches/" "{}" "403" > /dev/null; then
        log_success "Branches endpoint properly secured"
    else
        log_error "Branches endpoint security issue"
        return 1
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
            log_error "Static asset returned unexpected status: $url (HTTP $response_code)"
            return 1
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
                    log_error "SSL certificate validation issues detected"
                    return 1
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
        "/health"
        "/api/auth/provider"
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
    headers_output=$(curl -I -s --max-time "$TIMEOUT" "$BACKEND_URL/health" 2>/dev/null || echo "")

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

    if [[ ${#SKIPPED_TESTS[@]} -gt 0 ]]; then
        echo "⏭️  NOT VERIFIED TESTS (${#SKIPPED_TESTS[@]}):"
        for test in "${SKIPPED_TESTS[@]}"; do
            echo "  - $test"
        done
        echo
    fi

    if [[ ${#WARNING_TESTS[@]} -gt 0 ]]; then
        echo "⚠️  WARNING TESTS (${#WARNING_TESTS[@]}):"
        for test in "${WARNING_TESTS[@]}"; do
            echo "  - $test"
        done
        echo
    fi

    local total_tests=$((${#PASSED_TESTS[@]} + ${#FAILED_TESTS[@]}))
    echo "Summary: ${#PASSED_TESTS[@]}/$total_tests tests passed"

    if [[ ${#FAILED_TESTS[@]} -eq 0 ]]; then
        if [[ ${#SKIPPED_TESTS[@]} -eq 0 && ${#WARNING_TESTS[@]} -eq 0 ]]; then
            echo "🎉 All smoke tests passed successfully!"
        else
            echo "⚠️  All executed smoke tests passed; ${#SKIPPED_TESTS[@]} test(s) not verified and ${#WARNING_TESTS[@]} warning(s) require review"
        fi
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
