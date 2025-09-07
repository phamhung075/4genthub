# Claude Code & DhafnckMCP Agent System Integration Guide

## Overview

This guide explains how to integrate your advanced DhafnckMCP agent system (60+ specialized agents) with Claude Code's native agent system. Rather than replacing either system, we create a bridge architecture that allows both systems to work together seamlessly.

## System Architecture

### Two Complementary Systems

**DhafnckMCP Agent System:**
- 60+ specialized workflow orchestration agents
- Advanced task management with 4-tier context hierarchy
- Server-side orchestration (localhost:8000)
- Complex agent configurations with detailed metadata
- Multi-agent coordination and project management

**Claude Code Agent System:**
- IDE-integrated coding assistants
- Simple YAML frontmatter configuration
- Separate context windows per agent
- Automatic task-based agent selection
- Direct MCP tool integration

### Bridge Architecture

The solution creates **bridge agents** in Claude Code that:
- Invoke your specialized DhafnckMCP agents
- Maintain task tracking and context management
- Preserve workflow integration
- Enable seamless handoffs between systems

## Installation & Setup

### 1. Verify DhafnckMCP System

Ensure your DhafnckMCP server is running:

```bash
# Check server health
curl http://localhost:8000/mcp/health

# Verify in Claude Code
mcp__dhafnck_mcp_http__manage_connection(action="health_check")
```

### 2. Create Bridge Agents

#### Option A: Use Pre-built Bridge Agents

Core bridge agents are already created in `~/.claude/agents/`:

- `uber-orchestrator.md` - Project orchestration and coordination
- `coding-specialist.md` - Advanced coding with task management
- `debugging-expert.md` - Expert debugging and troubleshooting  
- `testing-orchestrator.md` - Comprehensive testing workflows

#### Option B: Generate All Agents Automatically

Use the generator script to create bridge agents for all 60+ agents:

```bash
cd /home/daihungpham/agentic-project
python scripts/generate-claude-agents.py

# Review generated agents
ls generated-agents/

# Install to Claude Code
cp generated-agents/*.md ~/.claude/agents/
```

### 3. Restart Claude Code

After installing agents, restart Claude Code to load the new agent definitions.

## Usage Guide

### Automatic Agent Selection

Claude Code will automatically select appropriate bridge agents based on your requests:

- **"Help me orchestrate this complex project"** → `uber-orchestrator` agent
- **"Implement this feature with proper task tracking"** → `coding-specialist` agent  
- **"Debug this issue systematically"** → `debugging-expert` agent
- **"Set up comprehensive testing"** → `testing-orchestrator` agent

### Manual Agent Invocation

You can also explicitly request specific agents:

```
Use the uber-orchestrator agent to coordinate this multi-phase project.
```

### Bridge Agent Workflow

When a bridge agent is activated, it will:

1. **Connect to your DhafnckMCP agent**:
   ```
   mcp__dhafnck_mcp_http__call_agent(name_agent="@uber_orchestrator_agent")
   ```

2. **Check existing project context**:
   ```
   mcp__dhafnck_mcp_http__manage_context(
       action="resolve",
       level="branch", 
       context_id=branch_id,
       include_inherited=true
   )
   ```

3. **Create or update tasks** for tracking:
   ```
   mcp__dhafnck_mcp_http__manage_task(
       action="create",
       git_branch_id=branch_id,
       title="Work description"
   )
   ```

4. **Execute specialized work** through your advanced agents

5. **Update context** with findings:
   ```
   mcp__dhafnck_mcp_http__manage_context(
       action="update",
       level="branch",
       context_id=branch_id,
       data={
           "work_completed": "Details",
           "key_decisions": "Important choices",
           "next_steps": "Follow-up actions"
       }
   )
   ```

## Agent Mapping

### Core Bridge Agents

| Claude Code Agent | DhafnckMCP Agents | Use Cases |
|------------------|-------------------|-----------|
| `uber-orchestrator` | @uber_orchestrator_agent, @task_planning_agent | Complex projects, coordination |
| `coding-specialist` | @coding_agent, @system_architect_agent, @algorithmic_problem_solver_agent | Implementation work |
| `debugging-expert` | @debugger_agent, @root_cause_analysis_agent | Bug fixes, troubleshooting |
| `testing-orchestrator` | @test_orchestrator_agent, @functional_tester_agent | Quality assurance |

### Specialized Agent Categories

**Design & UI:**
- @ui_designer_agent
- @ui_designer_expert_shadcn_agent  
- @ux_researcher_agent
- @graphic_design_agent

**Security & Compliance:**
- @security_auditor_agent
- @security_penetration_tester_agent
- @compliance_scope_agent
- @compliance_testing_agent

**DevOps & Operations:**
- @devops_agent
- @adaptive_deployment_strategist_agent
- @health_monitor_agent

**Research & Analysis:**
- @deep_research_agent
- @market_research_agent
- @analytics_setup_agent

## Advanced Configuration

### Creating Custom Bridge Agents

You can create custom bridge agents for specific workflows:

```yaml
---
name: my-custom-workflow
description: Custom workflow for specific project needs
tools: mcp__dhafnck_mcp_http__call_agent, mcp__dhafnck_mcp_http__manage_task
model: sonnet
---

# Custom Workflow Agent

I bridge your specific workflow requirements with the DhafnckMCP system.

When activated, I will:
1. Connect to @specialized_agent_name
2. Follow your custom workflow steps
3. Update context and tasks appropriately
```

### Agent Selection Logic

Modify the generator script to customize agent selection:

```python
def categorize_agent(agent_name: str) -> str:
    """Add custom categorization logic"""
    # Your custom logic here
    pass
```

## Best Practices

### 1. Context Management

Always ensure context is properly managed:

```python
# Before starting work
context = mcp__dhafnck_mcp_http__manage_context(
    action="resolve",
    level="branch",
    context_id=branch_id,
    include_inherited=true
)

# After completing work  
mcp__dhafnck_mcp_http__manage_context(
    action="update",
    level="branch", 
    context_id=branch_id,
    data={"findings": "Important discoveries"}
)
```

### 2. Task Tracking

Create tasks before starting significant work:

```python
task = mcp__dhafnck_mcp_http__manage_task(
    action="create",
    git_branch_id=branch_id,
    title="Descriptive task title",
    description="Detailed requirements"
)
```

### 3. Agent Coordination

When multiple agents are needed:

```python
# Start with orchestrator
mcp__dhafnck_mcp_http__call_agent(name_agent="@uber_orchestrator_agent")

# Then delegate to specialists
mcp__dhafnck_mcp_http__call_agent(name_agent="@coding_agent")
```

## Troubleshooting

### Common Issues

**Bridge agents not appearing:**
- Restart Claude Code after installing agents
- Check agent files are in `~/.claude/agents/`
- Verify YAML frontmatter syntax

**DhafnckMCP connection issues:**
- Verify server is running: `curl http://localhost:8000/mcp/health`
- Check MCP configuration in `.mcp.json`
- Ensure no port conflicts

**Task management not working:**
- Verify branch_id and project context
- Check MCP server has task management enabled
- Confirm authentication if required

### Debug Commands

```bash
# Check Claude Code agent directory
ls -la ~/.claude/agents/

# Test DhafnckMCP connection
curl http://localhost:8000/mcp/tools

# Verify MCP configuration
cat .mcp.json
```

## Integration Benefits

By using this bridge architecture, you get:

1. **Best of Both Worlds**: Claude Code's IDE integration + your advanced agent system
2. **Preserved Workflows**: Your existing task management and context systems continue working
3. **Automatic Selection**: Claude Code automatically chooses appropriate agents
4. **Seamless Handoffs**: Smooth transitions between IDE work and orchestration
5. **Context Continuity**: Work context preserved across sessions and agents
6. **Scalable Architecture**: Easy to add new bridge agents as your system grows

This integration creates a powerful development environment that combines Claude Code's natural language interface with your sophisticated multi-agent orchestration system.