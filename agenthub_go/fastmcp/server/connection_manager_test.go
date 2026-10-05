package server

import (
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestConnectionManagerStatsShape(t *testing.T) {
	cm := NewConnectionManager()

	info := entities.NewOrderedMap[any]()
	info.Set("name", "client-a")
	info.Set("version", "1.2")
	caps := entities.NewOrderedMap[any]()
	caps.Set("cap", true)

	conn := cm.RegisterConnection("s1", info, caps)
	if conn.HealthCheckCount != 0 || !conn.IsHealthy {
		t.Fatalf("new connection: health=%d healthy=%v", conn.HealthCheckCount, conn.IsHealthy)
	}

	stats := cm.GetConnectionStats()
	serverInfo := srvGet(stats, "server_info", nil)
	if got := srvInt(srvGet(serverInfo, "restart_count", -1)); got != 0 {
		t.Fatalf("restart_count = %d, want 0", got)
	}
	if _, ok := srvGet(serverInfo, "start_time", nil).(string); !ok {
		t.Fatalf("start_time not a string")
	}

	connections := srvGet(stats, "connections", nil)
	if got := srvInt(srvGet(connections, "total_registered", -1)); got != 1 {
		t.Fatalf("total_registered = %d, want 1", got)
	}
	if got := srvInt(srvGet(connections, "active_connections", -1)); got != 1 {
		t.Fatalf("active_connections = %d, want 1", got)
	}
	if got := srvInt(srvGet(connections, "stale_connections", -1)); got != 0 {
		t.Fatalf("stale_connections = %d, want 0", got)
	}

	clients, ok := srvGet(stats, "active_clients", nil).([]any)
	if !ok || len(clients) != 1 {
		t.Fatalf("active_clients = %#v, want one entry", srvGet(stats, "active_clients", nil))
	}
	c0 := clients[0]
	if got := srvGet(c0, "session_id", nil); got != "s1" {
		t.Fatalf("session_id = %v", got)
	}
	if got := srvGet(c0, "client_name", nil); got != "client-a" {
		t.Fatalf("client_name = %v", got)
	}
	if got := srvGet(c0, "client_version", nil); got != "1.2" {
		t.Fatalf("client_version = %v", got)
	}
	if got := srvInt(srvGet(c0, "health_checks", -1)); got != 0 {
		t.Fatalf("health_checks = %d", got)
	}
	if got := srvGet(c0, "is_healthy", nil); got != true {
		t.Fatalf("is_healthy = %v", got)
	}
	capList, ok := srvGet(c0, "capabilities", nil).([]any)
	if !ok || len(capList) != 1 || capList[0] != "cap" {
		t.Fatalf("capabilities = %#v", srvGet(c0, "capabilities", nil))
	}
}

func TestConnectionManagerInsertionOrder(t *testing.T) {
	cm := NewConnectionManager()
	cm.RegisterConnection("a", entities.NewOrderedMap[any](), nil)
	cm.RegisterConnection("b", entities.NewOrderedMap[any](), nil)
	stats := cm.GetConnectionStats()
	clients := srvGet(stats, "active_clients", nil).([]any)
	if len(clients) != 2 {
		t.Fatalf("len = %d", len(clients))
	}
	if srvGet(clients[0], "session_id", nil) != "a" || srvGet(clients[1], "session_id", nil) != "b" {
		t.Fatalf("insertion order lost")
	}
}

func TestConnectionManagerRestartAndStale(t *testing.T) {
	cm := NewConnectionManager()
	cm.RegisterConnection("a", entities.NewOrderedMap[any](), nil)
	cm.RegisterConnection("b", entities.NewOrderedMap[any](), nil)

	cm.HandleServerRestart()
	if cm.ServerRestartCount != 1 {
		t.Fatalf("restart count = %d", cm.ServerRestartCount)
	}
	if cm.GetConnection("a").IsHealthy || cm.GetConnection("b").IsHealthy {
		t.Fatalf("connections should be marked unhealthy after restart")
	}
	ri := cm.GetReconnectionInfo()
	if got := srvGet(ri, "recommended_action", nil); got != "reconnect" {
		t.Fatalf("recommended_action = %v", got)
	}
	if got := srvInt(srvGet(ri, "connection_timeout_minutes", -1)); got != 30 {
		t.Fatalf("connection_timeout_minutes = %v", got)
	}

	cm.GetConnection("a").LastActivity = time.Now().Add(-31 * time.Minute)
	if !cm.GetConnection("a").IsStale(30) {
		t.Fatalf("a should be stale")
	}
	if cm.GetActiveConnections().Len() != 1 {
		t.Fatalf("active connections = %d, want 1", cm.GetActiveConnections().Len())
	}
	if n := cm.CleanupStaleConnections(); n != 1 {
		t.Fatalf("cleaned = %d, want 1", n)
	}
	if cm.Connections.Len() != 1 {
		t.Fatalf("remaining = %d, want 1", cm.Connections.Len())
	}

	if cm.UnregisterConnection("b") == nil {
		t.Fatalf("unregister existing returned nil")
	}
	if cm.UnregisterConnection("b") != nil {
		t.Fatalf("unregister missing should return nil")
	}
}
