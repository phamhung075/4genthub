package repositories

import (
	"testing"
	"time"

	"agenthub/fastmcp/connection_management/domain/entities"
	domainrepos "agenthub/fastmcp/connection_management/domain/repositories"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

var (
	_ domainrepos.ConnectionRepository = (*InMemoryConnectionRepository)(nil)
	_ domainrepos.ServerRepository     = (*InMemoryServerRepository)(nil)
)

func pinNow(t *testing.T, pinned time.Time) {
	t.Helper()
	old := entities.Now
	entities.Now = func() time.Time { return pinned }
	t.Cleanup(func() { entities.Now = old })
}

func TestInMemoryConnectionRepository(t *testing.T) {
	pinNow(t, time.Date(2026, 3, 1, 10, 0, 0, 0, time.UTC))
	r := NewInMemoryConnectionRepository()

	a := r.CreateConnection("a", map[string]any{"agent": "x"})
	b := r.CreateConnection("b", nil)

	if r.FindByID("a") != a || r.FindByID("b") != b {
		t.Fatalf("FindByID returned the wrong connection")
	}
	if r.FindByID("missing") != nil {
		t.Fatalf("FindByID(missing) = %#v, want nil", r.FindByID("missing"))
	}
	if r.GetConnectionCount() != 2 {
		t.Fatalf("GetConnectionCount = %d, want 2", r.GetConnectionCount())
	}

	b.Disconnect()
	if r.GetConnectionCount() != 1 {
		t.Fatalf("GetConnectionCount after disconnect = %d, want 1", r.GetConnectionCount())
	}
	active := r.FindAllActive()
	if len(active) != 1 || active[0] != a {
		t.Fatalf("FindAllActive = %#v, want only a", active)
	}

	stats := r.GetConnectionStatistics()
	if stats["total_connections"] != 2 || stats["active_connections"] != 1 || stats["inactive_connections"] != 1 {
		t.Fatalf("statistics counts = %#v", stats)
	}
	ids, ok := stats["connection_ids"].([]string)
	if !ok || len(ids) != 2 || ids[0] != "a" || ids[1] != "b" {
		t.Fatalf("connection_ids = %#v, want [a b] in insertion order", stats["connection_ids"])
	}

	if !r.RemoveConnection("a") {
		t.Fatalf("RemoveConnection(a) = false, want true")
	}
	if r.RemoveConnection("a") {
		t.Fatalf("RemoveConnection(a) a second time = true, want false")
	}
	if r.GetConnectionCount() != 0 {
		t.Fatalf("GetConnectionCount after removal = %d, want 0", r.GetConnectionCount())
	}
}

func TestInMemoryServerRepository(t *testing.T) {
	pinNow(t, time.Date(2026, 3, 1, 10, 0, 0, 0, time.UTC))
	r := NewInMemoryServerRepository()
	if r.GetCurrentServer() != nil {
		t.Fatalf("empty repository returned a server")
	}

	env := tmentities.NewOrderedMap[any]()
	server := r.CreateServer("n", "v", env, nil, nil)
	if r.GetCurrentServer() != server {
		t.Fatalf("CreateServer did not store the server")
	}
	if server.Name != "n" || server.Version != "v" {
		t.Fatalf("server = %#v", server)
	}

	other := entities.CreateServer("n2", "v2", nil, nil, nil)
	r.SaveServer(other)
	if r.GetCurrentServer() != other {
		t.Fatalf("SaveServer did not replace the server")
	}
	r.UpdateServerUptime(other)
	if r.GetCurrentServer() != other {
		t.Fatalf("UpdateServerUptime did not keep the server")
	}
}
