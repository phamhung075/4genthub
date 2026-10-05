package websocket

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestGetWebSocketEndpointsInfo(t *testing.T) {
	info := GetWebSocketEndpointsInfo()
	wantKeys := []string{"websocket_endpoint", "health_endpoint", "stats_endpoint", "protocol_version", "authentication", "supported_message_types", "features"}
	got := info.Keys()
	for i := range wantKeys {
		if got[i] != wantKeys[i] {
			t.Fatalf("keys = %v, want %v", got, wantKeys)
		}
	}
	if v, _ := info.Get("websocket_endpoint"); v != "/ws/{user_id}" {
		t.Fatalf("websocket_endpoint = %v", v)
	}
	if v, _ := info.Get("protocol_version"); v != "2.0" {
		t.Fatalf("protocol_version = %v", v)
	}
	typesAny, _ := info.Get("supported_message_types")
	types := typesAny.([]any)
	if len(types) != 5 || types[0] != "update" || types[4] != "error" {
		t.Fatalf("supported_message_types = %v", types)
	}
	featuresAny, _ := info.Get("features")
	if features := featuresAny.([]any); len(features) != 6 {
		t.Fatalf("features = %v", features)
	}
}

func TestAddWebSocketHealthToMainHealthNotConfigured(t *testing.T) {
	main := wsDict("status", "healthy")
	result := AddWebSocketHealthToMainHealth(context.Background(), main, nil)
	websocketAny, _ := result.Get("websocket")
	websocket := websocketAny.(*entities.OrderedMap[any])
	if v, _ := websocket.Get("status"); v != "not_configured" {
		t.Fatalf("websocket.status = %v", v)
	}
}

func TestAddWebSocketHealthToMainHealthConfigured(t *testing.T) {
	server := NewWebSocketServer(&fakeApp{}, nil)
	main := wsDict("status", "healthy")
	result := AddWebSocketHealthToMainHealth(context.Background(), main, server)

	websocketAny, _ := result.Get("websocket")
	websocket := websocketAny.(*entities.OrderedMap[any])
	wantKeys := []string{"status", "version", "connections", "active_users", "batch_processing"}
	got := websocket.Keys()
	for i := range wantKeys {
		if got[i] != wantKeys[i] {
			t.Fatalf("keys = %v, want %v", got, wantKeys)
		}
	}
	if v, _ := websocket.Get("status"); v != "stopped" {
		t.Fatalf("status = %v", v)
	}
	if v, _ := websocket.Get("version"); v != "2.0" {
		t.Fatalf("version = %v", v)
	}
	if v, _ := websocket.Get("connections"); v != 0 {
		t.Fatalf("connections = %v", v)
	}
	if v, _ := websocket.Get("batch_processing"); v != false {
		t.Fatalf("batch_processing = %v", v)
	}
}

func TestSetupWebSocketIntegrationRequiresFactory(t *testing.T) {
	resetGlobalWebSocketServer()
	if _, err := SetupWebSocketIntegration(context.Background(), &fakeApp{}, nil); err == nil {
		t.Fatalf("SetupWebSocketIntegration(nil factory) should fail")
	}
}

func TestSetupWebSocketIntegrationRegistersHooks(t *testing.T) {
	resetGlobalWebSocketServer()
	defer resetGlobalWebSocketServer()

	app := &fakeApp{}
	factory := SessionFactory(func() (DBSession, error) { return nil, nil })
	server, err := SetupWebSocketIntegration(context.Background(), app, factory)
	if err != nil {
		t.Fatalf("SetupWebSocketIntegration: %v", err)
	}
	if server == nil {
		t.Fatalf("server should be returned")
	}
	if GetWebSocketServer() != server {
		t.Fatalf("global server was not initialized")
	}
	if len(app.startups) != 1 || len(app.shutdowns) != 1 {
		t.Fatalf("hooks: startups=%d shutdowns=%d", len(app.startups), len(app.shutdowns))
	}

	ctx := context.Background()
	if err := app.startups[0](ctx); err != nil {
		t.Fatalf("startup hook: %v", err)
	}
	if !server.IsRunning {
		t.Fatalf("startup hook should start the server")
	}
	if err := app.shutdowns[0](ctx); err != nil {
		t.Fatalf("shutdown hook: %v", err)
	}
	if server.IsRunning {
		t.Fatalf("shutdown hook should stop the server")
	}
}

func resetGlobalWebSocketServer() {
	websocketServerMu.Lock()
	websocketServer = nil
	websocketServerMu.Unlock()
}
