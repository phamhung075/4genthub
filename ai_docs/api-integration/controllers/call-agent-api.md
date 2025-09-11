# Call Agent API Documentation

## Overview

The Call Agent MCP Controller (`call_agent_mcp_controller`) provides dynamic agent invocation capabilities within the DhafnckMCP system. This controller enables AI systems and clients to dynamically load and execute specialized agents by name, facilitating flexible multi-agent orchestration and workflow management.

## Controller Details

- **Controller Name**: `CallAgentMCPController`
- **MCP Tool**: `call_agent`
- **Location**: `dhafnck_mcp_main/src/fastmcp/task_management/interface/mcp_controllers/call_agent_mcp_controller/`
- **Protocol**: MCP (Model Context Protocol)
- **Architecture**: Domain-Driven Design (DDD) compliant

## Purpose and Responsibilities

The Call Agent controller serves as the entry point for:
- **Dynamic Agent Loading**: Load and invoke agents by name at runtime
- **Agent Discovery**: Discover available agents in the system
- **Multi-Agent Orchestration**: Enable complex workflows involving multiple specialized agents
- **Agent Handoff**: Facilitate seamless transitions between different agent types
- **Specialized Task Delegation**: Route tasks to the most appropriate agent

## Available Actions

### call_agent

Loads and invokes a specific agent by name for task execution.

**Parameters:**
- `name_agent` (required): Name of the agent to load and invoke

**Usage Example:**
```json
{
  "action": "call_agent",
  "name_agent": "@master_orchestrator_agent"
}
```

## Agent Naming Convention

All agent names must follow the `@agent-name` format:
- **Prefix**: Must start with `@`
- **Format**: Use kebab-case (lowercase with hyphens)
- **Examples**: `@coding-agent`, `@test-orchestrator-agent`, `@security-auditor-agent`

## Available Agents (42 Total)

### Development & Coding (4)
- `@coding_agent` - Implementation and feature development
- `@debugger_agent` - Bug fixing and troubleshooting
- `@code_reviewer_agent` - Code quality and review
- `@prototyping_agent` - Rapid prototyping and POCs

### Testing & QA (3)
- `@test_orchestrator_agent` - Comprehensive test management
- `@uat_coordinator_agent` - User acceptance testing
- `@performance_load_tester_agent` - Performance and load testing

### Architecture & Design (4)
- `@system_architect_agent` - System design and architecture
- `@design_system_agent` - Design system and UI patterns
- `@ui_specialist_agent` - UI/UX design and frontend development
- `@core_concept_agent` - Core concepts and fundamentals

### DevOps & Infrastructure (1)
- `@devops_agent` - CI/CD and infrastructure

### Documentation (1)
- `@documentation_agent` - Technical documentation

### Project & Planning (4)
- `@project_initiator_agent` - Project setup and kickoff
- `@task_planning_agent` - Task breakdown and planning
- `@master_orchestrator_agent` - Complex workflow orchestration
- `@elicitation_agent` - Requirements gathering

### Security & Compliance (3)
- `@security_auditor_agent` - Security audits and reviews
- `@compliance_scope_agent` - Regulatory compliance
- `@ethical_review_agent` - Ethical considerations

### Analytics & Optimization (3)
- `@analytics_setup_agent` - Analytics and tracking setup
- `@efficiency_optimization_agent` - Process optimization
- `@health_monitor_agent` - System health monitoring

### Marketing & Branding (3)
- `@marketing_strategy_orchestrator_agent` - Marketing strategy
- `@community_strategy_agent` - Community building
- `@branding_agent` - Brand identity

### Research & Analysis (4)
- `@deep_research_agent` - In-depth research
- `@llm_ai_agents_research` - AI/ML research and innovations
- `@root_cause_analysis_agent` - Problem analysis
- `@technology_advisor_agent` - Technology recommendations

### AI & Machine Learning (1)
- `@ml_specialist_agent` - Machine learning implementation

### Creative & Ideation (1)
- `@creative_ideation_agent` - Creative idea generation

## Agent Selection Decision Tree

The system uses intelligent routing based on work type keywords:

```yaml
IF work_type matches "debug|fix|error|bug|troubleshoot":
    USE @debugger_agent
ELIF work_type matches "implement|code|build|develop|create":
    USE @coding_agent
ELIF work_type matches "test|verify|validate|qa":
    USE @test_orchestrator_agent
ELIF work_type matches "plan|analyze|breakdown|organize":
    USE @task_planning_agent
ELIF work_type matches "design|ui|interface|ux|frontend":
    USE @ui_specialist_agent
ELIF work_type matches "security|audit|vulnerability":
    USE @security_auditor_agent
ELIF work_type matches "deploy|infrastructure|devops|ci/cd":
    USE @devops_agent
ELIF work_type matches "document|guide|manual|readme":
    USE @documentation_agent
ELIF work_type matches "orchestrate|coordinate|multi-step|complex":
    USE @master_orchestrator_agent
ELSE:
    USE @master_orchestrator_agent  # Default fallback
```

## Architecture Components

### Handler Layer
- **AgentInvocationHandler**: Manages agent invocation logic
- **Responsibilities**: Validate agent names, load agents, handle invocation

### Service Layer
- **AgentDiscoveryService**: Discovers available agents in the system
- **Responsibilities**: Agent enumeration, validation, error reporting

### Use Case Layer
- **CallAgentUseCase**: Business logic for agent operations
- **Responsibilities**: Agent lifecycle management, execution coordination

## Authentication and Authorization

### Authentication Requirements
- **User Authentication**: Required for all agent invocation operations
- **Authentication Method**: JWT token validation
- **User Context**: Propagated through agent invocation chain

### Authorization Model
- **Permission**: `agents:invoke` - Required for all agent invocation operations
- **Resource-Specific**: Agent-specific permissions may apply
- **Audit Trail**: All agent invocations logged with user context

## Response Format

### Successful Response
```json
{
  "success": true,
  "agent_name": "@coding_agent",
  "status": "invoked",
  "message": "Agent successfully loaded and ready for operation",
  "agent_info": {
    "specialization": "Implementation and feature development",
    "capabilities": ["coding", "implementation", "feature development"],
    "context_requirements": "code files, requirements, architecture"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Error Response
```json
{
  "success": false,
  "error": "Agent '@invalid_agent' not found",
  "error_code": "AGENT_NOT_FOUND",
  "available_agents": [
    "@coding_agent",
    "@test_orchestrator_agent",
    "@master_orchestrator_agent"
  ],
  "suggestions": [
    "Check agent name spelling",
    "Ensure agent name starts with @",
    "Use one of the available agents listed"
  ],
  "timestamp": "2025-01-15T10:30:00Z"
}
```

## Usage Patterns

### Simple Agent Invocation
```python
response = await call_agent(name_agent="@coding_agent")
```

### Multi-Agent Workflow
```python
# Step 1: Plan with task planning agent
plan_response = await call_agent(name_agent="@task_planning_agent")

# Step 2: Implement with coding agent
code_response = await call_agent(name_agent="@coding_agent")

# Step 3: Test with test orchestrator
test_response = await call_agent(name_agent="@test_orchestrator_agent")
```

### Orchestrated Workflow
```python
# Use master orchestrator for complex workflows
orchestrator_response = await call_agent(name_agent="@master_orchestrator_agent")
```

## Error Handling

### Common Error Scenarios
1. **Agent Not Found**: Invalid or non-existent agent name
2. **Agent Load Failure**: Agent exists but fails to load
3. **Permission Denied**: User lacks agent invocation permissions
4. **Invalid Format**: Agent name doesn't follow @agent-name format

### Error Recovery
- **Fallback Agent**: System falls back to `@master_orchestrator_agent` on errors
- **Available Agents**: Error responses include list of available agents
- **Suggestions**: Helpful suggestions for resolving common errors

## Performance Considerations

### Agent Caching
- **Lazy Loading**: Agents loaded on first invocation
- **Memory Management**: Efficient agent lifecycle management
- **Concurrent Access**: Thread-safe agent invocation

### Optimization Strategies
- **Agent Reuse**: Agents cached for multiple invocations
- **Context Preservation**: Agent context maintained across invocations
- **Resource Management**: Automatic cleanup of unused agents

## Best Practices

### Agent Selection
1. **Use Specific Agents**: Choose the most appropriate agent for the task
2. **Fallback Strategy**: Always have a fallback to `@master_orchestrator_agent`
3. **Context Awareness**: Consider agent specialization and capabilities
4. **Workflow Planning**: Use `@task_planning_agent` for complex workflows

### Error Handling
1. **Validate Agent Names**: Ensure proper format before invocation
2. **Handle Errors Gracefully**: Implement proper error handling
3. **Use Fallbacks**: Have fallback agents for critical operations
4. **Log Operations**: Maintain audit trail for agent invocations

### Security
1. **Validate Permissions**: Ensure user has agent invocation rights
2. **Audit All Operations**: Log all agent invocations
3. **Sanitize Inputs**: Validate agent names for security
4. **Context Isolation**: Maintain user context isolation

## Integration Examples

### MCP Client Integration
```python
# MCP client example
import mcp_client

client = mcp_client.MCPClient()
response = await client.call_tool(
    "call_agent",
    {
        "name_agent": "@coding_agent"
    }
)
```

### Direct Controller Usage
```python
# Direct controller usage
controller = CallAgentMCPController(call_agent_use_case)
response = controller.call_agent(name_agent="@coding_agent")
```

## Testing

### Unit Tests
- **Agent Discovery**: Test agent enumeration functionality
- **Agent Invocation**: Test successful agent loading and invocation
- **Error Handling**: Test various error scenarios and responses
- **Permission Checking**: Test authorization logic

### Integration Tests
- **Multi-Agent Workflows**: Test agent handoff scenarios
- **Error Recovery**: Test fallback mechanisms
- **Performance**: Test concurrent agent invocations
- **Security**: Test authentication and authorization


## Troubleshooting

### Common Issues

1. **Agent Not Found Error**
   - **Cause**: Invalid agent name or missing @ prefix
   - **Solution**: Check agent name format and available agents list

2. **Permission Denied**
   - **Cause**: User lacks agent invocation permissions
   - **Solution**: Verify user has `agents:invoke` permission

3. **Agent Load Failure**
   - **Cause**: Agent exists but fails to initialize
   - **Solution**: Check agent configuration and dependencies

4. **Context Loss**
   - **Cause**: User context not properly propagated
   - **Solution**: Verify authentication middleware is active

### Debugging Tips

1. **Enable Debug Logging**: Set log level to DEBUG for detailed information
2. **Check Available Agents**: Use agent discovery to verify agent availability
3. **Validate Permissions**: Verify user permissions for agent invocation
4. **Test with Simple Agents**: Start with basic agents before complex workflows

---

**Last Updated**: 2025-01-15  
**Version**: 1.0  
**Related Controllers**: Agent MCP Controller, Task MCP Controller  
**Dependencies**: Agent Library, Authentication System