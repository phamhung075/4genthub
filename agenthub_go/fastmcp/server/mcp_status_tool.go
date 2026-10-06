package server

// MCP Status Tool for Real-time Status Updates
// (Python fastmcp/server/mcp_status_tool.py).

import (
	"fmt"
	"os"
	"strings"
	"time"

	"agenthub/fastmcp/config"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func mcpStatusNow() float64 { return float64(time.Now().UnixNano()) / 1e9 }

func mcpCtxSessionID(ctx *Context) string {
	if ctx != nil {
		return ctx.SessionID
	}
	return "unknown"
}

func mcpStatusErrString(v any) string {
	if err, ok := v.(error); ok {
		return err.Error()
	}
	return value_objects.PyStr(v)
}

func mcpStatusEnvDefault(key, def string) string {
	if v, ok := os.LookupEnv(key); ok {
		return v
	}
	return def
}

func mcpStatusOrderedString(k, v string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set(k, v)
	return m
}

func omGet(m *entities.OrderedMap[any], key string) (any, bool) {
	if m == nil {
		return nil, false
	}
	return m.Get(key)
}

func omGetMap(m *entities.OrderedMap[any], key string) *entities.OrderedMap[any] {
	v, ok := omGet(m, key)
	if !ok {
		return nil
	}
	mm, _ := v.(*entities.OrderedMap[any])
	return mm
}

func omString(m *entities.OrderedMap[any], key, def string) string {
	v, ok := omGet(m, key)
	if !ok || v == nil {
		return def
	}
	return value_objects.PyStr(v)
}

func omFloat(m *entities.OrderedMap[any], key string, def float64) float64 {
	v, ok := omGet(m, key)
	if !ok {
		return def
	}
	if f, ok := value_objects.PyFloat(v); ok {
		return f
	}
	return def
}

func omBool(m *entities.OrderedMap[any], key string) bool {
	v, _ := omGet(m, key)
	return value_objects.PyTruthy(v)
}

func omPy(m *entities.OrderedMap[any], key string, def any) string {
	v, ok := omGet(m, key)
	if !ok || v == nil {
		return value_objects.PyStr(def)
	}
	return value_objects.PyStr(v)
}

// GetMCPStatus mirrors get_mcp_status.
func GetMCPStatus(ctx *Context, includeDetails bool, cm *ConnectionManager, sb *ConnectionStatusBroadcaster) (status *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			e := mcpStatusErrString(r)
			status = entities.NewOrderedMap[any]()
			status.Set("timestamp", mcpStatusNow())
			status.Set("session_id", mcpCtxSessionID(ctx))
			si := entities.NewOrderedMap[any]()
			si.Set("status", "error")
			si.Set("message", "Status check failed: "+e)
			status.Set("server_info", si)
			status.Set("error", e)
		}
	}()

	now := mcpStatusNow()

	status = entities.NewOrderedMap[any]()
	status.Set("timestamp", now)
	status.Set("iso_timestamp", value_objects.IsoFormatNaive(time.Now()))
	status.Set("session_id", mcpCtxSessionID(ctx))
	serverInfo := entities.NewOrderedMap[any]()
	serverInfo.Set("name", config.ServerName)
	serverInfo.Set("version", config.ReleaseVersion)
	serverInfo.Set("status", "healthy")
	status.Set("server_info", serverInfo)

	// connection manager information
	var connErr any
	func() {
		defer func() {
			if r := recover(); r != nil {
				connErr = r
			}
		}()
		stats := cm.GetConnectionStats()
		reconnectionInfo := cm.GetReconnectionInfo()
		conns := omGetMap(stats, "connections")
		sinfo := omGetMap(stats, "server_info")

		ci := entities.NewOrderedMap[any]()
		ci.Set("active_connections", mustOm(conns, "active_connections"))
		ci.Set("total_registered", mustOm(conns, "total_registered"))
		ci.Set("stale_connections", mustOm(conns, "stale_connections"))
		ci.Set("server_restart_count", mustOm(sinfo, "restart_count"))
		ci.Set("uptime_seconds", mustOm(sinfo, "uptime_seconds"))
		ci.Set("recommended_action", mustOm(reconnectionInfo, "recommended_action"))
		status.Set("connection_info", ci)

		restartCount := omFloat(sinfo, "restart_count", 0)
		uptime := omFloat(sinfo, "uptime_seconds", 0)
		activeConnections := omFloat(conns, "active_connections", 0)

		if restartCount > 0 && uptime < 60 {
			serverInfo.Set("status", "restarted")
			serverInfo.Set("message", "Server recently restarted, reconnection recommended")
		} else if activeConnections == 0 && uptime > 60 {
			serverInfo.Set("status", "no_clients")
			serverInfo.Set("message", "Server healthy but no active client connections")
		} else {
			serverInfo.Set("status", "healthy")
			serverInfo.Set("message", "Server operating normally")
		}

		if includeDetails {
			if ac, ok := omGet(stats, "active_clients"); ok && value_objects.PyTruthy(ac) {
				status.Set("active_clients", ac)
			}
		}
	}()
	if connErr != nil {
		e := mcpStatusErrString(connErr)
		status.Set("connection_info", mcpStatusOrderedString("error", e))
		serverInfo.Set("status", "degraded")
		serverInfo.Set("message", "Connection manager error: "+e)
	}

	// status broadcaster information
	var bcastErr any
	func() {
		defer func() {
			if r := recover(); r != nil {
				bcastErr = r
			}
		}()
		lastBroadcast := sb.GetLastStatus()
		clientCount := sb.GetClientCount()
		bi := entities.NewOrderedMap[any]()
		bi.Set("registered_clients", clientCount)
		bi.Set("last_broadcast", lastBroadcast)
		bi.Set("broadcasting_active", true)
		status.Set("broadcast_info", bi)
	}()
	if bcastErr != nil {
		e := mcpStatusErrString(bcastErr)
		bi := entities.NewOrderedMap[any]()
		bi.Set("error", e)
		bi.Set("broadcasting_active", false)
		status.Set("broadcast_info", bi)
	}

	// authentication status - always enabled now
	authInfo := entities.NewOrderedMap[any]()
	authInfo.Set("enabled", true)
	authInfo.Set("production_mode", value_objects.PyLower(os.Getenv("PRODUCTION")) == "true")
	status.Set("auth_info", authInfo)

	// Docker/container information
	containerInfo := entities.NewOrderedMap[any]()
	_, dockErr := os.Stat("/.dockerenv")
	containerInfo.Set("is_docker", dockErr == nil)
	containerInfo.Set("transport", mcpStatusEnvDefault("FASTMCP_TRANSPORT", "stdio"))
	containerInfo.Set("host", mcpStatusEnvDefault("FASTMCP_HOST", "localhost"))
	containerInfo.Set("port", mcpStatusEnvDefault("FASTMCP_PORT", "8000"))
	status.Set("container_info", containerInfo)

	// tools availability check
	toolsInfo := entities.NewOrderedMap[any]()
	toolsInfo.Set("available", true)
	toolsInfo.Set("last_check", now)
	toolsInfo.Set("tool_count", "unknown")
	status.Set("tools_info", toolsInfo)

	// recommendations
	recommendations := []string{}
	serverStatus, _ := serverInfo.Get("status")
	switch serverStatus {
	case "restarted":
		recommendations = append(recommendations, "Use Cursor MCP toggle: Settings → Extensions → MCP → Toggle agenthub_http OFF/ON")
		recommendations = append(recommendations, "Alternative: Restart Cursor completely")
	case "no_clients":
		recommendations = append(recommendations, "Check Cursor MCP configuration in .cursor/mcp.json")
		recommendations = append(recommendations, "Verify MCP server URL: Check your backend service URL at /mcp/")
	default:
		if connInfo := omGetMap(status, "connection_info"); connInfo != nil {
			if omFloat(connInfo, "stale_connections", 0) > 0 {
				recommendations = append(recommendations, "Some connections are stale, consider reconnecting")
			}
		}
	}
	status.Set("recommendations", recommendations)

	return status
}

// mustOm returns the value at key, panicking (like a Python KeyError) when absent.
func mustOm(m *entities.OrderedMap[any], key string) any {
	v, ok := m.Get(key)
	if !ok {
		panic(fmt.Sprintf("KeyError: %s", key))
	}
	return v
}

// RegisterForStatusUpdates mirrors register_for_status_updates.
func RegisterForStatusUpdates(ctx *Context, sb *ConnectionStatusBroadcaster, cm *ConnectionManager) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			e := mcpStatusErrString(r)
			result = entities.NewOrderedMap[any]()
			result.Set("success", false)
			result.Set("error", e)
		}
	}()

	if ctx == nil || ctx.SessionID == "" {
		result = entities.NewOrderedMap[any]()
		result.Set("success", false)
		result.Set("error", "No valid session ID for registration")
		return result
	}

	sb.RegisterClient(ctx.SessionID)

	clientInfo := entities.NewOrderedMap[any]()
	clientInfo.Set("name", "cursor")
	clientInfo.Set("version", "unknown")
	clientInfo.Set("type", "mcp_client")
	cm.RegisterConnection(ctx.SessionID, clientInfo, nil)

	result = entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("session_id", ctx.SessionID)
	result.Set("message", "Successfully registered for status updates")
	result.Set("update_interval", 30)
	result.Set("immediate_events", []string{"server_restart", "tools_unavailable"})
	return result
}

// FormatMCPStatusTool mirrors the mcp_status_tool inner handler.
func FormatMCPStatusTool(ctx *Context, includeDetails bool, cm *ConnectionManager, sb *ConnectionStatusBroadcaster) string {
	statusInfo := GetMCPStatus(ctx, includeDetails, cm, sb)

	serverInfo := omGetMap(statusInfo, "server_info")
	serverStatus := omString(serverInfo, "status", "unknown")
	statusEmoji := map[string]string{
		"healthy":    "✅",
		"restarted":  "🔄",
		"no_clients": "📡",
		"degraded":   "⚠️",
		"error":      "🚨",
	}
	emoji, ok := statusEmoji[serverStatus]
	if !ok {
		emoji = "❓"
	}

	var b strings.Builder
	b.WriteString(emoji + " **MCP Server Status: " + value_objects.PyTitle(serverStatus) + "**\n\n")

	b.WriteString("**Server Information:**\n")
	b.WriteString("- Name: " + omString(serverInfo, "name", "Unknown") + "\n")
	b.WriteString("- Version: " + omString(serverInfo, "version", "Unknown") + "\n")
	b.WriteString("- Status: " + omString(serverInfo, "status", "Unknown") + "\n")
	if msg := omString(serverInfo, "message", ""); msg != "" {
		b.WriteString("- Message: " + msg + "\n")
	}
	b.WriteString("- Timestamp: " + omString(statusInfo, "iso_timestamp", "Unknown") + "\n\n")

	connInfo := omGetMap(statusInfo, "connection_info")
	if _, hasErr := omGet(connInfo, "error"); !hasErr {
		b.WriteString("**Connection Information:**\n")
		b.WriteString("- Active Connections: " + omPy(connInfo, "active_connections", 0) + "\n")
		b.WriteString("- Total Registered: " + omPy(connInfo, "total_registered", 0) + "\n")
		b.WriteString("- Stale Connections: " + omPy(connInfo, "stale_connections", 0) + "\n")
		b.WriteString("- Server Restarts: " + omPy(connInfo, "server_restart_count", 0) + "\n")
		b.WriteString(fmt.Sprintf("- Uptime: %.1f seconds\n", omFloat(connInfo, "uptime_seconds", 0)))
		b.WriteString("- Recommended Action: " + omString(connInfo, "recommended_action", "continue") + "\n\n")
	} else {
		b.WriteString("**Connection Error:** " + omString(connInfo, "error", "") + "\n\n")
	}

	broadcastInfo := omGetMap(statusInfo, "broadcast_info")
	if omBool(broadcastInfo, "broadcasting_active") {
		b.WriteString("**Real-time Updates:**\n")
		b.WriteString("- Broadcasting Active: ✅\n")
		b.WriteString("- Registered Clients: " + omPy(broadcastInfo, "registered_clients", 0) + "\n")
		if lb, ok := omGet(broadcastInfo, "last_broadcast"); ok && value_objects.PyTruthy(lb) {
			lbMap, _ := lb.(*entities.OrderedMap[any])
			b.WriteString("- Last Broadcast: " + omString(lbMap, "event_type", "unknown") + " ")
			b.WriteString("(" + omString(lbMap, "server_status", "unknown") + ")\n")
		}
		b.WriteString("\n")
	}

	authInfo := omGetMap(statusInfo, "auth_info")
	containerInfo := omGetMap(statusInfo, "container_info")
	b.WriteString("**Configuration:**\n")
	if omBool(authInfo, "enabled") {
		b.WriteString("- Authentication: Enabled\n")
	} else {
		b.WriteString("- Authentication: Disabled\n")
	}
	if omBool(authInfo, "mvp_mode") {
		b.WriteString("- MVP Mode: Yes\n")
	} else {
		b.WriteString("- MVP Mode: No\n")
	}
	if omBool(containerInfo, "is_docker") {
		b.WriteString("- Container: Docker\n")
	} else {
		b.WriteString("- Container: Local\n")
	}
	b.WriteString("- Transport: " + omString(containerInfo, "transport", "unknown") + "\n")
	b.WriteString("- Endpoint: " + omString(containerInfo, "host", "localhost") + ":" + omString(containerInfo, "port", "8000") + "\n\n")

	if includeDetails {
		if ac, ok := omGet(statusInfo, "active_clients"); ok && value_objects.PyTruthy(ac) {
			if list, ok := ac.([]any); ok {
				b.WriteString("**Active Clients:**\n")
				for _, client := range list {
					cmm, _ := client.(*entities.OrderedMap[any])
					b.WriteString("- " + omString(cmm, "client_name", "unknown") + " ")
					b.WriteString("(v" + omString(cmm, "client_version", "?") + ")\n")
					b.WriteString("  Session: " + omString(cmm, "session_id", "unknown") + "\n")
					b.WriteString(fmt.Sprintf("  Connected: %.1fs ago\n", omFloat(cmm, "connection_age_seconds", 0)))
					b.WriteString("  Health Checks: " + omPy(cmm, "health_checks", 0) + "\n")
				}
				b.WriteString("\n")
			}
		}
	}

	if recs, ok := omGet(statusInfo, "recommendations"); ok {
		if list, ok := recs.([]string); ok && len(list) > 0 {
			b.WriteString("**💡 Recommendations:**\n")
			for _, rec := range list {
				b.WriteString("- " + rec + "\n")
			}
			b.WriteString("\n")
		}
	}

	b.WriteString("**🔧 Quick Actions:**\n")
	b.WriteString("- Check connection: Call `connection_health_check` tool\n")
	b.WriteString("- Register for updates: Call `register_for_status_updates` tool\n")
	b.WriteString("- Server health: Visit your backend service URL at /health\n")

	return b.String()
}

// FormatRegisterStatusUpdatesTool mirrors the register_status_updates_tool inner handler.
func FormatRegisterStatusUpdatesTool(ctx *Context, sb *ConnectionStatusBroadcaster, cm *ConnectionManager) string {
	result := RegisterForStatusUpdates(ctx, sb, cm)

	var b strings.Builder
	if omBool(result, "success") {
		b.WriteString("✅ **Successfully Registered for Status Updates**\n\n")
		b.WriteString("**Session Information:**\n")
		b.WriteString("- Session ID: " + omString(result, "session_id", "unknown") + "\n")
		b.WriteString(fmt.Sprintf("- Update Interval: %s seconds\n", omPy(result, "update_interval", 30)))
		events := ""
		if v, ok := omGet(result, "immediate_events"); ok {
			if list, ok := v.([]string); ok {
				events = strings.Join(list, ", ")
			}
		}
		b.WriteString("- Immediate Events: " + events + "\n\n")
		b.WriteString("**What This Means:**\n")
		b.WriteString("- Your MCP tools status icon will update automatically\n")
		b.WriteString("- You'll receive immediate notifications on server restarts\n")
		b.WriteString("- Connection issues will be detected and reported\n")
		b.WriteString("- Tools availability changes will be broadcasted\n\n")
		b.WriteString("**Next Steps:**\n")
		b.WriteString("- Your session is now monitored for connection health\n")
		b.WriteString("- If the server restarts, you'll be notified to reconnect\n")
		b.WriteString("- Use the `get_mcp_status` tool to check current status anytime\n")
	} else {
		b.WriteString("❌ **Registration Failed**\n\n")
		b.WriteString("**Error:** " + omString(result, "error", "Unknown error") + "\n\n")
		b.WriteString("**Troubleshooting:**\n")
		b.WriteString("- Ensure you have a valid MCP session\n")
		b.WriteString("- Check server logs for connection issues\n")
		b.WriteString("- Try the `connection_health_check` tool for diagnostics\n")
	}
	return b.String()
}
