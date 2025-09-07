"""
Logging Management Tool Description

This module contains the comprehensive documentation for logging management MCP tools.
Separated from the controller logic for better maintainability and organization.
"""

MANAGE_LOGGING_DESCRIPTION = """
📋 LOGGING MANAGEMENT SYSTEM - Unified Frontend and Backend Log Collection

⭐ WHAT IT DOES: Manages centralized logging for both frontend and backend systems. Provides unified log collection, storage, and status monitoring for comprehensive application observability.
📋 WHEN TO USE: Log collection, debugging, monitoring, and system observability.
🎯 CRITICAL FOR: Debugging applications, monitoring system health, and maintaining comprehensive audit trails.
🚀 ENHANCED FEATURES: Batch log processing, unique batch IDs for traceability, automatic file management, and comprehensive status monitoring.

🤖 AI USAGE GUIDELINES:
• USE receive_frontend_logs for collecting browser/frontend application logs
• USE get_log_status to monitor logging system health and file sizes
• BATCH logs when possible for better performance and traceability
• MONITOR log file sizes to prevent disk space issues

| Action                | Required Parameters | Optional Parameters | Description                                    |
|-----------------------|-------------------|-------------------|------------------------------------------------|
| receive_frontend_logs | logs              | loggerId          | Receive and save frontend logs to file system |
| get_log_status        | (none)            |                   | Get logging system status and metrics         |

📝 PRACTICAL EXAMPLES FOR AI:
1. Collecting frontend errors:
   - action: "receive_frontend_logs", logs: [{"level": "ERROR", "message": "API call failed", "timestamp": "2024-01-01T12:00:00Z"}]

2. Monitoring log system:
   - action: "get_log_status" - returns file paths, sizes, and availability

💡 PARAMETERS:
• logs: Array of log entries with level, message, timestamp, and optional data
• loggerId: Optional identifier for log source (e.g., 'react-app', 'vue-component')

🔄 AUTOMATIC FEATURES:
• Batch ID generation for log traceability
• Automatic log file creation and management
• Structured log formatting with timestamps
• File size monitoring and status reporting
• UTF-8 encoding support for international content

📊 RESPONSE ENHANCEMENTS:
• batch_id: Unique identifier for each log batch
• log_file: Path to the log file where entries were saved
• status: Comprehensive logging system metrics
• file sizes and availability information

💡 BEST PRACTICES FOR AI:
• Batch multiple log entries in single calls for better performance
• Include meaningful loggerId for log source identification
• Monitor log file sizes regularly with get_log_status
• Use structured data in log entries for better analysis
• Include timestamps in frontend logs for accurate sequencing

🛑 ERROR HANDLING:
• Invalid log entries are gracefully handled with fallback formatting
• File system errors are caught and reported with clear error messages
• JSON serialization errors are handled with string fallback
• Missing log directories are automatically created
"""

MANAGE_LOGGING_PARAMETERS_DESCRIPTION = {
    "action": "Logging management action to perform. Valid values: receive_frontend_logs, get_log_status",
    "logs": "[OPTIONAL] Array of log entries to save. Required for receive_frontend_logs action. Each entry should have level, message, timestamp, and optional data fields",
    "loggerId": "[OPTIONAL] Identifier for log source (e.g., 'react-app', 'vue-component'). Used for log organization and filtering"
}

MANAGE_LOGGING_PARAMS = {
    "type": "object",
    "properties": {
        # Primary parameter (always required)
        "action": {
            "type": "string",
            "description": MANAGE_LOGGING_PARAMETERS_DESCRIPTION["action"]
        },
        
        # Log data parameters
        "logs": {
            "type": "string",
            "description": MANAGE_LOGGING_PARAMETERS_DESCRIPTION["logs"]
        },
        "loggerId": {
            "type": "string", 
            "description": MANAGE_LOGGING_PARAMETERS_DESCRIPTION["loggerId"]
        }
    },
    "required": ["action"],  # Only action required at schema level - business logic validates per action
    "additionalProperties": False
}

def get_manage_logging_parameters():
    """Get manage logging parameters for use in controller."""
    return MANAGE_LOGGING_PARAMS["properties"]

def get_manage_logging_description():
    """Get manage logging description for use in controller."""
    return MANAGE_LOGGING_DESCRIPTION

# Legacy parameter descriptions for backward compatibility  
MANAGE_LOGGING_PARAMETERS = {
    "action": "Logging management action to perform. Valid: 'receive_frontend_logs', 'get_log_status'. Required. (string)",
    "logs": "Array of log entries to save. Required for receive_frontend_logs action. Each entry should have level, message, timestamp, and optional data fields. (array)",
    "loggerId": "Identifier for log source (e.g., 'react-app', 'vue-component'). Optional for receive_frontend_logs action. (string)"
}