#!/bin/bash
# test-runner.sh - Main test runner for Docker CLI

# Set test mode
export DOCKER_CLI_TEST_MODE=true

# Get script directory
TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Don't set SCRIPT_DIR if already set
if [[ -z "${SCRIPT_DIR:-}" ]]; then
    SCRIPT_DIR="$(dirname "$TEST_DIR")"
fi

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test statistics
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

# Run specific test file
run_test_file() {
    local test_file="$1"
    
    if [[ ! -f "$test_file" ]]; then
        echo -e "${RED}Test file not found: $test_file${NC}"
        return 1
    fi
    
    echo -e "\n${BLUE}Running $(basename "$test_file")...${NC}"
    
    # Source and run the test file
    (
        cd "$TEST_DIR"
        source "$test_file"
    )
    
    local exit_code=$?
    return $exit_code
}

# Run all tests or specific category
run_tests() {
    local test_type="${1:-all}"
    local test_files=()
    
    echo -e "${BLUE}=== Docker CLI Test Suite ===${NC}"
    echo -e "Test mode: ${YELLOW}$test_type${NC}\n"
    
    # Determine which tests to run
    case "$test_type" in
        all)
            test_files=("$TEST_DIR"/test_*.sh)
            ;;
        core)
            test_files=("$TEST_DIR"/test_core_commands.sh)
            ;;
        service)
            test_files=("$TEST_DIR"/test_service_management.sh)
            ;;
        database|db)
            test_files=("$TEST_DIR"/test_database_operations.sh)
            ;;
        monitoring)
            test_files=("$TEST_DIR"/test_monitoring_health.sh)
            ;;
        workflow)
            test_files=("$TEST_DIR"/test_workflows.sh)
            ;;
        development|dev)
            test_files=("$TEST_DIR"/test_development_commands.sh)
            ;;
        *)
            echo -e "${RED}Unknown test type: $test_type${NC}"
            echo "Valid types: all, core, service, database, monitoring, workflow, development"
            return 1
            ;;
    esac
    
    # Run each test file
    local failed_files=()
    for test_file in "${test_files[@]}"; do
        if [[ -f "$test_file" ]]; then
            run_test_file "$test_file"
            if [[ $? -ne 0 ]]; then
                failed_files+=("$(basename "$test_file")")
            fi
        fi
    done
    
    # Summary
    echo -e "\n${BLUE}=== Test Summary ===${NC}"
    
    if [[ ${#failed_files[@]} -eq 0 ]]; then
        echo -e "${GREEN}✅ All test files passed!${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed test files:${NC}"
        for file in "${failed_files[@]}"; do
            echo -e "   ${RED}• $file${NC}"
        done
        return 1
    fi
}

# Main execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    run_tests "$@"
fi