package server

import (
	"fmt"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// SecureConnectionContext is the minimal stand-in for fastmcp.server.context.Context
// used by the secure connection tool. context.py IS ported (server/context.go);
// UserID mirrors getattr(ctx, "user_id", <default>), where a nil
// result means the attribute was absent. A nil interface means Python None.
type SecureConnectionContext interface {
	UserID() *string
}

// secureConnectionUserID mirrors
// `getattr(ctx, "user_id", default) if ctx else default`.
func secureConnectionUserID(ctx SecureConnectionContext, def string) *string {
	if ctx == nil {
		d := def
		return &d
	}
	uid := ctx.UserID()
	if uid == nil {
		d := def
		return &d
	}
	return uid
}

// SecureConnectionCheck mirrors secure_connection_check(ctx, access_level, **kwargs).
// The response is an OrderedMap in Python key order.
func SecureConnectionCheck(ctx SecureConnectionContext, accessLevel string, kwargs ...any) (out *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			out = entities.NewOrderedMap[any]()
			out.Set("success", false)
			out.Set("status", "error")
			out.Set("error", "Service temporarily unavailable")
			out.Set("timestamp", 0)
		}
	}()

	switch accessLevel {
	case "client":
		return ClientHealthCheck()

	case "authenticated":
		userID := secureConnectionUserID(ctx, "authenticated_user")
		return SecureHealthCheck(userID, false, false, nil)

	case "admin":
		userID := secureConnectionUserID(ctx, "admin_user")
		return SecureHealthCheck(userID, true, true, nil)

	default:
		out = entities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error", fmt.Sprintf("Invalid access level: %s", accessLevel))
		out.Set("valid_levels", []any{"client", "authenticated", "admin"})
		out.Set("timestamp", 0)
		return out
	}
}

// SecureHealthCheckTool mirrors the inner secure_health_check_tool returned from
// register_secure_connection_tool. The FastMCP @server.tool registration itself
// has no Go meaning and is not ported.
func SecureHealthCheckTool(ctx SecureConnectionContext, accessLevel string) (out string) {
	defer func() {
		if r := recover(); r != nil {
			out = "❌ Health Check Error\n\nService temporarily unavailable"
		}
	}()

	result := SecureConnectionCheck(ctx, accessLevel)

	if value_objects.PyTruthy(srvGet(result, "success", nil)) {
		return FormatSecureHealthResponse(result, accessLevel)
	}
	return "❌ Health Check Failed\n\nError: " +
		value_objects.PyStr(srvGet(result, "error", "Unknown error"))
}

// FormatSecureHealthResponse mirrors _format_secure_health_response.
func FormatSecureHealthResponse(result *entities.OrderedMap[any], accessLevel string) string {
	status := value_objects.PyStr(srvGet(result, "status", nil))
	statusEmoji := "🔴"
	if status == "healthy" {
		statusEmoji = "🟢"
	}
	timestamp := value_objects.PyStr(srvGet(result, "timestamp", nil))

	if accessLevel == "client" {
		return statusEmoji + " Server Status: " + strings.ToUpper(status) +
			"\n\nTimestamp: " + timestamp +
			"\n\nThis is a client-safe health check with minimal information disclosure."
	}

	uptimeHours := srvFloat(srvGet(result, "uptime_seconds", 0)) / 3600
	serverName := value_objects.PyStr(srvGet(result, "server_name", "Unknown"))
	version := value_objects.PyStr(srvGet(result, "version", "Unknown"))

	var b strings.Builder

	if accessLevel == "authenticated" {
		b.WriteString(statusEmoji + " Server Health Check - Authenticated View")
		b.WriteString("\n\n**Server Information:**")
		b.WriteString("\n• Name: " + serverName)
		b.WriteString("\n• Version: " + version)
		b.WriteString("\n• Status: " + strings.ToUpper(status))
		b.WriteString(fmt.Sprintf("\n• Uptime: %.1f hours", uptimeHours))
		b.WriteString("\n• Active Connections: " + value_objects.PyStr(srvGet(result, "active_connections", 0)))

		if restartCount := srvInt(srvGet(result, "restart_count", 0)); restartCount > 0 {
			b.WriteString("\n• Restart Count: " + value_objects.PyStr(restartCount))
			b.WriteString("\n• Notice: " + value_objects.PyStr(srvGet(result, "restart_notice", "")))
		}

		b.WriteString("\n\nTimestamp: " + timestamp)
		return b.String()
	}

	// admin
	b.WriteString(statusEmoji + " Server Health Check - Administrative View")
	b.WriteString("\n\n**Server Information:**")
	b.WriteString("\n• Name: " + serverName)
	b.WriteString("\n• Version: " + version)
	b.WriteString("\n• Status: " + strings.ToUpper(status))
	b.WriteString(fmt.Sprintf("\n• Uptime: %.1f hours", uptimeHours))

	auth := srvGet(result, "authentication", nil)
	b.WriteString("\n\n**Authentication:**")
	b.WriteString("\n• Enabled: " + value_objects.PyStr(srvGet(auth, "enabled", false)))
	b.WriteString("\n• MVP Mode: " + value_objects.PyStr(srvGet(auth, "mvp_mode", false)))

	taskMgmt := srvGet(result, "task_management", nil)
	b.WriteString("\n\n**Task Management:**")
	b.WriteString("\n• Enabled: " + value_objects.PyStr(srvGet(taskMgmt, "task_management_enabled", false)))
	b.WriteString("\n• Tools Count: " + value_objects.PyStr(srvGet(taskMgmt, "enabled_tools_count", 0)) +
		"/" + value_objects.PyStr(srvGet(taskMgmt, "total_tools_count", 0)))

	connections := srvGet(result, "connections", nil)
	b.WriteString("\n\n**Connections:**")
	b.WriteString("\n• Active: " + value_objects.PyStr(srvGet(connections, "active_connections", 0)))
	b.WriteString("\n• Restart Count: " + value_objects.PyStr(srvGet(connections, "server_restart_count", 0)))
	b.WriteString("\n• Recommended Action: " + value_objects.PyStr(srvGet(connections, "recommended_action", "unknown")))

	broadcasting := srvGet(connections, "status_broadcasting", nil)
	b.WriteString("\n• Broadcasting Active: " + value_objects.PyStr(srvGet(broadcasting, "active", false)))
	b.WriteString("\n• Registered Clients: " + value_objects.PyStr(srvGet(broadcasting, "registered_clients", 0)))

	env := srvGet(result, "environment", nil)
	if value_objects.PyTruthy(env) {
		b.WriteString("\n\n**Environment Configuration:**")
		b.WriteString("\n• Python Path: " + value_objects.PyStr(srvGet(env, "pythonpath", "not set")))
		b.WriteString("\n• Tasks JSON Path: " + value_objects.PyStr(srvGet(env, "tasks_json_path", "not set")))
		b.WriteString("\n• Projects File Path: " + value_objects.PyStr(srvGet(env, "projects_file_path", "not set")))
		b.WriteString("\n• Cursor Tools Disabled: " + value_objects.PyStr(srvGet(env, "cursor_tools_disabled", "false")))
		b.WriteString("\n• Supabase Configured: " + value_objects.PyStr(srvGet(env, "supabase_configured", false)))
	}

	securityCtx := srvGet(result, "security_context", nil)
	b.WriteString("\n\n**Security Context:**")
	b.WriteString("\n• Access Level: " + value_objects.PyStr(srvGet(securityCtx, "access_level", "unknown")))
	b.WriteString("\n• User ID: " + value_objects.PyStr(srvGet(securityCtx, "user_id", "unknown")))
	b.WriteString("\n• Environment: " + value_objects.PyStr(srvGet(securityCtx, "environment", "unknown")))

	b.WriteString("\n\nTimestamp: " + timestamp)
	return b.String()
}
