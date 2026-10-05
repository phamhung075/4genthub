package task

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

type fakeWorkflowHintEnhancer struct{}

func (fakeWorkflowHintEnhancer) EnhanceErrorResponseV2(response *entities.OrderedMap[any], action string, context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return response
}

func (fakeWorkflowHintEnhancer) EnhanceTaskResponse(response *entities.OrderedMap[any], action string, requestParams *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return response
}

func TestEnhanceResponseLegacyCreate(t *testing.T) {
	old := NewWorkflowHintEnhancerFunc
	NewWorkflowHintEnhancerFunc = func() WorkflowHintEnhancer { return fakeWorkflowHintEnhancer{} }
	defer func() { NewWorkflowHintEnhancerFunc = old }()

	response := entities.NewOrderedMap[any]()
	response.Set("success", true)
	task := entities.NewOrderedMap[any]()
	task.Set("id", "t1")
	task.Set("status", "todo")
	response.Set("task", task)

	got := NewTaskWorkflowGuidance().EnhanceResponse(response, "create", entities.NewOrderedMap[any]())
	wgVal, _ := got.Get("workflow_guidance")
	wg := wgVal.(*entities.OrderedMap[any])

	csVal, _ := wg.Get("current_state")
	state := csVal.(*entities.OrderedMap[any])
	if phase, _ := state.Get("phase"); phase != "not_started" {
		t.Fatalf("phase = %v", phase)
	}
	if !wg.Has("tips") {
		t.Fatal("tips missing on create")
	}
	if !got.Has("ai_reminders") {
		t.Fatal("ai_reminders missing on create")
	}
	rules, _ := wg.Get("rules")
	if got := rules.([]string)[0]; got != "📝 Always provide context when updating tasks" {
		t.Fatalf("rule = %v", got)
	}
}

func TestAnalyzeStateInProgressBuckets(t *testing.T) {
	response := entities.NewOrderedMap[any]()
	task := entities.NewOrderedMap[any]()
	task.Set("status", "in_progress")
	task.Set("overall_progress", 50)
	task.Set("subtasks", []any{"a"})
	response.Set("task", task)

	state := (&TaskWorkflowGuidance{}).AnalyzeState(response, entities.NewOrderedMap[any]())
	if phase, _ := state.Get("phase"); phase != "mid_progress" {
		t.Fatalf("phase = %v", phase)
	}
	if progress, _ := state.Get("progress"); progress != float64(50) {
		t.Fatalf("progress = %v", progress)
	}
	if has, _ := state.Get("has_subtasks"); has != true {
		t.Fatalf("has_subtasks = %v", has)
	}
}

func TestGenerateDependencyGuidanceBlocked(t *testing.T) {
	task := entities.NewOrderedMap[any]()
	depRel := entities.NewOrderedMap[any]()
	summary := entities.NewOrderedMap[any]()
	summary.Set("is_blocked", true)
	depRel.Set("summary", summary)
	workflow := entities.NewOrderedMap[any]()
	workflow.Set("next_actions", []any{"do-x"})
	blockingInfo := entities.NewOrderedMap[any]()
	blockingInfo.Set("is_blocked", true)
	blockingInfo.Set("blocking_tasks", []any{"b1", "b2"})
	blockingInfo.Set("blocking_chains", []any{"c1"})
	blockingInfo.Set("resolution_suggestions", []any{"resolve"})
	workflow.Set("blocking_info", blockingInfo)
	depRel.Set("workflow", workflow)
	task.Set("dependency_relationships", depRel)

	guidance := (&TaskWorkflowGuidance{}).generateDependencyGuidance(task)
	if status, _ := guidance.Get("dependency_status"); status != "blocked" {
		t.Fatalf("status = %v", status)
	}
	recs, _ := guidance.Get("recommendations")
	if got := recs.([]any)[0]; got != "🚧 Task is blocked by dependencies" {
		t.Fatalf("rec = %v", got)
	}
	bdVal, _ := guidance.Get("blocking_details")
	bd := bdVal.(*entities.OrderedMap[any])
	if n, _ := bd.Get("blocking_tasks"); n != 2 {
		t.Fatalf("blocking_tasks = %v", n)
	}
}
