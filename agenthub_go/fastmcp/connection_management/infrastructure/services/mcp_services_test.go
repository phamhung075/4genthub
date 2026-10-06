package services

import (
	"os"
	"testing"
	"time"

	"agenthub/fastmcp/connection_management/domain/entities"
	domainservices "agenthub/fastmcp/connection_management/domain/services"
	"agenthub/fastmcp/connection_management/domain/value_objects"
)

var (
	_ domainservices.ConnectionDiagnosticsService = (*MCPConnectionDiagnosticsService)(nil)
	_ domainservices.ServerHealthService          = (*MCPServerHealthService)(nil)
	_ domainservices.StatusBroadcastingService    = (*MCPStatusBroadcastingService)(nil)
)

func pinConnectionNow(t *testing.T, pinned time.Time) {
	t.Helper()
	old := entities.Now
	entities.Now = func() time.Time { return pinned }
	t.Cleanup(func() { entities.Now = old })
}

func TestMCPConnectionDiagnosticsService(t *testing.T) {
	pinned := time.Date(2026, 3, 1, 10, 0, 0, 0, time.UTC)
	pinConnectionNow(t, pinned)
	s := NewMCPConnectionDiagnosticsService()

	if s.GetConnectionStatistics()["connection_health"] != "no_clients" {
		t.Fatalf("connection_health = %#v", s.GetConnectionStatistics()["connection_health"])
	}
	recs := s.GetReconnectionRecommendations()
	if recs["recommended_action"] != "no_action_needed" {
		t.Fatalf("recommended_action = %#v", recs["recommended_action"])
	}
	infra := s.ValidateConnectionInfrastructure()
	if infra["infrastructure_health"] != "healthy" {
		t.Fatalf("infrastructure_health = %#v", infra["infrastructure_health"])
	}

	empty := s.AnalyzeConnectionPatterns(nil)
	if empty["pattern_analysis"] != "no_connections" {
		t.Fatalf("empty analysis = %#v", empty)
	}

	idle := func() *entities.Connection {
		c := entities.CreateConnection("c", nil)
		c.LastActivity = pinned.Add(-time.Hour)
		return c
	}
	active := func() *entities.Connection {
		c := entities.CreateConnection("c", nil)
		c.LastActivity = pinned.Add(-time.Minute)
		return c
	}
	analysis := s.AnalyzeConnectionPatterns([]*entities.Connection{idle(), idle(), active()})
	if analysis["total_connections"] != 3 || analysis["active_connections"] != 1 || analysis["idle_connections"] != 2 {
		t.Fatalf("analysis = %#v", analysis)
	}
	issues := analysis["issues"].([]string)
	if len(issues) != 1 || issues[0] != "More idle connections than active ones" {
		t.Fatalf("issues = %#v", issues)
	}

	many := []*entities.Connection{}
	for i := 0; i < 11; i++ {
		many = append(many, active())
	}
	manyAnalysis := s.AnalyzeConnectionPatterns(many)
	if manyAnalysis["total_connections"] != 11 {
		t.Fatalf("many analysis = %#v", manyAnalysis)
	}
	if len(manyAnalysis["issues"].([]string)) != 1 {
		t.Fatalf("many issues = %#v", manyAnalysis["issues"])
	}

	health, err := s.DiagnoseConnectionHealth(active())
	if err != nil {
		t.Fatal(err)
	}
	if !health.IsHealthy() {
		t.Fatalf("health = %#v, want healthy", health)
	}
}

func unsetenv(t *testing.T, key string) {
	t.Helper()
	old, had := os.LookupEnv(key)
	os.Unsetenv(key)
	t.Cleanup(func() {
		if had {
			os.Setenv(key, old)
		} else {
			os.Unsetenv(key)
		}
	})
}

func TestMCPServerHealthServiceEnvironment(t *testing.T) {
	s := NewMCPServerHealthService()

	// Every name the database gate reads must be cleared, not just the two the old flag tested:
	// a machine with DATABASE_TYPE exported would otherwise decide this case.
	for _, k := range []string{
		"AUTH_ENABLED", "AGENTHUB_DISABLE_CURSOR_TOOLS", "PRODUCTION",
		"DATABASE_TYPE", "DATABASE_HOST", "DATABASE_USER", "DATABASE_PASSWORD",
		"SUPABASE_DB_HOST", "SUPABASE_DB_PASSWORD", "SUPABASE_URL", "DATABASE_URL",
	} {
		unsetenv(t, k)
	}
	defaults := s.GetEnvironmentInfo()
	if defaults["auth_enabled"] != true || defaults["cursor_tools_disabled"] != false ||
		defaults["mvp_mode"] != false || defaults["database_configured"] != false {
		t.Fatalf("defaults = %#v", defaults)
	}
	services := defaults["services_configured"].(map[string]any)
	if services["database"] != false || services["authentication"] != true || services["task_management"] != true {
		t.Fatalf("services_configured = %#v", services)
	}

	t.Setenv("AUTH_ENABLED", "false")
	t.Setenv("AGENTHUB_DISABLE_CURSOR_TOOLS", "TRUE")
	t.Setenv("PRODUCTION", "true")
	// The supported way, not the two names the old flag tested.
	t.Setenv("DATABASE_TYPE", "postgresql")
	t.Setenv("DATABASE_HOST", "db.internal")
	t.Setenv("DATABASE_USER", "agenthub")
	t.Setenv("DATABASE_PASSWORD", "secret")
	got := s.GetEnvironmentInfo()
	if got["auth_enabled"] != false || got["cursor_tools_disabled"] != true ||
		got["mvp_mode"] != true || got["database_configured"] != true {
		t.Fatalf("custom env = %#v", got)
	}
	auth := s.GetAuthenticationStatus()
	if auth["enabled"] != false || auth["mvp_mode"] != true {
		t.Fatalf("auth status = %#v", auth)
	}

	task := s.GetTaskManagementInfo()
	if task["task_management_enabled"] != true || task["enabled_tools_count"] != 0 {
		t.Fatalf("task info = %#v", task)
	}
	config := s.ValidateServerConfiguration()
	if config["status"] != "healthy" || config["broadcasting_enabled"] != true ||
		config["active_connections"] != 0 || config["server_restart_count"] != 0 || config["uptime_seconds"] != 0 {
		t.Fatalf("config = %#v", config)
	}
}

// TestDatabaseConfiguredMirrorsTheServerGate pins the flag to the gate newDatabaseConfig
// enforces: a supported DATABASE_TYPE plus the credentials secureDatabaseURL derives from it.
//
// The first case is the one that matters. The flag used to test SUPABASE_URL and DATABASE_URL,
// names this server does not use for the connection (SUPABASE_URL is the auth variable), so it
// reported database_configured:false on a deployment configured the supported way - a health
// field that can be false on a healthy system, which is worse than no field at all.
func TestDatabaseConfiguredMirrorsTheServerGate(t *testing.T) {
	s := NewMCPServerHealthService()
	dbNames := []string{
		"DATABASE_TYPE", "DATABASE_HOST", "DATABASE_USER", "DATABASE_PASSWORD",
		"SUPABASE_DB_HOST", "SUPABASE_DB_PASSWORD", "SUPABASE_URL", "DATABASE_URL",
	}

	cases := []struct {
		name string
		env  map[string]string
		want bool
	}{
		{"postgresql with its credentials", map[string]string{
			"DATABASE_TYPE": "postgresql", "DATABASE_HOST": "db.internal",
			"DATABASE_USER": "agenthub", "DATABASE_PASSWORD": "secret"}, true},
		{"supabase with its credentials", map[string]string{
			"DATABASE_TYPE": "supabase", "SUPABASE_DB_HOST": "db.example.supabase.co",
			"SUPABASE_DB_PASSWORD": "secret"}, true},
		{"the auth variable alone is not a DSN", map[string]string{"SUPABASE_URL": "http://example"}, false},
		{"DATABASE_URL alone is not the gate the server enforces", map[string]string{
			"DATABASE_URL": "postgresql://u:p@h/db"}, false},
		{"postgresql missing its credentials", map[string]string{
			"DATABASE_TYPE": "postgresql", "DATABASE_HOST": "db.internal"}, false},
		{"no DATABASE_TYPE", map[string]string{
			"DATABASE_HOST": "db.internal", "DATABASE_USER": "agenthub",
			"DATABASE_PASSWORD": "secret"}, false},
		{"unsupported type", map[string]string{
			"DATABASE_TYPE": "mysql", "DATABASE_HOST": "db.internal",
			"DATABASE_USER": "agenthub", "DATABASE_PASSWORD": "secret"}, false},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			for _, k := range dbNames {
				unsetenv(t, k)
			}
			for k, v := range c.env {
				t.Setenv(k, v)
			}
			got := s.GetEnvironmentInfo()
			if got["database_configured"] != c.want {
				t.Fatalf("database_configured = %v, want %v (env %v)", got["database_configured"], c.want, c.env)
			}
			services := got["services_configured"].(map[string]any)
			if services["database"] != c.want {
				t.Fatalf("services_configured.database = %v, want %v", services["database"], c.want)
			}
		})
	}
}

func TestMCPServerHealthServiceCheckHealth(t *testing.T) {
	pinned := time.Date(2026, 3, 1, 10, 0, 0, 0, time.UTC)
	pinConnectionNow(t, pinned)
	server := entities.CreateServer("srv", "1.0", nil, nil, nil)
	server.StartedAt = pinned.Add(-time.Hour)
	status, err := NewMCPServerHealthService().CheckServerHealth(server)
	if err != nil {
		t.Fatal(err)
	}
	if !status.IsHealthy() {
		t.Fatalf("status = %#v, want healthy", status)
	}
}

func TestMCPStatusBroadcastingService(t *testing.T) {
	pinned := time.Date(2026, 3, 1, 10, 0, 0, 500000000, time.UTC)
	pinConnectionNow(t, pinned)
	oldVO := value_objects.Now
	value_objects.Now = func() time.Time { return pinned }
	t.Cleanup(func() { value_objects.Now = oldVO })

	s := NewMCPStatusBroadcastingService()
	if s.GetRegisteredClientsCount() != 0 {
		t.Fatalf("initial registered clients = %d", s.GetRegisteredClientsCount())
	}

	update, err := s.RegisterClientForUpdates("session-1", map[string]any{"agent": "x"})
	if err != nil {
		t.Fatal(err)
	}
	if update.EventType != "client_registered" || update.SessionID != "session-1" {
		t.Fatalf("registration update = %#v", update)
	}
	if s.GetRegisteredClientsCount() != 1 {
		t.Fatalf("registered clients = %d, want 1", s.GetRegisteredClientsCount())
	}

	if s.BroadcastStatusUpdate(update) != true {
		t.Fatalf("BroadcastStatusUpdate = false")
	}
	info := s.GetLastBroadcastInfo()
	if info["last_broadcast_time"] != nil || info["broadcast_count"] != 0 {
		t.Fatalf("last broadcast info = %#v", info)
	}
	infra := s.ValidateBroadcastingInfrastructure()
	if infra["status_broadcaster_available"] != true || infra["registered_clients"] != 1 {
		t.Fatalf("infra = %#v", infra)
	}

	if !s.UnregisterClient("session-1") {
		t.Fatalf("UnregisterClient = false, want true")
	}
	if s.UnregisterClient("session-1") {
		t.Fatalf("UnregisterClient a second time = true, want false")
	}

	if _, err := s.RegisterClientForUpdates("", nil); err == nil {
		t.Fatalf("RegisterClientForUpdates with empty session did not fail")
	}
}
