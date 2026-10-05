package entities

import "testing"

const agentUUID = "12345678-1234-5678-1234-567812345678"

func TestAgentLifecycle(t *testing.T) {
	a, err := CreateAgent(agentUUID, "A", "d", []AgentCapability{CapabilityTesting}, []string{"Rust_Lang"}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if !a.ValidateCapabilityMatch([]string{"TESTING", "rust lang"}) || a.ValidateCapabilityMatch([]string{"devops"}) {
		t.Fatal("capability match")
	}
	if err := a.StartTask("t1"); err != nil || a.Status != AgentStatusBusy {
		t.Fatalf("start: %v %v", err, a.Status)
	}
	if err := a.StartTask("t2"); err == nil || err.Error() != "Agent "+agentUUID+" is not available for new tasks" {
		t.Fatalf("start2: %v", err)
	}
	if err := a.CompleteTask("t1", false); err != nil {
		t.Fatal(err)
	}
	if *a.SuccessRate != 90.0 || a.Status != AgentStatusAvailable {
		t.Fatalf("complete: %v %v", *a.SuccessRate, a.Status)
	}
	av := a.CheckAvailability()
	if av["workload_score"] != 0.0 || av["estimated_capacity"] != 1 {
		t.Fatalf("avail: %v", av)
	}
	s, _ := a.CalculateTaskSuitabilityScore(TaskRequirements{Capabilities: []string{"testing", "bogus"}, Priority: "high"})
	if s != 50+20+10+9+10 {
		t.Fatalf("score %v", s)
	}
	if _, err := NewAgent(Agent{Name: "x"}); err == nil || err.Error() != "Agent id cannot be empty" {
		t.Fatalf("validate: %v", err)
	}
}
