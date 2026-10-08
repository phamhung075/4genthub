package handlers

import (
	"bytes"
	"context"
	"errors"
	"log/slog"
	"strings"
	"testing"

	taskdto "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
)

// fakeTaskFacade implements TaskHandlerFacade with canned responses.
type fakeTaskFacade struct {
	getTaskResult *entities.OrderedMap[any]
	listResult    *entities.OrderedMap[any]
	countResult   any
}

func (f *fakeTaskFacade) CreateTask(context.Context, *taskdto.CreateTaskRequest) *entities.OrderedMap[any] {
	return nil
}
func (f *fakeTaskFacade) GetTask(context.Context, string) *entities.OrderedMap[any] {
	return f.getTaskResult
}
func (f *fakeTaskFacade) UpdateTask(context.Context, *taskdto.UpdateTaskRequest) *entities.OrderedMap[any] {
	return nil
}
func (f *fakeTaskFacade) DeleteTask(context.Context, string, string) *entities.OrderedMap[any] {
	return nil
}
func (f *fakeTaskFacade) ListTasks(context.Context, *taskdto.ListTasksRequest, bool, bool) *entities.OrderedMap[any] {
	return f.listResult
}
func (f *fakeTaskFacade) CompleteTask(context.Context, string, string, *string, string) *entities.OrderedMap[any] {
	return nil
}
func (f *fakeTaskFacade) CountTasks(context.Context, map[string]any) any { return f.countResult }
func (f *fakeTaskFacade) ListTasksSummary(context.Context, map[string]any, int, int) *entities.OrderedMap[any] {
	return nil
}

type fakeFacadeService struct{ facade TaskHandlerFacade }

func (s fakeFacadeService) GetTaskFacade(_, _, _ *string) (any, error) { return s.facade, nil }

func om(pairs ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(pairs); i += 2 {
		m.Set(pairs[i].(string), pairs[i+1])
	}
	return m
}

// TestGetTaskSuccess mirrors crud_handler.get_task's success branch: success
// true, task dict converted through task_to_dto(include_subtasks=False).
func TestGetTaskSuccess(t *testing.T) {
	task := om("id", "t1", "title", "Hi", "status", "todo", "priority", "high", "git_branch_id", "b1")
	facade := &fakeTaskFacade{getTaskResult: om("success", true, "task", task)}
	h := NewTaskCrudHandler(fakeFacadeService{facade: facade})
	resp := h.GetTask(context.Background(), "t1", "u1")
	if !resp.Success {
		t.Fatalf("success = false, error=%v", func() string {
			if resp.Error != nil {
				return *resp.Error
			}
			return "<nil>"
		}())
	}
	if resp.Task == nil || resp.Task.ID != "t1" || resp.Task.Title != "Hi" || resp.Task.Status != "todo" {
		t.Fatalf("task = %+v", resp.Task)
	}
	if resp.Error != nil {
		t.Fatalf("error = %v, want nil", *resp.Error)
	}
}

// TestGetTaskFacadeError mirrors the facade result {"success": false,
// "error": ...}: error and message both carry the facade error.
func TestGetTaskFacadeError(t *testing.T) {
	facade := &fakeTaskFacade{getTaskResult: om("success", false, "error", "boom")}
	h := NewTaskCrudHandler(fakeFacadeService{facade: facade})
	resp := h.GetTask(context.Background(), "t1", "u1")
	if resp.Success {
		t.Fatal("success = true, want false")
	}
	if resp.Error == nil || *resp.Error != "boom" || resp.Message == nil || *resp.Message != "boom" {
		t.Fatalf("error/message = %v/%v", resp.Error, resp.Message)
	}
}

// TestGetTaskMissing mirrors `task = result.get("task")` being falsy: the
// controller returns "Task not found" / "Task not found or access denied".
func TestGetTaskMissing(t *testing.T) {
	facade := &fakeTaskFacade{getTaskResult: om("success", true, "task", nil)}
	h := NewTaskCrudHandler(fakeFacadeService{facade: facade})
	resp := h.GetTask(context.Background(), "t1", "u1")
	if resp.Success {
		t.Fatal("success = true, want false")
	}
	if resp.Error == nil || *resp.Error != "Task not found" {
		t.Fatalf("error = %v", resp.Error)
	}
	if resp.Message == nil || *resp.Message != "Task not found or access denied" {
		t.Fatalf("message = %v", resp.Message)
	}
}

// TestListTasks mirrors list_tasks: tasks converted, total = len(tasks).
func TestListTasks(t *testing.T) {
	task1 := om("id", "t1", "title", "A", "status", "todo", "priority", "low", "git_branch_id", "b1")
	task2 := om("id", "t2", "title", "B", "status", "done", "priority", "high", "git_branch_id", "b1")
	facade := &fakeTaskFacade{listResult: om("success", true, "tasks", []any{task1, task2})}
	h := NewTaskCrudHandler(fakeFacadeService{facade: facade})
	resp := h.ListTasks(context.Background(), &taskdto.ListTasksRequest{}, "u1")
	if !resp.Success || len(resp.Tasks) != 2 {
		t.Fatalf("success=%v tasks=%d", resp.Success, len(resp.Tasks))
	}
	if resp.Total == nil || *resp.Total != 2 {
		t.Fatalf("total = %v", resp.Total)
	}
}

// TestListTasksLogsTheFailureAndKeepsTheParityResponse pins the PAIR the lead ruled on: a listing
// that fails must be REPORTED with its message, while the response stays exactly as the retired Python
// leaves it.
//
// WHY THE PAIR AND NOT JUST THE LOG: the failure is invisible to the caller by design in both
// implementations - Python flags it in the handler and its route renders the flag as
// 200 {"success": true, "tasks": [], "count": 0} (task_user_routes.py:126-140, :175-180), and the Go
// route does the same (fastmcp/server/routes/task_user_routes.go). So a row the domain refuses - an
// empty description is the one that cost three seats an evening, task.py:197-198 in the retired
// Python and the same rule in entities.NewTask - made the whole list look EMPTY. The log is the only
// place the cause can surface; the wire contract is parity and must not drift while it is pinned here.
func TestListTasksLogsTheFailureAndKeepsTheParityResponse(t *testing.T) {
	var buf bytes.Buffer
	previous := listFailureLog
	listFailureLog = slog.New(slog.NewTextHandler(&buf, nil))
	defer func() { listFailureLog = previous }()

	facade := &fakeTaskFacade{listResult: om("success", false, "error", "Task description cannot be empty")}
	h := NewTaskCrudHandler(fakeFacadeService{facade: facade})

	resp := h.ListTasks(context.Background(), &taskdto.ListTasksRequest{}, "u1")

	// Half one: the response keeps the Python shape - a failure flag carrying the message, which the
	// route is free to render as its empty success envelope.
	if resp.Success {
		t.Errorf("success = true, want false: a refused listing must not report success")
	}
	if resp.Error == nil || *resp.Error != "Task description cannot be empty" {
		t.Errorf("error = %v, want the facade's message", resp.Error)
	}
	if len(resp.Tasks) != 0 {
		t.Errorf("tasks = %d, want 0", len(resp.Tasks))
	}

	// Half two: the message reached the log, in the Python's own words (crud_handler.py:332).
	logged := buf.String()
	if !strings.Contains(logged, "Task listing failed for user u1") {
		t.Errorf("the Python's warning wording is missing from the log: %q", logged)
	}
	if !strings.Contains(logged, "Task description cannot be empty") {
		t.Errorf("the CAUSE is missing from the log, which is the whole point: %q", logged)
	}
	if !strings.Contains(logged, "level=WARN") {
		t.Errorf("the failed-result branch must warn, as Python does: %q", logged)
	}
}

// TestListTasksLogsAnErrorWhenTheFacadeRaises covers the other Python log line (crud_handler.py:342,
// error with exc_info): a facade that cannot even be built is reported at error level with the cause,
// and the response still carries it.
func TestListTasksLogsAnErrorWhenTheFacadeRaises(t *testing.T) {
	var buf bytes.Buffer
	previous := listFailureLog
	listFailureLog = slog.New(slog.NewTextHandler(&buf, nil))
	defer func() { listFailureLog = previous }()

	h := NewTaskCrudHandler(raisingFacadeService{err: errors.New("database is gone")})
	resp := h.ListTasks(context.Background(), &taskdto.ListTasksRequest{}, "u2")

	if resp.Success {
		t.Errorf("success = true, want false")
	}
	logged := buf.String()
	if !strings.Contains(logged, "Error listing tasks for user u2") {
		t.Errorf("the Python's error wording is missing: %q", logged)
	}
	if !strings.Contains(logged, "database is gone") {
		t.Errorf("the cause is missing: %q", logged)
	}
	if !strings.Contains(logged, "level=ERROR") {
		t.Errorf("a raised facade must be logged at error level, as Python does: %q", logged)
	}
}

// raisingFacadeService is a facade service whose GetTaskFacade fails, mirroring the Python path where
// building the facade raises (caught by crud_handler.py:352-362).
type raisingFacadeService struct{ err error }

func (s raisingFacadeService) GetTaskFacade(_, _, _ *string) (any, error) { return nil, s.err }

// TestCountTasksLegacyInt mirrors search_handler.count_tasks when the facade
// returns a bare count (legacy format): success true, count as-is, filters
// echoed with user_id added.
func TestCountTasksLegacyInt(t *testing.T) {
	facade := &fakeTaskFacade{countResult: 7}
	h := NewTaskSearchHandler(fakeFacadeService{facade: facade})
	filters := om("status", "todo")
	resp := h.CountTasks(context.Background(), filters, "u1")
	if !resp.Success || resp.Count == nil || *resp.Count != 7 {
		t.Fatalf("success=%v count=%v", resp.Success, resp.Count)
	}
	if got, _ := filters.Get("user_id"); got != "u1" {
		t.Fatalf("filters user_id = %v", got)
	}
}
