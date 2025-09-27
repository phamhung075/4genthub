#!/bin/bash
# Quick Test Coverage Script
# Part of subtask: 4fabc4f5-5750-4790-8055-68b443c7aafc

set -e

echo "🧪 Quick Test Coverage Report"
echo "============================"

cd "$(dirname "$0")"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Run tests with coverage using uv
echo -e "${YELLOW}📊 Running tests with coverage...${NC}"
uv run python -m pytest --cov=src --cov-report=html --cov-report=xml --cov-report=term-missing --tb=short -x

# Check if coverage reports were generated
if [ -f "coverage.xml" ] && [ -d "htmlcov" ]; then
    echo -e "${GREEN}✅ Coverage reports generated successfully!${NC}"

    # Extract coverage percentage
    COVERAGE=$(grep -o 'line-rate="[0-9.]*"' coverage.xml | head -1 | grep -o '[0-9.]*')
    COVERAGE_PERCENT=$(echo "$COVERAGE * 100" | bc -l | xargs printf "%.1f")

    echo -e "${YELLOW}📈 Current coverage: ${COVERAGE_PERCENT}%${NC}"

    # Display links to reports
    echo ""
    echo "📋 Coverage Reports:"
    echo "  • HTML: file://$(pwd)/htmlcov/index.html"
    echo "  • XML:  $(pwd)/coverage.xml"

    # Coverage threshold check
    THRESHOLD=80
    if (( $(echo "$COVERAGE_PERCENT >= $THRESHOLD" | bc -l) )); then
        echo -e "${GREEN}✅ Coverage meets threshold (${THRESHOLD}%)${NC}"
        exit 0
    else
        echo -e "${RED}⚠️  Coverage below threshold (${THRESHOLD}%)${NC}"
        echo "   Consider adding more tests to reach the target."
        exit 1
    fi
else
    echo -e "${RED}❌ Coverage reports not generated${NC}"
    exit 1
fi