#!/bin/bash
# Phase 5B: Repository Error Tests (Remaining 47 errors from different root causes)
# Run remaining repository tests that have errors beyond session injection

set -e

echo "════════════════════════════════════════════════════════════════"
echo "  Phase 5B: Repository Tests - Remaining Errors"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Testing: Repository tests with import/dependency errors"
echo "Expected: ~47 errors to investigate and fix"
echo ""

cd "$(dirname "$0")/.."

# Run repository tests and capture results
echo "Running repository tests..."
python -m pytest \
    src/tests/unit/task_management/infrastructure/repositories/orm/ \
    -v \
    --tb=short \
    -x \
    2>&1 | tee /tmp/phase5b-results.txt

# Extract summary
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Phase 5B Results Summary"
echo "════════════════════════════════════════════════════════════════"
tail -n 30 /tmp/phase5b-results.txt | grep -E "(passed|failed|error|ERROR|FAILED)"

echo ""
echo "Full results saved to: /tmp/phase5b-results.txt"
echo ""
echo "Common Issues to Check:"
echo "  1. Import errors for moved/renamed classes"
echo "  2. Missing mock dependencies"
echo "  3. Changed method signatures"
echo "  4. Updated repository interfaces"
echo ""
