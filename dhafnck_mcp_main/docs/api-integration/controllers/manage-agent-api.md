# manage_agent - Agent Management API Documentation

## Overview

The `manage_agent` tool provides comprehensive agent lifecycle management, registration, assignment, and orchestration within the DhafnckMCP platform. It enables dynamic agent loading, execution tracking, and intelligent agent coordination for optimal task completion.

## Base Information

- **Tool Name**: `manage_agent`
- **Controller**: `AgentMCPController`
- **Module**: `fastmcp.task_management.interface.mcp_controllers.agent_mcp_controller`
- **Authentication**: Required (JWT-based user context)
- **Dynamic Loading**: ✅ Real-time agent discovery and instantiation
- **Execution Tracking**: ✅ Comprehensive activity monitoring and results
- **Multi-Agent Coordination**: ✅ Orchestrated agent collaboration

## Parameters Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "required": true,
      "description": "Agent management operation to perform"
    },
    "agent_id": {
      "type": "string",
      "description": "[OPTIONAL] Agent identifier (e.g., '@coding_agent')"
    },
    "task_id": {
      "type": "string",
      "description": "[OPTIONAL] Task UUID for agent assignment"
    },
    "git_branch_id": {
      "type": "string",
      "description": "[OPTIONAL] Branch UUID for branch-level agent assignment"
    },
    "project_id": {
      "type": "string", 
      "description": "[OPTIONAL] Project UUID for project-level operations"
    },
    "agent_config": {
      "type": "string",
      "description": "[OPTIONAL] Agent configuration as JSON string"
    },
    "execution_context": {
      "type": "string",
      "description": "[OPTIONAL] Execution context data as JSON string"
    },
    "timeout_seconds": {
      "type": "string",
      "description": "[OPTIONAL] Execution timeout in seconds"
    },
    "priority": {
      "type": "string",
      "description": "[OPTIONAL] Execution priority: 'low', 'normal', 'high', 'critical'"
    },
    "user_id": {
      "type": "string",
      "description": "[OPTIONAL] User identifier for authentication"
    }
  },
  "required": ["action"]
}
```

## Available Actions

### Agent Discovery and Registration

#### `list` - List Available Agents

Discovers and lists all available agents with their capabilities and status.

**Required Parameters:**
- `action`: "list"

**Optional Parameters:**
- `status`: Filter by status ("available", "busy", "error")
- `capability`: Filter by capability (e.g., "coding", "testing", "design")

**Example Request:**
```json
{
  "action": "list"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "list",
  "agents": [
    {
      "id": "@coding_agent",
      "name": "Coding Agent",
      "description": "Specialized in software development, implementation, and code review",
      "status": "available",
      "capabilities": [
        "code_generation",
        "code_review", 
        "debugging",
        "refactoring",
        "testing"
      ],
      "supported_languages": ["JavaScript", "TypeScript", "Python", "Java", "Go"],
      "current_assignments": 2,
      "max_concurrent": 5,
      "success_rate": 0.94,
      "average_completion_time": "2.3 hours",
      "last_activity": "2025-01-27T14:30:00Z"
    },
    {
      "id": "@ui_designer_agent", 
      "name": "UI Designer Agent",
      "description": "Expert in user interface design, UX patterns, and frontend development",
      "status": "busy",
      "capabilities": [
        "ui_design",
        "ux_analysis",
        "component_design",
        "accessibility_audit",
        "responsive_design"
      ],
      "frameworks": ["React", "Vue", "Angular", "Svelte"],
      "current_assignments": 1,
      "max_concurrent": 3,
      "success_rate": 0.89,
      "average_completion_time": "3.1 hours",
      "current_task": "Designing authentication flow UI"
    },
    {
      "id": "@security_auditor_agent",
      "name": "Security Auditor Agent", 
      "description": "Comprehensive security analysis, vulnerability assessment, and compliance",
      "status": "available",
      "capabilities": [
        "security_audit",
        "vulnerability_scan",
        "compliance_check",
        "penetration_testing",
        "code_security_review"
      ],
      "compliance_standards": ["OWASP", "SOC2", "GDPR", "HIPAA"],
      "current_assignments": 0,
      "max_concurrent": 2,
      "success_rate": 0.97,
      "average_completion_time": "4.7 hours"
    }
  ],
  "summary": {
    "total_agents": 15,
    "available": 12,
    "busy": 3,
    "error": 0,
    "total_capacity": 45,
    "current_utilization": 8
  }
}
```

#### `register` - Register New Agent

Registers a new agent with the system, making it available for assignment.

**Required Parameters:**
- `action`: "register"
- `agent_id`: Agent identifier
- `agent_config`: Agent configuration as JSON

**Example Request:**
```json
{
  "action": "register",
  "agent_id": "@custom_ml_agent",
  "agent_config": "{\"name\": \"Machine Learning Agent\", \"description\": \"Specialized in ML model training and analysis\", \"capabilities\": [\"model_training\", \"data_analysis\", \"feature_engineering\"], \"frameworks\": [\"TensorFlow\", \"PyTorch\", \"Scikit-learn\"], \"max_concurrent\": 2}"
}
```

#### `get_info` - Get Agent Information

Retrieves detailed information about a specific agent including current status and assignments.

**Required Parameters:**
- `action`: "get_info"
- `agent_id`: Agent identifier

**Example Request:**
```json
{
  "action": "get_info",
  "agent_id": "@coding_agent"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "get_info",
  "agent": {
    "id": "@coding_agent",
    "name": "Coding Agent",
    "description": "Specialized in software development, implementation, and code review",
    "status": "busy",
    "capabilities": ["code_generation", "code_review", "debugging", "refactoring", "testing"],
    "supported_languages": ["JavaScript", "TypeScript", "Python", "Java", "Go"],
    "configuration": {
      "max_concurrent": 5,
      "timeout_default": 1800,
      "retry_attempts": 3,
      "quality_threshold": 0.85
    },
    "current_assignments": [
      {
        "task_id": "task-123e4567-e89b-12d3-a456-426614174000",
        "title": "Implement JWT service",
        "assigned_at": "2025-01-27T13:45:00Z",
        "progress": 75,
        "estimated_completion": "2025-01-27T16:30:00Z"
      },
      {
        "branch_id": "branch-456e7890-f12b-34c5-d678-901234567efg",
        "name": "feature/user-authentication",
        "assigned_at": "2025-01-27T10:00:00Z",
        "tasks_completed": 3,
        "tasks_remaining": 4
      }
    ],
    "performance_metrics": {
      "total_completions": 247,
      "success_rate": 0.94,
      "average_completion_time": "2.3 hours",
      "quality_score": 0.91,
      "user_satisfaction": 4.3
    },
    "recent_activity": [
      {"timestamp": "2025-01-27T14:30:00Z", "event": "Task completed", "details": "JWT token validation implemented"},
      {"timestamp": "2025-01-27T13:45:00Z", "event": "Task started", "details": "JWT service implementation"},
      {"timestamp": "2025-01-27T12:15:00Z", "event": "Code review completed", "details": "Authentication middleware review"}
    ]
  }
}
```

### Agent Assignment Operations

#### `assign_to_task` - Assign Agent to Specific Task

Assigns an agent to work on a specific task with full context and requirements.

**Required Parameters:**
- `action`: "assign_to_task"
- `agent_id`: Agent identifier
- `task_id`: Task UUID

**Optional Parameters:**
- `execution_context`: Additional context as JSON
- `timeout_seconds`: Execution timeout
- `priority`: Assignment priority

**Example Request:**
```json
{
  "action": "assign_to_task",
  "agent_id": "@coding_agent",
  "task_id": "task-123e4567-e89b-12d3-a456-426614174000",
  "execution_context": "{\"requirements\": [\"Use TypeScript\", \"Include unit tests\", \"Follow ESLint rules\"], \"dependencies\": [\"@types/jsonwebtoken\", \"bcrypt\"], \"deadline\": \"2025-01-28T17:00:00Z\"}",
  "priority": "high"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "assign_to_task",
  "assignment": {
    "agent_id": "@coding_agent",
    "task_id": "task-123e4567-e89b-12d3-a456-426614174000",
    "assigned_at": "2025-01-27T15:00:00Z",
    "status": "accepted",
    "estimated_completion": "2025-01-27T17:30:00Z",
    "priority": "high"
  },
  "agent_context": {
    "task_details": {
      "title": "Implement JWT service",
      "description": "Create JWT token generation and validation service",
      "requirements": ["Use TypeScript", "Include unit tests", "Follow ESLint rules"]
    },
    "inherited_context": {
      "branch_context": "feature/user-authentication development guidelines",
      "project_context": "E-commerce platform technical standards"
    },
    "available_resources": {
      "existing_code": ["auth.types.ts", "user.model.ts"],
      "documentation": ["JWT implementation guide", "Security requirements"],
      "dependencies": ["@types/jsonwebtoken", "bcrypt"]
    }
  },
  "execution_plan": {
    "phases": [
      "Analyze existing code and requirements",
      "Design JWT service architecture", 
      "Implement token generation",
      "Implement token validation",
      "Add comprehensive tests",
      "Code review and optimization"
    ],
    "estimated_duration": "2.5 hours",
    "confidence": 0.87
  }
}
```

#### `assign_to_branch` - Assign Agent to Branch

Assigns an agent to work on all tasks within a branch, providing specialized focus.

**Required Parameters:**
- `action`: "assign_to_branch"
- `agent_id`: Agent identifier  
- `git_branch_id`: Branch UUID

**Example Request:**
```json
{
  "action": "assign_to_branch",
  "agent_id": "@security_auditor_agent",
  "git_branch_id": "branch-456e7890-f12b-34c5-d678-901234567efg"
}
```

#### `unassign` - Remove Agent Assignment

Removes an agent assignment from a task or branch.

**Required Parameters:**
- `action`: "unassign"
- `agent_id`: Agent identifier

**Optional Parameters:**
- `task_id`: Specific task to unassign from
- `git_branch_id`: Specific branch to unassign from

### Agent Execution Operations

#### `execute_task` - Execute Task with Agent

Directly executes a task using the specified agent with real-time monitoring.

**Required Parameters:**
- `action`: "execute_task"
- `agent_id`: Agent identifier
- `task_id`: Task UUID

**Optional Parameters:**
- `execution_context`: Execution parameters
- `timeout_seconds`: Execution timeout (default: 1800)
- `priority`: Execution priority

**Example Request:**
```json
{
  "action": "execute_task",
  "agent_id": "@coding_agent", 
  "task_id": "task-123e4567-e89b-12d3-a456-426614174000",
  "execution_context": "{\"mode\": \"implementation\", \"quality_level\": \"production\", \"test_coverage\": 0.9}",
  "timeout_seconds": "3600"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "execute_task",
  "execution": {
    "id": "exec-789abcde-f012-3456-789a-bcdef0123456",
    "agent_id": "@coding_agent",
    "task_id": "task-123e4567-e89b-12d3-a456-426614174000",
    "status": "running",
    "started_at": "2025-01-27T15:15:00Z",
    "estimated_completion": "2025-01-27T16:45:00Z",
    "progress": 0
  },
  "monitoring": {
    "real_time_updates": true,
    "progress_endpoint": "/api/executions/exec-789abcde-f012-3456-789a-bcdef0123456/status",
    "completion_webhook": "configured"
  },
  "initial_analysis": {
    "complexity_score": 0.7,
    "estimated_lines": 450,
    "required_tests": 12,
    "dependencies_needed": ["@types/jsonwebtoken", "bcrypt", "dotenv"]
  }
}
```

#### `get_execution_status` - Get Execution Status

Retrieves the current status of an agent task execution.

**Required Parameters:**
- `action`: "get_execution_status"
- `execution_id`: Execution UUID (returned from execute_task)

#### `cancel_execution` - Cancel Running Execution

Cancels a currently running agent execution.

**Required Parameters:**
- `action`: "cancel_execution"
- `execution_id`: Execution UUID

### Agent Analytics and Monitoring

#### `get_performance` - Get Agent Performance Metrics

Retrieves comprehensive performance analytics for an agent.

**Required Parameters:**
- `action`: "get_performance"
- `agent_id`: Agent identifier

**Optional Parameters:**
- `time_range`: Analysis period ("7d", "30d", "90d")
- `include_comparisons`: Include peer comparisons

**Example Response:**
```json
{
  "success": true,
  "operation": "get_performance",
  "agent_id": "@coding_agent",
  "time_range": "30d",
  "metrics": {
    "productivity": {
      "tasks_completed": 67,
      "average_completion_time": "2.3 hours",
      "velocity_trend": "increasing",
      "efficiency_score": 0.89
    },
    "quality": {
      "success_rate": 0.94,
      "defect_rate": 0.03,
      "test_coverage_average": 0.87,
      "code_review_score": 4.2
    },
    "reliability": {
      "uptime": 0.98,
      "error_rate": 0.02,
      "retry_success_rate": 0.91,
      "timeout_rate": 0.01
    },
    "collaboration": {
      "handoff_efficiency": 0.85,
      "context_preservation": 0.92,
      "documentation_quality": 4.1,
      "team_satisfaction": 4.3
    }
  },
  "trends": {
    "completion_time": "decreasing",
    "quality_score": "stable", 
    "error_rate": "decreasing",
    "user_satisfaction": "increasing"
  },
  "peer_comparison": {
    "rank": 3,
    "total_agents": 15,
    "percentile": 85,
    "areas_of_excellence": ["Code quality", "Test coverage"],
    "improvement_opportunities": ["Documentation", "Handoff communication"]
  }
}
```

#### `get_activity_log` - Get Agent Activity History

Retrieves detailed activity log for an agent.

**Required Parameters:**
- `action`: "get_activity_log"
- `agent_id`: Agent identifier

**Optional Parameters:**
- `days_back`: Number of days to include (default: 7)
- `activity_types`: Filter by activity types

## Agent Specialization Catalog

### Development Agents
- **@coding_agent**: General software development and implementation
- **@frontend_agent**: Frontend development, UI implementation  
- **@backend_agent**: Backend services, APIs, database integration
- **@fullstack_agent**: End-to-end application development

### Quality Assurance Agents
- **@test_orchestrator_agent**: Test strategy, framework setup, test orchestration
- **@functional_tester_agent**: Feature testing, user acceptance testing
- **@performance_tester_agent**: Load testing, performance optimization
- **@security_auditor_agent**: Security audits, vulnerability assessments

### Design and UX Agents  
- **@ui_designer_agent**: User interface design, component libraries
- **@ux_researcher_agent**: User research, usability analysis
- **@graphic_design_agent**: Visual design, branding, marketing materials

### Infrastructure Agents
- **@devops_agent**: CI/CD, deployment, infrastructure management
- **@database_agent**: Database design, optimization, migrations
- **@monitoring_agent**: System monitoring, alerting, observability

### Documentation and Analysis Agents
- **@documentation_agent**: Technical writing, API documentation
- **@business_analyst_agent**: Requirements analysis, process modeling
- **@data_analyst_agent**: Data analysis, reporting, insights

## Multi-Agent Coordination Patterns

### Sequential Execution
```json
// 1. Design phase
{"action": "assign_to_task", "agent_id": "@ui_designer_agent", "task_id": "design-task"}

// 2. Implementation phase (after design completion)
{"action": "assign_to_task", "agent_id": "@coding_agent", "task_id": "implementation-task"}

// 3. Testing phase
{"action": "assign_to_task", "agent_id": "@test_orchestrator_agent", "task_id": "testing-task"}
```

### Parallel Execution
```json
// Multiple agents working on different aspects simultaneously
{"action": "assign_to_task", "agent_id": "@frontend_agent", "task_id": "ui-task"}
{"action": "assign_to_task", "agent_id": "@backend_agent", "task_id": "api-task"}  
{"action": "assign_to_task", "agent_id": "@database_agent", "task_id": "schema-task"}
```

### Handoff Coordination
```json
// 1. Development completion triggers security review
{"action": "assign_to_task", "agent_id": "@coding_agent", "task_id": "feature-task"}

// 2. Automatic handoff to security agent upon completion
{"action": "assign_to_task", "agent_id": "@security_auditor_agent", "task_id": "security-review"}
```

## Error Handling

### Agent Errors
- `AGENT_NOT_FOUND`: Agent ID doesn't exist or isn't registered
- `AGENT_UNAVAILABLE`: Agent is at capacity or offline
- `AGENT_INCOMPATIBLE`: Agent doesn't support required capabilities
- `EXECUTION_FAILED`: Agent execution encountered an error
- `TIMEOUT_EXCEEDED`: Agent execution exceeded time limit

### Assignment Errors  
- `TASK_NOT_FOUND`: Task ID doesn't exist or user lacks access
- `ALREADY_ASSIGNED`: Task already has an agent assigned
- `CAPACITY_EXCEEDED`: Agent at maximum concurrent assignments
- `PERMISSION_DENIED`: User lacks permission for agent operations

### Example Error Response
```json
{
  "success": false,
  "error": "Agent is currently at maximum capacity",
  "error_code": "AGENT_UNAVAILABLE",
  "operation": "assign_to_task", 
  "metadata": {
    "agent_id": "@coding_agent",
    "current_assignments": 5,
    "max_capacity": 5,
    "estimated_availability": "2025-01-27T16:30:00Z",
    "alternative_agents": ["@fullstack_agent", "@backend_agent"]
  }
}
```

## Integration Patterns

### With Task Management
- Tasks can be automatically assigned to appropriate agents based on requirements
- Agent progress updates automatically sync with task progress
- Task completion triggers agent performance metrics updates

### With Context Management  
- Agents receive full context inheritance chain for comprehensive understanding
- Agent discoveries and insights automatically added to appropriate context levels
- Cross-agent knowledge sharing through shared context

### With Branch Management
- Branch assignments provide agents with focused work streams
- Agent specialization matched to branch requirements
- Branch health metrics include agent performance data

## Performance and Scalability

### Load Balancing
- **Capacity Management**: Automatic distribution based on agent capacity
- **Skill Matching**: Optimal agent selection based on task requirements
- **Priority Queuing**: High-priority tasks get preferential agent assignment
- **Failover Handling**: Automatic reassignment on agent failures

### Monitoring and Observability
- **Real-time Metrics**: Live performance monitoring for all agents
- **Execution Tracking**: Detailed logging of all agent activities
- **Resource Usage**: Memory, CPU, and time utilization monitoring
- **Quality Metrics**: Success rates, error patterns, and improvement trends

This agent management system provides comprehensive orchestration capabilities for intelligent, specialized AI agents working collaboratively on complex software development tasks.