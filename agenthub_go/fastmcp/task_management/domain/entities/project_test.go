package entities

import (
	"encoding/json"
	"fmt"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

func jsonOf(t *testing.T, v any) string {
	b, err := json.Marshal(v) // encoding/json sorts map keys like sort_keys=True
	if err != nil {
		t.Fatal(err)
	}
	return string(b)
}

// Expected strings come from running the same scenario on the Python entities
// (floats compared by value: Python prints 100.0 where Go prints 100).
func TestProjectScenarioMatchesPython(t *testing.T) {
	p, err := CreateProject("P", "")
	if err != nil {
		t.Fatal(err)
	}
	b1, _ := p.CreateGitBranch("feat/a", "A", "")
	b2, _ := p.CreateGitBranch("feat/b", "B", "")
	mk := func(n int) *Task {
		id, _ := value_objects.NewTaskId(fmt.Sprintf("00000000-0000-4000-8000-00000000000%d", n))
		task, err := CreateTask(Task{ID: &id, Title: fmt.Sprintf("t%d", n), Description: "d"})
		if err != nil {
			t.Fatal(err)
		}
		return task
	}
	t1, t2, t3 := mk(1), mk(2), mk(3)
	_ = b1.AddRootTask(t1)
	_ = b1.AddRootTask(t2)
	_ = b2.AddRootTask(t3)
	_ = t1.SetStatus(mustTaskStatus("done"))
	ag, _ := CreateAgent("12345678-1234-5678-1234-567812345678", "ag", "d", []AgentCapability{CapabilityTesting}, nil, nil)
	_ = p.RegisterAgent(ag)
	agID := ag.ID.Value
	if err := p.AssignAgentToTree(agID, b1.ID.Value); err != nil {
		t.Fatal(err)
	}
	if err := p.AddCrossTreeDependency(t3.ID.Value, t1.ID.Value); err != nil {
		t.Fatal(err)
	}
	if _, err := p.StartWorkSession(agID, t2.ID.Value, 2.0); err != nil {
		t.Fatal(err)
	}
	wantHealth := `{"counts":{"active_sessions":1,"assigned_agents":1,"blocked_tasks":1,"completed_branches":0,"total_agents":1,"total_branches":2,"total_tasks":3},"health_status":"poor","metrics":{"active_work_ratio":33.33,"agent_utilization":100,"blocked_task_percentage":33.33,"branch_completion_rate":0},"overall_health_score":46.67}`
	if got := jsonOf(t, p.CalculateProjectHealth()); got != wantHealth {
		t.Errorf("health\n got %s\nwant %s", got, wantHealth)
	}
	wantRisk := `{"assessment":"Project shows moderate risk with 33.3% completion","metrics":{"active_sessions":1,"agent_utilization":100,"blocked_ratio":33.33,"completion_rate":33.33},"recommendation":"Review and resolve blockers, ensure adequate agent coverage","risk_level":"medium_risk"}`
	if got := jsonOf(t, p.CheckDeadlineRisk()); got != wantRisk {
		t.Errorf("risk\n got %s\nwant %s", got, wantRisk)
	}
	wantCoord := `{"blocked_tasks":[],"missing_prerequisites":[],"ready_tasks":["00000000-0000-4000-8000-000000000003"],"total_dependencies":1,"validated_dependencies":1}`
	if got := jsonOf(t, p.CoordinateCrossTreeDependencies()); got != wantCoord {
		t.Errorf("coord\n got %s\nwant %s", got, wantCoord)
	}
	if !p.ValidateAgentAssignment(agID, b2.ID.Value) {
		t.Error("validate assignment")
	}
	if next := b1.GetNextTask(); next.Title != "t2" || b1.GetProgressPercentage() != 50.0 {
		t.Error("next task / progress")
	}
	_ = b1.UpdateStatusBasedOnTasks()
	if b1.Status.Value != "todo" {
		t.Error("branch status")
	}
	avail, err := p.GetAvailableWorkForAgent(agID)
	if err != nil || len(avail) != 1 || avail[0].Title != "t2" {
		t.Errorf("available work: %v %v", avail, err)
	}
	if err := p.AssignAgentToTree("nope", b1.ID.Value); err == nil || !strings.Contains(err.Error(), "not registered") {
		t.Error("unregistered agent")
	}
}
