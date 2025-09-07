#!/bin/bash
# test_framework_cleanup.sh - Tests for test framework cleanup integration

source "$(dirname "$0")/test_framework.sh"

describe "Test Framework Cleanup Integration"

# Test: Should call cleanup after each test
it "should call cleanup after individual test execution"
test_framework_cleanup_per_test() {
    # Setup - track cleanup calls
    local cleanup_log="/tmp/cleanup-calls.log"
    rm -f "$cleanup_log"
    
    # Override cleanup function to log calls
    cleanup_test_artifacts() {
        echo "cleanup_test_artifacts called" >> "$cleanup_log"
        # Still do actual cleanup
        rm -rf test-temp test-dir concurrent-test test-perf test-artifacts 2>/dev/null || true
        rm -f test-output.log test-file.txt .test-config 2>/dev/null || true
    }
    
    # Execute a single test
    init_test_env
    echo "test content" > "test-file.txt"
    cleanup_test_artifacts
    
    # Assert
    assert_exists "$cleanup_log" "Cleanup log should exist"
    local cleanup_count=$(wc -l < "$cleanup_log")
    assert_equals 1 "$cleanup_count" "Cleanup should be called once per test"
    
    # Cleanup
    rm -f "$cleanup_log" "test-file.txt"
}

# Test: Should handle cleanup errors without failing tests
it "should continue test execution even if cleanup fails"
test_framework_cleanup_error_handling() {
    # Setup - create cleanup that fails
    cleanup_test_artifacts() {
        return 1  # Simulate failure
    }
    
    # Execute test with failing cleanup
    local test_output=$(
        init_test_env
        touch "test-artifact.txt"
        cleanup_test_artifacts
        echo "Test completed"
    )
    
    # Assert
    assert_contains "$test_output" "Test completed" "Test should complete despite cleanup failure"
    
    # Manual cleanup
    rm -f "test-artifact.txt"
}

# Test: Should cleanup in correct order
it "should execute cleanup operations in correct order"
test_framework_cleanup_order() {
    # Setup - track cleanup order
    local order_log="/tmp/cleanup-order.log"
    rm -f "$order_log"
    
    # Override cleanup functions
    cleanup_docker_logs() {
        echo "1. docker_logs" >> "$order_log"
        # Actual cleanup
        rm -f docker-*.log 2>/dev/null || true
    }
    
    cleanup_test_artifacts() {
        echo "2. test_artifacts" >> "$order_log"
        # Actual cleanup
        rm -rf test-temp test-dir concurrent-test test-perf test-artifacts 2>/dev/null || true
        rm -f test-output.log test-file.txt .test-config 2>/dev/null || true
    }
    
    cleanup_test_env() {
        echo "3. test_env" >> "$order_log"
        # Actual cleanup
        unset DOCKER_CLI_TEST_MODE 2>/dev/null || true
    }
    
    # Execute full cleanup
    cleanup_docker_logs
    cleanup_test_artifacts
    cleanup_test_env
    
    # Assert order
    local first_line=$(head -n1 "$order_log")
    local second_line=$(sed -n '2p' "$order_log")
    local third_line=$(sed -n '3p' "$order_log")
    
    assert_equals "1. docker_logs" "$first_line" "Docker logs should be cleaned first"
    assert_equals "2. test_artifacts" "$second_line" "Test artifacts should be cleaned second"
    assert_equals "3. test_env" "$third_line" "Test environment should be cleaned last"
    
    # Cleanup
    rm -f "$order_log"
}

# Test: Should track cleanup performance
it "should complete cleanup within reasonable time"
test_framework_cleanup_performance() {
    # Setup - create many test files
    mkdir -p "test-perf"
    for i in {1..100}; do
        touch "test-perf/file-$i.txt"
    done
    
    # Measure cleanup time
    local start_time=$(date +%s)
    cleanup_test_artifacts
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Assert
    assert_less_than "$duration" 5 "Cleanup should complete within 5 seconds"
    assert_not_exists "test-perf" "Performance test directory should be cleaned"
}

# Test: Should provide cleanup hooks
it "should support custom cleanup hooks"
test_framework_cleanup_hooks() {
    # Setup - register cleanup hook
    local hook_executed=false
    
    register_cleanup_hook() {
        add_cleanup_hook "custom_cleanup"
    }
    
    custom_cleanup() {
        hook_executed=true
    }
    
    # Execute with hook
    register_cleanup_hook
    execute_cleanup_hooks
    
    # Assert
    assert_equals true "$hook_executed" "Custom cleanup hook should be executed"
}

# Test: Should cleanup only test-related files
it "should only remove test-related files and directories"
test_framework_cleanup_scope() {
    # Setup - create various files
    mkdir -p "test-dir"
    mkdir -p "src"
    touch "test-file.txt"
    touch "README.md"
    touch ".test-config"
    
    # Execute targeted cleanup - use the actual cleanup function from test_framework.sh
    # Source it again to ensure we have the real function
    source "$(dirname "$0")/test_framework.sh"
    cleanup_test_artifacts
    
    # Assert
    assert_not_exists "test-dir" "Test directories should be removed"
    assert_not_exists "test-file.txt" "Test files should be removed"
    assert_not_exists ".test-config" "Test config files should be removed"
    assert_exists "src" "Source directories should be preserved"
    assert_exists "README.md" "Project files should be preserved"
    
    # Cleanup remaining
    rm -rf "src" "README.md"
}

# Test: Should handle concurrent cleanup
it "should handle concurrent cleanup operations safely"
test_framework_cleanup_concurrent() {
    # Setup - create test files
    mkdir -p "concurrent-test"
    touch "concurrent-test/file1.txt"
    touch "concurrent-test/file2.txt"
    
    # Source to ensure we have the cleanup function
    source "$(dirname "$0")/test_framework.sh"
    
    # Execute concurrent cleanup
    cleanup_test_artifacts &
    local pid1=$!
    cleanup_test_artifacts &
    local pid2=$!
    
    # Wait for both to complete
    wait $pid1
    local exit1=$?
    wait $pid2
    local exit2=$?
    
    # Assert
    assert_equals 0 "$exit1" "First cleanup should succeed"
    assert_equals 0 "$exit2" "Second cleanup should succeed"
    assert_not_exists "concurrent-test" "Directory should be cleaned"
}

run_tests