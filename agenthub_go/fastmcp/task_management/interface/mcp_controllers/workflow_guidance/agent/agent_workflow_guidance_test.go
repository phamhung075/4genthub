package agent

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestAgentWorkflowGuidanceRegister(t *testing.T) {
	g := &AgentWorkflowGuidanceImpl{}
	ctx := entities.NewOrderedMap[any]()
	ctx.Set("project_id", "P1")
	out := g.GenerateGuidance("register", ctx)

	wantKeys := []string{"current_state", "rules", "next_actions", "hints", "warnings", "examples", "parameter_guidance"}
	gotKeys := out.Keys()
	if len(gotKeys) != len(wantKeys) {
		t.Fatalf("keys = %v, want %v", gotKeys, wantKeys)
	}
	for i := range wantKeys {
		if gotKeys[i] != wantKeys[i] {
			t.Fatalf("key[%d] = %q, want %q", i, gotKeys[i], wantKeys[i])
		}
	}

	state, _ := out.Get("current_state")
	sm := state.(*entities.OrderedMap[any])
	if v, _ := sm.Get("phase"); v != "agent_registration" {
		t.Errorf("phase = %v, want agent_registration", v)
	}
	if v, _ := sm.Get("action"); v != "register" {
		t.Errorf("action = %v, want register", v)
	}
	if v, _ := sm.Get("context"); v != "agent_management" {
		t.Errorf("context = %v, want agent_management", v)
	}

	rules, _ := out.Get("rules")
	if n := len(rules.([]any)); n != 8 {
		t.Errorf("rules len = %d, want 8", n)
	}

	next, _ := out.Get("next_actions")
	na := next.([]any)
	if len(na) != 3 {
		t.Fatalf("next_actions len = %d, want 3", len(na))
	}
	first := na[0].(*entities.OrderedMap[any])
	if v, _ := first.Get("priority"); v != "high" {
		t.Errorf("next_actions[0].priority = %v, want high", v)
	}
	ex, _ := first.Get("example")
	exm := ex.(*entities.OrderedMap[any])
	if v, _ := exm.Get("tool"); v != "manage_git_branch" {
		t.Errorf("example.tool = %v, want manage_git_branch", v)
	}
	params, _ := exm.Get("params")
	pm := params.(*entities.OrderedMap[any])
	if v, _ := pm.Get("project_id"); v != "P1" {
		t.Errorf("params.project_id = %v, want P1", v)
	}

	hints, _ := out.Get("hints")
	if n := len(hints.([]any)); n != 3 {
		t.Errorf("hints len = %d, want 3", n)
	}
	warnings, _ := out.Get("warnings")
	if n := len(warnings.([]any)); n != 2 {
		t.Errorf("warnings len = %d, want 2", n)
	}
	examples, _ := out.Get("examples")
	if n := len(examples.([]any)); n != 1 {
		t.Errorf("examples len = %d, want 1", n)
	}

	pg, _ := out.Get("parameter_guidance")
	pgm := pg.(*entities.OrderedMap[any])
	wantPG := []string{"project_id", "name", "agent_id", "call_agent"}
	gotPG := pgm.Keys()
	if len(gotPG) != len(wantPG) {
		t.Fatalf("parameter_guidance keys = %v, want %v", gotPG, wantPG)
	}
	for i := range wantPG {
		if gotPG[i] != wantPG[i] {
			t.Fatalf("parameter_guidance key[%d] = %q, want %q", i, gotPG[i], wantPG[i])
		}
	}
}

func TestAgentWorkflowGuidanceUnknownAction(t *testing.T) {
	g := &AgentWorkflowGuidanceImpl{}
	out := g.GenerateGuidance("bogus", nil)
	state, _ := out.Get("current_state")
	sm := state.(*entities.OrderedMap[any])
	if v, _ := sm.Get("phase"); v != "unknown" {
		t.Errorf("phase = %v, want unknown", v)
	}
	next, _ := out.Get("next_actions")
	if n := len(next.([]any)); n != 0 {
		t.Errorf("next_actions len = %d, want 0", n)
	}
	hints, _ := out.Get("hints")
	if n := len(hints.([]any)); n != 1 {
		t.Errorf("hints len = %d, want 1 (default)", n)
	}
}
