"""
🔗 UNIFIED CONNECTION MANAGEMENT ENGINE - Complete connection, health, and monitoring operations

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

# 🤖 AI-OPTIMIZED DECISION TREES AND RULES

HEALTH_CHECK_DECISION_TREE = """
🌲 HEALTH CHECK ACTION SELECTION:

IF system_startup:
    action = "health_check"
    include_details = True  # Get full startup diagnostics
    
ELIF need_capabilities:
    action = "server_capabilities"
    include_details = True  # Discover all features
    
ELIF monitoring_connections:
    action = "connection_health"
    connection_id = specific_connection_id if available else None
    include_details = True  # Get diagnostic details
    
ELIF need_full_status:
    action = "status"
    include_details = True  # Get comprehensive metrics
    
ELIF real_time_updates:
    action = "register_updates"
    session_id = unique_session_identifier
    client_info = {
        "client_type": "monitoring_dashboard",
        "notification_preferences": ["health", "performance", "errors"]
    }
"""

RESPONSE_INTERPRETATION_RULES = """
📏 RESPONSE ANALYSIS GUIDELINES:

🚦 HEALTH CHECK THRESHOLDS:
• Healthy: status = "ok", all services operational
• Warning: status = "degraded", some services impacted (>80% operational)
• Critical: status = "critical", major services down (<50% operational)
• Down: status = "error", server not responding

🎛️ CAPABILITY FEATURE FLAGS:
• core_features: Essential system functions (must have all)
• security_features: Authentication and authorization capabilities
• monitoring_features: Observability and metrics collection
• integration_features: External system connectivity options

🔬 CONNECTION DIAGNOSTICS PATTERNS:
• Latency Issues: response_time > 1000ms indicates performance problems
• Connection Drops: error_rate > 5% suggests stability issues
• Resource Exhaustion: connection_count near max_connections
• Authentication Problems: auth_failures > 0 requires investigation

📊 STATUS METRIC ANALYSIS:
• Server Load: cpu_usage > 80% or memory_usage > 90% indicates stress
• Connection Pool: active_connections / max_connections > 0.8 is high usage
• Error Rates: error_count / total_requests > 0.01 needs attention
• Performance: avg_response_time trending up suggests degradation
"""

MONITORING_PATTERNS = """
🔄 STANDARD MONITORING WORKFLOWS:

📍 STARTUP SEQUENCE:
1. health_check → Verify server is responsive
2. server_capabilities → Discover available features
3. status → Get baseline metrics
4. register_updates → Subscribe to real-time changes

⏰ PERIODIC HEALTH CHECKS:
• Frequency: Every 30 seconds for critical systems
• Pattern: health_check with include_details=false for efficiency
• Escalation: If 3 consecutive failures, switch to diagnostic mode

📈 PERFORMANCE MONITORING:
• Baseline: Capture initial status metrics
• Tracking: Monitor trends in response_time, error_rate, resource_usage
• Alerting: Trigger when metrics exceed thresholds for 5+ minutes
• Analysis: Use connection_health for deep diagnostics

🚨 ERROR DETECTION AND RECOVERY:
• Detection: Monitor error_count and error_types in status
• Diagnosis: Use connection_health with specific connection_id
• Recovery: Implement exponential backoff for retries
• Reporting: Log patterns for post-incident analysis
"""

INTEGRATION_WORKFLOWS = """
🔗 CROSS-TOOL INTEGRATION PATTERNS:

🏗️ SYSTEM READINESS VALIDATION:
BEFORE any_tool_operation:
    health = manage_connection(action="health_check")
    IF health.status != "ok":
        WAIT_AND_RETRY or FAIL_FAST

🔍 DEPENDENCY CHECKING:
BEFORE task_operations:
    capabilities = manage_connection(action="server_capabilities")
    IF "task_management" not in capabilities.core_features:
        HANDLE_MISSING_DEPENDENCY

🎯 COORDINATED WORKFLOWS:
1. Connection Health → Task Management:
   • Verify connection healthy before creating tasks
   • Check authentication status for user context
   
2. Status Monitoring → Agent Switching:
   • Monitor system load before intensive operations
   • Defer non-critical work during high load
   
3. Real-time Updates → Multi-client Sync:
   • Register all clients for consistent state
   • Broadcast critical status changes immediately

🛡️ RESILIENCE PATTERNS:
• Circuit Breaker: After 3 health_check failures, stop operations
• Bulkhead: Isolate connection issues from affecting other tools
• Timeout: Set max wait of 5 seconds for health checks
• Fallback: Use cached capabilities if server temporarily unavailable
"""

# 🎯 PRACTICAL EXAMPLES FOR AI AGENTS

CONNECTION_EXAMPLES = """
💡 REAL-WORLD USAGE EXAMPLES:

1. SYSTEM STARTUP CHECK:
   response = manage_connection(
       action="health_check",
       include_details=True
   )
   IF response.status == "ok" AND response.auth_enabled:
       proceed_with_initialization()

2. CAPABILITY-BASED FEATURE TOGGLE:
   caps = manage_connection(action="server_capabilities")
   IF "advanced_search" in caps.features:
       use_advanced_search()
   ELSE:
       use_basic_search()

3. CONNECTION TROUBLESHOOTING:
   health = manage_connection(
       action="connection_health",
       connection_id=problematic_connection_id
   )
   FOR issue in health.diagnostics.issues:
       apply_remediation(issue.recommendation)

4. DASHBOARD MONITORING:
   status = manage_connection(action="status")
   update_dashboard({
       "server_health": status.overall_health,
       "active_users": status.connection_stats.active_count,
       "performance": status.metrics.avg_response_time
   })

5. REAL-TIME CLIENT SYNC:
   manage_connection(
       action="register_updates",
       session_id=client.session_id,
       client_info={
           "client_type": "web_dashboard",
           "interested_events": ["health_change", "new_connection"]
       }
   )
"""

# 🤖 AI AGENT BEHAVIORAL RULES

AI_BEHAVIORAL_RULES = """
🧠 INTELLIGENT CONNECTION MANAGEMENT RULES:

1. PROACTIVE MONITORING:
   • Always check health before critical operations
   • Cache capabilities for 5 minutes to reduce load
   • Subscribe to updates for long-running sessions

2. FAILURE HANDLING:
   • Implement exponential backoff: 1s, 2s, 4s, 8s...
   • Log all failures with context for analysis
   • Fallback to cached data when appropriate

3. PERFORMANCE OPTIMIZATION:
   • Use include_details=false for routine checks
   • Batch status requests when possible
   • Monitor trends, not just absolute values

4. SECURITY AWARENESS:
   • Validate auth status before sensitive operations
   • Check rate limits in capabilities
   • Report suspicious patterns immediately

5. USER EXPERIENCE:
   • Provide meaningful error messages
   • Suggest remediation steps for issues
   • Maintain service during degraded states
"""