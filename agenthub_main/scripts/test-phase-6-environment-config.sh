#!/bin/bash
# Phase 6: Environment Configuration Tests (9 failures)
# DATABASE_TYPE validation and configuration tests

set -e

echo "════════════════════════════════════════════════════════════════"
echo "  Phase 6: Environment Configuration Tests"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Testing: DATABASE_TYPE validation and environment config"
echo "Expected: ~9 failures related to DATABASE_TYPE enum validation"
echo ""

cd "$(dirname "$0")/.."

# Run environment configuration tests
echo "Running environment config tests..."
python -m pytest \
    src/tests/unit/task_management/infrastructure/configuration/ \
    -v \
    --tb=short \
    -k "database_type or DATABASE_TYPE or env" \
    2>&1 | tee /tmp/phase6-results.txt

# Also check any database config tests
echo ""
echo "Running database config tests..."
python -m pytest \
    src/tests/unit/task_management/infrastructure/database/ \
    -v \
    --tb=short \
    -k "config or type or DATABASE" \
    2>&1 | tee -a /tmp/phase6-results.txt

# Extract summary
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Phase 6 Results Summary"
echo "════════════════════════════════════════════════════════════════"
tail -n 30 /tmp/phase6-results.txt | grep -E "(passed|failed|error|ERROR|FAILED)"

echo ""
echo "Full results saved to: /tmp/phase6-results.txt"
echo ""
echo "Common Issues to Check:"
echo "  1. DATABASE_TYPE enum validation tightened"
echo "  2. Invalid DATABASE_TYPE values in tests"
echo "  3. Environment variable validation changes"
echo "  4. Configuration class constructor updates"
echo ""
