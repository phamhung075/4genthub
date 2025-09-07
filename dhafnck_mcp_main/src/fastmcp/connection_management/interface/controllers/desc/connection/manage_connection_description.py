"""
Manage Connection Tool Description

Comprehensive connection management and monitoring capabilities for MCP server operations.
"""

MANAGE_CONNECTION_DESCRIPTION = """🔗 UNIFIED CONNECTION MANAGEMENT ENGINE - Complete connection, health, and monitoring operations

⭐ WHAT IT DOES: Comprehensive connection management system providing health monitoring, capabilities discovery, diagnostics, status tracking, and real-time updates
🔗 WHEN TO USE: All connection-related operations including health checks, server monitoring, capability discovery, diagnostics, and status broadcasting
🎯 CRITICAL FOR: Server monitoring, connection reliability, system diagnostics, client synchronization, and operational visibility

🔧 FUNCTIONALITY:
• Health Monitoring: Real-time server health checks with detailed status reporting
• Capability Discovery: Comprehensive server features and configuration information
• Connection Diagnostics: Advanced connection health analysis with troubleshooting guidance
• Status Tracking: Complete server status with connection statistics and performance metrics
• Update Broadcasting: Real-time status notification system for connected clients
• Authentication Integration: Auth status monitoring and token validation support
• Performance Metrics: Server uptime, response times, and operational statistics

💡 ACTION TYPES:
• 'health_check': Basic server health and availability check (supports: include_details)
• 'server_capabilities': Detailed server features and configuration discovery (supports: include_details)
• 'connection_health': Connection diagnostics with troubleshooting guidance (supports: include_details, connection_id)
• 'status': Comprehensive server status with connection statistics (supports: include_details)
• 'register_updates': Register session for real-time status notifications (requires: session_id, supports: client_info)

🔍 HEALTH CHECK FEATURES:
• Server availability and response verification
• Authentication system status and configuration
• Task management system integration status
• Environment configuration validation
• Connection pool health and statistics
• Database connectivity and performance
• Critical service dependency verification

📊 SERVER CAPABILITIES FEATURES:
• Core functionality enumeration (Task Management, Authentication, etc.)
• Available action mapping by functional area
• Security feature configuration (rate limiting, token validation)
• Tool configuration and enablement status
• API version and compatibility information
• Performance characteristics and limitations

🩺 CONNECTION DIAGNOSTICS FEATURES:
• Individual connection health assessment
• Network connectivity troubleshooting
• Performance bottleneck identification
• Error pattern analysis and recommendations
• Resource utilization monitoring
• Client compatibility verification
• Connection lifecycle tracking

📈 STATUS MONITORING FEATURES:
• Real-time server performance metrics
• Connection pool statistics and health
• Active session tracking and management
• Resource usage and capacity monitoring
• Error rate tracking and alerting
• Performance trend analysis
• System load and throughput metrics

📡 UPDATE BROADCASTING FEATURES:
• Real-time client notification system
• Session-based update delivery
• Event filtering and prioritization
• Client registration and management
• Status change propagation
• Alert and notification distribution

⚠️ USAGE GUIDELINES:
• Action Parameter: Required parameter specifying the operation type
• Include Details: Optional boolean for controlling response verbosity (default: true)
• Session ID: Required for register_updates action, identifies client session
• Connection ID: Optional for connection_health, targets specific connection
• Client Info: Optional metadata for client identification and customization
• Error Handling: All actions include comprehensive error reporting and suggestions

🎯 USE CASES:
• System Monitoring: Regular health checks and status monitoring for operational visibility
• Troubleshooting: Diagnostic tools for identifying and resolving connection issues
• Client Integration: Capability discovery for dynamic client configuration
• Real-time Updates: Status broadcasting for responsive client applications
• Performance Analysis: Metrics collection for capacity planning and optimization
• Security Monitoring: Authentication status tracking and security posture assessment
• Operational Dashboard: Comprehensive status information for administrative interfaces

🚀 INTEGRATION PATTERNS:
• Polling Pattern: Regular health_check calls for basic monitoring
• Discovery Pattern: server_capabilities for dynamic feature detection
• Diagnostic Pattern: connection_health for troubleshooting workflows
• Dashboard Pattern: status for comprehensive operational views
• Event-Driven Pattern: register_updates for real-time client synchronization
• Hybrid Pattern: Combining multiple actions for complete monitoring solutions

🛡️ RELIABILITY FEATURES:
• Graceful degradation under high load
• Comprehensive error reporting with actionable guidance
• Automatic retry logic for transient failures
• Circuit breaker patterns for dependency protection
• Health check caching for performance optimization
• Detailed logging for audit trails and debugging
"""

# Parameter descriptions for the manage_connection tool
MANAGE_CONNECTION_PARAMETERS = {
    "action": "Connection management action to perform. Valid actions: 'health_check' (basic server health), 'server_capabilities' (feature discovery), 'connection_health' (diagnostics), 'status' (comprehensive monitoring), 'register_updates' (real-time notifications). Each action provides specific operational insights and monitoring capabilities. (string)",
    
    "include_details": "Whether to include detailed information in responses. When true, provides comprehensive data including metrics, configuration details, and diagnostic information. When false, returns minimal essential information for reduced bandwidth and faster responses. Default: true (boolean)",
    
    "connection_id": "Specific connection identifier for targeted diagnostics. Used with 'connection_health' action to analyze individual connection performance and health. When not provided, analyzes overall connection pool health. Useful for isolating connection-specific issues. (string)",
    
    "session_id": "Client session identifier for update registration. Required for 'register_updates' action to establish real-time notification delivery. Should be unique per client session and maintained throughout the connection lifecycle. Used for update routing and session management. (string)",
    
    "client_info": "Optional client metadata for registration customization. JSON object containing client identification, capabilities, preferences, and filtering criteria. Used to customize update delivery, prioritize notifications, and provide client-specific monitoring. Supports fields like client_type, version, features, and notification_preferences. (object)"
}