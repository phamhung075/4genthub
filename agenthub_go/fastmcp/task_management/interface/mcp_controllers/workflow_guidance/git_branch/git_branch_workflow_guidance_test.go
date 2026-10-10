package git_branch

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestGitBranchWorkflowGuidanceCreate(t *testing.T) {
	g := &GitBranchWorkflowGuidance{}
	ctx := entities.NewOrderedMap[any]()
	ctx.Set("project_id", "P1")
	ctx.Set("git_branch_id", "B1")
	out := g.GenerateGuidance("create", ctx)

	state, _ := out.Get("current_state")
	sm := state.(*entities.OrderedMap[any])
	if v, _ := sm.Get("phase"); v != "branch_creation" {
		t.Errorf("phase = %v, want branch_creation", v)
	}
	if v, _ := sm.Get("context"); v != "git_branch_management" {
		t.Errorf("context = %v, want git_branch_management", v)
	}

	examples, _ := out.Get("examples")
	ex := examples.([]any)
	if len(ex) != 2 {
		t.Fatalf("examples len = %d, want 2", len(ex))
	}
	code, _ := ex[0].(*entities.OrderedMap[any]).Get("code")
	wantCode := "manage_git_branch(\n    action=\"assign_agent\",\n    project_id=\"P1\",\n    git_branch_id=\"B1\",\n    agent_id=\"@go-dev\"\n)"
	if code != wantCode {
		t.Errorf("examples[0].code = %q, want %q", code, wantCode)
	}

	pg, _ := out.Get("parameter_guidance")
	pgm := pg.(*entities.OrderedMap[any])
	wantKeys := []string{"project_id", "git_branch_id", "agent_id", "title"}
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

func TestGitBranchWorkflowGuidanceDeleteOverridesProjectID(t *testing.T) {
	g := &GitBranchWorkflowGuidance{}
	out := g.GenerateGuidance("delete", nil)
	pg, _ := out.Get("parameter_guidance")
	pgm := pg.(*entities.OrderedMap[any])
	got := pgm.Keys()
	if len(got) == 0 || got[0] != "project_id" {
		t.Fatalf("parameter_guidance keys = %v, want project_id first", got)
	}
	proj, _ := pgm.Get("project_id")
	req, _ := proj.(*entities.OrderedMap[any]).Get("requirement")
	if req != "REQUIRED" {
		t.Errorf("project_id.requirement = %v, want REQUIRED", req)
	}
	warnings, _ := out.Get("warnings")
	if n := len(warnings.([]any)); n != 3 {
		t.Errorf("warnings len = %d, want 3", n)
	}
}
