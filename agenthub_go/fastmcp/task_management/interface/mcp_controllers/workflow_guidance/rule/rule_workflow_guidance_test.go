package rule

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestRuleWorkflowGuidanceParseRule(t *testing.T) {
	g := &RuleWorkflowGuidance{}
	ctx := entities.NewOrderedMap[any]()
	ctx.Set("target", "T")
	out := g.GenerateGuidance("parse_rule", ctx)

	state, _ := out.Get("current_state")
	sm := state.(*entities.OrderedMap[any])
	if v, _ := sm.Get("phase"); v != "rule_parsing" {
		t.Errorf("phase = %v, want rule_parsing", v)
	}
	if v, _ := sm.Get("context"); v != "rule_management" {
		t.Errorf("context = %v, want rule_management", v)
	}

	next, _ := out.Get("next_actions")
	na := next.([]any)
	if len(na) != 2 {
		t.Fatalf("next_actions len = %d, want 2", len(na))
	}
	ex, _ := na[0].(*entities.OrderedMap[any]).Get("example")
	params, _ := ex.(*entities.OrderedMap[any]).Get("params")
	if v, _ := params.(*entities.OrderedMap[any]).Get("target"); v != "T" {
		t.Errorf("target = %v, want T", v)
	}

	pg, _ := out.Get("parameter_guidance")
	pgm := pg.(*entities.OrderedMap[any])
	wantKeys := []string{"action", "target", "content"}
	got := pgm.Keys()
	if len(got) != len(wantKeys) {
		t.Fatalf("parameter_guidance keys = %v, want %v", got, wantKeys)
	}
	for i := range wantKeys {
		if got[i] != wantKeys[i] {
			t.Fatalf("key[%d] = %q, want %q", i, got[i], wantKeys[i])
		}
	}
}

func TestRuleWorkflowGuidanceParameterGuidanceBranches(t *testing.T) {
	g := &RuleWorkflowGuidance{}

	listOut := g.GenerateGuidance("list", nil)
	pg, _ := listOut.Get("parameter_guidance")
	pgm := pg.(*entities.OrderedMap[any])
	if got := pgm.Keys(); len(got) != 1 || got[0] != "action" {
		t.Fatalf("list parameter_guidance keys = %v, want [action]", got)
	}

	unknownOut := g.GenerateGuidance("made_up", nil)
	pg2, _ := unknownOut.Get("parameter_guidance")
	pgm2 := pg2.(*entities.OrderedMap[any])
	want := []string{"action", "target", "content"}
	got2 := pgm2.Keys()
	if len(got2) != len(want) {
		t.Fatalf("unknown parameter_guidance keys = %v, want %v", got2, want)
	}
	for i := range want {
		if got2[i] != want[i] {
			t.Fatalf("unknown key[%d] = %q, want %q", i, got2[i], want[i])
		}
	}
}
