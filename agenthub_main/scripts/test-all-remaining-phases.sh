#!/bin/bash
# Master Script: Run All Remaining Test Phases
# Executes Phase 5B, 6, and 7 sequentially and provides combined summary

set -e

SCRIPT_DIR="$(dirname "$0")"
cd "$SCRIPT_DIR/.."

echo "════════════════════════════════════════════════════════════════"
echo "  Running All Remaining Test Phases (5B, 6, 7)"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Progress So Far:"
echo "  ✅ Phase 1: TaskResponse.from_domain() signatures (9 tests)"
echo "  ✅ Phase 2: Computed properties (13 tests)"
echo "  ✅ Phase 3: WebSocket & business logic (3 tests)"
echo "  ✅ Phase 4: Agent controller config (12 tests)"
echo "  ✅ Phase 5A: Repository session injection (26 tests)"
echo "  📊 TOTAL FIXED: 63 of 102 tests (61.8%)"
echo ""
echo "Remaining Phases to Execute:"
echo "  🔄 Phase 5B: Repository errors (~47 errors)"
echo "  🔄 Phase 6: Environment config (~9 failures)"
echo "  🔄 Phase 7: Miscellaneous (~9+ failures)"
echo ""
read -p "Press Enter to start all remaining phases..."

# Phase 5B: Repository Errors
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Starting Phase 5B: Repository Errors"
echo "════════════════════════════════════════════════════════════════"
bash "$SCRIPT_DIR/test-phase-5b-repository-errors.sh"

# Phase 6: Environment Config
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Starting Phase 6: Environment Configuration"
echo "════════════════════════════════════════════════════════════════"
bash "$SCRIPT_DIR/test-phase-6-environment-config.sh"

# Phase 7: Miscellaneous
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Starting Phase 7: Miscellaneous Tests"
echo "════════════════════════════════════════════════════════════════"
bash "$SCRIPT_DIR/test-phase-7-misc.sh"

# Final Summary
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Final Combined Summary"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Phase 5B Results:"
grep -E "passed|failed|error" /tmp/phase5b-results.txt | tail -n 1 || echo "Check /tmp/phase5b-results.txt"
echo ""
echo "Phase 6 Results:"
grep -E "passed|failed|error" /tmp/phase6-results.txt | tail -n 1 || echo "Check /tmp/phase6-results.txt"
echo ""
echo "Phase 7 Results:"
grep -E "passed|failed|error" /tmp/phase7-results.txt | tail -n 1 || echo "Check /tmp/phase7-results.txt"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  All Phases Complete!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Detailed results available at:"
echo "  - /tmp/phase5b-results.txt"
echo "  - /tmp/phase6-results.txt"
echo "  - /tmp/phase7-results.txt"
echo ""
