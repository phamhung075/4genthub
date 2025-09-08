# manage_compliance - Compliance Management API Documentation

## Overview

The `manage_compliance` tool provides comprehensive operation validation and audit capabilities for security monitoring and regulatory adherence. It validates operations against security policies, tracks detailed audit trails, executes commands with compliance checks, and provides real-time compliance dashboards.

## Base Information

- **Tool Name**: `manage_compliance`
- **Controller**: `ComplianceMCPController`
- **Module**: `fastmcp.task_management.interface.mcp_controllers.compliance_mcp_controller`
- **Authentication**: Required (JWT-based with user scoping)
- **Security Focus**: Operational validation, audit trails, command execution monitoring
- **Multi-Tenant**: ✅ Complete user isolation with audit trail segregation

## Key Features

- **Real-time Compliance Scoring**: Operations scored against security policies (0.0-1.0)
- **Comprehensive Audit Trails**: Detailed logging with metadata and timestamps
- **Command Execution Monitoring**: Secure command execution with compliance validation
- **Security Level Enforcement**: Multi-tier security validation (public, internal, restricted, confidential)
- **Regulatory Compliance**: Built-in support for compliance reporting and monitoring

## Parameters Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "required": true,
      "description": "Compliance management action to perform",
      "enum": [
        "validate_compliance",
        "get_compliance_dashboard", 
        "execute_with_compliance",
        "get_audit_trail"
      ]
    },
    "operation": {
      "type": "string",
      "description": "[OPTIONAL] Operation type to validate. Required for validate_compliance. Examples: 'edit_file', 'delete_file', 'execute_command'"
    },
    "command": {
      "type": "string", 
      "description": "[OPTIONAL] Command to execute with compliance validation. Required for execute_with_compliance"
    },
    "file_path": {
      "type": "string",
      "description": "[OPTIONAL] File path for file operations. Used with validate_compliance for file-based operations"
    },
    "content": {
      "type": "string",
      "description": "[OPTIONAL] File content or command content to validate. Used for security policy validation"
    },
    "user_id": {
      "type": "string",
      "description": "[OPTIONAL] User identifier for audit trails and access control. Defaults to 'system' if not provided"
    },
    "security_level": {
      "type": "string",
      "description": "[OPTIONAL] Security level for validation. Valid: 'public', 'internal', 'restricted', 'confidential'. Defaults to 'public'",
      "enum": ["public", "internal", "restricted", "confidential"]
    },
    "audit_required": {
      "type": "string",
      "description": "[OPTIONAL] Whether to create audit trail entry. Accepts: 'true', 'false', '1', '0'. Defaults to 'true'"
    },
    "timeout": {
      "type": "integer",
      "description": "[OPTIONAL] Command execution timeout in seconds. Used with execute_with_compliance"
    },
    "limit": {
      "type": "integer",
      "description": "[OPTIONAL] Number of audit trail entries to retrieve. Used with get_audit_trail. Defaults to 100"
    }
  },
  "required": ["action"]
}
```

## Available Actions

### 1. validate_compliance

Validates operations against security policies and returns compliance score.

#### Required Parameters
- `action`: "validate_compliance"
- `operation`: Operation type (e.g., "edit_file", "delete_file", "execute_command")

#### Optional Parameters
- `file_path`: File path for file operations
- `content`: File or command content to validate
- `user_id`: User identifier for audit trails
- `security_level`: Security classification level
- `audit_required`: Whether to create audit entry

#### JSON-RPC Request Example
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "manage_compliance",
  "params": {
    "action": "validate_compliance",
    "operation": "edit_file",
    "file_path": "/etc/passwd",
    "content": "user:x:1000:1000:User:/home/user:/bin/bash",
    "security_level": "restricted",
    "user_id": "user_123",
    "audit_required": "true"
  }
}
```

#### Response Format
```json
{
  "jsonrpc": "2.0", 
  "id": 1,
  "result": {
    "success": true,
    "compliance_score": 0.85,
    "operation": "edit_file",
    "file_path": "/etc/passwd",
    "security_level": "restricted",
    "violations": [],
    "recommendations": [
      "Consider using configuration management tools for system files"
    ],
    "audit_entry_id": "audit_uuid_123",
    "timestamp": "2024-09-08T15:30:00Z"
  }
}
```

### 2. get_compliance_dashboard

Retrieves real-time compliance metrics and system status.

#### Required Parameters
- `action`: "get_compliance_dashboard"

#### Optional Parameters
None

#### JSON-RPC Request Example
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "manage_compliance",
  "params": {
    "action": "get_compliance_dashboard"
  }
}
```

#### Response Format
```json
{
  "jsonrpc": "2.0",
  "id": 2, 
  "result": {
    "success": true,
    "dashboard": {
      "overall_compliance_score": 0.92,
      "total_operations": 1547,
      "compliant_operations": 1423,
      "violations": 124,
      "security_levels": {
        "public": {"score": 0.98, "operations": 892},
        "internal": {"score": 0.91, "operations": 445},
        "restricted": {"score": 0.87, "operations": 156},
        "confidential": {"score": 0.83, "operations": 54}
      },
      "recent_violations": [
        {
          "timestamp": "2024-09-08T15:25:00Z",
          "operation": "execute_command", 
          "user_id": "user_456",
          "violation": "Unauthorized system command execution"
        }
      ],
      "trends": {
        "compliance_trend": "improving",
        "violation_trend": "decreasing"
      },
      "last_updated": "2024-09-08T15:30:00Z"
    }
  }
}
```

### 3. execute_with_compliance

Executes commands with compliance validation and monitoring.

#### Required Parameters
- `action`: "execute_with_compliance"
- `command`: Shell command to execute

#### Optional Parameters
- `timeout`: Execution timeout in seconds
- `user_id`: User identifier for audit trails
- `audit_required`: Whether to create audit entry

#### JSON-RPC Request Example
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "manage_compliance",
  "params": {
    "action": "execute_with_compliance",
    "command": "ls -la /home/user",
    "timeout": 30,
    "user_id": "user_789",
    "audit_required": "true"
  }
}
```

#### Response Format
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "success": true,
    "command": "ls -la /home/user",
    "compliance_score": 0.95,
    "execution_time": 0.123,
    "exit_code": 0,
    "stdout": "total 24\ndrwxr-xr-x 6 user user 4096 Sep  8 15:30 .\ndrwxr-xr-x 3 root root 4096 Sep  8 10:00 ..",
    "stderr": "",
    "security_analysis": {
      "risk_level": "low",
      "detected_patterns": [],
      "recommendations": []
    },
    "audit_entry_id": "audit_uuid_456",
    "timestamp": "2024-09-08T15:30:00Z"
  }
}
```

### 4. get_audit_trail

Retrieves detailed audit trail with metadata and filtering.

#### Required Parameters
- `action`: "get_audit_trail"

#### Optional Parameters
- `limit`: Number of entries to retrieve (default: 100)

#### JSON-RPC Request Example
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "manage_compliance",
  "params": {
    "action": "get_audit_trail",
    "limit": 50
  }
}
```

#### Response Format
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "result": {
    "success": true,
    "audit_entries": [
      {
        "id": "audit_uuid_789",
        "timestamp": "2024-09-08T15:30:00Z",
        "user_id": "user_123",
        "action": "validate_compliance",
        "operation": "edit_file",
        "file_path": "/etc/passwd",
        "compliance_score": 0.85,
        "security_level": "restricted",
        "result": "compliant",
        "violations": [],
        "metadata": {
          "ip_address": "192.168.1.100",
          "user_agent": "MCP-Client/1.0",
          "session_id": "session_abc123"
        }
      },
      {
        "id": "audit_uuid_456", 
        "timestamp": "2024-09-08T15:25:00Z",
        "user_id": "user_456",
        "action": "execute_with_compliance",
        "command": "rm -rf /tmp/*",
        "compliance_score": 0.65,
        "result": "violation",
        "violations": [
          "Destructive command execution without proper authorization"
        ],
        "metadata": {
          "ip_address": "192.168.1.101",
          "risk_level": "high"
        }
      }
    ],
    "total_entries": 1547,
    "limit": 50,
    "offset": 0,
    "has_more": true
  }
}
```

## Security and Permission Requirements

### Authentication
- **JWT Token Required**: All operations require valid JWT token
- **User Scoping**: Operations are scoped to authenticated user
- **Session Validation**: Tokens validated for each request

### Security Levels
1. **public**: Basic validation, minimal restrictions
2. **internal**: Standard corporate security policies
3. **restricted**: Enhanced security checks, limited operations
4. **confidential**: Maximum security, extensive logging

### Audit Requirements
- **Mandatory Logging**: High-security operations always logged
- **Retention Policy**: Audit entries retained per compliance requirements
- **Access Control**: Audit trail access restricted by user permissions

## Error Handling and Status Codes

### Common Error Responses

#### Missing Required Parameters
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "success": false,
    "error": "Missing required field: operation",
    "error_code": "MISSING_FIELD",
    "field": "operation", 
    "expected": "A valid operation string (e.g., 'create_file', 'edit_file', etc.)",
    "hint": "Include 'operation' in your request body"
  }
}
```

#### Invalid Action
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "success": false,
    "error": "Invalid action: invalid_action. Valid actions are: validate_compliance, get_compliance_dashboard, execute_with_compliance, get_audit_trail",
    "error_code": "UNKNOWN_ACTION",
    "field": "action",
    "expected": "One of: validate_compliance, get_compliance_dashboard, execute_with_compliance, get_audit_trail",
    "hint": "Check the 'action' parameter for typos"
  }
}
```

#### Security Violation
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "success": false,
    "error": "Operation violates security policy",
    "error_code": "SECURITY_VIOLATION",
    "compliance_score": 0.25,
    "violations": [
      "Unauthorized access to restricted file",
      "Invalid security level for operation"
    ],
    "recommendations": [
      "Request appropriate permissions",
      "Use secure alternatives"
    ]
  }
}
```

#### Command Execution Failure
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "success": false,
    "error": "Command execution failed",
    "error_code": "EXECUTION_FAILED",
    "command": "invalid_command",
    "exit_code": 127,
    "stderr": "Command not found",
    "audit_entry_id": "audit_uuid_error"
  }
}
```

## Usage Guidelines

### Best Practices
1. **Pre-validation**: Always validate operations before execution
2. **Appropriate Security Levels**: Use correct security classification
3. **Audit Trail Review**: Regularly review audit logs for violations
4. **Dashboard Monitoring**: Monitor compliance dashboard for trends
5. **Command Validation**: Use execute_with_compliance for system commands

### AI Agent Decision Trees
```
Operation Request Received:
IF operation involves file_modification:
    USE validate_compliance(operation="edit_file", file_path=path, content=content)
    IF compliance_score >= 0.8:
        PROCEED with operation
    ELSE:
        REJECT and log security violation
        
ELIF operation involves command_execution:
    USE execute_with_compliance(command=cmd, timeout=30)
    MONITOR output for security violations
    
ELIF monitoring_compliance_status:
    USE get_compliance_dashboard()
    IF violations > threshold:
        ALERT and investigate with get_audit_trail()
```

### Common Workflow Patterns
1. **File Operation Validation**:
   - validate_compliance → check score → proceed or abort
2. **Secure Command Execution**:
   - execute_with_compliance → monitor results → audit review
3. **Compliance Monitoring**:
   - get_compliance_dashboard → identify issues → get_audit_trail
4. **Security Incident Investigation**:
   - get_audit_trail → filter by timeframe → analyze patterns

## Integration Examples

### Python Integration
```python
import json
import requests

def validate_file_edit(file_path, content, security_level="public"):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "manage_compliance",
        "params": {
            "action": "validate_compliance",
            "operation": "edit_file",
            "file_path": file_path,
            "content": content,
            "security_level": security_level,
            "audit_required": "true"
        }
    }
    
    response = requests.post("http://localhost:8000/mcp", 
                           json=payload,
                           headers={"Authorization": "Bearer YOUR_JWT_TOKEN"})
    
    result = response.json()
    if result["result"]["success"]:
        compliance_score = result["result"]["compliance_score"]
        if compliance_score >= 0.8:
            return True, "Operation approved"
        else:
            return False, f"Low compliance score: {compliance_score}"
    else:
        return False, result["result"]["error"]
```

### JavaScript Integration
```javascript
async function executeSecureCommand(command, timeout = 30) {
    const payload = {
        jsonrpc: "2.0",
        id: Date.now(),
        method: "manage_compliance",
        params: {
            action: "execute_with_compliance",
            command: command,
            timeout: timeout,
            audit_required: "true"
        }
    };

    const response = await fetch("http://localhost:8000/mcp", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${JWT_TOKEN}`
        },
        body: JSON.stringify(payload)
    });

    const result = await response.json();
    return result.result;
}
```

## Troubleshooting

### Common Issues
1. **Low Compliance Scores**: Review security policies and operation details
2. **Audit Trail Gaps**: Check audit_required parameter settings
3. **Command Timeouts**: Increase timeout parameter for long-running commands
4. **Permission Errors**: Verify JWT token and user permissions

### Debug Mode
Enable detailed logging by setting appropriate security level and reviewing audit trail entries for debugging information.

## Related Documentation
- [Security Configuration Guide](../configuration.md)
- [Audit Trail Management](../../troubleshooting-guides/audit-troubleshooting.md)
- [Authentication Setup](../../setup-guides/auth-setup.md)
- [Compliance Policies](../../operations/compliance-policies.md)