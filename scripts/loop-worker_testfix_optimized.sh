#!/bin/bash

# ======================================================================
# TOKEN-EFFICIENT TEST FIX LOOP WORKER - Smart Cache + Auto-Retest + Recent Context
# ======================================================================
# Features:
# - Integrates with test-menu.sh cache system for fast operation
# - Intelligent cache management: auto-refresh when empty/stale
# - TOKEN-EFFICIENT context: Only last 3 results + current test
# - AUTO-RETESTS after each fix to detect newly broken tests
# - Compact error output and smart file inclusion
# - Recent results tracking to prevent token burn
# - Cache status monitoring and health indicators
# - Clear fix instructions with minimal context bloat
# ======================================================================

# Configuration
CACHE_DIR="${PROJECT_ROOT:-$(pwd)}/.test_cache"
FAILED_TESTS="${CACHE_DIR}/failed_tests.txt"
PASSED_TESTS="${CACHE_DIR}/passed_tests.txt"
CONTEXT_FILE="ai_docs/_workplace/workers/fix_tests_loop/current_context.md"
PROGRESS_FILE="ai_docs/_workplace/workers/fix_tests_loop/progress.json"
INSTRUCTIONS_FILE="ai_docs/_workplace/workers/fix_tests_loop/instructions.md"
LOG_FILE="ai_docs/_workplace/workers/fix_tests_loop/session.log"
RECENT_RESULTS_FILE="ai_docs/_workplace/workers/fix_tests_loop/recent_results.log"
DELAY_SECONDS=15
MAX_RECENT_RESULTS=3

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

# Check if cache needs refresh (empty or stale)
cache_needs_refresh() {
    local failed_count=$(wc -l < "$FAILED_TESTS" 2>/dev/null || echo "0")
    local passed_count=$(wc -l < "$PASSED_TESTS" 2>/dev/null || echo "0")
    local total_cache=$((failed_count + passed_count))

    # Cache is empty or minimal
    if [[ $total_cache -lt 3 ]]; then
        echo "empty"
        return 0
    fi

    # Check if cache files are older than 30 minutes (stale)
    if [[ -f "$FAILED_TESTS" ]] && [[ $(find "$FAILED_TESTS" -mmin +30 | wc -l) -gt 0 ]]; then
        echo "stale"
        return 0
    fi

    echo "fresh"
    return 1
}

# Add test result to recent history (keep only last 3)
add_recent_result() {
    local test_path="$1"
    local status="$2"  # "FIXED" or "FAILED"
    local details="$3"
    local timestamp=$(date -Iseconds)

    # Create result entry
    local result_entry="[$timestamp] $status: ${test_path#*/agenthub_main/}"
    if [[ -n "$details" ]]; then
        result_entry="$result_entry - $details"
    fi

    # Add to recent results file
    echo "$result_entry" >> "$RECENT_RESULTS_FILE"

    # Keep only last MAX_RECENT_RESULTS entries
    if [[ -f "$RECENT_RESULTS_FILE" ]] && [[ $(wc -l < "$RECENT_RESULTS_FILE") -gt $MAX_RECENT_RESULTS ]]; then
        tail -n $MAX_RECENT_RESULTS "$RECENT_RESULTS_FILE" > "${RECENT_RESULTS_FILE}.tmp"
        mv "${RECENT_RESULTS_FILE}.tmp" "$RECENT_RESULTS_FILE"
    fi
}

# Get recent results for context
get_recent_results() {
    if [[ -f "$RECENT_RESULTS_FILE" ]] && [[ -s "$RECENT_RESULTS_FILE" ]]; then
        cat "$RECENT_RESULTS_FILE"
    else
        echo "No recent results yet."
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

    # Add to recent results
    add_recent_result "$test_path" "FIXED" "Successfully fixed and verified"

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

# Build token-efficient context with recent results only
build_efficient_context() {
    local test_path="$1"
    local iteration="$2"

    {
        echo "# 🔧 FIX TEST: \`${test_path#*/agenthub_main/}\` (Iteration $iteration)"
        echo ""

        # Recent session context (only last 3 results to save tokens)
        echo "## 📜 Recent Results (Last 3):"
        echo '```'
        get_recent_results
        echo '```'
        echo ""

        echo "## 🎯 Task: Fix this failing test"
        echo ""

        # Compact error output (last 30 lines only)
        echo "## 🚨 Error Output:"
        echo '```bash'
        python -m pytest "$test_path" -xvs --tb=short 2>&1 | tail -30
        echo '```'
        echo ""

        # Show only test file if small, or key parts if large
        local line_count=$(wc -l < "$test_path")
        echo "## 📄 Test File (\`${test_path}\` - $line_count lines):"

        if [[ $line_count -le 50 ]]; then
            # Small file - show complete
            echo '```python'
            cat "$test_path"
            echo '```'
        else
            # Large file - show imports and main test functions only
            echo '```python'
            echo "# Imports:"
            grep -E "^(from|import)" "$test_path" | head -10
            echo ""
            echo "# Test functions:"
            grep -E "^def test_|^class Test" "$test_path" | head -5
            echo ""
            echo "# Use 'Read' tool to see full file if needed"
            echo '```'
        fi
        echo ""

        # Quick project info (very compact)
        local total_failed=$(wc -l < "$FAILED_TESTS" 2>/dev/null || echo "0")
        echo "## 📊 Status: $total_failed tests remaining"
        echo ""

        echo "**ACTION: Please fix the test to make it pass. Use Read/Edit tools as needed.**"
        echo ""
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
    echo -e "${CYAN}║${NC} ${GREEN}🤖 OPTIMIZED TEST FIX LOOP - Auto-Retest Mode${NC}              ${CYAN}║${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════════════════════════════╣${NC}"

    local total_failed=$(wc -l < "$FAILED_TESTS" 2>/dev/null || echo "0")
    local total_passed=$(wc -l < "$PASSED_TESTS" 2>/dev/null || echo "0")
    local fixed_count=$(python3 -c "import json; print(json.load(open('$PROGRESS_FILE')).get('fixed_count', 0))" 2>/dev/null || echo "0")
    local iterations=$(python3 -c "import json; print(json.load(open('$PROGRESS_FILE')).get('iterations', 0))" 2>/dev/null || echo "0")
    local cache_status=$(cache_needs_refresh)

    echo -e "${CYAN}║${NC} Failed Tests: ${RED}$total_failed${NC}    Fixed This Session: ${GREEN}$fixed_count${NC}"
    echo -e "${CYAN}║${NC} Total Passed: ${GREEN}$total_passed${NC}    Iterations: $iterations"

    # Show cache status
    case "$cache_status" in
        "empty")
            echo -e "${CYAN}║${NC} Cache Status: ${YELLOW}Empty/Minimal${NC} - Will auto-refresh on next run"
            ;;
        "stale")
            echo -e "${CYAN}║${NC} Cache Status: ${YELLOW}Stale${NC} - Will refresh soon"
            ;;
        "fresh")
            echo -e "${CYAN}║${NC} Cache Status: ${GREEN}Fresh${NC} - Using cached results"
            ;;
    esac

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

    # Initial cache check and intelligent refresh
    local failed_count=$(wc -l < "$FAILED_TESTS" 2>/dev/null || echo "0")
    local passed_count=$(wc -l < "$PASSED_TESTS" 2>/dev/null || echo "0")
    local total_cache=$((failed_count + passed_count))

    if [[ $total_cache -lt 5 ]]; then
        echo -e "${YELLOW}📊 Cache is empty/minimal ($total_cache tests) - running full test suite to build work list${NC}" | tee -a "$LOG_FILE"
        update_test_cache "all"
    else
        echo -e "${CYAN}📊 Cache has $total_cache tests ($failed_count failed, $passed_count passed) - using smart refresh${NC}" | tee -a "$LOG_FILE"
        update_test_cache "smart"
    fi

    ITERATION=0

    while true; do
        ITERATION=$((ITERATION + 1))
        update_progress "iterations" "$ITERATION"

        show_status

        # Get next failing test
        NEXT_TEST=$(get_next_failing_test)

        if [[ -z "$NEXT_TEST" ]]; then
            echo -e "${GREEN}🎉 Cache shows no failures! Validating...${NC}" | tee -a "$LOG_FILE"

            # Check if cache is empty or very small - might need full refresh
            local failed_count=$(wc -l < "$FAILED_TESTS" 2>/dev/null || echo "0")
            local passed_count=$(wc -l < "$PASSED_TESTS" 2>/dev/null || echo "0")
            local total_cache=$((failed_count + passed_count))

            if [[ $total_cache -lt 5 ]]; then
                echo -e "${YELLOW}⚠️  Cache is nearly empty ($total_cache tests) - running full test to renew work list${NC}" | tee -a "$LOG_FILE"
                update_test_cache "all"
            else
                echo -e "${CYAN}Running smart refresh to validate cache...${NC}" | tee -a "$LOG_FILE"
                update_test_cache "smart"
            fi

            # Check if any failures were discovered
            NEXT_TEST=$(get_next_failing_test)
            if [[ -n "$NEXT_TEST" ]]; then
                echo -e "${YELLOW}📍 Refresh found failures - renewing work list and continuing...${NC}" | tee -a "$LOG_FILE"
                continue
            fi

            # If still no failures after refresh, do periodic full validation
            if [[ $((ITERATION % 10)) -eq 0 ]]; then
                echo -e "${CYAN}🔍 Periodic full validation (every 10th iteration) - ensuring no hidden failures...${NC}" | tee -a "$LOG_FILE"
                update_test_cache "all"

                # Check again after full run
                NEXT_TEST=$(get_next_failing_test)
                if [[ -n "$NEXT_TEST" ]]; then
                    echo -e "${YELLOW}📍 Full validation revealed hidden failures - continuing...${NC}" | tee -a "$LOG_FILE"
                    continue
                fi
            fi

            echo -e "${GREEN}✅ All tests genuinely passing! Waiting $DELAY_SECONDS seconds before rechecking...${NC}"
            sleep $DELAY_SECONDS
            continue
        fi

        echo -e "${YELLOW}📍 Working on test:${NC} ${NEXT_TEST#*/agenthub_main/}" | tee -a "$LOG_FILE"
        update_progress "current_test" "\"$NEXT_TEST\""

        # Build efficient context with recent results only
        build_efficient_context "$NEXT_TEST" "$ITERATION"

        # Send to Claude with token-efficient context + recent results
        echo -e "${CYAN}🤖 Sending to Claude for test fixing (with recent context)...${NC}" | tee -a "$LOG_FILE"

        cat "$CONTEXT_FILE" | claude -p --dangerously-skip-permissions 2>&1 | tee -a "$LOG_FILE"

        # Wait a moment for file changes to complete
        sleep 3

        # Verify if test is fixed
        if verify_test_fix "$NEXT_TEST"; then
            mark_test_fixed "$NEXT_TEST"
            echo -e "${GREEN}✅ Test successfully fixed!${NC}" | tee -a "$LOG_FILE"

            # CRITICAL: Check if the fix broke other tests
            echo -e "${CYAN}🔍 Checking if fix introduced new failures...${NC}" | tee -a "$LOG_FILE"
            local old_failed_count=$(wc -l < "$FAILED_TESTS" 2>/dev/null || echo "0")

            # Run comprehensive test to detect newly broken tests
            update_test_cache "smart"

            local new_failed_count=$(wc -l < "$FAILED_TESTS" 2>/dev/null || echo "0")
            local failed_diff=$((new_failed_count - old_failed_count + 1))  # +1 because we just fixed one

            if [[ $failed_diff -gt 0 ]]; then
                echo -e "${YELLOW}⚠️  Fix introduced $failed_diff new test failure(s)${NC}" | tee -a "$LOG_FILE"
                echo -e "${CYAN}🔄 New failures detected - continuing loop to fix them${NC}" | tee -a "$LOG_FILE"

                # Update progress to track new failures
                local total_failures=$(wc -l < "$FAILED_TESTS" 2>/dev/null || echo "0")
                update_progress "total_failures" "$total_failures"
                echo -e "${BLUE}📊 Updated total failures: $total_failures${NC}" | tee -a "$LOG_FILE"
            else
                echo -e "${GREEN}✅ Fix didn't break any other tests${NC}" | tee -a "$LOG_FILE"
            fi
        else
            echo -e "${RED}❌ Test still failing, will retry in next iteration${NC}" | tee -a "$LOG_FILE"

            # Add to recent results
            add_recent_result "$NEXT_TEST" "FAILED" "Fix attempt unsuccessful"

            # Move test to end of failed list for round-robin
            grep -v "^${NEXT_TEST}$" "$FAILED_TESTS" > "${FAILED_TESTS}.tmp" 2>/dev/null || true
            echo "$NEXT_TEST" >> "${FAILED_TESTS}.tmp"
            mv "${FAILED_TESTS}.tmp" "$FAILED_TESTS"
        fi

        # Short delay before next iteration
        echo -e "${CYAN}⏳ Waiting $DELAY_SECONDS seconds before next test...${NC}"
        sleep $DELAY_SECONDS

        # More frequent cache refresh to catch new failures quickly
        if [[ $((ITERATION % 3)) -eq 0 ]]; then
            echo -e "${CYAN}🔄 Periodic cache refresh (iteration $ITERATION)...${NC}" | tee -a "$LOG_FILE"
            update_test_cache "smart"
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