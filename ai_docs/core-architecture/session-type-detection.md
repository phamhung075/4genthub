# Agent Context Management - Runtime Agent Switching

**Issue**: The `CLAUDE.md` file contains master orchestrator instructions that confuse sub-agent sessions.

**Solution**: Automatic runtime agent switching when agents are called, providing appropriate context without manual configuration.

## How It Works

When Claude calls an agent using `mcp__4genthub_http__call_agent`, the system automatically:
1. **Detects Agent Calls** - Post-tool hook monitors for agent invocations
2. **Switches Context** - Provides specialized agent instructions 
3. **Runtime Switching** - Works within the same session without env vars

### Automatic Agent Context Switching

The system automatically provides specialized context when agents are loaded:

## Agent Context Instructions

### 🎯 Master Orchestrator (Default)
Standard Claude behavior with orchestrator capabilities loaded via:
```
mcp__4genthub_http__call_agent('master-orchestrator-agent')
```

### 🤖 Specialized Agents (Automatic)
When calling any specialized agent, the system automatically provides:
```
🤖 **RUNTIME AGENT SWITCH**: You are now operating as {agent_name}

**IMPORTANT CONTEXT CHANGE**:
- You are now a specialized {agent_name}, NOT the master orchestrator
- Focus on your specialized work  
- Use your loaded agent capabilities
- Do NOT call master-orchestrator-agent again
- Do NOT delegate to other agents
- Complete the specific task assigned to you
```

## Usage Examples

### Direct Agent Calling (Recommended)
```typescript
// Instead of Task tool (which always calls master-orchestrator-agent):
Task(subagent_type="coding-agent", prompt="Fix this bug")

// Use direct agent calling:
mcp__4genthub_http__call_agent("coding-agent")
// System automatically provides specialized context
```

### Agent Delegation Pattern
```typescript
// 1. Create MCP task with full context
const taskResult = await mcp__4genthub_http__manage_task({
  action: "create",
  git_branch_id: "branch-uuid", 
  title: "Fix authentication bug",
  description: "Full context and details here...",
  assignees: "coding-agent"
});

// 2. Delegate with task ID only (saves tokens)
mcp__4genthub_http__call_agent("coding-agent")
// Agent will be told: "task_id: {uuid}" and load full context from MCP
```

## Benefits

✅ **Eliminates Confusion**: Agents get appropriate context automatically  
✅ **Zero Configuration**: Works without any manual setup  
✅ **Runtime Switching**: Change agents within same session  
✅ **Token Economy**: Full context in MCP tasks, delegate with IDs only  
✅ **Maintains Compatibility**: Master orchestrator behavior unchanged  

## Implementation Details

### How the System Works

1. **Post-Tool Hook Detection** (`.claude/hooks/post_tool_use.py`):
   - Monitors for `mcp__4genthub_http__call_agent` calls
   - Automatically invokes agent context switching
   - Provides specialized instructions via system reminder

2. **Agent Context Manager** (`.claude/hooks/utils/agent_context_manager.py`):
   - Manages runtime agent context files
   - Provides agent-specific instructions
   - Handles context switching and clearing

3. **Agent Helper Functions** (`.claude/hooks/utils/agent_helpers.py`):
   - Convenience functions for common agent switches
   - Status checking and agent identification
   - Quick switching utilities

### Agent Context Flow
```
1. Claude calls mcp__4genthub_http__call_agent("coding-agent")
2. Post-tool hook detects the call
3. Agent context manager creates specialized context
4. System provides runtime instructions to Claude
5. Claude operates as specialized coding agent
6. Agent completes task with specialized focus
```

## Token Economy Pattern

The system implements efficient token usage:

1. **Full Context in MCP Task**: Create task with complete context
2. **ID-Only Delegation**: Pass only task UUID to agent
3. **Agent Context Loading**: Agent loads full context from MCP
4. **Specialized Focus**: Agent works with appropriate instructions

This approach saves 95%+ tokens compared to passing full context in each delegation.

## Technical Architecture

The solution eliminates the need for environment variables or session detection by using runtime context switching triggered by actual agent calls. This ensures agents receive appropriate instructions exactly when needed, without any manual configuration or startup confusion.