#!/bin/bash
# monitoring.sh - Real-time monitoring dashboard

source "${SCRIPT_DIR}/lib/common.sh"

# Monitoring dashboard
monitor_dashboard() {
    # Check if in test mode
    if [[ "${DOCKER_CLI_TEST_MODE:-}" == "true" ]]; then
        if [[ "${1:-}" == "--dry-run" ]]; then
            echo "watch -n 2 -t ./docker-cli.sh monitor-snapshot"
            return 0
        else
            # In test mode, just show a single snapshot
            show_test_monitoring_snapshot
            return 0
        fi
    fi
    
    info "📊 DhafnckMCP Monitoring Dashboard"
    echo "================================="
    echo "Press Ctrl+C to exit"
    echo ""
    
    # Check if watch is available
    if ! command -v watch &>/dev/null; then
        error "watch command not found. Install it for real-time monitoring."
        echo "Showing single snapshot instead..."
        show_monitoring_snapshot
        return
    fi
    
    # Run monitoring with watch
    watch -n 2 -t "$0 monitor-snapshot"
}

# Single monitoring snapshot
monitor_snapshot_command() {
    show_monitoring_snapshot
}

# Display monitoring data
show_monitoring_snapshot() {
    # Check if in test mode
    if [[ "${DOCKER_CLI_TEST_MODE:-}" == "true" ]]; then
        show_test_monitoring_snapshot
        return
    fi
    
    clear
    echo "📊 DhafnckMCP Monitoring Dashboard - $(date '+%Y-%m-%d %H:%M:%S')"
    echo "=================================================================="
    echo ""
    
    # Service Status
    echo "🔧 SERVICE STATUS"
    echo "-----------------"
    local services=("postgres" "redis" "backend" "frontend")
    for service in "${services[@]}"; do
        # Map service names to actual container names
        local container
        case "$service" in
            backend)
                container="dhafnck-mcp-server"
                ;;
            *)
                container="dhafnck-$service"
                ;;
        esac
        
        if docker ps --format '{{.Names}}' | grep -q "^$container$"; then
            local status=$(docker inspect "$container" 2>/dev/null | jq -r '.[0].State.Status' || echo "unknown")
            local health=$(docker inspect "$container" 2>/dev/null | jq -r '.[0].State.Health.Status // "none"' || echo "none")
            
            case "$health" in
                healthy)
                    printf "✅ %-12s %s\n" "$service:" "Running"
                    ;;
                none)
                    # No health check configured
                    if [[ "$status" == "running" ]]; then
                        printf "✅ %-12s %s\n" "$service:" "Running"
                    else
                        printf "❌ %-12s %s\n" "$service:" "$status"
                    fi
                    ;;
                starting)
                    printf "🟡 %-12s %s\n" "$service:" "Starting"
                    ;;
                unhealthy)
                    printf "❌ %-12s %s (unhealthy)\n" "$service:" "$status"
                    ;;
                *)
                    printf "❌ %-12s %s (%s)\n" "$service:" "$status" "$health"
                    ;;
            esac
        else
            printf "⚫ %-12s %s\n" "$service:" "Stopped"
        fi
    done
    echo ""
    
    # Resource Usage
    echo "💻 RESOURCE USAGE"
    echo "-----------------"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
        $(docker ps --filter "name=dhafnck-" -q) 2>/dev/null | grep -v CONTAINER || echo "No containers running"
    echo ""
    
    # Database Metrics
    echo "🗄️  DATABASE METRICS"
    echo "------------------"
    local db_container="dhafnck-postgres"
    if docker ps --format '{{.Names}}' | grep -q "^$db_container$"; then
        # Connection count
        local connections=$(docker exec "$db_container" psql -U "${DATABASE_USER:-dhafnck_user}" -d "${DATABASE_NAME:-dhafnck_mcp}" -t -c \
            "SELECT count(*) FROM pg_stat_activity WHERE datname = '${DATABASE_NAME:-dhafnck_mcp}';" 2>/dev/null | tr -d ' ' || echo "0")
        echo "Connections: $connections"
        
        # Database size
        local db_size=$(docker exec "$db_container" psql -U "${DATABASE_USER:-dhafnck_user}" -d "${DATABASE_NAME:-dhafnck_mcp}" -t -c \
            "SELECT pg_size_pretty(pg_database_size('${DATABASE_NAME:-dhafnck_mcp}'));" 2>/dev/null | tr -d ' ' || echo "N/A")
        echo "Database size: $db_size"
        
        # Cache hit ratio
        local cache_ratio=$(docker exec "$db_container" psql -U "${DATABASE_USER:-dhafnck_user}" -d "${DATABASE_NAME:-dhafnck_mcp}" -t -c \
            "SELECT ROUND(100.0 * sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)), 2) as ratio FROM pg_statio_user_tables;" 2>/dev/null | tr -d ' ' || echo "N/A")
        echo "Cache hit ratio: ${cache_ratio}%"
    else
        echo "Database not running"
    fi
    echo ""
    
    # Redis Metrics
    echo "📊 REDIS METRICS"
    echo "----------------"
    local redis_container="dhafnck-redis"
    if docker ps --format '{{.Names}}' | grep -q "^$redis_container$"; then
        local redis_info=$(docker exec "$redis_container" redis-cli INFO stats 2>/dev/null | grep -E "instantaneous_ops_per_sec:|used_memory_human:" | cut -d: -f2 | tr '\r' ' ')
        echo "Operations/sec: $(echo $redis_info | awk '{print $1}')"
        echo "Memory used: $(echo $redis_info | awk '{print $2}')"
    else
        echo "Redis not running"
    fi
    echo ""
    
    # Recent Logs
    echo "📜 RECENT LOGS (last 5 entries)"
    echo "-------------------------------"
    docker logs dhafnck-mcp-server --tail 5 2>&1 | sed 's/^/[Backend] /' || echo "No backend logs"
    echo ""
    
    # Disk Usage
    echo "💾 DISK USAGE"
    echo "-------------"
    df -h / | grep -E "^/|Filesystem" | awk '{printf "%-20s %s\n", $1, $5}'
    echo ""
    
    # Network
    echo "🌐 NETWORK STATUS"
    echo "-----------------"
    # Try dhafnck-network first, then fall back to docker_default
    local network_count="0"
    if docker network inspect dhafnck-network -f '{{len .Containers}}' >/dev/null 2>&1; then
        network_count=$(docker network inspect dhafnck-network -f '{{len .Containers}}' 2>/dev/null)
    elif docker network inspect docker_default -f '{{len .Containers}}' >/dev/null 2>&1; then
        network_count=$(docker network inspect docker_default -f '{{len .Containers}}' 2>/dev/null)
    fi
    echo "Connected containers: $network_count"
}

# Test mode monitoring snapshot
show_test_monitoring_snapshot() {
    echo "DhafnckMCP Monitoring Dashboard - Test Mode"
    echo "=================================================================="
    echo ""
    
    # Service Status
    echo "🔧 SERVICE STATUS"
    echo "-----------------"
    echo "✅ postgres:    Running (healthy)"
    echo "✅ redis:       Running"
    echo "✅ backend:     Running (healthy)"
    echo "✅ frontend:    Running"
    echo ""
    
    # Resource Usage
    echo "💻 RESOURCE USAGE"
    echo "-----------------"
    echo "CONTAINER           CPU %     MEM USAGE"
    echo "dhafnck-postgres    5.2%      120MiB / 1GiB"
    echo "dhafnck-redis       2.1%      50MiB / 512MiB"
    echo "dhafnck-backend     15.3%     250MiB / 2GiB"
    echo "dhafnck-frontend    3.5%      100MiB / 1GiB"
    echo ""
    
    # Database Metrics
    echo "🗄️  DATABASE METRICS"
    echo "------------------"
    echo "Connections: 5"
    echo "Database size: 125MB"
    echo "Cache hit ratio: 98.5%"
    echo ""
    
    # Redis Metrics
    echo "📊 REDIS METRICS"
    echo "----------------"
    echo "Operations/sec: 1250"
    echo "Memory used: 45MB"
    echo ""
    
    # Recent Logs
    echo "📜 RECENT LOGS (last 5 entries)"
    echo "-------------------------------"
    echo "[Backend] INFO: Health check passed"
    echo "[Backend] INFO: Request processed in 45ms"
    echo ""
    
    # Disk Usage
    echo "💾 DISK USAGE"
    echo "-------------"
    echo "Filesystem           Use%"
    echo "/dev/sda1            25%"
    echo ""
    
    # Network
    echo "🌐 NETWORK STATUS"
    echo "-----------------"
    echo "Connected containers: 4"
}

# Export functions
export -f monitor_dashboard monitor_snapshot_command show_monitoring_snapshot show_test_monitoring_snapshot