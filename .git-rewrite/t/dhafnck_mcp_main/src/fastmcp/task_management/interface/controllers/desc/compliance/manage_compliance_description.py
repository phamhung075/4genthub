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
| validate_compliance      | operation                  | file_path, content, user_id (default: 'system'), security_level (default: 'public'), audit_required (default: True) | Validate operation against compliance policies   |
| get_compliance_dashboard | (none)                     |                                    | Get real-time compliance metrics and status      |
| execute_with_compliance  | command                    | timeout, user_id (default: 'system'), audit_required (default: True)   | Execute command with compliance validation       |
| get_audit_trail          | (none)                     | limit (default: 100)               | Retrieve detailed audit trail with metadata      |

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

📊 WORKFLOW PATTERNS:

1. **Secure File Operation Pattern**:
   ```python
   # Step 1: Validate before operation
   validation = validate_compliance(
       operation="edit_file",
       file_path="/sensitive/config.yaml",
       content=new_content,
       security_level="restricted"
   )
   
   # Step 2: Proceed only if compliant
   if validation["compliance_score"] >= 0.8:
       perform_file_operation()
   else:
       handle_security_violation(validation["violations"])
   ```

2. **Compliant Command Execution Pattern**:
   ```python
   # Execute with automatic compliance checks
   result = execute_with_compliance(
       command="rm -rf /tmp/*",
       timeout=60,
       user_id="admin_user",
       audit_required=True
   )
   
   # Check execution status
   if result["success"]:
       log_successful_operation(result["metadata"])
   else:
       investigate_failure(result["error"])
   ```

3. **Compliance Monitoring Pattern**:
   ```python
   # Regular compliance check
   dashboard = get_compliance_dashboard()
   
   if dashboard["compliance_rate"] < 0.95:
       # Investigate violations
       audit = get_audit_trail(limit=50)
       analyze_violations(audit["entries"])
   ```

💡 ENHANCED PARAMETERS:
• operation: Operation types include 'create_file', 'edit_file', 'delete_file', 'run_command', 'access_resource'
• security_level: Levels are 'public', 'internal', 'restricted', 'confidential', 'secret'
• user_id: Should be actual user identifier for proper audit attribution
• audit_required: Set to False only for read-only operations in non-sensitive areas
• timeout: Integer seconds for command execution (recommended: 30-300 based on operation)
• limit: Number of audit entries to retrieve (max: 1000, default: 100)

🔐 SECURITY BEST PRACTICES:
• Always validate operations before execution, especially for file modifications
• Use appropriate security levels - default 'public' is only for non-sensitive operations
• Enable audit trails (audit_required=True) for all state-changing operations
• Review audit trails regularly for suspicious patterns or repeated violations
• Set reasonable timeouts to prevent long-running malicious commands
• Monitor compliance dashboard for trending security issues

📈 COMPLIANCE SCORING:
• 1.0: Fully compliant, no violations detected
• 0.8-0.99: Minor violations, operation may proceed with warnings
• 0.5-0.79: Moderate violations, requires review or elevated permissions
• 0.0-0.49: Critical violations, operation blocked, security alert triggered

⚠️ CRITICAL WARNINGS:
• Never disable audit_required for privileged operations
• Always use execute_with_compliance instead of direct shell commands for sensitive operations
• Compliance validation is synchronous - may add latency to operations
• Audit trails are immutable - all actions are permanently logged
• Security levels cascade - 'secret' operations require highest privileges

🛑 ERROR HANDLING:
• Missing required parameters return detailed field-specific errors with hints
• Unknown actions return complete list of valid actions
• Validation failures include specific violation details and remediation steps
• Command execution errors include stderr, return codes, and timeout information
• Internal errors are logged with correlation IDs for investigation
"""

MANAGE_COMPLIANCE_PARAMETERS = {
    "action": "Compliance management action to perform. Valid actions: 'validate_compliance', 'get_compliance_dashboard', 'execute_with_compliance', 'get_audit_trail'. (string)",
    "operation": "Operation to validate (e.g., 'create_file', 'edit_file', 'delete_file', 'run_command'). Required for validate_compliance action. (string)",
    "file_path": "Path to file being operated on. Optional. (string)",
    "content": "Content of file operation. Optional. (string)",
    "user_id": "User performing operation. Default: 'system'. (string)",
    "security_level": "Security level for operation. Default: 'public'. (string)",
    "audit_required": "Whether to log to audit trail. Default: True. (boolean)",
    "command": "Command to execute. Required for execute_with_compliance action. (string)",
    "timeout": "Timeout in seconds for command execution. Optional. (integer)",
    "limit": "Maximum number of audit entries to return. Default: 100. Used for get_audit_trail action. (integer)"
} 