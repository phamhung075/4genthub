package orchestration

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

// TestOrchestratorRouterDelegates mirrors the Python OrchestratorRouter surface:
// the router is a thin delegation layer over ProjectOrchestrator.
func TestOrchestratorRouterDelegates(t *testing.T) {
	project, err := entities.CreateProject("Test Project", "desc")
	if err != nil {
		t.Fatalf("CreateProject: %v", err)
	}

	router := NewOrchestratorRouter(nil)
	if router == nil || router.orchestrator == nil {
		t.Fatal("NewOrchestratorRouter returned nil orchestrator")
	}

	got, err := router.OrchestrateProject(project)
	if err != nil {
		t.Fatalf("OrchestrateProject: %v", err)
	}
	if got["orchestrator_layer"] != "application" {
		t.Errorf("orchestrator_layer = %v, want application", got["orchestrator_layer"])
	}
	if got["conflicts_detected"] != 0 {
		t.Errorf("conflicts_detected = %v, want 0", got["conflicts_detected"])
	}
	if got["available_agents"] != 0 {
		t.Errorf("available_agents = %v, want 0", got["available_agents"])
	}
	if _, ok := got["project_id"]; !ok {
		t.Error("result missing project_id")
	}

	if issues := router.CoordinateCrossTreeDependencies(project); len(issues) != 0 {
		t.Errorf("CoordinateCrossTreeDependencies = %v, want empty", issues)
	}

	balanced, err := router.BalanceWorkload(project)
	if err != nil {
		t.Fatalf("BalanceWorkload: %v", err)
	}
	if balanced["orchestrator_layer"] != "application" {
		t.Errorf("balance orchestrator_layer = %v, want application", balanced["orchestrator_layer"])
	}
}

// TestOrchestrateProjectConvenienceChecksFactory checks the module-level
// convenience function builds the same application-layer orchestrator.
func TestOrchestrateProjectConvenienceChecksFactory(t *testing.T) {
	if GetOrchestrator(nil) == nil {
		t.Fatal("GetOrchestrator(nil) returned nil")
	}
	project, err := entities.CreateProject("P", "")
	if err != nil {
		t.Fatalf("CreateProject: %v", err)
	}
	res, err := OrchestrateProject(project, nil)
	if err != nil {
		t.Fatalf("OrchestrateProject: %v", err)
	}
	if res["orchestrator_layer"] != "application" {
		t.Errorf("orchestrator_layer = %v, want application", res["orchestrator_layer"])
	}
}
