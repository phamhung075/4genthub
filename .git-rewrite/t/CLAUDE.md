# DhafnckMCP Usage Guide for AI Agents

## 🤖 Agent Switching - Use The Right Specialist

### ⚠️ CRITICAL: Agent Loading and Interface Compliance

Available agents: general-purpose, statusline-setup, output-style-setup,claude-code-troubleshooter and 60 more agents on MCP server (need fetch information using mcp__dhafnck_mcp_http__call_agent).


## **Actual Claude Code Style Agent Display:**

```bash
[Agent: {agent_name} - Working...]
[Agent: {agent_name} - Ready]
[Agent: {agent_name} - Initializing...]
```

- **Simple bracket notation**: `[Agent: name - status]`
- **Basic status words**: Working, Ready, Initializing, Error, etc.
- **Clean terminal output** without fancy graphics

## **Corrected Step-by-Step Process:**

**Step 1: Initialize MCP Agent**
- Call `mcp__dhafnck_mcp_http__call_agent` to get agent information
- **Display**: `[Agent: Initializing...]`

**Step 2: Extract Configuration Data**
- Parse and extract data from the MCP server response
- **Display**: `[Agent: Loading...]`

**Step 3: Launch Agent with Task Tool**
- Use the Task tool to launch complete agent specification
- **Display**: `[Agent: {agent_name} - Working...]`

**Step 4: Agent Operational**
- Agent equivalent to `.claude/agents` launches
- **Display**: `[Agent: {agent_name} - Ready]`


## 🚀 Quick Start - Your First Actions

```python
# 1. Switch to appropriate agent role
mcp__dhafnck_mcp_http__call_agent(name_agent="@uber_orchestrator_agent")

# 2. Check system health
mcp__dhafnck_mcp_http__manage_connection(action="health_check")

# 3. List available projects
mcp__dhafnck_mcp_http__manage_project(action="list")

# 4. Get or create a task to work on
mcp__dhafnck_mcp_http__manage_task(
    action="next",
    git_branch_id=branch_id,
    include_context=True
)
```

## 📊 Context Management - Share Information Between Sessions

### The Context Hierarchy
```
GLOBAL (per-user) → PROJECT → BRANCH → TASK
```
Each level inherits from above. The global context is user-scoped (each user has their own global context instance). Update context to share information between:
- Different AI sessions
- Different agents  
- Different time periods

### ⚠️ CRITICAL: Context Creation for Frontend Visibility
**Tasks DO NOT automatically create context**. You must explicitly create context for tasks to be viewable in the frontend "Actions context" feature.

```python
# After creating a task, ALWAYS create its context:
task = mcp__dhafnck_mcp_http__manage_task(
    action="create",
    git_branch_id=branch_id,
    title="My new task"
)

# REQUIRED: Create context for frontend visibility
mcp__dhafnck_mcp_http__manage_context(
    action="create",
    level="task",
    context_id=task["task"]["id"],
    git_branch_id=branch_id,
    data={
        "branch_id": branch_id,
        "task_data": {
            "title": task["task"]["title"],
            "status": task["task"]["status"],
            "description": task["task"]["description"]
        }
    }
)
```

### Always Update Context With Your Work
```python
# After making discoveries or decisions, UPDATE the context:
mcp__dhafnck_mcp_http__manage_context(
    action="update",
    level="branch",  # or "project" for broader sharing
    context_id=branch_id,
    data={
        "discoveries": ["Found the API uses port 3800", "Database is PostgreSQL"],
        "decisions": ["Using React hooks for state management"],
        "current_work": "Implementing user authentication",
        "blockers": ["Missing Supabase credentials"],
        "next_steps": ["Add JWT token validation", "Test login flow"]
    },
    propagate_changes=True
)
```

### Read Context From Previous Sessions
```python
# Get all inherited context to understand previous work:
context = mcp__dhafnck_mcp_http__manage_context(
    action="resolve",
    level="branch",
    context_id=branch_id,
    force_refresh=False
)
# Context will contain all updates from this branch, project, and global levels
```

**MANDATORY PROCEDURE:**
1. **Load Agent**: Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@agent_name")`
2. **Switch Interface**: Immediately adopt the loaded agent's interface using metadata 
3. **Follow Specifications**: Use ONLY the agent's yaml_content as source of truth
4. **Obey All Rules**: Follow capabilities, rules, tools, contexts from the response

### Agent Loading Protocol
```python
# STEP 1: Load agent from MCP server
agent_response = mcp__dhafnck_mcp_http__call_agent(name_agent="@coding_agent")

# STEP 2: Extract agent specifications from response
agent_config = agent_response["yaml_content"]["config"]
agent_metadata = agent_response["yaml_content"]["metadata"]
agent_contexts = agent_response["yaml_content"]["contexts"]
agent_rules = agent_response["yaml_content"]["rules"]
agent_capabilities = agent_response["capabilities"]

# STEP 3: Follow agent's interface specifications
# - Use only the tools listed in agent_capabilities["mcp_tools"]
# - Follow all rules in agent_rules
# - Operate within the contexts defined in agent_contexts
# - Respect the capabilities.permissions
```

### Source of Truth Hierarchy
1. **PRIMARY**: `agent_response["yaml_content"]` - Complete agent specification
2. **SECONDARY**: `agent_response["capabilities"]` - Available actions and tools
3. **METADATA**: `agent_response["agent_info"]` - Basic agent information
4. **NEVER**: Hardcoded agent lists or assumptions

### Quick Agent Selection
```python
# Based on work type, switch to appropriate agent:
if "debug" in user_request or "fix" in user_request:
    response = mcp__dhafnck_mcp_http__call_agent(name_agent="@debugger_agent")
elif "implement" in user_request or "code" in user_request:
    response = mcp__dhafnck_mcp_http__call_agent(name_agent="@coding_agent")
elif "test" in user_request:
    response = mcp__dhafnck_mcp_http__call_agent(name_agent="@test_orchestrator_agent")
elif "design" in user_request or "ui" in user_request:
    response = mcp__dhafnck_mcp_http__call_agent(name_agent="@ui_designer_agent")
elif "document" in user_request or "docs" in user_request:
    response = mcp__dhafnck_mcp_http__call_agent(name_agent="@documentation_agent")
else:
    response = mcp__dhafnck_mcp_http__call_agent(name_agent="@uber_orchestrator_agent")

# MANDATORY: Switch to loaded agent interface
current_agent = response["yaml_content"]
available_tools = response["capabilities"]["mcp_tools"]["tools"]
agent_rules = response["yaml_content"]["rules"]
```

### Agent Response Structure
```python
{
  "success": true,
  "agent_info": {
    "name": "agent_name",
    "capabilities_summary": {...}
  },
  "yaml_content": {
    "config": {
      "agent_info": {...},
      "capabilities": {...}
    },
    "contexts": [...],      # Agent operational contexts
    "rules": [...],         # Agent behavioral rules  
    "output_formats": [...], # Expected output formats
    "metadata": {           # ✅ NOW AVAILABLE - Agent metadata
      "name": "agent-name",
      "description": "Complete agent description with examples",
      "model": "sonnet",
      "color": "stone",
      "migration": {...},   # Migration history and version
      "validation": {...}   # Compatibility and structure validation
    }
  },
  "capabilities": {
    "available_actions": [...],
    "mcp_tools": {...},
    "permissions": {...}
  }
}
```

### Available Specialist Agents
**⚠️ DYNAMIC LIST**: Use `mcp__dhafnck_mcp_http__call_agent` to load current agents. This list may be outdated:
- `@coding_agent` - Writing implementation code
- `@debugger_agent` - Fixing bugs and errors
- `@test_orchestrator_agent` - Creating and running tests
- `@ui_designer_agent` - Frontend and UI work
- `@documentation_agent` - Writing docs and guides
- `@task_planning_agent` - Breaking down complex tasks
- `@security_auditor_agent` - Security reviews
- `@uber_orchestrator_agent` - General coordination

## 📝 Task Management - Track Your Work

### Create Task Before Starting Work
```python
task = mcp__dhafnck_mcp_http__manage_task(
    action="create",
    git_branch_id=branch_id,
    title="Implement user authentication",
    description="Add JWT-based auth with login/logout",
    priority="high"
)
```

### Update Task Progress
```python
mcp__dhafnck_mcp_http__manage_task(
    action="update",
    task_id=task_id,
    status="in_progress",
    details="Completed login UI, working on JWT validation"
)
```

### Complete Task With Summary
```python
mcp__dhafnck_mcp_http__manage_task(
    action="complete",
    task_id=task_id,
    completion_summary="Implemented full JWT authentication with refresh tokens",
    testing_notes="Added unit tests for auth service, tested login/logout flow"
)
```

## 🔄 Practical Workflows

### Starting New Work
```python
# 1. Load and switch to orchestrator agent
orchestrator = mcp__dhafnck_mcp_http__call_agent(name_agent="@uber_orchestrator_agent")
# Follow loaded agent specifications
orchestrator_rules = orchestrator["yaml_content"]["rules"]
orchestrator_capabilities = orchestrator["capabilities"]

# 2. Get branch context to understand current state
context = mcp__dhafnck_mcp_http__manage_context(
    action="resolve",
    level="branch",
    context_id=branch_id
)

# 3. Create or get task
task = mcp__dhafnck_mcp_http__manage_task(
    action="next",  # or "create" for new task
    git_branch_id=branch_id
)

# 4. Load and switch to appropriate specialist
coding_agent = mcp__dhafnck_mcp_http__call_agent(name_agent="@coding_agent")
# Extract agent specifications as source of truth
agent_config = coding_agent["yaml_content"]["config"]
agent_metadata = coding_agent["yaml_content"]["metadata"]  # ✅ NOW AVAILABLE
agent_contexts = coding_agent["yaml_content"]["contexts"]
agent_rules = coding_agent["yaml_content"]["rules"]
available_tools = coding_agent["capabilities"]["mcp_tools"]["tools"]
permissions = coding_agent["capabilities"]["permissions"]

# Use metadata for agent information
print(f"Loaded agent: {agent_metadata['name']} (Model: {agent_metadata['model']})")

# 5. Update status (following agent capabilities)
if permissions.get("mcp_tools", False):
    mcp__dhafnck_mcp_http__manage_task(
        action="update",
        task_id=task.task_id,
        status="in_progress"
    )

# 6. Do the work following agent rules and contexts...

# 7. Update context with findings
mcp__dhafnck_mcp_http__manage_context(
    action="update",
    level="branch",
    context_id=branch_id,
    data={
        "completed_work": "Added user authentication",
        "technical_decisions": ["Using JWT with 24h expiry"],
        "files_modified": ["auth.service.ts", "login.component.tsx"],
        "agent_used": coding_agent["agent_info"]["name"],
        "agent_capabilities": coding_agent["capabilities_summary"]
    }
)

# 8. Complete task following agent output formats
mcp__dhafnck_mcp_http__manage_task(
    action="complete",
    task_id=task.task_id,
    completion_summary="Full authentication implementation complete",
    testing_notes="Following agent testing guidelines from yaml_content"
)
```

### Debugging Existing Code
```python
# 1. Load and switch to debugger agent
debugger_agent = mcp__dhafnck_mcp_http__call_agent(name_agent="@debugger_agent")
# Extract and follow agent specifications
debug_rules = debugger_agent["yaml_content"]["rules"]
debug_contexts = debugger_agent["yaml_content"]["contexts"]
debug_capabilities = debugger_agent["capabilities"]

# 2. Get context to understand the issue (using agent capabilities)
if debug_capabilities["permissions"]["mcp_tools"]:
    context = mcp__dhafnck_mcp_http__manage_context(
        action="resolve",
        level="branch",
        context_id=branch_id
    )

# 3. Investigate and fix following agent rules and contexts...
# Use only tools available in debug_capabilities["mcp_tools"]["tools"]

# 4. Update context with solution (following agent output formats)
mcp__dhafnck_mcp_http__manage_context(
    action="update",
    level="branch",
    context_id=branch_id,
    data={
        "bug_fixed": "Login redirect loop",
        "root_cause": "Missing token refresh logic", 
        "solution": "Added token refresh interceptor",
        "debugging_agent": debugger_agent["agent_info"]["name"],
        "debug_methodology": "Following agent contexts and rules",
        "tools_used": debug_capabilities["mcp_tools"]["tools"]
    }
)
```

## 🔍 Finding Information From Previous Sessions

### Check Project Context
```python
# See what's been done in this project
project_context = mcp__dhafnck_mcp_http__manage_context(
    action="get",
    level="project",
    context_id=project_id,
    include_inherited=True
)
```

### Check Branch Context
```python
# See current branch work and decisions
branch_context = mcp__dhafnck_mcp_http__manage_context(
    action="get",
    level="branch", 
    context_id=branch_id,
    include_inherited=True
)
```

### ⚠️ CRITICAL: Project Context Database Structure
**PROJECT contexts have 4 predefined database columns:**
- `team_preferences` - Team settings and preferences
- `technology_stack` - Technology choices (NOT `technical_stack`!)
- `project_workflow` - Workflow and process definitions
- `local_standards` - Project standards and conventions

**Any other fields are stored in `local_standards._custom`:**
```python
# ✅ CORRECT - Data goes to proper columns
mcp__dhafnck_mcp_http__manage_context(
    action="update",
    level="project",
    context_id=project_id,
    data={
        "team_preferences": {"review_required": True},
        "technology_stack": {"frontend": ["React"], "backend": ["Python"]},
        "project_workflow": {"phases": ["design", "develop", "test"]},
        "local_standards": {"naming": "camelCase"}
    }
)

# ⚠️ CUSTOM - Goes to local_standards._custom
mcp__dhafnck_mcp_http__manage_context(
    action="update",
    level="project",
    context_id=project_id,
    data={
        "project_info": {...},  # -> local_standards._custom.project_info
        "core_features": {...},  # -> local_standards._custom.core_features
        "technical_stack": {...}  # -> local_standards._custom.technical_stack (wrong key!)
    }
)
```

### Search Tasks
```python
# Find related work
tasks = mcp__dhafnck_mcp_http__manage_task(
    action="search",
    query="authentication login",
    git_branch_id=branch_id
)
```

## 🔍 Using Agent Metadata

### Access Agent Information
```python
# Load agent and extract metadata
agent_response = mcp__dhafnck_mcp_http__call_agent(name_agent="@coding_agent")
metadata = agent_response["yaml_content"]["metadata"]

# Agent identification
print(f"Agent Name: {metadata['name']}")
print(f"Description: {metadata['description']}")
print(f"Preferred Model: {metadata['model']}")
print(f"UI Color: {metadata['color']}")

# Migration and validation info
migration_info = metadata.get('migration', {})
validation_info = metadata.get('validation', {})
print(f"Agent Version: {migration_info.get('version', 'unknown')}")
print(f"Backward Compatible: {validation_info.get('backward_compatible', 'unknown')}")
```

### Practical Metadata Usage
```python
# Choose model preference based on agent metadata
def select_model_for_agent(agent_response):
    metadata = agent_response["yaml_content"]["metadata"]
    preferred_model = metadata.get('model', 'default')
    
    # Agent specifies preferred AI model
    if preferred_model == 'sonnet':
        return 'claude-3-sonnet'
    elif preferred_model == 'haiku':
        return 'claude-3-haiku'
    else:
        return 'claude-3-sonnet'  # fallback

# Validate agent compatibility
def check_agent_compatibility(agent_response):
    metadata = agent_response["yaml_content"]["metadata"]
    validation = metadata.get('validation', {})
    
    return {
        'backward_compatible': validation.get('backward_compatible', False),
        'capabilities_mapped': validation.get('capabilities_mapped', False),
        'structure_valid': validation.get('structure_valid', False)
    }

# Display agent in UI with proper styling
def get_agent_ui_config(agent_response):
    metadata = agent_response["yaml_content"]["metadata"]
    return {
        'display_name': metadata.get('name', 'Unknown Agent'),
        'color_theme': metadata.get('color', 'gray'),
        'description': metadata.get('description', 'No description available')
    }
```

## 💡 Key Principles

### 1. Always Update Context
After any significant work, discovery, or decision, update the branch or project context so future sessions can access this information.

### 2. Use The Right Agent
Switch to the appropriate specialist agent for the work type. Don't try to do everything with one agent.

### 3. Track Work With Tasks
Create tasks before starting work. Update progress. Complete with detailed summaries.

### 4. Read Context First
Before starting work, always resolve context to understand what's been done before.

### 5. Share Reusable Patterns
If you discover something reusable, delegate it to project or global level:
```python
mcp__dhafnck_mcp_http__manage_context(
    action="delegate",
    level="branch",
    context_id=branch_id,
    delegate_to="project",
    delegate_data={
        "pattern": "JWT refresh token implementation",
        "code": refresh_token_code,
        "usage": "How to implement token refresh"
    },
    delegation_reason="Reusable authentication pattern"
)
```

## 🚨 Important Rules

1. **🤖 AGENT INTERFACE COMPLIANCE** - MANDATORY: Call `mcp__dhafnck_mcp_http__call_agent` before any work and follow the loaded agent's specifications as source of truth
2. **📋 No work without task** - Create or get a task before starting work
3. **📝 Update CHANGELOG.md** - Document all project changes
4. **🔄 Update context regularly** - Share information for other sessions
5. **✅ Complete tasks properly** - Include detailed summaries and testing notes
6. **👁️ Create context for visibility** - Tasks need explicit context creation to be viewable in frontend
7. **⚙️ Follow agent capabilities** - Use only the tools, rules, and permissions defined in the loaded agent's yaml_content
8. **🔒 Respect agent permissions** - Check capabilities.permissions before attempting file operations, system commands, etc.

## 🎯 Agent Interface Compliance Rules

### MANDATORY: Source of Truth Protocol
- **PRIMARY SOURCE**: `agent_response["yaml_content"]` contains the complete agent specification
- **NEVER ASSUME**: Agent capabilities, tools, or rules - always load and check
- **DYNAMIC LOADING**: Agent specifications can change - always load fresh
- **INTERFACE SWITCHING**: When calling an agent, immediately adopt its interface

### Agent Metadata Loading (RESOLVED ✅)
**✅ FIXED**: Agent metadata.yaml files are now successfully loaded in responses
- **Implementation**: Complete metadata loading implemented in AgentFactory
- **Available**: `yaml_content.metadata` contains full agent metadata including:
  - `name`: Agent canonical name
  - `description`: Complete agent description with examples
  - `model`: Preferred AI model (e.g., "sonnet")
  - `color`: UI color scheme preference
  - `migration`: Migration history and version info
  - `validation`: Backward compatibility and structure validation status
- **Usage**: Access via `agent_response["yaml_content"]["metadata"]`
- **Status**: Working across all agent calls as of 2025-08-20

### Compliance Checklist
Before starting any work:
- [ ] Called `mcp__dhafnck_mcp_http__call_agent` to load agent
- [ ] Extracted `yaml_content` and `capabilities` from response
- [ ] Verified agent metadata in `yaml_content.metadata` ✅
- [ ] Verified available tools in `capabilities.mcp_tools`
- [ ] Checked permissions in `capabilities.permissions`
- [ ] Read agent rules in `yaml_content.rules`
- [ ] Understood agent contexts in `yaml_content.contexts`
- [ ] Confirmed agent compatibility via `metadata.validation`

## 📋 Common Tool Patterns

### Project Management
```python
# Create project
mcp__dhafnck_mcp_http__manage_project(action="create", name="new-feature")

# List projects
mcp__dhafnck_mcp_http__manage_project(action="list")

# Get project health
mcp__dhafnck_mcp_http__manage_project(action="project_health_check", project_id=id)
```

### Branch Management
```python
# Create branch
mcp__dhafnck_mcp_http__manage_git_branch(
    action="create",
    project_id=project_id,
    git_branch_name="feature/auth"
)

# Assign agent to branch
mcp__dhafnck_mcp_http__manage_git_branch(
    action="assign_agent",
    project_id=project_id,
    git_branch_id=branch_id,
    agent_id="@coding_agent"
)
```

### Subtask Management
```python
# Create subtask
mcp__dhafnck_mcp_http__manage_subtask(
    action="create",
    task_id=parent_task_id,
    title="Create login component"
)

# Update subtask progress
mcp__dhafnck_mcp_http__manage_subtask(
    action="update",
    task_id=parent_task_id,
    subtask_id=subtask_id,
    progress_percentage=75,
    progress_notes="Login UI complete"
)
```

## 🔧 Troubleshooting Context Issues

### Context Not Showing in Frontend?

If you see "No context available for this task" in the frontend:

1. **Check if context exists**:
```python
mcp__dhafnck_mcp_http__manage_context(
    action="get",
    level="task",
    context_id=task_id,
    include_inherited=True
)
```

2. **If context doesn't exist, create it**:
```python
# First ensure branch context exists
mcp__dhafnck_mcp_http__manage_context(
    action="create",
    level="branch",
    context_id=branch_id,
    project_id=project_id,
    data={"project_id": project_id, "git_branch_id": branch_id}
)

# Then create task context
mcp__dhafnck_mcp_http__manage_context(
    action="create",
    level="task",
    context_id=task_id,
    git_branch_id=branch_id,
    data={
        "branch_id": branch_id,
        "task_data": {"title": "Task title", "status": "in_progress"}
    }
)
```

3. **Update task to link context**:
```python
mcp__dhafnck_mcp_http__manage_task(
    action="update",
    task_id=task_id,
    context_id=task_id  # Link task to its context
)
```

### Known Issue: Auto-Context Creation
Currently, contexts are NOT automatically created when:
- Tasks are created
- Tasks are completed
- Tasks are updated

**You MUST manually create contexts for frontend visibility.**

## 🔗 System Information

- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:3800
- **Database**: `/data/dhafnck_mcp.db` (Docker)
- **Docs**: `dhafnck_mcp_main/docs/`
- **Tests**: `dhafnck_mcp_main/src/tests/`

---

**Remember**: The key to multi-session collaboration is updating context. Every AI agent and session can access shared context, making your work persistent and discoverable.
    - Do not EXPOSED PASSWORD: All password need store in .env file on root (single file)