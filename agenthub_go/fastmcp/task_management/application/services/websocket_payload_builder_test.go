package services

import (
	"context"
	"testing"
	"time"

	taskdtos "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func wsTestTask() *entities.Task {
	return &entities.Task{
		Title:       "Build payload",
		Description: "short",
		ID:          &value_objects.TaskId{EntityId: value_objects.EntityId{Value: "t-1"}},
		Status:      &value_objects.TaskStatus{Value: "todo"},
		Priority:    &value_objects.Priority{Value: "medium"},
		GitBranchID: wsStrPtr("branch-1"),
		ProgressHistory: map[string]any{
			"progress_1": map[string]any{"progress_number": 1},
		},
		ProgressCount: 1,
		Assignees:     []string{"alice"},
		Labels:        []string{"bug"},
		Dependencies:  []value_objects.TaskId{{EntityId: value_objects.EntityId{Value: "t-0"}}},
		Subtasks:      []string{"s-1", "s-2"},
		ContextID:     wsStrPtr("ctx-1"),
	}
}

func wsStrPtr(s string) *string { return &s }

func wsTaskWithCreated(t *entities.Task) *entities.Task {
	c := time.Date(2024, 1, 2, 3, 4, 5, 0, time.UTC)
	t.CreatedAt = &c
	t.UpdatedAt = &c
	return t
}

func TestBuildTaskPayload_EntityOrderAndValues(t *testing.T) {
	task := wsTaskWithCreated(wsTestTask())
	payload := WebSocketPayloadBuilder{}.BuildTaskPayload(task, nil, true)

	wantKeys := []string{
		"id", "title", "status", "priority",
		"project_id", "git_branch_id", "subtask_count", "completed_subtasks",
		"progress_percentage", "progress_count", "progress_history", "details",
		"assignees", "has_dependencies", "has_context", "labels",
		"created_at", "updated_at", "description",
	}
	gotKeys := payload.Keys()
	if len(gotKeys) != len(wantKeys) {
		t.Fatalf("key count = %d, want %d (%v)", len(gotKeys), len(wantKeys), gotKeys)
	}
	for i, k := range wantKeys {
		if gotKeys[i] != k {
			t.Fatalf("key[%d] = %q, want %q (all: %v)", i, gotKeys[i], k, gotKeys)
		}
	}

	checks := map[string]any{
		"id":                  "t-1",
		"title":               "Build payload",
		"status":              "todo",
		"priority":            "medium",
		"project_id":          nil,
		"git_branch_id":       "branch-1",
		"subtask_count":       2,
		"completed_subtasks":  0,
		"progress_percentage": 0,
		"progress_count":      1,
		"has_dependencies":    true,
		"has_context":         true,
		"created_at":          "2024-01-02T03:04:05+00:00",
		"updated_at":          "2024-01-02T03:04:05+00:00",
		"description":         "short",
	}
	for k, want := range checks {
		got, _ := payload.Get(k)
		if got != want {
			t.Errorf("%s = %#v, want %#v", k, got, want)
		}
	}
	assignees, _ := payload.Get("assignees")
	if len(assignees.([]string)) != 1 || assignees.([]string)[0] != "alice" {
		t.Errorf("assignees = %#v", assignees)
	}
	labels, _ := payload.Get("labels")
	if len(labels.([]string)) != 1 || labels.([]string)[0] != "bug" {
		t.Errorf("labels = %#v", labels)
	}
}

func TestBuildTaskPayload_LongDescriptionTruncated(t *testing.T) {
	long := ""
	for i := 0; i < 205; i++ {
		long += "x"
	}
	task := wsTestTask()
	task.Description = long
	payload := WebSocketPayloadBuilder{}.BuildTaskPayload(task, nil, true)
	got, _ := payload.Get("description")
	want := long[:200] + "..."
	if got != want {
		t.Fatalf("description = %q, want %q", got, want)
	}
}

func TestBuildTaskPayload_LightweightOmitsHistory(t *testing.T) {
	task := wsTaskWithCreated(wsTestTask())
	payload := WebSocketPayloadBuilder{}.BuildLightweightPayload(task, nil)
	ph, _ := payload.Get("progress_history")
	if m, ok := ph.(map[string]any); !ok || len(m) != 0 {
		t.Fatalf("progress_history = %#v, want empty map", ph)
	}
	details, _ := payload.Get("details")
	if details != "" {
		t.Fatalf("details = %#v, want empty string", details)
	}
}

func TestBuildTaskPayload_FromResponse(t *testing.T) {
	task := wsTaskWithCreated(wsTestTask())
	resp := taskdtos.NewTaskResponse(taskdtos.TaskResponse{
		ProjectID:         wsStrPtr("proj-1"),
		GitBranchID:       wsStrPtr("branch-2"),
		Subtasks:          []any{"a", "b", "c"},
		CompletedSubtasks: 2,
		ProgressCount:     3,
		Details:           "history text",
	})
	payload := WebSocketPayloadBuilder{}.BuildTaskPayload(task, resp, true)
	checks := map[string]any{
		"project_id":         "proj-1",
		"git_branch_id":      "branch-2",
		"subtask_count":      3,
		"completed_subtasks": 2,
		"progress_count":     3,
		"details":            "history text",
	}
	for k, want := range checks {
		got, _ := payload.Get(k)
		if got != want {
			t.Errorf("%s = %#v, want %#v", k, got, want)
		}
	}
}

func TestEstimatePayloadSize(t *testing.T) {
	task := wsTaskWithCreated(wsTestTask())
	payload := WebSocketPayloadBuilder{}.BuildTaskPayload(task, nil, true)
	size := WebSocketPayloadBuilder{}.EstimatePayloadSize(payload)
	if size <= 0 {
		t.Fatalf("size = %d, want > 0", size)
	}
	// json.dumps default separators: ", " and ": ".
	if s := string(payloadKeysSample(payload)); s == "" {
		t.Fatalf("unexpected empty sample")
	}
}

// payloadKeysSample forces a compact JSON encoding to prove the OrderedMap is
// serialisable through PyJSONDumps.
func payloadKeysSample(payload *entities.OrderedMap[any]) []byte {
	s, err := value_objects.PyJSONDumps(payload, -1)
	if err != nil {
		return nil
	}
	return []byte(s)
}

func TestIsDuplicateNotification(t *testing.T) {
	// Use unique identifiers so the process-global cache does not leak state.
	wsNotificationCacheMu.Lock()
	wsNotificationCache = map[string]float64{}
	wsNotificationCacheMu.Unlock()

	if wsIsDuplicateNotification("created", "task", "dup-1", "u1") {
		t.Fatal("first call must not be duplicate")
	}
	if !wsIsDuplicateNotification("created", "task", "dup-1", "u1") {
		t.Fatal("second immediate call must be duplicate")
	}
	if wsIsDuplicateNotification("created", "task", "dup-2", "u1") {
		t.Fatal("different key must not be duplicate")
	}
}

type wsRecordingBroker struct {
	eventType  string
	entityType string
	entityID   string
	metadata   *entities.OrderedMap[any]
	calls      int
}

func (b *wsRecordingBroker) BroadcastDataChange(_ context.Context, eventType, entityType, entityID, userID string, data any, metadata *entities.OrderedMap[any]) error {
	b.eventType, b.entityType, b.entityID, b.metadata = eventType, entityType, entityID, metadata
	b.calls++
	return nil
}

func TestBroadcastTaskEvent_MetadataOrder(t *testing.T) {
	wsNotificationCacheMu.Lock()
	wsNotificationCache = map[string]float64{}
	wsNotificationCacheMu.Unlock()

	broker := &wsRecordingBroker{}
	svc := &WebSocketNotificationService{Broker: broker}
	err := svc.BroadcastTaskEvent(
		context.Background(), "created", "task-9", "user-9",
		entities.NewOrderedMap[any](), wsStrPtr("branch-9"), wsStrPtr("proj-9"),
	)
	if err != nil {
		t.Fatal(err)
	}
	if broker.calls != 1 || broker.entityType != "task" || broker.entityID != "task-9" {
		t.Fatalf("broker got calls=%d entity=%s/%s", broker.calls, broker.entityType, broker.entityID)
	}
	keys := broker.metadata.Keys()
	want := []string{"git_branch_id", "project_id", "timestamp", "task_title", "parent_branch_id", "parent_branch_title"}
	if len(keys) != len(want) {
		t.Fatalf("metadata keys = %v, want %v", keys, want)
	}
	for i := range want {
		if keys[i] != want[i] {
			t.Fatalf("metadata key[%d] = %q, want %q", i, keys[i], want[i])
		}
	}
	// No provider -> Python fallback context.
	if v, _ := broker.metadata.Get("task_title"); v != "Task task-9" {
		t.Fatalf("task_title = %#v", v)
	}
	if v, _ := broker.metadata.Get("parent_branch_title"); v != "Unknown Branch" {
		t.Fatalf("parent_branch_title = %#v", v)
	}
}
