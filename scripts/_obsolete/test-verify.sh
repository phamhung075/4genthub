#!/bin/bash
# Quick test to verify pytest can find modules

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "Testing pytest module discovery..."

# Set up paths
PROJECT_ROOT="/home/daihungpham/__projects__/agentic-project"
export PYTHONPATH="${PROJECT_ROOT}/dhafnck_mcp_main/src:${PYTHONPATH}"

# Change to project directory
cd "${PROJECT_ROOT}/dhafnck_mcp_main"

# Try to collect tests without running them
echo "Attempting to collect tests..."
python -m pytest src/tests --collect-only --quiet 2>&1 | head -20

# Check result
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Test collection successful!${NC}"
else
    echo -e "${RED}✗ Test collection failed${NC}"
    echo "Showing detailed errors:"
    python -m pytest src/tests --collect-only --tb=short 2>&1 | head -50
fi

# Show count of collected tests
echo ""
echo "Test statistics:"
python -m pytest src/tests --collect-only -q 2>&1 | tail -5