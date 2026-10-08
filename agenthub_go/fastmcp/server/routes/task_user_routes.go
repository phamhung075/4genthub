// task_user_routes.go ports server/routes/task_user_routes.py. FastAPI router
// and Depends plumbing dropped; handler logic, response dict order and status
// codes kept. The API controllers have no Go port yet.
package routes

import (
	"context"
	"strings"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	dtostask "agenthub/fastmcp/task_management/application/dtos/task"
	taskdomain "agenthub/fastmcp/task_management/domain/entities"
)

// UserTaskController is the minimal TaskAPIController surface.
type UserTaskController interface {
	CreateTask(ctx context.Context, req *dtostask.CreateTaskRequest, userID string) (UserTaskResult, error)
	ListTasks(ctx context.Context, req *dtostask.ListTasksRequest, userID string) (UserTaskListResult, error)
	GetTask(ctx context.Context, taskID, userID string) (UserTaskResult, error)
	UpdateTask(ctx context.Context, taskID string, req *dtostask.UpdateTaskRequest, userID string) (UserTaskResult, error)
	DeleteTask(ctx context.Context, taskID, userID string) (UserTaskResult, error)
	CompleteTask(ctx context.Context, taskID, summary string, notes *string, userID string) (UserTaskResult, error)
}

// UserTaskResult mirrors create/get/update/delete/complete result attributes.
type UserTaskResult struct {
	Success bool
	Error   *string
	Message *string
	Task    *taskdomain.OrderedMap[any]
	Body    *taskdomain.OrderedMap[any]
}

// UserTaskListResult mirrors list_tasks' tasks array.
type UserTaskListResult struct {
	Success bool
	Error   *string
	Tasks   []any
}

// UserSubtaskController is the minimal SubtaskAPIController surface.
type UserSubtaskController interface {
	ListSubtasks(ctx context.Context, taskID, userID string) (UserSubtaskResult, error)
}

// UserSubtaskResult mirrors list_subtasks.
type UserSubtaskResult struct {
	Success  bool
	Error    *string
	Subtasks []*taskdomain.OrderedMap[any]
}

// CreateUserTask ports create_task (POST /).
func CreateUserTask(ctx context.Context, req *dtostask.CreateTaskRequest, currentUser *authdomain.User, c UserTaskController) (*taskdomain.OrderedMap[any], error) {
	result, err := c.CreateTask(ctx, req, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to create task")
	}
	if !result.Success {
		return nil, httpErr(500, pyOrStr(result.Message, "Failed to create task"))
	}
	return result.Body, nil
}

// ListUserTasks ports list_tasks (GET /).
func ListUserTasks(ctx context.Context, req *dtostask.ListTasksRequest, currentUser *authdomain.User, c UserTaskController) (*taskdomain.OrderedMap[any], error) {
	result, err := c.ListTasks(ctx, req, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to list tasks")
	}
	tasks := []any{}
	if result.Success {
		if result.Tasks != nil {
			tasks = result.Tasks
		}
	}
	out := taskdomain.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("tasks", tasks)
	out.Set("count", len(tasks))
	out.Set("user", currentUser.Email)
	return out, nil
}

// GetUserTask ports get_task (GET /{task_id}).
func GetUserTask(ctx context.Context, taskID string, currentUser *authdomain.User, c UserTaskController) (*taskdomain.OrderedMap[any], error) {
	result, err := c.GetTask(ctx, taskID, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to get task")
	}
	if !result.Success {
		return nil, httpErr(404, "Task not found")
	}
	out := taskdomain.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("task", result.Task)
	return out, nil
}

// UpdateUserTask ports update_task (PUT /{task_id}).
func UpdateUserTask(ctx context.Context, taskID string, req *dtostask.UpdateTaskRequest, currentUser *authdomain.User, c UserTaskController) (*taskdomain.OrderedMap[any], error) {
	result, err := c.UpdateTask(ctx, taskID, req, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to update task")
	}
	if !result.Success {
		if result.Error != nil && strings.Contains(strings.ToLower(*result.Error), "not found") {
			return nil, httpErr(404, "Task not found")
		}
		return nil, httpErr(500, pyOrStr(result.Message, "Failed to update task"))
	}
	out := taskdomain.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("task", result.Task)
	out.Set("message", "Task updated successfully")
	return out, nil
}

// DeleteUserTask ports delete_task (DELETE /{task_id}).
func DeleteUserTask(ctx context.Context, taskID string, currentUser *authdomain.User, c UserTaskController) (*taskdomain.OrderedMap[any], error) {
	result, err := c.DeleteTask(ctx, taskID, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to delete task")
	}
	if !result.Success {
		if result.Error != nil && strings.Contains(strings.ToLower(*result.Error), "not found") {
			return nil, httpErr(404, "Task not found")
		}
		return nil, httpErr(500, pyOrStr(result.Message, "Failed to delete task"))
	}
	out := taskdomain.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("message", "Task deleted successfully")
	return out, nil
}

// CompleteUserTask ports complete_task (POST /{task_id}/complete).
func CompleteUserTask(ctx context.Context, taskID, completionSummary string, testingNotes *string, currentUser *authdomain.User, c UserTaskController) (*taskdomain.OrderedMap[any], error) {
	result, err := c.CompleteTask(ctx, taskID, completionSummary, testingNotes, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to complete task")
	}
	if !result.Success {
		if result.Error != nil && strings.Contains(strings.ToLower(*result.Error), "not found") {
			return nil, httpErr(404, "Task not found")
		}
		return nil, httpErr(500, pyOrStr(result.Message, "Failed to complete task"))
	}
	out := taskdomain.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("task", result.Task)
	out.Set("message", "Task completed successfully")
	return out, nil
}

// GetUserSubtaskSummaries ports get_subtask_summaries (POST /{task_id}/subtasks/summaries).
func GetUserSubtaskSummaries(ctx context.Context, taskID string, currentUser *authdomain.User, c UserSubtaskController) (*taskdomain.OrderedMap[any], error) {
	result, err := c.ListSubtasks(ctx, taskID, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, err.Error())
	}
	if !result.Success {
		return nil, httpErr(500, pyOrStr(result.Error, "Failed to fetch subtasks"))
	}
	summaries, statusCounts := trBuildSubtaskSummaries(result.Subtasks, true)
	progress := trBuildProgressSummary(summaries, statusCounts)
	out := taskdomain.NewOrderedMap[any]()
	out.Set("subtasks", summaries)
	out.Set("parent_task_id", taskID)
	out.Set("total_count", len(summaries))
	out.Set("progress_summary", progress)
	return out, nil
}
