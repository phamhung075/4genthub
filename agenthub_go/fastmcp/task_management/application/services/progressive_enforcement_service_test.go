package services

import (
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestProgressiveAgentProfileShouldEscalate(t *testing.T) {
	// Python: strict never escalates.
	strict := NewAgentProfile("a", time.Now().UTC(), zpEnfEnforcementLevelStrict, 10)
	strict.ConsecutiveFailures = 99
	if strict.ShouldEscalate() {
		t.Fatalf("strict profile must not escalate")
	}

	// Python: 5+ consecutive failures escalate at warning level.
	warn := NewAgentProfile("a", time.Now().UTC(), zpEnfEnforcementLevelWarning, 10)
	warn.ConsecutiveFailures = 5
	if !warn.ShouldEscalate() {
		t.Fatalf("5 consecutive failures must escalate")
	}

	// Python: after 20 operations, compliance rate < 0.6 escalates.
	low := NewAgentProfile("a", time.Now().UTC(), zpEnfEnforcementLevelSoft, 10)
	low.OperationsCount = 20
	low.ConsecutiveFailures = 0
	low.ComplianceHistory = []bool{false, true, false, true, false, true, false, true, false, true} // 0.5
	if !low.ShouldEscalate() {
		t.Fatalf("compliance 0.5 after 20 ops must escalate")
	}

	// Python: warning level with 10+ warnings escalates.
	warned := NewAgentProfile("a", time.Now().UTC(), zpEnfEnforcementLevelWarning, 10)
	warned.WarningsReceived = 10
	if !warned.ShouldEscalate() {
		t.Fatalf("10 warnings must escalate")
	}
}

func TestProgressiveAgentProfileShouldDeescalate(t *testing.T) {
	soft := NewAgentProfile("a", time.Now().UTC(), zpEnfEnforcementLevelSoft, 10)
	soft.ConsecutiveCompliant = 20
	soft.ComplianceHistory = make([]bool, 20)
	for i := range soft.ComplianceHistory {
		soft.ComplianceHistory[i] = true
	}
	if soft.ShouldDeescalate() {
		t.Fatalf("soft profile must not deescalate")
	}

	warn := NewAgentProfile("a", time.Now().UTC(), zpEnfEnforcementLevelWarning, 10)
	warn.ConsecutiveCompliant = 20
	warn.ComplianceHistory = make([]bool, 20)
	for i := range warn.ComplianceHistory {
		warn.ComplianceHistory[i] = true
	}
	if !warn.ShouldDeescalate() {
		t.Fatalf("100%% compliance over 20 ops must deescalate")
	}
}

func TestProgressiveUpdateComplianceAndHistoryCap(t *testing.T) {
	p := NewAgentProfile("a", time.Now().UTC(), zpEnfEnforcementLevelWarning, 10)
	p.UpdateCompliance(false, true)
	if p.OperationsCount != 1 || p.ConsecutiveFailures != 1 || p.WarningsReceived != 1 {
		t.Fatalf("failure accounting wrong: %+v", p)
	}
	p.UpdateCompliance(true, false)
	if p.ConsecutiveCompliant != 1 || p.ConsecutiveFailures != 0 || p.WarningsReceived != 1 {
		t.Fatalf("success accounting wrong: %+v", p)
	}
	for i := 0; i < 150; i++ {
		p.UpdateCompliance(true, false)
	}
	if len(p.ComplianceHistory) != 100 {
		t.Fatalf("history must cap at 100, got %d", len(p.ComplianceHistory))
	}
}

func TestProgressiveEscalateDeescalateLevels(t *testing.T) {
	p := NewAgentProfile("a", time.Now().UTC(), zpEnfEnforcementLevelSoft, 10)
	p.EscalateLevel()
	if p.EnforcementLevel != zpEnfEnforcementLevelWarning || p.LastEscalation == nil {
		t.Fatalf("soft -> warning expected, got %s", p.EnforcementLevel)
	}
	p.EscalateLevel()
	if p.EnforcementLevel != zpEnfEnforcementLevelStrict {
		t.Fatalf("warning -> strict expected, got %s", p.EnforcementLevel)
	}
	p.DeescalateLevel()
	if p.EnforcementLevel != zpEnfEnforcementLevelWarning || p.ConsecutiveCompliant != 0 {
		t.Fatalf("strict -> warning expected, got %s", p.EnforcementLevel)
	}
	p.DeescalateLevel()
	if p.EnforcementLevel != zpEnfEnforcementLevelSoft {
		t.Fatalf("warning -> soft expected, got %s", p.EnforcementLevel)
	}
}

func TestProgressiveEnforcementStatsKeyOrder(t *testing.T) {
	svc := NewProgressiveEnforcementService(nil, zpEnfEnforcementLevelWarning)
	soft := svc.getOrCreateProfile("soft-agent")
	soft.EnforcementLevel = zpEnfEnforcementLevelSoft
	strict := svc.getOrCreateProfile("strict-agent")
	strict.EnforcementLevel = zpEnfEnforcementLevelStrict
	strict.OperationsCount = 20
	strict.ComplianceHistory = []bool{false, false, false, false, false, false, false, false, false, true} // 0.1

	stats := svc.GetEnforcementStats()
	wantKeys := []string{"total_agents", "by_level", "learning_phase", "average_compliance", "problem_agents"}
	gotKeys := stats.Keys()
	if len(gotKeys) != len(wantKeys) {
		t.Fatalf("keys = %v", gotKeys)
	}
	for i := range wantKeys {
		if gotKeys[i] != wantKeys[i] {
			t.Fatalf("key[%d] = %q want %q", i, gotKeys[i], wantKeys[i])
		}
	}
	if v, _ := stats.Get("total_agents"); v.(int) != 2 {
		t.Fatalf("total_agents = %v", v)
	}
	byLevel, _ := stats.Get("by_level")
	bl := byLevel.(*entities.OrderedMap[any])
	if got := bl.Keys(); len(got) != 3 || got[0] != "soft" || got[1] != "warning" || got[2] != "strict" {
		t.Fatalf("by_level keys = %v", got)
	}
	if v, _ := bl.Get("soft"); v.(int) != 1 {
		t.Fatalf("soft = %v", v)
	}
	if v, _ := bl.Get("strict"); v.(int) != 1 {
		t.Fatalf("strict = %v", v)
	}
}
