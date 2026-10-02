package handlers

import (
	"context"
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
func (f *fakeTaskFacade) GetTaskStatistics(context.Context, string) any  { return nil }
func (f *fakeTaskFacade) CountTasks(context.Context, map[string]any) any { return f.countResult }
func (f *fakeTaskFacade) ListTasksSummary(context.Context, map[string]any, int, int) *entities.OrderedMap[any] {
	return nil
}
func (f *fakeTaskFacade) GetTaskWithRelations(context.Context, string) any { return nil }

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
