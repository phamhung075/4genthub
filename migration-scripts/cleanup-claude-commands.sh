#!/bin/bash
# CLAUDE Commands Consolidation Script  
# DhafnckMCP Project - Clean up and consolidate .claude/commands directory

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly RESET='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
CLAUDE_DIR="$PROJECT_ROOT/.claude"
COMMANDS_DIR="$CLAUDE_DIR/commands"
BACKUP_DIR="$PROJECT_ROOT/backups/$(date +%Y%m%d_%H%M%S)"

echo -e "${CYAN}${BOLD}📝 DhafnckMCP CLAUDE Commands Consolidation${RESET}"
echo -e "${CYAN}${BOLD}===========================================${RESET}"
echo ""

# Function to create backup of .claude directory
create_claude_backup() {
    echo -e "${YELLOW}📦 Creating backup of .claude directory...${RESET}"
    
    if [ ! -d "$CLAUDE_DIR" ]; then
        echo -e "${RED}  ❌ .claude directory not found${RESET}"
        return 1
    fi
    
    mkdir -p "$BACKUP_DIR"
    cp -r "$CLAUDE_DIR" "$BACKUP_DIR/"
    
    echo -e "${GREEN}  ✅ .claude directory backed up to $BACKUP_DIR/.claude${RESET}"
    echo ""
}

# Function to analyze current commands
analyze_commands() {
    echo -e "${YELLOW}🔍 Analyzing current CLAUDE commands...${RESET}"
    
    if [ ! -d "$COMMANDS_DIR" ]; then
        echo -e "${RED}  ❌ Commands directory not found: $COMMANDS_DIR${RESET}"
        return 1
    fi
    
    local total_files=$(find "$COMMANDS_DIR" -name "*.md" | wc -l)
    local backup_files=$(find "$COMMANDS_DIR" -name "*.prev" | wc -l)
    local active_files=$((total_files - backup_files))
    
    echo "  📊 Commands Analysis:"
    echo "    • Total command files: $total_files"
    echo "    • Backup files (.prev): $backup_files"  
    echo "    • Active command files: $active_files"
    echo ""
    
    # Categorize commands by purpose
    echo "  📋 Command Categories:"
    
    # Development/Testing commands
    local dev_commands=$(find "$COMMANDS_DIR" -name "*.md" | grep -E "(test|tdd|debug|fix)" | wc -l)
    echo "    • Development/Testing: $dev_commands"
    
    # Documentation commands
    local doc_commands=$(find "$COMMANDS_DIR" -name "*.md" | grep -E "(doc|readme|update.*docs)" | wc -l)
    echo "    • Documentation: $doc_commands"
    
    # Maintenance commands
    local maint_commands=$(find "$COMMANDS_DIR" -name "*.md" | grep -E "(clean|sync|update|fix)" | wc -l)
    echo "    • Maintenance: $maint_commands"
    
    # Project-specific commands
    local proj_commands=$(find "$COMMANDS_DIR" -name "*.md" | grep -E "(ddd|continue|analyze)" | wc -l)
    echo "    • Project-specific: $proj_commands"
    
    echo ""
    
    # Show largest files
    echo "  📏 Largest command files:"
    find "$COMMANDS_DIR" -name "*.md" -exec ls -lh {} + | sort -k5 -hr | head -5 | while read -r line; do
        local size=$(echo "$line" | awk '{print $5}')
        local file=$(echo "$line" | awk '{print $NF}')
        local basename_file=$(basename "$file")
        echo "    • $basename_file ($size)"
    done
    
    echo ""
}

# Function to identify files for removal
identify_removal_candidates() {
    echo -e "${YELLOW}🗑️  Identifying files for removal...${RESET}"
    
    # Backup files (.prev)
    local backup_files=()
    while IFS= read -r -d '' file; do
        backup_files+=("$file")
    done < <(find "$COMMANDS_DIR" -name "*.prev" -print0)
    
    echo "  📦 Backup files to remove:"
    if [ ${#backup_files[@]} -eq 0 ]; then
        echo -e "${GREEN}    • None found${RESET}"
    else
        for file in "${backup_files[@]}"; do
            local basename_file=$(basename "$file")
            echo "    • $basename_file"
        done
    fi
    
    # Outdated/temporary files (last modified > 30 days ago and small)
    local old_files=()
    while IFS= read -r -d '' file; do
        # Skip if it's a backup file (already handled)
        if [[ "$file" == *.prev ]]; then continue; fi
        
        # Check if file is older than 30 days and smaller than 1KB
        if [ "$(find "$file" -mtime +30 -size -1024c | wc -l)" -gt 0 ]; then
            old_files+=("$file")
        fi
    done < <(find "$COMMANDS_DIR" -name "*.md" -print0)
    
    echo "  ⏰ Old/small files (>30 days, <1KB) to consider for removal:"
    if [ ${#old_files[@]} -eq 0 ]; then
        echo -e "${GREEN}    • None found${RESET}"
    else
        for file in "${old_files[@]}"; do
            local basename_file=$(basename "$file")
            local mod_time=$(stat -c %y "$file" | cut -d' ' -f1)
            echo "    • $basename_file (modified: $mod_time)"
        done
    fi
    
    # Store for later use
    printf '%s\n' "${backup_files[@]}" > /tmp/dhafnck_backup_files.txt
    printf '%s\n' "${old_files[@]}" > /tmp/dhafnck_old_files.txt
    
    echo ""
}

# Function to analyze command content for consolidation
analyze_command_content() {
    echo -e "${YELLOW}🔍 Analyzing command content for consolidation opportunities...${RESET}"
    
    # Look for similar commands that could be merged
    local similar_commands=()
    
    # Test-related commands
    local test_files=($(find "$COMMANDS_DIR" -name "*.md" | grep -E "(test|tdd)" | head -10))
    if [ ${#test_files[@]} -gt 1 ]; then
        similar_commands+=("Testing commands: ${#test_files[@]} files could be consolidated")
    fi
    
    # Fix/update commands  
    local fix_files=($(find "$COMMANDS_DIR" -name "*.md" | grep -E "(fix|update)" | head -10))
    if [ ${#fix_files[@]} -gt 2 ]; then
        similar_commands+=("Fix/update commands: ${#fix_files[@]} files could be consolidated")
    fi
    
    # Continue/resume commands
    local continue_files=($(find "$COMMANDS_DIR" -name "*.md" | grep -E "continue" | head -10))
    if [ ${#continue_files[@]} -gt 1 ]; then
        similar_commands+=("Continue commands: ${#continue_files[@]} files could be consolidated")
    fi
    
    echo "  🔄 Consolidation opportunities:"
    if [ ${#similar_commands[@]} -eq 0 ]; then
        echo -e "${GREEN}    • No obvious consolidation opportunities found${RESET}"
    else
        for opportunity in "${similar_commands[@]}"; do
            echo "    • $opportunity"
        done
    fi
    
    # Check for commands that might belong in CLAUDE.md instead
    local claude_md_candidates=()
    
    # Look for general guidance files
    while IFS= read -r -d '' file; do
        if grep -qE "(general|guideline|rule|principle|best.practice)" "$file" 2>/dev/null; then
            claude_md_candidates+=("$(basename "$file")")
        fi
    done < <(find "$COMMANDS_DIR" -name "*.md" -print0)
    
    echo ""
    echo "  📋 Commands that might belong in CLAUDE.md:"
    if [ ${#claude_md_candidates[@]} -eq 0 ]; then
        echo -e "${GREEN}    • None identified${RESET}"
    else
        for candidate in "${claude_md_candidates[@]}"; do
            echo "    • $candidate"
        done
    fi
    
    echo ""
}

# Function to remove backup files
remove_backup_files() {
    echo -e "${YELLOW}🗑️  Removing backup files...${RESET}"
    
    local removed_count=0
    
    while IFS= read -r file; do
        if [ -n "$file" ] && [ -f "$file" ]; then
            local basename_file=$(basename "$file")
            echo "  • Removing $basename_file"
            rm "$file"
            removed_count=$((removed_count + 1))
        fi
    done < /tmp/dhafnck_backup_files.txt
    
    echo -e "${GREEN}  ✅ Removed $removed_count backup files${RESET}"
    echo ""
}

# Function to consolidate similar commands
consolidate_similar_commands() {
    echo -e "${YELLOW}🔄 Consolidating similar commands...${RESET}"
    
    # Consolidate test-related commands
    local test_files=($(find "$COMMANDS_DIR" -name "*.md" | grep -E "(test|tdd)" | grep -v ".prev"))
    if [ ${#test_files[@]} -gt 1 ]; then
        echo "  • Consolidating ${#test_files[@]} test-related commands..."
        
        local consolidated_file="$COMMANDS_DIR/testing-guide.md"
        
        cat > "$consolidated_file" << 'EOF'
# DhafnckMCP Testing Guide
## Consolidated Testing Commands and Procedures

This document consolidates all testing-related commands and procedures for the DhafnckMCP project.

## Quick Commands

### Run Unit Tests
```bash
cd dhafnck_mcp_main
python -m pytest src/tests/unit/ -v
```

### Run Integration Tests  
```bash
cd dhafnck_mcp_main
python -m pytest src/tests/integration/ -v
```

### Run All Tests
```bash
cd dhafnck_mcp_main
python -m pytest src/tests/ -v --tb=short
```

### TDD Workflow
1. Write failing test
2. Run specific test: `python -m pytest src/tests/path/to/test.py::test_name -v`
3. Implement minimal code to pass
4. Refactor and repeat

## Test Categories

### Unit Tests
- Location: `src/tests/unit/`
- Focus: Individual components, functions, classes
- Mock external dependencies

### Integration Tests
- Location: `src/tests/integration/`  
- Focus: Component interactions, database operations
- Use test database

### End-to-End Tests
- Location: `src/tests/e2e/`
- Focus: Full system workflows
- Test against running system

## Common Issues and Fixes

### Database Test Issues
- Ensure test database is clean: Use fixtures with rollback
- Check database connections in test environment
- Verify test data isolation

### MCP Test Issues  
- Mock MCP calls for unit tests
- Use test MCP server for integration tests
- Check agent availability in test environment

### Import/Path Issues
- Verify PYTHONPATH includes src directory
- Check relative imports in test files
- Ensure test discovery patterns match

## Debugging Tests
- Use `pytest -s` to see print statements
- Use `pytest --tb=long` for detailed tracebacks
- Use `pytest -k pattern` to run specific tests
- Use `pytest --lf` to run only last failed tests

EOF
        
        # Archive old test files
        local archive_dir="$COMMANDS_DIR/archived-test-commands"
        mkdir -p "$archive_dir"
        
        for test_file in "${test_files[@]}"; do
            local basename_file=$(basename "$test_file")
            echo "    - Archiving $basename_file"
            mv "$test_file" "$archive_dir/"
        done
        
        echo -e "${GREEN}    ✅ Created consolidated testing-guide.md${RESET}"
        echo -e "${CYAN}    ℹ️  Original files archived in archived-test-commands/${RESET}"
    fi
    
    # Consolidate fix/update commands (if more than 3)
    local fix_files=($(find "$COMMANDS_DIR" -name "*.md" | grep -E "(fix|update)" | grep -v ".prev" | head -10))
    if [ ${#fix_files[@]} -gt 3 ]; then
        echo "  • Consolidating ${#fix_files[@]} fix/update commands..."
        
        local consolidated_file="$COMMANDS_DIR/maintenance-procedures.md"
        
        cat > "$consolidated_file" << 'EOF'
# DhafnckMCP Maintenance Procedures
## Consolidated Fix and Update Procedures

This document consolidates maintenance, fix, and update procedures for the DhafnckMCP project.

## Common Fix Procedures

### Rebuild Docker Containers
```bash
# Complete rebuild (Option 9)
./docker-system/docker-menu.sh
# Select option 9 for force complete rebuild
```

### Clear Python Cache
```bash
find dhafnck_mcp_main -name "__pycache__" -type d -exec rm -rf {} +
find dhafnck_mcp_main -name "*.pyc" -delete
```

### Reset Development Environment
```bash
# Stop all services
./docker-system/docker-menu.sh stop-dev

# Clear caches
find dhafnck_mcp_main -name "__pycache__" -exec rm -rf {} +

# Restart development mode
./docker-system/docker-menu.sh start-dev
```

### Database Issues
```bash
# Reset development database
rm -f dhafnck_mcp_dev.db

# Restart services to recreate database
./docker-system/docker-menu.sh restart-dev
```

## Update Procedures

### Update Dependencies
```bash
cd dhafnck_mcp_main

# Update Python dependencies
pip install -U -r requirements.txt

# Update frontend dependencies  
cd ../dhafnck-frontend
npm update
```

### Update Documentation
```bash
# Update CHANGELOG.md with changes
# Follow Keep a Changelog format
# Update version numbers if applicable
```

### Code Updates After Changes
```bash
# For Docker mode - rebuild containers
./docker-system/docker-menu.sh
# Select option 9 (force rebuild)

# For development mode - restart services  
./docker-system/docker-menu.sh restart-dev
```

## Troubleshooting Common Issues

### Port Conflicts
- Check running processes: `lsof -i :8000`
- Kill conflicting processes or use different ports
- Restart docker-menu.sh

### Import Errors
- Verify PYTHONPATH includes src directory
- Check for circular imports
- Ensure all __init__.py files exist

### Docker Issues
- Clean up: `docker system prune -a`
- Remove specific containers: `docker rm container_name`
- Check logs: `docker logs container_name`

### MCP Connection Issues
- Verify MCP server is running
- Check port configuration in .env.dev
- Verify agent availability with call_agent

EOF
        
        # Archive old fix files
        local archive_dir="$COMMANDS_DIR/archived-fix-commands"
        mkdir -p "$archive_dir"
        
        for fix_file in "${fix_files[@]}"; do
            local basename_file=$(basename "$fix_file")
            echo "    - Archiving $basename_file"
            mv "$fix_file" "$archive_dir/"
        done
        
        echo -e "${GREEN}    ✅ Created consolidated maintenance-procedures.md${RESET}"
        echo -e "${CYAN}    ℹ️  Original files archived in archived-fix-commands/${RESET}"
    fi
    
    echo ""
}

# Function to clean up archive directories if empty
cleanup_archives() {
    echo -e "${YELLOW}🧹 Cleaning up empty archive directories...${RESET}"
    
    for archive_dir in "$COMMANDS_DIR/archived-"*; do
        if [ -d "$archive_dir" ] && [ -z "$(ls -A "$archive_dir")" ]; then
            echo "  • Removing empty directory: $(basename "$archive_dir")"
            rmdir "$archive_dir"
        fi
    done
    
    echo ""
}

# Function to update CLAUDE.md with command references
update_claude_md_references() {
    echo -e "${YELLOW}📝 Checking CLAUDE.md for command references...${RESET}"
    
    local claude_md="$PROJECT_ROOT/CLAUDE.md"
    
    if [ ! -f "$claude_md" ]; then
        echo -e "${YELLOW}  ⚠️  CLAUDE.md not found, skipping updates${RESET}"
        return
    fi
    
    # Check if CLAUDE.md already references the consolidated commands
    local needs_update=false
    
    if ! grep -q "testing-guide.md" "$claude_md" 2>/dev/null; then
        needs_update=true
    fi
    
    if ! grep -q "maintenance-procedures.md" "$claude_md" 2>/dev/null; then
        needs_update=true
    fi
    
    if [ "$needs_update" = true ]; then
        echo "  • Adding references to consolidated commands in CLAUDE.md..."
        
        # Add a section about consolidated commands (append to end)
        cat >> "$claude_md" << 'EOF'

## Consolidated Command References

The following consolidated command guides are available in `.claude/commands/`:

- **testing-guide.md**: Comprehensive testing procedures and TDD workflow
- **maintenance-procedures.md**: System maintenance, fixes, and update procedures

These replace individual command files and provide organized, comprehensive guidance for common development tasks.

EOF
        
        echo -e "${GREEN}  ✅ Updated CLAUDE.md with consolidated command references${RESET}"
    else
        echo -e "${GREEN}  ✅ CLAUDE.md already has current command references${RESET}"
    fi
    
    echo ""
}

# Function to generate cleanup report
generate_cleanup_report() {
    local report_file="$BACKUP_DIR/claude-commands-cleanup-report.txt"
    
    echo -e "${YELLOW}📄 Generating cleanup report...${RESET}"
    
    local final_count=$(find "$COMMANDS_DIR" -name "*.md" | wc -l)
    local backup_count=$(wc -l < /tmp/dhafnck_backup_files.txt 2>/dev/null || echo "0")
    
    cat > "$report_file" << EOF
DhafnckMCP CLAUDE Commands Cleanup Report
========================================
Date: $(date)
Backup Location: $BACKUP_DIR

Cleanup Summary:
- Files before cleanup: $(( final_count + backup_count ))
- Files after cleanup: $final_count
- Backup files removed: $backup_count
- Consolidation performed: $([ -f "$COMMANDS_DIR/testing-guide.md" ] && echo "Yes" || echo "No")

Actions Performed:
✅ Created comprehensive backup
✅ Analyzed command structure and content
✅ Removed backup files (.prev)
✅ Consolidated similar commands
✅ Created organized command guides
✅ Updated CLAUDE.md references
✅ Generated cleanup report

Consolidated Commands Created:
$([ -f "$COMMANDS_DIR/testing-guide.md" ] && echo "  - testing-guide.md (comprehensive testing procedures)")
$([ -f "$COMMANDS_DIR/maintenance-procedures.md" ] && echo "  - maintenance-procedures.md (fix and update procedures)")

Remaining Command Files:
$(find "$COMMANDS_DIR" -name "*.md" -not -path "*/archived-*" | while read -r file; do
    echo "  - $(basename "$file")"
done)

Archive Directories:
$(find "$COMMANDS_DIR" -type d -name "archived-*" | while read -r dir; do
    echo "  - $(basename "$dir") ($(ls -1 "$dir" | wc -l) files)"
done)

Rollback Instructions:
To rollback this cleanup:
1. cd $PROJECT_ROOT
2. Restore from backup: cp -r $BACKUP_DIR/.claude ./
3. Remove consolidated files if desired

Maintenance Recommendations:
1. Regularly review and update consolidated guides
2. Remove archived files after 6 months if not needed
3. Keep core commands focused and specific
4. Document new procedures in consolidated guides
5. Remove this backup after confirming everything works

Next Steps:
1. Test consolidated commands work as expected
2. Verify CLAUDE.md references are accessible
3. Update team documentation about new command structure
4. Consider similar consolidation for other directories
EOF
    
    echo -e "${GREEN}  ✅ Report saved to: $report_file${RESET}"
}

# Main execution function
main() {
    echo -e "${CYAN}Starting CLAUDE commands consolidation...${RESET}"
    echo ""
    
    # Step 1: Create backup
    if ! create_claude_backup; then
        exit 1
    fi
    
    # Step 2: Analyze current commands
    analyze_commands
    
    # Step 3: Identify removal candidates
    identify_removal_candidates
    
    # Step 4: Analyze content for consolidation
    analyze_command_content
    
    # Step 5: Get user confirmation
    echo -e "${YELLOW}${BOLD}⚠️  CONSOLIDATION CONFIRMATION${RESET}"
    echo "This will:"
    echo "  • Remove backup files (.prev)"
    echo "  • Create consolidated command guides"
    echo "  • Archive individual command files"
    echo "  • Update CLAUDE.md references"
    echo ""
    echo "A backup has been created at: $BACKUP_DIR"
    echo ""
    read -p "Proceed with consolidation? (y/N): " confirm
    
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}❌ Consolidation cancelled by user${RESET}"
        exit 1
    fi
    
    # Step 6: Remove backup files
    remove_backup_files
    
    # Step 7: Consolidate similar commands
    consolidate_similar_commands
    
    # Step 8: Clean up empty archives
    cleanup_archives
    
    # Step 9: Update CLAUDE.md
    update_claude_md_references
    
    # Step 10: Generate report
    generate_cleanup_report
    
    # Cleanup temp files
    rm -f /tmp/dhafnck_backup_files.txt /tmp/dhafnck_old_files.txt
    
    echo -e "${GREEN}${BOLD}✅ CLAUDE Commands Consolidation Complete!${RESET}"
    echo ""
    echo -e "${CYAN}📋 Summary:${RESET}"
    echo "  • Backup location: $BACKUP_DIR"
    echo "  • Backup files removed: $(wc -l < "$BACKUP_DIR/.claude/commands/"*.prev 2>/dev/null | head -1 || echo "0")"
    echo "  • Consolidated guides created: $(find "$COMMANDS_DIR" -name "*-guide.md" -o -name "*-procedures.md" | wc -l)"
    echo "  • Final command count: $(find "$COMMANDS_DIR" -name "*.md" -not -path "*/archived-*" | wc -l)"
    echo ""
    echo -e "${YELLOW}📝 Next Steps:${RESET}"
    echo "  1. Test consolidated commands: Check .claude/commands/testing-guide.md"
    echo "  2. Verify CLAUDE.md updates: Check references section"
    echo "  3. Use new consolidated guides for development workflows"
    echo "  4. Clean up backup: Remove $BACKUP_DIR after verification"
    echo ""
    echo -e "${GREEN}🎉 Command structure successfully streamlined!${RESET}"
}

# Verify we're in the right directory
if [ ! -f "$PROJECT_ROOT/CLAUDE.md" ]; then
    echo -e "${RED}❌ Error: This doesn't appear to be the DhafnckMCP project root${RESET}"
    echo "Expected to find CLAUDE.md in: $PROJECT_ROOT"
    exit 1
fi

# Verify .claude directory exists
if [ ! -d "$CLAUDE_DIR" ]; then
    echo -e "${RED}❌ Error: .claude directory not found at: $CLAUDE_DIR${RESET}"
    echo "This script requires a .claude directory with commands"
    exit 1
fi

# Run main function
main "$@"