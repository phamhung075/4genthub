# Session Type Detection - Main vs Sub-Agent Sessions

**Issue**: The `CLAUDE.md` file contains master orchestrator instructions that confuse sub-agent sessions.

**Solution**: Automatic session type detection that provides different instructions based on session context.

## How It Works

The session start hook now detects whether Claude is running as:
1. **Main Session** (master orchestrator) 
2. **Sub-Agent Session** (specialized agent)

### Detection Methods

The hook checks multiple indicators in order:

#### 1. Environment Variables (Explicit)
```bash
# Force sub-agent session
export CLAUDE_SESSION_TYPE=subagent

# Force main session  
export CLAUDE_SESSION_TYPE=main

# Specify agent role
export CLAUDE_AGENT_ROLE=debugger-agent
```

#### 2. Configuration File
Create `.claude.env` with:
```bash
CLAUDE_SESSION_TYPE=subagent
```

#### 3. Directory Context
- Main session: `/path/to/agentic-project` (project root)
- Sub-agent session: `/path/with/agent/coding/work` (contains agent keywords)

#### 4. Automatic Heuristics
Detects sub-agent indicators in working directory:
- `agent`, `subagent`, `sub-agent`
- `coding`, `debug`, `test`, `security`

## Session Instructions

### 🎯 Main Session (Master Orchestrator)
```
🚀 INITIALIZATION REQUIRED: You MUST immediately call 
mcp__dhafnck_mcp_http__call_agent('master-orchestrator-agent') 
to load your orchestrator capabilities.

🎯 You are the MASTER ORCHESTRATOR - coordinate and delegate 
work to specialized agents.
```

### 🤖 Sub-Agent Session
```
🤖 SUB-AGENT SESSION DETECTED

IMPORTANT: You are a specialized agent, NOT the master orchestrator.
- Focus on your specialized work
- Do NOT call master-orchestrator-agent
- Do NOT delegate to other agents
- Complete the task assigned to you

📖 See: ai_docs/core-architecture/sub-agent-instructions.md
```

## Usage Examples

### Method 1: Environment Variable
```bash
# Start a debugging session
export CLAUDE_SESSION_TYPE=subagent
export CLAUDE_AGENT_ROLE=debugger-agent
claude-code

# Start main orchestrator session  
export CLAUDE_SESSION_TYPE=main
claude-code
```

### Method 2: Configuration File
```bash
# Create .claude.env in project directory
echo "CLAUDE_SESSION_TYPE=subagent" > .claude.env
echo "CLAUDE_AGENT_ROLE=coding-agent" >> .claude.env

claude-code
```

### Method 3: Working Directory
```bash
# Create sub-agent working directory
mkdir -p workspace/coding-agent-work
cd workspace/coding-agent-work
claude-code  # Automatically detected as sub-agent session
```

## Troubleshooting

### Issue: Wrong Session Type Detected
**Solution**: Use explicit environment variable
```bash
export CLAUDE_SESSION_TYPE=main  # or subagent
```

### Issue: Sub-Agent Still Gets Master Orchestrator Instructions
**Solution**: Check detection logic works
```bash
# Test detection
python3 -c "
import sys
sys.path.append('.claude/hooks')
from session_start import detect_session_type
print('Detected:', detect_session_type())
"
```

### Issue: Need to Override Detection
**Solution**: Create `.claude.env` file
```bash
echo "CLAUDE_SESSION_TYPE=subagent" > .claude.env
```

## Benefits

✅ **Eliminates Confusion**: Sub-agents get appropriate instructions  
✅ **Automatic Detection**: Works without manual configuration  
✅ **Override Capability**: Can force specific session types  
✅ **Clear Instructions**: Different workflows for different roles  
✅ **Maintains Compatibility**: Main sessions work as before  

## Implementation Details

### Modified Files
1. **`.claude/hooks/session_start.py`**
   - Added `detect_session_type()` function
   - Modified `load_development_context()` to use detection
   - Added environment variable and file checks

2. **`ai_docs/core-architecture/sub-agent-instructions.md`**
   - Complete sub-agent workflow guide
   - Clear do's and don'ts for specialized agents

### Detection Priority
1. `CLAUDE_SESSION_TYPE` environment variable
2. `CLAUDE_AGENT_ROLE` environment variable  
3. `.claude.env` configuration file
4. Working directory analysis
5. Default to main session (safe fallback)

## Future Enhancements

### Possible Improvements
- Auto-detect based on Task tool delegation context
- Integration with agent loading system
- Session type persistence across restarts
- Agent-specific configuration files

### Integration Points
- Could integrate with MCP task system
- Could use session ID patterns for detection
- Could analyze recent prompts/commands for context

The current implementation provides a solid foundation for eliminating the CLAUDE.md confusion while maintaining flexibility for both automatic and manual session type control.