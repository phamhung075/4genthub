package httpapp

import (
	"context"

	"agenthub/fastmcp/server/routes"
	dtostask "agenthub/fastmcp/task_management/application/dtos/task"
	taskapicontroller "agenthub/fastmcp/task_management/interface/api_controllers/task_api_controller"
	"agenthub/fastmcp/types"
)

// userTaskControllerAdapter satisfies routes.UserTaskController over TaskAPIController,
// whose methods return typed pydantic-style responses.
type userTaskControllerAdapter struct {
	c *taskapicontroller.TaskAPIController
}

func (a userTaskControllerAdapter) CreateTask(ctx context.Context, req *dtostask.CreateTaskRequest, userID string) (routes.UserTaskResult, error) {
	r := a.c.CreateTask(ctx, req, userID)
	return routes.UserTaskResult{Success: r.Success, Error: r.Error, Message: r.Message, Body: r.ModelDump()}, nil
}

func (a userTaskControllerAdapter) GetTask(ctx context.Context, taskID, userID string) (routes.UserTaskResult, error) {
	r := a.c.GetTask(ctx, taskID, userID)
	return taskResult(r.Success, r.Error, r.Message, r.Task), nil
}

func (a userTaskControllerAdapter) UpdateTask(ctx context.Context, taskID string, req *dtostask.UpdateTaskRequest, userID string) (routes.UserTaskResult, error) {
	r := a.c.UpdateTask(ctx, taskID, req, userID)
	return taskResult(r.Success, r.Error, r.Message, r.Task), nil
}

func (a userTaskControllerAdapter) DeleteTask(ctx context.Context, taskID, userID string) (routes.UserTaskResult, error) {
	r := a.c.DeleteTask(ctx, taskID, userID)
	return routes.UserTaskResult{Success: r.Success, Error: r.Error, Message: r.Message}, nil
}

func (a userTaskControllerAdapter) CompleteTask(ctx context.Context, taskID, summary string, notes *string, userID string) (routes.UserTaskResult, error) {
	r := a.c.CompleteTask(ctx, taskID, summary, notes, userID)
	return taskResult(r.Success, r.Error, r.Message, r.Task), nil
}

func (a userTaskControllerAdapter) ListTasks(ctx context.Context, req *dtostask.ListTasksRequest, userID string) (routes.UserTaskListResult, error) {
	r := a.c.ListTasks(ctx, req, userID)
	tasks := make([]any, 0, len(r.Tasks))
	for _, t := range r.Tasks {
		tasks = append(tasks, t.ModelDump())
	}
	return routes.UserTaskListResult{Success: r.Success, Error: r.Error, Tasks: tasks}, nil
}

func taskResult(success bool, errMsg, msg *string, task *types.TaskDTO) routes.UserTaskResult {
	res := routes.UserTaskResult{Success: success, Error: errMsg, Message: msg}
	if success && task != nil {
		res.Task = task.ModelDump()
	}
	return res
}
