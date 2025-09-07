# manage_connection - Connection Management API Documentation

## Overview

The `manage_connection` tool provides comprehensive system health monitoring, diagnostics, connection management, and operational status tracking for the DhafnckMCP platform. It serves as the primary interface for system reliability, performance monitoring, and troubleshooting.

## Base Information

- **Tool Name**: `manage_connection`
- **Controller**: `ConnectionMCPController`  
- **Module**: `fastmcp.connection_management.interface.mcp_controllers.connection_mcp_controller`
- **Authentication**: Optional (some operations require authentication, others are public)
- **Real-time Monitoring**: ✅ Live system health and performance metrics
- **Multi-Component Health**: ✅ Database, cache, external services, and agent monitoring

## Parameters Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "required": true,
      "description": "Connection management operation to perform"
    },
    "component": {
      "type": "string",
      "description": "[OPTIONAL] Specific component to check: 'database', 'cache', 'agents', 'external_services'"
    },
    "include_details": {
      "type": "string",
      "description": "[OPTIONAL] Include detailed diagnostics: 'true', 'false'"
    },
    "timeout_seconds": {
      "type": "string", 
      "description": "[OPTIONAL] Health check timeout in seconds"
    },
    "fix_issues": {
      "type": "string",
      "description": "[OPTIONAL] Attempt to fix detected issues: 'true', 'false'"
    },
    "user_id": {
      "type": "string",
      "description": "[OPTIONAL] User identifier for authenticated operations"
    }
  },
  "required": ["action"]
}
```

## Available Actions

### Core Health Monitoring

#### `health_check` - Comprehensive System Health

Performs a comprehensive health check across all system components with detailed diagnostics.

**Required Parameters:**
- `action`: "health_check"

**Optional Parameters:**
- `component`: Specific component to focus on
- `include_details`: Include detailed diagnostics
- `timeout_seconds`: Check timeout (default: 30)

**Example Request:**
```json
{
  "action": "health_check",
  "include_details": "true",
  "timeout_seconds": "60"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "health_check",
  "timestamp": "2025-01-27T15:30:00Z",
  "overall_health": {
    "status": "healthy",
    "score": 92,
    "uptime": "7d 14h 32m",
    "last_incident": "2025-01-20T03:15:00Z"
  },
  "components": {
    "database": {
      "status": "healthy",
      "response_time_ms": 12,
      "connection_pool": {
        "active_connections": 8,
        "max_connections": 100,
        "utilization": 8
      },
      "performance": {
        "queries_per_second": 142,
        "avg_query_time_ms": 8.3,
        "slow_queries": 0
      },
      "storage": {
        "disk_usage_gb": 2.7,
        "disk_available_gb": 47.3,
        "utilization_percent": 5.4
      }
    },
    "cache": {
      "status": "healthy",
      "type": "Redis",
      "response_time_ms": 2,
      "memory_usage": {
        "used_mb": 245,
        "max_mb": 2048,
        "utilization_percent": 12
      },
      "performance": {
        "hit_rate": 0.89,
        "operations_per_second": 1247,
        "connected_clients": 12
      }
    },
    "agents": {
      "status": "healthy",
      "total_agents": 15,
      "available_agents": 12,
      "busy_agents": 3,
      "error_agents": 0,
      "average_response_time_ms": 340,
      "active_executions": 8,
      "queue_length": 2
    },
    "external_services": {
      "status": "degraded",
      "services": {
        "auth_service": {
          "status": "healthy",
          "url": "https://auth.example.com",
          "response_time_ms": 145,
          "last_check": "2025-01-27T15:29:45Z"
        },
        "notification_service": {
          "status": "degraded", 
          "url": "https://notifications.example.com",
          "response_time_ms": 2100,
          "error": "High response time detected",
          "last_check": "2025-01-27T15:29:50Z"
        },
        "storage_service": {
          "status": "healthy",
          "url": "https://storage.example.com", 
          "response_time_ms": 89,
          "last_check": "2025-01-27T15:29:52Z"
        }
      }
    },
    "system_resources": {
      "status": "healthy",
      "cpu_usage_percent": 23,
      "memory_usage_percent": 67,
      "disk_usage_percent": 42,
      "network_io_mbps": 45,
      "load_average": [1.2, 1.4, 1.1]
    }
  },
  "alerts": [
    {
      "level": "warning",
      "component": "external_services",
      "message": "Notification service response time above threshold (2.1s > 1.0s)",
      "timestamp": "2025-01-27T15:29:50Z",
      "action_required": "Monitor service performance and consider failover"
    }
  ],
  "recommendations": [
    "Consider adding more Redis memory for better cache performance",
    "Monitor notification service performance and implement retry logic",
    "Database performance is excellent, no action needed"
  ]
}
```

#### `ping` - Quick Connectivity Test

Performs a lightweight connectivity test to verify basic system responsiveness.

**Required Parameters:**
- `action`: "ping"

**Example Request:**
```json
{
  "action": "ping"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "ping",
  "timestamp": "2025-01-27T15:30:15Z",
  "response_time_ms": 3,
  "server_info": {
    "version": "1.2.3",
    "environment": "production",
    "region": "us-west-2",
    "instance_id": "i-0123456789abcdef0"
  },
  "status": "ok"
}
```

### Component-Specific Health Checks

#### `database_health` - Database Health Check

Performs detailed database health assessment including performance metrics.

**Required Parameters:**
- `action`: "database_health"

**Optional Parameters:**
- `include_details`: Include query performance details
- `fix_issues`: Attempt to fix detected issues

**Example Response:**
```json
{
  "success": true,
  "operation": "database_health",
  "database": {
    "status": "healthy",
    "type": "PostgreSQL",
    "version": "14.2",
    "connection": {
      "status": "connected",
      "response_time_ms": 8,
      "pool_status": "optimal"
    },
    "performance": {
      "active_connections": 12,
      "max_connections": 100,
      "queries_per_second": 156,
      "avg_query_time_ms": 6.7,
      "cache_hit_ratio": 0.94,
      "index_usage": 0.87
    },
    "storage": {
      "total_size_gb": 50.0,
      "used_size_gb": 3.2,
      "available_gb": 46.8,
      "growth_rate_gb_per_day": 0.15
    },
    "maintenance": {
      "last_vacuum": "2025-01-26T02:00:00Z",
      "last_analyze": "2025-01-26T02:15:00Z", 
      "next_maintenance": "2025-01-28T02:00:00Z"
    },
    "slow_queries": [],
    "issues": []
  }
}
```

#### `cache_health` - Cache System Health

Monitors cache system performance and memory usage.

**Required Parameters:**
- `action`: "cache_health"

#### `agent_health` - Agent System Status

Checks the health and availability of all registered agents.

**Required Parameters:**
- `action`: "agent_health"

**Example Response:**
```json
{
  "success": true,
  "operation": "agent_health",
  "agents": {
    "overall_status": "healthy",
    "summary": {
      "total_agents": 15,
      "healthy": 14,
      "degraded": 1,
      "error": 0,
      "offline": 0
    },
    "performance": {
      "average_response_time_ms": 280,
      "total_executions_today": 147,
      "success_rate": 0.96,
      "queue_length": 3
    },
    "agent_details": [
      {
        "id": "@coding_agent",
        "status": "healthy",
        "current_load": 3,
        "max_capacity": 5,
        "response_time_ms": 245,
        "success_rate": 0.97,
        "last_activity": "2025-01-27T15:25:00Z"
      },
      {
        "id": "@ui_designer_agent",
        "status": "degraded",
        "current_load": 2,
        "max_capacity": 3,
        "response_time_ms": 890,
        "success_rate": 0.89,
        "last_activity": "2025-01-27T15:20:00Z",
        "issue": "Response time above normal threshold"
      }
    ],
    "capacity_utilization": {
      "total_capacity": 67,
      "used_capacity": 23,
      "utilization_percent": 34,
      "projected_peak_hour": "14:00-15:00"
    }
  }
}
```

### Diagnostic Operations

#### `diagnose` - Comprehensive System Diagnostics

Performs deep diagnostic analysis to identify potential issues and performance bottlenecks.

**Required Parameters:**
- `action`: "diagnose"

**Optional Parameters:**
- `component`: Focus on specific component
- `severity`: Minimum issue severity to report
- `fix_issues`: Attempt automatic remediation

**Example Request:**
```json
{
  "action": "diagnose",
  "component": "all",
  "fix_issues": "true"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "diagnose",
  "timestamp": "2025-01-27T15:35:00Z",
  "diagnostics": {
    "issues_found": 3,
    "issues_fixed": 1,
    "warnings": 2,
    "recommendations": 5
  },
  "issues": [
    {
      "id": "DB001",
      "severity": "medium",
      "component": "database",
      "title": "Unused indexes detected",
      "description": "3 indexes are no longer being used and consuming storage",
      "impact": "Minor performance impact, increased storage usage",
      "fix_available": true,
      "fix_applied": true,
      "resolution": "Dropped unused indexes: idx_old_user_email, idx_legacy_task_status, idx_unused_branch"
    },
    {
      "id": "EXT001", 
      "severity": "high",
      "component": "external_services",
      "title": "Notification service degraded performance",
      "description": "Response times consistently above 2 seconds",
      "impact": "User notification delays, potential timeout errors",
      "fix_available": false,
      "recommendations": [
        "Implement retry logic with exponential backoff",
        "Add notification queue for async processing",
        "Contact service provider about performance issues"
      ]
    },
    {
      "id": "AGT001",
      "severity": "low", 
      "component": "agents",
      "title": "Agent load imbalance detected",
      "description": "@coding_agent is handling 65% of all coding tasks",
      "impact": "Potential bottleneck during peak usage",
      "fix_available": true,
      "recommendations": [
        "Enable automatic load balancing",
        "Consider adding additional coding agents",
        "Implement task distribution algorithms"
      ]
    }
  ],
  "performance_analysis": {
    "bottlenecks": [
      {
        "component": "external_services",
        "metric": "notification_response_time",
        "current_value": "2.1s",
        "threshold": "1.0s",
        "severity": "medium"
      }
    ],
    "trends": {
      "database_performance": "stable",
      "cache_efficiency": "improving",
      "agent_utilization": "increasing",
      "response_times": "stable"
    }
  },
  "system_optimization": {
    "suggestions": [
      "Enable database query plan caching",
      "Increase Redis memory allocation by 50%", 
      "Configure agent auto-scaling rules",
      "Implement circuit breakers for external services",
      "Add monitoring alerts for response time thresholds"
    ],
    "estimated_improvements": {
      "response_time": "15-25% faster",
      "reliability": "99.9% uptime target achievable", 
      "capacity": "40% more concurrent users"
    }
  }
}
```

#### `fix_issues` - Automatic Issue Resolution

Attempts to automatically resolve detected system issues.

**Required Parameters:**
- `action`: "fix_issues"

**Optional Parameters:**
- `issue_ids`: Specific issues to fix (array as JSON string)
- `component`: Limit fixes to specific component
- `dry_run`: Simulate fixes without applying them

#### `system_metrics` - Detailed System Metrics

Retrieves comprehensive system performance and usage metrics.

**Required Parameters:**
- `action`: "system_metrics"

**Optional Parameters:**
- `time_range`: Metrics time range ("1h", "24h", "7d", "30d")
- `components`: Specific components to include

### Connection Testing

#### `test_connections` - Test All System Connections

Tests connectivity to all external dependencies and internal services.

**Required Parameters:**
- `action`: "test_connections"

**Optional Parameters:**
- `services`: Specific services to test (JSON array)
- `timeout_seconds`: Connection timeout per service

**Example Response:**
```json
{
  "success": true,
  "operation": "test_connections",
  "timestamp": "2025-01-27T15:40:00Z",
  "results": {
    "database": {
      "status": "connected",
      "response_time_ms": 11,
      "details": "PostgreSQL connection pool healthy"
    },
    "cache": {
      "status": "connected", 
      "response_time_ms": 3,
      "details": "Redis cluster responding normally"
    },
    "auth_service": {
      "status": "connected",
      "response_time_ms": 134,
      "details": "JWT validation endpoint responsive"
    },
    "notification_service": {
      "status": "degraded",
      "response_time_ms": 2200,
      "details": "Service responding but slower than expected",
      "warning": "Consider implementing fallback mechanism"
    },
    "file_storage": {
      "status": "connected",
      "response_time_ms": 67,
      "details": "S3-compatible storage accessible"
    },
    "monitoring": {
      "status": "connected",
      "response_time_ms": 89, 
      "details": "Metrics collection active"
    }
  },
  "summary": {
    "total_services": 6,
    "connected": 5,
    "degraded": 1,
    "failed": 0,
    "average_response_time_ms": 384
  }
}
```

### Monitoring and Alerting

#### `get_alerts` - Retrieve Active Alerts

Gets all active system alerts and warnings.

**Required Parameters:**
- `action`: "get_alerts"

**Optional Parameters:**
- `severity`: Filter by alert severity
- `component`: Filter by component
- `limit`: Maximum alerts to return

#### `clear_alert` - Clear Resolved Alert

Marks an alert as resolved and clears it from active alerts.

**Required Parameters:**
- `action`: "clear_alert"
- `alert_id`: Alert identifier

#### `set_monitoring` - Configure Monitoring

Configures system monitoring parameters and thresholds.

**Required Parameters:**
- `action`: "set_monitoring"
- `config`: Monitoring configuration as JSON

## Health Status Levels

### Overall System Health
- **Healthy** (90-100): All components operating optimally
- **Degraded** (70-89): Some performance issues but system functional
- **Warning** (50-69): Significant issues requiring attention
- **Critical** (25-49): Major problems affecting system operation
- **Down** (0-24): System unavailable or severely impaired

### Component Health Indicators
- **🟢 Healthy**: Operating within normal parameters
- **🟡 Degraded**: Performance issues but functional
- **🔴 Error**: Component failures or severe issues
- **⚫ Offline**: Component unavailable or unreachable

### Alert Severity Levels
- **Critical**: Immediate attention required, system impact
- **High**: Important issue affecting user experience  
- **Medium**: Performance degradation, monitor closely
- **Low**: Minor issues, informational only

## Error Handling

### System Errors
- `HEALTH_CHECK_FAILED`: Unable to complete health assessment
- `COMPONENT_UNAVAILABLE`: Specific component not responding
- `TIMEOUT_EXCEEDED`: Health check exceeded timeout limit
- `INSUFFICIENT_PERMISSIONS`: Operation requires elevated permissions
- `DIAGNOSTIC_FAILED`: Unable to complete diagnostic analysis

### Connection Errors
- `DATABASE_CONNECTION_FAILED`: Cannot connect to database
- `CACHE_CONNECTION_FAILED`: Cannot connect to cache system
- `EXTERNAL_SERVICE_UNAVAILABLE`: External service not responding
- `AGENT_COMMUNICATION_FAILED`: Cannot communicate with agents

### Example Error Response
```json
{
  "success": false,
  "error": "Database connection failed during health check",
  "error_code": "DATABASE_CONNECTION_FAILED",
  "operation": "health_check",
  "metadata": {
    "component": "database",
    "connection_string": "postgresql://***:***@localhost:5432/dhafnck_mcp",
    "timeout_seconds": 30,
    "last_successful_connection": "2025-01-27T14:20:00Z",
    "retry_attempts": 3,
    "suggested_actions": [
      "Check database service status",
      "Verify network connectivity",
      "Review connection pool configuration",
      "Check for database maintenance windows"
    ]
  }
}
```

## Monitoring Integration

### Real-time Metrics
- **Live Dashboard**: Real-time system health visualization
- **Metric Streaming**: WebSocket-based live metric updates  
- **Alert Notifications**: Instant notifications for critical issues
- **Performance Graphs**: Historical trend analysis and forecasting

### External Monitoring
- **Prometheus Integration**: Metrics export for external monitoring
- **Grafana Dashboards**: Pre-configured visualization dashboards
- **PagerDuty Integration**: Incident escalation and notification
- **Slack Notifications**: Team alert integration

### Health Check Scheduling
- **Automated Checks**: Regular health assessments every 5 minutes
- **Deep Diagnostics**: Comprehensive analysis every hour
- **Trend Analysis**: Performance trend evaluation daily
- **Capacity Planning**: Weekly capacity and growth analysis

## Best Practices

### Health Monitoring
1. **Regular Checks**: Monitor system health continuously
2. **Proactive Alerts**: Set up alerts before issues become critical
3. **Trend Analysis**: Watch for gradual performance degradation
4. **Capacity Planning**: Monitor growth trends for scaling decisions
5. **Documentation**: Keep runbooks updated for common issues

### Performance Optimization
- **Baseline Monitoring**: Establish performance baselines
- **Bottleneck Identification**: Regular diagnostic analysis
- **Resource Optimization**: Right-size system components
- **Caching Strategy**: Optimize cache hit rates and memory usage
- **Connection Pooling**: Proper database connection management

### Incident Response
- **Alert Escalation**: Clear escalation paths for different severity levels
- **Automated Remediation**: Implement fixes for common issues
- **Documentation**: Maintain incident response procedures
- **Post-Incident Review**: Learn from incidents to prevent recurrence
- **Recovery Testing**: Regularly test disaster recovery procedures

This connection management system provides comprehensive visibility into system health with proactive monitoring, automated diagnostics, and intelligent remediation capabilities.