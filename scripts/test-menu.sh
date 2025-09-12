#!/bin/bash

# Smart Test Menu System for DhafnckMCP
# Features intelligent caching to skip passed tests and rerun only failures
# Created: 2025-09-12

set -e

# Colors for better UI
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Project paths - handle both direct execution and symlink
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$(basename "$SCRIPT_DIR")" == "scripts" ]]; then
    # Running from scripts directory
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
else
    # Running from project root (symlink)
    PROJECT_ROOT="$(pwd)"
fi
TEST_DIR="${PROJECT_ROOT}/dhafnck_mcp_main/src/tests"
VENV_PATH="${PROJECT_ROOT}/venv"

# Smart cache paths for test results
CACHE_DIR="${PROJECT_ROOT}/.test_cache"
PASSED_TESTS="${CACHE_DIR}/passed_tests.txt"
FAILED_TESTS="${CACHE_DIR}/failed_tests.txt"
TEST_HASHES="${CACHE_DIR}/test_hashes.txt"
RUN_LOG="${CACHE_DIR}/last_run.log"
STATS_FILE="${CACHE_DIR}/stats.txt"

# Create cache directory if it doesn't exist
mkdir -p "${CACHE_DIR}"

# Initialize cache files if they don't exist
touch "${PASSED_TESTS}" "${FAILED_TESTS}" "${TEST_HASHES}" "${STATS_FILE}"

# Function to calculate hash of a test file
get_file_hash() {
    local file="$1"
    if [ -f "$file" ]; then
        md5sum "$file" | cut -d' ' -f1
    else
        echo "MISSING"
    fi
}

# Function to check if test file has changed
has_test_changed() {
    local test_file="$1"
    local current_hash=$(get_file_hash "$test_file")
    local cached_hash=$(grep "^${test_file}:" "${TEST_HASHES}" 2>/dev/null | cut -d':' -f2)
    
    if [ "$current_hash" != "$cached_hash" ]; then
        return 0  # Changed
    else
        return 1  # Not changed
    fi
}

# Function to update test hash
update_test_hash() {
    local test_file="$1"
    local new_hash=$(get_file_hash "$test_file")
    
    # Remove old hash if exists
    grep -v "^${test_file}:" "${TEST_HASHES}" > "${TEST_HASHES}.tmp" 2>/dev/null || true
    mv "${TEST_HASHES}.tmp" "${TEST_HASHES}"
    
    # Add new hash
    echo "${test_file}:${new_hash}" >> "${TEST_HASHES}"
}

# Function to mark test as passed
mark_test_passed() {
    local test="$1"
    # Remove from failed if exists
    grep -v "^${test}$" "${FAILED_TESTS}" > "${FAILED_TESTS}.tmp" 2>/dev/null || true
    mv "${FAILED_TESTS}.tmp" "${FAILED_TESTS}"
    
    # Add to passed if not already there
    if ! grep -q "^${test}$" "${PASSED_TESTS}" 2>/dev/null; then
        echo "$test" >> "${PASSED_TESTS}"
    fi
    
    # Update hash
    update_test_hash "$test"
}

# Function to mark test as failed
mark_test_failed() {
    local test="$1"
    # Remove from passed if exists
    grep -v "^${test}$" "${PASSED_TESTS}" > "${PASSED_TESTS}.tmp" 2>/dev/null || true
    mv "${PASSED_TESTS}.tmp" "${PASSED_TESTS}"
    
    # Add to failed if not already there
    if ! grep -q "^${test}$" "${FAILED_TESTS}" 2>/dev/null; then
        echo "$test" >> "${FAILED_TESTS}"
    fi
}

# Function to get test statistics
get_test_stats() {
    local total_tests=$(find "${TEST_DIR}" -name "*test*.py" -type f | wc -l)
    local passed_count=$(wc -l < "${PASSED_TESTS}" 2>/dev/null || echo 0)
    local failed_count=$(wc -l < "${FAILED_TESTS}" 2>/dev/null || echo 0)
    local cached_count=$((passed_count))
    local untested_count=$((total_tests - passed_count - failed_count))
    
    echo "total:${total_tests}"
    echo "passed:${passed_count}"
    echo "failed:${failed_count}"
    echo "cached:${cached_count}"
    echo "untested:${untested_count}"
}

# Function to print header with stats
print_header() {
    clear
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${WHITE}${BOLD}        🧪 SMART TEST RUNNER - DhafnckMCP 🧪                   ${CYAN}║${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════════════════════════════╣${NC}"
    
    # Get statistics
    local stats=$(get_test_stats)
    local total=$(echo "$stats" | grep "^total:" | cut -d':' -f2)
    local passed=$(echo "$stats" | grep "^passed:" | cut -d':' -f2)
    local failed=$(echo "$stats" | grep "^failed:" | cut -d':' -f2)
    local cached=$(echo "$stats" | grep "^cached:" | cut -d':' -f2)
    
    echo -e "${CYAN}║${NC} ${BOLD}Test Statistics:${NC}"
    echo -e "${CYAN}║${NC}   Total Tests: ${WHITE}${total}${NC}"
    echo -e "${CYAN}║${NC}   ${GREEN}✓ Passed (Cached):${NC} ${GREEN}${passed}${NC}"
    echo -e "${CYAN}║${NC}   ${RED}✗ Failed:${NC} ${RED}${failed}${NC}"
    echo -e "${CYAN}║${NC}   ${YELLOW}⚡ Will Skip (Cached):${NC} ${YELLOW}${cached}${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
}

# Function to print menu
print_menu() {
    echo ""
    echo -e "${YELLOW}${BOLD}═══ SMART TEST EXECUTION ═══${NC}"
    echo -e "${GREEN}1${NC})  🚀 ${BOLD}Run Backend Tests${NC} (Skip cached passed tests)"
    echo -e "${GREEN}2${NC})  🔴 ${BOLD}Run Failed Tests Only${NC}"
    echo -e "${GREEN}3${NC})  🔄 ${BOLD}Run All Tests${NC} (Ignore cache)"
    echo -e "${GREEN}4${NC})  📝 ${BOLD}Run Specific Test File${NC}"
    echo ""
    echo -e "${YELLOW}${BOLD}═══ CACHE MANAGEMENT ═══${NC}"
    echo -e "${BLUE}5${NC})  🗑️  ${BOLD}Clear All Cache${NC} (Force full rerun)"
    echo -e "${BLUE}6${NC})  🧹 ${BOLD}Clear Failed Tests Cache${NC}"
    echo -e "${BLUE}7${NC})  📊 ${BOLD}Show Cache Statistics${NC}"
    echo -e "${BLUE}8${NC})  📋 ${BOLD}List Cached Tests${NC}"
    echo ""
    echo -e "${YELLOW}${BOLD}═══ TEST CATEGORIES ═══${NC}"
    echo -e "${MAGENTA}10${NC}) Run Unit Tests"
    echo -e "${MAGENTA}11${NC}) Run Integration Tests"
    echo -e "${MAGENTA}12${NC}) Run E2E Tests"
    echo -e "${MAGENTA}13${NC}) Run Performance Tests"
    echo ""
    echo -e "${YELLOW}${BOLD}═══ UTILITIES ═══${NC}"
    echo -e "${CYAN}20${NC}) 📈 Generate Coverage Report"
    echo -e "${CYAN}21${NC}) 🔍 Find Obsolete Tests"
    echo -e "${CYAN}22${NC}) 📜 View Last Run Log"
    echo ""
    echo -e "${RED}Q${NC})  Quit"
    echo ""
}

# Function to run tests with smart caching
run_smart_tests() {
    local mode="$1"
    local specific_path="$2"
    
    echo -e "${CYAN}${BOLD}Starting Smart Test Run...${NC}\n"
    
    # Prepare test list based on mode
    local tests_to_run=""
    local tests_to_skip=""
    
    case "$mode" in
        "smart")
            echo -e "${YELLOW}Mode: Smart (Skip cached passed tests)${NC}"
            # Find all test files
            while IFS= read -r test_file; do
                # Check if test is in passed cache and hasn't changed
                if grep -q "^${test_file}$" "${PASSED_TESTS}" 2>/dev/null; then
                    if ! has_test_changed "$test_file"; then
                        tests_to_skip="${tests_to_skip} ${test_file}"
                        echo -e "${GREEN}⚡ Skipping (cached):${NC} ${test_file#${PROJECT_ROOT}/}"
                    else
                        tests_to_run="${tests_to_run} ${test_file}"
                        echo -e "${YELLOW}↻ Re-running (changed):${NC} ${test_file#${PROJECT_ROOT}/}"
                    fi
                else
                    tests_to_run="${tests_to_run} ${test_file}"
                    if grep -q "^${test_file}$" "${FAILED_TESTS}" 2>/dev/null; then
                        echo -e "${RED}↻ Re-running (failed):${NC} ${test_file#${PROJECT_ROOT}/}"
                    else
                        echo -e "${BLUE}→ Running (new):${NC} ${test_file#${PROJECT_ROOT}/}"
                    fi
                fi
            done < <(find "${TEST_DIR}" -name "*test*.py" -type f)
            ;;
            
        "failed")
            echo -e "${YELLOW}Mode: Failed tests only${NC}"
            if [ -s "${FAILED_TESTS}" ]; then
                tests_to_run=$(cat "${FAILED_TESTS}")
                echo -e "${RED}Running ${NC}$(wc -l < "${FAILED_TESTS}")${RED} failed tests${NC}"
            else
                echo -e "${GREEN}No failed tests to run!${NC}"
                return 0
            fi
            ;;
            
        "all")
            echo -e "${YELLOW}Mode: All tests (ignoring cache)${NC}"
            tests_to_run=$(find "${TEST_DIR}" -name "*test*.py" -type f)
            ;;
            
        "specific")
            echo -e "${YELLOW}Mode: Specific test${NC}"
            tests_to_run="$specific_path"
            ;;
    esac
    
    # Run the tests if there are any
    if [ -n "$tests_to_run" ]; then
        echo -e "\n${CYAN}${BOLD}Running tests...${NC}\n"
        
        # Count tests to run
        local test_count=$(echo "$tests_to_run" | wc -w)
        echo -e "${YELLOW}Tests to run: ${test_count}${NC}\n"
        
        # Set environment variables
        export PYTHONDONTWRITEBYTECODE=1
        export PYTEST_CURRENT_TEST_DIR="${TEST_DIR}"
        
        # Run pytest and capture results
        cd "${PROJECT_ROOT}"
        
        # Create temporary file for test results
        local temp_results="${CACHE_DIR}/temp_results.txt"
        > "$temp_results"
        
        # Run tests and parse results
        python -m pytest $tests_to_run -v --tb=short 2>&1 | tee "${RUN_LOG}" | while IFS= read -r line; do
            # Parse test results
            if echo "$line" | grep -q "PASSED"; then
                local test_name=$(echo "$line" | sed -n 's/.*\(src\/tests\/.*\.py\).*/\1/p')
                if [ -n "$test_name" ]; then
                    echo "PASSED:${PROJECT_ROOT}/${test_name}" >> "$temp_results"
                fi
            elif echo "$line" | grep -q "FAILED"; then
                local test_name=$(echo "$line" | sed -n 's/.*\(src\/tests\/.*\.py\).*/\1/p')
                if [ -n "$test_name" ]; then
                    echo "FAILED:${PROJECT_ROOT}/${test_name}" >> "$temp_results"
                fi
            fi
            echo "$line"
        done
        
        # Update cache based on results
        echo -e "\n${CYAN}${BOLD}Updating cache...${NC}"
        while IFS=: read -r status test_file; do
            if [ "$status" = "PASSED" ]; then
                mark_test_passed "$test_file"
                echo -e "${GREEN}✓ Cached as passed:${NC} ${test_file#${PROJECT_ROOT}/}"
            elif [ "$status" = "FAILED" ]; then
                mark_test_failed "$test_file"
                echo -e "${RED}✗ Marked as failed:${NC} ${test_file#${PROJECT_ROOT}/}"
            fi
        done < "$temp_results"
        
        # Clean up
        rm -f "$temp_results"
    else
        echo -e "${GREEN}${BOLD}All tests are cached and passing! Nothing to run.${NC}"
    fi
    
    # Show final statistics
    echo -e "\n${CYAN}${BOLD}Test Run Complete!${NC}"
    show_statistics
}

# Function to clear cache
clear_cache() {
    local cache_type="$1"
    
    case "$cache_type" in
        "all")
            echo -e "${YELLOW}Clearing all cache...${NC}"
            > "${PASSED_TESTS}"
            > "${FAILED_TESTS}"
            > "${TEST_HASHES}"
            > "${STATS_FILE}"
            echo -e "${GREEN}✓ All cache cleared!${NC}"
            ;;
        "failed")
            echo -e "${YELLOW}Clearing failed tests cache...${NC}"
            > "${FAILED_TESTS}"
            echo -e "${GREEN}✓ Failed tests cache cleared!${NC}"
            ;;
    esac
}

# Function to show statistics
show_statistics() {
    echo ""
    echo -e "${CYAN}${BOLD}═══ Cache Statistics ═══${NC}"
    
    local stats=$(get_test_stats)
    local total=$(echo "$stats" | grep "^total:" | cut -d':' -f2)
    local passed=$(echo "$stats" | grep "^passed:" | cut -d':' -f2)
    local failed=$(echo "$stats" | grep "^failed:" | cut -d':' -f2)
    local cached=$(echo "$stats" | grep "^cached:" | cut -d':' -f2)
    local untested=$(echo "$stats" | grep "^untested:" | cut -d':' -f2)
    
    # Calculate percentages
    local pass_rate=0
    if [ "$total" -gt 0 ]; then
        pass_rate=$((passed * 100 / total))
    fi
    
    echo -e "  Total Tests:        ${WHITE}${total}${NC}"
    echo -e "  ${GREEN}Passed (Cached):    ${passed}${NC} (${pass_rate}%)"
    echo -e "  ${RED}Failed:             ${failed}${NC}"
    echo -e "  ${YELLOW}Untested:           ${untested}${NC}"
    echo -e "  ${CYAN}Cache Efficiency:   ${cached}${NC} tests will be skipped"
    
    # Show cache size
    local cache_size=$(du -sh "${CACHE_DIR}" 2>/dev/null | cut -f1)
    echo -e "  Cache Size:         ${cache_size}"
}

# Function to list cached tests
list_cached_tests() {
    echo -e "${CYAN}${BOLD}═══ Cached Passed Tests ═══${NC}"
    if [ -s "${PASSED_TESTS}" ]; then
        cat "${PASSED_TESTS}" | while read test; do
            echo -e "${GREEN}✓${NC} ${test#${PROJECT_ROOT}/}"
        done
    else
        echo -e "${YELLOW}No passed tests cached yet${NC}"
    fi
    
    echo -e "\n${CYAN}${BOLD}═══ Failed Tests ═══${NC}"
    if [ -s "${FAILED_TESTS}" ]; then
        cat "${FAILED_TESTS}" | while read test; do
            echo -e "${RED}✗${NC} ${test#${PROJECT_ROOT}/}"
        done
    else
        echo -e "${GREEN}No failed tests!${NC}"
    fi
}

# Function to find obsolete tests
find_obsolete_tests() {
    echo -e "${CYAN}${BOLD}Searching for obsolete tests...${NC}\n"
    
    echo -e "${YELLOW}Tests with deprecated imports:${NC}"
    grep -r "TaskContextRepository\|manage_hierarchical_context\|deprecated\|legacy" \
        "${TEST_DIR}" --include="*.py" 2>/dev/null | \
        cut -d: -f1 | sort -u | while read file; do
        echo -e "  ${RED}⚠${NC} ${file#${PROJECT_ROOT}/}"
    done
    
    echo -e "\n${YELLOW}Tests not following naming convention:${NC}"
    find "${TEST_DIR}" -name "*.py" -type f | \
        grep -v -E "(test_.*\.py|.*_test\.py|__init__\.py|conftest\.py)" | \
        while read file; do
        echo -e "  ${YELLOW}⚠${NC} ${file#${PROJECT_ROOT}/}"
    done
}

# Function to run specific category
run_category() {
    local category="$1"
    local path="${TEST_DIR}/${category}"
    
    if [ -d "$path" ]; then
        echo -e "${CYAN}Running ${category} tests...${NC}"
        cd "${PROJECT_ROOT}"
        python -m pytest "$path" -v --tb=short 2>&1 | tee "${RUN_LOG}"
    else
        echo -e "${RED}Category ${category} not found!${NC}"
    fi
}

# Main menu loop
main() {
    while true; do
        print_header
        print_menu
        
        read -p "$(echo -e ${BOLD}Select option:${NC} )" choice
        echo ""
        
        case $choice in
            1)
                run_smart_tests "smart"
                ;;
            2)
                run_smart_tests "failed"
                ;;
            3)
                run_smart_tests "all"
                ;;
            4)
                read -p "Enter test file path: " test_path
                run_smart_tests "specific" "$test_path"
                ;;
            5)
                clear_cache "all"
                ;;
            6)
                clear_cache "failed"
                ;;
            7)
                show_statistics
                ;;
            8)
                list_cached_tests
                ;;
            10)
                run_category "unit"
                ;;
            11)
                run_category "integration"
                ;;
            12)
                run_category "e2e"
                ;;
            13)
                run_category "performance"
                ;;
            20)
                echo -e "${CYAN}Generating coverage report...${NC}"
                cd "${PROJECT_ROOT}"
                python -m pytest "${TEST_DIR}" --cov=src --cov-report=html --cov-report=term
                echo -e "${GREEN}Coverage report generated!${NC}"
                ;;
            21)
                find_obsolete_tests
                ;;
            22)
                if [ -f "${RUN_LOG}" ]; then
                    less "${RUN_LOG}"
                else
                    echo -e "${RED}No run log found!${NC}"
                fi
                ;;
            [Qq])
                echo -e "${GREEN}${BOLD}Goodbye!${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid option!${NC}"
                ;;
        esac
        
        echo ""
        read -p "$(echo -e ${YELLOW}Press Enter to continue...${NC})"
    done
}

# Debug path information
echo "Debug info:"
echo "SCRIPT_DIR: $SCRIPT_DIR"
echo "PROJECT_ROOT: $PROJECT_ROOT"
echo "TEST_DIR: $TEST_DIR"
echo "Current PWD: $(pwd)"
echo ""

# Check if running from correct directory
if [ ! -d "${TEST_DIR}" ]; then
    echo -e "${RED}Error: Test directory not found at ${TEST_DIR}${NC}"
    echo -e "${YELLOW}Please run this script from the project root${NC}"
    echo -e "${YELLOW}Available directories in PROJECT_ROOT:${NC}"
    ls -la "${PROJECT_ROOT}/" | grep "^d"
    exit 1
fi

# Initialize stats on first run
if [ ! -s "${STATS_FILE}" ]; then
    get_test_stats > "${STATS_FILE}"
fi

# Start the menu
main