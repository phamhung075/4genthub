#!/bin/bash

# ======================================================================
# OPTIMIZED TEST FIX LOOP WORKER - Minimal Token Usage + Cache Integration
# ======================================================================
# Features:
# - Integrates with test-menu.sh cache system
# - Only sends failed tests and recent fixes to AI
# - Uses incremental context instead of accumulating all history
# - Tracks progress without bloating context
# ======================================================================

# Configuration
CACHE_DIR="${PROJECT_ROOT:-$(pwd)}/.test_cache"
FAILED_TESTS="${CACHE_DIR}/failed_tests.txt"
PASSED_TESTS="${CACHE_DIR}/passed_tests.txt"
CONTEXT_FILE="ai_docs/_workplace/workers/fix_tests_loop/current_context.md"
PROGRESS_FILE="ai_docs/_workplace/workers/fix_tests_loop/progress.json"
INSTRUCTIONS_FILE="ai_docs/_workplace/workers/fix_tests_loop/instructions.md"
LOG_FILE="ai_docs/_workplace/workers/fix_tests_loop/session.log"
DELAY_SECONDS=15

# Create directories
mkdir -p "$(dirname "$CONTEXT_FILE")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Initialize progress tracking
init_progress() {
    if [[ ! -f "$PROGRESS_FILE" ]]; then
        echo '{
  "session_start": "'$(date -Iseconds)'",
  "total_failures": 0,
  "fixed_count": 0,
  "current_test": null,
  "iterations": 0
}' > "$PROGRESS_FILE"
    fi
}

# Update progress without bloating context
update_progress() {
    local field="$1"
    local value="$2"

    # Use python for JSON manipulation
    python3 -c "
import json
with open('$PROGRESS_FILE', 'r') as f:
    data = json.load(f)
data['$field'] = $value
data['last_update'] = '$(date -Iseconds)'
with open('$PROGRESS_FILE', 'w') as f:
    json.dump(data, f, indent=2)
"
}

# Get next failing test from cache
get_next_failing_test() {
    if [[ -s "$FAILED_TESTS" ]]; then
        head -1 "$FAILED_TESTS"
    else
        echo ""
    fi
}

# Move test from failed to passed
mark_test_fixed() {
    local test_path="$1"

    # Remove from failed list
    grep -v "^${test_path}$" "$FAILED_TESTS" > "${FAILED_TESTS}.tmp" 2>/dev/null || true
    mv "${FAILED_TESTS}.tmp" "$FAILED_TESTS"

    # Add to passed list
    echo "$test_path" >> "$PASSED_TESTS"

    # Update progress
    local fixed_count=$(python3 -c "import json; data=json.load(open('$PROGRESS_FILE')); print(data.get('fixed_count', 0) + 1)")
    update_progress "fixed_count" "$fixed_count"

    echo -e "${GREEN}✓ Test marked as fixed:${NC} ${test_path#*/agenthub_main/}" | tee -a "$LOG_FILE"
}

# Run single test to verify fix
verify_test_fix() {
    local test_path="$1"

    echo -e "${CYAN}🔍 Verifying test:${NC} ${test_path#*/agenthub_main/}" | tee -a "$LOG_FILE"

    # Run the specific test
    if python -m pytest "$test_path" -xvs 2>&1 | tee -a "$LOG_FILE" | grep -q "PASSED"; then
        return 0  # Test passed
    else
        return 1  # Test still failing
    fi
}

# Build minimal context for AI (token-efficient)
build_minimal_context() {
    local test_path="$1"
    local iteration="$2"

    {
        echo "# Test Fix Request - Iteration $iteration"
        echo "Timestamp: $(date -Iseconds)"
        echo ""

        # Include custom instructions if exists
        if [[ -f "$INSTRUCTIONS_FILE" ]]; then
            echo "## Instructions:"
            cat "$INSTRUCTIONS_FILE"
            echo ""
        fi

        echo "## Current Task:"
        echo "Fix the failing test: \`${test_path#*/agenthub_main/}\`"
        echo ""

        # Get test failure output (last 50 lines only to save tokens)
        echo "## Test Failure Output:"
        echo '```'
        python -m pytest "$test_path" -xvs 2>&1 | tail -50
        echo '```'
        echo ""

        # Include test file content (first 100 lines for context)
        echo "## Test File Content (first 100 lines):"
        echo '```python'
        head -100 "$test_path"
        echo '```'

        if [[ $(wc -l < "$test_path") -gt 100 ]]; then
            echo "*(File has $(wc -l < "$test_path") total lines)*"
        fi
        echo ""

        # Quick progress summary (minimal)
        local total_failed=$(wc -l < "$FAILED_TESTS" 2>/dev/null || echo "0")
        local fixed_count=$(python3 -c "import json; print(json.load(open('$PROGRESS_FILE')).get('fixed_count', 0))" 2>/dev/null || echo "0")

        echo "## Progress:"
        echo "- Tests remaining: $total_failed"
        echo "- Tests fixed this session: $fixed_count"
        echo "- Current iteration: $iteration"
        echo ""

        echo "## Action Required:"
        echo "1. Analyze the test failure"
        echo "2. Fix the issue in the test file"
        echo "3. Ensure the fix follows project patterns"
        echo ""
        echo "*Note: Focus only on fixing this specific test. Context is minimal to save tokens.*"
    } > "$CONTEXT_FILE"

    # Log context size
    local context_size=$(wc -c < "$CONTEXT_FILE")
    local context_lines=$(wc -l < "$CONTEXT_FILE")
    echo -e "${BLUE}📊 Context size: ${context_lines} lines, ${context_size} chars${NC}" | tee -a "$LOG_FILE"
}

# Run test-menu.sh to update cache
update_test_cache() {
    local mode="${1:-failed}"  # Default to "failed" mode, accept parameter for different modes

    echo -e "${CYAN}🔄 Updating test cache (${mode} mode)...${NC}" | tee -a "$LOG_FILE"

    if [[ -f "test-menu.sh" ]]; then
        case "$mode" in
            "smart")
                echo "1" | ./test-menu.sh > /dev/null 2>&1  # Run smart mode (skip cached passed tests)
                ;;
            "all")
                echo "3" | ./test-menu.sh > /dev/null 2>&1  # Run all tests (ignore cache)
                ;;
            "failed"|*)
                echo "2" | ./test-menu.sh > /dev/null 2>&1  # Run failed tests only (default)
                ;;
        esac
    else
        echo -e "${YELLOW}⚠️  test-menu.sh not found, using existing cache${NC}" | tee -a "$LOG_FILE"
    fi
}

# Display status dashboard
show_status() {
    clear
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${GREEN}🤖 OPTIMIZED TEST FIX LOOP - Token Efficient Mode${NC}           ${CYAN}║${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════════════════════════════╣${NC}"

    local total_failed=$(wc -l < "$FAILED_TESTS" 2>/dev/null || echo "0")
    local total_passed=$(wc -l < "$PASSED_TESTS" 2>/dev/null || echo "0")
    local fixed_count=$(python3 -c "import json; print(json.load(open('$PROGRESS_FILE')).get('fixed_count', 0))" 2>/dev/null || echo "0")
    local iterations=$(python3 -c "import json; print(json.load(open('$PROGRESS_FILE')).get('iterations', 0))" 2>/dev/null || echo "0")

    echo -e "${CYAN}║${NC} Failed Tests: ${RED}$total_failed${NC}    Fixed This Session: ${GREEN}$fixed_count${NC}"
    echo -e "${CYAN}║${NC} Total Passed: ${GREEN}$total_passed${NC}    Iterations: $iterations"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Cleanup on exit
cleanup_and_exit() {
    echo ""
    echo -e "${YELLOW}🛑 Script terminated${NC}" | tee -a "$LOG_FILE"

    # Show final statistics
    local fixed_count=$(python3 -c "import json; print(json.load(open('$PROGRESS_FILE')).get('fixed_count', 0))" 2>/dev/null || echo "0")
    echo -e "${GREEN}✅ Fixed $fixed_count tests this session${NC}" | tee -a "$LOG_FILE"

    exit 0
}

trap cleanup_and_exit SIGINT SIGTERM

# Main execution
main() {
    echo "Starting Optimized Test Fix Loop - $(date)" | tee "$LOG_FILE"
    init_progress

    # Initial cache update - use smart mode for comprehensive scan
    update_test_cache "smart"

    ITERATION=0

    while true; do
        ITERATION=$((ITERATION + 1))
        update_progress "iterations" "$ITERATION"

        show_status

        # Get next failing test
        NEXT_TEST=$(get_next_failing_test)

        if [[ -z "$NEXT_TEST" ]]; then
            echo -e "${GREEN}🎉 All tests are passing! No failures found.${NC}" | tee -a "$LOG_FILE"
            echo -e "${CYAN}Running comprehensive cache refresh to check for new failures...${NC}" | tee -a "$LOG_FILE"
            update_test_cache "smart"  # Use smart mode to discover any newly failing tests
            echo -e "${CYAN}Waiting $DELAY_SECONDS seconds before rechecking...${NC}"
            sleep $DELAY_SECONDS
            continue
        fi

        echo -e "${YELLOW}📍 Working on test:${NC} ${NEXT_TEST#*/agenthub_main/}" | tee -a "$LOG_FILE"
        update_progress "current_test" "\"$NEXT_TEST\""

        # Build minimal context (token-efficient)
        build_minimal_context "$NEXT_TEST" "$ITERATION"

        # Send to Claude with minimal context
        echo -e "${CYAN}🤖 Sending to Claude for analysis...${NC}" | tee -a "$LOG_FILE"

        cat "$CONTEXT_FILE" | claude -p --dangerously-skip-permissions 2>&1 | tee -a "$LOG_FILE"

        # Wait a moment for file changes to complete
        sleep 3

        # Verify if test is fixed
        if verify_test_fix "$NEXT_TEST"; then
            mark_test_fixed "$NEXT_TEST"
            echo -e "${GREEN}✅ Test successfully fixed!${NC}" | tee -a "$LOG_FILE"
        else
            echo -e "${RED}❌ Test still failing, will retry in next iteration${NC}" | tee -a "$LOG_FILE"
            # Move test to end of failed list for round-robin
            grep -v "^${NEXT_TEST}$" "$FAILED_TESTS" > "${FAILED_TESTS}.tmp" 2>/dev/null || true
            echo "$NEXT_TEST" >> "${FAILED_TESTS}.tmp"
            mv "${FAILED_TESTS}.tmp" "$FAILED_TESTS"
        fi

        # Short delay before next iteration
        echo -e "${CYAN}⏳ Waiting $DELAY_SECONDS seconds before next test...${NC}"
        sleep $DELAY_SECONDS

        # Periodically refresh cache (every 5 iterations)
        if [[ $((ITERATION % 5)) -eq 0 ]]; then
            update_test_cache
        fi
    done
}

# Check prerequisites
if [[ ! -d "$CACHE_DIR" ]]; then
    echo -e "${RED}Error: Test cache directory not found at $CACHE_DIR${NC}"
    echo -e "${YELLOW}Run test-menu.sh first to initialize the cache${NC}"
    exit 1
fi

# Start main loop
main