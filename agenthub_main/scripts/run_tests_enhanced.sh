#!/bin/bash
# Enhanced Test Runner Script with Coverage and CI Integration
# Part of subtask: 4fabc4f5-5750-4790-8055-68b443c7aafc

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "OPTIONS:"
    echo "  --type TYPE              Test type: unit, integration, e2e, all, performance, parallel (default: all)"
    echo "  --coverage-threshold N   Coverage threshold percentage (default: 80)"
    echo "  --ci                     CI mode - generate machine-readable reports"
    echo "  --quick                  Quick mode - skip coverage reports"
    echo "  --parallel               Run tests in parallel"
    echo "  --verbose                Verbose output"
    echo "  --help                   Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                       # Run all tests with coverage"
    echo "  $0 --type unit           # Run only unit tests"
    echo "  $0 --parallel            # Run tests in parallel"
    echo "  $0 --ci                  # CI mode with JSON reports"
    echo "  $0 --quick               # Quick test run without coverage"
}

# Default values
TEST_TYPE="all"
COVERAGE_THRESHOLD=80
CI_MODE=false
QUICK_MODE=false
PARALLEL_MODE=false
VERBOSE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --type)
            TEST_TYPE="$2"
            shift 2
            ;;
        --coverage-threshold)
            COVERAGE_THRESHOLD="$2"
            shift 2
            ;;
        --ci)
            CI_MODE=true
            shift
            ;;
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --parallel)
            PARALLEL_MODE=true
            TEST_TYPE="parallel"
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

print_status $BLUE "🧪 Enhanced Test Runner"
print_status $BLUE "======================="
echo "📂 Project directory: $PROJECT_DIR"
echo "🎯 Test type: $TEST_TYPE"
echo "📊 Coverage threshold: $COVERAGE_THRESHOLD%"
echo "⚡ Quick mode: $QUICK_MODE"
echo "🚀 Parallel mode: $PARALLEL_MODE"
echo "🔧 CI mode: $CI_MODE"
echo ""

# Change to project directory
cd "$PROJECT_DIR"

# Setup environment
print_status $YELLOW "🔧 Setting up environment..."

# Load test environment if available
if [ -f .env.test ]; then
    print_status $BLUE "📄 Loading test environment from .env.test"
    set -a  # automatically export all variables
    source .env.test
    set +a
fi

# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}$(pwd)/src"
export TESTING=true
export FASTMCP_TEST_MODE=1

# Create reports directory
mkdir -p test_reports

# Install test dependencies if needed
if [ ! -f "src/tests/hooks/requirements-test.installed" ]; then
    print_status $YELLOW "📦 Installing test dependencies..."
    pip install -r src/tests/hooks/requirements-test.txt
    touch src/tests/hooks/requirements-test.installed
fi

# Function to run tests with timing
run_with_timing() {
    local description="$1"
    shift
    local start_time=$(date +%s)

    print_status $YELLOW "🏃 $description"

    if $VERBOSE; then
        "$@"
    else
        "$@" 2>&1 | while IFS= read -r line; do
            # Show only important lines to reduce noise
            if [[ "$line" =~ (FAILED|ERROR|passed|failed|TOTAL|Coverage|===) ]]; then
                echo "$line"
            fi
        done
    fi

    local exit_code=$?
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    if [ $exit_code -eq 0 ]; then
        print_status $GREEN "✅ $description completed in ${duration}s"
    else
        print_status $RED "❌ $description failed in ${duration}s"
    fi

    return $exit_code
}

# Build pytest command based on options
build_pytest_command() {
    local cmd=("python" "-m" "pytest")

    # Add test type marker
    case "$TEST_TYPE" in
        unit)
            cmd+=("-m" "unit")
            ;;
        integration)
            cmd+=("-m" "integration")
            ;;
        e2e)
            cmd+=("-m" "e2e")
            ;;
        performance)
            cmd+=("-m" "performance")
            ;;
        parallel)
            cmd+=("-n" "auto")
            ;;
    esac

    # Add coverage options (unless quick mode)
    if [ "$QUICK_MODE" = false ] && [[ "$TEST_TYPE" =~ ^(unit|all|parallel)$ ]]; then
        cmd+=(
            "--cov=src"
            "--cov-report=html"
            "--cov-report=term-missing"
            "--cov-report=xml"
            "--cov-fail-under=$COVERAGE_THRESHOLD"
        )
    fi

    # Add JUnit XML report
    cmd+=("--junit-xml=test_reports/${TEST_TYPE}_tests.xml")

    # Add verbose flag
    cmd+=("-v")

    # Add durations for performance monitoring
    cmd+=("--durations=10")

    echo "${cmd[@]}"
}

# Main test execution
main() {
    local overall_success=true

    # Build and run pytest command
    local pytest_cmd
    read -ra pytest_cmd <<< "$(build_pytest_command)"

    if ! run_with_timing "Running $TEST_TYPE tests" "${pytest_cmd[@]}"; then
        overall_success=false
    fi

    # Generate additional reports in CI mode
    if [ "$CI_MODE" = true ] && [ "$QUICK_MODE" = false ]; then
        print_status $YELLOW "📊 Generating CI reports..."

        # Generate JSON coverage report
        if ! run_with_timing "Generating JSON coverage report" python -m coverage json -o test_reports/coverage.json; then
            print_status $YELLOW "⚠️  Warning: Could not generate JSON coverage report"
        fi

        # Generate coverage badge data
        if [ -f "test_reports/coverage.json" ]; then
            local coverage_percent=$(python -c "
import json
try:
    with open('test_reports/coverage.json') as f:
        data = json.load(f)
    print(f\"{data['totals']['percent_covered']:.1f}\")
except:
    print('0.0')
")
            echo "{\"schemaVersion\": 1, \"label\": \"coverage\", \"message\": \"${coverage_percent}%\", \"color\": \"$([ $(echo "$coverage_percent >= $COVERAGE_THRESHOLD" | bc -l) -eq 1 ] && echo "green" || echo "red")\"}" > test_reports/coverage_badge.json
            print_status $BLUE "🏷️  Coverage badge: ${coverage_percent}%"
        fi
    fi

    # Final status
    print_status $BLUE "\n📋 Test Summary"
    print_status $BLUE "==============="

    if [ "$overall_success" = true ]; then
        print_status $GREEN "✅ All tests completed successfully!"

        # Show coverage summary if available
        if [ -f "htmlcov/index.html" ] && [ "$QUICK_MODE" = false ]; then
            print_status $BLUE "📊 Coverage report: file://$(pwd)/htmlcov/index.html"
        fi

        # Show test reports
        if [ -f "test_reports/${TEST_TYPE}_tests.xml" ]; then
            print_status $BLUE "📋 JUnit report: test_reports/${TEST_TYPE}_tests.xml"
        fi

        exit 0
    else
        print_status $RED "❌ Some tests failed!"

        # Show helpful debugging information
        print_status $YELLOW "🔍 Debugging tips:"
        echo "  - Check test output above for specific failures"
        echo "  - Run with --verbose for detailed output"
        echo "  - Use --type unit to run faster unit tests only"
        echo "  - Check test_reports/ directory for detailed reports"

        exit 1
    fi
}

# Cleanup function
cleanup() {
    print_status $YELLOW "🧹 Cleaning up..."
    # Add any cleanup logic here if needed
}

# Set trap for cleanup
trap cleanup EXIT

# Run main function
main