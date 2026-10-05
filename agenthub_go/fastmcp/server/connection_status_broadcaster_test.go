package server

import (
	"strings"
	"testing"
)

func TestStatusUpdateDictShape(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "yes") // Python quirk: only the exact "true" is truthy
	b := NewConnectionStatusBroadcaster(nil)
	su := b.createStatusUpdate("connection_health")

	if su.EventType != "connection_health" || su.ServerStatus != "healthy" {
		t.Fatalf("basic fields: %+v", su)
	}
	if su.ConnectionCount != 0 || su.ServerRestartCount != 0 || su.UptimeSeconds != 0 {
		t.Fatalf("counts: %+v", su)
	}
	if su.RecommendedAction != "continue" || !su.ToolsAvailable {
		t.Fatalf("action/tools: %+v", su)
	}
	if su.AuthEnabled {
		t.Fatalf("AUTH_ENABLED=yes must not map to true")
	}

	got := su.ToDict().Keys()
	want := []string{"event_type", "timestamp", "server_status", "connection_count",
		"server_restart_count", "uptime_seconds", "recommended_action", "tools_available",
		"auth_enabled", "additional_info"}
	if len(got) != len(want) {
		t.Fatalf("keys = %v", got)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("key %d = %q, want %q", i, got[i], want[i])
		}
	}

	info := srvGet(su.ToDict(), "additional_info", nil)
	if got := srvInt(srvGet(info, "client_count", -1)); got != 0 {
		t.Fatalf("client_count = %d", got)
	}
	if _, ok := srvGet(info, "broadcast_time", nil).(string); !ok {
		t.Fatalf("broadcast_time missing")
	}
}

func TestStatusBroadcasterClientsAndRestart(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "true")
	cm := NewConnectionManager()
	cm.HandleServerRestart()

	b := NewConnectionStatusBroadcaster(cm)
	b.RegisterClient("c1")
	if b.GetClientCount() != 1 {
		t.Fatalf("client count = %d", b.GetClientCount())
	}

	su := b.createStatusUpdate("server_restart")
	if su.ServerRestartCount != 1 || su.ServerStatus != "restarted" {
		t.Fatalf("restart status: %+v", su)
	}
	if !su.AuthEnabled {
		t.Fatalf("AUTH_ENABLED=true should be true")
	}

	b.BroadcastToolsStatus(false)
	last := b.GetLastStatus()
	if last == nil {
		t.Fatalf("last status nil")
	}
	if got := srvGet(last, "tools_available", nil); got != false {
		t.Fatalf("tools_available = %v", got)
	}
	if got := srvGet(last, "recommended_action", nil); got != "reconnect" {
		t.Fatalf("recommended_action = %v", got)
	}
	if got := srvGet(last, "server_status", nil); got != "degraded" {
		t.Fatalf("server_status = %v", got)
	}

	b.UnregisterClient("c1")
	if b.GetClientCount() != 0 {
		t.Fatalf("client count = %d", b.GetClientCount())
	}
}

type fakeHealthSession struct{ id *string }

func (f fakeHealthSession) SessionID() *string { return f.id }

func TestConnectionHealthCheckAndFormat(t *testing.T) {
	CleanupConnectionManager()
	defer CleanupConnectionManager()

	sid := "sess-1"
	h := ConnectionHealthCheck(fakeHealthSession{id: &sid})

	if got := srvGet(h, "current_session_id", nil); got != "sess-1" {
		t.Fatalf("current_session_id = %v", got)
	}
	if got := srvGet(h, "server_status", nil); got != "no_clients" {
		t.Fatalf("server_status = %v", got)
	}
	if got := srvGet(h, "recommendation", nil); got != "No active MCP clients connected." {
		t.Fatalf("recommendation = %v", got)
	}
	warnings, ok := srvGet(h, "warnings", nil).([]any)
	if !ok || len(warnings) != 1 {
		t.Fatalf("warnings = %#v", srvGet(h, "warnings", nil))
	}
	if warnings[0] != "No active connections detected, but current session exists. Connection state may be inconsistent." {
		t.Fatalf("warning text = %q", warnings[0])
	}

	text := FormatConnectionHealth(h)
	if !strings.Contains(text, "📡 **Connection Health Status: No Clients**") {
		t.Fatalf("missing header:\n%s", text)
	}
	if !strings.Contains(text, "- Session ID: sess-1") {
		t.Fatalf("missing session line:\n%s", text)
	}
	if !strings.Contains(text, "**🔄 Quick Cursor Reconnection (Recommended):**") {
		t.Fatalf("missing reconnection steps:\n%s", text)
	}
	if strings.Contains(text, "**🚨 Immediate Troubleshooting:**") {
		t.Fatalf("unexpected immediate troubleshooting section:\n%s", text)
	}
}

func TestConnectionHealthErrorFormat(t *testing.T) {
	text := FormatConnectionHealth(connectionHealthErrorDict("boom"))
	if !strings.Contains(text, "🚨 **Connection Health Status: Error**") {
		t.Fatalf("missing error header:\n%s", text)
	}
	if !strings.Contains(text, "**🚨 Error Details:**\nboom") {
		t.Fatalf("missing error detail:\n%s", text)
	}
	if !strings.Contains(text, "**🚨 Immediate Troubleshooting:**") {
		t.Fatalf("missing immediate steps:\n%s", text)
	}
}
