package controllers

import (
	"testing"

	"agenthub/fastmcp/connection_management/application/dtos"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

func connCtlTestOD(pairs ...any) *tmentities.OrderedMap[any] {
	m := tmentities.NewOrderedMap[any]()
	for i := 0; i < len(pairs); i += 2 {
		m.Set(pairs[i].(string), pairs[i+1])
	}
	return m
}

func TestFormatHealthCheckResponseSanitizes(t *testing.T) {
	response := &dtos.HealthCheckResponse{
		Success:    true,
		Status:     "healthy",
		ServerName: "agenthub",
		Version:    "0.0.2c",
		Timestamp:  123.5,
		Authentication: connCtlTestOD(
			"enabled", true, "mvp_mode", false, "secret_token", "leak",
		),
		TaskManagement: connCtlTestOD("task_management_enabled", true, "internal", "x"),
		Environment: connCtlTestOD(
			"auth_enabled", true, "mvp_mode", false, "database_configured", true,
			"SECRET", "nope", "services_configured", map[string]any{"database": true},
		),
		Connections: connCtlTestOD(
			"active_connections", 2, "status", "healthy", "internal_debug", "x",
		),
	}

	out := connCtlFormatHealthCheckResponse(response)

	wantKeys := []string{"success", "status", "server_name", "version", "timestamp", "authentication", "task_management", "environment", "connections"}
	if len(out.Keys()) != len(wantKeys) {
		t.Fatalf("keys=%v", out.Keys())
	}
	for i, k := range wantKeys {
		if out.Keys()[i] != k {
			t.Fatalf("keys=%v want=%v", out.Keys(), wantKeys)
		}
	}

	auth, _ := out.Get("authentication")
	authMap := auth.(*tmentities.OrderedMap[any])
	if authMap.Len() != 2 || authMap.Keys()[0] != "enabled" || authMap.Keys()[1] != "mvp_mode" {
		t.Fatalf("authentication keys=%v", authMap.Keys())
	}
	if v, _ := authMap.Get("enabled"); v != true {
		t.Fatalf("enabled=%v", v)
	}

	tm, _ := out.Get("task_management")
	tmMap := tm.(*tmentities.OrderedMap[any])
	if tmMap.Len() != 1 {
		t.Fatalf("task_management keys=%v", tmMap.Keys())
	}
	if v, _ := tmMap.Get("task_management_enabled"); v != true {
		t.Fatalf("task_management_enabled=%v", v)
	}

	env, _ := out.Get("environment")
	envMap := env.(*tmentities.OrderedMap[any])
	if len(envMap.Keys()) != 4 {
		t.Fatalf("environment keys=%v", envMap.Keys())
	}
	// SECRET is not in the allowed key list.
	if envMap.Has("SECRET") {
		t.Fatal("SECRET leaked into environment")
	}

	conns, _ := out.Get("connections")
	connsMap := conns.(*tmentities.OrderedMap[any])
	if len(connsMap.Keys()) != 2 || connsMap.Has("internal_debug") {
		t.Fatalf("connections keys=%v", connsMap.Keys())
	}
}

func TestFormatHealthCheckResponseError(t *testing.T) {
	response := &dtos.HealthCheckResponse{Success: false, Timestamp: 7}
	out := connCtlFormatHealthCheckResponse(response)
	want := []string{"success", "status", "message", "timestamp"}
	if len(out.Keys()) != len(want) {
		t.Fatalf("keys=%v", out.Keys())
	}
	for i, k := range want {
		if out.Keys()[i] != k {
			t.Fatalf("keys=%v want=%v", out.Keys(), want)
		}
	}
	if v, _ := out.Get("message"); v != "Health check failed" {
		t.Fatalf("message=%v", v)
	}
}
