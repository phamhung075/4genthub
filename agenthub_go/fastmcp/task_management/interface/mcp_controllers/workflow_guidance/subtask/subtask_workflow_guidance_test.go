package subtask

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestEnhanceResponseFailureReturnedUnchanged(t *testing.T) {
	response := entities.NewOrderedMap[any]()
	response.Set("success", false)

	got := (&SubtaskWorkflowGuidance{}).EnhanceResponse(response, "list", entities.NewOrderedMap[any]())
	if got != response {
		t.Fatal("expected same response pointer")
	}
	if got.Has("workflow_guidance") {
		t.Fatal("workflow_guidance must not be added on failure")
	}
}

func TestEnhanceResponseListState(t *testing.T) {
	response := entities.NewOrderedMap[any]()
	response.Set("success", true)
	done := entities.NewOrderedMap[any]()
	done.Set("status", "done")
	done.Set("assignees", []any{"agent"})
	todo := entities.NewOrderedMap[any]()
	todo.Set("status", "todo")
	response.Set("subtasks", []any{done, todo})

	got := (&SubtaskWorkflowGuidance{}).EnhanceResponse(response, "list", entities.NewOrderedMap[any]())
	wgVal, _ := got.Get("workflow_guidance")
	wg := wgVal.(*entities.OrderedMap[any])

	csVal, _ := wg.Get("current_state")
	state := csVal.(*entities.OrderedMap[any])
	if phase, _ := state.Get("phase"); phase != "in_progress" {
		t.Fatalf("phase = %v", phase)
	}
	if total, _ := state.Get("total"); total != 2 {
		t.Fatalf("total = %v", total)
	}
	if cp, _ := state.Get("completion_percentage"); cp != 50 {
		t.Fatalf("completion_percentage = %v", cp)
	}

	ovVal, _ := wg.Get("overview")
	overview := ovVal.(*entities.OrderedMap[any])
	if rate, _ := overview.Get("completion_rate"); rate != "1/2" {
		t.Fatalf("completion_rate = %v", rate)
	}
}

func TestAnalyzeSubtaskStatePhaseAndAssignees(t *testing.T) {
	sub := entities.NewOrderedMap[any]()
	sub.Set("status", "done")
	sub.Set("assignees", []any{})

	state := (&SubtaskWorkflowGuidance{}).analyzeSubtaskState(sub)
	if phase, _ := state.Get("phase"); phase != "completed" {
		t.Fatalf("phase = %v", phase)
	}
	if has, _ := state.Get("has_assignees"); has != false {
		t.Fatalf("has_assignees = %v", has)
	}
}

func TestNotStartedSubtasksState(t *testing.T) {
	state := (&SubtaskWorkflowGuidance{}).analyzeSubtasksState(nil)
	if phase, _ := state.Get("phase"); phase != "no_subtasks" {
		t.Fatalf("phase = %v", phase)
	}
	if total, _ := state.Get("total"); total != 0 {
		t.Fatalf("total = %v", total)
	}
}
