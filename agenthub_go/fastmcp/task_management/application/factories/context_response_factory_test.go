package factories

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func ctxRespJSON(t *testing.T, v any) string {
	t.Helper()
	s, err := value_objects.PyJSONDumps(v, -1)
	if err != nil {
		t.Fatalf("dumps: %v", err)
	}
	return s
}

// TestContextResponseCreateUnifiedContextTemplate covers case 1 and the section defaults.
func TestContextResponseCreateUnifiedContextTemplate(t *testing.T) {
	inner := entities.NewOrderedMap[any]()
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("task_id", "t1")
	inner.Set("metadata", metadata)
	input := entities.NewOrderedMap[any]()
	input.Set("template_context", inner)

	out := ContextResponseCreateUnifiedContext(input)
	if out == nil {
		t.Fatal("expected context")
	}
	want := []string{"metadata", "objective", "requirements", "technical", "dependencies", "progress", "subtasks", "notes", "custom_sections"}
	got := out.Keys()
	if len(got) != len(want) {
		t.Fatalf("keys = %v", got)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("keys[%d] = %q want %q (%v)", i, got[i], want[i], got)
		}
	}
	if out != inner {
		t.Fatal("expected the template_context dict itself to be mutated")
	}
	if v, _ := metadata.Get("task_id"); v != "t1" {
		t.Fatalf("task_id = %v", v)
	}
}

func TestContextResponseCreateUnifiedContextFalsy(t *testing.T) {
	if out := ContextResponseCreateUnifiedContext(nil); out != nil {
		t.Fatalf("nil -> %v", out)
	}
	if out := ContextResponseCreateUnifiedContext(entities.NewOrderedMap[any]()); out != nil {
		t.Fatalf("empty -> %v", out)
	}
}

// TestContextResponseConvertTaskData covers case 4 metadata/objective/key order.
func TestContextResponseConvertTaskData(t *testing.T) {
	taskData := entities.NewOrderedMap[any]()
	taskData.Set("status", "in_progress")
	taskData.Set("title", "Ship it")
	input := entities.NewOrderedMap[any]()
	input.Set("task_data", taskData)
	input.Set("id", "t9")

	out := ContextResponseCreateUnifiedContext(input)
	if out == nil {
		t.Fatal("expected context")
	}
	metadata, _ := out.Get("metadata")
	md := metadata.(*entities.OrderedMap[any])
	if v, _ := md.Get("task_id"); v != "t9" {
		t.Fatalf("task_id = %v", v)
	}
	if v, _ := md.Get("status"); v != "in_progress" {
		t.Fatalf("status = %v", v)
	}
	if v, _ := md.Get("priority"); v != "medium" {
		t.Fatalf("priority = %v", v)
	}
	objectiveAny, _ := out.Get("objective")
	objective := objectiveAny.(*entities.OrderedMap[any])
	if v, _ := objective.Get("title"); v != "Ship it" {
		t.Fatalf("title = %v", v)
	}
	progressAny, _ := out.Get("progress")
	progress := progressAny.(*entities.OrderedMap[any])
	if v, _ := progress.Get("completion_percentage"); v != int64(0) {
		t.Fatalf("completion_percentage = %#v", v)
	}
}

// TestContextResponseApplyToTaskResponseNoContext covers the else branch.
func TestContextResponseApplyToTaskResponseNoContext(t *testing.T) {
	task := entities.NewOrderedMap[any]()
	task.Set("id", "t1")
	out := ContextResponseApplyToTaskResponse(task)
	if v, _ := out.Get("context_available"); v != false {
		t.Fatalf("context_available = %v", v)
	}
	if out.Has("context_data") {
		t.Fatalf("context_data should be absent")
	}
}

// TestContextResponseApplyToTaskResponseWithContext covers the unifying branch.
func TestContextResponseApplyToTaskResponseWithContext(t *testing.T) {
	ctxData := entities.NewOrderedMap[any]()
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("task_id", "t1")
	ctxData.Set("metadata", metadata)
	task := entities.NewOrderedMap[any]()
	task.Set("id", "t1")
	task.Set("context_data", ctxData)

	out := ContextResponseApplyToTaskResponse(task)
	if v, _ := out.Get("context_available"); v != true {
		t.Fatalf("context_available = %v", v)
	}
	unifiedAny, _ := out.Get("context_data")
	unified, ok := unifiedAny.(*entities.OrderedMap[any])
	if !ok || unified == nil {
		t.Fatalf("context_data = %#v", unifiedAny)
	}
	if !unified.Has("subtasks") {
		t.Fatalf("expected completed structure, keys=%v", unified.Keys())
	}
}

// TestContextResponseApplyToNextResponse covers context_info extraction/removal and nesting.
func TestContextResponseApplyToNextResponse(t *testing.T) {
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("task_id", "t7")
	contextInfo := entities.NewOrderedMap[any]()
	contextInfo.Set("metadata", metadata)

	nestedTask := entities.NewOrderedMap[any]()
	nextItem := entities.NewOrderedMap[any]()
	nextItem.Set("task", nestedTask)

	task := entities.NewOrderedMap[any]()
	task.Set("context_info", contextInfo)
	task.Set("next_item", nextItem)

	nextResponse := entities.NewOrderedMap[any]()
	nextResponse.Set("task", task)

	out := ContextResponseApplyToNextResponse(nextResponse)
	if task.Has("context_info") {
		t.Fatal("context_info should be deleted")
	}
	if v, _ := task.Get("context"); v != "t7" {
		t.Fatalf("context = %v", v)
	}
	if v, _ := task.Get("context_available"); v != true {
		t.Fatalf("context_available = %v", v)
	}
	if v, _ := nestedTask.Get("context_available"); v != true {
		t.Fatalf("nested context_available = %v", v)
	}
	if !nestedTask.Has("context_data") {
		t.Fatal("nested context_data missing")
	}
	if len(out.Keys()) != 1 {
		t.Fatalf("next_response keys = %v", out.Keys())
	}
}

func TestContextResponseCreateUnifiedContextNonDictSections(t *testing.T) {
	// task_data null: Python raises inside _convert_task_data_to_template -> None.
	in := entities.NewOrderedMap[any]()
	in.Set("task_data", nil)
	if got := ContextResponseCreateUnifiedContext(in); got != nil {
		t.Fatalf("null task_data should give nil")
	}
	// template_context with a non-dict metadata keeps the value and returns the context.
	meta := entities.NewOrderedMap[any]()
	meta.Set("metadata", nil)
	in = entities.NewOrderedMap[any]()
	in.Set("template_context", meta)
	got := ContextResponseCreateUnifiedContext(in)
	if got == nil {
		t.Fatalf("non-dict metadata must not drop the context")
	}
	if v, _ := got.Get("metadata"); v != nil {
		t.Fatalf("metadata kept as is, got %v", v)
	}
	// case 3 uses Python `in` semantics: "task_id" in "task_id" is True.
	in = entities.NewOrderedMap[any]()
	in.Set("metadata", "task_id")
	if got := ContextResponseCreateUnifiedContext(in); got == nil {
		t.Fatalf("string metadata containing task_id is the template context")
	}
}
