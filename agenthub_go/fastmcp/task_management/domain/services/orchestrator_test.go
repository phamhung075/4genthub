package services

import (
	"errors"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

const orchAgentID = "00000000-0000-4000-8000-0000000000a1"

func orchProject(t *testing.T) *entities.Project {
	t.Helper()
	p, err := entities.CreateProject("P", "d")
	if err != nil {
		t.Fatal(err)
	}
	return p
}

func orchAgent(t *testing.T, p *entities.Project) *entities.Agent {
	t.Helper()
	a, err := entities.CreateAgent(orchAgentID, "A1", "agent one",
		[]entities.AgentCapability{entities.CapabilityFrontendDevelopment}, nil, []string{"typescript"})
	if err != nil {
		t.Fatal(err)
	}
	if err := p.RegisterAgent(a); err != nil {
		t.Fatal(err)
	}
	return a
}

// Python: an unassigned branch meeting an available agent raises
// ValueError("Agent <uuid> not registered") because AgentId objects never match str keys.
func TestOrchestrateProjectUnassignedBranchRaisesNotRegistered(t *testing.T) {
	p := orchProject(t)
	if _, err := p.CreateGitBranch("feature-ui", "UI branch", "d"); err != nil {
		t.Fatal(err)
	}
	orchAgent(t, p)
	_, err := NewOrchestrator(nil).OrchestrateProject(p)
	var ve *value_objects.ValueError
	if !errors.As(err, &ve) || !strings.Contains(err.Error(), "Agent "+orchAgentID+" not registered") {
		t.Fatalf("got %v", err)
	}
}

func TestOrchestrateProjectNoBranchesReturnsCounts(t *testing.T) {
	p := orchProject(t)
	orchAgent(t, p)
	r, err := NewOrchestrator(nil).OrchestrateProject(p)
	if err != nil {
		t.Fatal(err)
	}
	if r["conflicts_detected"] != 0 || r["active_sessions"] != 0 || r["available_agents"] != 1 {
		t.Fatalf("got %v", r)
	}
	if _, ok := r["orchestration_timestamp"].(string); !ok {
		t.Fatal("missing timestamp")
	}
}

func TestBalanceWorkloadNoAgentsZeroDivision(t *testing.T) {
	_, err := NewOrchestrator(nil).BalanceWorkload(orchProject(t))
	if !errors.Is(err, entities.ErrZeroDivision) {
		t.Fatalf("got %v", err)
	}
}

func TestBalanceWorkloadIdleAgentIsUnderloaded(t *testing.T) {
	p := orchProject(t)
	orchAgent(t, p)
	r, err := NewOrchestrator(nil).BalanceWorkload(p)
	if err != nil {
		t.Fatal(err)
	}
	a := r["workload_analysis"].(map[string]any)
	if len(a["overloaded_agents"].([]*value_objects.AgentId)) != 0 ||
		len(a["underloaded_agents"].([]*value_objects.AgentId)) != 1 || a["average_workload"] != 0.0 {
		t.Fatalf("got %v", a)
	}
}

func TestCoordinateCrossTreeDependenciesNoDeps(t *testing.T) {
	issues := NewOrchestrator(nil).CoordinateCrossTreeDependencies(orchProject(t))
	if issues == nil || len(issues) != 0 {
		t.Fatalf("got %#v", issues)
	}
}
