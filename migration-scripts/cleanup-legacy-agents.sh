#!/bin/bash
# DEPRECATED SCRIPT - DO NOT USE
# 
# The agent-library system is NOT legacy and should NOT be removed
# It is an active system used for server-side agent building

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
BACKUP_DIR="${PROJECT_ROOT}/backups/$(date +%Y%m%d_%H%M%S)"

echo -e "${CYAN}${BOLD}🧹 DhafnckMCP Legacy Agent Cleanup${RESET}"
echo -e "${CYAN}${BOLD}===================================${RESET}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to create backup
create_backup() {
    echo -e "${YELLOW}📦 Creating comprehensive backup...${RESET}"
    mkdir -p "$BACKUP_DIR"
    
    # Backup legacy agent system if it exists
    if [ -d "$PROJECT_ROOT/dhafnck_mcp_main/agent-library" ]; then
        echo "  • Backing up agent-library system..."
        cp -r "$PROJECT_ROOT/dhafnck_mcp_main/agent-library" "$BACKUP_DIR/"
        echo -e "${GREEN}  ✅ agent-library backed up${RESET}"
    else
        echo -e "${CYAN}  ℹ️  No legacy agent-library directory found${RESET}"
    fi
    
    # Backup current .claude/agents system
    if [ -d "$PROJECT_ROOT/.claude/agents" ]; then
        echo "  • Backing up current .claude/agents system..."
        cp -r "$PROJECT_ROOT/.claude/agents" "$BACKUP_DIR/"
        echo -e "${GREEN}  ✅ .claude/agents backed up${RESET}"
    fi
    
    # Create git commit as additional backup
    cd "$PROJECT_ROOT"
    if [ -d ".git" ]; then
        echo "  • Creating git commit backup..."
        git add -A >/dev/null 2>&1 || true
        git commit -m "Backup before legacy agent cleanup - $(date +%Y-%m-%d_%H:%M:%S)" >/dev/null 2>&1 || echo "    No changes to commit"
        echo -e "${GREEN}  ✅ Git backup created${RESET}"
    fi
    
    echo -e "${GREEN}✅ Backup completed: $BACKUP_DIR${RESET}"
    echo ""
}

# Function to analyze current agent systems
analyze_systems() {
    echo -e "${YELLOW}🔍 Analyzing current agent systems...${RESET}"
    
    # Count legacy agents
    LEGACY_COUNT=0
    if [ -d "$PROJECT_ROOT/dhafnck_mcp_main/agent-library/agents" ]; then
        LEGACY_COUNT=$(find "$PROJECT_ROOT/dhafnck_mcp_main/agent-library/agents" -type d -name "*agent*" 2>/dev/null | wc -l)
    fi
    
    # Count new system agents
    NEW_COUNT=0
    if [ -d "$PROJECT_ROOT/.claude/agents" ]; then
        NEW_COUNT=$(find "$PROJECT_ROOT/.claude/agents" -name "*.md" 2>/dev/null | wc -l)
    fi
    
    echo "  📊 System Analysis:"
    echo "    • Legacy YAML agents: $LEGACY_COUNT"
    echo "    • New Markdown agents: $NEW_COUNT"
    echo ""
    
    if [ "$LEGACY_COUNT" -eq 0 ]; then
        echo -e "${GREEN}  ✅ No legacy agents found - cleanup not needed${RESET}"
        return 1
    fi
    
    if [ "$NEW_COUNT" -ge "$LEGACY_COUNT" ]; then
        echo -e "${GREEN}  ✅ Agent migration appears complete (new >= legacy)${RESET}"
        return 0
    else
        echo -e "${YELLOW}  ⚠️  Warning: New system has fewer agents than legacy system${RESET}"
        echo "    This might indicate incomplete migration."
        echo ""
        return 2
    fi
}

# Function to verify agent functionality
verify_agent_functionality() {
    echo -e "${YELLOW}🔍 Verifying agent system functionality...${RESET}"
    
    # Check if MCP server is accessible (basic test)
    cd "$PROJECT_ROOT/dhafnck_mcp_main"
    
    # Test if Python environment works
    if [ -d "venv" ]; then
        source venv/bin/activate
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
    fi
    
    # Basic import test
    if python -c "from fastmcp.task_management.application.use_cases.call_agent import CallAgentUseCase; print('Agent system imports successfully')" 2>/dev/null; then
        echo -e "${GREEN}  ✅ Agent system imports successfully${RESET}"
    else
        echo -e "${YELLOW}  ⚠️  Cannot verify agent system (development environment not set up)${RESET}"
    fi
    
    # Check agent directory structure
    if [ -d "$PROJECT_ROOT/.claude/agents" ] && [ "$(ls -A "$PROJECT_ROOT/.claude/agents")" ]; then
        echo -e "${GREEN}  ✅ New agent system has content${RESET}"
    else
        echo -e "${RED}  ❌ New agent system appears empty${RESET}"
        return 1
    fi
    
    echo ""
    return 0
}

# Function to show agent comparison
show_agent_comparison() {
    echo -e "${YELLOW}📋 Agent System Comparison:${RESET}"
    echo ""
    
    if [ -d "$PROJECT_ROOT/dhafnck_mcp_main/agent-library/agents" ]; then
        echo -e "${YELLOW}Legacy YAML Agents:${RESET}"
        find "$PROJECT_ROOT/dhafnck_mcp_main/agent-library/agents" -type d -name "*agent*" | sort | while read -r dir; do
            agent_name=$(basename "$dir")
            echo "  • $agent_name"
        done
        echo ""
    fi
    
    if [ -d "$PROJECT_ROOT/.claude/agents" ]; then
        echo -e "${GREEN}New Markdown Agents:${RESET}"
        find "$PROJECT_ROOT/.claude/agents" -name "*.md" | sort | while read -r file; do
            agent_name=$(basename "$file" .md)
            echo "  • $agent_name"
        done
        echo ""
    fi
}

# Function to remove legacy system
remove_legacy_system() {
    echo -e "${YELLOW}🗑️  Removing legacy agent-library system...${RESET}"
    
    if [ -d "$PROJECT_ROOT/dhafnck_mcp_main/agent-library" ]; then
        # Additional safety check
        if [ -d "$BACKUP_DIR/agent-library" ]; then
            rm -rf "$PROJECT_ROOT/dhafnck_mcp_main/agent-library"
            echo -e "${GREEN}  ✅ Legacy agent-library system removed${RESET}"
        else
            echo -e "${RED}  ❌ Backup not found, aborting removal for safety${RESET}"
            return 1
        fi
    else
        echo -e "${CYAN}  ℹ️  Legacy agent-library already removed${RESET}"
    fi
    
    # Clean up any potential YAML parsing dependencies
    # This is conservative - only remove if we're certain they're not used elsewhere
    echo "  • Checking for unused YAML dependencies..."
    # cd "$PROJECT_ROOT/dhafnck_mcp_main"
    # Check requirements.txt or pyproject.toml for yaml dependencies
    # This would need careful manual review
    echo -e "${GREEN}  ✅ Legacy system removal complete${RESET}"
    echo ""
}

# Function to generate cleanup report
generate_report() {
    local report_file="$BACKUP_DIR/cleanup-report.txt"
    
    echo -e "${YELLOW}📄 Generating cleanup report...${RESET}"
    
    cat > "$report_file" << EOF
DhafnckMCP Legacy Agent Cleanup Report
=====================================
Date: $(date)
Backup Location: $BACKUP_DIR

System Analysis:
- Legacy YAML Agents: $LEGACY_COUNT
- New Markdown Agents: $NEW_COUNT
- Migration Status: $([ $NEW_COUNT -ge $LEGACY_COUNT ] && echo "Complete" || echo "Needs Review")

Actions Performed:
✅ Created comprehensive backup
✅ Analyzed agent systems
✅ Verified new system functionality
✅ Removed legacy agent-library directory
✅ Generated cleanup report

Files Backed Up:
$(find "$BACKUP_DIR" -type f | sed 's|^|  |')

Rollback Instructions:
To rollback this cleanup:
1. cd $PROJECT_ROOT
2. git reset --hard HEAD~1 (if using git backup)
3. Or restore from backup: cp -r $BACKUP_DIR/agent-library dhafnck_mcp_main/

Next Steps:
- Verify agent functionality with MCP calls
- Update any documentation references
- Remove this backup after confirming everything works
EOF
    
    echo -e "${GREEN}  ✅ Report saved to: $report_file${RESET}"
}

# Main execution function - DISABLED
main() {
    echo "❌ ERROR: This script has been DISABLED"
    echo ""
    echo "🚨 CRITICAL: agent-library is NOT legacy!"  
    echo "   • The 43 agents in agent-library/ are ACTIVE"
    echo "   • Used for server-side agent building"
    echo "   • Required for production operations"
    echo "   • DO NOT REMOVE agent-library content"
    echo ""
    echo "✅ Corrected understanding:"
    echo "   • agent-library/ = Server-side agent definitions (YAML)"
    echo "   • .claude/agents/ = Client-side agent configurations"
    echo "   • Both systems work together"
    echo ""
    echo "If you need to perform actual cleanup, use:"
    echo "   ./cleanup-obsolete-files.sh"
    echo ""
    exit 1
}

# Verify we're in the right directory
if [ ! -f "$PROJECT_ROOT/CLAUDE.md" ]; then
    echo -e "${RED}❌ Error: This doesn't appear to be the DhafnckMCP project root${RESET}"
    echo "Expected to find CLAUDE.md in: $PROJECT_ROOT"
    exit 1
fi

# Run main function
main "$@"