# MCP Integration Guide

## Overview
This guide covers the complete integration of DhafnckMCP server with MCP (Model Context Protocol) clients, including Claude Desktop, custom clients, and bridge implementations.

## Quick Start

### 1. Basic Configuration (.mcp.json)
```json
{
  "mcpServers": {
    "dhafnck_mcp_http": {
      "type": "http",
      "url": "http://localhost:8000/mcp/",
      "headers": {
        "Accept": "application/json, text/event-stream",
        "Authorization": "Bearer YOUR_JWT_TOKEN"
      }
    }
  }
}
```

### 2. Generate Authentication Token
```python
# scripts/generate_mcp_token.py
import jwt
from datetime import datetime, timedelta

SECRET = 'dGhpcyBpcyBhIGR1bW15IGp3dCBzZWNyZXQgZm9yIGRldmVsb3BtZW50'

def generate_token(user_id='mcp-client', days=30):
    payload = {
        'sub': user_id,
        'user_id': user_id,
        'type': 'access',
        'scopes': ['execute:mcp'],
        'exp': datetime.utcnow() + timedelta(days=days),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, SECRET, algorithm='HS256')

if __name__ == '__main__':
    token = generate_token()
    print(f'Your MCP token:\n{token}')
```

### 3. Test Connection
```bash
# Test MCP initialization
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {
        "name": "test-client",
        "version": "1.0"
      }
    },
    "id": 1
  }'
```

## Integration Patterns

### Pattern 1: Direct HTTP Integration

**Use Case**: Web applications, REST API clients

```javascript
class DhafnckMCPClient {
  constructor(token) {
    this.baseUrl = 'http://localhost:8000/mcp/';
    this.token = token;
    this.initialized = false;
  }

  async initialize() {
    const response = await fetch(this.baseUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.token}`,
        'Accept': 'application/json, text/event-stream'
      },
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'initialize',
        params: {
          protocolVersion: '2024-11-05',
          capabilities: {},
          clientInfo: {
            name: 'web-client',
            version: '1.0'
          }
        },
        id: 1
      })
    });

    const result = await response.json();
    this.initialized = true;
    return result;
  }

  async callTool(toolName, args) {
    if (!this.initialized) {
      await this.initialize();
    }

    const response = await fetch(this.baseUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.token}`
      },
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'tools/call',
        params: {
          name: toolName,
          arguments: args
        },
        id: Date.now()
      })
    });

    return await response.json();
  }
}
```

### Pattern 2: STDIO Bridge Integration

**Use Case**: Claude Desktop, CLI tools

```python
# src/mcp_bridge.py
import sys
import json
import requests
import asyncio

class MCPBridge:
    def __init__(self):
        self.server_url = "http://localhost:8000/mcp/"
        self.session = requests.Session()
        
    def send_request(self, data):
        """Forward STDIO request to HTTP server"""
        response = self.session.post(
            self.server_url,
            json=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.get_token()}",
                "Accept": "application/json, text/event-stream"
            }
        )
        return response.json()
    
    async def run(self):
        """Main bridge loop"""
        while True:
            line = sys.stdin.readline()
            if not line:
                break
                
            request = json.loads(line)
            response = self.send_request(request)
            print(json.dumps(response))
            sys.stdout.flush()
```

### Pattern 3: Registration-Based Integration

**Use Case**: Clients requiring session management

```typescript
interface RegistrationResponse {
  success: boolean;
  session_id: string;
  server: {
    name: string;
    version: string;
    protocol_version: string;
  };
  endpoints: {
    mcp: string;
    initialize: string;
    tools: string;
    health: string;
  };
}

class RegisteredMCPClient {
  private sessionId: string | null = null;
  private endpoints: any = {};

  async register(): Promise<void> {
    const response = await fetch('http://localhost:8000/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        client_info: {
          name: 'typescript-client',
          version: '1.0'
        },
        capabilities: {
          tools: true,
          resources: true
        }
      })
    });

    const data: RegistrationResponse = await response.json();
    this.sessionId = data.session_id;
    this.endpoints = data.endpoints;
  }

  async initialize(token: string): Promise<any> {
    if (!this.sessionId) {
      await this.register();
    }

    return fetch(this.endpoints.mcp, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'X-Session-ID': this.sessionId
      },
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'initialize',
        params: {
          protocolVersion: '2024-11-05',
          capabilities: {},
          clientInfo: {
            name: 'typescript-client',
            version: '1.0'
          }
        },
        id: 1
      })
    });
  }
}
```

## Tool Usage Examples

### Managing Tasks
```javascript
// Create a new task
const result = await client.callTool('manage_task', {
  action: 'create',
  git_branch_id: 'branch-uuid',
  title: 'Implement new feature',
  description: 'Add user authentication',
  priority: 'high'
});

// Get next task
const nextTask = await client.callTool('manage_task', {
  action: 'next',
  git_branch_id: 'branch-uuid',
  include_context: true
});

// Complete task
const completion = await client.callTool('manage_task', {
  action: 'complete',
  task_id: 'task-uuid',
  completion_summary: 'Implemented JWT authentication',
  testing_notes: 'All tests passing'
});
```

### Managing Context
```javascript
// Update branch context
await client.callTool('manage_context', {
  action: 'update',
  level: 'branch',
  context_id: 'branch-uuid',
  data: {
    current_work: 'Authentication implementation',
    decisions: ['Using JWT', 'Redis for sessions'],
    blockers: []
  }
});

// Get inherited context
const context = await client.callTool('manage_context', {
  action: 'resolve',
  level: 'branch',
  context_id: 'branch-uuid',
  include_inherited: true
});
```

### Calling Agents
```javascript
// Switch to coding agent
await client.callTool('call_agent', {
  name_agent: 'coding-agent'
});

// Call documentation agent
await client.callTool('call_agent', {
  name_agent: 'documentation-agent'
});
```

## Protocol Details

### JSON-RPC 2.0 Format
All requests follow JSON-RPC 2.0 specification:

```json
{
  "jsonrpc": "2.0",
  "method": "method_name",
  "params": {
    "param1": "value1",
    "param2": "value2"
  },
  "id": 1
}
```

### Response Format
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    // Method-specific response data
  }
}
```

### Error Format
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32603,
    "message": "Internal error",
    "data": "Additional error information"
  }
}
```

## Available Methods

### Core Protocol Methods
- `initialize` - Initialize MCP connection
- `tools/list` - List available tools
- `tools/call` - Execute a tool
- `resources/list` - List available resources
- `resources/read` - Read resource content
- `prompts/list` - List available prompts
- `prompts/get` - Get prompt template

### DhafnckMCP Extensions
- `agents/list` - List available agents
- `agents/call` - Switch to agent
- `workflow/status` - Get workflow status
- `vision/insights` - Get AI insights

## Authentication

### Token Requirements
- **Algorithm**: HS256
- **Required Claims**: sub, type, scopes, exp
- **Required Scope**: execute:mcp
- **Header Format**: Bearer <token>

### Token Validation Flow
1. Extract token from Authorization header
2. Verify JWT signature
3. Check expiration
4. Validate required scopes
5. Extract user context

## Error Handling

### Common Errors

#### Authentication Errors
```json
{
  "error": "invalid_token",
  "error_description": "Token expired or invalid"
}
```

**Solution**: Generate new token with correct expiration

#### Protocol Errors
```json
{
  "error": {
    "code": -32600,
    "message": "Invalid Request"
  }
}
```

**Solution**: Check request format matches JSON-RPC 2.0

#### Tool Errors
```json
{
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": "Missing required parameter: action"
  }
}
```

**Solution**: Include all required parameters for the tool

## Performance Optimization

### Connection Pooling
```python
# Reuse connections for multiple requests
session = requests.Session()
session.headers.update({
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
})

# Use session for all requests
response = session.post(url, json=data)
```

### Batch Requests
```json
[
  {"jsonrpc": "2.0", "method": "tools/list", "id": 1},
  {"jsonrpc": "2.0", "method": "agents/list", "id": 2},
  {"jsonrpc": "2.0", "method": "resources/list", "id": 3}
]
```

### Caching
- Cache tool list (changes rarely)
- Cache agent configurations
- Cache authentication tokens

## Monitoring Integration

### Health Checks
```bash
# Basic health check
curl http://localhost:8000/health

# Detailed status
curl http://localhost:8000/api/status
```

### Metrics to Track
- Request latency
- Tool execution time
- Authentication failures
- Active sessions
- Error rates

### Logging
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/mcp-client.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('mcp-client')
logger.info('MCP client initialized')
```

## Security Best Practices

### 1. Token Security
- Store tokens in environment variables
- Never commit tokens to version control
- Rotate tokens regularly
- Use short-lived tokens when possible

### 2. Network Security
- Use HTTPS in production
- Implement request signing
- Validate SSL certificates
- Use VPN for remote access

### 3. Input Validation
- Sanitize all user inputs
- Validate parameter types
- Check parameter bounds
- Escape special characters

## Deployment Configurations

### Development
```yaml
# docker-compose.yml
services:
  mcp-server:
    environment:
      - AUTH_ENABLED=false
      - LOG_LEVEL=DEBUG
    ports:
      - "8000:8000"
```

### Production
```yaml
# docker-compose.prod.yml
services:
  mcp-server:
    environment:
      - AUTH_ENABLED=true
      - LOG_LEVEL=INFO
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    ports:
      - "443:8000"
    volumes:
      - ./ssl:/etc/ssl
```

## Troubleshooting Checklist

1. **Connection Issues**
   - [ ] Docker container running?
   - [ ] Port 8000 accessible?
   - [ ] Firewall rules configured?

2. **Authentication Issues**
   - [ ] Token not expired?
   - [ ] Correct JWT secret?
   - [ ] Required scopes present?

3. **Protocol Issues**
   - [ ] Valid JSON-RPC format?
   - [ ] Correct protocol version?
   - [ ] Required headers present?

4. **Tool Issues**
   - [ ] Tool name correct?
   - [ ] Required parameters provided?
   - [ ] Parameter types correct?

## Additional Resources

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc7519)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
- [DhafnckMCP API Documentation](/ai_docs/api/)