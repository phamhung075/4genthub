#!/bin/bash
# Fast test execution scripts

echo "🚀 Fast Test Runner"
echo "=================="

# Function to show timing
time_it() {
    local start=$(date +%s)
    "$@"
    local end=$(date +%s)
    echo "⏱️  Execution time: $((end - start)) seconds"
}

case "$1" in
    "unit")
        echo "Running unit tests (ultra-fast, no database)..."
        time_it pytest -m unit -q --tb=short
        ;;
    
    "unit-parallel")
        echo "Running unit tests in parallel..."
        time_it pytest -m unit -n auto --tb=short
        ;;
    
    "value-objects")
        echo "Running value object tests (fastest)..."
        time_it pytest src/tests/**/value_objects/ -q --tb=short
        ;;
    
    "entities")
        echo "Running entity tests..."
        time_it pytest src/tests/**/entities/ -q --tb=short
        ;;
    
    "integration")
        echo "Running integration tests..."
        time_it pytest -m integration --tb=short
        ;;
    
    "integration-parallel")
        echo "Running integration tests in parallel (be careful with database)..."
        time_it pytest -m integration -n 4 --tb=short
        ;;
    
    "all-parallel")
        echo "Running ALL tests in parallel..."
        time_it pytest -n auto --tb=short
        ;;
    
    "failed")
        echo "Running only failed tests..."
        time_it pytest --lf -v
        ;;
    
    "profile")
        echo "Running tests with profiling (shows slowest tests)..."
        time_it pytest --durations=20 -v
        ;;
    
    *)
        echo "Usage: $0 {unit|unit-parallel|value-objects|entities|integration|integration-parallel|all-parallel|failed|profile}"
        echo ""
        echo "Examples:"
        echo "  $0 unit              # Run unit tests quickly"
        echo "  $0 unit-parallel     # Run unit tests in parallel (fastest)"
        echo "  $0 value-objects     # Run only value object tests"
        echo "  $0 failed            # Re-run failed tests"
        echo "  $0 profile           # Show slowest tests"
        exit 1
        ;;
esac