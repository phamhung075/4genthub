# manage_connection - Connection Management API Documentation

## Overview

The `manage_connection` tool provides unified connection management, health monitoring, and system status operations for the DhafnckMCP platform. It serves as the primary interface for connection diagnostics, server capability discovery, and client session management.

## Base Information

- **Tool Name**: `manage_connection`
- **Controller**: `ConnectionMCPController`  
- **Module**: `fastmcp.connection_management.interface.mcp_controllers.connection_mcp_controller`
- **Authentication**: Optional (varies by operation)
- **Connection Health**: ✅ Real-time connection monitoring
- **Server Capabilities**: ✅ Dynamic capability discovery

## Parameters Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "required": true,
      "description": "Connection management action to perform"
    },
    "include_details": {
      "type": "boolean",
      "default": true,
      "description": "[OPTIONAL] Whether to include detailed information in responses"
    },
    "connection_id": {
      "type": "string",
      "description": "[OPTIONAL] Specific connection identifier for targeted diagnostics"
    },
    "session_id": {
      "type": "string",
      "description": "[OPTIONAL] Client session identifier for update registration"
    },
    "client_info": {
      "oneOf": [
        {"type": "string"},
        {"type": "object"}
      ],
      "description": "[OPTIONAL] Client metadata for registration customization"
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

### Core Operations

#### `health_check` - System Health Check

Performs a basic health check to verify system availability and responsiveness.

**Required Parameters:**
- `action`: "health_check"

**Optional Parameters:**
- `include_details`: Include detailed information (default: true)
- `user_id`: User identifier for audit trails

**Example Request:**
```json
{
  "action": "health_check",
  "include_details": true
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "health_check",
  "status": "healthy",
  "timestamp": "2025-01-27T15:30:00Z"
}
```

#### `server_capabilities` - Server Capability Discovery

Retrieves information about server capabilities, available tools, and system configuration.

**Required Parameters:**
- `action`: "server_capabilities"

**Optional Parameters:**
- `include_details`: Include detailed capability information (default: true)
- `user_id`: User identifier for audit trails

**Example Request:**
```json
{
  "action": "server_capabilities"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "server_capabilities",
  "capabilities": {
    "version": "1.0.0",
    "tools": ["manage_task", "manage_context", "manage_project"],
    "features": ["authentication", "real_time_updates"]
  }
}
```

#### `connection_health` - Connection Health Check

Checks the health of specific connections or all system connections.

**Required Parameters:**
- `action`: "connection_health"

**Optional Parameters:**
- `connection_id`: Specific connection to check
- `include_details`: Include detailed connection information (default: true)
- `user_id`: User identifier for audit trails

**Example Request:**
```json
{
  "action": "connection_health",
  "connection_id": "conn_123456"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "connection_health",
  "connections": {
    "conn_123456": {
      "status": "healthy",
      "last_ping": "2025-01-27T15:29:45Z"
    }
  }
}
```

#### `status` - Overall System Status

Retrieves comprehensive system status including uptime, performance metrics, and general health.

**Required Parameters:**
- `action`: "status"

**Optional Parameters:**
- `include_details`: Include detailed status information (default: true)
- `user_id`: User identifier for audit trails

**Example Request:**
```json
{
  "action": "status"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "status",
  "system_status": {
    "uptime": "7d 14h 32m",
    "status": "operational",
    "version": "1.0.0"
  }
}
```

### Client Management

#### `register_updates` - Register Client for Updates

Registers a client session to receive real-time updates and notifications.

**Required Parameters:**
- `action`: "register_updates"

**Optional Parameters:**
- `session_id`: Client session identifier for registration
- `client_info`: Client metadata for registration customization (string or object)
- `user_id`: User identifier for authentication and audit trails

**Example Request:**
```json
{
  "action": "register_updates",
  "session_id": "sess_abc123",
  "client_info": {
    "type": "web_client",
    "version": "1.0.0",
    "capabilities": ["real_time_updates"]
  }
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "register_updates",
  "registration": {
    "session_id": "sess_abc123",
    "status": "registered",
    "update_types": ["task_updates", "system_notifications"]
  }
}
```

## Error Handling

### Common Errors
- `INVALID_ACTION`: Unknown or unsupported action requested
- `MISSING_PARAMETERS`: Required parameters not provided
- `CONNECTION_FAILED`: Unable to establish or verify connection
- `AUTHENTICATION_REQUIRED`: Operation requires user authentication
- `INTERNAL_SERVER_ERROR`: Unexpected system error occurred

### Example Error Response
```json
{
  "success": false,
  "error": "Invalid action specified",
  "error_code": "INVALID_ACTION",
  "operation": "invalid_operation",
  "metadata": {
    "valid_actions": [
      "health_check",
      "server_capabilities", 
      "connection_health",
      "status",
      "register_updates"
    ],
    "timestamp": "2025-01-27T15:30:00Z"
  }
}
```

## Usage Guidelines

### Best Practices
1. **Regular Health Checks**: Use `health_check` for routine system monitoring
2. **Capability Discovery**: Use `server_capabilities` to understand available features
3. **Connection Monitoring**: Use `connection_health` to diagnose connectivity issues
4. **System Status**: Use `status` for comprehensive system overview
5. **Client Registration**: Use `register_updates` for real-time update subscriptions

### Parameter Guidelines
- **include_details**: Set to `false` for lightweight responses when detailed information is not needed
- **connection_id**: Provide specific connection ID when troubleshooting individual connections
- **session_id**: Use consistent session IDs for reliable update delivery
- **client_info**: Provide meaningful client metadata to improve debugging and monitoring

### Response Handling
- Always check the `success` field to determine operation outcome
- Use `error_code` for programmatic error handling
- Review `metadata` for additional context and troubleshooting information
- Monitor `timestamp` fields for timing analysis and debugging

This connection management system provides essential connectivity monitoring and client management capabilities with a clean, consistent API interface.