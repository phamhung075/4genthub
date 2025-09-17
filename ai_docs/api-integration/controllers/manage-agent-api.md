# manage_agent - Agent Management API Documentation

## Overview

The `manage_agent` tool provides agent registration, assignment, and lifecycle management within the agenthub platform. It handles basic CRUD operations for agents and their assignment to git branches (task trees) within projects.

## Base Information

- **Tool Name**: `manage_agent`
- **Controller**: `AgentMCPController`
- **Module**: `fastmcp.task_management.interface.mcp_controllers.agent_mcp_controller`
- **Authentication**: Required (JWT-based user context)
- **Architecture**: Domain-Driven Design with modular handlers
- **Response Format**: Standardized success/error responses with workflow guidance

## Parameters Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "required": true,
      "description": "Agent management action to perform"
    },
    "project_id": {
      "type": "string",
      "required": true,
      "description": "Project identifier - REQUIRED for all actions"
    },
    "agent_id": {
      "type": "string",
      "description": "[OPTIONAL] Agent identifier - required for most actions except register/list/rebalance"
    },
    "name": {
      "type": "string",
      "description": "[OPTIONAL] Agent name - required for register, optional for update"
    },
    "call_agent": {
      "type": "string",
      "description": "[OPTIONAL] Call agent string or configuration - optional for register/update"
    },
    "git_branch_id": {
      "type": "string",
      "description": "[OPTIONAL] Git branch identifier - required for assign/unassign actions"
    },
    "user_id": {
      "type": "string",
      "description": "[OPTIONAL] User identifier for authentication and audit trails"
    }
  },
  "required": ["action"]
}
```

## Available Actions

### Basic CRUD Operations

#### `register` - Register New Agent

Registers a new agent to a project with optional configuration.

**Required Parameters:**
- `action`: "register"
- `project_id`: Project identifier
- `name`: Agent name

**Optional Parameters:**
- `agent_id`: Agent identifier (auto-generated if not provided)
- `call_agent`: Call agent string or configuration

**Example Request:**
```json
{
  "action": "register",
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Security Auditor Agent",
  "call_agent": "security_audit_config"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "register",
  "data": {
    "agent_id": "550e8400-e29b-41d4-a716-446655440001",
    "name": "Security Auditor Agent",
    "call_agent": "security_audit_config",
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "registered_at": "2025-01-27T15:00:00Z"
  },
  "metadata": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "agent_id": "550e8400-e29b-41d4-a716-446655440001",
    "agent_name": "Security Auditor Agent",
    "success_message": "Agent 'Security Auditor Agent' registered successfully"
  },
  "workflow_guidance": {
    "next_actions": ["assign agent to git branch", "update agent configuration"],
    "hints": ["Agent is now available for branch assignment"],
    "rules": ["Agents must be assigned to branches before task execution"]
  }
}
```

#### `get` - Get Agent Details

Retrieves detailed information about a specific agent.

**Required Parameters:**
- `action`: "get"
- `project_id`: Project identifier
- `agent_id`: Agent identifier

**Example Request:**
```json
{
  "action": "get",
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "get",
  "data": {
    "agent_id": "550e8400-e29b-41d4-a716-446655440001",
    "name": "Security Auditor Agent",
    "call_agent": "security_audit_config",
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "registered_at": "2025-01-27T15:00:00Z",
    "current_assignments": [
      {
        "git_branch_id": "550e8400-e29b-41d4-a716-446655440002",
        "assigned_at": "2025-01-27T15:30:00Z"
      }
    ]
  },
  "metadata": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "agent_id": "550e8400-e29b-41d4-a716-446655440001",
    "success_message": "Agent retrieved successfully"
  }
}
```

#### `list` - List All Agents in Project

Lists all agents registered to a project.

**Required Parameters:**
- `action`: "list"
- `project_id`: Project identifier

**Example Request:**
```json
{
  "action": "list",
  "project_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "list",
  "data": {
    "agents": [
      {
        "agent_id": "550e8400-e29b-41d4-a716-446655440001",
        "name": "Security Auditor Agent",
        "call_agent": "security_audit_config",
        "registered_at": "2025-01-27T15:00:00Z",
        "assignments": 1
      },
      {
        "agent_id": "550e8400-e29b-41d4-a716-446655440003",
        "name": "Coding Agent",
        "call_agent": null,
        "registered_at": "2025-01-27T14:30:00Z",
        "assignments": 2
      }
    ]
  },
  "metadata": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "agent_count": 2,
    "success_message": "Retrieved 2 agents"
  }
}
```

#### `update` - Update Agent

Updates an existing agent's metadata.

**Required Parameters:**
- `action`: "update"
- `project_id`: Project identifier
- `agent_id`: Agent identifier

**Optional Parameters:**
- `name`: New agent name
- `call_agent`: New call agent configuration

**Example Request:**
```json
{
  "action": "update",
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_id": "550e8400-e29b-41d4-a716-446655440001",
  "name": "Senior Security Auditor Agent",
  "call_agent": "advanced_security_config"
}
```

#### `unregister` - Remove Agent

Removes an agent from a project.

**Required Parameters:**
- `action`: "unregister"
- `project_id`: Project identifier
- `agent_id`: Agent identifier

**Example Request:**
```json
{
  "action": "unregister",
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

### Assignment Operations

#### `assign` - Assign Agent to Git Branch

Assigns an agent to a git branch (task tree) for specialized work.

**Required Parameters:**
- `action`: "assign"
- `project_id`: Project identifier
- `agent_id`: Agent identifier
- `git_branch_id`: Git branch identifier

**Example Request:**
```json
{
  "action": "assign",
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_id": "550e8400-e29b-41d4-a716-446655440001",
  "git_branch_id": "550e8400-e29b-41d4-a716-446655440002"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "assign",
  "data": {
    "agent_id": "550e8400-e29b-41d4-a716-446655440001",
    "git_branch_id": "550e8400-e29b-41d4-a716-446655440002",
    "assigned_at": "2025-01-27T15:30:00Z",
    "assignment_id": "550e8400-e29b-41d4-a716-446655440004"
  },
  "metadata": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "agent_id": "550e8400-e29b-41d4-a716-446655440001",
    "git_branch_id": "550e8400-e29b-41d4-a716-446655440002",
    "success_message": "Agent assigned successfully"
  },
  "workflow_guidance": {
    "next_actions": ["create tasks in the branch", "monitor agent progress"],
    "hints": ["Agent is now responsible for all tasks in this branch"],
    "rules": ["Tasks in this branch will inherit this agent assignment"]
  }
}
```

#### `unassign` - Remove Agent Assignment

Removes an agent assignment from a git branch.

**Required Parameters:**
- `action`: "unassign"
- `project_id`: Project identifier
- `agent_id`: Agent identifier
- `git_branch_id`: Git branch identifier

**Example Request:**
```json
{
  "action": "unassign",
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_id": "550e8400-e29b-41d4-a716-446655440001",
  "git_branch_id": "550e8400-e29b-41d4-a716-446655440002"
}
```

### Optimization Operations

#### `rebalance` - Rebalance Agent Assignments

Optimizes agent assignments across all branches in a project.

**Required Parameters:**
- `action`: "rebalance"
- `project_id`: Project identifier

**Example Request:**
```json
{
  "action": "rebalance",
  "project_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "rebalance",
  "data": {
    "rebalanced_agents": 3,
    "assignments_optimized": 7,
    "performance_improvement": "15%",
    "rebalance_summary": {
      "agents_reassigned": 2,
      "workload_balanced": true,
      "optimization_score": 0.89
    }
  },
  "metadata": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "rebalanced_agents": 3,
    "success_message": "Agent rebalancing completed successfully (3 agents affected)"
  }
}
```

## Two-Stage Validation

The manage_agent tool uses a two-stage validation pattern for optimal flexibility and user experience:

1. **Schema Level**: Only 'action' is required in the JSON schema for MCP compatibility
2. **Business Logic Level**: Each action has its own specific required parameters validated by the controller

### Action-Specific Requirements

| Action | Required Parameters | Optional Parameters |
|--------|-------------------|-------------------|
| register | action, project_id, name | agent_id, call_agent |
| get | action, project_id, agent_id | - |
| list | action, project_id | - |
| update | action, project_id, agent_id | name, call_agent |
| unregister | action, project_id, agent_id | - |
| assign | action, project_id, agent_id, git_branch_id | - |
| unassign | action, project_id, agent_id, git_branch_id | - |
| rebalance | action, project_id | - |

## Error Handling

### Missing Required Fields
```json
{
  "success": false,
  "error": "Missing required field: project_id",
  "error_code": "MISSING_FIELD",
  "field": "project_id",
  "action": "register",
  "expected": "A valid project_id value",
  "hint": "Include 'project_id' in your request for action 'register'"
}
```

### Operation Failures
```json
{
  "success": false,
  "error": "Failed to register agent: Agent name already exists in project",
  "error_code": "OPERATION_FAILED",
  "operation": "register",
  "metadata": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "agent_name": "Security Auditor Agent"
  }
}
```

### Unknown Actions
```json
{
  "success": false,
  "error": "Unknown action: invalid_action",
  "error_code": "UNKNOWN_ACTION",
  "valid_actions": ["register", "get", "list", "update", "unregister", "assign", "unassign", "rebalance"]
}
```

## Integration with Other Systems

### Project Management
- Agents are scoped to specific projects
- Agent assignments affect project resource allocation
- Project health metrics include agent utilization

### Git Branch Management
- Agents are assigned to git branches (task trees)
- Branch assignments provide focused work streams
- Agent specialization matched to branch requirements

### Task Management
- Tasks inherit agent assignments from their parent branches
- Agent progress updates reflected in task status
- Task completion metrics contribute to agent performance

### Context System
- Agent assignments propagated through context hierarchy
- Agent insights automatically added to appropriate context levels
- Context inheritance provides agents with complete project understanding

## Best Practices

### Agent Organization
- Use descriptive names that clearly indicate agent specialization
- Group related agents (e.g., all security agents) with consistent naming
- Register agents before assigning them to branches

### Assignment Strategy
- Assign specialized agents to matching branch types (security agents to security branches)
- Use the rebalance operation to optimize workload distribution
- Monitor agent utilization to prevent overloading

### Workflow Integration
- Create project → Register agents → Create branches → Assign agents → Create tasks
- Use workflow guidance responses to understand next steps
- Regular rebalancing improves overall project efficiency

This agent management system provides simple but effective agent registration and assignment capabilities within the agenthub platform's Domain-Driven Design architecture.