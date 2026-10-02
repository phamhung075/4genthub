package database

import "testing"

func TestDatabaseSourceManagerInfoOrder(t *testing.T) {
	t.Setenv("MCP_DB_PATH", "/tmp/example.db")
	m := NewDatabaseSourceManager()
	path, err := m.GetDatabasePath()
	if err != nil {
		t.Fatalf("GetDatabasePath: %v", err)
	}
	if path != "/tmp/example.db" {
		t.Fatalf("path = %q", path)
	}
	info := m.GetInfo()
	wantKeys := []string{"mode", "database_path", "is_docker", "is_test", "is_stdin", "is_normal"}
	got := info.Keys()
	if len(got) != len(wantKeys) {
		t.Fatalf("keys = %v", got)
	}
	for i, k := range wantKeys {
		if got[i] != k {
			t.Fatalf("key[%d] = %q want %q", i, got[i], k)
		}
	}
	if v, _ := info.Get("database_path"); v != "/tmp/example.db" {
		t.Fatalf("database_path = %v", v)
	}
	if v, _ := info.Get("is_normal"); v != true {
		t.Fatalf("is_normal = %v", v)
	}
}

func TestGetDatabasePathDeprecated(t *testing.T) {
	if _, err := GetDatabasePath(); err == nil {
		t.Fatal("expected error")
	}
}
