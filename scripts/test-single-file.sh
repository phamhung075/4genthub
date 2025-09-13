#!/bin/bash
# Single test file runner that avoids creating files in project root

if [ -z "$1" ]; then
    echo "Usage: $0 <test_file_path>"
    echo "Example: $0 dhafnck_mcp_main/src/tests/unit/auth/services/auth_services_module_init_test.py"
    exit 1
fi

TEST_FILE="$1"
PROJECT_ROOT="/home/daihungpham/__projects__/agentic-project"

# Ensure we're in the right directory
cd "$PROJECT_ROOT/dhafnck_mcp_main" || exit 1

# Create a temporary directory for pytest cache
TEMP_DIR=$(mktemp -d)
export PYTEST_CACHE_DIR="$TEMP_DIR/.pytest_cache"

# Run the test with cache in temp directory
python -m pytest "$PROJECT_ROOT/$TEST_FILE" \
    -xvs \
    --tb=short \
    --cache-dir="$TEMP_DIR/.pytest_cache" \
    --rootdir="$TEMP_DIR" \
    2>&1

# Clean up temp directory
rm -rf "$TEMP_DIR"