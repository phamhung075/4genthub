"""
Compliance Management Tool Description

This module contains the comprehensive documentation for the manage_compliance MCP tool.
Separated from the controller logic for better maintainability and organization.
"""

MANAGE_COMPLIANCE_DESCRIPTION = """
🛡️ COMPLIANCE MANAGEMENT SYSTEM - Operation Validation and Audit

⭐ WHAT IT DOES: Validates operations against security policies, tracks comprehensive audit trails, executes commands with compliance checks, and provides real-time compliance dashboards for security monitoring and regulatory adherence.
📋 WHEN TO USE: Security validation, audit logging, compliant command execution, compliance reporting, and regulatory oversight.
🎯 CRITICAL FOR: Security enforcement, audit trail integrity, regulatory compliance, risk management, and operational security.
🚀 ENHANCED FEATURES: Real-time compliance scoring, detailed audit trails with metadata, security level enforcement, and automated compliance validation.

🤖 AI USAGE GUIDELINES:
• ALWAYS validate operations before execution when handling sensitive files or commands
• USE execute_with_compliance for any system commands that modify state
• CHECK compliance dashboard regularly for security posture assessment
• REVIEW audit trails when investigating security incidents or compliance issues

| Action                   | Required Parameters         | Optional Parameters                | Description                                      |
|--------------------------|----------------------------|------------------------------------|--------------------------------------------------|
| validate_compliance      | operation                  | file_path, content, user_id, security_level, audit_required | Validate operation against compliance policies   |
| get_compliance_dashboard | (none)                     |                                    | Get real-time compliance metrics and status      |
| execute_with_compliance  | command                    | timeout, user_id, audit_required   | Execute command with compliance validation       |
| get_audit_trail          | (none)                     | limit                               | Retrieve detailed audit trail with metadata      |

🔍 AI DECISION TREES:
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

💡 BEST PRACTICES FOR AI:
• Validate all file operations before execution
• Use appropriate security levels based on file sensitivity
• Monitor compliance dashboard regularly
• Investigate audit trails for security violations
• Execute system commands through compliance validation

🛑 ERROR HANDLING:
• Missing required parameters return clear error messages
• Invalid security levels are rejected with valid options
• Command execution failures are logged with compliance context
• Audit trail access is controlled by user permissions
"""

MANAGE_COMPLIANCE_PARAMETERS_DESCRIPTION = {
    "action": "Compliance management action to perform. Valid values: validate_compliance, get_compliance_dashboard, execute_with_compliance, get_audit_trail",
    "operation": "[OPTIONAL] Operation type to validate. Required for validate_compliance action. Examples: 'edit_file', 'delete_file', 'execute_command'",
    "command": "[OPTIONAL] Command to execute with compliance validation. Required for execute_with_compliance action",
    "file_path": "[OPTIONAL] File path for file operations. Used with validate_compliance for file-based operations",
    "content": "[OPTIONAL] File content or command content to validate. Used for security policy validation",
    "user_id": "[OPTIONAL] User identifier for audit trails and access control. Defaults to 'system' if not provided",
    "security_level": "[OPTIONAL] Security level for validation. Valid values: 'public', 'internal', 'restricted', 'confidential'. Defaults to 'public'",
    "audit_required": "[OPTIONAL] Whether to create audit trail entry. Accepts: 'true', 'false', '1', '0'. Defaults to 'true'",
    "timeout": "[OPTIONAL] Command execution timeout in seconds. Integer value for execute_with_compliance action",
    "limit": "[OPTIONAL] Number of audit trail entries to retrieve. Integer value for get_audit_trail action. Defaults to 100"
}

MANAGE_COMPLIANCE_PARAMS = {
    "type": "object",
    "properties": {
        # Primary parameter (always required)
        "action": {
            "type": "string",
            "description": MANAGE_COMPLIANCE_PARAMETERS_DESCRIPTION["action"]
        },
        
        # Operation parameters
        "operation": {
            "type": "string",
            "description": MANAGE_COMPLIANCE_PARAMETERS_DESCRIPTION["operation"]
        },
        "command": {
            "type": "string",
            "description": MANAGE_COMPLIANCE_PARAMETERS_DESCRIPTION["command"]
        },
        
        # File operation parameters
        "file_path": {
            "type": "string",
            "description": MANAGE_COMPLIANCE_PARAMETERS_DESCRIPTION["file_path"]
        },
        "content": {
            "type": "string",
            "description": MANAGE_COMPLIANCE_PARAMETERS_DESCRIPTION["content"]
        },
        
        # Security parameters
        "user_id": {
            "type": "string",
            "description": MANAGE_COMPLIANCE_PARAMETERS_DESCRIPTION["user_id"]
        },
        "security_level": {
            "type": "string",
            "description": MANAGE_COMPLIANCE_PARAMETERS_DESCRIPTION["security_level"]
        },
        "audit_required": {
            "type": "string",
            "description": MANAGE_COMPLIANCE_PARAMETERS_DESCRIPTION["audit_required"]
        },
        
        # Execution parameters
        "timeout": {
            "type": "integer",
            "description": MANAGE_COMPLIANCE_PARAMETERS_DESCRIPTION["timeout"]
        },
        "limit": {
            "type": "integer",
            "description": MANAGE_COMPLIANCE_PARAMETERS_DESCRIPTION["limit"]
        }
    },
    "required": ["action"],  # Only action required at schema level - business logic validates per action
    "additionalProperties": False
}

def get_manage_compliance_parameters():
    """Get manage compliance parameters for use in controller."""
    return MANAGE_COMPLIANCE_PARAMS["properties"]

def get_manage_compliance_description():
    """Get manage compliance description for use in controller."""
    return MANAGE_COMPLIANCE_DESCRIPTION