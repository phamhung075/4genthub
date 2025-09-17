# manage_connection - Simplified Health Check API

## Overview

The `manage_connection` tool provides a basic health check endpoint for system monitoring. This has been simplified from the original complex connection management system to focus only on essential health monitoring functionality.

**Note**: This controller was significantly simplified to remove unused complexity. Only the health check functionality is retained as it's the only feature actually used by the frontend.

## Base Information

- **Tool Name**: `manage_connection`
- **Controller**: `ConnectionMCPController`  
- **Module**: `fastmcp.connection_management.interface.controllers.connection_mcp_controller`
- **Authentication**: Optional
- **Purpose**: Basic system health monitoring

## Parameters Schema

```json
{
  "type": "object",
  "properties": {
    "include_details": {
      "type": "boolean",
      "default": true,
      "description": "[OPTIONAL] Whether to include detailed information in health response"
    },
    "user_id": {
      "type": "string",
      "description": "[OPTIONAL] User identifier for authentication and audit trails"
    }
  },
  "required": []
}
```

## Health Check Operation

### Basic Health Check

Performs a basic health check to verify system availability and responsiveness.

**Optional Parameters:**
- `include_details`: Include detailed information (default: true)
- `user_id`: User identifier for audit trails

**Example Request:**
```json
{
  "include_details": true
}
```

**Example Response (Success):**
```json
{
  "success": true,
  "status": "healthy",
  "server_name": "4genthub",
  "version": "1.0.0",
  "authentication": {
    "enabled": true,
    "type": "JWT"
  },
  "task_management": {
    "active_tasks": 5,
    "status": "operational"
  },
  "environment": "development",
  "connections": {
    "database": "connected",
    "cache": "connected"
  },
  "timestamp": "2025-01-27T15:30:00Z"
}
```

**Example Response (Error):**
```json
{
  "success": false,
  "status": "error",
  "error": "Database connection failed",
  "timestamp": "2025-01-27T15:30:00Z"
}
```

## Error Handling

### Common Errors
- `INTERNAL_SERVER_ERROR`: Unexpected system error occurred
- `DATABASE_CONNECTION_FAILED`: Unable to connect to database
- `SERVICE_UNAVAILABLE`: System is temporarily unavailable

### Example Error Response
```json
{
  "success": false,
  "error": "Database connection timeout",
  "action": "health_check",
  "timestamp": "2025-01-27T15:30:00Z"
}
```

## Usage Guidelines

### Best Practices
1. **Regular Monitoring**: Use this endpoint for routine system health monitoring
2. **Lightweight Checks**: Set `include_details` to `false` for high-frequency monitoring
3. **Error Handling**: Always check the `success` field to determine system health
4. **Timeout Handling**: Implement appropriate timeouts for health check requests

### Integration Examples

#### Frontend Health Check
```javascript
// Simple health check
const healthCheck = async () => {
  try {
    const response = await mcpClient.callTool('manage_connection', {
      include_details: false
    });
    
    return response.success && response.status === 'healthy';
  } catch (error) {
    console.error('Health check failed:', error);
    return false;
  }
};
```

#### Monitoring Dashboard
```javascript
// Detailed health check for dashboard
const detailedHealthCheck = async () => {
  try {
    const response = await mcpClient.callTool('manage_connection', {
      include_details: true,
      user_id: 'monitoring_dashboard'
    });
    
    if (response.success) {
      return {
        status: response.status,
        server: response.server_name,
        version: response.version,
        services: {
          database: response.connections?.database,
          auth: response.authentication?.enabled,
          tasks: response.task_management?.status
        }
      };
    }
  } catch (error) {
    return { status: 'error', error: error.message };
  }
};
```

## Migration Notes

This API was simplified from a complex connection management system that supported multiple actions:
- ~~`server_capabilities`~~ - Removed (unused)
- ~~`connection_health`~~ - Removed (unused)  
- ~~`status`~~ - Removed (unused)
- ~~`register_updates`~~ - Removed (unused)
- ✅ `health_check` - Retained (actively used)

**Breaking Changes:**
- The `action` parameter is no longer required or supported
- All complex actions have been removed
- The tool now functions as a simple health check endpoint

If you need the removed functionality, consider implementing dedicated endpoints or tools for those specific use cases.

## Summary

This simplified connection management endpoint provides essential health monitoring capabilities with a clean, minimal API interface. The complexity has been reduced to focus on the single most important function: verifying system health.