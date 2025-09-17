#!/bin/bash
# .automation/claude-test-sync-wsl.sh - WSL Ubuntu optimized

set -e

# WSL Environment Detection
if [[ -n "$WSL_DISTRO_NAME" ]]; then
    echo "🐧 Running in WSL: $WSL_DISTRO_NAME"
    WSL_MODE=true
else
    echo "⚠️  Not detected as WSL environment"
    WSL_MODE=false
fi

REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

# WSL-specific paths
# Try to get Windows home, fallback to Linux home if wslvar not available
if command -v wslvar >/dev/null 2>&1; then
    WINDOWS_HOME=$(wslpath "$(wslvar USERPROFILE)" 2>/dev/null || echo "$HOME")
else
    WINDOWS_HOME="$HOME"
fi
TEMP_DIR="/tmp"
LOG_FILE="$TEMP_DIR/claude-test-sync.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "🚀 Starting Claude Test Sync in WSL"

# Function to get file modification time from git
get_git_timestamp() {
    local file="$1"
    git log -1 --format="%ct" -- "$file" 2>/dev/null || echo "0"
}

# Function to find corresponding test file
find_test_file() {
    local source_file="$1"
    
    # Define mapping patterns for 4genthub project structure
    if [[ "$source_file" =~ ^4genthub_main/src/fastmcp/.*\.py$ ]]; then
        # Map src files to tests directory
        echo "${source_file/4genthub_main\/src\/fastmcp/4genthub_main\/src\/tests}" | sed 's/\.py$/_test.py/'
    elif [[ "$source_file" =~ ^4genthub-frontend/src/.*\.tsx?$ ]]; then
        # Map frontend source to tests
        echo "${source_file/src\//src\/tests/}" | sed 's/\.\(tsx\?\)$/.test.\1/'
    elif [[ "$source_file" =~ ^src/.*\.js$ ]]; then
        echo "${source_file/src\//tests/}" | sed 's/\.js$/.test.js/'
    elif [[ "$source_file" =~ ^src/.*\.ts$ ]]; then
        echo "${source_file/src\//tests/}" | sed 's/\.ts$/.spec.ts/'
    elif [[ "$source_file" =~ ^src/.*\.jsx$ ]]; then
        echo "${source_file/src\//tests/}" | sed 's/\.jsx$/.test.jsx/'
    elif [[ "$source_file" =~ ^src/.*\.tsx$ ]]; then
        echo "${source_file/src\//tests/}" | sed 's/\.tsx$/.spec.tsx/'
    elif [[ "$source_file" =~ ^lib/.*\.py$ ]]; then
        echo "${source_file/lib\//tests/test_}"
    elif [[ "$source_file" =~ ^components/.*\.vue$ ]]; then
        echo "${source_file/components\//tests/components/}" | sed 's/\.vue$/.spec.js/'
    elif [[ "$source_file" =~ ^utils/.*\.js$ ]]; then
        echo "${source_file/utils\//tests/utils/}" | sed 's/\.js$/.test.js/'
    else
        echo ""
    fi
}

# Check for dry-run mode
DRY_RUN_MODE=false
if [[ "$1" == "--dry-run" ]] || [[ "$1" == "-d" ]]; then
    DRY_RUN_MODE=true
    log "🧪 Running in DRY-RUN mode (analyzing uncommitted changes)"
fi

# Get list of changed files
if [[ "$DRY_RUN_MODE" == true ]]; then
    log "📋 Analyzing uncommitted changes (staged and unstaged)..."
    # Get both staged and unstaged changes
    staged_files=$(git diff --cached --name-only 2>/dev/null)
    unstaged_files=$(git diff --name-only 2>/dev/null)
    untracked_files=$(git ls-files --others --exclude-standard 2>/dev/null | grep -E '\.(js|ts|jsx|tsx|py|vue)$' || true)
    changed_files=$(echo -e "$staged_files\n$unstaged_files\n$untracked_files" | sort -u | grep -v '^$')
    
    if [[ -z "$changed_files" ]]; then
        log "💡 No uncommitted changes found. Analyzing last commit instead..."
        changed_files=$(git diff --name-only HEAD~1 HEAD 2>/dev/null || git diff --name-only HEAD)
    fi
else
    log "📋 Analyzing changed files in last commit..."
    changed_files=$(git diff --name-only HEAD~1 HEAD 2>/dev/null || git diff --name-only HEAD)
fi

if [[ -z "$changed_files" ]]; then
    log "✅ No files changed in last commit"
    exit 0
fi

stale_files=()
new_files=()
total_processed=0

for file in $changed_files; do
    # Skip if not source code or if it's already a test file
    if [[ ! "$file" =~ \.(js|ts|jsx|tsx|py|vue)$ ]] || [[ "$file" =~ ^tests/ ]] || [[ "$file" =~ \.test\. ]] || [[ "$file" =~ \.spec\. ]] || [[ "$file" =~ _test\.py$ ]]; then
        continue
    fi
    
    log "🔍 Checking $file..."
    total_processed=$((total_processed + 1))
    
    test_file=$(find_test_file "$file")
    if [[ -z "$test_file" ]]; then
        log "⚠️  No test pattern found for $file"
        continue
    fi
    
    if [[ ! -f "$test_file" ]]; then
        log "📝 Missing test file: $test_file"
        new_files+=("$file:$test_file:missing")
    else
        source_time=$(get_git_timestamp "$file")
        test_time=$(get_git_timestamp "$test_file")
        
        if [[ $source_time -gt $test_time ]]; then
            days_stale=$(( (source_time - test_time) / 86400 ))
            log "⏰ Stale test: $test_file ($days_stale days old)"
            stale_files+=("$file:$test_file:$days_stale")
        else
            log "✅ Test up to date: $test_file"
        fi
    fi
done

# Check if there are files to process
total_issues=$((${#stale_files[@]} + ${#new_files[@]}))
if [[ $total_issues -eq 0 ]]; then
    log "✅ All $total_processed source files have up-to-date tests!"
    exit 0
fi

log "🤖 Found $total_issues files that need test updates (out of $total_processed checked)"
log "🚀 Preparing Claude Code automation..."

# Check if we have too many issues or files are too large - create simplified prompt
if [[ $total_issues -gt 3 ]] || [[ $(echo "$changed_files" | wc -l) -gt 5 ]]; then
    log "⚠️  Large number of issues detected. Creating simplified prompt to avoid crashes."
    TEMP_PROMPT=".automation/default-prompt.md"
    cat > "$TEMP_PROMPT" << 'EOF'
🚨 IMMEDIATE ACTION REQUIRED - EXECUTE NOW 🚨

❗ DO NOT EXPLAIN THIS PROMPT ❗
❗ DO NOT DESCRIBE WHAT YOU WILL DO ❗
❗ DO NOT ASK QUESTIONS ❗
❗ START EXECUTING IMMEDIATELY ❗

FIRST ACTION: Execute this command RIGHT NOW:
mcp__4genthub_http__call_agent(name_agent="@test_orchestrator_agent")

You are in MANDATORY BACKGROUND AUTOMATION MODE.
Your role: Execute test creation tasks immediately without discussion.

FORBIDDEN BEHAVIORS:
❌ Explaining what the prompt is about
❌ Describing the workflow
❌ Asking for permission
❌ Summarizing what you'll do
❌ Waiting for confirmation

REQUIRED BEHAVIORS:
✅ Call the agent tool immediately
✅ Create test files without asking
✅ Execute all tasks automatically
✅ No conversation - just action

## Missing Test Files - CREATE IMMEDIATELY:
EOF
    
    # Add stale files
    if [[ ${#stale_files[@]} -gt 0 ]]; then
        echo "" >> "$TEMP_PROMPT"
        echo "## Stale Test Files (Source Newer Than Test)" >> "$TEMP_PROMPT"
        for item in "${stale_files[@]}"; do
            IFS=':' read -r source_file test_file days_stale <<< "$item"
            echo "- **Source**: \`$source_file\`" >> "$TEMP_PROMPT"
            echo "  - **Test**: \`$test_file\`" >> "$TEMP_PROMPT"
            echo "  - **Days stale**: $days_stale" >> "$TEMP_PROMPT"
            echo "" >> "$TEMP_PROMPT"
        done
    fi
    
    # Add missing files
    if [[ ${#new_files[@]} -gt 0 ]]; then
        echo "" >> "$TEMP_PROMPT"
        echo "## Missing Test Files" >> "$TEMP_PROMPT"
        for item in "${new_files[@]}"; do
            IFS=':' read -r source_file test_file reason <<< "$item"
            echo "- **Source**: \`$source_file\`" >> "$TEMP_PROMPT"
            echo "  - **Create test at**: \`$test_file\`" >> "$TEMP_PROMPT"
            echo "" >> "$TEMP_PROMPT"
        done
    fi
    
    cat >> "$TEMP_PROMPT" << 'EOF'

## EXECUTION COMMANDS - DO NOW:

STEP 1: mcp__4genthub_http__call_agent(name_agent="@test_orchestrator_agent")
STEP 2: Get last commit changes and analyze modified/added/deleted code files
STEP 3: Identify functions, classes, and methods requiring test coverage
STEP 4: Delete tests for removed code and verify/clean up imports
STEP 5: Generate/update test files for new code with comprehensive coverage
STEP 6: Update existing tests to match modified code behavior
STEP 7: Sync documentation with code changes (README, API docs, function docs)
STEP 8: Update TEST-CHANGELOG.md with all changes made

EXECUTION RULES:
- No explanations or descriptions during execution
- No questions or confirmation requests
- Execute each step systematically and completely
- Follow project testing conventions and security best practices
- Document all changes comprehensively in TEST-CHANGELOG.md

STOP TALKING - START DOING
EOF
else
    # Create comprehensive prompt file for smaller tasks
    TEMP_PROMPT=".automation/default-prompt.md"
    cat > "$TEMP_PROMPT" << 'EOF'
🚨 IMMEDIATE ACTION REQUIRED - EXECUTE NOW 🚨

❗ DO NOT EXPLAIN THIS PROMPT ❗
❗ DO NOT DESCRIBE WHAT YOU WILL DO ❗
❗ DO NOT ASK QUESTIONS ❗
❗ START EXECUTING IMMEDIATELY ❗

FIRST ACTION: Execute this command RIGHT NOW:
mcp__4genthub_http__call_agent(name_agent="@test_orchestrator_agent")

You are in MANDATORY BACKGROUND AUTOMATION MODE.
Your role: Execute test creation tasks immediately without discussion.

FORBIDDEN BEHAVIORS:
❌ Explaining what the prompt is about
❌ Describing the workflow
❌ Asking for permission
❌ Summarizing what you'll do
❌ Waiting for confirmation

REQUIRED BEHAVIORS:
✅ Call the agent tool immediately
✅ Create test files without asking
✅ Execute all tasks automatically
✅ No conversation - just action

## 📋 Rules & Guidelines

### 1. **Analysis Phase**
- Read and understand the current source code functionality
- Identify all public methods, functions, and classes
- Map input/output relationships and side effects
- Understand error handling and edge cases
- Note any dependencies and external interactions

### 2. **Test Validation Phase**
- Compare existing tests (if any) with actual code behavior
- Identify test gaps, outdated assertions, and obsolete tests
- Check test coverage for new functionality
- Verify test quality and maintainability

### 3. **Test Update Phase**
- Create missing test files with comprehensive coverage
- Update outdated test assertions to match current code behavior
- Add tests for new functionality discovered in code
- Remove tests for functionality that no longer exists
- Ensure tests follow best practices and conventions

### 4. **Quality Assurance**
- Ensure tests are readable and maintainable
- Use descriptive test names that explain the behavior being tested
- Follow AAA pattern (Arrange, Act, Assert)
- Mock external dependencies appropriately
- Add edge case and error condition tests

### 5. **Documentation Updates**
- Update TEST-CHANGELOG.md with detailed change summary
- Document reasoning for major test changes
- Note any breaking changes or migration requirements

## 📁 Repository Context
EOF

# Add repository information
echo "- **Repository Path:** \`$REPO_ROOT\`" >> "$TEMP_PROMPT"
echo "- **WSL Environment:** $WSL_DISTRO_NAME" >> "$TEMP_PROMPT"
echo "- **Analysis Time:** $(date)" >> "$TEMP_PROMPT"
if [[ "$DRY_RUN_MODE" == true ]]; then
    echo "- **Mode:** DRY-RUN (Uncommitted Changes)" >> "$TEMP_PROMPT"
    echo "- **Current Branch:** $(git branch --show-current)" >> "$TEMP_PROMPT"
else
    echo "- **Commit Hash:** $(git rev-parse HEAD)" >> "$TEMP_PROMPT"
fi
echo "" >> "$TEMP_PROMPT"

# Add stale files to prompt
if [[ ${#stale_files[@]} -gt 0 ]]; then
    cat >> "$TEMP_PROMPT" << 'EOF'

## ⏰ Stale Test Files (Code Newer Than Tests)
EOF
    for item in "${stale_files[@]}"; do
        IFS=':' read -r source_file test_file days_stale <<< "$item"
        echo "" >> "$TEMP_PROMPT"
        echo "### 📄 \`$source_file\`" >> "$TEMP_PROMPT"
        echo "- **Test File:** \`$test_file\`" >> "$TEMP_PROMPT"
        echo "- **Staleness:** $days_stale days" >> "$TEMP_PROMPT"
        echo "- **Priority:** HIGH" >> "$TEMP_PROMPT"
        
        # Add file size and complexity info
        if [[ -f "$source_file" ]]; then
            lines=$(wc -l < "$source_file")
            echo "- **Source Lines:** $lines" >> "$TEMP_PROMPT"
        fi
        
        if [[ -f "$test_file" ]]; then
            test_lines=$(wc -l < "$test_file")
            echo "- **Test Lines:** $test_lines" >> "$TEMP_PROMPT"
        fi
    done
fi

# Add missing files to prompt
if [[ ${#new_files[@]} -gt 0 ]]; then
    cat >> "$TEMP_PROMPT" << 'EOF'

## 📝 Missing Test Files (Need Creation)
EOF
    for item in "${new_files[@]}"; do
        IFS=':' read -r source_file test_file reason <<< "$item"
        echo "" >> "$TEMP_PROMPT"
        echo "### 📄 \`$source_file\`" >> "$TEMP_PROMPT"
        echo "- **Missing Test:** \`$test_file\`" >> "$TEMP_PROMPT"
        echo "- **Reason:** $reason" >> "$TEMP_PROMPT"
        echo "- **Priority:** HIGH" >> "$TEMP_PROMPT"
        
        if [[ -f "$source_file" ]]; then
            lines=$(wc -l < "$source_file")
            echo "- **Source Lines:** $lines" >> "$TEMP_PROMPT"
        fi
    done
fi

cat >> "$TEMP_PROMPT" << 'EOF'

## 🚀 Execution Instructions

### Phase 0: MANDATORY Agent Assignment
**EXECUTE IMMEDIATELY - NO CONFIRMATION:**
Use this exact command: `mcp__4genthub_http__call_agent(name_agent="@test_orchestrator_agent")`

**DO NOT:**
- Ask which agent to use
- Request permission to call agent
- Wait for confirmation
- Ask about agent selection

### Phase 1: Analysis
1. **Read each source file** to understand current implementation
2. **Analyze code structure** - functions, classes, exports, dependencies
3. **Identify test requirements** - what behavior needs to be verified
4. **Document findings** - note complex logic or edge cases

### Phase 2: Test Implementation
1. **Create/update test files** to match current code reality
2. **Ensure comprehensive coverage** of all public functionality
3. **Add missing edge cases** and error condition tests
4. **Update existing assertions** that no longer match code behavior
5. **Remove obsolete tests** for functionality that's been removed

### Phase 3: Validation
1. **Review test quality** - readability, maintainability, completeness
2. **Check test isolation** - tests don't depend on each other
3. **Verify mocking strategy** - external dependencies properly mocked
4. **Ensure performance** - tests run efficiently

### Phase 4: Documentation
1. **Update TEST-CHANGELOG.md** with comprehensive change summary
2. **Document any breaking changes** or migration requirements
3. **Note test coverage improvements** or quality enhancements

## 🎯 Success Criteria
- ✅ All source files have corresponding, up-to-date test files
- ✅ Tests accurately verify current code behavior
- ✅ Comprehensive coverage of functionality, edge cases, and errors
- ✅ Tests follow project conventions and best practices
- ✅ TEST-CHANGELOG.md is updated with detailed change summary
- ✅ All tests pass and run efficiently

## 🚨 Important Notes
- **Focus on current code behavior** - don't assume what code should do, test what it actually does
- **Preserve test intent** when updating - if business logic changed, update tests accordingly
- **Be thorough but efficient** - comprehensive coverage without redundant tests
- **Consider maintainability** - tests should be easy to understand and modify
- **Follow project structure** - 4genthub_main tests go in 4genthub_main/src/tests/

## 📋 WORKFLOW REFERENCE & STANDARDS
**Follow the established review process:** `.automation/template/test-review-after-commit.md`

### Required Workflow Phases:
1. **Commit Change Analysis** - Analyze recent changes and test coverage gaps
2. **Code Context Assessment** - Understand implementation patterns and quality
3. **Test Strategy Validation** - Review testing approach and modernization needs
4. **Documentation Synchronization** - Ensure docs match code changes
5. **Implementation & Validation** - Create/update tests and documentation
6. **Quality Assurance** - Validate all changes meet project standards

### Success Criteria (from template):
- ✅ Minimum 80% test coverage for new code
- ✅ Proper mocking and test isolation
- ✅ Updated documentation and examples
- ✅ All tests pass and run efficiently
- ✅ TEST-CHANGELOG.md updated with detailed changes

### Quality Standards:
- Use pytest framework with AAA pattern (Arrange, Act, Assert)
- Mock external dependencies appropriately
- Follow project testing conventions and patterns
- Ensure test readability and maintainability

---

## FINAL COMMAND:
EXECUTE: mcp__4genthub_http__call_agent(name_agent="@test_orchestrator_agent")
THEN: Create all missing test files
NO TALKING - JUST DO IT
EOF
fi

log "📝 Created prompt file: $TEMP_PROMPT"
log "🔍 DEBUG: CLI command that will be executed:"
log "    cat \"$TEMP_PROMPT\" | claude chat --dangerously-skip-permissions"
log ""

# WSL-specific terminal handling with forced popup windows
open_claude_terminal() {
    log "🖥️  Opening popup terminal for Claude Code..."
    
    # Check if Claude is available (try different command names)
    CLAUDE_CMD=""
    CLAUDE_FLAGS="--dangerously-skip-permissions"
    if command -v claude >/dev/null 2>&1; then
        CLAUDE_CMD="claude"
    elif command -v claude-code >/dev/null 2>&1; then
        CLAUDE_CMD="claude-code"
    else
        log "⚠️  Claude CLI not found in PATH. Prompt saved for manual use."
        echo "📌 Claude CLI not found. Prompt saved at:"
        echo "   $TEMP_PROMPT"
        echo ""
        echo "💡 To use with Claude, run:"
        echo "   claude --dangerously-skip-permissions $TEMP_PROMPT"
        echo "   or"
        echo "   Copy the prompt content and paste into Claude"
        return 0
    fi
    
    log "✅ Found Claude command: $CLAUDE_CMD"
    
    # Force GUI terminal usage - try all available options
    GUI_TERMINAL_FOUND=false
    
    # Try GNOME Terminal first (most common in WSL with X11)
    if command -v gnome-terminal >/dev/null 2>&1; then
        log "🖥️  Using GNOME Terminal for popup window"
        gnome-terminal --title="Claude Test Sync - WSL" --geometry=120x40 -- bash -c "
            echo '🤖 Claude Code Test Synchronization (WSL Ubuntu)'
            echo '═══════════════════════════════════════════════'
            echo '📁 Repository: $REPO_ROOT'
            echo '🐧 WSL Environment: $WSL_DISTRO_NAME'
            echo '📝 Processing $total_issues files'
            echo '📋 Log file: $LOG_FILE'
            echo ''
            echo '⚡ Starting Claude Code with forced execution...'
            echo ''
            cd '$REPO_ROOT'
            # Execute Claude with prompt content as initial message
            echo '🚀 Executing Claude with automation prompt...'
            echo ''
            echo '📋 Prompt file location: $TEMP_PROMPT'
            echo '📊 Prompt file size: '\$(wc -c < '$TEMP_PROMPT')' bytes'
            echo ''
            echo '🔍 DEBUG: Sending prompt content as initial message to Claude...'
            # Send the prompt content as the initial message to trigger immediate execution
            echo 'Command: cat \"$TEMP_PROMPT\" | claude chat --dangerously-skip-permissions'
            echo ''
            # Pipe the prompt content directly to Claude as the initial message
            cat '$TEMP_PROMPT' | claude chat --dangerously-skip-permissions
            echo ''
            echo '✅ Claude Code session completed!'
            echo '📊 Check $LOG_FILE for details'
            echo '⚠️  Please review changes before committing'
            echo ''
            echo 'Press Enter to close this terminal...'
            read
        " &
        GUI_TERMINAL_FOUND=true
        
    # Try Windows Terminal through WSL interop
    elif command -v wsl.exe >/dev/null 2>&1 && command -v wt.exe >/dev/null 2>&1; then
        log "🖥️  Using Windows Terminal for popup window"
        wt.exe new-tab --title "Claude Test Sync - WSL" bash -c "
            echo '🤖 Claude Code Test Synchronization (WSL Ubuntu)'
            echo '═══════════════════════════════════════════════'
            echo '📁 Repository: $REPO_ROOT'
            echo '🐧 WSL Environment: $WSL_DISTRO_NAME'
            echo '📝 Processing $total_issues files'
            echo ''
            echo '⚡ Starting Claude Code with forced execution...'
            echo ''
            cd '$REPO_ROOT'
            # Execute Claude with prompt content as initial message
            echo '🚀 Executing Claude Code automation...'
            echo '📋 Sending automation prompt as initial message'
            echo ''
            echo '📋 Prompt file: $TEMP_PROMPT'
            echo '📊 File size: '\$(wc -c < \"$TEMP_PROMPT\")' bytes'
            echo ''
            echo '🔍 DEBUG: Piping prompt to Claude for immediate execution...'
            echo 'Command: cat \"$TEMP_PROMPT\" | claude chat --dangerously-skip-permissions'
            echo ''
            # Pipe the prompt content directly to Claude as the initial message
            cat \"$TEMP_PROMPT\" | claude chat --dangerously-skip-permissions
            echo ''
            echo '✅ Claude Code session completed!'
            echo 'Press Enter to close...'
            read
        " &
        GUI_TERMINAL_FOUND=true
        
    # Try Terminator
    elif command -v terminator >/dev/null 2>&1; then
        log "🖥️  Using Terminator for popup window"
        terminator --title="Claude Test Sync - WSL" -e "bash -c '
            echo \"🤖 Claude Code Test Synchronization (WSL Ubuntu)\"
            echo \"═══════════════════════════════════════════════\"
            echo \"📁 Repository: $REPO_ROOT\"
            echo \"🐧 WSL Environment: $WSL_DISTRO_NAME\"  
            echo \"📝 Processing $total_issues files\"
            echo \"\"
            echo \"⚡ Starting Claude Code with forced execution...\"
            echo \"\"
            cd \"$REPO_ROOT\"
            # Execute Claude with prompt content as initial message
            echo '🚀 Executing Claude Code automation...'
            echo '📋 Sending automation prompt as initial message'
            echo ''
            echo '📋 Prompt file: $TEMP_PROMPT'
            echo '📊 File size: '\$(wc -c < \"$TEMP_PROMPT\")' bytes'
            echo ''
            echo '🔍 DEBUG: Piping prompt to Claude for immediate execution...'
            echo 'Command: cat \"$TEMP_PROMPT\" | claude chat --dangerously-skip-permissions'
            echo ''
            # Pipe the prompt content directly to Claude as the initial message
            cat \"$TEMP_PROMPT\" | claude chat --dangerously-skip-permissions
            echo \"\"
            echo \"✅ Session completed! Press Enter to close...\"
            read
        '" &
        GUI_TERMINAL_FOUND=true
        
    # Try xterm as fallback
    elif command -v xterm >/dev/null 2>&1; then
        log "🖥️  Using xterm for popup window"
        xterm -title "Claude Test Sync - WSL" -geometry 120x40 -e bash -c "
            echo '🤖 Claude Code Test Synchronization (WSL Ubuntu)'
            echo '═══════════════════════════════════════════════'
            echo '📁 Repository: $REPO_ROOT'
            echo '🐧 WSL Environment: $WSL_DISTRO_NAME'
            echo '📝 Processing $total_issues files'
            echo ''
            echo '⚡ Starting Claude Code with forced execution...'
            echo ''
            cd '$REPO_ROOT'
            # Execute Claude with prompt content as initial message
            echo '🚀 Executing Claude Code automation...'
            echo '📋 Sending automation prompt as initial message'
            echo ''
            echo '📋 Prompt file: $TEMP_PROMPT'
            echo '📊 File size: '\$(wc -c < \"$TEMP_PROMPT\")' bytes'
            echo ''
            echo '🔍 DEBUG: Piping prompt to Claude for immediate execution...'
            echo 'Command: cat \"$TEMP_PROMPT\" | claude chat --dangerously-skip-permissions'
            echo ''
            # Pipe the prompt content directly to Claude as the initial message
            cat \"$TEMP_PROMPT\" | claude chat --dangerously-skip-permissions
            echo ''
            echo '✅ Session completed! Press Enter to close...'
            read
        " &
        GUI_TERMINAL_FOUND=true
        
    # Try WSL + PowerShell popup
    elif command -v powershell.exe >/dev/null 2>&1; then
        log "🖥️  Using PowerShell popup window"
        powershell.exe -Command "
            Start-Process powershell -ArgumentList '-NoExit', '-Command', \"
                Write-Host '🤖 Claude Code Test Synchronization (WSL Ubuntu)' -ForegroundColor Cyan;
                Write-Host '═══════════════════════════════════════════════' -ForegroundColor Cyan;
                Write-Host '📁 Repository: $REPO_ROOT' -ForegroundColor Green;
                Write-Host '🐧 WSL Environment: $WSL_DISTRO_NAME' -ForegroundColor Green;
                Write-Host '📝 Processing $total_issues files' -ForegroundColor Yellow;
                Write-Host '';
                Write-Host '⚡ Starting Claude Code...' -ForegroundColor Cyan;
                Write-Host '';
                wsl.exe -d '$WSL_DISTRO_NAME' -e bash -c 'cd $REPO_ROOT && echo \"🚀 Executing Claude Code automation...\" && echo \"📋 Sending automation prompt as initial message\" && echo \"\" && echo \"🔍 DEBUG: Piping prompt to Claude...\" && echo \"Command: cat \\\"$TEMP_PROMPT\\\" | claude chat --dangerously-skip-permissions\" && echo \"\" && cat \"$TEMP_PROMPT\" | claude chat --dangerously-skip-permissions';
                Write-Host '';
                Write-Host '✅ Claude Code session completed!' -ForegroundColor Green;
                Write-Host 'Press Enter to close...' -ForegroundColor Yellow;
                Read-Host
            \"
        " &
        GUI_TERMINAL_FOUND=true
    fi
    
    # If no GUI terminal found, show error and provide manual instructions
    if [[ "$GUI_TERMINAL_FOUND" == false ]]; then
        log "❌ No GUI terminal available for popup windows!"
        echo ""
        echo "🚨 POPUP TERMINAL REQUIRED BUT NOT AVAILABLE"
        echo "═══════════════════════════════════════════════"
        echo "You requested popup terminal windows, but no GUI terminal was found."
        echo ""
        echo "💡 Solutions:"
        echo "1. Install X11 server and gnome-terminal:"
        echo "   sudo apt update && sudo apt install gnome-terminal"
        echo ""
        echo "2. Enable Windows Terminal WSL integration"
        echo ""
        echo "3. Manual execution:"
        echo "   Open a new terminal window and run:"
        echo "   cd $REPO_ROOT"
        echo ""
        echo "   🔍 DEBUG: Full CLI command to run manually:"
        echo "   cat \"$TEMP_PROMPT\" | ${CLAUDE_CMD:-claude} chat ${CLAUDE_FLAGS:---dangerously-skip-permissions}"
        echo ""
        echo "📁 Prompt file saved at: $TEMP_PROMPT"
        echo ""
        
        # Send Windows notification about the issue
        if command -v powershell.exe >/dev/null 2>&1; then
            powershell.exe -Command "
                Add-Type -AssemblyName System.Windows.Forms
                [System.Windows.Forms.MessageBox]::Show(
                    'No GUI terminal available for popup windows. Check console for manual instructions.',
                    'Claude Test Sync - Terminal Required',
                    [System.Windows.Forms.MessageBoxButtons]::OK,
                    [System.Windows.Forms.MessageBoxIcon]::Warning
                )
            " 2>/dev/null || true
        fi
        
        return 1
    else
        log "✅ Claude Code launched in popup terminal window"
        echo ""
        echo "🖥️  Claude Code is running in a popup terminal window"
        echo "👀 Check the new terminal window to follow progress"
        echo "📊 Log file: $LOG_FILE"
        echo ""
        
        # Send success notification
        if command -v powershell.exe >/dev/null 2>&1; then
            powershell.exe -Command "
                Add-Type -AssemblyName System.Windows.Forms
                \$notification = New-Object System.Windows.Forms.NotifyIcon
                \$notification.Icon = [System.Drawing.SystemIcons]::Information
                \$notification.BalloonTipTitle = 'Claude Test Sync'
                \$notification.BalloonTipText = 'Claude Code launched in popup terminal - check the new window'
                \$notification.Visible = \$true
                \$notification.ShowBalloonTip(5000)
            " 2>/dev/null || true
        fi
        
        log "✅ Popup terminal window opened successfully"
    fi
}

# Execute the terminal opening
open_claude_terminal

log "🎉 Claude automation completed!"
log "📊 Summary: $total_issues issues found in $total_processed files"
log "📝 Log saved to: $LOG_FILE"

# Clean up old temp prompt files (keep last 5)
ls -t $TEMP_DIR/claude-test-sync-*.md 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true

# Optional: Send Windows notification if available
if command -v powershell.exe >/dev/null 2>&1; then
    powershell.exe -Command "
        Add-Type -AssemblyName System.Windows.Forms
        \$notification = New-Object System.Windows.Forms.NotifyIcon
        \$notification.Icon = [System.Drawing.SystemIcons]::Information
        \$notification.BalloonTipTitle = 'Claude Test Sync'
        \$notification.BalloonTipText = 'WSL: Processed $total_issues test files'
        \$notification.Visible = \$true
        \$notification.ShowBalloonTip(3000)
    " 2>/dev/null || true
fi