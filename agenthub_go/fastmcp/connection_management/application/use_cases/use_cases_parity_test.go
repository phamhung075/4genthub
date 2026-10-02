package use_cases

import (
	"testing"

	"agenthub/fastmcp/connection_management/application/dtos"
	"agenthub/fastmcp/connection_management/infrastructure/repositories"
	infraservices "agenthub/fastmcp/connection_management/infrastructure/services"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

func connKeys(m *tmentities.OrderedMap[any]) []string { return m.Keys() }

func connGet(m *tmentities.OrderedMap[any], k string) any { v, _ := m.Get(k); return v }

func eqStrings(t *testing.T, label string, got, want []string) {
	t.Helper()
	if len(got) != len(want) {
		t.Fatalf("%s: got %v want %v", label, got, want)
	}
	for i := range got {
		if got[i] != want[i] {
			t.Fatalf("%s: got %v want %v", label, got, want)
		}
	}
}

func TestCheckConnectionHealthNoClients(t *testing.T) {
	uc := NewCheckConnectionHealthUseCase(
		repositories.NewInMemoryConnectionRepository(),
		infraservices.NewMCPConnectionDiagnosticsService(),
	)
	resp := uc.Execute(dtos.NewConnectionHealthRequest(nil, nil))

	if !resp.Success || resp.Status != "no_clients" {
		t.Fatalf("success=%v status=%q", resp.Success, resp.Status)
	}
	eqStrings(t, "connection_info keys", connKeys(resp.ConnectionInfo), []string{"active_connections", "total_connections"})
	if connGet(resp.ConnectionInfo, "active_connections") != 0 || connGet(resp.ConnectionInfo, "total_connections") != 0 {
		t.Fatalf("connection_info=%v", connKeys(resp.ConnectionInfo))
	}
	eqStrings(t, "diagnostics keys", connKeys(resp.Diagnostics), []string{
		"active_connections", "total_connections", "server_restart_count", "uptime_seconds", "connection_health",
	})
	if len(resp.Recommendations) != 3 || resp.Recommendations[0] != "Server is running normally" {
		t.Fatalf("recommendations=%v", resp.Recommendations)
	}
}

func TestCheckConnectionHealthMissingID(t *testing.T) {
	uc := NewCheckConnectionHealthUseCase(
		repositories.NewInMemoryConnectionRepository(),
		infraservices.NewMCPConnectionDiagnosticsService(),
	)
	id := "abc"
	resp := uc.Execute(dtos.NewConnectionHealthRequest(&id, nil))
	eqStrings(t, "connection_info keys", connKeys(resp.ConnectionInfo), []string{"error"})
	if connGet(resp.ConnectionInfo, "error") != "Connection abc not found" {
		t.Fatalf("connection_info error=%v", connGet(resp.ConnectionInfo, "error"))
	}
}

func TestGetServerCapabilities(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "true")
	t.Setenv("PRODUCTION", "false")
	uc := NewGetServerCapabilitiesUseCase(
		repositories.NewInMemoryServerRepository(),
		infraservices.NewMCPServerHealthService(),
	)
	resp := uc.Execute(dtos.NewServerCapabilitiesRequest(nil))

	if !resp.Success || resp.Version != "2.1.0" {
		t.Fatalf("success=%v version=%q want=%q", resp.Success, resp.Version, "2.1.0")
	}
	if len(resp.CoreFeatures) != 10 || resp.CoreFeatures[0] != "Task Management" {
		t.Fatalf("core_features=%v", resp.CoreFeatures)
	}
	if resp.TotalActions != 37 {
		t.Fatalf("total_actions=%d", resp.TotalActions)
	}
	if !resp.AuthenticationEnabled || resp.MvpMode {
		t.Fatalf("auth=%v mvp=%v", resp.AuthenticationEnabled, resp.MvpMode)
	}
	eqStrings(t, "available_actions keys", resp.AvailableActions.Keys(), []string{
		"connection_management", "authentication", "project_management",
		"task_management", "subtask_management", "agent_management",
	})
}

func TestRegisterStatusUpdates(t *testing.T) {
	uc := NewRegisterStatusUpdatesUseCase(infraservices.NewMCPStatusBroadcastingService())
	resp := uc.Execute(&dtos.RegisterUpdatesRequest{SessionID: "s1"})

	if !resp.Success || !resp.Registered || resp.SessionID != "s1" {
		t.Fatalf("resp=%+v", resp)
	}
	eqStrings(t, "update_info keys", connKeys(resp.UpdateInfo), []string{
		"registered_clients", "last_broadcast", "registration_time", "event_type",
	})
	if connGet(resp.UpdateInfo, "registered_clients") != 1 {
		t.Fatalf("registered_clients=%v", connGet(resp.UpdateInfo, "registered_clients"))
	}
	if connGet(resp.UpdateInfo, "event_type") != "client_registered" {
		t.Fatalf("event_type=%v", connGet(resp.UpdateInfo, "event_type"))
	}
	lastBroadcast, ok := connGet(resp.UpdateInfo, "last_broadcast").(*tmentities.OrderedMap[any])
	if !ok {
		t.Fatalf("last_broadcast type %T", connGet(resp.UpdateInfo, "last_broadcast"))
	}
	eqStrings(t, "last_broadcast keys", connKeys(lastBroadcast), []string{
		"last_broadcast_time", "last_broadcast_type", "broadcast_count",
	})
}
