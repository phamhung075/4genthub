# Claude Code Agent Delegation Guide

## Overview

The DhafnckMCP `call_agent` tool now provides Claude Code-compatible agent definitions, enabling seamless agent delegation between Claude Code's Task tool and DhafnckMCP's specialized agents.

## How It Works

### 1. Agent Conversion Process

When `call_agent` is invoked, it:

1. **Loads the agent** from `dhafnck_mcp_main/agent-library/agents/{agent_name}/`
2. **Extracts configuration** from YAML files (config.yaml, capabilities.yaml, contexts/)
3. **Converts to Claude Code format** with proper frontmatter and system prompt
4. **Returns** a `claude_agent_definition` field compatible with `.claude/agents/*.md`

### 2. Agent Structure Mapping

| DhafnckMCP Structure | Claude Code Format |
|---------------------|-------------------|
| `config.yaml` → `agent_info.description` | `description:` frontmatter field |
| `config.yaml` → `agent_info.slug` | `name:` frontmatter field |
| `capabilities.yaml` → `groups` | `tools:` frontmatter field |
| `contexts/instructions.yaml` → `custom_instructions` | System prompt body |

### 3. Available Tools Mapping

| Capability Group | Claude Code Tools |
|-----------------|-------------------|
| `read` | `Read, Grep, Glob` |
| `edit` | `Edit, Write, MultiEdit` |
| `command` | `Bash` |
| `mcp` | `*` (All MCP tools) |

## Usage Examples

### Basic Agent Invocation

```python
# Call the MCP tool to get agent definition
result = mcp__dhafnck_mcp_http__call_agent(name_agent="@coding_agent")

if result['success']:
    # The claude_agent_definition can be used by Claude Code's Task tool
    claude_definition = result['claude_agent_definition']
    
    # This creates an equivalent to .claude/agents/coding-agent.md
    print(claude_definition)
```

### Expected Output

```markdown
---
name: coding-agent
description: This autonomous agent transforms detailed specifications and algorithmic designs into high-quality, production-ready code. It specializes in implementing features across multiple programming languages and frameworks, complete with comprehensive testing, documentation, and adherence to best practices.
tools: Read, Grep, Glob, Edit, Write, MultiEdit, Bash, *
---

**Core Purpose**: Transform specifications and designs into production-ready, well-tested, and documented code.

**Key Capabilities**:
- Multi-language code implementation (JavaScript/TypeScript, Python, Java, C#, Go, Rust, PHP, Ruby)
- Frontend development (React, Vue, Angular, Svelte, Next.js, Nuxt.js, SolidJS)
- Backend development (Node.js, Express, FastAPI, Spring, .NET, Flask, Django, Gin, Koa)
...
```

### Claude Code Integration Pattern

Now Claude Code can delegate to DhafnckMCP agents using this pattern:

```python
# 1. Get the agent definition from DhafnckMCP
agent_result = mcp__dhafnck_mcp_http__call_agent(name_agent="@coding_agent")

# 2. If successful, Claude Code can now use the Task tool with the agent specification
if agent_result['success']:
    # The Task tool can now use this agent definition
    Task(
        subagent_type="coding-agent",  # from claude_agent_definition
        description="Implement user authentication",
        prompt="Create a JWT-based authentication system with login, logout, and session management"
    )
```

## Supported Agents

All 42+ agents from `dhafnck_mcp_main/agent-library/agents/` are supported:

### Development & Coding
- `coding_agent` - Implementation and feature development
- `debugger_agent` - Bug fixing and troubleshooting  
- `code_reviewer_agent` - Code quality and review
- `prototyping_agent` - Rapid prototyping and POCs

### Testing & QA
- `test_orchestrator_agent` - Comprehensive test management
- `uat_coordinator_agent` - User acceptance testing
- `performance_load_tester_agent` - Performance and load testing

### Architecture & Design
- `system_architect_agent` - System design and architecture
- `design_system_agent` - Design system and UI patterns
- `ui_designer_expert_shadcn_agent` - Shadcn/UI components
- `core_concept_agent` - Core concepts and fundamentals

### Security & Compliance
- `security_auditor_agent` - Security audits and reviews
- `compliance_scope_agent` - Regulatory compliance
- `ethical_review_agent` - Ethical considerations

And many more...

## Integration Benefits

### For Claude Code Users

1. **Access to 42+ Specialized Agents** - Leverage DhafnckMCP's extensive agent library
2. **Production-Ready Agents** - All agents include comprehensive system prompts and capabilities
3. **Consistent Interface** - Standard `.claude/agents/*.md` format for familiarity
4. **Tool Access Control** - Agents inherit appropriate tool permissions based on capabilities

### For DhafnckMCP Users

1. **Claude Code Compatibility** - Agents work seamlessly with Claude Code's Task tool
2. **Delegation Workflow** - Smooth handoff between main Claude and specialized agents
3. **Context Preservation** - Agent definitions maintain full context from agent-library
4. **No Duplication** - Single source of truth in agent-library, multiple consumption formats

## Advanced Usage

### Chaining Multiple Agents

```python
# 1. Plan the work
task_plan = mcp__dhafnck_mcp_http__call_agent(name_agent="@task_planning_agent")

# 2. Implement the features  
coding_work = mcp__dhafnck_mcp_http__call_agent(name_agent="@coding_agent")

# 3. Review the code
code_review = mcp__dhafnck_mcp_http__call_agent(name_agent="@code_reviewer_agent")

# 4. Test everything
testing = mcp__dhafnck_mcp_http__call_agent(name_agent="@test_orchestrator_agent")
```

### Dynamic Agent Selection

The `call_agent` tool can be used to dynamically select the best agent for a task:

```python
def get_best_agent_for_task(task_type):
    agent_mapping = {
        'security': 'security_auditor_agent',
        'testing': 'test_orchestrator_agent', 
        'ui': 'ui_designer_expert_shadcn_agent',
        'api': 'coding_agent',
        'architecture': 'system_architect_agent'
    }
    
    agent_name = agent_mapping.get(task_type, 'coding_agent')
    return mcp__dhafnck_mcp_http__call_agent(name_agent=f"@{agent_name}")
```

## Technical Implementation

### Call Agent Response Structure

```python
{
    "success": True,
    "agent_info": {
        "name": "coding_agent",
        "role": "...",
        "context": "...",
        "capabilities_summary": {...}
    },
    "claude_agent_definition": "---\nname: coding-agent\n...",  # ← Claude Code format
    "yaml_content": {
        "config": {...},
        "contexts": [...],
        "rules": [...],
        ...
    },
    "capabilities": {
        "available_actions": [...],
        "mcp_tools": [...],
        "permissions": {...}
    },
    "source": "agent-library"
}
```

The `claude_agent_definition` field contains a complete `.claude/agents/*.md` compatible definition that can be consumed directly by Claude Code's agent system.

## Best Practices

1. **Agent Name Normalization** - Use the `@agent_name` format when calling agents
2. **Error Handling** - Always check the `success` field before using `claude_agent_definition`
3. **Tool Permissions** - Review the `capabilities.permissions` to understand what each agent can do
4. **Context Awareness** - Agents maintain their full context from the agent-library structure
5. **Version Compatibility** - Agent definitions are backward-compatible with existing Claude Code workflows

## Troubleshooting

### Common Issues

**Agent Not Found**
```python
{
    "success": False,
    "error": "Agent 'unknown_agent' not found in agent-library",
    "available_agents": ["coding_agent", "debugger_agent", ...]
}
```

**Solution**: Check the `available_agents` list for correct agent names.

**Missing Agent Library**
```python
{
    "success": False,
    "error": "Agent library not available. Please ensure agent-library directory exists."
}
```

**Solution**: Ensure `dhafnck_mcp_main/agent-library/` exists and contains agent definitions.

This integration provides a powerful bridge between Claude Code's delegation capabilities and DhafnckMCP's specialized agent ecosystem, enabling more sophisticated and specialized AI workflows.