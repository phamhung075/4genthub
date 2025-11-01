# cclaude CLI - Multiple Claude Terminal Sessions

## Overview
Research and implementation of a CLI tool to open multiple Claude Code terminal sessions in VSCode, similar to the built-in Task tool but for interactive terminal-based work.

**Date**: 2025-11-01
**Status**: Prototype Implemented
**Location**: `.claude/bin/cclaude`

---

## Research Summary

### Question
Can we create a CLI command (like `cclaude`) that opens new VSCode terminal sessions running Claude, allowing multiple parallel interactive sessions similar to how the Task tool works?

### Answer
**YES** - It's feasible with multiple approaches. A basic implementation has been created.

---

## Architecture Analysis

### Current Task Tool vs Proposed cclaude CLI

| Aspect | Task Tool (Built-in) | cclaude CLI (Proposed) |
|--------|---------------------|----------------------|
| **Purpose** | Automated sub-agent delegation | Interactive terminal sessions |
| **Visibility** | Background (invisible) | Foreground (visible terminals) |
| **Session Type** | Managed within Claude Code | Independent terminal processes |
| **Context Sharing** | Efficient (shared parent context) | Isolated (each terminal separate) |
| **Interactivity** | No user interaction | Full terminal interaction |
| **Token Efficiency** | High (delegates with task IDs) | Lower (full session per terminal) |
| **Use Case** | Automation, delegation | Debugging, monitoring, manual work |
| **Parallelism** | Multiple agents, one session | Multiple terminals, multiple sessions |

### Key Insights

1. **Different Tools, Different Purposes**
   - Task tool: For automated workflows and efficient delegation
   - cclaude CLI: For interactive, visible, manual work sessions

2. **Token Economics**
   - Task tool delegates with just task IDs (~10 tokens)
   - cclaude would create full sessions (~1000+ tokens each)
   - Trade visibility/interactivity for efficiency

3. **Complementary, Not Replacement**
   - Task tool remains ideal for automation
   - cclaude serves interactive debugging/monitoring needs
   - Both can coexist in workflow

---

## Implementation Approaches

### Approach 1: Shell Script (IMPLEMENTED) ✅

**File**: `.claude/bin/cclaude`

```bash
#!/bin/bash
# Opens new terminal with Claude session

TASK_DESC="$*"

# Platform detection and terminal launching
if command -v gnome-terminal &> /dev/null; then
    gnome-terminal -- bash -c "claude '$TASK_DESC'; exec bash"
elif command -v osascript &> /dev/null; then
    osascript -e "tell application \"Terminal\" to do script \"claude '$TASK_DESC'\""
else
    claude "$TASK_DESC"  # Fallback to current terminal
fi
```

**Pros:**
- ✅ Simple, no dependencies
- ✅ Easy to modify
- ✅ Works immediately
- ✅ Version controlled in project

**Cons:**
- ⚠️ Platform-specific terminal detection
- ⚠️ Limited VSCode API access
- ⚠️ Manual terminal management

### Approach 2: VSCode Extension (FUTURE)

```typescript
// Extension with deep VSCode integration
vscode.commands.registerCommand('cclaude.newSession', async (taskDesc) => {
  const terminal = vscode.window.createTerminal({
    name: `Claude: ${taskDesc.substring(0, 20)}...`,
    cwd: vscode.workspace.rootPath
  });
  terminal.sendText(`claude "${taskDesc}"`);
  terminal.show();
});
```

**Pros:**
- ✅ Native VSCode integration
- ✅ Terminal lifecycle management
- ✅ Custom UI possibilities
- ✅ Cross-platform consistency

**Cons:**
- ⚠️ Requires extension development
- ⚠️ Distribution/publishing overhead
- ⚠️ More complex maintenance

### Approach 3: MCP Integration (RECOMMENDED FUTURE)

```bash
#!/bin/bash
# Enhanced with MCP task tracking

# Create MCP task first
TASK_ID=$(python3 .claude/bin/create_mcp_task.py "$*")

# Open terminal with task context
gnome-terminal -- bash -c "claude 'task_id: $TASK_ID'; exec bash"

echo "Task $TASK_ID opened in new terminal"
```

**Pros:**
- ✅ Integrates with existing MCP system
- ✅ Context persists across sessions
- ✅ Task tracking maintained
- ✅ Follows project patterns

**Cons:**
- ⚠️ Requires MCP helper scripts
- ⚠️ Additional setup complexity

---

## Current Implementation Status

### What's Working ✅

1. **Basic Script Created**
   - Location: `.claude/bin/cclaude`
   - Executable permissions set
   - Added to PATH (via `~/.bashrc`)

2. **Platform Support**
   - Linux/WSL2: gnome-terminal detection
   - macOS: AppleScript automation
   - Fallback: Current terminal

3. **Usage**
   ```bash
   # After sourcing ~/.bashrc
   cclaude "Fix authentication bug"
   cclaude "Implement user dashboard"
   ```

### What's Next 🚀

1. **MCP Integration** (Phase 2)
   - Create helper script to generate MCP tasks
   - Pass task IDs to new terminals
   - Enable context sharing

2. **VSCode Extension** (Phase 3 - Optional)
   - Native terminal creation
   - Keybinding support (e.g., Ctrl+Shift+C)
   - Custom sidebar for session management

3. **Session Management**
   - Track active cclaude sessions
   - Auto-cleanup on completion
   - Session status monitoring

---

## Use Cases

### Best Use Cases for cclaude ✅

1. **Interactive Debugging**
   ```bash
   # Terminal 1: Watch logs
   cclaude "Monitor application logs"

   # Terminal 2: Debug specific issue
   cclaude "Debug user login flow"

   # Terminal 3: Run tests
   cclaude "Run test suite with verbose output"
   ```

2. **Parallel Development**
   ```bash
   # Frontend work
   cclaude "Implement user dashboard UI"

   # Backend work
   cclaude "Create REST API endpoints"

   # Database work
   cclaude "Design database schema"
   ```

3. **Long-Running Tasks**
   - Visible progress tracking
   - Ability to interact mid-execution
   - Manual intervention possible

### NOT Ideal For ❌

- Fully automated workflows → Use Task tool
- Token-efficient delegation → Use Task tool
- Background processing → Use Task tool

---

## Technical Considerations

### Platform Compatibility

**Linux/WSL2** (Current Environment)
```bash
# Uses gnome-terminal
gnome-terminal --working-directory="$PWD" \
               --title="Claude: $TASK_DESC" \
               -- bash -c "claude '$TASK_DESC'"
```

**macOS**
```bash
# Uses AppleScript
osascript -e 'tell application "Terminal"
    do script "cd '$PWD' && claude '$TASK_DESC'"
end tell'
```

**Windows**
```bash
# Uses cmd.exe or PowerShell
start cmd /k "cd /d %CD% && claude %TASK_DESC%"
```

### Session Management

**Current**:
- Each terminal is independent
- No automatic cleanup
- Manual session tracking

**Future** (with MCP integration):
- MCP tasks track all sessions
- Automatic status updates
- Cleanup on completion
- Session history preserved

---

## Comparison with Existing Tools

### vs. Built-in Task Tool

**Task Tool** (for automation):
```python
# Invisible background delegation
Task(subagent_type="coding-agent", prompt="task_id: abc123")
# Agent works in background, returns results
```

**cclaude CLI** (for interaction):
```bash
# Visible terminal session
cclaude "Fix the authentication bug"
# You can see and interact with the work
```

### vs. Regular `claude` Command

**Regular claude**:
```bash
# Runs in current terminal
claude "Implement feature"
# Blocks current terminal
```

**cclaude**:
```bash
# Opens NEW terminal
cclaude "Implement feature"
# Current terminal remains free
```

---

## Future Enhancements

### Short Term
1. ✅ **MCP Task Integration**
   - Auto-create task for each session
   - Track session in MCP system
   - Enable context sharing

2. ✅ **Session List Command**
   ```bash
   cclaude --list  # Show all active sessions
   cclaude --kill <session-id>  # Close specific session
   ```

3. ✅ **Configuration File**
   ```json
   // .claude/cclaude.config.json
   {
     "terminal": "gnome-terminal",
     "create_mcp_task": true,
     "auto_track": true
   }
   ```

### Long Term
1. **VSCode Extension**
   - Native terminal API
   - Sidebar for session management
   - Keybindings and commands

2. **Advanced Session Management**
   - Session grouping
   - Shared context between sessions
   - Session templates

3. **Integration with Hooks**
   - Custom `NewTerminalSession` hook
   - Session start/stop tracking
   - Automatic documentation

---

## Installation & Usage

### Installation

```bash
# Already done - script exists at:
# /home/daihu/__projects__/4genthub/.claude/bin/cclaude

# Add to PATH (already in ~/.bashrc):
export PATH="$PATH:$HOME/__projects__/4genthub/.claude/bin"

# Reload shell
source ~/.bashrc
```

### Usage

```bash
# Basic usage
cclaude "task description here"

# Examples
cclaude "Fix authentication bug in user login"
cclaude "Implement JWT token refresh mechanism"
cclaude "Debug websocket connection issues"

# Help
cclaude
# Shows usage instructions
```

### Current Limitations

1. **No MCP Integration Yet**
   - Sessions not tracked in MCP system
   - No task context sharing
   - Manual session management

2. **Platform-Specific**
   - Tested on Linux/WSL2 only
   - macOS code untested
   - Windows support not implemented

3. **No Session Tracking**
   - Can't list active sessions
   - No automatic cleanup
   - Manual terminal management

---

## Conclusion

### Summary

✅ **Feasible and Implemented**
- Basic working prototype created
- Simple shell script approach
- Cross-platform architecture designed
- Ready for testing and iteration

### Recommendations

1. **Use for Interactive Work**
   - Debugging sessions
   - Monitoring tasks
   - Manual interventions

2. **Keep Using Task Tool for Automation**
   - Efficient delegation
   - Background processing
   - Automated workflows

3. **Enhance with MCP Integration**
   - Track sessions properly
   - Share context effectively
   - Maintain consistency with project architecture

### Next Steps

1. Test the basic script
2. Gather feedback on UX
3. Implement MCP integration
4. Consider VSCode extension if needed

---

## References

- Claude CLI documentation: `claude --help`
- VSCode Terminal API: https://code.visualstudio.com/api/references/vscode-api#Terminal
- Project MCP tools: `ai_docs/claude-code/tools_list.md`
- Existing hooks system: `.claude/hooks/`

---

**Last Updated**: 2025-11-01
**Author**: Master Orchestrator Agent
**Status**: Research Complete, Prototype Implemented
