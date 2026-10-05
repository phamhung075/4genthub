package workflow_guidance

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestGenerateGuidanceListAllDone(t *testing.T) {
	response := entities.NewOrderedMap[any]()
	s1 := entities.NewOrderedMap[any]()
	s1.Set("status", "done")
	s2 := entities.NewOrderedMap[any]()
	s2.Set("status", "done")
	response.Set("subtasks", []any{s1, s2})

	context := entities.NewOrderedMap[any]()
	context.Set("response", response)

	out := (SubtaskWorkflowGuidance{}).GenerateGuidance("list", context)

	hints, _ := out.Get("hints")
	if got := hints.([]any)[0]; got != "All 2 subtasks complete! Parent task ready for completion." {
		t.Fatalf("hint = %v", got)
	}
	recs, _ := out.Get("recommendations")
	if got := recs.([]any)[0]; got != "Consider completing the parent task" {
		t.Fatalf("recommendation = %v", got)
	}
	keys := out.Keys()
	want := []string{"hints", "next_actions", "rules", "recommendations"}
	for i := range want {
		if keys[i] != want[i] {
			t.Fatalf("key order = %v", keys)
		}
	}
}

func TestGenerateGuidancePartialProgress(t *testing.T) {
	response := entities.NewOrderedMap[any]()
	s1 := entities.NewOrderedMap[any]()
	s1.Set("status", "done")
	s2 := entities.NewOrderedMap[any]()
	s2.Set("status", "todo")
	response.Set("subtasks", []any{s1, s2})

	context := entities.NewOrderedMap[any]()
	context.Set("response", response)

	out := (SubtaskWorkflowGuidance{}).GenerateGuidance("list", context)
	hints, _ := out.Get("hints")
	if got := hints.([]any)[0]; got != "Progress: 1/2 subtasks completed" {
		t.Fatalf("hint = %v", got)
	}
}

func TestGenerateGuidanceCreate(t *testing.T) {
	out := (SubtaskWorkflowGuidance{}).GenerateGuidance("create", entities.NewOrderedMap[any]())
	hints, _ := out.Get("hints")
	if got := hints.([]any)[0]; got != "Subtask created successfully. Remember to update progress regularly." {
		t.Fatalf("hint = %v", got)
	}
	next, _ := out.Get("next_actions")
	na := next.([]any)[0].(*entities.OrderedMap[any])
	action, _ := na.Get("action")
	desc, _ := na.Get("description")
	if action != "update" || desc != "Update progress as you work" {
		t.Fatalf("next_action = %v/%v", action, desc)
	}
}
