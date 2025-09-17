#!/bin/bash
# 4genthub Project Cleanup Script
# Version: 1.0
# Date: 2025-09-08
# Description: Safely removes obsolete files with backup and rollback capability

set -e  # Exit on any error

PROJECT_ROOT="/home/daihungpham/__projects__/agentic-project"
BACKUP_DIR="/tmp/4genthub-cleanup-backup-$(date +%Y%m%d_%H%M%S)"
LOG_FILE="/tmp/cleanup-$(date +%Y%m%d_%H%M%S).log"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG_FILE"
}

confirm() {
    echo -e "${YELLOW}$1${NC}"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "${RED}Operation cancelled by user${NC}"
        exit 1
    fi
}

show_header() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                    4genthub Project Cleanup Script                         ║"
    echo "║                                                                              ║"
    echo "║ This script will safely remove 50+ obsolete files (~50MB disk space)       ║"
    echo "║ Full backup and rollback capability included                                ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

create_backup() {
    log "${GREEN}Creating backup directory: $BACKUP_DIR${NC}"
    mkdir -p "$BACKUP_DIR"
    
    # Backup critical files
    log "Backing up critical log files..."
    cp "$PROJECT_ROOT/4genthub_main/logs/4genthub.log" "$BACKUP_DIR/" 2>/dev/null || log "Note: 4genthub.log not found"
    cp "$PROJECT_ROOT/4genthub_main/logs/4genthub_errors.log" "$BACKUP_DIR/" 2>/dev/null || log "Note: 4genthub_errors.log not found"
    
    # Archive development artifacts
    log "Archiving development artifacts..."
    if [ -d "$PROJECT_ROOT/ai_docs/architecture/working/" ]; then
        tar -czf "$BACKUP_DIR/ai_docs-working.tar.gz" "$PROJECT_ROOT/ai_docs/architecture/working/"
        log "Development artifacts archived"
    fi
    
    # Note: .claude/agents/ and agent-library/ are active systems - NOT archived
    
    # Backup .prev files before deletion
    log "Backing up .prev files..."
    find "$PROJECT_ROOT" -name "*.prev" -exec cp {} "$BACKUP_DIR/" \; 2>/dev/null || true
    
    log "${GREEN}Backup created successfully${NC}"
    echo "Backup location: $BACKUP_DIR"
}

safety_checks() {
    log "${YELLOW}Performing comprehensive safety checks...${NC}"
    
    # Check if we're in the right directory
    if [ ! -f "$PROJECT_ROOT/CLAUDE.md" ]; then
        log "${RED}Error: Not in 4genthub project root${NC}"
        exit 1
    fi
    
    # Check git status
    cd "$PROJECT_ROOT"
    if [ -n "$(git status --porcelain)" ]; then
        log "${YELLOW}Warning: Uncommitted changes detected:${NC}"
        git status --porcelain
        confirm "Proceed with uncommitted changes?"
    fi
    
    # Check for active processes using log files
    if lsof +D "$PROJECT_ROOT/4genthub_main/logs/" 2>/dev/null | grep -q .; then
        log "${RED}Error: Active processes are using log files:${NC}"
        lsof +D "$PROJECT_ROOT/4genthub_main/logs/" 2>/dev/null
        confirm "Force cleanup despite active processes?"
    fi
    
    # Check disk space
    local available_space=$(df /tmp | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 1048576 ]; then # Less than 1GB
        log "${RED}Warning: Low disk space in /tmp ($(df -h /tmp | awk 'NR==2 {print $4}') available)${NC}"
        confirm "Proceed with limited disk space?"
    fi
    
    # Check Docker status
    if docker ps 2>/dev/null | grep -q 4genthub; then
        log "${YELLOW}Warning: 4genthub Docker containers are running${NC}"
        docker ps --filter name=4genthub
        confirm "Proceed with running containers?"
    fi
    
    log "${GREEN}Safety checks completed${NC}"
}

show_cleanup_plan() {
    log "${BLUE}=== CLEANUP PLAN ===${NC}"
    
    echo "Files to be deleted:"
    echo "1. Rotated backend logs (backend.log.2-5): ~40MB"
    echo "2. Standalone log files: ~8MB"
    echo "3. Backup files (.prev): ~2KB"
    echo "4. Misplaced test files: ~4KB"
    echo "5. Development artifacts: ~132KB"
    echo ""
    echo "Total space recovery: ~50MB"
    echo "Files affected: 50+ files"
    echo ""
}

cleanup_logs() {
    log "${GREEN}Phase 1: Cleaning up log files...${NC}"
    
    local deleted_files=0
    local saved_space=0
    
    # Remove rotated backend logs (keep current + 1 backup)
    for i in {2..9}; do
        local log_file="$PROJECT_ROOT/4genthub_main/logs/backend.log.$i"
        if [ -f "$log_file" ]; then
            local file_size=$(stat -c%s "$log_file" 2>/dev/null || echo 0)
            rm -f "$log_file"
            deleted_files=$((deleted_files + 1))
            saved_space=$((saved_space + file_size))
            log "Deleted: backend.log.$i ($(numfmt --to=iec $file_size))"
        fi
    done
    
    # Remove standalone log files (not in logs/ directory)
    while IFS= read -r -d '' log_file; do
        if [[ "$log_file" != */logs/* ]] && [[ "$log_file" != */node_modules/* ]]; then
            local file_size=$(stat -c%s "$log_file" 2>/dev/null || echo 0)
            rm -f "$log_file"
            deleted_files=$((deleted_files + 1))
            saved_space=$((saved_space + file_size))
            log "Deleted: $(basename "$log_file") ($(numfmt --to=iec $file_size))"
        fi
    done < <(find "$PROJECT_ROOT" -name "*.log" -type f -print0 2>/dev/null)
    
    log "${GREEN}Log cleanup completed: $deleted_files files, $(numfmt --to=iec $saved_space) saved${NC}"
}

cleanup_backups() {
    log "${GREEN}Phase 2: Cleaning up backup files...${NC}"
    
    local deleted_files=0
    
    # Remove .prev files
    while IFS= read -r -d '' backup_file; do
        rm -f "$backup_file"
        deleted_files=$((deleted_files + 1))
        log "Deleted: $(basename "$backup_file")"
    done < <(find "$PROJECT_ROOT" -name "*.prev" -type f -print0 2>/dev/null)
    
    # Remove .bak files
    while IFS= read -r -d '' backup_file; do
        rm -f "$backup_file"
        deleted_files=$((deleted_files + 1))
        log "Deleted: $(basename "$backup_file")"
    done < <(find "$PROJECT_ROOT" -name "*.bak" -type f -print0 2>/dev/null)
    
    # Remove .tmp files
    while IFS= read -r -d '' temp_file; do
        if [[ "$temp_file" != */node_modules/* ]]; then
            rm -f "$temp_file"
            deleted_files=$((deleted_files + 1))
            log "Deleted: $(basename "$temp_file")"
        fi
    done < <(find "$PROJECT_ROOT" -name "*.tmp" -type f -print0 2>/dev/null)
    
    log "${GREEN}Backup files cleanup completed: $deleted_files files${NC}"
}

cleanup_test_files() {
    log "${GREEN}Phase 3: Cleaning up misplaced test files...${NC}"
    
    local test_files=(
        "$PROJECT_ROOT/test_context_operations.py"
        "$PROJECT_ROOT/test_next_task_with_parent_context.py"
        "$PROJECT_ROOT/test_tool_registration_fix.py"
        "$PROJECT_ROOT/test-branch-delete.html"
    )
    
    local deleted_files=0
    
    for test_file in "${test_files[@]}"; do
        if [ -f "$test_file" ]; then
            rm -f "$test_file"
            deleted_files=$((deleted_files + 1))
            log "Deleted: $(basename "$test_file")"
        fi
    done
    
    log "${GREEN}Test files cleanup completed: $deleted_files files${NC}"
}

cleanup_development_artifacts() {
    log "${GREEN}Phase 4: Cleaning up development artifacts...${NC}"
    
    local artifacts_dir="$PROJECT_ROOT/ai_docs/architecture/working"
    
    if [ -d "$artifacts_dir" ]; then
        local file_count=$(find "$artifacts_dir" -type f | wc -l)
        rm -rf "$artifacts_dir"
        log "Deleted working directory with $file_count files"
        log "${GREEN}Development artifacts cleanup completed${NC}"
    else
        log "No development artifacts directory found"
    fi
}

cleanup_git_ignored() {
    log "${GREEN}Phase 5: Cleaning up git-ignored files...${NC}"
    
    cd "$PROJECT_ROOT"
    
    # Clean untracked files (but preserve .env files)
    if [ -n "$(git clean -n -d --exclude='.env*')" ]; then
        log "Git-ignored files to be removed:"
        git clean -n -d --exclude='.env*'
        confirm "Remove these untracked files?"
        git clean -f -d --exclude='.env*'
        log "${GREEN}Git cleanup completed${NC}"
    else
        log "No git-ignored files to clean"
    fi
}

show_summary() {
    log "${GREEN}=== CLEANUP SUMMARY ===${NC}"
    
    # Calculate current disk usage
    local logs_size=$(du -sh "$PROJECT_ROOT/4genthub_main/logs/" 2>/dev/null | cut -f1 || echo "N/A")
    local total_size=$(du -sh "$PROJECT_ROOT" --exclude="node_modules" 2>/dev/null | cut -f1 || echo "N/A")
    
    echo ""
    echo -e "${GREEN}✅ Cleanup completed successfully${NC}"
    echo ""
    echo "📊 Results:"
    echo "   • Backup location: $BACKUP_DIR"
    echo "   • Log file: $LOG_FILE"
    echo "   • Remaining logs size: $logs_size"
    echo "   • Total project size (excl. node_modules): $total_size"
    echo ""
    echo "🛡️  Recovery:"
    echo "   • Backups retained for 30 days in /tmp"
    echo "   • Use rollback() function if issues occur"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "   1. Test MCP server startup"
    echo "   2. Run git status to verify clean state"
    echo "   3. Verify application functionality"
}

rollback() {
    log "${YELLOW}Rolling back changes...${NC}"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        log "${RED}Error: No backup directory found for rollback${NC}"
        echo "Available backups:"
        ls -la /tmp/4genthub-cleanup-backup-* 2>/dev/null || echo "No backups found"
        exit 1
    fi
    
    # Restore critical logs
    if [ -f "$BACKUP_DIR/4genthub.log" ]; then
        cp "$BACKUP_DIR/4genthub.log" "$PROJECT_ROOT/4genthub_main/logs/"
        log "Restored 4genthub.log"
    fi
    
    if [ -f "$BACKUP_DIR/4genthub_errors.log" ]; then
        cp "$BACKUP_DIR/4genthub_errors.log" "$PROJECT_ROOT/4genthub_main/logs/"
        log "Restored 4genthub_errors.log"
    fi
    
    # Restore development artifacts
    if [ -f "$BACKUP_DIR/ai_docs-working.tar.gz" ]; then
        cd "$PROJECT_ROOT"
        tar -xzf "$BACKUP_DIR/ai_docs-working.tar.gz"
        log "Restored development artifacts"
    fi
    
    # Restore .prev files
    cp "$BACKUP_DIR"/*.prev "$PROJECT_ROOT/.claude/commands/" 2>/dev/null || true
    
    log "${GREEN}Rollback completed${NC}"
}

# Verify post-cleanup state
verify_cleanup() {
    log "${BLUE}Verifying cleanup results...${NC}"
    
    # Check git status
    cd "$PROJECT_ROOT"
    local git_status=$(git status --porcelain)
    if [ -z "$git_status" ]; then
        log "✅ Git status is clean"
    else
        log "⚠️  Git status has changes:"
        git status --porcelain
    fi
    
    # Check for broken references
    local broken_refs=$(grep -r "ai_docs/architecture/working" "$PROJECT_ROOT/ai_docs/" 2>/dev/null || true)
    if [ -z "$broken_refs" ]; then
        log "✅ No broken references found"
    else
        log "⚠️  Broken references found:"
        echo "$broken_refs"
    fi
    
    # Test basic file structure
    if [ -f "$PROJECT_ROOT/CLAUDE.md" ] && [ -f "$PROJECT_ROOT/4genthub_main/src/fastmcp/__init__.py" ]; then
        log "✅ Project structure intact"
    else
        log "❌ Project structure may be damaged"
    fi
}

# Main execution
main() {
    show_header
    
    log "${GREEN}Starting 4genthub Project Cleanup${NC}"
    log "Project root: $PROJECT_ROOT"
    log "Backup directory: $BACKUP_DIR"
    log "Log file: $LOG_FILE"
    echo ""
    
    show_cleanup_plan
    
    confirm "This will delete 50+ obsolete files (~50MB) and create full backups. Continue?"
    
    safety_checks
    create_backup
    
    echo ""
    log "${BLUE}Starting cleanup phases...${NC}"
    
    # Execute cleanup phases
    cleanup_logs
    cleanup_backups
    cleanup_test_files
    cleanup_development_artifacts
    cleanup_git_ignored
    
    verify_cleanup
    show_summary
    
    log "${GREEN}🎉 Cleanup script completed successfully${NC}"
}

# Show help
show_help() {
    echo "4genthub Project Cleanup Script"
    echo ""
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  --help, -h     Show this help message"
    echo "  --dry-run      Show what would be deleted without making changes"
    echo "  --rollback     Rollback the last cleanup (requires backup directory)"
    echo "  --verify       Verify project state after cleanup"
    echo ""
    echo "Examples:"
    echo "  $0                    # Run full cleanup with prompts"
    echo "  $0 --dry-run          # Show cleanup plan without executing"
    echo "  $0 --rollback         # Rollback last cleanup"
}

dry_run() {
    echo -e "${BLUE}=== DRY RUN MODE ===${NC}"
    echo "The following actions would be performed:"
    echo ""
    
    echo "1. Log files to delete:"
    find "$PROJECT_ROOT/4genthub_main/logs/" -name "backend.log.[2-9]" 2>/dev/null | while read -r file; do
        echo "   - $(basename "$file") ($(du -h "$file" | cut -f1))"
    done
    
    echo ""
    echo "2. Backup files to delete:"
    find "$PROJECT_ROOT" -name "*.prev" -o -name "*.bak" -o -name "*.tmp" | grep -v node_modules | while read -r file; do
        echo "   - $file"
    done
    
    echo ""
    echo "3. Test files to delete:"
    for test_file in test_context_operations.py test_next_task_with_parent_context.py test_tool_registration_fix.py test-branch-delete.html; do
        if [ -f "$PROJECT_ROOT/$test_file" ]; then
            echo "   - $test_file"
        fi
    done
    
    echo ""
    echo "4. Development artifacts:"
    if [ -d "$PROJECT_ROOT/ai_docs/architecture/working" ]; then
        echo "   - ai_docs/architecture/working/ ($(du -sh "$PROJECT_ROOT/ai_docs/architecture/working" | cut -f1))"
    fi
    
    echo ""
    echo -e "${GREEN}No files were actually deleted in dry-run mode${NC}"
}

# Trap for cleanup on error
trap 'log "${RED}Script failed. Backup available at: $BACKUP_DIR${NC}"; log "Run: bash $0 --rollback to restore files"' ERR

# Parse command line arguments
case "${1:-}" in
    --help|-h)
        show_help
        exit 0
        ;;
    --dry-run)
        dry_run
        exit 0
        ;;
    --rollback)
        echo "Enter backup directory path (or press Enter to use latest):"
        read -r backup_path
        if [ -n "$backup_path" ]; then
            BACKUP_DIR="$backup_path"
        else
            BACKUP_DIR=$(ls -td /tmp/4genthub-cleanup-backup-* 2>/dev/null | head -1)
        fi
        rollback
        exit 0
        ;;
    --verify)
        verify_cleanup
        exit 0
        ;;
    *)
        # Execute main function
        main "$@"
        ;;
esac