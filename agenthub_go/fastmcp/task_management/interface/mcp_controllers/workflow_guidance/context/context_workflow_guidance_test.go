package context

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestContextWorkflowGuidanceCreate(t *testing.T) {
	g := &ContextWorkflowGuidance{}
	ctx := entities.NewOrderedMap[any]()
	ctx.Set("task_id", "T1")
	out := g.GenerateGuidance("create", ctx)

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
	if v, _ := sm.Get("phase"); v != "creating_context" {
		t.Errorf("phase = %v, want creating_context", v)
	}
	if v, _ := sm.Get("action"); v != "create" {
		t.Errorf("action = %v, want create", v)
	}
	if _, ok := sm.Get("context"); ok {
		t.Errorf("current_state should not have context key")
	}

	next, _ := out.Get("next_actions")
	na := next.([]any)
	if len(na) != 2 {
		t.Fatalf("next_actions len = %d, want 2", len(na))
	}
	ex, _ := na[0].(*entities.OrderedMap[any]).Get("example")
	exm := ex.(*entities.OrderedMap[any])
	params, _ := exm.Get("params")
	if v, _ := params.(*entities.OrderedMap[any]).Get("task_id"); v != "T1" {
		t.Errorf("next_actions[0].params.task_id = %v, want T1", v)
	}

	examples, _ := out.Get("examples")
	em := examples.(*entities.OrderedMap[any])
	if got := em.Keys(); len(got) != 2 || got[0] != "basic_create" || got[1] != "detailed_create" {
		t.Fatalf("examples keys = %v", got)
	}
	basic, _ := em.Get("basic_create")
	cmd, _ := basic.(*entities.OrderedMap[any]).Get("command")
	if cmd != "manage_context(action='create', task_id='T1', project_id='your_project')" {
		t.Errorf("command = %q", cmd)
	}

	pg, _ := out.Get("parameter_guidance")
	pgm := pg.(*entities.OrderedMap[any])
	if got := pgm.Keys(); len(got) != 2 || got[0] != "applicable_parameters" || got[1] != "parameter_tips" {
		t.Fatalf("parameter_guidance keys = %v", got)
	}
	ap, _ := pgm.Get("applicable_parameters")
	want := []any{"task_id", "user_id", "project_id", "git_branch_name", "data_title", "data_description", "data_status", "data_priority"}
	got := ap.([]any)
	if len(got) != len(want) {
		t.Fatalf("applicable_parameters = %v, want %v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("applicable_parameters[%d] = %v, want %v", i, got[i], want[i])
		}
	}
}

func TestContextWorkflowGuidanceDeleteWarningAndDefaultTask(t *testing.T) {
	g := &ContextWorkflowGuidance{}
	out := g.GenerateGuidance("delete", nil)
	warnings, _ := out.Get("warnings")
	if n := len(warnings.([]any)); n != 2 {
		t.Errorf("warnings len = %d, want 2", n)
	}
	examples, _ := out.Get("examples")
	em := examples.(*entities.OrderedMap[any])
	general, _ := em.Get("general")
	cmd, _ := general.(*entities.OrderedMap[any]).Get("command")
	if cmd != "manage_context(action='delete', task_id='your-task-id')" {
		t.Errorf("command = %q", cmd)
	}
}
