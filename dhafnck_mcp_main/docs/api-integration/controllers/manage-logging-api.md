# manage_logging - Unified Logging Management API Documentation

## Overview

The `manage_logging` tool provides a unified logging system for both frontend and backend applications with centralized log collection, storage, and monitoring capabilities. It features batch processing, unique batch IDs for traceability, automatic file management, and comprehensive status monitoring for complete application observability.

## Base Information

- **Tool Name**: `manage_logging`
- **Controller**: `LoggingMCPController`
- **Module**: `fastmcp.task_management.interface.mcp_controllers.logging_mcp_controller`
- **Authentication**: Optional (enhanced with user context when available)
- **Log Storage**: File-based with UTF-8 encoding support
- **Batch Processing**: ✅ Unique batch IDs for traceability
- **Multi-Application Support**: ✅ Frontend and backend log separation

## Log File Structure

```
{project_root}/logs/
├── frontend.log    # Browser/client application logs
├── backend.log     # Server/API application logs (future)
└── ...            # Additional log files as needed
```

> **📁 Dynamic Path Resolution**: Log file paths are dynamically resolved based on the current execution environment. The system automatically detects whether it's running in a Docker container (`/app/logs`) or local environment (`{project_root}/logs`) and adjusts paths accordingly.

### Log Format
Each log entry is formatted with the following structure:
```
[{loggerId}] {timestamp} - {level} - {message} | Data: {data} | Batch: {batch_id}
```

## Parameters Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "required": true,
      "description": "Logging management action to perform"
    },
    "logs": {
      "type": "string",
      "description": "[OPTIONAL] Array of log entries to save. Required for receive_frontend_logs action"
    },
    "loggerId": {
      "type": "string",
      "description": "[OPTIONAL] Identifier for log source (e.g., 'react-app', 'vue-component')"
    }
  },
  "required": ["action"]
}
```

## Available Actions

### Log Collection Operations

#### `receive_frontend_logs` - Collect Frontend Logs

Receives and stores frontend application logs with batch processing and unique identifiers.

**Required Parameters:**
- `action`: "receive_frontend_logs"
- `logs`: Array of log entries (as JSON string or array)

**Optional Parameters:**
- `loggerId`: Source identifier for log organization

**Log Entry Structure:**
Each log entry should contain:
- `level`: Log level (ERROR, WARN, INFO, DEBUG, TRACE)
- `message`: Log message content
- `timestamp`: ISO 8601 timestamp (optional - auto-generated if missing)
- `data`: Additional structured data (optional)
- `loggerId`: Entry-specific logger ID (optional)

**Example Request:**
```json
{
  "action": "receive_frontend_logs",
  "logs": "[{\"level\": \"ERROR\", \"message\": \"API call failed\", \"timestamp\": \"2024-01-27T10:15:30.123Z\", \"data\": {\"url\": \"/api/users\", \"status\": 500, \"error\": \"Internal Server Error\"}}, {\"level\": \"INFO\", \"message\": \"User logged in successfully\", \"timestamp\": \"2024-01-27T10:16:45.456Z\", \"data\": {\"userId\": \"user-123\", \"sessionId\": \"sess-abc\"}}]",
  "loggerId": "react-app"
}
```

**Example Response:**
```json
{
  "success": true,
  "message": "Successfully logged 2 entries",
  "batch_id": "batch_20240127_101630_123456",
  "log_file": "/path/to/project/logs/frontend.log"
}
```

**Error Response (Missing logs):**
```json
{
  "success": false,
  "error": "Missing required field: logs",
  "error_code": "MISSING_FIELD",
  "field": "logs",
  "expected": "Array of log entries with level, message, timestamp fields",
  "hint": "Include 'logs' parameter with log entries array"
}
```

**Error Response (Invalid JSON):**
```json
{
  "success": false,
  "error": "Invalid JSON in logs parameter: Expecting ',' delimiter: line 1 column 45 (char 44)",
  "error_code": "INVALID_JSON",
  "field": "logs",
  "hint": "Ensure logs parameter contains valid JSON array"
}
```

### Monitoring Operations

#### `get_log_status` - Get Logging System Status

Retrieves comprehensive status information about the logging system including file paths, sizes, and availability.

**Required Parameters:**
- `action`: "get_log_status"

**Optional Parameters:** None

**Example Request:**
```json
{
  "action": "get_log_status"
}
```

**Example Response:**
```json
{
  "success": true,
  "status": {
    "logs_directory": "/path/to/project/logs",
    "backend_log": {
      "path": "/path/to/project/logs/backend.log",
      "exists": false,
      "size_bytes": 0
    },
    "frontend_log": {
      "path": "/path/to/project/logs/frontend.log",
      "exists": true,
      "size_bytes": 15420
    }
  }
}
```

## Usage Patterns

### Frontend Log Collection

#### JavaScript/TypeScript Applications
```javascript
// Example: React application logging
const sendLogsToMCP = async (logEntries) => {
  const request = {
    action: "receive_frontend_logs",
    logs: JSON.stringify(logEntries),
    loggerId: "react-app"
  };
  
  const response = await mcpClient.call("manage_logging", request);
  console.log(`Logs sent - Batch ID: ${response.batch_id}`);
};

// Usage examples
const errorLog = {
  level: "ERROR",
  message: "Failed to load user profile",
  timestamp: new Date().toISOString(),
  data: {
    userId: "user-123",
    error: "Network timeout",
    url: "/api/profile"
  }
};

const infoLog = {
  level: "INFO", 
  message: "User action performed",
  timestamp: new Date().toISOString(),
  data: {
    action: "button_click",
    component: "UserDashboard",
    userId: "user-123"
  }
};

await sendLogsToMCP([errorLog, infoLog]);
```

#### Vue.js Application Logging
```javascript
// Vue.js global error handler integration
const app = createApp(App);

app.config.errorHandler = (error, instance, info) => {
  const logEntry = {
    level: "ERROR",
    message: `Vue error: ${error.message}`,
    timestamp: new Date().toISOString(),
    data: {
      error: error.stack,
      info: info,
      component: instance?.$options.name || "Unknown"
    }
  };
  
  mcpClient.call("manage_logging", {
    action: "receive_frontend_logs",
    logs: JSON.stringify([logEntry]),
    loggerId: "vue-app"
  });
};
```

#### Angular Application Logging
```typescript
// Angular error handler service
@Injectable()
export class LoggingService {
  async sendErrorToMCP(error: any, context: string = 'Unknown') {
    const logEntry = {
      level: 'ERROR',
      message: error.message || 'Unknown error',
      timestamp: new Date().toISOString(),
      data: {
        stack: error.stack,
        context: context,
        url: window.location.href
      }
    };

    await this.mcpClient.call('manage_logging', {
      action: 'receive_frontend_logs', 
      logs: JSON.stringify([logEntry]),
      loggerId: 'angular-app'
    });
  }
}
```

### Batch Log Processing

#### High-Performance Batch Collection
```javascript
// Efficient batching for high-volume applications
class LogCollector {
  constructor() {
    this.logBuffer = [];
    this.batchSize = 10;
    this.flushInterval = 5000; // 5 seconds
    
    // Auto-flush on interval
    setInterval(() => this.flush(), this.flushInterval);
  }
  
  addLog(level, message, data = null) {
    const logEntry = {
      level: level.toUpperCase(),
      message,
      timestamp: new Date().toISOString(),
      data
    };
    
    this.logBuffer.push(logEntry);
    
    // Flush if buffer is full
    if (this.logBuffer.length >= this.batchSize) {
      this.flush();
    }
  }
  
  async flush() {
    if (this.logBuffer.length === 0) return;
    
    const logsToSend = [...this.logBuffer];
    this.logBuffer = [];
    
    try {
      const response = await mcpClient.call("manage_logging", {
        action: "receive_frontend_logs",
        logs: JSON.stringify(logsToSend),
        loggerId: "batch-collector"
      });
      
      console.log(`Flushed ${logsToSend.length} logs - Batch: ${response.batch_id}`);
    } catch (error) {
      // Re-add logs to buffer on failure
      this.logBuffer.unshift(...logsToSend);
      console.error("Failed to send logs:", error);
    }
  }
}

// Usage
const logger = new LogCollector();
logger.addLog("INFO", "Application started", { version: "1.2.3" });
logger.addLog("ERROR", "API call failed", { endpoint: "/api/data", status: 500 });
```

### System Monitoring

#### Log Status Monitoring
```javascript
// Monitor logging system health
const checkLoggingStatus = async () => {
  try {
    const response = await mcpClient.call("manage_logging", {
      action: "get_log_status"
    });
    
    const { status } = response;
    
    console.log("Logging System Status:");
    console.log(`- Logs Directory: ${status.logs_directory}`);
    console.log(`- Frontend Log: ${status.frontend_log.exists ? 'Exists' : 'Missing'} (${status.frontend_log.size_bytes} bytes)`);
    console.log(`- Backend Log: ${status.backend_log.exists ? 'Exists' : 'Missing'} (${status.backend_log.size_bytes} bytes)`);
    
    // Alert on large log files (>10MB)
    if (status.frontend_log.size_bytes > 10485760) {
      console.warn("Frontend log file is getting large - consider log rotation");
    }
    
  } catch (error) {
    console.error("Failed to check logging status:", error);
  }
};

// Check status periodically
setInterval(checkLoggingStatus, 60000); // Every minute
```

## Response Formats

### Success Responses

#### Successful Log Collection
```json
{
  "success": true,
  "message": "Successfully logged 5 entries",
  "batch_id": "batch_20240127_143022_789123", 
  "log_file": "/path/to/project/logs/frontend.log"
}
```

#### Successful Status Check
```json
{
  "success": true,
  "status": {
    "logs_directory": "/path/to/project/logs",
    "backend_log": {
      "path": "/path/to/project/logs/backend.log",
      "exists": true,
      "size_bytes": 2048576
    },
    "frontend_log": {
      "path": "/path/to/project/logs/frontend.log", 
      "exists": true,
      "size_bytes": 5242880
    }
  }
}
```

### Error Responses

#### Missing Required Field
```json
{
  "success": false,
  "error": "Missing required field: logs",
  "error_code": "MISSING_FIELD",
  "field": "logs",
  "expected": "Array of log entries with level, message, timestamp fields",
  "hint": "Include 'logs' parameter with log entries array"
}
```

#### Invalid JSON Format
```json
{
  "success": false,
  "error": "Invalid JSON in logs parameter: Unexpected token '}' in JSON at position 45",
  "error_code": "INVALID_JSON", 
  "field": "logs",
  "hint": "Ensure logs parameter contains valid JSON array"
}
```

#### Unknown Action
```json
{
  "success": false,
  "error": "Invalid action: invalid_action. Valid actions are: receive_frontend_logs, get_log_status",
  "error_code": "UNKNOWN_ACTION",
  "field": "action",
  "expected": "One of: receive_frontend_logs, get_log_status",
  "hint": "Check the 'action' parameter for typos"
}
```

#### Internal System Error
```json
{
  "success": false,
  "error": "Logging operation failed: Permission denied",
  "error_code": "INTERNAL_ERROR",
  "details": "Permission denied"
}
```

## Advanced Features

### Batch ID Traceability

Every log collection operation generates a unique batch ID with timestamp and microsecond precision:
- Format: `batch_YYYYMMDD_HHMMSS_microseconds`
- Example: `batch_20240127_143022_789123`
- Used for log correlation and debugging
- Automatically appended to each log entry

### Automatic File Management

The logging system provides:
- **Auto-creation**: Log directories created automatically if missing
- **UTF-8 Encoding**: Full international character support
- **Immediate Flushing**: Logs written immediately for crash resilience
- **Path Resolution**: Docker-aware path resolution (`/app/logs` vs project root)

### Structured Data Support

Log entries support complex structured data:
```javascript
const complexLogEntry = {
  level: "INFO",
  message: "User performed complex operation",
  timestamp: "2024-01-27T14:30:22.123Z",
  data: {
    user: {
      id: "user-123",
      email: "user@example.com",
      role: "admin"
    },
    operation: {
      type: "database_query",
      query: "SELECT * FROM users WHERE active = true",
      duration_ms: 45,
      results_count: 150
    },
    request: {
      ip: "192.168.1.100",
      user_agent: "Mozilla/5.0...",
      headers: {
        "content-type": "application/json"
      }
    }
  }
};
```

### Error Recovery

The logging system handles various error scenarios gracefully:
- **Malformed log entries**: Fallback formatting with error notation
- **File system errors**: Clear error messages with system details
- **JSON parsing failures**: String fallback with original data preservation
- **Missing directories**: Automatic creation with proper permissions

## Best Practices

### Performance Optimization
1. **Batch Multiple Entries**: Send multiple log entries in single requests
2. **Use Meaningful Logger IDs**: Include application/component identifiers
3. **Monitor File Sizes**: Regular status checks to prevent disk space issues
4. **Structure Log Data**: Use consistent data structures for easier analysis

### Development Guidelines
1. **Include Timestamps**: Always provide ISO 8601 formatted timestamps
2. **Use Appropriate Levels**: ERROR for failures, WARN for issues, INFO for events
3. **Provide Context**: Include relevant data for debugging and analysis
4. **Test Log Integration**: Verify log collection in development environments

### Production Considerations
1. **Log Rotation**: Implement external log rotation for large files
2. **Disk Space Monitoring**: Monitor log directory disk usage
3. **Access Controls**: Secure log files with appropriate permissions
4. **Backup Strategy**: Include logs in backup procedures for compliance

## Integration Examples

### React + TypeScript Integration
```typescript
// types/logging.ts
interface LogEntry {
  level: 'ERROR' | 'WARN' | 'INFO' | 'DEBUG' | 'TRACE';
  message: string;
  timestamp?: string;
  data?: Record<string, any>;
}

// services/LoggingService.ts
class LoggingService {
  private static instance: LoggingService;
  
  static getInstance(): LoggingService {
    if (!LoggingService.instance) {
      LoggingService.instance = new LoggingService();
    }
    return LoggingService.instance;
  }
  
  async sendLogs(entries: LogEntry[]): Promise<void> {
    // Add timestamps if missing
    const processedEntries = entries.map(entry => ({
      ...entry,
      timestamp: entry.timestamp || new Date().toISOString()
    }));
    
    const response = await mcpClient.call('manage_logging', {
      action: 'receive_frontend_logs',
      logs: JSON.stringify(processedEntries),
      loggerId: 'react-typescript-app'
    });
    
    console.log(`Logs sent successfully: ${response.batch_id}`);
  }
}
```

### Node.js Backend Integration (Future)
```javascript
// When backend logging support is added
const backendLogger = {
  async logToMCP(level, message, data = null) {
    const logEntry = {
      level: level.toUpperCase(),
      message,
      timestamp: new Date().toISOString(),
      data,
      source: 'nodejs-backend'
    };
    
    await mcpClient.call('manage_logging', {
      action: 'receive_backend_logs', // Future action
      logs: JSON.stringify([logEntry]),
      loggerId: 'nodejs-api'
    });
  }
};
```

## Common Use Cases

### 1. Error Tracking and Debugging
Collect frontend errors with full context for debugging:
```javascript
window.addEventListener('error', (event) => {
  const errorLog = {
    level: 'ERROR',
    message: `Uncaught error: ${event.message}`,
    timestamp: new Date().toISOString(),
    data: {
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      stack: event.error?.stack,
      url: window.location.href
    }
  };
  
  mcpClient.call('manage_logging', {
    action: 'receive_frontend_logs',
    logs: JSON.stringify([errorLog]),
    loggerId: 'error-tracker'
  });
});
```

### 2. User Activity Tracking
Monitor user interactions for analytics:
```javascript
const trackUserAction = (action, component, data = {}) => {
  const activityLog = {
    level: 'INFO',
    message: `User action: ${action}`,
    timestamp: new Date().toISOString(),
    data: {
      action,
      component,
      userId: getCurrentUserId(),
      sessionId: getSessionId(),
      ...data
    }
  };
  
  mcpClient.call('manage_logging', {
    action: 'receive_frontend_logs',
    logs: JSON.stringify([activityLog]),
    loggerId: 'user-analytics'
  });
};
```

### 3. Performance Monitoring
Track application performance metrics:
```javascript
const logPerformanceMetric = (metric, value, context = {}) => {
  const perfLog = {
    level: 'INFO',
    message: `Performance metric: ${metric}`,
    timestamp: new Date().toISOString(),
    data: {
      metric,
      value,
      unit: 'ms',
      context,
      timestamp: performance.now()
    }
  };
  
  mcpClient.call('manage_logging', {
    action: 'receive_frontend_logs',
    logs: JSON.stringify([perfLog]),
    loggerId: 'performance-monitor'
  });
};
```

This comprehensive API documentation provides complete coverage of the manage_logging MCP controller's capabilities, usage patterns, and integration examples for unified frontend and backend logging management.