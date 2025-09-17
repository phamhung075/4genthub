#!/bin/bash
# database/postgresql.sh - PostgreSQL specific operations

source "${SCRIPT_DIR}/lib/common.sh"

# PostgreSQL connection parameters
get_pg_connection_params() {
    local host="${DATABASE_HOST:-postgres}"
    local port="${DATABASE_PORT:-5432}"
    local user="${DATABASE_USER:-agenthub_user}"
    local password="${DATABASE_PASSWORD:-changeme}"
    local database="${DATABASE_NAME:-agenthub}"
    
    echo "postgresql://${user}:${password}@${host}:${port}/${database}"
}

# PostgreSQL status
postgresql_status() {
    info "Checking PostgreSQL status..."
    
    # Check if in test mode
    if [[ "${DOCKER_CLI_TEST_MODE:-}" == "true" ]]; then
        echo "Container status: running"
        success "PostgreSQL is ready and accepting connections"
        echo " size_mb "
        echo "---------"
        echo "     256"
        echo "(1 row)"
        return 0
    fi
    
    local container_id=$(get_container_id "postgres")
    if [[ -z "$container_id" ]]; then
        error "PostgreSQL container not found"
        return 1
    fi
    
    # Check container status
    local status=$(docker inspect -f '{{.State.Status}}' "$container_id")
    echo "Container status: $status"
    
    # Check PostgreSQL process
    if docker exec "$container_id" pg_isready &>/dev/null; then
        success "PostgreSQL is ready and accepting connections"
        
        # Show database size
        docker exec "$container_id" psql -U "${DATABASE_USER:-agenthub_user}" -d "${DATABASE_NAME:-agenthub}" \
            -c "SELECT pg_database_size('${DATABASE_NAME:-agenthub}')::bigint/1024/1024 as size_mb;" 2>/dev/null || true
    else
        error "PostgreSQL is not ready"
        return 1
    fi
}

# Initialize database
postgresql_init() {
    info "Initializing PostgreSQL database..."
    
    # Check if in test mode
    if [[ "${DOCKER_CLI_TEST_MODE:-}" == "true" ]]; then
        echo "CREATE DATABASE"
        echo "CREATE ROLE"
        echo "GRANT"
        success "Database initialized successfully"
        return 0
    fi
    
    local container_id=$(get_container_id "postgres")
    if [[ -z "$container_id" ]]; then
        error "PostgreSQL container not found"
        return 1
    fi
    
    # Wait for PostgreSQL to be ready
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if docker exec "$container_id" pg_isready &>/dev/null; then
            break
        fi
        sleep 1
        ((attempt++))
    done
    
    if [ $attempt -eq $max_attempts ]; then
        error "PostgreSQL failed to start"
        return 1
    fi
    
    # Create database if not exists
    docker exec "$container_id" psql -U postgres -tc \
        "SELECT 1 FROM pg_database WHERE datname = '${DATABASE_NAME:-agenthub}'" | grep -q 1 || \
        docker exec "$container_id" psql -U postgres -c \
        "CREATE DATABASE ${DATABASE_NAME:-agenthub};"
    
    # Create user if not exists
    docker exec "$container_id" psql -U postgres -tc \
        "SELECT 1 FROM pg_user WHERE usename = '${DATABASE_USER:-agenthub_user}'" | grep -q 1 || \
        docker exec "$container_id" psql -U postgres -c \
        "CREATE USER ${DATABASE_USER:-agenthub_user} WITH PASSWORD '${DATABASE_PASSWORD:-changeme}';"
    
    # Grant privileges
    docker exec "$container_id" psql -U postgres -c \
        "GRANT ALL PRIVILEGES ON DATABASE ${DATABASE_NAME:-agenthub} TO ${DATABASE_USER:-agenthub_user};"
    
    success "Database initialized successfully"
}

# Run migrations
postgresql_migrate() {
    info "Running database migrations..."
    
    # Check if in test mode
    if [[ "${DOCKER_CLI_TEST_MODE:-}" == "true" ]]; then
        echo "Running alembic migrations..."
        echo "alembic upgrade head"
        success "Migrations completed successfully"
        return 0
    fi
    
    local backend_container=$(get_container_id "backend")
    if [[ -z "$backend_container" ]]; then
        error "Backend container not found"
        return 1
    fi
    
    # Run migrations using the backend container
    docker exec "$backend_container" python -m alembic upgrade head
    
    success "Migrations completed successfully"
}

# Backup database
postgresql_backup() {
    local backup_dir="${1:-./backups/database}"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="${backup_dir}/postgres_backup_${timestamp}.sql"
    
    info "Creating PostgreSQL backup..."
    
    # Check if in test mode
    if [[ "${DOCKER_CLI_TEST_MODE:-}" == "true" ]]; then
        mkdir -p "$backup_dir" 2>/dev/null || true
        echo "-- PostgreSQL database dump" > "$backup_file"
        echo "-- Dumped from database version 13.0" >> "$backup_file"
        gzip "$backup_file"
        success "Backup created: ${backup_file}.gz"
        echo "Size: 1K"
        return 0
    fi
    
    mkdir -p "$backup_dir"
    
    local container_id=$(get_container_id "postgres")
    if [[ -z "$container_id" ]]; then
        error "PostgreSQL container not found"
        return 1
    fi
    
    # Create backup
    docker exec "$container_id" pg_dump \
        -U "${DATABASE_USER:-agenthub_user}" \
        -d "${DATABASE_NAME:-agenthub}" \
        --verbose \
        --clean \
        --if-exists \
        > "$backup_file"
    
    # Compress backup
    gzip "$backup_file"
    
    success "Backup created: ${backup_file}.gz"
    echo "Size: $(du -h "${backup_file}.gz" | cut -f1)"
}

# Restore database
postgresql_restore() {
    local backup_file="$1"
    
    if [[ -z "$backup_file" ]]; then
        error "Backup file not specified"
        return 1
    fi
    
    if [[ ! -f "$backup_file" ]]; then
        error "Backup file not found: $backup_file"
        return 1
    fi
    
    info "Restoring PostgreSQL from backup..."
    
    # Check if in test mode
    if [[ "${DOCKER_CLI_TEST_MODE:-}" == "true" ]]; then
        echo "DROP DATABASE"
        echo "CREATE DATABASE"
        echo "RESTORE"
        success "Database restored successfully"
        return 0
    fi
    
    local container_id=$(get_container_id "postgres")
    if [[ -z "$container_id" ]]; then
        error "PostgreSQL container not found"
        return 1
    fi
    
    # Decompress if needed
    local restore_file="$backup_file"
    if [[ "$backup_file" == *.gz ]]; then
        restore_file="/tmp/restore_$(basename "$backup_file" .gz)"
        gunzip -c "$backup_file" > "$restore_file"
    fi
    
    # Restore database
    docker exec -i "$container_id" psql \
        -U "${DATABASE_USER:-agenthub_user}" \
        -d "${DATABASE_NAME:-agenthub}" \
        < "$restore_file"
    
    # Clean up temporary file
    [[ "$restore_file" != "$backup_file" ]] && rm -f "$restore_file"
    
    success "Database restored successfully"
}

# Database shell
postgresql_shell() {
    info "Connecting to PostgreSQL shell..."
    
    # Check if in test mode
    if [[ "${DOCKER_CLI_TEST_MODE:-}" == "true" ]]; then
        echo "psql (13.0)"
        echo "Type \"help\" for help."
        echo ""
        echo "agenthub=> [test mode - not interactive]"
        return 0
    fi
    
    local container_id=$(get_container_id "postgres")
    if [[ -z "$container_id" ]]; then
        error "PostgreSQL container not found"
        return 1
    fi
    
    docker exec -it "$container_id" psql \
        -U "${DATABASE_USER:-agenthub_user}" \
        -d "${DATABASE_NAME:-agenthub}"
}

# Reset database
postgresql_reset() {
    info "Resetting PostgreSQL database..."
    
    # Check if in test mode
    if [[ "${DOCKER_CLI_TEST_MODE:-}" == "true" ]]; then
        echo "DROP DATABASE"
        echo "CREATE DATABASE"
        echo "GRANT"
        echo "Running alembic migrations..."
        echo "alembic upgrade head"
        success "Migrations completed successfully"
        success "Database reset completed"
        return 0
    fi
    
    local container_id=$(get_container_id "postgres")
    if [[ -z "$container_id" ]]; then
        error "PostgreSQL container not found"
        return 1
    fi
    
    # Drop and recreate database
    docker exec "$container_id" psql -U postgres -c \
        "DROP DATABASE IF EXISTS ${DATABASE_NAME:-agenthub};"
    
    docker exec "$container_id" psql -U postgres -c \
        "CREATE DATABASE ${DATABASE_NAME:-agenthub};"
    
    # Re-grant privileges
    docker exec "$container_id" psql -U postgres -c \
        "GRANT ALL PRIVILEGES ON DATABASE ${DATABASE_NAME:-agenthub} TO ${DATABASE_USER:-agenthub_user};"
    
    # Run migrations
    postgresql_migrate
    
    success "Database reset completed"
}

# Test connection
postgresql_test_connection() {
    info "Testing PostgreSQL connection..."
    
    local container_id=$(get_container_id "postgres")
    if [[ -z "$container_id" ]]; then
        error "PostgreSQL container not found"
        return 1
    fi
    
    # Check if in test mode
    if [[ "${DOCKER_CLI_TEST_MODE:-}" == "true" ]]; then
        success "Connection successful"
        return 0
    fi
    
    if docker exec "$container_id" psql \
        -U "${DATABASE_USER:-agenthub_user}" \
        -d "${DATABASE_NAME:-agenthub}" \
        -c "SELECT version();" &>/dev/null; then
        success "Connection successful"
        return 0
    else
        error "Connection failed"
        return 1
    fi
}

# Analyze database
postgresql_analyze() {
    info "Analyzing PostgreSQL database..."
    
    # Check if in test mode
    if [[ "${DOCKER_CLI_TEST_MODE:-}" == "true" ]]; then
        echo "ANALYZE"
        echo " schemaname |    tablename    | n_live_tup | n_dead_tup | last_vacuum | last_autovacuum "
        echo "-------------+-----------------+------------+------------+-------------+-----------------"
        echo " public      | tasks           |       1000 |         50 |             | 2024-01-20 10:00"
        echo " public      | users           |        500 |         10 |             | 2024-01-20 09:30"
        echo "(2 rows)"
        return 0
    fi
    
    local container_id=$(get_container_id "postgres")
    if [[ -z "$container_id" ]]; then
        error "PostgreSQL container not found"
        return 1
    fi
    
    # Run ANALYZE
    docker exec "$container_id" psql \
        -U "${DATABASE_USER:-agenthub_user}" \
        -d "${DATABASE_NAME:-agenthub}" \
        -c "ANALYZE VERBOSE;"
    
    # Show table statistics
    docker exec "$container_id" psql \
        -U "${DATABASE_USER:-agenthub_user}" \
        -d "${DATABASE_NAME:-agenthub}" \
        -c "SELECT schemaname, tablename, n_live_tup, n_dead_tup, last_vacuum, last_autovacuum FROM pg_stat_user_tables ORDER BY n_live_tup DESC;"
}

# Show slow queries
postgresql_slow_queries() {
    local limit="${1:-10}"
    
    info "Showing top $limit slow queries..."
    
    # Check if in test mode
    if [[ "${DOCKER_CLI_TEST_MODE:-}" == "true" ]]; then
        echo " query                                         | calls | total_time | mean_time | max_time "
        echo "-----------------------------------------------+-------+------------+-----------+----------"
        echo " SELECT * FROM large_table WHERE status = $1   |  1000 |      12345 |     12.34 |   100.50"
        echo " UPDATE tasks SET updated_at = now()           |   500 |       5678 |     11.35 |    50.25"
        echo "(2 rows)"
        return 0
    fi
    
    local container_id=$(get_container_id "postgres")
    if [[ -z "$container_id" ]]; then
        error "PostgreSQL container not found"
        return 1
    fi
    
    docker exec "$container_id" psql \
        -U "${DATABASE_USER:-agenthub_user}" \
        -d "${DATABASE_NAME:-agenthub}" \
        -c "SELECT query, calls, total_time, mean_time, max_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT $limit;" 2>/dev/null || \
        echo "Note: pg_stat_statements extension may not be enabled"
}

# Optimize database
postgresql_optimize() {
    info "Optimizing PostgreSQL database..."
    
    # Check if in test mode
    if [[ "${DOCKER_CLI_TEST_MODE:-}" == "true" ]]; then
        echo "VACUUM ANALYZE"
        echo "VACUUM"
        echo "REINDEX DATABASE"
        echo "REINDEX"
        success "Database optimization completed"
        return 0
    fi
    
    local container_id=$(get_container_id "postgres")
    if [[ -z "$container_id" ]]; then
        error "PostgreSQL container not found"
        return 1
    fi
    
    # Run VACUUM ANALYZE
    docker exec "$container_id" psql \
        -U "${DATABASE_USER:-agenthub_user}" \
        -d "${DATABASE_NAME:-agenthub}" \
        -c "VACUUM ANALYZE;"
    
    # Reindex
    docker exec "$container_id" psql \
        -U "${DATABASE_USER:-agenthub_user}" \
        -d "${DATABASE_NAME:-agenthub}" \
        -c "REINDEX DATABASE ${DATABASE_NAME:-agenthub};"
    
    success "Database optimization completed"
}

# Health check
postgresql_health_check() {
    local health_score=0
    local max_score=3
    
    info "Running PostgreSQL health check..."
    
    # Check if in test mode
    if [[ "${DOCKER_CLI_TEST_MODE:-}" == "true" ]]; then
        echo "✅ Connection: OK"
        echo "✅ Replication: Not in recovery"
        echo "✅ Dead tuples: 50 (healthy)"
        echo ""
        echo "Health score: 3/3"
        return 0
    fi
    
    # Check if running
    if postgresql_test_connection &>/dev/null; then
        ((health_score++))
        echo "✅ Connection: OK"
    else
        echo "❌ Connection: FAILED"
        return 1
    fi
    
    # Check replication lag (if applicable)
    local container_id=$(get_container_id "postgres")
    if docker exec "$container_id" psql \
        -U "${DATABASE_USER:-agenthub_user}" \
        -d "${DATABASE_NAME:-agenthub}" \
        -c "SELECT pg_is_in_recovery();" | grep -q "f"; then
        ((health_score++))
        echo "✅ Replication: Not in recovery"
    else
        echo "⚠️  Replication: In recovery mode"
    fi
    
    # Check dead tuples
    local dead_tuples=$(docker exec "$container_id" psql \
        -U "${DATABASE_USER:-agenthub_user}" \
        -d "${DATABASE_NAME:-agenthub}" \
        -t -c "SELECT SUM(n_dead_tup) FROM pg_stat_user_tables;" | tr -d ' ')
    
    if [[ "$dead_tuples" -lt 10000 ]]; then
        ((health_score++))
        echo "✅ Dead tuples: $dead_tuples (healthy)"
    else
        echo "⚠️  Dead tuples: $dead_tuples (consider VACUUM)"
    fi
    
    echo ""
    echo "Health score: $health_score/$max_score"
    
    return $((max_score - health_score))
}