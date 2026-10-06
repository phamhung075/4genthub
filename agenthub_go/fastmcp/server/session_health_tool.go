// Session Health Check Tool (Python fastmcp/server/session_health_tool.py).
//
// register_session_health_tool is not ported: it is a FastMCP @server.tool
// decorator with no Go meaning. The check and the human-readable formatting are
// ported; the registered tool is present here as a plain function, dispatched
// from the MCP route as `check_session_health` (httpapp/mcp_routes.go:332).
package server

import (
	"reflect"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// zpSessionStoreTypeName mirrors type(event_store).__name__ (drops *pkg.).
func zpSessionStoreTypeName(v any) string {
	t := reflect.TypeOf(v)
	if t == nil {
		return "NoneType"
	}
	name := t.String()
	name = strings.TrimPrefix(name, "*")
	if i := strings.LastIndex(name, "."); i >= 0 {
		name = name[i+1:]
	}
	return name
}

// SessionHealthCheck mirrors session_health_check. Python's outer try/except
// becomes a returned OrderedMap; there is no recoverable error until the global
// store creation, which has no error path here.
func SessionHealthCheck(ctx *Context) *entities.OrderedMap[any] {
	eventStore := GetGlobalEventStore()

	healthInfo := entities.NewOrderedMap[any]()
	healthInfo.Set("session_store_type", zpSessionStoreTypeName(eventStore))
	sessionID := ""
	if ctx != nil {
		sessionID = ctx.SessionID
	}
	healthInfo.Set("current_session_id", sessionID)
	// Python: ctx.request_context.session.created_at.isoformat() when present.
	// The minimal Go Context has no created_at, so the hasattr branch is false.
	healthInfo.Set("timestamp", "unknown")

	if hc, ok := eventStore.(zpHealthCheckable); ok {
		storeHealth := hc.HealthCheck()
		if storeHealth != nil {
			for _, k := range storeHealth.Keys() {
				v, _ := storeHealth.Get(k)
				healthInfo.Set(k, v)
			}
		}
	}

	if sessionID != "" {
		healthInfo.Set("session_active", true)
		healthInfo.Set("session_id_length", len(sessionID))

		events := eventStore.GetEvents(sessionID, nil, nil, 5)
		healthInfo.Set("recent_events_count", len(events))
		recent := make([]any, 0, 3)
		for i, event := range events {
			if i >= 3 {
				break
			}
			entry := entities.NewOrderedMap[any]()
			entry.Set("type", event.EventType)
			entry.Set("timestamp", event.Timestamp)
			// Python bug kept: event.timestamp - event.timestamp == 0.
			entry.Set("age_seconds", 0)
			recent = append(recent, entry)
		}
		healthInfo.Set("recent_events", recent)
	} else {
		healthInfo.Set("session_active", false)
		healthInfo.Set("session_warning", "No session ID available - this may indicate session persistence issues")
	}

	if sessionID != "" {
		// Python calls store_event(session_id=..., event_type=..., event_data=...,
		// ttl=60) while EventStore.store_event takes (stream_id, message); the call
		// always raises TypeError, is caught, and records the error.
		healthInfo.Set("test_store_error", "store_event() got an unexpected keyword argument 'session_id'")
		healthInfo.Set("test_store_success", false)
	}

	healthInfo.Set("overall_status", "healthy")

	warnings := []any{}
	if !zpSessionHealthBool(healthInfo, "session_active") {
		warnings = append(warnings, "No active session detected")
	}
	if zpSessionHealthBool(healthInfo, "using_fallback") {
		warnings = append(warnings, "Using memory fallback instead of Redis")
	}
	if !zpSessionHealthBoolDefault(healthInfo, "redis_connected", true) {
		warnings = append(warnings, "Redis connection unavailable")
	}
	if !zpSessionHealthBoolDefault(healthInfo, "test_store_success", true) {
		warnings = append(warnings, "Session storage test failed")
	}

	if len(warnings) > 0 {
		healthInfo.Set("warnings", warnings)
		if len(warnings) <= 2 {
			healthInfo.Set("overall_status", "degraded")
		} else {
			healthInfo.Set("overall_status", "unhealthy")
		}
	}

	recommendations := []any{}
	if zpSessionHealthBool(healthInfo, "using_fallback") {
		recommendations = append(recommendations, "Consider setting up Redis for persistent session storage. Set REDIS_URL environment variable or check Redis connectivity.")
	}
	if !zpSessionHealthBool(healthInfo, "session_active") {
		recommendations = append(recommendations, "Session persistence may not be working correctly. Check MCP client connection and server configuration.")
	}
	if n, ok := healthInfo.Get("session_count"); ok && zpSessionFloat(n) > 1000 {
		recommendations = append(recommendations, "High session count detected. Consider implementing session cleanup policies.")
	}
	healthInfo.Set("recommendations", recommendations)

	return healthInfo
}

func zpSessionHealthBool(m *entities.OrderedMap[any], key string) bool {
	return zpSessionHealthBoolDefault(m, key, false)
}

func zpSessionHealthBoolDefault(m *entities.OrderedMap[any], key string, def bool) bool {
	v, ok := m.Get(key)
	if !ok || v == nil {
		return def
	}
	b, _ := v.(bool)
	return b
}

// SessionHealthToolText mirrors the string returned by the registered
// session_health_tool (the status emoji + formatted sections).
func SessionHealthToolText(healthInfo *entities.OrderedMap[any]) string {
	statusEmoji := map[string]string{
		"healthy":   "\u2705",
		"degraded":  "\u26a0\ufe0f",
		"unhealthy": "\u274c",
		"error":     "\U0001f6a8",
	}

	overall := "error"
	if v, ok := healthInfo.Get("overall_status"); ok {
		if s, ok := v.(string); ok {
			overall = s
		}
	}
	emoji := statusEmoji[overall]
	if emoji == "" {
		emoji = "\u2753"
	}

	response := emoji + " **Session Health Status: " + strings.ToUpper(overall) + "**\n\n"

	response += "**Core Information:**\n"
	response += "- Session Store: " + zpSessionHealthString(healthInfo, "session_store_type", "unknown") + "\n"
	response += "- Session Active: " + zpSessionHealthPyBool(zpSessionHealthBool(healthInfo, "session_active")) + "\n"
	response += "- Current Session ID: " + zpSessionHealthString(healthInfo, "current_session_id", "none") + "\n"

	if v, ok := healthInfo.Get("session_count"); ok && v != nil {
		response += "- Total Sessions: " + value_objects.PyStr(v) + "\n"
	}

	if _, ok := healthInfo.Get("redis_available"); ok {
		response += "\n**Redis Information:**\n"
		response += "- Redis Available: " + zpSessionHealthPyBool(zpSessionHealthBool(healthInfo, "redis_available")) + "\n"
		response += "- Redis Connected: " + zpSessionHealthPyBool(zpSessionHealthBool(healthInfo, "redis_connected")) + "\n"
		response += "- Using Fallback: " + zpSessionHealthPyBool(zpSessionHealthBool(healthInfo, "using_fallback")) + "\n"
		if ri, ok := healthInfo.Get("redis_info"); ok && ri != nil {
			if m, ok := ri.(*entities.OrderedMap[any]); ok {
				response += "- Connected Clients: " + zpSessionHealthString(m, "connected_clients", "unknown") + "\n"
				response += "- Memory Used: " + zpSessionHealthString(m, "used_memory", "unknown") + "\n"
			}
		}
	}

	if v, ok := healthInfo.Get("test_store_success"); ok {
		if b, _ := v.(bool); b {
			response += "\n**Storage Test:** \u2705 PASS\n"
		} else {
			response += "\n**Storage Test:** \u274c FAIL\n"
		}
	}

	if v, ok := healthInfo.Get("recent_events"); ok && v != nil {
		if list, ok := v.([]any); ok && len(list) > 0 {
			response += "\n**Recent Session Events:**\n"
			for _, item := range list {
				entry, _ := item.(*entities.OrderedMap[any])
				etype := zpSessionHealthString(entry, "type", "unknown")
				age := 0.0
				if entry != nil {
					if av, ok := entry.Get("age_seconds"); ok {
						age = zpSessionFloat(av)
					}
				}
				response += "- " + etype + " (age: " + zpSessionFixed1(age) + "s)\n"
			}
		}
	}

	if v, ok := healthInfo.Get("warnings"); ok && v != nil {
		if list, ok := v.([]any); ok && len(list) > 0 {
			response += "\n**\u26a0\ufe0f Warnings:**\n"
			for _, w := range list {
				response += "- " + value_objects.PyStr(w) + "\n"
			}
		}
	}

	if v, ok := healthInfo.Get("recommendations"); ok && v != nil {
		if list, ok := v.([]any); ok && len(list) > 0 {
			response += "\n**\U0001f4a1 Recommendations:**\n"
			for _, r := range list {
				response += "- " + value_objects.PyStr(r) + "\n"
			}
		}
	}

	if v, ok := healthInfo.Get("error"); ok && v != nil && value_objects.PyTruthy(v) {
		response += "\n**\U0001f6a8 Error Details:**\n" + value_objects.PyStr(v) + "\n"
	}

	return response
}

func zpSessionHealthString(m *entities.OrderedMap[any], key, def string) string {
	if m == nil {
		return def
	}
	v, ok := m.Get(key)
	if !ok || v == nil {
		return def
	}
	s, ok := v.(string)
	if !ok {
		return value_objects.PyStr(v)
	}
	return s
}

func zpSessionHealthPyBool(b bool) string {
	if b {
		return "True"
	}
	return "False"
}

// zpSessionFixed1 mirrors f"{x:.1f}".
func zpSessionFixed1(f float64) string {
	neg := f < 0
	if neg {
		f = -f
	}
	scaled := int64(f*10 + 0.5)
	whole := scaled / 10
	frac := scaled % 10
	s := zpSessionItoa(int(whole)) + "." + string(rune('0'+frac))
	if neg {
		return "-" + s
	}
	return s
}
