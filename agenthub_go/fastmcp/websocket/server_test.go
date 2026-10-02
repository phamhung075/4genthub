package websocket

import (
	"context"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

type routeRecord struct {
	path    string
	methods []string
}

type fakeApp struct {
	wsRoutes   []string
	httpRoutes []routeRecord
	startups   []func(ctx context.Context) error
	shutdowns  []func(ctx context.Context) error
}

func (a *fakeApp) AddWebSocketRoute(path string, endpoint WebSocketEndpoint) {
	a.wsRoutes = append(a.wsRoutes, path)
}
func (a *fakeApp) AddHTTPRoute(path string, methods []string, endpoint HTTPHandler) {
	a.httpRoutes = append(a.httpRoutes, routeRecord{path, methods})
}
func (a *fakeApp) OnStartup(handler func(ctx context.Context) error) {
	a.startups = append(a.startups, handler)
}
func (a *fakeApp) OnShutdown(handler func(ctx context.Context) error) {
	a.shutdowns = append(a.shutdowns, handler)
}

type fakeKeycloakAuth struct {
	validation *TokenValidation
	err        error
}

func (f fakeKeycloakAuth) ValidateToken(ctx context.Context, token string) (*TokenValidation, error) {
	return f.validation, f.err
}

func TestNewWebSocketServerRegistersRoutes(t *testing.T) {
	app := &fakeApp{}
	NewWebSocketServer(app, nil)

	if len(app.wsRoutes) != 1 || app.wsRoutes[0] != "/ws/{user_id}" {
		t.Fatalf("wsRoutes = %v", app.wsRoutes)
	}
	if len(app.httpRoutes) != 2 {
		t.Fatalf("httpRoutes = %v", app.httpRoutes)
	}
	if app.httpRoutes[0].path != "/ws/health" || app.httpRoutes[1].path != "/ws/stats" {
		t.Fatalf("http route paths = %v", app.httpRoutes)
	}
	for _, r := range app.httpRoutes {
		if len(r.methods) != 1 || r.methods[0] != "GET" {
			t.Fatalf("methods = %v", r.methods)
		}
	}
}

func TestGetHealthStatusStopped(t *testing.T) {
	s := NewWebSocketServer(&fakeApp{}, nil)
	health := s.GetHealthStatus(context.Background())
	wantKeys := []string{"status", "version", "is_running", "startup_time", "connections", "batch_processing"}
	got := health.Keys()
	for i := range wantKeys {
		if got[i] != wantKeys[i] {
			t.Fatalf("keys = %v, want %v", got, wantKeys)
		}
	}
	if status, _ := health.Get("status"); status != "stopped" {
		t.Fatalf("status = %v", status)
	}
	if v, _ := health.Get("startup_time"); v != nil {
		t.Fatalf("startup_time = %v, want nil", v)
	}
	connections, _ := health.Get("connections")
	conns := connections.(*entities.OrderedMap[any])
	if total, _ := conns.Get("total"); total != 0 {
		t.Fatalf("connections.total = %v", total)
	}
	if active, _ := conns.Get("active_users"); active != 0 {
		t.Fatalf("connections.active_users = %v", active)
	}
}

func TestStartStopHealth(t *testing.T) {
	s := NewWebSocketServer(&fakeApp{}, nil)
	ctx := context.Background()
	if err := s.Start(ctx); err != nil {
		t.Fatalf("Start: %v", err)
	}
	if !s.IsRunning || s.StartupTime == nil {
		t.Fatalf("server should be running with a startup time")
	}
	health := s.GetHealthStatus(ctx)
	if status, _ := health.Get("status"); status != "healthy" {
		t.Fatalf("status = %v", status)
	}
	if v, _ := health.Get("is_running"); v != true {
		t.Fatalf("is_running = %v", v)
	}
	if !strings.HasSuffix(*s.StartupTime, "+00:00") {
		t.Fatalf("startup_time = %q, want isoformat with +00:00", *s.StartupTime)
	}
	s.Stop(ctx)
	if s.IsRunning || s.StartupTime != nil {
		t.Fatalf("server should be stopped")
	}
}

func TestGetDetailedStats(t *testing.T) {
	s := NewWebSocketServer(&fakeApp{}, nil)
	stats := s.GetDetailedStats(context.Background())
	wantKeys := []string{"server", "connections", "batch_processing", "protocol"}
	got := stats.Keys()
	for i := range wantKeys {
		if got[i] != wantKeys[i] {
			t.Fatalf("keys = %v, want %v", got, wantKeys)
		}
	}
	protocolAny, _ := stats.Get("protocol")
	protocol := protocolAny.(*entities.OrderedMap[any])
	if v, _ := protocol.Get("version"); v != "2.0" {
		t.Fatalf("protocol.version = %v", v)
	}
	typesAny, _ := protocol.Get("supported_message_types")
	types := typesAny.([]any)
	if len(types) != 5 || types[0] != "update" || types[4] != "error" {
		t.Fatalf("supported_message_types = %v", types)
	}
	sourcesAny, _ := protocol.Get("supported_sources")
	sources := sourcesAny.([]any)
	if len(sources) != 3 || sources[0] != "user" || sources[1] != "mcp-ai" || sources[2] != "system" {
		t.Fatalf("supported_sources = %v", sources)
	}
	if v, _ := protocol.Get("max_message_size_bytes"); v != 64*1024 {
		t.Fatalf("max_message_size_bytes = %v", v)
	}
}

func TestBroadcastAndSendMessageToUser(t *testing.T) {
	s := NewWebSocketServer(&fakeApp{}, nil)
	ctx := context.Background()

	if ok, _ := s.BroadcastMessage(ctx, nil); ok {
		t.Fatalf("BroadcastMessage before start = true")
	}
	if err := s.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer s.Stop(ctx)

	if ok, _ := s.BroadcastMessage(ctx, nil); ok {
		t.Fatalf("BroadcastMessage with no connections = true")
	}
	ws := &fakeWebSocket{}
	if _, err := s.ConnectionManager.Connect(ctx, ws, "u1", nil); err != nil {
		t.Fatal(err)
	}
	if ok, _ := s.BroadcastMessage(ctx, nil); !ok {
		t.Fatalf("BroadcastMessage with a connection = false")
	}
	if ok, _ := s.SendMessageToUser(ctx, "u1", nil); !ok {
		t.Fatalf("SendMessageToUser(connected) = false")
	}
	if ok, _ := s.SendMessageToUser(ctx, "missing", nil); ok {
		t.Fatalf("SendMessageToUser(disconnected) = true")
	}
	if s.GetConnectionCount() != 1 {
		t.Fatalf("GetConnectionCount = %d", s.GetConnectionCount())
	}
}

func TestHandleWebSocketConnectionAuth(t *testing.T) {
	original := NewKeycloakAuth
	defer func() { NewKeycloakAuth = original }()

	ctx := context.Background()
	s := NewWebSocketServer(&fakeApp{}, nil)

	NewKeycloakAuth = func() KeycloakAuth { return fakeKeycloakAuth{validation: &TokenValidation{Valid: false}} }
	invalid := &fakeWebSocket{}
	s.handleWebSocketConnection(ctx, invalid, "u1", "tok")
	if invalid.closeCode != 1008 || invalid.closeReason != "Invalid token" {
		t.Fatalf("invalid token close = %d %q", invalid.closeCode, invalid.closeReason)
	}

	other := "other"
	NewKeycloakAuth = func() KeycloakAuth {
		return fakeKeycloakAuth{validation: &TokenValidation{Valid: true, UserID: &other}}
	}
	mismatch := &fakeWebSocket{}
	s.handleWebSocketConnection(ctx, mismatch, "u1", "tok")
	if mismatch.closeCode != 1008 || mismatch.closeReason != "User ID mismatch" {
		t.Fatalf("mismatch close = %d %q", mismatch.closeCode, mismatch.closeReason)
	}

	user := "u1"
	NewKeycloakAuth = func() KeycloakAuth { return fakeKeycloakAuth{validation: &TokenValidation{Valid: true, UserID: &user}} }
	ok := &fakeWebSocket{}
	s.handleWebSocketConnection(ctx, ok, "u1", "tok")
	if !ok.accepted {
		t.Fatalf("valid connection was not accepted")
	}
	if ok.closeCode != 1000 {
		t.Fatalf("valid connection close code = %d, want 1000", ok.closeCode)
	}
	if s.IsUserConnected("u1") {
		t.Fatalf("connection should be cleaned up after disconnect")
	}
}
