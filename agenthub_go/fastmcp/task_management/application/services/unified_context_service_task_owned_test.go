package services

import (
	"context"
	"errors"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// The row's acceptance, both rows the ticket names: a task context read serves the LIVE task's
// own fields, so a done task and an in-progress task cannot resolve as todo. Remove
// overlayTaskOwnedFields and both cases fail on status.
func TestZucsGetContextServesTheLiveTaskOwnedFields(t *testing.T) {
	for _, tc := range []struct{ name, live string }{
		{"done", "done"},
		{"in_progress", "in_progress"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			s, task := newZucsTaskService(&fakeEntityLookup{ownFields: map[string]any{
				"status":   tc.live,
				"priority": "high",
			}})
			task.store["t1"] = zucsTaskContext("t1", "todo")

			res, err := s.ResolveContext(context.Background(), "task", "t1", false, nil)
			if err != nil {
				t.Fatalf("resolve: %v", err)
			}
			if v, _ := res.Get("success"); v != true {
				t.Fatalf("success=%v", v)
			}
			served := zucsServedTaskData(t, res)
			if v, _ := served.Get("status"); v != tc.live {
				t.Fatalf("served task_data.status = %v, want the live %q", v, tc.live)
			}
			if v, _ := served.Get("priority"); v != "high" {
				t.Fatalf("served task_data.priority = %v, want the live high", v)
			}
			// The record's copy of what the context owns survives the overlay.
			if v, _ := served.Get("title"); v != "stored title" {
				t.Fatalf("served task_data.title = %v, want the stored title", v)
			}
		})
	}
}

// The overlay replaces only the task's own fields: everything the context owns is untouched.
func TestZucsOverlayLeavesWhatTheContextOwns(t *testing.T) {
	s, task := newZucsTaskService(&fakeEntityLookup{ownFields: map[string]any{"status": "done"}})
	task.store["t1"] = zucsTaskContext("t1", "todo")

	res, _ := s.ResolveContext(context.Background(), "task", "t1", false, nil)
	served := zucsServedTaskData(t, res)
	if v, _ := served.Get("description"); v != "stored description" {
		t.Fatalf("description = %v, want the stored one", v)
	}
	if v, _ := served.Get("estimated_effort"); v != "3d" {
		t.Fatalf("estimated_effort = %v, want the stored one: the context owns it", v)
	}
}

// A read must not fail because the task could not be produced: the stored copy is served.
func TestZucsOverlayKeepsTheStoredCopyWhenTheTaskIsUnavailable(t *testing.T) {
	for _, tc := range []struct {
		name   string
		lookup EntityIDLookup
	}{
		{"no lookup", nil},
		{"lookup error", &fakeEntityLookup{err: errors.New("the task repository is down")}},
		{"no live fields", &fakeEntityLookup{}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			s, task := newZucsTaskService(tc.lookup)
			task.store["t1"] = zucsTaskContext("t1", "todo")

			res, err := s.ResolveContext(context.Background(), "task", "t1", false, nil)
			if err != nil {
				t.Fatalf("resolve: %v", err)
			}
			if v, _ := res.Get("success"); v != true {
				t.Fatalf("success=%v", v)
			}
			if v, _ := zucsServedTaskData(t, res).Get("status"); v != "todo" {
				t.Fatalf("status = %v, want the stored todo when the live task is unavailable", v)
			}
		})
	}
}

// A non-task level is not overlaid: the lookup is only the task's source of truth.
func TestZucsOverlaySkipsNonTaskLevels(t *testing.T) {
	s, _ := newZucsTaskService(&fakeEntityLookup{ownFields: map[string]any{"status": "done"}})
	global := s.repositories[value_objects.ContextLevelGlobal]
	global.(*zucsFakeRepo).store["g"] = entities.NewGlobalContext("g", "Org", map[string]any{"status": "todo"}, map[string]any{"user_id": "user-1"})

	res, _ := s.GetContext(context.Background(), "global", "g", false, false, nil)
	servedAny, _ := res.Get("context")
	served, ok := servedAny.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("context is %T", servedAny)
	}
	if v, _ := served.Get("status"); v != "todo" {
		t.Fatalf("global status = %v, want it untouched", v)
	}
}

func newZucsTaskService(lookup EntityIDLookup) (*UnifiedContextService, *zucsFakeRepo) {
	task := newZucsFakeRepo()
	user := "user-1"
	s := NewUnifiedContextService(newZucsFakeRepo(), newZucsFakeRepo(), newZucsFakeRepo(), task, nil, nil, nil, nil, &user)
	if lookup != nil {
		s = s.WithEntityLookup(lookup)
	}
	return s, task
}

// zucsTaskContext is a stored task context holding the creation-time copy of the task's fields.
func zucsTaskContext(id, status string) *entities.TaskContextUnified {
	c := entities.NewTaskContextUnified(id, "br-1")
	c.TaskData = map[string]any{
		"title":            "stored title",
		"description":      "stored description",
		"status":           status,
		"priority":         "low",
		"estimated_effort": "3d",
	}
	return c
}

func zucsServedTaskData(t *testing.T, res *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	t.Helper()
	contextAny, _ := res.Get("context")
	served, ok := contextAny.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("context is %T", contextAny)
	}
	td, present := served.Get("task_data")
	if !present {
		t.Fatal("task_data missing from the served context")
	}
	switch v := td.(type) {
	case *entities.OrderedMap[any]:
		return v
	case map[string]any:
		out := entities.NewOrderedMap[any]()
		for _, k := range []string{"title", "description", "status", "priority", "estimated_effort"} {
			if val, ok := v[k]; ok {
				out.Set(k, val)
			}
		}
		return out
	}
	t.Fatalf("task_data is %T", td)
	return nil
}

// The builder both the sync and the read overlay take the task's own fields from: the key set is
// the contract, the "@" handling is shared, and estimated_effort is deliberately absent.
func TestTaskOwnedFieldsFromTask(t *testing.T) {
	status, err := value_objects.NewTaskStatus("in_progress")
	if err != nil {
		t.Fatal(err)
	}
	created := time.Date(2026, 10, 11, 9, 30, 0, 0, time.UTC)
	task := &entities.Task{
		Status:          &status,
		Labels:          []string{"x", "y"},
		Assignees:       []string{"@alice", "bob"},
		EstimatedEffort: "2d",
	}
	// CreatedAt is promoted from the embedded BaseTimestampEntity: assignable, not literal-settable.
	task.CreatedAt = &created

	got := TaskOwnedFieldsFromTask(task)
	wantKeys := []string{"status", "priority", "labels", "assignees", "created_at"}
	if len(got) != len(wantKeys) {
		t.Fatalf("keys=%v want %v", got, wantKeys)
	}
	for _, k := range wantKeys {
		if _, ok := got[k]; !ok {
			t.Fatalf("missing %q in %v", k, got)
		}
	}
	if v, _ := got["status"].(string); v != "in_progress" {
		t.Fatalf("status=%v", got["status"])
	}
	assignees, _ := got["assignees"].([]string)
	if len(assignees) != 2 || assignees[0] != "@alice" || assignees[1] != "@bob" {
		t.Fatalf("assignees=%v: the @ handling is shared with the sync", assignees)
	}
	if v, _ := got["created_at"].(string); v == "" {
		t.Fatal("created_at must be formatted when the task carries one")
	}
	// A task with NO labels serves an empty list, never nil: the entity's own reader normalizes the
	// same way (task.go:85-86), and a nil slice would marshal to JSON null where the stored copy and
	// the entity both say [].
	bare := TaskOwnedFieldsFromTask(&entities.Task{})
	if labels, ok := bare["labels"].([]string); !ok || labels == nil || len(labels) != 0 {
		t.Fatalf("labels for a task with none = %#v, want a non-nil empty list", bare["labels"])
	}
	if _, ok := got["updated_at"]; ok {
		t.Fatal("a nil UpdatedAt must omit the key, as the sync did")
	}
	if _, ok := got["estimated_effort"]; ok {
		t.Fatal("estimated_effort belongs to the context's objective, not to these fields")
	}
	if TaskOwnedFieldsFromTask(nil) != nil {
		t.Fatal("a nil task must yield nil so the caller keeps the stored copy")
	}
}
