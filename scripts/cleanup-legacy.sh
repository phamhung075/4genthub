#!/bin/bash
# DhafnckMCP Legacy Cleanup Script
# Phase 6: Clean up unused files and legacy configurations
# Version: 2.1.0 - Safe cleanup with backup option

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RESET='\033[0m'
BOLD='\033[1m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
CLEANUP_LOG="${PROJECT_ROOT}/logs/cleanup-$(date +%Y%m%d-%H%M%S).log"
BACKUP_DIR="${PROJECT_ROOT}/logs/cleanup-backup-$(date +%Y%m%d-%H%M%S)"
DRY_RUN="${DRY_RUN:-false}"

# Ensure log directory exists
mkdir -p "$(dirname "$CLEANUP_LOG")" "$BACKUP_DIR"

# Logging functions
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${RESET} $1" | tee -a "$CLEANUP_LOG"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${RESET} $1" | tee -a "$CLEANUP_LOG"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${RESET} $1" | tee -a "$CLEANUP_LOG"
}

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${RESET} $1" | tee -a "$CLEANUP_LOG"
}

# Backup function
backup_file() {
    local file="$1"
    local backup_path="$BACKUP_DIR/$(echo "$file" | sed "s|^$PROJECT_ROOT/||")"

    # Create directory structure in backup
    mkdir -p "$(dirname "$backup_path")"

    # Copy file to backup
    cp "$file" "$backup_path"
    log_info "Backed up: $file"
}

# Safe removal function
safe_remove() {
    local file="$1"
    local reason="$2"

    if [[ ! -f "$file" ]]; then
        log_warning "File not found: $file"
        return 1
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would remove: $file ($reason)"
        return 0
    fi

    # Backup before removal
    backup_file "$file"

    # Remove file
    rm "$file"
    log "Removed: $file ($reason)"
}

# Safe directory removal
safe_remove_dir() {
    local dir="$1"
    local reason="$2"

    if [[ ! -d "$dir" ]]; then
        log_warning "Directory not found: $dir"
        return 1
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would remove directory: $dir ($reason)"
        return 0
    fi

    # Backup directory before removal
    local backup_path="$BACKUP_DIR/$(echo "$dir" | sed "s|^$PROJECT_ROOT/||")"
    mkdir -p "$(dirname "$backup_path")"
    cp -r "$dir" "$backup_path"
    log_info "Backed up directory: $dir"

    # Remove directory
    rm -rf "$dir"
    log "Removed directory: $dir ($reason)"
}

# Cleanup functions
cleanup_backup_files() {
    log_info "Cleaning up backup files..."

    local backup_files=(
        "/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src/tests/auth/services/mcp_token_service_test.py.bak"
        "/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src/tests/task_management/interface/controllers/git_branch_mcp_controller_test.py.backup"
        "/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src/mcp_http_server.py.backup"
        "/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/src/fastmcp/server/production_app.py.backup"
        "/home/daihungpham/__projects__/agentic-project/.test_cache/failed_tests.txt.backup"
        "/home/daihungpham/__projects__/agentic-project/CHANGELOG.md.backup"
    )

    for file in "${backup_files[@]}"; do
        if [[ -f "$file" ]]; then
            safe_remove "$file" "legacy backup file"
        fi
    done
}

cleanup_test_logs() {
    log_info "Cleaning up test logs outside logs directory..."

    local test_log_files=(
        "/home/daihungpham/__projects__/agentic-project/fix-1by1.log"
        "/home/daihungpham/__projects__/agentic-project/.test_cache/last_run.log"
        "/home/daihungpham/__projects__/agentic-project/.test_cache/test_run_iteration_44.log"
        "/home/daihungpham/__projects__/agentic-project/ai_docs/_workplace/workers/fix_tests_loop/fix-1by1.log"
    )

    for file in "${test_log_files[@]}"; do
        if [[ -f "$file" ]]; then
            safe_remove "$file" "legacy test log"
        fi
    done
}

cleanup_loop_workers() {
    log_info "Cleaning up legacy loop worker scripts..."

    local worker_files=(
        "/home/daihungpham/__projects__/agentic-project/loop-worker_testfix.sh"
        "/home/daihungpham/__projects__/agentic-project/scripts/workers/loop-worker_continue-unit-test-making.sh"
        "/home/daihungpham/__projects__/agentic-project/scripts/workers/loop-worker_continue-test-results copy.sh"
    )

    for file in "${worker_files[@]}"; do
        if [[ -f "$file" ]]; then
            safe_remove "$file" "legacy loop worker script"
        fi
    done

    # Check if workers directory is empty and remove if so
    local workers_dir="/home/daihungpham/__projects__/agentic-project/scripts/workers"
    if [[ -d "$workers_dir" ]] && [[ -z "$(ls -A "$workers_dir")" ]]; then
        safe_remove_dir "$workers_dir" "empty workers directory"
    fi
}

cleanup_old_cache_dirs() {
    log_info "Cleaning up old cache directories..."

    # Check .test_cache for old files
    local test_cache_dir="/home/daihungpham/__projects__/agentic-project/.test_cache"
    if [[ -d "$test_cache_dir" ]]; then
        # Remove old iteration logs
        find "$test_cache_dir" -name "test_run_iteration_*.log" -mtime +7 -type f | while read -r file; do
            safe_remove "$file" "old test iteration log (>7 days)"
        done
    fi

    # Clean up old pytest cache if it exists
    local pytest_cache="/home/daihungpham/__projects__/agentic-project/.pytest_cache"
    if [[ -d "$pytest_cache" ]]; then
        find "$pytest_cache" -name "*.pyc" -type f | while read -r file; do
            safe_remove "$file" "pytest cache file"
        done
    fi
}

cleanup_duplicate_docker_files() {
    log_info "Cleaning up duplicate Docker files..."

    # Look for potential duplicates (these would need manual review)
    local docker_dir="/home/daihungpham/__projects__/agentic-project/docker-system"

    # Check for old/duplicate docker menu files
    if [[ -f "$PROJECT_ROOT/docker-menu.sh" ]]; then
        # Check if it's a duplicate of the one in docker-system
        if [[ -f "$docker_dir/docker-menu.sh" ]]; then
            if cmp -s "$PROJECT_ROOT/docker-menu.sh" "$docker_dir/docker-menu.sh"; then
                safe_remove "$PROJECT_ROOT/docker-menu.sh" "duplicate of docker-system/docker-menu.sh"
            else
                log_warning "Root docker-menu.sh differs from docker-system version - manual review needed"
            fi
        fi
    fi
}

cleanup_node_modules_artifacts() {
    log_info "Cleaning up node_modules artifacts..."

    # Clean up frontend node_modules logs (these shouldn't be in git anyway)
    local frontend_dir="/home/daihungpham/__projects__/agentic-project/dhafnck-frontend"
    if [[ -f "$frontend_dir/node_modules/nwsapi/dist/lint.log" ]]; then
        safe_remove "$frontend_dir/node_modules/nwsapi/dist/lint.log" "node_modules artifact log"
    fi

    # Clean up any .DS_Store files (macOS artifacts)
    find "$PROJECT_ROOT" -name ".DS_Store" -type f | while read -r file; do
        safe_remove "$file" "macOS .DS_Store file"
    done
}

cleanup_htmlcov_artifacts() {
    log_info "Cleaning up HTML coverage artifacts..."

    # Remove specific test worker coverage files that are no longer relevant
    local htmlcov_dir="/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/htmlcov"
    if [[ -f "$htmlcov_dir/z_5757ee64987f52a2_test_workers_init_py.html" ]]; then
        safe_remove "$htmlcov_dir/z_5757ee64987f52a2_test_workers_init_py.html" "obsolete coverage artifact"
    fi
}

# Process ID cleanup
cleanup_stale_pid_files() {
    log_info "Cleaning up stale PID files..."

    local pid_files=(
        "/home/daihungpham/__projects__/agentic-project/dev-backend.pid"
        "/home/daihungpham/__projects__/agentic-project/dev-frontend.pid"
    )

    for pid_file in "${pid_files[@]}"; do
        if [[ -f "$pid_file" ]]; then
            local pid
            pid=$(cat "$pid_file")

            # Check if process is still running
            if ! ps -p "$pid" > /dev/null 2>&1; then
                safe_remove "$pid_file" "stale PID file (process $pid not running)"
            else
                log_info "PID file $pid_file is valid (process $pid running)"
            fi
        fi
    done
}

# Generate cleanup report
generate_report() {
    local report_file="${PROJECT_ROOT}/logs/cleanup-report-$(date +%Y%m%d-%H%M%S).md"

    cat > "$report_file" << EOF
# DhafnckMCP Cleanup Report
**Date**: $(date)
**Type**: ${DRY_RUN}

## Summary
$(if [[ "$DRY_RUN" == "true" ]]; then echo "**DRY RUN** - No files were actually removed"; else echo "Cleanup completed successfully"; fi)

## Backup Location
\`$BACKUP_DIR\`

## Cleanup Log
\`$CLEANUP_LOG\`

## Files Processed
See log file for detailed list of files processed.

## Recommendations
1. Keep backups for at least 30 days
2. Review backup directory before permanent deletion
3. Update .gitignore to prevent future accumulation of temporary files

## Next Steps
- [ ] Verify system functionality after cleanup
- [ ] Update documentation if any critical files were moved
- [ ] Schedule regular cleanup maintenance
EOF

    log "Generated cleanup report: $report_file"
}

# Main cleanup execution
main() {
    local mode="${1:-interactive}"

    log "🧹 Starting DhafnckMCP cleanup process..."
    log "Backup directory: $BACKUP_DIR"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_warning "DRY RUN MODE - No files will be actually removed"
    fi

    case "$mode" in
        "all"|"full")
            cleanup_backup_files
            cleanup_test_logs
            cleanup_loop_workers
            cleanup_old_cache_dirs
            cleanup_duplicate_docker_files
            cleanup_node_modules_artifacts
            cleanup_htmlcov_artifacts
            cleanup_stale_pid_files
            ;;
        "backup-only")
            cleanup_backup_files
            ;;
        "logs-only")
            cleanup_test_logs
            cleanup_old_cache_dirs
            ;;
        "workers-only")
            cleanup_loop_workers
            ;;
        "interactive"|*)
            echo -e "\n${BOLD}${BLUE}DhafnckMCP Cleanup Tool${RESET}"
            echo -e "${BLUE}========================${RESET}"
            echo -e "${BOLD}1.${RESET} Full cleanup (recommended)"
            echo -e "${BOLD}2.${RESET} Backup files only"
            echo -e "${BOLD}3.${RESET} Log files only"
            echo -e "${BOLD}4.${RESET} Worker scripts only"
            echo -e "${BOLD}5.${RESET} Custom selection"
            echo -e "${BOLD}0.${RESET} Exit"
            echo ""
            read -p "Select cleanup option [1-5]: " choice

            case $choice in
                1) cleanup_backup_files; cleanup_test_logs; cleanup_loop_workers; cleanup_old_cache_dirs; cleanup_duplicate_docker_files; cleanup_node_modules_artifacts; cleanup_htmlcov_artifacts; cleanup_stale_pid_files ;;
                2) cleanup_backup_files ;;
                3) cleanup_test_logs; cleanup_old_cache_dirs ;;
                4) cleanup_loop_workers ;;
                5)
                    echo "Custom cleanup not implemented yet. Use specific mode arguments."
                    exit 1
                    ;;
                0) log "Cleanup cancelled by user"; exit 0 ;;
                *) log_error "Invalid option: $choice"; exit 1 ;;
            esac
            ;;
    esac

    generate_report

    if [[ "$DRY_RUN" != "true" ]]; then
        log "✅ Cleanup completed successfully!"
        log "📁 Backups stored in: $BACKUP_DIR"
        log "📋 Cleanup log: $CLEANUP_LOG"
    else
        log "✅ Dry run completed - review above for changes that would be made"
    fi
}

# Handle command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS] [MODE]"
            echo ""
            echo "Options:"
            echo "  --dry-run        Show what would be removed without actually removing"
            echo "  --help, -h       Show this help"
            echo ""
            echo "Modes:"
            echo "  all, full        Complete cleanup (default for non-interactive)"
            echo "  backup-only      Clean up .bak/.backup files only"
            echo "  logs-only        Clean up log files only"
            echo "  workers-only     Clean up worker scripts only"
            echo "  interactive      Interactive mode (default)"
            echo ""
            exit 0
            ;;
        *)
            MODE="$1"
            shift
            ;;
    esac
done

# Execute main function
main "${MODE:-interactive}"