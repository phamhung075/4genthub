package workflow_guidance

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestBaseWorkflowGuidanceDefaults(t *testing.T) {
	var g BaseWorkflowGuidance
	out := g.GenerateGuidance("op", nil)

	wantKeys := []string{"current_state", "rules", "next_actions", "hints", "warnings", "examples", "parameter_guidance"}
	got := out.Keys()
	if len(got) != len(wantKeys) {
		t.Fatalf("keys = %v, want %v", got, wantKeys)
	}
	for i := range wantKeys {
		if got[i] != wantKeys[i] {
			t.Fatalf("key[%d] = %q, want %q", i, got[i], wantKeys[i])
		}
	}

	state, _ := out.Get("current_state")
	sm := state.(*entities.OrderedMap[any])
	if v, _ := sm.Get("phase"); v != "operation" {
		t.Errorf("phase = %v, want operation", v)
	}
	if v, _ := sm.Get("action"); v != "op" {
		t.Errorf("action = %v, want op", v)
	}

	for _, k := range []string{"rules", "next_actions", "hints", "warnings"} {
		v, _ := out.Get(k)
		if n := len(v.([]any)); n != 0 {
			t.Errorf("%s len = %d, want 0", k, n)
		}
	}
	examples, _ := out.Get("examples")
	if n := examples.(*entities.OrderedMap[any]).Len(); n != 0 {
		t.Errorf("examples len = %d, want 0", n)
	}
	pg, _ := out.Get("parameter_guidance")
	pgm := pg.(*entities.OrderedMap[any])
	ap, _ := pgm.Get("applicable_parameters")
	if n := len(ap.([]any)); n != 0 {
		t.Errorf("applicable_parameters len = %d, want 0", n)
	}
	tips, _ := pgm.Get("parameter_tips")
	if n := tips.(*entities.OrderedMap[any]).Len(); n != 0 {
		t.Errorf("parameter_tips len = %d, want 0", n)
	}
}

func TestContextHelpers(t *testing.T) {
	ctx := entities.NewOrderedMap[any]()
	ctx.Set("a", "x")
	if v := ContextGet(ctx, "a"); v != "x" {
		t.Errorf("ContextGet = %v, want x", v)
	}
	if v := ContextGet(ctx, "missing"); v != nil {
		t.Errorf("ContextGet missing = %v, want nil", v)
	}
	empty := entities.NewOrderedMap[any]()
	if v := ContextGet(empty, "a"); v != nil {
		t.Errorf("ContextGet empty = %v, want nil", v)
	}
	if v := ContextGetDefault(empty, "a", "def"); v != "def" {
		t.Errorf("ContextGetDefault = %v, want def", v)
	}
	if v := ContextGetStringDefault(ctx, "missing", "def"); v != "def" {
		t.Errorf("ContextGetStringDefault = %v, want def", v)
	}
	if v := OrString("", "fallback"); v != "fallback" {
		t.Errorf("OrString empty = %v, want fallback", v)
	}
	if v := OrValue("value", "fallback"); v != "value" {
		t.Errorf("OrValue = %v, want value", v)
	}
}
