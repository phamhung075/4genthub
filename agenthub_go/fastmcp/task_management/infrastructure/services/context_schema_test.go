package services

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func od(t *testing.T, v any) *entities.OrderedMap[any] {
	t.Helper()
	o, ok := v.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("value %#v is not an ordered map", v)
	}
	return o
}

func oval(t *testing.T, o *entities.OrderedMap[any], key string) any {
	t.Helper()
	v, ok := o.Get(key)
	if !ok {
		t.Fatalf("key %q missing", key)
	}
	return v
}

func TestContextMetadataDefaults(t *testing.T) {
	m := NewContextMetadata("task123", "proj456")
	if m.GitBranchID != "main" {
		t.Fatalf("git_branch_id = %q, want main", m.GitBranchID)
	}
	if m.UserID != nil {
		t.Fatalf("user_id = %#v, want nil", m.UserID)
	}
	if m.Status.String() != "todo" || m.Priority.String() != "medium" {
		t.Fatalf("status/priority = %q/%q", m.Status.String(), m.Priority.String())
	}
	if len(m.Assignees) != 0 || len(m.Labels) != 0 {
		t.Fatalf("assignees/labels = %#v/%#v", m.Assignees, m.Labels)
	}
	if m.Version != "1.0" {
		t.Fatalf("version = %q, want 1.0", m.Version)
	}
}

func TestContextObjectiveDefaults(t *testing.T) {
	o := NewContextObjective("Test task")
	if o.Title != "Test task" || o.Description != "" || o.EstimatedEffort != "medium" || o.DueDate != nil {
		t.Fatalf("objective = %#v", o)
	}
}

func TestTaskContextToDict(t *testing.T) {
	m := NewContextMetadata("task123", "proj456")
	m.Status = value_objects.TaskStatus{Value: "in_progress"}
	m.Priority = value_objects.Priority{Value: "high"}
	o := NewContextObjective("Test task")
	o.Description = "Test description"

	ctx := NewTaskContext(m, o)
	d := ctx.ToDict()

	metadata := od(t, oval(t, d, "metadata"))
	if oval(t, metadata, "task_id") != "task123" || oval(t, metadata, "project_id") != "proj456" {
		t.Fatalf("metadata = %#v", metadata.Keys())
	}
	if oval(t, metadata, "status") != "in_progress" || oval(t, metadata, "priority") != "high" {
		t.Fatalf("status/priority = %#v/%#v", oval(t, metadata, "status"), oval(t, metadata, "priority"))
	}
	objective := od(t, oval(t, d, "objective"))
	if oval(t, objective, "title") != "Test task" || oval(t, objective, "description") != "Test description" {
		t.Fatalf("objective = %#v", objective.Keys())
	}

	// Top-level key order matches the dataclass field order.
	want := []string{"metadata", "objective", "requirements", "technical", "dependencies", "progress", "subtasks", "notes", "custom_sections"}
	got := d.Keys()
	if len(got) != len(want) {
		t.Fatalf("keys = %#v", got)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("keys = %#v, want %#v", got, want)
		}
	}
}

func TestTaskContextFromDict(t *testing.T) {
	data := map[string]any{
		"metadata": map[string]any{
			"task_id": "task123", "project_id": "proj456",
			"status": "in_progress", "priority": "high",
			"assignees": []any{"agent1"}, "labels": []any{"test"},
		},
		"objective": map[string]any{"title": "Test task", "description": "From dict test"},
		"requirements": map[string]any{
			"checklist": []any{map[string]any{
				"id": "req1", "title": "Requirement 1", "completed": true,
				"priority": "medium", "notes": "Test note",
			}},
			"custom_requirements": []any{"Custom req 1"},
			"completion_criteria": []any{"All tests pass"},
		},
		"dependencies": map[string]any{
			"task_dependencies": []any{map[string]any{
				"task_id": "dep1", "title": "Dependency task", "status": "done",
				"blocking_reason": "Must finish first",
			}},
			"external_dependencies": []any{"External API"},
			"blocked_by":            []any{"task999"},
		},
		"subtasks": map[string]any{
			"items": []any{map[string]any{
				"id": "sub1", "title": "Subtask 1", "description": "First subtask",
				"status": "todo", "assignees": []any{"agent2"}, "completed": false,
				"progress_notes": "Not started",
			}},
			"total_count": 1, "completed_count": 0, "progress_percentage": 0.0,
		},
	}

	ctx, err := TaskContextFromDict(data)
	if err != nil {
		t.Fatal(err)
	}
	if ctx.Metadata.TaskID != "task123" || ctx.Metadata.ProjectID != "proj456" {
		t.Fatalf("metadata = %#v", ctx.Metadata)
	}
	if ctx.Metadata.Status.String() != "in_progress" || ctx.Metadata.Priority.String() != "high" {
		t.Fatalf("status/priority = %q/%q", ctx.Metadata.Status.String(), ctx.Metadata.Priority.String())
	}
	if len(ctx.Metadata.Assignees) != 1 || ctx.Metadata.Assignees[0] != "agent1" {
		t.Fatalf("assignees = %#v", ctx.Metadata.Assignees)
	}
	if ctx.Metadata.UserID == nil || *ctx.Metadata.UserID != "" {
		t.Fatalf("user_id = %#v, want empty string", ctx.Metadata.UserID)
	}
	if ctx.Objective.Title != "Test task" || ctx.Objective.Description != "From dict test" {
		t.Fatalf("objective = %#v", ctx.Objective)
	}
	if len(ctx.Requirements.Checklist) != 1 || ctx.Requirements.Checklist[0].ID != "req1" {
		t.Fatalf("requirements = %#v", ctx.Requirements)
	}
	if !ctx.Requirements.Checklist[0].Completed || ctx.Requirements.Checklist[0].Priority.String() != "medium" {
		t.Fatalf("checklist item = %#v", ctx.Requirements.Checklist[0])
	}
	if len(ctx.Dependencies.TaskDependencies) != 1 || ctx.Dependencies.TaskDependencies[0].Status.String() != "done" {
		t.Fatalf("dependencies = %#v", ctx.Dependencies)
	}
	if len(ctx.Subtasks.Items) != 1 || ctx.Subtasks.Items[0].Assignees[0] != "agent2" {
		t.Fatalf("subtasks = %#v", ctx.Subtasks)
	}
}

func TestTaskContextRoundtrip(t *testing.T) {
	m := NewContextMetadata("task123", "proj456")
	m.Status = value_objects.TaskStatus{Value: "in_progress"}
	m.Priority = value_objects.Priority{Value: "critical"}
	m.Assignees = []string{"agent1", "agent2"}
	ctx := NewTaskContext(m, NewContextObjective("Test roundtrip"))
	ctx.Requirements.Checklist = append(ctx.Requirements.Checklist, &ContextRequirement{
		ID: "req1", Title: "Test requirement", Priority: value_objects.Priority{Value: "high"},
	})

	reconstructed, err := TaskContextFromDict(ctx.ToDict())
	if err != nil {
		t.Fatal(err)
	}
	if reconstructed.Metadata.TaskID != "task123" || reconstructed.Metadata.Status.String() != "in_progress" {
		t.Fatalf("metadata = %#v", reconstructed.Metadata)
	}
	if reconstructed.Metadata.Priority.String() != "critical" {
		t.Fatalf("priority = %q", reconstructed.Metadata.Priority.String())
	}
	if len(reconstructed.Metadata.Assignees) != 2 {
		t.Fatalf("assignees = %#v", reconstructed.Metadata.Assignees)
	}
	if len(reconstructed.Requirements.Checklist) != 1 || reconstructed.Requirements.Checklist[0].Priority.String() != "high" {
		t.Fatalf("checklist = %#v", reconstructed.Requirements.Checklist)
	}
}

func TestTaskContextFromDictInvalidStatus(t *testing.T) {
	_, err := TaskContextFromDict(map[string]any{
		"metadata":  map[string]any{"task_id": "t", "project_id": "p", "status": "bogus"},
		"objective": map[string]any{"title": "x"},
	})
	if err == nil {
		t.Fatalf("invalid status did not fail")
	}
}

func TestContextSchemaGetDefaultSchema(t *testing.T) {
	schema := ContextSchema{}.GetDefaultSchema()
	if oval(t, schema, "version") != "1.0" || oval(t, schema, "type") != "object" {
		t.Fatalf("version/type = %#v/%#v", oval(t, schema, "version"), oval(t, schema, "type"))
	}
	required, ok := oval(t, schema, "required").([]string)
	if !ok || len(required) != 2 || required[0] != "metadata" || required[1] != "objective" {
		t.Fatalf("required = %#v", oval(t, schema, "required"))
	}
	if _, ok := schema.Get("properties"); !ok {
		t.Fatalf("properties missing")
	}
	if _, ok := schema.Get("definitions"); !ok {
		t.Fatalf("definitions missing")
	}

	properties := od(t, oval(t, schema, "properties"))
	metadataProps := od(t, oval(t, od(t, oval(t, properties, "metadata")), "properties"))
	statusEnum := oval(t, od(t, oval(t, metadataProps, "status")), "enum")
	statuses, _ := statusEnum.([]string)
	if len(statuses) != len(value_objects.TaskStatusValues) {
		t.Fatalf("status enum = %#v", statusEnum)
	}
	for i, s := range value_objects.TaskStatusValues {
		if statuses[i] != string(s) {
			t.Fatalf("status enum[%d] = %q, want %q", i, statuses[i], s)
		}
	}
	priorityEnum := oval(t, od(t, oval(t, metadataProps, "priority")), "enum")
	priorities, _ := priorityEnum.([]string)
	if len(priorities) != len(value_objects.PriorityLevels) {
		t.Fatalf("priority enum = %#v", priorityEnum)
	}
	for i, p := range value_objects.PriorityLevels {
		if priorities[i] != p.Label {
			t.Fatalf("priority enum[%d] = %q, want %q", i, priorities[i], p.Label)
		}
	}
}

func TestContextSchemaValidateContext(t *testing.T) {
	valid := map[string]any{
		"metadata":  map[string]any{"task_id": "task123", "project_id": "proj456"},
		"objective": map[string]any{"title": "Test task"},
	}
	ok, errors := ContextSchema{}.ValidateContext(valid)
	if !ok || len(errors) != 0 {
		t.Fatalf("valid = %v, errors = %#v", ok, errors)
	}

	ok, errors = ContextSchema{}.ValidateContext(map[string]any{"metadata": map[string]any{"task_id": "t"}})
	if ok || len(errors) != 1 || errors[0] != "Missing required section: objective" {
		t.Fatalf("missing objective: ok=%v errors=%#v", ok, errors)
	}

	ok, errors = ContextSchema{}.ValidateContext("not a dict")
	if ok || len(errors) != 1 || errors[0] != "Context data must be a dictionary" {
		t.Fatalf("non-dict: ok=%v errors=%#v", ok, errors)
	}
}

func TestContextSchemaCreateEmptyContext(t *testing.T) {
	ctx, err := ContextSchema{}.CreateEmptyContext("task123", "proj456", "Empty context test", nil)
	if err != nil {
		t.Fatal(err)
	}
	if ctx.Metadata.TaskID != "task123" || ctx.Metadata.ProjectID != "proj456" || ctx.Metadata.GitBranchID != "main" {
		t.Fatalf("metadata = %#v", ctx.Metadata)
	}
	if ctx.Metadata.UserID == nil || *ctx.Metadata.UserID != "" {
		t.Fatalf("user_id = %#v, want empty", ctx.Metadata.UserID)
	}
	if ctx.Metadata.Status.String() != "todo" || ctx.Metadata.Priority.String() != "medium" {
		t.Fatalf("status/priority = %q/%q", ctx.Metadata.Status.String(), ctx.Metadata.Priority.String())
	}
	if ctx.Objective.Description != "" {
		t.Fatalf("description = %q", ctx.Objective.Description)
	}

	ctx, err = ContextSchema{}.CreateEmptyContext("task123", "proj456", "Custom context", map[string]any{
		"git_branch_id": "feature/test", "user_id": "user789", "status": "in_progress",
		"priority": "high", "assignees": []any{"agent1", "agent2"}, "labels": []any{"urgent"},
		"description": "Custom description", "estimated_effort": "large", "due_date": "2024-12-31",
	})
	if err != nil {
		t.Fatal(err)
	}
	if ctx.Metadata.GitBranchID != "feature/test" || ctx.Metadata.UserID == nil || *ctx.Metadata.UserID != "user789" {
		t.Fatalf("metadata = %#v", ctx.Metadata)
	}
	if ctx.Metadata.Status.String() != "in_progress" || ctx.Metadata.Priority.String() != "high" {
		t.Fatalf("status/priority = %q/%q", ctx.Metadata.Status.String(), ctx.Metadata.Priority.String())
	}
	if len(ctx.Metadata.Assignees) != 2 || len(ctx.Metadata.Labels) != 1 {
		t.Fatalf("assignees/labels = %#v/%#v", ctx.Metadata.Assignees, ctx.Metadata.Labels)
	}
	if ctx.Objective.Description != "Custom description" || ctx.Objective.EstimatedEffort != "large" {
		t.Fatalf("objective = %#v", ctx.Objective)
	}
	if ctx.Objective.DueDate == nil || *ctx.Objective.DueDate != "2024-12-31" {
		t.Fatalf("due_date = %#v", ctx.Objective.DueDate)
	}
}

func TestTaskContextEmptyCollections(t *testing.T) {
	ctx := NewTaskContext(NewContextMetadata("task123", "proj456"), NewContextObjective("Test empty collections"))
	d := ctx.ToDict()
	if v := oval(t, od(t, oval(t, d, "metadata")), "assignees"); len(v.([]string)) != 0 {
		t.Fatalf("assignees = %#v", v)
	}
	if v := oval(t, od(t, oval(t, d, "requirements")), "checklist"); len(v.([]any)) != 0 {
		t.Fatalf("checklist = %#v", v)
	}
	if v := oval(t, d, "custom_sections"); len(v.([]any)) != 0 {
		t.Fatalf("custom_sections = %#v", v)
	}
}
