package routes

import (
	"context"
	"testing"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	dtostask "agenthub/fastmcp/task_management/application/dtos/task"
)

// listControllerStub serves one canned list result and satisfies UserTaskController's full surface.
type listControllerStub struct {
	result UserTaskListResult
	err    error
}

func (s listControllerStub) ListTasks(context.Context, *dtostask.ListTasksRequest, string) (UserTaskListResult, error) {
	return s.result, s.err
}
func (s listControllerStub) CreateTask(context.Context, *dtostask.CreateTaskRequest, string) (UserTaskResult, error) {
	return UserTaskResult{}, nil
}
func (s listControllerStub) GetTask(context.Context, string, string) (UserTaskResult, error) {
	return UserTaskResult{}, nil
}
func (s listControllerStub) UpdateTask(context.Context, string, *dtostask.UpdateTaskRequest, string) (UserTaskResult, error) {
	return UserTaskResult{}, nil
}
func (s listControllerStub) DeleteTask(context.Context, string, string) (UserTaskResult, error) {
	return UserTaskResult{}, nil
}
func (s listControllerStub) CompleteTask(context.Context, string, string, *string, string) (UserTaskResult, error) {
	return UserTaskResult{}, nil
}
func (s listControllerStub) GetTaskStatistics(context.Context, string) (UserTaskStatsResult, error) {
	return UserTaskStatsResult{}, nil
}

// TestListUserTasksKeepsTheInheritedEnvelope pins what the WIRE does when the listing FAILED: 200 with
// {"success": true, "tasks": [], "count": 0, "user": <email>}.
//
// THAT IS NOT A PORT ACCIDENT, and this test exists so nobody "fixes" it by accident or leaves it
// undocumented. The retired Python catches the failure and flags it (crud_handler.py:333-339 for a
// failed result, :352-362 for a raised one, both returning TasksResponse(success=False, ...)), and its
// route then renders the flag as exactly these bytes - task_user_routes.py:126-140 sets tasks = [] when
// controller_result.success is false, and :175-180 returns the envelope with success True. The Go route
// reproducing that is parity.
//
// The consequence, measured on the OF4 stack: a row the DOMAIN refuses (an empty description -
// task.py:197-198 in the retired Python, the same rule in entities.NewTask) makes the entire list look
// empty and healthy. The diagnostic for that lives in the handler's log now
// (handlers/crud_handler.go, listLogWarn/listLogError, mirroring Python's two log lines), NOT here.
// If the owner decides a 500 is worth more than a cheerful empty page, this is the test that changes.
func TestListUserTasksKeepsTheInheritedEnvelope(t *testing.T) {
	failure := "Task description cannot be empty"
	body, err := ListUserTasks(context.Background(), &dtostask.ListTasksRequest{},
		&authdomain.User{Email: "dev@example.com"},
		listControllerStub{result: UserTaskListResult{Success: false, Error: &failure}})
	if err != nil {
		t.Fatalf("ListUserTasks returned an error, so the envelope is not the Python one: %v", err)
	}

	if success, _ := body.Get("success"); success != true {
		t.Errorf("success = %v, want true: this is the inherited envelope, not a claim that the read worked", success)
	}
	tasks, _ := body.Get("tasks")
	if list, ok := tasks.([]any); !ok || len(list) != 0 {
		t.Errorf("tasks = %v, want an empty list", tasks)
	}
	if count, _ := body.Get("count"); count != 0 {
		t.Errorf("count = %v, want 0", count)
	}
	if user, _ := body.Get("user"); user != "dev@example.com" {
		t.Errorf("user = %v, want the current user's email", user)
	}
	// And the message the controller did carry is NOT in the envelope - which is precisely why the
	// handler must log it.
	for _, key := range []string{"error", "message", "detail"} {
		if v, ok := body.Get(key); ok && v != nil {
			t.Errorf("the envelope carries %q (%v): the failure is not surfaced here in the retired Python either", key, v)
		}
	}
}
