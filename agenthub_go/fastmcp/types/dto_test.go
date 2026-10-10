package types

import (
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func dict(kv ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i < len(kv); i += 2 {
		m.Set(kv[i].(string), kv[i+1])
	}
	return m
}

func TestTaskToDTODict(t *testing.T) {
	task := dict(
		"id", "123e4567-e89b-12d3-a456-426614174000",
		"title", "Implement auth",
		"description", "desc",
		"status", "in_progress",
		"priority", "high",
		"assignees", []string{"a", "b"},
		"dependencies", []string{"d1", "d2"},
		"git_branch_id", "b-1",
		"context_id", "ctx-1",
		"project_id", "p-1",
		"subtask_count", 3,
		"created_at", "2025-01-02T03:04:05+00:00",
		"labels", []string{"x"},
	)
	dto, err := TaskToDTO(task, false)
	if err != nil {
		t.Fatalf("TaskToDTO: %v", err)
	}
	if dto.ID != "123e4567-e89b-12d3-a456-426614174000" || dto.Title != "Implement auth" {
		t.Fatalf("id/title: %+v", dto)
	}
	if dto.Status != "in_progress" || dto.Priority != "high" {
		t.Fatalf("status/priority: %+v", dto)
	}
	if dto.AssigneesCount != 2 || dto.SubtaskCount != 3 {
		t.Fatalf("counts: %+v", dto)
	}
	if !dto.HasDependencies || dto.DependencyCount == nil || *dto.DependencyCount != 2 {
		t.Fatalf("dependencies: %+v", dto)
	}
	if strings.Join(dto.Dependencies, ",") != "d1,d2" {
		t.Fatalf("dep list: %+v", dto.Dependencies)
	}
	if !dto.HasContext || dto.ContextID == nil || *dto.ContextID != "ctx-1" {
		t.Fatalf("context: %+v", dto)
	}
	if dto.GitBranchID == nil || *dto.GitBranchID != "b-1" {
		t.Fatalf("git branch: %+v", dto.GitBranchID)
	}
	if dto.ProjectID == nil || *dto.ProjectID != "p-1" {
		t.Fatalf("project: %+v", dto.ProjectID)
	}
	if dto.CreatedAt == nil || *dto.CreatedAt != "2025-01-02T03:04:05+00:00" {
		t.Fatalf("created_at: %+v", dto.CreatedAt)
	}
	if dto.Subtasks != nil {
		t.Fatalf("subtasks should be None: %+v", dto.Subtasks)
	}
	if dto.Labels == nil || len(dto.Labels) != 1 {
		t.Fatalf("labels: %+v", dto.Labels)
	}

	dump := dto.ModelDump()
	wantKeys := "id,title,description,status,priority,assignees,assignees_count,subtask_count," +
		"has_dependencies,dependency_count,dependencies,has_context,context_id,context_data," +
		"git_branch_id,project_id,created_at,updated_at,due_date,estimated_effort,labels,details," +
		"progress_percentage,subtasks"
	if got := strings.Join(dump.Keys(), ","); got != wantKeys {
		t.Fatalf("key order:\n got %s\nwant %s", got, wantKeys)
	}
	if v, _ := dump.Get("subtask_count"); v != 3 {
		t.Fatalf("dump subtask_count: %v", v)
	}
	if v, _ := dump.Get("description"); v != "desc" {
		t.Fatalf("dump description: %v", v)
	}
}

func TestTaskToDTOMissingKey(t *testing.T) {
	_, err := TaskToDTO(entities.NewOrderedMap[any](), false)
	if err == nil || err.Error() != "'id'" {
		t.Fatalf("want KeyError 'id', got %v", err)
	}
}

func TestTaskToDTOEntity(t *testing.T) {
	id, err := value_objects.NewTaskId("123e4567-e89b-12d3-a456-426614174000")
	if err != nil {
		t.Fatal(err)
	}
	status, _ := value_objects.NewTaskStatus("in_progress")
	priority, _ := value_objects.NewPriority("high")
	task := &entities.Task{
		Title:       "T",
		Description: "D",
		ID:          &id,
		Status:      &status,
		Priority:    &priority,
	}
	task.Subtasks = []string{"s1", "s2"}
	task.Assignees = []string{"a"}
	task.Dependencies = []value_objects.TaskId{id}

	dto, err := TaskToDTO(task, false)
	if err != nil {
		t.Fatalf("TaskToDTO entity: %v", err)
	}
	if dto.ID != id.String() {
		t.Fatalf("id: %q", dto.ID)
	}
	if dto.Status != "in_progress" || dto.Priority != "high" {
		t.Fatalf("status/priority: %+v", dto)
	}
	if dto.SubtaskCount != 2 {
		t.Fatalf("subtask_count (property/method): %d", dto.SubtaskCount)
	}
	if dto.Description == nil || *dto.Description != "D" {
		t.Fatalf("description: %+v", dto.Description)
	}
	// Python: git_branch_id=str(getattr(task,"git_branch_id","")) -> str(None) == "None".
	if dto.GitBranchID == nil || *dto.GitBranchID != "None" {
		t.Fatalf("git_branch_id quirk: %+v", dto.GitBranchID)
	}
	// Python: project_id absent -> "".
	if dto.ProjectID == nil || *dto.ProjectID != "" {
		t.Fatalf("project_id: %+v", dto.ProjectID)
	}
	if !dto.HasDependencies || dto.DependencyCount == nil || *dto.DependencyCount != 1 {
		t.Fatalf("dependencies: %+v", dto)
	}
	if dto.ProgressPercentage != nil {
		t.Fatalf("progress_percentage should be None: %+v", dto.ProgressPercentage)
	}
}

func TestTaskToDTOIncludeSubtasksDict(t *testing.T) {
	task := dict(
		"id", "t1", "title", "T", "status", "todo", "priority", "low",
		"git_branch_id", "b1",
		"subtasks", []any{dict("id", "s1", "title", "S", "status", "done", "priority", "low")},
	)
	dto, err := TaskToDTO(task, true)
	if err != nil {
		t.Fatalf("TaskToDTO: %v", err)
	}
	if len(dto.Subtasks) != 1 {
		t.Fatalf("subtasks: %+v", dto.Subtasks)
	}
	sub := dto.Subtasks[0]
	if sub.ID != "s1" || sub.Status != "done" {
		t.Fatalf("subtask: %+v", sub)
	}
}

func TestSubtaskToDTODictParentFallback(t *testing.T) {
	dto, err := SubtaskToDTO(dict("id", "s1", "title", "S", "status", "todo", "priority", "medium", "task_id", "parent-1"))
	if err != nil {
		t.Fatalf("SubtaskToDTO: %v", err)
	}
	if dto.TaskID != "parent-1" {
		t.Fatalf("task_id fallback: %q", dto.TaskID)
	}

	// Present-but-None parent_task_id wins over the task_id fallback: str(None).
	dto2, err := SubtaskToDTO(dict("id", "s2", "title", "S", "status", "todo", "priority", "medium", "parent_task_id", nil, "task_id", "parent-2"))
	if err != nil {
		t.Fatalf("SubtaskToDTO: %v", err)
	}
	if dto2.TaskID != "None" {
		t.Fatalf("present None parent: %q", dto2.TaskID)
	}
}

func TestSummaryConverters(t *testing.T) {
	task := dict(
		"id", "t1", "title", "T", "status", "done", "priority", "high",
		"assignees", []string{"a"}, "dependencies", []string{"d1"},
		"git_branch_id", nil, "project_id", "p1", "subtask_count", 4,
	)
	sum, err := TaskSummaryToDTO(task)
	if err != nil {
		t.Fatalf("TaskSummaryToDTO: %v", err)
	}
	if sum.SubtaskCount != 4 || sum.AssigneesCount != 1 || !sum.HasDependencies {
		t.Fatalf("summary: %+v", sum)
	}
	if sum.GitBranchID != nil {
		t.Fatalf("git_branch_id should be None: %+v", sum.GitBranchID)
	}
	if sum.ProjectID == nil || *sum.ProjectID != "p1" {
		t.Fatalf("project_id: %+v", sum.ProjectID)
	}

	sub, err := SubtaskSummaryToDTO(dict("id", "s1", "title", "S", "status", "todo", "priority", "low", "parent_task_id", "t1", "progress_percentage", 50))
	if err != nil {
		t.Fatalf("SubtaskSummaryToDTO: %v", err)
	}
	if sub.TaskID != "t1" || sub.ProgressPercentage == nil || *sub.ProgressPercentage != 50 {
		t.Fatalf("subtask summary: %+v", sub)
	}
}

func TestTaskSummaryEntity(t *testing.T) {
	id, _ := value_objects.NewTaskId("123e4567-e89b-12d3-a456-426614174000")
	status, _ := value_objects.NewTaskStatus("done")
	priority, _ := value_objects.NewPriority("high")
	task := &entities.Task{Title: "T", ID: &id, Status: &status, Priority: &priority}
	task.Subtasks = []string{"s1", "s2", "s3"}

	sum, err := TaskSummaryToDTO(task)
	if err != nil {
		t.Fatalf("TaskSummaryToDTO: %v", err)
	}
	if sum.SubtaskCount != 3 {
		t.Fatalf("subtask_count: %d", sum.SubtaskCount)
	}
	if sum.GitBranchID != nil || sum.ProjectID != nil {
		t.Fatalf("entity git/project should be None: %+v / %+v", sum.GitBranchID, sum.ProjectID)
	}
}

func TestBulkResponseDefaults(t *testing.T) {
	r := NewBulkSummaryResponse()
	if !r.Success {
		t.Fatal("default success should be true")
	}
	dump := r.ModelDump()
	if v, _ := dump.Get("success"); v != true {
		t.Fatalf("success: %v", v)
	}
	// summaries/projects default to {} rather than None.
	for _, k := range []string{"summaries", "projects"} {
		v, _ := dump.Get(k)
		om, ok := v.(*entities.OrderedMap[any])
		if !ok || om.Len() != 0 {
			t.Fatalf("%s default: %#v", k, v)
		}
	}
}

func TestResponseDefaultsAndDump(t *testing.T) {
	r := NewTaskResponse()
	if !r.Success {
		t.Fatal("default success should be true")
	}
	dump := r.ModelDump()
	want := "success,task,error,message,timestamp"
	if got := strings.Join(dump.Keys(), ","); got != want {
		t.Fatalf("TaskResponse key order: %s", got)
	}
	if v, _ := dump.Get("task"); v != nil {
		t.Fatalf("task should be None: %v", v)
	}
}

func TestGetValue(t *testing.T) {
	m := dict("a", 1)
	if v := getValue(m, "a", nil); v != 1 {
		t.Fatalf("dict getValue: %v", v)
	}
	if v := getValue(m, "missing", "def"); v != "def" {
		t.Fatalf("dict default: %v", v)
	}
	if v := getValue("not a struct", "x", "def"); v != "def" {
		t.Fatalf("object default: %v", v)
	}
}
