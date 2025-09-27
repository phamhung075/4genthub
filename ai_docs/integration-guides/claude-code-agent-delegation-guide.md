# Claude Code Agent Delegation Guide

## Overview

The agenthub `call_agent` tool now provides Claude Code-compatible agent definitions, enabling seamless agent delegation between Claude Code's Task tool and agenthub's specialized agents.

## How It Works

### 1. Agent Conversion Process

When `call_agent` is invoked, it:

1. **Loads the agent** from `agenthub_main/agent-library/agents/{agent_name}/`
2. **Extracts configuration** from YAML files (config.yaml, capabilities.yaml, contexts/)
3. **Converts to Claude Code format** with proper frontmatter and system prompt
4. **Returns** a `claude_agent_definition` field compatible with `.claude/agents/*.md`

### 2. Agent Structure Mapping

| agenthub Structure | Claude Code Format |
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
result = mcp__agenthub_http__call_agent(name_agent="coding-agent")

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

Now Claude Code can delegate to agenthub agents using this pattern:

```python
# 1. Get the agent definition from agenthub
agent_result = mcp__agenthub_http__call_agent(name_agent="coding-agent")

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

All 32 agents from `agenthub_main/agent-library/agents/` are supported:

### Development & Coding
- `coding-agent` - Implementation and feature development
- `debugger-agent` - Bug fixing and troubleshooting  
- `code-reviewer-agent` - Code quality and review
- `prototyping-agent` - Rapid prototyping and POCs

### Testing & QA
- `test-orchestrator-agent` - Comprehensive test management
- `uat-coordinator-agent` - User acceptance testing
- `performance-load-tester-agent` - Performance and load testing

### Architecture & Design
- `system-architect-agent` - System design and architecture
- `design-system-agent` - Design system and UI patterns
- `ui_designer_expert_shadcn_agent` - Shadcn/UI components
- `core-concept-agent` - Core concepts and fundamentals

### Security & Compliance
- `security-auditor-agent` - Security audits and reviews
- `compliance-scope-agent` - Regulatory compliance
- `ethical-review-agent` - Ethical considerations

And many more...

## Integration Benefits

### For Claude Code Users

1. **Access to 32 Specialized Agents** - Leverage agenthub's extensive agent library
2. **Production-Ready Agents** - All agents include comprehensive system prompts and capabilities
3. **Consistent Interface** - Standard `.claude/agents/*.md` format for familiarity
4. **Tool Access Control** - Agents inherit appropriate tool permissions based on capabilities

### For agenthub Users

1. **Claude Code Compatibility** - Agents work seamlessly with Claude Code's Task tool
2. **Delegation Workflow** - Smooth handoff between main Claude and specialized agents
3. **Context Preservation** - Agent definitions maintain full context from agent-library
4. **No Duplication** - Single source of truth in agent-library, multiple consumption formats

## Advanced Usage

### Delegating to Multiple Agents via Task Tool

```python
# IMPORTANT: You must delegate via Task Tool, not call directly
# Each agent will internally call call_agent to load their core capabilities

# 1. Delegate planning work via Task Tool
Task(
    subagent_type="task-planning-agent",
    description="Plan the implementation",
    prompt="Create a detailed plan for implementing the user authentication system"
)

# 2. Delegate implementation via Task Tool
Task(
    subagent_type="coding-agent",
    description="Implement the features",
    prompt="Implement the authentication system based on the plan"
)

# 3. Delegate code review via Task Tool
Task(
    subagent_type="code-reviewer-agent",
    description="Review the implementation",
    prompt="Review the authentication implementation for quality and security"
)

# 4. Delegate testing via Task Tool
Task(
    subagent_type="test-orchestrator-agent",
    description="Test the implementation",
    prompt="Create and run comprehensive tests for the authentication system"
)
```

### Dynamic Agent Selection for Delegation

When delegating tasks, select the appropriate agent based on task type:

```python
def delegate_to_best_agent(task_type, task_description, task_prompt):
    agent_mapping = {
        'security': 'security-auditor-agent',
        'testing': 'test-orchestrator-agent', 
        'ui': 'ui-designer-expert-shadcn-agent',
        'api': 'coding-agent',
        'architecture': 'system-architect-agent'
    }
    
    agent_name = agent_mapping.get(task_type, 'coding-agent')
    
    # Delegate via Task Tool
    Task(
        subagent_type=agent_name,
        description=task_description,
        prompt=task_prompt
    )
    
    # Note: The delegated agent will internally call call_agent 
    # to load their personal capabilities and rules
```

## Technical Implementation

### Call Agent Response Structure

```python
{
    "success": True,
    "agent_info": {
        "name": "coding-agent",
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

1. **Agent Name Normalization** - Use the `@agent_name` format when delegating to agents via Task Tool
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
    "available_agents": ["coding-agent", "debugger-agent", ...]
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

**Solution**: Ensure `agenthub_main/agent-library/` exists and contains agent definitions.

This integration provides a powerful bridge between Claude Code's delegation capabilities and agenthub's specialized agent ecosystem, enabling more sophisticated and specialized AI workflows.
