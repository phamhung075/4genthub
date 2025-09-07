# Cloud MCP Platform - API Reference

## Overview

The Cloud MCP Platform provides both MCP protocol endpoints and REST API endpoints for comprehensive integration options.

**Base URL**: `https://api.cloud-mcp.example.com`  
**Version**: `v1`  
**Authentication**: Bearer token (JWT)

## Authentication

### Obtaining a Token

```http
POST /auth/token
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "refresh_token_string"
}
```

### Using the Token

Include the token in the Authorization header:
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

## MCP Protocol Endpoints

### Initialize MCP Session

```http
POST /mcp/initialize
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {}
    },
    "clientInfo": {
      "name": "your-client",
      "version": "1.0.0"
    }
  }
}
```

### List Available Tools

```http
POST /mcp/tools/list
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {}
}
```

### Call MCP Tool

```http
POST /mcp/tools/call
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "create_task",
    "arguments": {
      "title": "Build landing page",
      "description": "Create responsive landing page",
      "priority": "high"
    }
  }
}
```

## Task Management API

### Create Task

```http
POST /api/v1/tasks
Content-Type: application/json
Authorization: Bearer <token>

{
  "title": "Implement user authentication",
  "description": "Add JWT-based authentication to the API",
  "priority": "high",
  "assigned_agent_id": "agent_abc123",
  "due_date": "2025-02-01T00:00:00Z",
  "tags": ["backend", "security"],
  "template": "backend_feature"
}
```

**Response**:
```json
{
  "success": true,
  "task": {
    "id": "task_xyz789",
    "title": "Implement user authentication",
    "description": "Add JWT-based authentication to the API",
    "status": "pending",
    "priority": "high",
    "assigned_agent_id": "agent_abc123",
    "created_at": "2025-01-19T10:00:00Z",
    "created_by": "user_123",
    "organization_id": "org_456"
  }
}
```

### Get Task

```http
GET /api/v1/tasks/{task_id}
Authorization: Bearer <token>
```

**Response**:
```json
{
  "success": true,
  "task": {
    "id": "task_xyz789",
    "title": "Implement user authentication",
    "status": "in_progress",
    "progress": 45,
    "subtasks": [
      {
        "id": "subtask_001",
        "title": "Design authentication schema",
        "status": "completed"
      }
    ],
    "execution_logs": [
      {
        "timestamp": "2025-01-19T10:30:00Z",
        "message": "Agent started task execution",
        "level": "info"
      }
    ]
  }
}
```

### Update Task

```http
PATCH /api/v1/tasks/{task_id}
Content-Type: application/json
Authorization: Bearer <token>

{
  "status": "in_progress",
  "progress": 60,
  "notes": "Completed backend implementation, working on tests"
}
```

### List Tasks

```http
GET /api/v1/tasks?status=pending&priority=high&limit=20&offset=0
Authorization: Bearer <token>
```

**Query Parameters**:
- `status`: Filter by status (pending, in_progress, completed, failed)
- `priority`: Filter by priority (low, medium, high, critical)
- `assigned_agent_id`: Filter by assigned agent
- `created_after`: Filter by creation date (ISO 8601)
- `limit`: Number of results (default: 20, max: 100)
- `offset`: Pagination offset

### Delete Task

```http
DELETE /api/v1/tasks/{task_id}
Authorization: Bearer <token>
```

## Agent Management API

### Create Custom Agent

```http
POST /api/v1/agents
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "React Component Generator",
  "description": "Specialized agent for creating React components",
  "capabilities": [
    "generate_react_component",
    "typescript_support",
    "testing_integration"
  ],
  "tools": ["eslint", "prettier", "jest"],
  "base_template": "frontend_developer",
  "configuration": {
    "framework": "react",
    "language": "typescript",
    "styling": "tailwind"
  },
  "sharing": "team"
}
```

**Response**:
```json
{
  "success": true,
  "agent": {
    "id": "agent_custom_123",
    "name": "React Component Generator",
    "status": "active",
    "capabilities": ["generate_react_component", "typescript_support"],
    "api_key": "agent_key_xyz789",
    "webhook_url": "https://api.cloud-mcp.example.com/agents/agent_custom_123/webhook"
  }
}
```

### List Available Agents

```http
GET /api/v1/agents?type=custom&sharing=public
Authorization: Bearer <token>
```

### Get Agent Details

```http
GET /api/v1/agents/{agent_id}
Authorization: Bearer <token>
```

### Update Agent

```http
PATCH /api/v1/agents/{agent_id}
Content-Type: application/json
Authorization: Bearer <token>

{
  "configuration": {
    "max_concurrent_tasks": 5,
    "timeout_seconds": 300
  },
  "status": "active"
}
```

### Delete Agent

```http
DELETE /api/v1/agents/{agent_id}
Authorization: Bearer <token>
```

### Assign Agent to Task

```http
POST /api/v1/agents/{agent_id}/assign
Content-Type: application/json
Authorization: Bearer <token>

{
  "task_id": "task_xyz789",
  "execution_mode": "autonomous",
  "parameters": {
    "max_retries": 3,
    "timeout": 600
  }
}
```

## File Generation API

### Create File Template

```http
POST /api/v1/templates
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "React Component Template",
  "description": "Template for generating React components",
  "template_content": {
    "files": [
      {
        "path": "src/components/{{componentName}}/{{componentName}}.tsx",
        "template": "import React from 'react';\n\nexport const {{componentName}} = () => {\n  return <div>{{componentName}}</div>;\n};"
      },
      {
        "path": "src/components/{{componentName}}/{{componentName}}.test.tsx",
        "template": "import { render } from '@testing-library/react';\nimport { {{componentName}} } from './{{componentName}}';\n\ntest('renders {{componentName}}', () => {\n  render(<{{componentName}} />);\n});"
      }
    ]
  },
  "variables": {
    "componentName": {
      "type": "string",
      "required": true,
      "description": "Name of the React component"
    }
  },
  "tags": ["react", "typescript", "component"],
  "sharing": "public"
}
```

### Generate Files from Template

```http
POST /api/v1/templates/{template_id}/generate
Content-Type: application/json
Authorization: Bearer <token>

{
  "variables": {
    "componentName": "Button"
  },
  "output_format": "zip"
}
```

**Response**:
```json
{
  "success": true,
  "generation_id": "gen_abc123",
  "files_count": 2,
  "download_url": "https://storage.cloud-mcp.example.com/generated/gen_abc123.zip",
  "expires_at": "2025-01-19T12:00:00Z"
}
```

### List Templates

```http
GET /api/v1/templates?tags=react&sharing=public
Authorization: Bearer <token>
```

## Marketplace API

### Search Marketplace

```http
GET /api/v1/marketplace/search?q=react&type=agent&sort=popularity
Authorization: Bearer <token>
```

### Get Marketplace Item

```http
GET /api/v1/marketplace/items/{item_id}
Authorization: Bearer <token>
```

### Purchase/Subscribe to Item

```http
POST /api/v1/marketplace/items/{item_id}/subscribe
Content-Type: application/json
Authorization: Bearer <token>

{
  "plan": "monthly",
  "payment_method": "credit_card"
}
```

### Rate Marketplace Item

```http
POST /api/v1/marketplace/items/{item_id}/rate
Content-Type: application/json
Authorization: Bearer <token>

{
  "rating": 5,
  "review": "Excellent agent, saved hours of work!"
}
```

## Project Management API

### Create Project with Agents

```http
POST /api/v1/projects
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "E-commerce Platform",
  "template": "fullstack_web",
  "team_size": 5,
  "required_capabilities": [
    "frontend_development",
    "backend_development",
    "database_design",
    "testing",
    "deployment"
  ],
  "configuration": {
    "frontend_framework": "nextjs",
    "backend_framework": "fastapi",
    "database": "postgresql"
  }
}
```

**Response**:
```json
{
  "success": true,
  "project": {
    "id": "proj_123",
    "name": "E-commerce Platform",
    "status": "initialized",
    "tasks_created": 15,
    "agents_assigned": 5,
    "estimated_completion": "2025-02-15T00:00:00Z",
    "dashboard_url": "https://app.cloud-mcp.example.com/projects/proj_123"
  }
}
```

### Execute Project

```http
POST /api/v1/projects/{project_id}/execute
Content-Type: application/json
Authorization: Bearer <token>

{
  "execution_mode": "parallel",
  "auto_approve": false,
  "notification_webhook": "https://your-app.com/webhook"
}
```

## WebSocket API

### Real-time Task Updates

```javascript
const ws = new WebSocket('wss://api.cloud-mcp.example.com/ws');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'subscribe',
    channels: ['tasks', 'agents'],
    auth_token: 'your_jwt_token'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update received:', data);
  // Handle real-time updates
};
```

### Event Types

```json
{
  "type": "task.updated",
  "data": {
    "task_id": "task_xyz789",
    "status": "completed",
    "progress": 100
  }
}

{
  "type": "agent.status",
  "data": {
    "agent_id": "agent_abc123",
    "status": "busy",
    "current_task": "task_xyz789"
  }
}

{
  "type": "file.generated",
  "data": {
    "generation_id": "gen_abc123",
    "status": "ready",
    "download_url": "https://..."
  }
}
```

## Error Responses

All API endpoints return consistent error responses:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input parameters",
    "details": {
      "field": "priority",
      "issue": "Must be one of: low, medium, high, critical"
    }
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Invalid or missing authentication |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 400 | Invalid input parameters |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

## Rate Limiting

API requests are rate limited based on your subscription plan:

| Plan | Requests/Hour | Concurrent Tasks | Storage |
|------|---------------|------------------|---------|
| Free | 100 | 5 | 1 GB |
| Starter | 1,000 | 20 | 10 GB |
| Professional | 10,000 | 100 | 100 GB |
| Enterprise | Unlimited | Unlimited | Unlimited |

Rate limit headers are included in responses:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1640995200
```

## SDK Examples

### Python SDK

```python
from cloud_mcp import CloudMCPClient

client = CloudMCPClient(api_key="your_api_key")

# Create a task
task = client.tasks.create(
    title="Build landing page",
    description="Create responsive landing page",
    priority="high"
)

# Assign an agent
agent = client.agents.get("agent_abc123")
agent.assign_to_task(task.id)

# Generate files
template = client.templates.get("react_component")
files = template.generate(variables={"componentName": "Header"})
files.download("./src/components/")
```

### JavaScript SDK

```javascript
import { CloudMCP } from '@cloud-mcp/sdk';

const client = new CloudMCP({ apiKey: 'your_api_key' });

// Create and execute a task
const task = await client.tasks.create({
  title: 'Build landing page',
  description: 'Create responsive landing page',
  priority: 'high'
});

const agent = await client.agents.get('agent_abc123');
const result = await agent.execute(task);

// Download generated files
const files = await result.getGeneratedFiles();
await files.downloadTo('./output');
```

## Webhooks

Configure webhooks to receive real-time notifications:

```http
POST /api/v1/webhooks
Content-Type: application/json
Authorization: Bearer <token>

{
  "url": "https://your-app.com/webhook",
  "events": ["task.completed", "agent.failed", "file.generated"],
  "secret": "webhook_secret_key"
}
```

Webhook payload example:
```json
{
  "event": "task.completed",
  "timestamp": "2025-01-19T10:00:00Z",
  "data": {
    "task_id": "task_xyz789",
    "result": "success",
    "files_generated": 5
  },
  "signature": "sha256=..."
}
```