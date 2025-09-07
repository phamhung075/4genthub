#!/bin/bash
# test_database_operations.sh - Tests for database operations

source "$(dirname "$0")/test_framework.sh"

describe "Database Operations"

# Test: DB init should initialize database
it "should initialize PostgreSQL database"
test_db_init() {
    # Setup
    mock_docker_exec "postgres" "psql -U postgres"
    
    # Execute
    output=$($DOCKER_CLI db init 2>&1)
    exit_code=$?
    
    # Assert
    assert_equals 0 $exit_code "DB init should exit with 0"
    assert_contains "$output" "Initializing PostgreSQL database" "Should show init message"
    assert_contains "$output" "Database initialized successfully" "Should show success message"
}

# Test: DB test-connection should verify connectivity
it "should test database connection"
test_db_connection() {
    # Setup
    mock_docker_exec "postgres" "pg_isready"
    
    # Execute
    output=$($DOCKER_CLI db test-connection 2>&1)
    exit_code=$?
    
    # Assert
    assert_equals 0 $exit_code "DB test-connection should exit with 0"
    assert_contains "$output" "Testing PostgreSQL connection" "Should show test message"
    assert_contains "$output" "Connection successful" "Should show success message"
}

# Test: DB backup should create backup
it "should create database backup"
test_db_backup() {
    # Setup
    local backup_dir="${SCRIPT_DIR}/backups"
    mkdir -p "$backup_dir"
    mock_docker_exec "postgres" "pg_dump"
    
    # Execute
    output=$($DOCKER_CLI db backup 2>&1)
    exit_code=$?
    
    # Assert
    assert_equals 0 $exit_code "DB backup should exit with 0"
    assert_contains "$output" "Creating PostgreSQL backup" "Should show backup message"
    assert_contains "$output" "Backup created" "Should show completion message"
    
    # Cleanup
    rm -rf "$backup_dir"
}

# Test: DB restore should restore from backup
it "should restore database from backup"
test_db_restore() {
    # Setup
    local backup_file="test_backup.sql"
    touch "$backup_file"
    mock_docker_exec "postgres" "psql"
    
    # Execute
    output=$($DOCKER_CLI db restore "$backup_file" 2>&1)
    exit_code=$?
    
    # Assert
    assert_equals 0 $exit_code "DB restore should exit with 0"
    assert_contains "$output" "Restoring PostgreSQL from backup" "Should show restore message"
    assert_contains "$output" "Database restored successfully" "Should show success message"
    
    # Cleanup
    rm -f "$backup_file"
}

# Test: DB reset should reset database
it "should reset database with confirmation"
test_db_reset() {
    # Setup
    mock_docker_exec "postgres" "dropdb"
    mock_docker_exec "postgres" "createdb"
    
    # Execute with forced yes
    output=$(echo "y" | $DOCKER_CLI db reset 2>&1)
    exit_code=$?
    
    # Assert
    assert_equals 0 $exit_code "DB reset should exit with 0"
    assert_contains "$output" "This will DELETE ALL DATA" "Should show warning"
    assert_contains "$output" "Database reset complete" "Should show completion"
}

# Test: DB shell should provide database access
it "should provide database shell access"
test_db_shell() {
    # Setup
    mock_docker_exec "postgres" "psql"
    
    # Execute
    output=$($DOCKER_CLI db shell 2>&1)
    exit_code=$?
    
    # Assert
    assert_equals 0 $exit_code "DB shell should exit with 0"
    assert_contains "$output" "Connecting to PostgreSQL shell" "Should show connection message"
    assert_contains "$output" "psql (13.0)" "Should show psql version"
}

# Test: Invalid DB command should show error
it "should show error for invalid database command"
test_invalid_db_command() {
    # Execute
    output=$($DOCKER_CLI db invalidcommand 2>&1)
    exit_code=$?
    
    # Assert
    assert_not_equals 0 $exit_code "Invalid DB command should exit with non-zero"
    assert_contains "$output" "Unknown database command" "Should show error message"
    assert_contains "$output" "Valid commands:" "Should list valid commands"
}

# Test: DB backup with custom filename
it "should create backup with custom filename"
test_db_backup_custom_name() {
    # Setup
    local backup_name="custom_backup"
    mock_docker_exec "postgres" "pg_dump"
    
    # Execute
    output=$($DOCKER_CLI db backup "$backup_name" 2>&1)
    exit_code=$?
    
    # Assert
    assert_equals 0 $exit_code "DB backup should exit with 0"
    assert_contains "$output" "$backup_name" "Should use custom backup name"
}

# Test: DB operations should check container exists
it "should verify PostgreSQL container exists"
test_db_container_check() {
    # Setup - simulate no container
    export DOCKER_CLI_TEST_MOCK_NO_CONTAINERS="true"
    
    # Execute
    output=$($DOCKER_CLI db test-connection 2>&1)
    exit_code=$?
    
    # Assert
    assert_not_equals 0 $exit_code "Should fail when container doesn't exist"
    assert_contains "$output" "PostgreSQL container not found" "Should show container error"
    
    # Cleanup
    unset DOCKER_CLI_TEST_MOCK_NO_CONTAINERS
}

run_tests