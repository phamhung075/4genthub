package middleware

import (
	"reflect"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func validTaskEventData() *entities.OrderedMap[any] {
	return om(
		"id", "t1",
		"title", "Task",
		"status", "pending",
		"priority", "medium",
		"assignees", []any{"alice"},
		"subtask_count", int64(2),
		"completed_subtasks", int64(1),
		"progress_percentage", int64(50),
		"created_at", "2024-01-01T00:00:00+00:00",
		"updated_at", "2024-01-02T00:00:00+00:00",
	)
}

func validSubtaskEventData() *entities.OrderedMap[any] {
	return om(
		"id", "s1",
		"title", "Subtask",
		"status", "pending",
		"priority", "medium",
		"parent_task_id", "t1",
		"assignees", []any{},
		"progress_percentage", int64(0),
		"created_at", "2024-01-01T00:00:00+00:00",
		"updated_at", "2024-01-02T00:00:00+00:00",
	)
}

func TestWebSocketEventTypeValues(t *testing.T) {
	cases := map[WebSocketEventType]string{
		WebSocketEventTypeTaskCreated:      "task.created",
		WebSocketEventTypeTaskUpdated:      "task.updated",
		WebSocketEventTypeTaskDeleted:      "task.deleted",
		WebSocketEventTypeTaskCompleted:    "task.completed",
		WebSocketEventTypeSubtaskCreated:   "subtask.created",
		WebSocketEventTypeSubtaskUpdated:   "subtask.updated",
		WebSocketEventTypeSubtaskDeleted:   "subtask.deleted",
		WebSocketEventTypeSubtaskCompleted: "subtask.completed",
		WebSocketEventTypeBranchUpdated:    "branch.updated",
		WebSocketEventTypeProjectUpdated:   "project.updated",
		WebSocketEventTypeContextUpdated:   "context.updated",
	}
	for et, want := range cases {
		if string(et) != want {
			t.Errorf("%v = %q, want %q", et, string(et), want)
		}
	}
}

func TestValidateMessageTaskMissingRequired(t *testing.T) {
	msg := om("event", "task.created", "data", entities.NewOrderedMap[any]())
	errs := (WebSocketMessageValidator{}).ValidateMessage(msg)

	want := []string{
		"Task event 'task.created': Missing required field 'id'",
		"Task event 'task.created': Missing required field 'title'",
		"Task event 'task.created': Missing required field 'status'",
		"Task event 'task.created': Missing required field 'priority'",
		"Task event 'task.created': Missing required field 'assignees'",
		"Task event 'task.created': Missing required field 'subtask_count'",
		"Task event 'task.created': Missing required field 'completed_subtasks'",
		"Task event 'task.created': Missing required field 'progress_percentage'",
		"Task event 'task.created': Missing required field 'created_at'",
		"Task event 'task.created': Missing required field 'updated_at'",
	}
	if !reflect.DeepEqual(errs, want) {
		t.Fatalf("errors = %#v", errs)
	}
}

func TestValidateMessageTaskNullRequired(t *testing.T) {
	data := validTaskEventData()
	data.Set("title", nil)
	msg := om("event", "task.updated", "data", data)
	errs := (WebSocketMessageValidator{}).ValidateMessage(msg)
	want := []string{"Task event 'task.updated': Required field 'title' is null"}
	if !reflect.DeepEqual(errs, want) {
		t.Fatalf("errors = %#v", errs)
	}
}

func TestValidateMessageTaskWrongType(t *testing.T) {
	data := validTaskEventData()
	data.Set("subtask_count", "2")
	msg := om("event", "task.created", "data", data)
	errs := (WebSocketMessageValidator{}).ValidateMessage(msg)
	want := []string{"Task event 'task.created': Field 'subtask_count' has wrong type (expected int, got str)"}
	if !reflect.DeepEqual(errs, want) {
		t.Fatalf("errors = %#v", errs)
	}
}

func TestValidateMessageTaskCompletedExceedsCount(t *testing.T) {
	data := validTaskEventData()
	data.Set("subtask_count", int64(1))
	data.Set("completed_subtasks", int64(3))
	msg := om("event", "task.completed", "data", data)
	errs := (WebSocketMessageValidator{}).ValidateMessage(msg)
	want := []string{"Task event 'task.completed': completed_subtasks (3) exceeds subtask_count (1)"}
	if !reflect.DeepEqual(errs, want) {
		t.Fatalf("errors = %#v", errs)
	}
}

func TestValidateMessageTaskAssigneesNotList(t *testing.T) {
	data := validTaskEventData()
	data.Set("assignees", "nope")
	msg := om("event", "task.created", "data", data)
	errs := (WebSocketMessageValidator{}).ValidateMessage(msg)
	want := []string{
		"Task event 'task.created': Field 'assignees' has wrong type (expected list, got str)",
		"Task event 'task.created': assignees must be a list, got str",
	}
	if !reflect.DeepEqual(errs, want) {
		t.Fatalf("errors = %#v", errs)
	}
}

func TestValidateMessageTaskAssigneeElements(t *testing.T) {
	data := validTaskEventData()
	data.Set("assignees", []any{"alice", int64(2)})
	msg := om("event", "task.created", "data", data)
	errs := (WebSocketMessageValidator{}).ValidateMessage(msg)
	want := []string{"Task event 'task.created': assignees[1] must be string"}
	if !reflect.DeepEqual(errs, want) {
		t.Fatalf("errors = %#v", errs)
	}
}

func TestValidateMessageSubtaskMissingRequired(t *testing.T) {
	msg := om("event", "subtask.created", "data", entities.NewOrderedMap[any]())
	errs := (WebSocketMessageValidator{}).ValidateMessage(msg)
	want := []string{
		"Subtask event 'subtask.created': Missing required field 'id'",
		"Subtask event 'subtask.created': Missing required field 'title'",
		"Subtask event 'subtask.created': Missing required field 'status'",
		"Subtask event 'subtask.created': Missing required field 'priority'",
		"Subtask event 'subtask.created': Missing required field 'parent_task_id'",
		"Subtask event 'subtask.created': Missing required field 'assignees'",
		"Subtask event 'subtask.created': Missing required field 'progress_percentage'",
		"Subtask event 'subtask.created': Missing required field 'created_at'",
		"Subtask event 'subtask.created': Missing required field 'updated_at'",
	}
	if !reflect.DeepEqual(errs, want) {
		t.Fatalf("errors = %#v", errs)
	}
}

func TestValidateMessageSubtaskWrongType(t *testing.T) {
	data := validSubtaskEventData()
	data.Set("progress_percentage", "half")
	msg := om("event", "subtask.updated", "data", data)
	errs := (WebSocketMessageValidator{}).ValidateMessage(msg)
	want := []string{"Subtask event 'subtask.updated': Field 'progress_percentage' has wrong type (expected int, got str)"}
	if !reflect.DeepEqual(errs, want) {
		t.Fatalf("errors = %#v", errs)
	}
}

func TestValidateMessageBaseStructure(t *testing.T) {
	// Non-dict message.
	if errs := (WebSocketMessageValidator{}).ValidateMessage("nope"); !reflect.DeepEqual(errs, []string{"Message must be a dictionary"}) {
		t.Fatalf("errors = %#v", errs)
	}
	// Missing event.
	msg := om("data", entities.NewOrderedMap[any]())
	if errs := (WebSocketMessageValidator{}).ValidateMessage(msg); !reflect.DeepEqual(errs, []string{"Missing required field: 'event'"}) {
		t.Fatalf("errors = %#v", errs)
	}
	// Non-string event.
	msg = om("event", int64(1), "data", entities.NewOrderedMap[any]())
	if errs := (WebSocketMessageValidator{}).ValidateMessage(msg); len(errs) != 1 || errs[0] != "Field 'event' must be a string" {
		t.Fatalf("errors = %#v", errs)
	}
	// Missing data.
	msg = om("event", "task.created")
	if errs := (WebSocketMessageValidator{}).ValidateMessage(msg); len(errs) == 0 || errs[0] != "Missing required field: 'data'" {
		t.Fatalf("errors = %#v", errs)
	}
	// Non-dict data.
	msg = om("event", "task.created", "data", "x")
	if errs := (WebSocketMessageValidator{}).ValidateMessage(msg); !reflect.DeepEqual(errs, []string{"Field 'data' must be a dictionary"}) {
		t.Fatalf("errors = %#v", errs)
	}
}

func TestWebSocketMessageLoggerCountersAndStats(t *testing.T) {
	l := NewWebSocketMessageLogger()

	errs := l.LogMessage("task.created", entities.NewOrderedMap[any](), nil, true)
	if len(errs) != 10 {
		t.Fatalf("len(errs) = %d", len(errs))
	}
	if l.MessageCount != 1 || l.ErrorCount != 1 || len(l.ValidationErrors) != 10 {
		t.Fatalf("counters = %d/%d/%d", l.MessageCount, l.ErrorCount, len(l.ValidationErrors))
	}

	if errs := l.LogMessage("task.created", validTaskEventData(), nil, true); len(errs) != 0 {
		t.Fatalf("valid message errors = %#v", errs)
	}
	if l.MessageCount != 2 || l.ErrorCount != 1 {
		t.Fatalf("counters = %d/%d", l.MessageCount, l.ErrorCount)
	}

	stats := l.GetStats()
	if got := stats.Keys(); !reflect.DeepEqual(got, []string{"total_messages", "validation_errors", "error_rate", "recent_errors"}) {
		t.Fatalf("keys = %#v", got)
	}
	if v, _ := stats.Get("total_messages"); v != 2 {
		t.Fatalf("total_messages = %#v", v)
	}
	if v, _ := stats.Get("validation_errors"); v != 1 {
		t.Fatalf("validation_errors = %#v", v)
	}
	if v, _ := stats.Get("error_rate"); v != "50.0%" {
		t.Fatalf("error_rate = %#v", v)
	}
	if v, _ := stats.Get("recent_errors"); !reflect.DeepEqual(v, l.ValidationErrors[len(l.ValidationErrors)-10:]) {
		t.Fatalf("recent_errors = %#v", v)
	}
}

func TestWebSocketMessageLoggerValidateFalseAndEmptyStats(t *testing.T) {
	empty := NewWebSocketMessageLogger()
	stats := empty.GetStats()
	if v, _ := stats.Get("error_rate"); v != "0.0%" {
		t.Fatalf("error_rate = %#v", v)
	}
	if v, _ := stats.Get("recent_errors"); !reflect.DeepEqual(v, []string{}) {
		t.Fatalf("recent_errors = %#v", v)
	}

	l := NewWebSocketMessageLogger()
	if errs := l.LogMessage("task.created", entities.NewOrderedMap[any](), nil, false); len(errs) != 0 {
		t.Fatalf("validate=false errors = %#v", errs)
	}
	if l.ErrorCount != 0 || len(l.ValidationErrors) != 0 {
		t.Fatalf("counters = %d/%d", l.ErrorCount, len(l.ValidationErrors))
	}
	if l.MessageCount != 1 {
		t.Fatalf("message_count = %d", l.MessageCount)
	}
}

func TestWebSocketMessageLoggerRecentErrorsLastTen(t *testing.T) {
	l := NewWebSocketMessageLogger()
	l.MessageCount = 12
	l.ErrorCount = 12
	for i := 1; i <= 12; i++ {
		l.ValidationErrors = append(l.ValidationErrors, string(rune('a'+i-1)))
	}
	recent, _ := l.GetStats().Get("recent_errors")
	want := []string{"c", "d", "e", "f", "g", "h", "i", "j", "k", "l"}
	if !reflect.DeepEqual(recent, want) {
		t.Fatalf("recent_errors = %#v", recent)
	}
}

func TestGlobalWebSocketLogger(t *testing.T) {
	// Reset the module-level logger to a known state.
	globalWebSocketLogger.MessageCount = 0
	globalWebSocketLogger.ErrorCount = 0
	globalWebSocketLogger.ValidationErrors = []string{}

	if errs := LogWebSocketMessage("branch.updated", entities.NewOrderedMap[any](), nil, true); len(errs) != 0 {
		t.Fatalf("branch.updated errors = %#v", errs)
	}
	if GetWebSocketLogger().MessageCount != 1 {
		t.Fatalf("message_count = %d", GetWebSocketLogger().MessageCount)
	}

	errs := LogWebSocketMessage("task.created", entities.NewOrderedMap[any](), nil, true)
	if len(errs) != 10 {
		t.Fatalf("len(errs) = %d", len(errs))
	}
	if GetWebSocketLogger().ErrorCount != 1 {
		t.Fatalf("error_count = %d", GetWebSocketLogger().ErrorCount)
	}
	stats := GetWebSocketStats()
	if v, _ := stats.Get("total_messages"); v != 2 {
		t.Fatalf("total_messages = %#v", v)
	}
	if v, _ := stats.Get("validation_errors"); v != 1 {
		t.Fatalf("validation_errors = %#v", v)
	}
}
