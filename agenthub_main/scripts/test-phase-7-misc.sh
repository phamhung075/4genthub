#!/bin/bash
# Phase 7: Miscellaneous & WebSocket Tests (remaining failures)
# Various edge cases and miscellaneous test failures

set -e

echo "════════════════════════════════════════════════════════════════"
echo "  Phase 7: Miscellaneous & WebSocket Tests"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Testing: Remaining miscellaneous test failures"
echo "Expected: Various edge cases, WebSocket updates, misc issues"
echo ""

cd "$(dirname "$0")/.."

# Run misc tests - exclude already-fixed categories
echo "Running miscellaneous tests (excluding fixed categories)..."
python -m pytest \
    src/tests/unit/ \
    -v \
    --tb=short \
    --ignore=src/tests/unit/task_management/application/use_cases/test_get_task.py \
    --ignore=src/tests/unit/task_management/application/use_cases/test_update_task.py \
    --ignore=src/tests/unit/task_management/application/use_cases/test_add_subtask_with_status_and_progress.py \
    --ignore=src/tests/unit/task_management/domain/entities/test_task_dto_serialization.py \
    --ignore=src/tests/unit/task_management/domain/value_objects/task_status_test.py \
    --ignore=src/tests/unit/task_management/domain/value_objects/test_task_status.py \
    --ignore=src/tests/unit/task_management/infrastructure/test_websocket_routes.py \
    --ignore=src/tests/unit/task_management/interface/controllers/agent_mcp_controller_test.py \
    --ignore=src/tests/unit/task_management/infrastructure/repositories/ \
    -x \
    2>&1 | tee /tmp/phase7-results.txt

# Extract summary
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Phase 7 Results Summary"
echo "════════════════════════════════════════════════════════════════"
tail -n 30 /tmp/phase7-results.txt | grep -E "(passed|failed|error|ERROR|FAILED)"

echo ""
echo "Full results saved to: /tmp/phase7-results.txt"
echo ""
echo "Common Issues to Check:"
echo "  1. Edge case handling updates"
echo "  2. API response format changes"
echo "  3. Validation rule updates"
echo "  4. Domain event changes"
echo ""
