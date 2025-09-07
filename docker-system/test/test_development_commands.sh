#!/bin/bash
# test_development_commands.sh - Tests for development commands

source "$(dirname "$0")/test_framework.sh"

describe "Development Commands"

# Test: Dev setup should initialize development environment
it "should setup development environment"
test_dev_setup() {
    # Setup
    mock_docker_compose "up -d" "Creating network..."
    
    # Execute
    output=$($DOCKER_CLI dev setup 2>&1)
    exit_code=$?
    
    # Assert
    assert_equals 0 $exit_code "Dev setup should exit with 0"
    assert_contains "$output" "Setting up development environment" "Should show setup message"
    assert_contains "$output" "Development environment setup complete" "Should show completion"
    assert_contains "$output" "Backend API: http://localhost:8000" "Should show backend URL"
    assert_contains "$output" "Frontend:    http://localhost:3000" "Should show frontend URL"
}

# Test: Dev reset should reset development data
it "should reset development environment"
test_dev_reset() {
    # Setup
    mock_docker_compose "stop" "Stopping containers..."
    mock_docker "volume rm" "Volume removed"
    
    # Execute with forced yes
    output=$(echo "y" | $DOCKER_CLI dev reset 2>&1)
    exit_code=$?
    
    # Assert
    assert_equals 0 $exit_code "Dev reset should exit with 0"
    assert_contains "$output" "This will reset all development data" "Should show warning"
    assert_contains "$output" "Development environment reset complete" "Should show completion"
}

# Test: Dev seed should populate sample data
it "should seed development data"
test_dev_seed() {
    # Setup
    mock_docker_exec "backend" "python scripts/seed_data.py"
    
    # Execute
    output=$($DOCKER_CLI dev seed 2>&1)
    exit_code=$?
    
    # Assert
    assert_equals 0 $exit_code "Dev seed should exit with 0"
    assert_contains "$output" "Seeding development data" "Should show seed message"
    assert_contains "$output" "Development data seeded" "Should show completion"
}

# Test: Build command should build Docker images
it "should build all services"
test_build_all() {
    # Setup
    mock_docker_compose "build --parallel" "Building images..."
    
    # Execute
    output=$($DOCKER_CLI build 2>&1)
    exit_code=$?
    
    # Assert
    assert_equals 0 $exit_code "Build should exit with 0"
    assert_contains "$output" "Building Docker images" "Should show build message"
    assert_contains "$output" "Build completed" "Should show completion"
}

# Test: Build specific service
it "should build specific service"
test_build_specific() {
    # Setup
    mock_docker_compose "build backend" "Building backend..."
    
    # Execute
    output=$($DOCKER_CLI build backend 2>&1)
    exit_code=$?
    
    # Assert
    assert_equals 0 $exit_code "Build backend should exit with 0"
    assert_contains "$output" "Building Docker images" "Should show build message"
    assert_contains "$output" "Building backend" "Should show service being built"
}

# Test: Test command should run all tests
it "should run all tests"
test_run_all_tests() {
    # Setup
    export DOCKER_CLI_TESTING_TESTS="true"
    mock_docker_exec "backend" "pytest"
    
    # Execute
    output=$($DOCKER_CLI test all 2>&1)
    exit_code=$?
    
    # Assert
    assert_equals 0 $exit_code "Test all should exit with 0"
    assert_contains "$output" "Running all tests" "Should show test message"
    
    # Cleanup
    unset DOCKER_CLI_TESTING_TESTS
}

# Test: Test unit command
it "should run unit tests"
test_run_unit_tests() {
    # Setup
    export DOCKER_CLI_TESTING_TESTS="true"
    mock_docker_exec "backend" "pytest tests/unit"
    
    # Execute
    output=$($DOCKER_CLI test unit 2>&1)
    exit_code=$?
    
    # Assert
    assert_equals 0 $exit_code "Test unit should exit with 0"
    assert_contains "$output" "Running unit tests" "Should show test type"
    
    # Cleanup
    unset DOCKER_CLI_TESTING_TESTS
}

# Test: Test integration command
it "should run integration tests"
test_run_integration_tests() {
    # Setup
    export DOCKER_CLI_TESTING_TESTS="true"
    mock_docker_exec "backend" "pytest tests/integration"
    
    # Execute
    output=$($DOCKER_CLI test integration 2>&1)
    exit_code=$?
    
    # Assert
    assert_equals 0 $exit_code "Test integration should exit with 0"
    assert_contains "$output" "Running integration tests" "Should show test type"
    
    # Cleanup
    unset DOCKER_CLI_TESTING_TESTS
}

# Test: Invalid dev command
it "should show error for invalid dev command"
test_invalid_dev_command() {
    # Execute
    output=$($DOCKER_CLI dev invalidcommand 2>&1)
    exit_code=$?
    
    # Assert
    assert_not_equals 0 $exit_code "Invalid dev command should exit with non-zero"
    assert_contains "$output" "Unknown dev command" "Should show error"
    assert_contains "$output" "Valid commands: setup, reset, seed" "Should list valid commands"
}

# Test: Environment file creation
it "should create .env file if not exists"
test_env_file_creation() {
    # Setup - ensure no .env exists
    local test_env="${PROJECT_ROOT}/.env"
    rm -f "$test_env"
    
    # Execute
    output=$($DOCKER_CLI dev setup 2>&1)
    exit_code=$?
    
    # Assert
    assert_contains "$output" "Created .env file from dev template" "Should create env file"
    # In test mode, we don't actually create the file
    
    # Cleanup
    rm -f "$test_env"
}

run_tests