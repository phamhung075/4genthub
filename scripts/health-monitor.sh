#!/bin/bash
# 4genthub Health Monitoring System
# Comprehensive system health monitoring with alerting capabilities
# Version: 2.1.0 - Phase 6 Production Monitoring

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
LOG_FILE="${PROJECT_ROOT}/logs/health-monitor.log"
ALERT_FILE="${PROJECT_ROOT}/logs/health-alerts.log"
STATUS_FILE="${PROJECT_ROOT}/logs/system-status.json"

# Default endpoints and timeouts
BACKEND_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3800"
DB_CONTAINER="4genthub-postgres"
TIMEOUT=10
CHECK_INTERVAL=60
ALERT_COOLDOWN=300  # 5 minutes

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RESET='\033[0m'
BOLD='\033[1m'

# Ensure log directories exist
mkdir -p "$(dirname "$LOG_FILE")" "$(dirname "$ALERT_FILE")" "$(dirname "$STATUS_FILE")"

# Logging functions
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${RESET} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${RESET} $1" | tee -a "$LOG_FILE" "$ALERT_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${RESET} $1" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${RESET} $1" | tee -a "$LOG_FILE"
}

# Health check functions
check_backend_health() {
    local url="${BACKEND_URL}/health"
    local status="healthy"
    local response_time=0
    local error_msg=""

    local start_time=$(date +%s.%N)

    if response=$(curl -s -f -m "$TIMEOUT" "$url" 2>&1); then
        local end_time=$(date +%s.%N)
        response_time=$(echo "$end_time - $start_time" | bc -l | xargs printf "%.3f")

        # Parse backend health response
        if echo "$response" | jq -e '.status == "healthy"' > /dev/null 2>&1; then
            local uptime=$(echo "$response" | jq -r '.connections.uptime_seconds // 0')
            local active_connections=$(echo "$response" | jq -r '.connections.active_connections // 0')
            local version=$(echo "$response" | jq -r '.version // "unknown"')

            log_info "Backend healthy - Version: $version, Uptime: ${uptime}s, Connections: $active_connections, Response: ${response_time}s"
        else
            status="degraded"
            error_msg="Unexpected health response format"
        fi
    else
        status="unhealthy"
        error_msg="Health check failed: $response"
        log_error "Backend health check failed: $error_msg"
    fi

    # Update status
    jq -n --arg status "$status" --arg response_time "$response_time" --arg error "$error_msg" --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" '{
        service: "backend",
        status: $status,
        response_time_ms: ($response_time | tonumber * 1000 | round),
        error: $error,
        timestamp: $timestamp,
        url: "'"$url"'"
    }' > /tmp/backend_status.json

    echo "$status"
}

check_frontend_health() {
    local url="$FRONTEND_URL"
    local status="healthy"
    local response_time=0
    local error_msg=""

    local start_time=$(date +%s.%N)

    if response=$(curl -s -f -m "$TIMEOUT" "$url" 2>&1); then
        local end_time=$(date +%s.%N)
        response_time=$(echo "$end_time - $start_time" | bc -l | xargs printf "%.3f")

        # Check if response contains expected content
        if echo "$response" | grep -q "4genthub" || echo "$response" | grep -q "vite" || echo "$response" | grep -q "<!DOCTYPE html>"; then
            log_info "Frontend healthy - Response: ${response_time}s"
        else
            status="degraded"
            error_msg="Unexpected response content"
        fi
    else
        status="unhealthy"
        error_msg="Frontend unreachable: $response"
        log_error "Frontend health check failed: $error_msg"
    fi

    # Update status
    jq -n --arg status "$status" --arg response_time "$response_time" --arg error "$error_msg" --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" '{
        service: "frontend",
        status: $status,
        response_time_ms: ($response_time | tonumber * 1000 | round),
        error: $error,
        timestamp: $timestamp,
        url: "'"$url"'"
    }' > /tmp/frontend_status.json

    echo "$status"
}

check_database_health() {
    local status="healthy"
    local error_msg=""
    local connection_count=0

    if docker exec "$DB_CONTAINER" pg_isready -U "${DATABASE_USER:-4genthub_user}" -d "${DATABASE_NAME:-4genthub}" > /dev/null 2>&1; then
        # Get additional database metrics
        if connection_count=$(docker exec "$DB_CONTAINER" psql -U "${DATABASE_USER:-4genthub_user}" -d "${DATABASE_NAME:-4genthub}" -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | xargs); then
            log_info "Database healthy - Active connections: $connection_count"
        else
            connection_count=0
        fi
    else
        status="unhealthy"
        error_msg="Database connection failed"
        log_error "Database health check failed: $error_msg"
    fi

    # Update status
    jq -n --arg status "$status" --arg connections "$connection_count" --arg error "$error_msg" --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" '{
        service: "database",
        status: $status,
        active_connections: ($connections | tonumber),
        error: $error,
        timestamp: $timestamp,
        container: "'"$DB_CONTAINER"'"
    }' > /tmp/database_status.json

    echo "$status"
}

check_docker_resources() {
    local status="healthy"
    local error_msg=""
    local warnings=()

    # Check Docker daemon
    if ! docker info > /dev/null 2>&1; then
        status="unhealthy"
        error_msg="Docker daemon not running"
        log_error "Docker daemon health check failed"
        echo "$status"
        return 1
    fi

    # Get resource usage
    local disk_usage=$(docker system df --format "table {{.Type}}\t{{.TotalCount}}\t{{.Size}}" | tail -n +2)
    local container_stats=$(docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null || echo "Stats unavailable")

    # Check for high resource usage
    if echo "$disk_usage" | grep -q "GB"; then
        local total_size=$(echo "$disk_usage" | awk '/Images/ {print $3}' | sed 's/GB//' | head -1)
        if (( $(echo "$total_size > 10" | bc -l) )); then
            warnings+=("High disk usage: ${total_size}GB")
        fi
    fi

    # Update status
    jq -n --arg status "$status" --arg error "$error_msg" --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --argjson warnings "$(printf '%s\n' "${warnings[@]}" | jq -R . | jq -s .)" '{
        service: "docker",
        status: $status,
        error: $error,
        warnings: $warnings,
        timestamp: $timestamp
    }' > /tmp/docker_status.json

    log_info "Docker resources healthy"
    echo "$status"
}

check_system_resources() {
    local status="healthy"
    local warnings=()

    # Check memory usage
    local mem_usage=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
    if (( mem_usage > 85 )); then
        warnings+=("High memory usage: ${mem_usage}%")
        status="degraded"
    fi

    # Check disk usage
    local disk_usage=$(df / | tail -1 | awk '{print int($3/$2 * 100)}')
    if (( disk_usage > 80 )); then
        warnings+=("High disk usage: ${disk_usage}%")
        if (( disk_usage > 90 )); then
            status="degraded"
        fi
    fi

    # Check load average
    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',')
    local cpu_cores=$(nproc)
    if (( $(echo "$load_avg > $cpu_cores * 1.5" | bc -l) )); then
        warnings+=("High system load: ${load_avg} (cores: ${cpu_cores})")
        status="degraded"
    fi

    # Update status
    jq -n --arg status "$status" --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --arg mem_usage "$mem_usage" --arg disk_usage "$disk_usage" --arg load_avg "$load_avg" --argjson warnings "$(printf '%s\n' "${warnings[@]}" | jq -R . | jq -s .)" '{
        service: "system",
        status: $status,
        memory_usage_percent: ($mem_usage | tonumber),
        disk_usage_percent: ($disk_usage | tonumber),
        load_average: ($load_avg | tonumber),
        warnings: $warnings,
        timestamp: $timestamp
    }' > /tmp/system_status.json

    if [[ ${#warnings[@]} -gt 0 ]]; then
        log_warning "System resources degraded: $(IFS=', '; echo "${warnings[*]}")"
    else
        log_info "System resources healthy - Memory: ${mem_usage}%, Disk: ${disk_usage}%, Load: $load_avg"
    fi

    echo "$status"
}

# Comprehensive health check
run_health_checks() {
    log_info "Starting comprehensive health check..."

    local overall_status="healthy"
    local failed_services=()
    local degraded_services=()

    # Check all services
    local backend_status=$(check_backend_health)
    local frontend_status=$(check_frontend_health)
    local database_status=$(check_database_health)
    local docker_status=$(check_docker_resources)
    local system_status=$(check_system_resources)

    # Aggregate results
    for service_status in "$backend_status" "$frontend_status" "$database_status" "$docker_status" "$system_status"; do
        case "$service_status" in
            "unhealthy")
                overall_status="unhealthy"
                failed_services+=("$service_status")
                ;;
            "degraded")
                if [[ "$overall_status" != "unhealthy" ]]; then
                    overall_status="degraded"
                fi
                degraded_services+=("$service_status")
                ;;
        esac
    done

    # Combine all status files
    jq -s '{
        timestamp: (.[0].timestamp // (now | strftime("%Y-%m-%dT%H:%M:%SZ"))),
        overall_status: "'"$overall_status"'",
        services: {
            backend: .[0],
            frontend: .[1],
            database: .[2],
            docker: .[3],
            system: .[4]
        }
    }' /tmp/backend_status.json /tmp/frontend_status.json /tmp/database_status.json /tmp/docker_status.json /tmp/system_status.json > "$STATUS_FILE"

    # Cleanup temp files
    rm -f /tmp/*_status.json

    # Log overall status
    case "$overall_status" in
        "healthy")
            log "✅ All systems healthy"
            ;;
        "degraded")
            log_warning "⚠️ System degraded - Services: $(IFS=', '; echo "${degraded_services[*]}")"
            ;;
        "unhealthy")
            log_error "❌ System unhealthy - Failed services: $(IFS=', '; echo "${failed_services[*]}")"
            ;;
    esac
}

# Monitoring loop
monitor_continuous() {
    log_info "Starting continuous monitoring (interval: ${CHECK_INTERVAL}s)"

    while true; do
        run_health_checks

        # Wait for next check
        sleep "$CHECK_INTERVAL"
    done
}

# Status display
show_status() {
    if [[ ! -f "$STATUS_FILE" ]]; then
        echo -e "${RED}❌ No status file found. Run health check first.${RESET}"
        return 1
    fi

    echo -e "\n${BOLD}${BLUE}=== 4genthub System Status ===${RESET}"
    echo -e "${BLUE}================================${RESET}\n"

    local overall_status=$(jq -r '.overall_status' "$STATUS_FILE")
    local timestamp=$(jq -r '.timestamp' "$STATUS_FILE")

    case "$overall_status" in
        "healthy")
            echo -e "Overall Status: ${GREEN}✅ HEALTHY${RESET}"
            ;;
        "degraded")
            echo -e "Overall Status: ${YELLOW}⚠️ DEGRADED${RESET}"
            ;;
        "unhealthy")
            echo -e "Overall Status: ${RED}❌ UNHEALTHY${RESET}"
            ;;
    esac

    echo -e "Last Check: $timestamp\n"

    # Display service status
    echo -e "${BOLD}Service Health:${RESET}"

    jq -r '.services | to_entries[] | "\(.key): \(.value.status)"' "$STATUS_FILE" | while read -r line; do
        service=$(echo "$line" | cut -d: -f1)
        status=$(echo "$line" | cut -d: -f2 | xargs)

        case "$status" in
            "healthy")
                echo -e "  ${service}: ${GREEN}✅ Healthy${RESET}"
                ;;
            "degraded")
                echo -e "  ${service}: ${YELLOW}⚠️ Degraded${RESET}"
                ;;
            "unhealthy")
                echo -e "  ${service}: ${RED}❌ Unhealthy${RESET}"
                ;;
        esac
    done

    echo -e "\n${BOLD}Recent Alerts:${RESET}"
    if [[ -f "$ALERT_FILE" ]]; then
        tail -n 5 "$ALERT_FILE" | sed 's/^/  /'
    else
        echo "  No recent alerts"
    fi
}

# Main execution
main() {
    case "${1:-}" in
        "monitor"|"continuous")
            monitor_continuous
            ;;
        "check"|"once")
            run_health_checks
            ;;
        "status"|"show")
            show_status
            ;;
        "help"|"-h"|"--help")
            echo "Usage: $0 [COMMAND]"
            echo ""
            echo "Commands:"
            echo "  monitor, continuous  Start continuous monitoring"
            echo "  check, once         Run health check once"
            echo "  status, show        Show current system status"
            echo "  help                Show this help"
            echo ""
            exit 0
            ;;
        "")
            show_status
            ;;
        *)
            echo "Unknown command: $1"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Handle signals for graceful shutdown
trap 'log_info "Health monitor stopped"; exit 0' INT TERM

# Execute main function
main "$@"