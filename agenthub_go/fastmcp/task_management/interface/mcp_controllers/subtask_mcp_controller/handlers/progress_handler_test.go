package handlers

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func sub(status string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("status", status)
	return m
}

func TestCalculateTaskProgress(t *testing.T) {
	h := NewProgressHandler(nil, nil)
	subtasks := []*entities.OrderedMap[any]{
		sub("completed"), sub("completed"), sub("in_progress"), sub("pending"), sub("blocked"), sub("cancelled"),
	}
	got := h.CalculateTaskProgress("t1", subtasks)

	wantKeys := []string{"total_subtasks", "completed_subtasks", "in_progress_subtasks", "pending_subtasks", "blocked_subtasks", "cancelled_subtasks", "progress_percentage", "progress_status", "last_calculated"}
	for i, k := range got.Keys() {
		if k != wantKeys[i] {
			t.Fatalf("key[%d]=%q want %q (order %v)", i, k, wantKeys[i], got.Keys())
		}
	}
	if v, _ := got.Get("total_subtasks"); v != 6 {
		t.Errorf("total=%v want 6", v)
	}
	if v, _ := got.Get("completed_subtasks"); v != 2 {
		t.Errorf("completed=%v want 2", v)
	}
	// weighted = 2 + 0.5 = 2.5; 2.5/6*100 = 41.66 -> 41
	if v, _ := got.Get("progress_percentage"); v != 41 {
		t.Errorf("progress_percentage=%v want 41", v)
	}
	if v, _ := got.Get("progress_status"); v != "in_progress" {
		t.Errorf("progress_status=%v want in_progress", v)
	}
}

func TestCalculateTaskProgressAllDone(t *testing.T) {
	h := NewProgressHandler(nil, nil)
	got := h.CalculateTaskProgress("t1", []*entities.OrderedMap[any]{sub("completed"), sub("completed")})
	if v, _ := got.Get("progress_status"); v != "completed" {
		t.Errorf("status=%v want completed", v)
	}
	if v, _ := got.Get("progress_percentage"); v != 100 {
		t.Errorf("percentage=%v want 100", v)
	}
}

// TestCalculateTaskProgressDoneQuirk preserves the Python quirk: "done" is not a
// key of status_counts, so it is counted as pending.
func TestCalculateTaskProgressDoneQuirk(t *testing.T) {
	h := NewProgressHandler(nil, nil)
	got := h.CalculateTaskProgress("t1", []*entities.OrderedMap[any]{sub("done"), sub("done")})
	if v, _ := got.Get("completed_subtasks"); v != 0 {
		t.Errorf("completed=%v want 0", v)
	}
	if v, _ := got.Get("pending_subtasks"); v != 2 {
		t.Errorf("pending=%v want 2", v)
	}
}

func TestCalculateTaskProgressEmpty(t *testing.T) {
	h := NewProgressHandler(nil, nil)
	got := h.CalculateTaskProgress("t1", nil)
	wantKeys := []string{"total_subtasks", "completed_subtasks", "in_progress_subtasks", "pending_subtasks", "progress_percentage", "progress_status"}
	if len(got.Keys()) != len(wantKeys) {
		t.Fatalf("keys=%v", got.Keys())
	}
	for i, k := range got.Keys() {
		if k != wantKeys[i] {
			t.Fatalf("key[%d]=%q want %q", i, k, wantKeys[i])
		}
	}
	if v, _ := got.Get("progress_status"); v != "no_subtasks" {
		t.Errorf("status=%v want no_subtasks", v)
	}
}

func TestUpdateParentProgressNoFacade(t *testing.T) {
	h := NewProgressHandler(nil, nil)
	got := h.UpdateParentProgress(context.Background(), "t1", "create", entities.NewOrderedMap[any](), nil)
	if v, _ := got.Get("updated"); v != false {
		t.Errorf("updated=%v", v)
	}
	if v, _ := got.Get("reason"); v != "No context facade available" {
		t.Errorf("reason=%v", v)
	}
}

func TestCreateProgressContent(t *testing.T) {
	h := NewProgressHandler(nil, nil)
	data := entities.NewOrderedMap[any]()
	data.Set("title", "API")
	data.Set("status", "in_progress")
	notes := "working"
	if got := h.createProgressContent("update", data, &notes); got != "Updated subtask 'API' - Status: in_progress - working" {
		t.Errorf("got %q", got)
	}
	if got := h.createProgressContent("create", data, nil); got != "Created subtask: API" {
		t.Errorf("got %q", got)
	}
}

func TestGenerateProgressInsightsAndRecommendations(t *testing.T) {
	h := NewProgressHandler(nil, nil)
	progress := entities.NewOrderedMap[any]()
	progress.Set("total_subtasks", 3)
	progress.Set("completed_subtasks", 3)
	progress.Set("in_progress_subtasks", 0)
	progress.Set("blocked_subtasks", 0)
	progress.Set("pending_subtasks", 0)

	insights := h.generateProgressInsights(progress, nil)
	if len(insights) != 1 || insights[0] != "All subtasks completed! 🎉" {
		t.Errorf("insights=%v", insights)
	}
	recs := h.generateProgressRecommendations(progress, nil)
	if len(recs) != 1 || recs[0] != "Consider marking the parent task as completed" {
		t.Errorf("recommendations=%v", recs)
	}
}

func TestGetProgressSummaryAddsInsights(t *testing.T) {
	h := NewProgressHandler(nil, nil)
	progress := h.GetProgressSummary("t1", []*entities.OrderedMap[any]{sub("blocked")})
	if _, ok := progress.Get("insights"); !ok {
		t.Error("missing insights")
	}
	if _, ok := progress.Get("recommendations"); !ok {
		t.Error("missing recommendations")
	}
}

// fakeFormatter records create_error_response arguments.
type fakeFormatter struct {
	operation string
	errMsg    string
	errorCode ErrorCode
	metadata  *entities.OrderedMap[any]
}

func (f *fakeFormatter) CreateErrorResponse(operation, errorMessage string, errorCode ErrorCode, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	f.operation = operation
	f.errMsg = errorMessage
	f.errorCode = errorCode
	f.metadata = metadata
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	return m
}

func TestCreateSubtaskValidation(t *testing.T) {
	f := &fakeFormatter{}
	h := NewSubtaskCRUDHandler(f, nil, nil, nil)

	h.CreateSubtask(context.Background(), nil, "", "title", nil, nil, nil, nil, nil, nil, nil)
	if f.operation != "subtask_validation" || f.errorCode != ErrorCodeValidation {
		t.Errorf("op=%q code=%q", f.operation, f.errorCode)
	}
	if f.errMsg != "Missing required field: task_id. Expected: A valid task_id string" {
		t.Errorf("msg=%q", f.errMsg)
	}
	if v, _ := f.metadata.Get("hint"); v != "Include 'task_id' in your request" {
		t.Errorf("hint=%v", v)
	}

	h.CreateSubtask(context.Background(), nil, "t1", "", nil, nil, nil, nil, nil, nil, nil)
	if f.errMsg != "Missing required field: title. Expected: A non-empty title string" {
		t.Errorf("msg=%q", f.errMsg)
	}
}

func TestUpdateSubtaskRequiresProgressNotes(t *testing.T) {
	f := &fakeFormatter{}
	h := NewSubtaskCRUDHandler(f, nil, nil, nil)
	short := "short"
	h.UpdateSubtask(context.Background(), nil, "t1", "s1", nil, nil, nil, nil, nil, nil, &short)
	if f.operation != "update_subtask" || f.errorCode != ErrorCodeValidation {
		t.Errorf("op=%q code=%q", f.operation, f.errorCode)
	}
	if f.errMsg != "Missing required field: progress_notes (minimum 10 characters). Updates must include progress description." {
		t.Errorf("msg=%q", f.errMsg)
	}
}

func TestValidateAssigneeListQuirk(t *testing.T) {
	// Keep the Python quirk: ValidateAssigneeList usage.
	task := &entities.Task{}
	got, err := task.ValidateAssigneeList([]string{"coding-agent"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(got) != 1 {
		t.Fatalf("got %v", got)
	}
}
