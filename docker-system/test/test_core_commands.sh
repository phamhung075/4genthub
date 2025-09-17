#!/bin/bash
# test_core_commands.sh - Tests for core Docker CLI commands

# Test framework setup
source "$(dirname "$0")/test_framework.sh"

# Test suite for core commands
describe "Core Docker Commands"

# Test: Start command should start all services
it "should start all services with 'start' command"
test_start_command() {
    # Setup
    mock_docker_compose "up -d" "Starting agenthub_postgres_1 ... done"
    
    # Execute
    output=$($DOCKER_CLI start 2>&1)
    exit_code=$?
    
    # Assert
    assert_equals 0 $exit_code "Start command should exit with 0"
    assert_contains "$output" "Starting agenthub services" "Should show starting message"
    assert_docker_compose_called_with "up -d"
}

# Test: Stop command should stop all services
it "should stop all services with 'stop' command"
test_stop_command() {
    # Setup
    mock_docker_compose "stop" "Stopping agenthub_postgres_1 ... done"
    
    # Execute
    output=$($DOCKER_CLI stop 2>&1)
    exit_code=$?
    
    # Assert
    assert_equals 0 $exit_code "Stop command should exit with 0"
    assert_contains "$output" "Stopping agenthub services" "Should show stopping message"
    assert_docker_compose_called_with "stop"
}

# Test: Restart command should restart services
it "should restart specific service"
test_restart_specific_service() {
    # Setup
    mock_docker_compose "restart backend" "Restarting agenthub-backend ... done"
    
    # Execute
    output=$($DOCKER_CLI restart backend 2>&1)
    exit_code=$?
    
    # Assert
    assert_equals 0 $exit_code "Restart command should exit with 0"
    assert_contains "$output" "Restarting service: backend" "Should show restart message"
    assert_docker_compose_called_with "restart backend"
}

# Test: Status command should show service status
it "should display service status"
test_status_command() {
    # Setup
    mock_docker_ps "agenthub-postgres:Running (healthy):5432->5432/tcp
agenthub-redis:Running (healthy):6379->6379/tcp
agenthub-backend:Running (healthy):8000->8000/tcp
agenthub-frontend:Running:3000->3000/tcp"
    
    # Execute
    output=$($DOCKER_CLI status 2>&1)
    exit_code=$?
    
    # Assert
    assert_equals 0 $exit_code "Status command should exit with 0"
    assert_contains "$output" "postgres" "Should show postgres status"
    assert_contains "$output" "redis" "Should show redis status"
    assert_contains "$output" "backend" "Should show backend status"
    assert_contains "$output" "frontend" "Should show frontend status"
    assert_contains "$output" "Running" "Should show running state"
}

# Test: Logs command should show service logs
it "should show logs for specific service"
test_logs_command() {
    # Setup
    mock_docker_compose "logs -f --tail=100 backend" "backend_1  | [2025-01-20] Starting server..."
    
    # Execute
    output=$($DOCKER_CLI logs backend 2>&1)
    exit_code=$?
    
    # Assert
    assert_equals 0 $exit_code "Logs command should exit with 0"
    assert_contains "$output" "Starting server" "Should show backend logs"
}

# Test: Shell command should access container shell
it "should access container shell"
test_shell_command() {
    # Setup
    mock_docker_exec "backend" "/bin/bash"
    
    # Execute
    # Note: We can't test interactive shell directly, so we test the command building
    output=$($DOCKER_CLI shell backend --dry-run 2>&1)
    exit_code=$?
    
    # Assert
    assert_equals 0 $exit_code "Shell command should exit with 0"
    assert_contains "$output" "docker exec -it agenthub-backend" "Should build correct exec command"
}

# Test: Invalid command should show error
it "should show error for invalid command"
test_invalid_command() {
    # Execute
    output=$($DOCKER_CLI invalidcommand 2>&1)
    exit_code=$?
    
    # Assert
    assert_not_equals 0 $exit_code "Invalid command should exit with non-zero"
    assert_contains "$output" "Unknown command: invalidcommand" "Should show error message"
    assert_contains "$output" "help" "Should suggest help command"
}

# Test: Help command should show usage
it "should display help information"
test_help_command() {
    # Execute
    output=$($DOCKER_CLI help 2>&1)
    exit_code=$?
    
    # Assert
    assert_equals 0 $exit_code "Help command should exit with 0"
    assert_contains "$output" "agenthub Docker CLI" "Should show title"
    assert_contains "$output" "USAGE:" "Should show usage section"
    assert_contains "$output" "COMMANDS:" "Should show commands section"
    assert_contains "$output" "start" "Should list start command"
    assert_contains "$output" "stop" "Should list stop command"
}

# Run all tests
run_tests