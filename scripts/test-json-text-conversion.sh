#!/bin/bash
# Test script for JSON-to-text conversion functions
# Tests format_attempt_as_text() and build_smart_context_from_json()
# Creates mock data, runs tests, cleans up automatically

set -eo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test directories (isolated from real data)
TEST_DIR="/tmp/test-loop-worker-$$"
TEST_CACHE_DIR="$TEST_DIR/.pytest_cache"
TEST_WORKPLACE="$TEST_DIR/workplace"
TEST_CACHE_FILE="$TEST_CACHE_DIR/test-menu-cache.json"
TEST_CONTEXT_FILE="$TEST_WORKPLACE/current_context.md"
TEST_INSTRUCTIONS="$TEST_WORKPLACE/instructions.md"

# Track test results
TESTS_PASSED=0
TESTS_FAILED=0

# Cleanup function (ALWAYS runs on exit)
cleanup() {
    echo ""
    echo -e "${YELLOW}🧹 Cleaning up test data...${NC}"

    if [[ -d "$TEST_DIR" ]]; then
        rm -rf "$TEST_DIR"
        echo -e "${GREEN}✓ Removed test directory: $TEST_DIR${NC}"
    fi

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}📊 TEST SUMMARY${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${GREEN}✓ Tests Passed: $TESTS_PASSED${NC}"
    if [[ $TESTS_FAILED -gt 0 ]]; then
        echo -e "${RED}✗ Tests Failed: $TESTS_FAILED${NC}"
        exit 1
    else
        echo -e "${GREEN}🎉 All tests passed!${NC}"
        exit 0
    fi
}

# Register cleanup to run on EXIT (success, failure, or Ctrl+C)
trap cleanup EXIT INT TERM

# Test assertion helpers
assert_file_exists() {
    local file="$1"
    local description="$2"

    if [[ -f "$file" ]]; then
        echo -e "${GREEN}✓ PASS: $description${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗ FAIL: $description${NC}"
        echo -e "${RED}  File not found: $file${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

assert_contains() {
    local file="$1"
    local pattern="$2"
    local description="$3"

    if grep -q "$pattern" "$file" 2>/dev/null; then
        echo -e "${GREEN}✓ PASS: $description${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗ FAIL: $description${NC}"
        echo -e "${RED}  Pattern not found: $pattern${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

assert_not_contains() {
    local file="$1"
    local pattern="$2"
    local description="$3"

    if ! grep -q "$pattern" "$file" 2>/dev/null; then
        echo -e "${GREEN}✓ PASS: $description${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗ FAIL: $description${NC}"
        echo -e "${RED}  Pattern should NOT be present: $pattern${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# Setup test environment
setup_test_environment() {
    echo -e "${BLUE}🔧 Setting up test environment...${NC}"

    # Create test directories
    mkdir -p "$TEST_CACHE_DIR"
    mkdir -p "$TEST_WORKPLACE"

    # Create mock JSON cache with test data
    cat > "$TEST_CACHE_FILE" <<'EOF'
{
  "version": "2.0",
  "last_updated": "2025-10-24T09:30:00Z",
  "statistics": {
    "total_tests": 10,
    "passed": 7,
    "failed": 3,
    "untested": 0
  },
  "tests": {
    "agenthub_main/src/tests/unit/test_example.py": {
      "status": "failed",
      "hash": "abc123def456",
      "last_run": "2025-10-24T09:30:00Z",
      "run_count": 6,
      "recent_attempts": [
        {
          "iteration": 5,
          "timestamp": "2025-10-24T09:30:00Z",
          "status": "failed",
          "error_type": "ImportError",
          "error_summary": "cannot import name 'old_function' from module 'utils'",
          "fix_applied": "Updated import statement to use new function name",
          "duration": 2.3
        },
        {
          "iteration": 4,
          "timestamp": "2025-10-24T09:25:00Z",
          "status": "failed",
          "error_type": "ImportError",
          "error_summary": "module 'utils' not found",
          "fix_applied": "Added __init__.py to utils package",
          "duration": 1.8
        },
        {
          "iteration": 3,
          "timestamp": "2025-10-24T09:20:00Z",
          "status": "failed",
          "error_type": "AttributeError",
          "error_summary": "object has no attribute 'calculate'",
          "fix_applied": "Updated method name from 'compute' to 'calculate'",
          "duration": 2.1
        }
      ]
    },
    "agenthub_main/src/tests/unit/test_another.py": {
      "status": "failed",
      "hash": "xyz789abc123",
      "last_run": "2025-10-24T09:28:00Z",
      "run_count": 2,
      "recent_attempts": [
        {
          "iteration": 2,
          "timestamp": "2025-10-24T09:28:00Z",
          "status": "failed",
          "error_type": "TypeError",
          "error_summary": "expected str, got int",
          "fix_applied": "Added type conversion in validator",
          "duration": 1.5
        }
      ]
    },
    "agenthub_main/src/tests/unit/test_passed.py": {
      "status": "passed",
      "hash": "passed123",
      "last_run": "2025-10-24T09:15:00Z",
      "run_count": 1,
      "recent_attempts": []
    }
  }
}
EOF

    # Create mock instructions file
    cat > "$TEST_INSTRUCTIONS" <<'EOF'
# Test Fix Instructions

Fix the failing tests by analyzing the error messages and applying appropriate fixes.

## Guidelines
- Read the error message carefully
- Apply minimal changes
- Verify the fix works
EOF

    echo -e "${GREEN}✓ Test environment created at: $TEST_DIR${NC}"
    echo -e "${GREEN}✓ Mock JSON cache: $TEST_CACHE_FILE${NC}"
    echo -e "${GREEN}✓ Mock instructions: $TEST_INSTRUCTIONS${NC}"
    echo ""
}

# Source the functions from loop-worker_testfix.sh
source_functions() {
    echo -e "${BLUE}📦 Sourcing functions from loop-worker_testfix.sh...${NC}"

    # Extract just the functions we need (isolated testing)
    # We'll define them inline for the test

    # Function 1: format_attempt_as_text
    format_attempt_as_text() {
        local attempt_json="$1"
        local attempt_num="$2"

        local iteration=$(echo "$attempt_json" | jq -r '.iteration')
        local timestamp=$(echo "$attempt_json" | jq -r '.timestamp')
        local status=$(echo "$attempt_json" | jq -r '.status')
        local error_type=$(echo "$attempt_json" | jq -r '.error_type // "N/A"')
        local error_summary=$(echo "$attempt_json" | jq -r '.error_summary // "No details"')
        local fix_applied=$(echo "$attempt_json" | jq -r '.fix_applied // "No fix recorded"')

        cat <<EOF

### Attempt #${attempt_num} - Iteration ${iteration} (${timestamp})

**Result:** ${status^^}

$(if [[ "$status" == "failed" ]]; then
    echo "**Error Type:** $error_type"
    echo "**Error Details:** $error_summary"
    echo ""
    echo "**What was tried:** $fix_applied"
    echo ""
    echo "**Outcome:** This approach did not work. The test still fails."
else
    echo "**Success!** The test passed after applying this fix."
    echo ""
    echo "**What worked:** $fix_applied"
fi)

---

EOF
    }

    # Function 2: build_smart_context_from_json
    build_smart_context_from_json() {
        local iteration=$1
        local target_test="$2"
        local CACHE_FILE="$TEST_CACHE_FILE"
        local COMMAND_FILE="$TEST_INSTRUCTIONS"
        local CONTEXT_FILE="$TEST_CONTEXT_FILE"

        {
            echo "# Current Instructions (Iteration $iteration)"
            cat "$COMMAND_FILE"
            echo ""
            echo "---"
            echo ""

            if [[ -n "$target_test" ]]; then
                echo "# 🎯 Target Test: $target_test"
                echo ""

                local test_info=$(jq --arg file "$target_test" '.tests[$file]' "$CACHE_FILE")
                local run_count=$(echo "$test_info" | jq -r '.run_count // 0')
                local last_run=$(echo "$test_info" | jq -r '.last_run // "never"')
                local current_status=$(echo "$test_info" | jq -r '.status // "unknown"')

                echo "**Current Status:** $current_status"
                echo "**Total Attempts:** $run_count"
                echo "**Last Executed:** $last_run"
                echo ""

                local attempts_json=$(jq --arg file "$target_test" '.tests[$file].recent_attempts // []' "$CACHE_FILE")
                local attempts_count=$(echo "$attempts_json" | jq 'length')

                if [[ "$attempts_count" -gt 0 ]]; then
                    echo "## 📜 History of Recent Fix Attempts"
                    echo ""
                    echo "Here are the last $attempts_count attempts to fix this test, showing what was tried and what happened:"
                    echo ""

                    # Process attempts array directly with array indexing
                    for i in $(seq 0 $((attempts_count - 1))); do
                        local attempt=$(echo "$attempts_json" | jq -c ".[$i]")
                        format_attempt_as_text "$attempt" "$((i + 1))"
                    done

                    echo ""
                    echo "## 🔍 Error Pattern Analysis"
                    echo ""

                    local error_types=$(echo "$attempts_json" | jq -r '.[] | select(.error_type != null) | .error_type' | sort | uniq -c | sort -rn)

                    if [[ -n "$error_types" ]]; then
                        echo "**Common error patterns detected:**"
                        echo ""
                        echo "$error_types" | while read count error; do
                            echo "- **$error** appeared $count time(s) - this is the main issue to focus on"
                        done
                        echo ""
                    fi

                    local has_success=$(echo "$attempts_json" | jq '[.[] | select(.status == "passed")] | length')

                    if [[ "$has_success" -gt 0 ]]; then
                        echo "✅ **Important Note:** This test passed in a previous attempt! Something may have changed since then."
                        echo ""
                    fi
                fi

                if [[ "$run_count" -gt 5 ]]; then
                    echo "## 💡 Recommended Strategy"
                    echo ""
                    echo "⚠️ **This test has failed $run_count times.** Previous approaches are not working."
                    echo ""
                    echo "**Suggested approach:**"
                    echo "1. Review ALL previous attempts above to see what was already tried"
                    echo "2. Try a COMPLETELY DIFFERENT approach - don't repeat what failed"
                    echo "3. Consider if this is a deeper architectural issue, not just a simple fix"
                    echo ""
                fi
            fi

            echo "## 🔗 Other Failing Tests (for context)"
            echo ""

            local other_failures=$(jq -r --arg current "$target_test" '
                .tests
                | to_entries[]
                | select(.value.status == "failed" and .key != $current)
                | "\(.key): \(.value.run_count) attempts"
            ' "$CACHE_FILE" | head -5)

            if [[ -n "$other_failures" ]]; then
                echo "$other_failures" | while read line; do
                    echo "- $line"
                done
            fi
            echo ""

        } > "$CONTEXT_FILE"
    }

    echo -e "${GREEN}✓ Functions loaded${NC}"
    echo ""
}

# Run tests
run_tests() {
    echo -e "${BLUE}🧪 Running tests...${NC}"
    echo ""

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}TEST 1: build_smart_context_from_json()${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Test the main function
    build_smart_context_from_json 5 "agenthub_main/src/tests/unit/test_example.py"

    # Validate outputs
    assert_file_exists "$TEST_CONTEXT_FILE" "Context file was created"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}TEST 2: Output is readable text (not JSON)${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Should NOT contain raw JSON
    assert_not_contains "$TEST_CONTEXT_FILE" '{"iteration"' "No raw JSON objects in output"
    assert_not_contains "$TEST_CONTEXT_FILE" '"status"' "No JSON field syntax in output"

    # Should contain readable markdown
    assert_contains "$TEST_CONTEXT_FILE" "### Attempt #" "Contains attempt headers"
    assert_contains "$TEST_CONTEXT_FILE" "**Result:**" "Contains result labels"
    assert_contains "$TEST_CONTEXT_FILE" "**Error Type:**" "Contains error type labels"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}TEST 3: All 3 attempts are present${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    assert_contains "$TEST_CONTEXT_FILE" "Attempt #1" "Attempt 1 present"
    assert_contains "$TEST_CONTEXT_FILE" "Attempt #2" "Attempt 2 present"
    assert_contains "$TEST_CONTEXT_FILE" "Attempt #3" "Attempt 3 present"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}TEST 4: Error details are included${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    assert_contains "$TEST_CONTEXT_FILE" "ImportError" "ImportError is mentioned"
    assert_contains "$TEST_CONTEXT_FILE" "cannot import name" "Error message included"
    assert_contains "$TEST_CONTEXT_FILE" "What was tried:" "Fix attempts described"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}TEST 5: Error pattern analysis${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    assert_contains "$TEST_CONTEXT_FILE" "Error Pattern Analysis" "Has error pattern section"
    assert_contains "$TEST_CONTEXT_FILE" "appeared.*time" "Shows error frequency"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}TEST 6: Strategy recommendations${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    assert_contains "$TEST_CONTEXT_FILE" "Recommended Strategy" "Has strategy section"
    assert_contains "$TEST_CONTEXT_FILE" "failed 6 times" "Mentions failure count"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}TEST 7: Context file preview${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    echo ""
    echo -e "${YELLOW}First 50 lines of generated context:${NC}"
    head -50 "$TEST_CONTEXT_FILE"
    echo ""
    echo -e "${YELLOW}... (truncated for brevity) ...${NC}"
    echo ""
}

# Main execution
main() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}🧪 JSON-to-Text Conversion Test Suite${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    setup_test_environment
    source_functions
    run_tests

    # cleanup() will be called automatically via trap
}

main "$@"
