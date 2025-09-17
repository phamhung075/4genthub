#!/bin/bash
# test_framework.sh - Testing framework for Docker CLI tests

# Configuration
DOCKER_CLI="${DOCKER_CLI:-./docker-cli.sh}"
TEST_ENV_FILE="${TEST_ENV_FILE:-./environments/test.env}"
MOCK_DIR="/tmp/docker-cli-test-mocks"
TEST_RESULTS=()
CURRENT_TEST=""
CURRENT_SUITE=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Initialize test environment
init_test_env() {
    # Create mock directory
    mkdir -p "$MOCK_DIR"
    
    # Set test environment
    export DEFAULT_ENV="test"
    export DOCKER_CLI_TEST_MODE="true"
    
    # Create mock docker command
    create_mock_docker
}

# Cleanup test environment
cleanup_test_env() {
    # Skip cleanup if configured
    if [[ "${SKIP_TEST_CLEANUP:-}" == "true" ]]; then
        return 0
    fi
    
    rm -rf "$MOCK_DIR"
    unset DOCKER_CLI_TEST_MODE
}

# Cleanup test artifacts
cleanup_test_artifacts() {
    # Skip cleanup if configured
    if [[ "${SKIP_TEST_CLEANUP:-}" == "true" ]]; then
        return 0
    fi
    
    # Remove test-related directories and files
    rm -rf test-temp test-dir concurrent-test test-perf test-artifacts 2>/dev/null || true
    rm -f test-output.log test-file.txt .test-config 2>/dev/null || true
    
    # Remove test backups directory if it exists
    if [[ -d "backups" ]] && [[ -z "$(ls -A backups 2>/dev/null)" ]]; then
        rmdir backups 2>/dev/null || true
    elif [[ -d "backups" ]]; then
        # Only remove test backup files
        rm -f backups/test-*.tar.gz backups/backup_*.tar.gz 2>/dev/null || true
        # Remove directory if now empty
        rmdir backups 2>/dev/null || true
    fi
    
    # Handle permission errors gracefully
    if [[ -d "test-restricted" ]]; then
        if ! chmod -R 755 "test-restricted" 2>/dev/null; then
            echo "Warning: Could not change permissions on test-restricted" >&2
            echo "Warning: Could not change permissions on test-restricted"
        fi
        if ! rm -rf "test-restricted" 2>/dev/null; then
            echo "Warning: Could not remove test-restricted" >&2
            echo "Warning: Could not remove test-restricted"
        fi
    fi
    
    return 0
}

# Cleanup docker logs
cleanup_docker_logs() {
    # Skip cleanup if configured
    if [[ "${SKIP_TEST_CLEANUP:-}" == "true" ]]; then
        return 0
    fi
    
    if [[ -d "$MOCK_DIR" ]]; then
        rm -f "$MOCK_DIR"/*.calls 2>/dev/null || true
    fi
    
    return 0
}

# Cleanup with summary
cleanup_with_summary() {
    local items_cleaned=0
    
    echo "Cleanup Summary"
    echo "==============="
    
    # Clean mock directory
    if [[ -d "$MOCK_DIR" ]]; then
        cleanup_test_env
        echo "Mock directory: removed"
        ((items_cleaned++))
    fi
    
    # Clean test artifacts
    local artifact_count=0
    for item in test-temp test-dir test-output.log test-file.txt backups; do
        if [[ -e "$item" ]]; then
            ((artifact_count++))
        fi
    done
    
    if [[ $artifact_count -gt 0 ]]; then
        cleanup_test_artifacts
        echo "Test artifacts: removed ($artifact_count items)"
        ((items_cleaned += artifact_count))
    fi
    
    # Clean docker logs
    if [[ -d "$MOCK_DIR" ]] && ls "$MOCK_DIR"/*.calls &>/dev/null; then
        cleanup_docker_logs
        echo "Docker logs: removed"
        ((items_cleaned++))
    fi
    
    echo "Total items cleaned: $items_cleaned"
}

# Cleanup hook management
declare -a CLEANUP_HOOKS=()

add_cleanup_hook() {
    local hook_name="$1"
    CLEANUP_HOOKS+=("$hook_name")
}

execute_cleanup_hooks() {
    for hook in "${CLEANUP_HOOKS[@]}"; do
        if declare -f "$hook" >/dev/null; then
            "$hook"
        fi
    done
    
    # Clear hooks after execution
    CLEANUP_HOOKS=()
}

# Test suite functions
describe() {
    CURRENT_SUITE="$1"
    echo -e "\n${BLUE}Test Suite: $CURRENT_SUITE${NC}"
    echo "================================"
}

it() {
    CURRENT_TEST="$1"
    echo -n "  - $CURRENT_TEST ... "
}

# Assertion functions
assert_equals() {
    local expected="$1"
    local actual="$2"
    local message="${3:-Values should be equal}"
    
    if [[ "$expected" == "$actual" ]]; then
        pass_test
    else
        fail_test "$message\n    Expected: '$expected'\n    Actual: '$actual'"
    fi
}

assert_not_equals() {
    local unexpected="$1"
    local actual="$2"
    local message="${3:-Values should not be equal}"
    
    if [[ "$unexpected" != "$actual" ]]; then
        pass_test
    else
        fail_test "$message\n    Unexpected: '$unexpected'\n    Actual: '$actual'"
    fi
}

assert_contains() {
    local haystack="$1"
    local needle="$2"
    local message="${3:-String should contain substring}"
    
    if [[ "$haystack" == *"$needle"* ]]; then
        pass_test
    else
        fail_test "$message\n    String: '$haystack'\n    Should contain: '$needle'"
    fi
}

assert_not_contains() {
    local haystack="$1"
    local needle="$2"
    local message="${3:-String should not contain substring}"
    
    if [[ "$haystack" != *"$needle"* ]]; then
        pass_test
    else
        fail_test "$message\n    String: '$haystack'\n    Should not contain: '$needle'"
    fi
}

assert_file_exists() {
    local file="$1"
    local message="${2:-File should exist}"
    
    if [[ -f "$file" ]]; then
        pass_test
    else
        fail_test "$message\n    File not found: '$file'"
    fi
}

assert_exists() {
    local path="$1"
    local message="${2:-Path should exist}"
    
    if [[ -e "$path" ]]; then
        pass_test
    else
        fail_test "$message\n    Path: '$path'"
    fi
}

assert_not_exists() {
    local path="$1"
    local message="${2:-Path should not exist}"
    
    if [[ ! -e "$path" ]]; then
        pass_test
    else
        fail_test "$message\n    Path: '$path'"
    fi
}

assert_less_than() {
    local actual="$1"
    local expected="$2"
    local message="${3:-Value should be less than expected}"
    
    if [[ "$actual" -lt "$expected" ]]; then
        pass_test
    else
        fail_test "$message\n    Actual: '$actual'\n    Should be less than: '$expected'"
    fi
}

assert_dir_exists() {
    local dir="$1"
    local message="${2:-Directory should exist}"
    
    if [[ -d "$dir" ]]; then
        pass_test
    else
        fail_test "$message\n    Directory not found: '$dir'"
    fi
}

# Test result functions
pass_test() {
    echo -e "${GREEN}PASS${NC}"
    TEST_RESULTS+=("PASS:$CURRENT_SUITE:$CURRENT_TEST")
}

fail_test() {
    local message="$1"
    echo -e "${RED}FAIL${NC}"
    echo -e "    ${RED}$message${NC}"
    TEST_RESULTS+=("FAIL:$CURRENT_SUITE:$CURRENT_TEST:$message")
}

skip_test() {
    local reason="$1"
    echo -e "${YELLOW}SKIP${NC} - $reason"
    TEST_RESULTS+=("SKIP:$CURRENT_SUITE:$CURRENT_TEST:$reason")
}

# Mock functions
create_mock_docker() {
    cat > "$MOCK_DIR/docker" << EOF
#!/bin/bash
# Mock docker command
MOCK_DIR="$MOCK_DIR"
echo "\$@" >> "\$MOCK_DIR/docker.calls"

case "\$1" in
    "compose")
        shift
        if [[ -f "\$MOCK_DIR/docker-compose.mock" ]]; then
            source "\$MOCK_DIR/docker-compose.mock" "\$@"
        else
            echo "Mock docker-compose not configured" >&2
            exit 1
        fi
        ;;
    "ps")
        if [[ -f "\$MOCK_DIR/docker-ps.mock" ]]; then
            source "\$MOCK_DIR/docker-ps.mock" "\$@"
        else
            echo "Mock docker ps not configured" >&2
            exit 1
        fi
        ;;
    "exec")
        if [[ -f "\$MOCK_DIR/docker-exec.mock" ]]; then
            source "\$MOCK_DIR/docker-exec.mock" "\$@"
        else
            echo "Mock docker exec not configured" >&2
            exit 1
        fi
        ;;
    "logs")
        if [[ -f "\$MOCK_DIR/docker-logs.mock" ]]; then
            source "\$MOCK_DIR/docker-logs.mock" "\$@"
        else
            echo "Mock docker logs not configured" >&2
            exit 1
        fi
        ;;
    "inspect")
        if [[ -f "\$MOCK_DIR/docker-inspect.mock" ]]; then
            source "\$MOCK_DIR/docker-inspect.mock" "\$@"
        else
            echo "Mock docker inspect not configured" >&2
            exit 1
        fi
        ;;
    "info")
        if [[ -f "\$MOCK_DIR/docker-info.mock" ]]; then
            source "\$MOCK_DIR/docker-info.mock" "\$@"
        else
            echo "Docker version 20.10.0"
            exit 0
        fi
        ;;
    "stats")
        echo "CONTAINER CPU% MEM%"
        exit 0
        ;;
    "network")
        if [[ "\$2" == "inspect" ]]; then
            echo '{"Containers": {}}'
        else
            echo "4genthub-network"
        fi
        exit 0
        ;;
    "volume")
        if [[ "\$2" == "rm" ]]; then
            echo "Volume removed"
        fi
        exit 0
        ;;
    "pull")
        if [[ -f "\$MOCK_DIR/docker-pull.mock" ]]; then
            source "\$MOCK_DIR/docker-pull.mock" "\$@"
        else
            echo "Pulling \$2..."
            exit 0
        fi
        ;;
    *)
        # Check for generic mock file with sanitized name
        SANITIZED=\$(echo "\$1" | tr ' /:' '___')
        if [[ -f "\$MOCK_DIR/docker-\$SANITIZED.mock" ]]; then
            source "\$MOCK_DIR/docker-\$SANITIZED.mock" "\$@"
        elif [[ -f "\$MOCK_DIR/docker-\$1.mock" ]]; then
            source "\$MOCK_DIR/docker-\$1.mock" "\$@"
        else
            echo "Mock docker: Unknown command \$1" >&2
            exit 1
        fi
        ;;
esac
EOF
    chmod +x "$MOCK_DIR/docker"
    
    # Create docker-compose wrapper
    cat > "$MOCK_DIR/docker-compose" << EOF
#!/bin/bash
MOCK_DIR="$MOCK_DIR"
"\$MOCK_DIR/docker" compose "\$@"
EOF
    chmod +x "$MOCK_DIR/docker-compose"
    
    # Add mock directory to PATH
    export PATH="$MOCK_DIR:$PATH"
}

mock_docker() {
    local command="$1"
    local output="$2"
    
    # Use sanitized filename - replace spaces, colons, and slashes
    local filename=$(echo "$command" | tr ' /:' '___')
    cat > "$MOCK_DIR/docker-${filename}.mock" << EOF
#!/bin/bash
if [[ -n "$output" ]]; then
    echo "$output"
fi
exit 0
EOF
    chmod +x "$MOCK_DIR/docker-${filename}.mock"
}

mock_docker_compose() {
    local command="$1"
    local output="$2"
    
    cat > "$MOCK_DIR/docker-compose.mock" << EOF
#!/bin/bash
# If the command matches exactly or is contained in arguments
if [[ "\$*" == "$command" ]] || [[ "\$*" == *"$command"* ]]; then
    if [[ -n "$output" ]]; then
        echo "$output"
    fi
    exit 0
else
    echo "Mock docker-compose: Unexpected arguments: \$*" >&2
    exit 1
fi
EOF
    chmod +x "$MOCK_DIR/docker-compose.mock"
}

mock_docker_ps() {
    local output="$1"
    
    cat > "$MOCK_DIR/docker-ps.mock" << EOF
#!/bin/bash
# Output format: NAME:STATUS:PORTS
echo "$output" | while IFS=: read -r name status ports; do
    echo "\$name|\$status|\$ports"
done
exit 0
EOF
    chmod +x "$MOCK_DIR/docker-ps.mock"
}

mock_docker_logs() {
    local container="$1"
    local output="$2"
    
    cat > "$MOCK_DIR/docker-logs.mock" << EOF
#!/bin/bash
if [[ "\$2" == "$container" ]]; then
    echo "$output"
    exit 0
else
    echo "Mock docker logs: Container not found: \$2" >&2
    exit 1
fi
EOF
    chmod +x "$MOCK_DIR/docker-logs.mock"
}

mock_docker_exec() {
    local container="$1"
    local command="$2"
    
    cat > "$MOCK_DIR/docker-exec.mock" << EOF
#!/bin/bash
echo "Mock exec: \$*" >> "\$MOCK_DIR/docker-exec.calls"
if [[ "\$*" == *"$container"* ]]; then
    exit 0
else
    echo "Mock docker exec: Container not found" >&2
    exit 1
fi
EOF
    chmod +x "$MOCK_DIR/docker-exec.mock"
}

# Verification functions
assert_docker_compose_called_with() {
    local expected="$1"
    local calls=$(cat "$MOCK_DIR/docker.calls" 2>/dev/null)
    
    if [[ "$calls" == *"compose $expected"* ]]; then
        pass_test
    else
        fail_test "Docker compose not called with expected arguments\n    Expected: 'compose $expected'\n    Calls: $calls"
    fi
}

assert_docker_logs_called_with() {
    local expected="$1"
    local calls=$(cat "$MOCK_DIR/docker.calls" 2>/dev/null)
    
    if [[ "$calls" == *"logs $expected"* ]]; then
        pass_test
    else
        fail_test "Docker logs not called with expected arguments\n    Expected: 'logs $expected'\n    Calls: $calls"
    fi
}

# Test runner
run_tests() {
    init_test_env
    
    # Run all test functions
    for func in $(declare -F | grep "^declare -f test_" | awk '{print $3}'); do
        # Clear mock calls before test
        rm -f "$MOCK_DIR"/*.calls 2>/dev/null || true
        
        # Run test
        $func
        
        # Cleanup after each test
        cleanup_test_artifacts
        cleanup_docker_logs
    done
    
    # Final cleanup
    cleanup_test_env
    cleanup_test_artifacts
    
    # Execute any registered cleanup hooks
    execute_cleanup_hooks
    
    # Show summary
    show_test_summary
}

# Run tests with cleanup option
run_tests_with_cleanup() {
    run_tests
    
    # Additional cleanup if requested
    if [[ "${THOROUGH_CLEANUP:-}" == "true" ]]; then
        cleanup_with_summary
    fi
}

show_test_summary() {
    echo -e "\n${BLUE}Test Summary${NC}"
    echo "================================"
    
    local total=0
    local passed=0
    local failed=0
    local skipped=0
    
    for result in "${TEST_RESULTS[@]}"; do
        ((total++))
        case "$result" in
            PASS:*) ((passed++)) ;;
            FAIL:*) ((failed++)) ;;
            SKIP:*) ((skipped++)) ;;
        esac
    done
    
    echo "Total: $total"
    echo -e "Passed: ${GREEN}$passed${NC}"
    echo -e "Failed: ${RED}$failed${NC}"
    echo -e "Skipped: ${YELLOW}$skipped${NC}"
    
    if [[ $failed -gt 0 ]]; then
        echo -e "\n${RED}TESTS FAILED${NC}"
        exit 1
    else
        echo -e "\n${GREEN}ALL TESTS PASSED${NC}"
        exit 0
    fi
}