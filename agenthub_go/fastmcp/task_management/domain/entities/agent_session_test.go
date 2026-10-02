package entities

import (
	"testing"
)

func TestAgentSessionHealthAndLifecycle(t *testing.T) {
	if _, err := NewAgentSession(AgentSessionOptions{}); err == nil || err.Error() != "Session agent_id cannot be empty" {
		t.Fatalf("agent id: %v", err)
	}
	zero := 0
	if _, err := NewAgentSession(AgentSessionOptions{AgentID: "a", HeartbeatInterval: &zero}); err == nil || err.Error() != "heartbeat_interval must be greater than 0" {
		t.Fatalf("heartbeat: %v", err)
	}
	s, err := NewAgentSession(AgentSessionOptions{AgentID: "a"})
	if err != nil {
		t.Fatal(err)
	}
	if err := s.Activate(); err != nil || s.State != SessionStateActive {
		t.Fatal("activate")
	}
	if err := s.Activate(); err == nil || err.Error() != "Cannot activate session in state active" {
		t.Fatalf("re-activate: %v", err)
	}
	id := "r1"
	s.AllocateResource(ResourceAPIQuota, 100, &id)
	s.UpdateResourceUsage(ResourceAPIQuota, 95, &id)
	_ = s.StartTask("t1")
	_ = s.CompleteTask("t1", false)
	s.Metrics.ErrorCount = 1
	// resource 95% → -30; errors 1/(0+1+0)=100% → -30; failures 100% → -20 → 20.0
	if got := s.CalculateHealthScore(); got != 20.0 {
		t.Fatalf("health %v", got)
	}
	if !s.NeedsRecovery() {
		t.Fatal("needs recovery")
	}
	_ = s.Recover()
	if s.Metrics.RecoveryCount != 1 || s.Metrics.ErrorCount != 0 {
		t.Fatal("recover")
	}
	if r, _ := s.Resources.Get("api_quota_r1"); r.UsedAmount != 50 {
		t.Fatalf("overutilized reset: %v", r.UsedAmount)
	}
	_ = s.Terminate("Normal termination")
	if s.State != SessionStateTerminated || s.Resources.Len() != 0 || s.ResourceLocks.Len() != 0 || s.IsAlive() {
		t.Fatal("terminate")
	}
}
