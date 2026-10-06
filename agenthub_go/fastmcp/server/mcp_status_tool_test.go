package server

import (
	"reflect"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/config"
	"agenthub/fastmcp/task_management/domain/entities"
)

func mustMap(t *testing.T, m *entities.OrderedMap[any], key string) *entities.OrderedMap[any] {
	t.Helper()
	v, ok := m.Get(key)
	if !ok {
		t.Fatalf("missing key %q", key)
	}
	mm, ok := v.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("key %q is %T, not OrderedMap", key, v)
	}
	return mm
}

func statusManager(active int, restart int, uptime time.Duration) *ConnectionManager {
	cm := NewConnectionManager()
	cm.ServerStartTime = time.Now().Add(-uptime)
	cm.ServerRestartCount = restart
	for i := 0; i < active; i++ {
		info := entities.NewOrderedMap[any]()
		info.Set("name", "cursor")
		info.Set("version", "unknown")
		cm.RegisterConnection("client-"+string(rune('a'+i)), info, nil)
	}
	return cm
}

func TestGetMCPStatusNoClients(t *testing.T) {
	cm := statusManager(0, 0, 100*time.Second)
	sb := NewConnectionStatusBroadcaster(cm)
	got := GetMCPStatus(&Context{SessionID: "sess-1"}, true, cm, sb)

	wantKeys := []string{"timestamp", "iso_timestamp", "session_id", "server_info", "connection_info", "broadcast_info", "auth_info", "container_info", "tools_info", "recommendations"}
	if !reflect.DeepEqual(got.Keys(), wantKeys) {
		t.Fatalf("keys = %v, want %v", got.Keys(), wantKeys)
	}
	if v, _ := got.Get("session_id"); v != "sess-1" {
		t.Errorf("session_id = %v", v)
	}
	serverInfo := mustMap(t, got, "server_info")
	if !reflect.DeepEqual(serverInfo.Keys(), []string{"name", "version", "status", "message"}) {
		t.Errorf("server_info keys = %v", serverInfo.Keys())
	}
	if v, _ := serverInfo.Get("version"); v != config.ReleaseVersion {
		t.Errorf("server_info.version = %v, want %q", v, config.ReleaseVersion)
	}
	if v, _ := serverInfo.Get("status"); v != "no_clients" {
		t.Errorf("status = %v", v)
	}
	if v, _ := serverInfo.Get("message"); v != "Server healthy but no active client connections" {
		t.Errorf("message = %v", v)
	}
	connectionInfo := mustMap(t, got, "connection_info")
	if v, _ := connectionInfo.Get("total_registered"); v != 0 {
		t.Errorf("total_registered = %v", v)
	}
	recs, _ := got.Get("recommendations")
	if !reflect.DeepEqual(recs, []string{
		"Check Cursor MCP configuration in .cursor/mcp.json",
		"Verify MCP server URL: Check your backend service URL at /mcp/",
	}) {
		t.Errorf("recommendations = %v", recs)
	}
}

func TestGetMCPStatusRestarted(t *testing.T) {
	cm := statusManager(3, 1, 30*time.Second)
	sb := NewConnectionStatusBroadcaster(cm)
	got := GetMCPStatus(nil, false, cm, sb)
	serverInfo := mustMap(t, got, "server_info")
	if v, _ := serverInfo.Get("status"); v != "restarted" {
		t.Errorf("status = %v", v)
	}
	if v, _ := serverInfo.Get("message"); v != "Server recently restarted, reconnection recommended" {
		t.Errorf("message = %v", v)
	}
	if v, _ := got.Get("session_id"); v != "unknown" {
		t.Errorf("session_id = %v", v)
	}
	if _, ok := got.Get("active_clients"); ok {
		t.Errorf("active_clients should be absent when includeDetails=false")
	}
}

func TestGetMCPStatusConnectionError(t *testing.T) {
	sb := NewConnectionStatusBroadcaster(nil)
	got := GetMCPStatus(&Context{SessionID: "s"}, true, nil, sb)
	serverInfo := mustMap(t, got, "server_info")
	if v, _ := serverInfo.Get("status"); v != "degraded" {
		t.Errorf("status = %v", v)
	}
	ci := mustMap(t, got, "connection_info")
	if _, ok := ci.Get("error"); !ok {
		t.Errorf("connection_info should carry error, got %v", ci.Keys())
	}
}

func TestRegisterForStatusUpdates(t *testing.T) {
	cm := NewConnectionManager()
	sb := NewConnectionStatusBroadcaster(cm)

	bad := RegisterForStatusUpdates(nil, sb, cm)
	if v, _ := bad.Get("success"); v != false {
		t.Errorf("success = %v", v)
	}
	if v, _ := bad.Get("error"); v != "No valid session ID for registration" {
		t.Errorf("error = %v", v)
	}

	ok := RegisterForStatusUpdates(&Context{SessionID: "sess-9"}, sb, cm)
	wantKeys := []string{"success", "session_id", "message", "update_interval", "immediate_events"}
	if !reflect.DeepEqual(ok.Keys(), wantKeys) {
		t.Fatalf("keys = %v, want %v", ok.Keys(), wantKeys)
	}
	if v, _ := ok.Get("update_interval"); v != 30 {
		t.Errorf("update_interval = %v", v)
	}
	if cm.GetConnection("sess-9") == nil {
		t.Errorf("connection not registered")
	}
	if sb.GetClientCount() != 1 {
		t.Errorf("broadcaster client count = %d", sb.GetClientCount())
	}
}

func TestFormatMCPStatusTool(t *testing.T) {
	cm := statusManager(0, 0, 100*time.Second)
	sb := NewConnectionStatusBroadcaster(cm)
	out := FormatMCPStatusTool(&Context{SessionID: "s"}, false, cm, sb)
	for _, want := range []string{
		"**MCP Server Status: No_Clients**",
		"- MVP Mode: No\n",
		"- Authentication: Enabled\n",
		"**💡 Recommendations:**",
	} {
		if !strings.Contains(out, want) {
			t.Errorf("output missing %q", want)
		}
	}
}
