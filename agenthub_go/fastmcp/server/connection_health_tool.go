package server

import (
	"fmt"
	"strings"
	"time"
	"unicode"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// HealthCheckSession is the minimal stand-in for fastmcp.server.context.Context
// used by the connection health tool. context.py is FastMCP/MCP-SDK specific and
// has no Go port; SessionID mirrors the Context.session_id property (nil = None).
type HealthCheckSession interface {
	SessionID() *string
}

func srvFloat(v any) float64 {
	if f, ok := value_objects.PyFloat(v); ok {
		return f
	}
	return 0
}

func sessionIDAny(sid *string) any {
	if sid == nil {
		return nil
	}
	return *sid
}

// pyTitle mirrors Python str.title() for the status strings used here.
func pyTitle(s string) string {
	var b strings.Builder
	prevCased := false
	for _, r := range s {
		cased := unicode.IsLetter(r)
		if cased {
			if prevCased {
				r = unicode.ToLower(r)
			} else {
				r = unicode.ToUpper(r)
			}
		}
		b.WriteRune(r)
		prevCased = cased
	}
	return b.String()
}

// ConnectionHealthCheck mirrors connection_health_check(ctx): it returns the
// health dict (OrderedMap in Python key order) and converts a Python
// `except Exception` into the error dict.
func ConnectionHealthCheck(ctx HealthCheckSession) (out *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			out = connectionHealthErrorDict(panicString(r))
		}
	}()

	connectionManager := GetConnectionManager()

	var sessionID *string
	if ctx != nil {
		sessionID = ctx.SessionID()
	}
	if sessionID != nil && *sessionID != "" {
		connectionManager.UpdateConnectionActivity(*sessionID)
	}

	connectionStats := connectionManager.GetConnectionStats()
	reconnectionInfo := connectionManager.GetReconnectionInfo()

	healthInfo := entities.NewOrderedMap[any]()
	healthInfo.Set("timestamp", value_objects.IsoFormatNaive(time.Now()))
	healthInfo.Set("current_session_id", sessionIDAny(sessionID))
	healthInfo.Set("server_status", "healthy")
	healthInfo.Set("connection_manager", connectionStats)
	healthInfo.Set("reconnection_info", reconnectionInfo)

	connections := srvGet(connectionStats, "connections", nil)
	serverInfo := srvGet(connectionStats, "server_info", nil)
	activeConnections := srvInt(srvGet(connections, "active_connections", 0))
	restartCount := srvInt(srvGet(serverInfo, "restart_count", 0))

	switch {
	case restartCount > 0 && activeConnections == 0:
		healthInfo.Set("server_status", "restarted_no_clients")
		healthInfo.Set("recommendation", "Server was restarted. MCP clients should reconnect.")
	case restartCount > 0:
		healthInfo.Set("server_status", "restarted_with_clients")
		healthInfo.Set("recommendation", "Server was restarted but has active connections.")
	case activeConnections == 0:
		healthInfo.Set("server_status", "no_clients")
		healthInfo.Set("recommendation", "No active MCP clients connected.")
	default:
		healthInfo.Set("recommendation", "All connections healthy.")
	}

	warnings := []any{}
	if restartCount > 0 {
		warnings = append(warnings, fmt.Sprintf(
			"Server has been restarted %d time(s). MCP clients may need to reconnect.", restartCount))
	}
	staleConnections := srvInt(srvGet(connections, "stale_connections", 0))
	if staleConnections > 0 {
		warnings = append(warnings, fmt.Sprintf("%d stale connections detected.", staleConnections))
	}
	if activeConnections == 0 && sessionID != nil && *sessionID != "" {
		warnings = append(warnings, "No active connections detected, but current session exists. Connection state may be inconsistent.")
	}
	if len(warnings) > 0 {
		healthInfo.Set("warnings", warnings)
	}

	troubleshooting := entities.NewOrderedMap[any]()
	troubleshooting.Set("cursor_reconnection", []any{
		"1. Toggle MCP server off in Cursor settings",
		"2. Wait 2-3 seconds",
		"3. Toggle MCP server back on",
		"4. Check if tools are available again",
	})
	troubleshooting.Set("docker_rebuild", []any{
		"1. After rebuilding Docker containers",
		"2. The MCP server gets a new container ID",
		"3. Cursor's HTTP connection becomes stale",
		"4. Use the toggle method above to reconnect",
	})
	troubleshooting.Set("alternative_methods", []any{
		"1. Restart Cursor completely (slower but reliable)",
		"2. Use Cursor Developer Tools to check MCP connection status",
		"3. Check Docker container status: docker ps",
		"4. Verify server health: curl http://localhost:8000/health",
	})
	healthInfo.Set("troubleshooting", troubleshooting)

	return healthInfo
}

func panicString(r any) string {
	if err, ok := r.(error); ok {
		return err.Error()
	}
	return value_objects.PyStr(r)
}

func connectionHealthErrorDict(message string) *entities.OrderedMap[any] {
	om := entities.NewOrderedMap[any]()
	om.Set("timestamp", value_objects.IsoFormatNaive(time.Now()))
	om.Set("server_status", "error")
	om.Set("error", message)
	om.Set("recommendation", "Connection health check failed. Check server logs for details.")
	troubleshooting := entities.NewOrderedMap[any]()
	troubleshooting.Set("immediate_steps", []any{
		"1. Check if Docker container is running: docker ps",
		"2. Check server logs: docker logs agenthub-server",
		"3. Verify server health: curl http://localhost:8000/health",
		"4. Restart MCP server if needed",
	})
	om.Set("troubleshooting", troubleshooting)
	return om
}

// FormatConnectionHealth mirrors the string built by the inner
// connection_health_tool returned from register_connection_health_tool. The
// FastMCP @server.tool registration itself has no Go meaning and is not ported.
func FormatConnectionHealth(healthInfo *entities.OrderedMap[any]) string {
	statusEmoji := map[string]string{
		"healthy":                "✅",
		"restarted_no_clients":   "🔄",
		"restarted_with_clients": "⚠️",
		"no_clients":             "📡",
		"error":                  "🚨",
	}
	emoji := "❓"
	if e, ok := statusEmoji[value_objects.PyStr(srvGet(healthInfo, "server_status", "error"))]; ok {
		emoji = e
	}
	status := pyTitle(strings.ReplaceAll(
		value_objects.PyStr(srvGet(healthInfo, "server_status", "unknown")), "_", " "))

	var b strings.Builder
	b.WriteString(emoji + " **Connection Health Status: " + status + "**\n\n")

	b.WriteString("**Current Session:**\n")
	b.WriteString("- Session ID: " + value_objects.PyStr(srvGet(healthInfo, "current_session_id", "none")) + "\n")
	b.WriteString("- Timestamp: " + value_objects.PyStr(srvGet(healthInfo, "timestamp", "unknown")) + "\n\n")

	serverInfo := srvGet(srvGet(healthInfo, "connection_manager", nil), "server_info", nil)
	b.WriteString("**Server Information:**\n")
	b.WriteString(fmt.Sprintf("- Uptime: %.1f seconds\n", srvFloat(srvGet(serverInfo, "uptime_seconds", 0))))
	b.WriteString("- Restart Count: " + value_objects.PyStr(srvGet(serverInfo, "restart_count", 0)) + "\n")
	b.WriteString("- Start Time: " + value_objects.PyStr(srvGet(serverInfo, "start_time", "unknown")) + "\n\n")

	connections := srvGet(srvGet(healthInfo, "connection_manager", nil), "connections", nil)
	b.WriteString("**Connection Statistics:**\n")
	b.WriteString("- Active Connections: " + value_objects.PyStr(srvGet(connections, "active_connections", 0)) + "\n")
	b.WriteString("- Total Registered: " + value_objects.PyStr(srvGet(connections, "total_registered", 0)) + "\n")
	b.WriteString("- Stale Connections: " + value_objects.PyStr(srvGet(connections, "stale_connections", 0)) + "\n\n")

	activeClients := srvGet(srvGet(healthInfo, "connection_manager", nil), "active_clients", []any{})
	if list, ok := activeClients.([]any); ok && len(list) > 0 {
		b.WriteString("**Active Clients:**\n")
		for _, client := range list {
			b.WriteString("- " + value_objects.PyStr(srvGet(client, "client_name", "unknown")) +
				" (v" + value_objects.PyStr(srvGet(client, "client_version", "?")) + ")\n")
			b.WriteString(fmt.Sprintf("  Connected: %.1fs ago\n", srvFloat(srvGet(client, "connection_age_seconds", 0))))
			b.WriteString("  Health Checks: " + value_objects.PyStr(srvGet(client, "health_checks", 0)) + "\n")
		}
		b.WriteString("\n")
	}

	if recommendation := srvGet(healthInfo, "recommendation", nil); recommendation != nil && value_objects.PyTruthy(recommendation) {
		b.WriteString("**💡 Recommendation:**\n" + value_objects.PyStr(recommendation) + "\n\n")
	}

	if warnings := srvGet(healthInfo, "warnings", nil); warnings != nil {
		if list, ok := warnings.([]any); ok && len(list) > 0 {
			b.WriteString("**⚠️ Warnings:**\n")
			for _, warning := range list {
				b.WriteString("- " + value_objects.PyStr(warning) + "\n")
			}
			b.WriteString("\n")
		}
	}

	troubleshooting := srvGet(healthInfo, "troubleshooting", nil)

	if steps := stepList(troubleshooting, "cursor_reconnection"); steps != nil {
		b.WriteString("**🔄 Quick Cursor Reconnection (Recommended):**\n")
		for _, step := range steps {
			b.WriteString(value_objects.PyStr(step) + "\n")
		}
		b.WriteString("\n")
	}
	if steps := stepList(troubleshooting, "docker_rebuild"); steps != nil {
		b.WriteString("**🐳 After Docker Rebuild:**\n")
		for _, step := range steps {
			b.WriteString(value_objects.PyStr(step) + "\n")
		}
		b.WriteString("\n")
	}
	if steps := stepList(troubleshooting, "alternative_methods"); steps != nil {
		b.WriteString("**🛠️ Alternative Methods:**\n")
		for _, step := range steps {
			b.WriteString(value_objects.PyStr(step) + "\n")
		}
		b.WriteString("\n")
	}
	if steps := stepList(troubleshooting, "immediate_steps"); steps != nil {
		b.WriteString("**🚨 Immediate Troubleshooting:**\n")
		for _, step := range steps {
			b.WriteString(value_objects.PyStr(step) + "\n")
		}
		b.WriteString("\n")
	}

	reconnectionInfo := srvGet(healthInfo, "reconnection_info", nil)
	if value_objects.PyStr(srvGet(reconnectionInfo, "recommended_action", nil)) == "reconnect" {
		b.WriteString("**🔗 Reconnection Required:**\n")
		b.WriteString("Server was restarted. Please use the quick reconnection steps above.\n\n")
	}

	if errValue := srvGet(healthInfo, "error", nil); errValue != nil && value_objects.PyTruthy(errValue) {
		b.WriteString("**🚨 Error Details:**\n" + value_objects.PyStr(errValue) + "\n\n")
	}

	return b.String()
}

// stepList returns the steps for a troubleshooting key when the Python
// `"key" in troubleshooting` test would be true.
func stepList(troubleshooting any, key string) []any {
	v, ok := srvGet(troubleshooting, key, nil).([]any)
	if !ok {
		if ss, ok2 := srvGet(troubleshooting, key, nil).([]string); ok2 {
			out := make([]any, len(ss))
			for i, s := range ss {
				out[i] = s
			}
			return out
		}
		return nil
	}
	return v
}
