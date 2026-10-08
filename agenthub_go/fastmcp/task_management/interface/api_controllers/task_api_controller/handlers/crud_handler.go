// Package handlers ports task_management/interface/api_controllers/
// task_api_controller/handlers (Python). TaskCrudHandler etc. delegate to the
// task/subtask application facades; the facades are reached through the
// consumer-side interfaces declared here because the Go facades package does
// not (yet) expose the full method set used by the Python handlers.
package handlers

import (
	"context"
	"fmt"
	"log/slog"
	"time"

	taskdto "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/types"
)

// TaskHandlerFacade is the consumer-side view of the task application facade
// used by the three task handlers. Method names mirror the Python facade.
type TaskHandlerFacade interface {
	CreateTask(ctx context.Context, request *taskdto.CreateTaskRequest) *entities.OrderedMap[any]
	GetTask(ctx context.Context, taskID string) *entities.OrderedMap[any]
	UpdateTask(ctx context.Context, request *taskdto.UpdateTaskRequest) *entities.OrderedMap[any]
	DeleteTask(ctx context.Context, taskID, userID string) *entities.OrderedMap[any]
	ListTasks(ctx context.Context, request *taskdto.ListTasksRequest, includeDependencies, minimal bool) *entities.OrderedMap[any]
	CompleteTask(ctx context.Context, taskID, completionSummary string, testingNotes *string, userID string) *entities.OrderedMap[any]
	CountTasks(ctx context.Context, filters map[string]any) any
	ListTasksSummary(ctx context.Context, filters map[string]any, offset, limit int) *entities.OrderedMap[any]
}

// TaskFacadeService mirrors FacadeService.get_task_facade. The signature matches
// services.FacadeService so that the real service satisfies it; the untyped
// Python return is the `any`, asserted to TaskHandlerFacade by the handlers.
type TaskFacadeService interface {
	GetTaskFacade(projectID, gitBranchID, userID *string) (any, error)
}

// TaskCrudHandler mirrors crud_handler.TaskCrudHandler.
type TaskCrudHandler struct {
	facadeService TaskFacadeService
}

// NewTaskCrudHandler builds the handler. Python resolves the facade lazily
// through FacadeService; the Go service is injected.
func NewTaskCrudHandler(facadeService TaskFacadeService) *TaskCrudHandler {
	return &TaskCrudHandler{facadeService: facadeService}
}

// thNow is datetime.now(UTC).isoformat().
func thNow() *string {
	s := value_objects.IsoFormat(time.Now().UTC())
	return &s
}

// thOmGet is dict.get(key) returning nil (Python None) when absent.
func thOmGet(m *entities.OrderedMap[any], key string) any {
	if m == nil {
		return nil
	}
	v, _ := m.Get(key)
	return v
}

// thOmGetDefault is dict.get(key, def) (present-but-None stays None).
func thOmGetDefault(m *entities.OrderedMap[any], key string, def any) any {
	if m != nil {
		if v, ok := m.Get(key); ok {
			return v
		}
	}
	return def
}

// thSuccess is result.get("success") truthiness.
func thSuccess(m *entities.OrderedMap[any]) bool {
	return value_objects.PyTruthy(thOmGet(m, "success"))
}

// thMsg converts a Python error/message value to a *string (None -> nil).
func thMsg(v any) *string {
	if v == nil {
		return nil
	}
	s := value_objects.PyStr(v)
	return &s
}

// thPanicStr renders a recovered panic value as str(exc).
func thPanicStr(r any) *string {
	s := value_objects.PyStr(r)
	return &s
}

// thTaskValue converts a facade task value the way Python's
// `task_to_dto(task) if isinstance(task, dict) else task` does: a dict is
// converted, an already-built DTO passes through, None stays nil.
func thTaskValue(task any, includeSubtasks bool) (*types.TaskDTO, error) {
	if task == nil {
		return nil, nil
	}
	if dto, ok := task.(*types.TaskDTO); ok {
		return dto, nil
	}
	return types.TaskToDTO(task, includeSubtasks)
}

// thErrorMsg mirrors result.get("error", default).
func thErrorMsg(m *entities.OrderedMap[any], def string) *string {
	return thMsg(thOmGetDefault(m, "error", def))
}

// thPanicked fills a TaskResponse after a recovered panic, mirroring the
// generic `except Exception` branches.
func thPanicked(resp *types.TaskResponse, r any, message string) {
	resp.Success = false
	resp.Task = nil
	resp.Error = thPanicStr(r)
	resp.Message = thPanicStr(r)
	_ = message
	resp.Timestamp = thNow()
}

// thStr is Python str() for response messages.
func thStr(v any) string { return value_objects.PyStr(v) }

// CreateTask mirrors TaskCrudHandler.create_task.
func (h *TaskCrudHandler) CreateTask(ctx context.Context, request *taskdto.CreateTaskRequest, userID string) (resp *types.TaskResponse) {
	resp = &types.TaskResponse{Success: false, Timestamp: thNow()}
	defer func() {
		if r := recover(); r != nil {
			thPanicked(resp, r, "Failed to create task")
		}
	}()
	raw, err := h.facadeService.GetTaskFacade(nil, &request.GitBranchID, &userID)
	if err != nil {
		return thCreateFailure(err)
	}
	facade, ok := raw.(TaskHandlerFacade)
	if !ok {
		return thCreateFailureMsg("Failed to create task")
	}
	result := facade.CreateTask(ctx, request)
	if thSuccess(result) {
		task := thOmGet(result, "task")
		dto, derr := thTaskValue(task, false)
		if derr != nil {
			return thCreateFailure(derr)
		}
		return &types.TaskResponse{
			Success:   true,
			Task:      dto,
			Message:   thMsg("Task created successfully"),
			Timestamp: thNow(),
		}
	}
	errorMsg := thErrorMsg(result, "Failed to create task")
	return &types.TaskResponse{
		Success:   false,
		Task:      nil,
		Error:     errorMsg,
		Message:   errorMsg,
		Timestamp: thNow(),
	}
}

// GetTask mirrors TaskCrudHandler.get_task.
func (h *TaskCrudHandler) GetTask(ctx context.Context, taskID, userID string) (resp *types.TaskResponse) {
	resp = &types.TaskResponse{Success: false, Timestamp: thNow()}
	defer func() {
		if r := recover(); r != nil {
			thPanicked(resp, r, "Failed to get task")
		}
	}()
	raw, err := h.facadeService.GetTaskFacade(nil, nil, &userID)
	if err != nil {
		return thGetFailure(err)
	}
	facade, ok := raw.(TaskHandlerFacade)
	if !ok {
		return thGetFailureMsg("Failed to get task")
	}
	result := facade.GetTask(ctx, taskID)
	if !thSuccess(result) {
		errorMsg := thErrorMsg(result, "Task not found")
		return &types.TaskResponse{Success: false, Task: nil, Error: errorMsg, Message: errorMsg, Timestamp: thNow()}
	}
	task := thOmGet(result, "task")
	if task == nil {
		return &types.TaskResponse{Success: false, Task: nil, Error: thMsg("Task not found"), Message: thMsg("Task not found or access denied"), Timestamp: thNow()}
	}
	dto, derr := thTaskValue(task, false)
	if derr != nil {
		return thGetFailure(derr)
	}
	return &types.TaskResponse{Success: true, Task: dto, Timestamp: thNow()}
}

// UpdateTask mirrors TaskCrudHandler.update_task.
func (h *TaskCrudHandler) UpdateTask(ctx context.Context, taskID string, request *taskdto.UpdateTaskRequest, userID string) (resp *types.TaskResponse) {
	resp = &types.TaskResponse{Success: false, Timestamp: thNow()}
	defer func() {
		if r := recover(); r != nil {
			thPanicked(resp, r, "Failed to update task")
		}
	}()
	raw, err := h.facadeService.GetTaskFacade(nil, nil, &userID)
	if err != nil {
		return thUpdateFailure(err)
	}
	facade, ok := raw.(TaskHandlerFacade)
	if !ok {
		return thUpdateFailureMsg("Failed to update task")
	}
	request.TaskID = taskID
	result := facade.UpdateTask(ctx, request)
	if thSuccess(result) {
		task := thOmGet(result, "task")
		dto, derr := thTaskValue(task, false)
		if derr != nil {
			return thUpdateFailure(derr)
		}
		return &types.TaskResponse{Success: true, Task: dto, Message: thMsg("Task updated successfully"), Timestamp: thNow()}
	}
	errorMsg := thErrorMsg(result, "Failed to update task")
	return &types.TaskResponse{Success: false, Task: nil, Error: errorMsg, Message: errorMsg, Timestamp: thNow()}
}

// DeleteTask mirrors TaskCrudHandler.delete_task.
func (h *TaskCrudHandler) DeleteTask(ctx context.Context, taskID, userID string) (resp *types.DeleteResponse) {
	resp = &types.DeleteResponse{Success: false, Deleted: boolPtr(false), Timestamp: thNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Deleted = boolPtr(false)
			resp.Error = thPanicStr(r)
			resp.Message = thPanicStr(r)
			resp.Timestamp = thNow()
		}
	}()
	raw, err := h.facadeService.GetTaskFacade(nil, nil, &userID)
	if err != nil {
		return thDeleteFailure(err)
	}
	facade, ok := raw.(TaskHandlerFacade)
	if !ok {
		return thDeleteFailureMsg("Failed to delete task")
	}
	result := facade.DeleteTask(ctx, taskID, userID)
	if thSuccess(result) {
		return &types.DeleteResponse{Success: true, Deleted: boolPtr(true), ID: &taskID, Message: thMsg("Task deleted successfully"), Timestamp: thNow()}
	}
	errorMsg := thErrorMsg(result, "Failed to delete task")
	return &types.DeleteResponse{Success: false, Deleted: boolPtr(false), Error: errorMsg, Message: errorMsg, Timestamp: thNow()}
}

// listFailureLog is where a failed listing is reported. The retired Python logs it in TWO places - a
// warning when the facade returns a failure (crud_handler.py:332, "Task listing failed for user ...:
// <error>") and an error when the call raises (:342, with exc_info) - and the Go port logged NEITHER.
// The message that names the cause (for example "Task description cannot be empty", raised by the
// domain rule the Python and the Go entity share) therefore existed and went nowhere: a refused read
// looked exactly like an empty account, and that cost three seats an evening of falsified hypotheses.
//
// THE WIRE CONTRACT IS DELIBERATELY UNCHANGED. The retired Python catches the failure, flags it, and
// lets its route render the flag as 200 with {"success": true, "tasks": [], "count": 0}
// (task_user_routes.py:126-140 then :175-180), so the Go route discarding the same flag is parity, not
// a defect. What was missing is the diagnostic, and that is what these two lines restore.
//
// A package-level seam rather than an injected interface: tests replace the variable.
var listFailureLog *slog.Logger = slog.Default()

// listLogWarn mirrors crud_handler.py:332 for a listing that failed without raising.
func listLogWarn(userID, message string) {
	listFailureLog.Warn(fmt.Sprintf("Task listing failed for user %s: %s", userID, message))
}

// listLogError mirrors crud_handler.py:342, which logs the exception with exc_info.
func listLogError(userID string, cause any) {
	listFailureLog.Error(fmt.Sprintf("Error listing tasks for user %s: %v", userID, cause))
}

// ListTasks mirrors TaskCrudHandler.list_tasks.
func (h *TaskCrudHandler) ListTasks(ctx context.Context, request *taskdto.ListTasksRequest, userID string) (resp *types.TasksResponse) {
	resp = &types.TasksResponse{Success: false, Tasks: []*types.TaskDTO{}, Timestamp: thNow()}
	defer func() {
		if r := recover(); r != nil {
			listLogError(userID, r)
			resp.Success = false
			resp.Tasks = []*types.TaskDTO{}
			resp.Error = thPanicStr(r)
			resp.Message = thPanicStr(r)
			resp.Timestamp = thNow()
		}
	}()
	raw, err := h.facadeService.GetTaskFacade(nil, request.GitBranchID, &userID)
	if err != nil {
		listLogError(userID, err)
		return thListFailure(err)
	}
	facade, ok := raw.(TaskHandlerFacade)
	if !ok {
		listLogError(userID, "Failed to list tasks")
		return thListFailureMsg("Failed to list tasks")
	}
	result := facade.ListTasks(ctx, request, true, false)
	if thSuccess(result) {
		tasks := thAnySlice(thOmGetDefault(result, "tasks", []any{}))
		dtos := make([]*types.TaskDTO, 0, len(tasks))
		for _, t := range tasks {
			dto, derr := thTaskValue(t, false)
			if derr != nil {
				listLogError(userID, derr)
				return thListFailure(derr)
			}
			dtos = append(dtos, dto)
		}
		total := len(dtos)
		return &types.TasksResponse{Success: true, Tasks: dtos, Total: &total, Timestamp: thNow()}
	}
	errorMsg := thErrorMsg(result, "Failed to list tasks")
	// The branch the Python warns on (crud_handler.py:332): the listing failed without raising, and
	// its message is the only thing that names the cause.
	if errorMsg != nil {
		listLogWarn(userID, *errorMsg)
	} else {
		listLogWarn(userID, "Failed to list tasks")
	}
	return &types.TasksResponse{Success: false, Tasks: []*types.TaskDTO{}, Error: errorMsg, Message: errorMsg, Timestamp: thNow()}
}

// --- small shared helpers ---

func boolPtr(b bool) *bool { return &b }

func thAnySlice(v any) []any {
	switch x := v.(type) {
	case []any:
		return x
	case []*entities.OrderedMap[any]:
		out := make([]any, 0, len(x))
		for _, e := range x {
			out = append(out, e)
		}
		return out
	}
	return nil
}

func thCreateFailure(err error) *types.TaskResponse {
	return thCreateFailureMsg(err.Error())
}

func thCreateFailureMsg(msg string) *types.TaskResponse {
	if msg == "" {
		msg = "Failed to create task"
	}
	return &types.TaskResponse{Success: false, Task: nil, Error: &msg, Message: &msg, Timestamp: thNow()}
}

func thGetFailure(err error) *types.TaskResponse { return thGetFailureMsg(err.Error()) }

func thGetFailureMsg(msg string) *types.TaskResponse {
	if msg == "" {
		msg = "Failed to get task"
	}
	return &types.TaskResponse{Success: false, Task: nil, Error: &msg, Message: &msg, Timestamp: thNow()}
}

func thUpdateFailure(err error) *types.TaskResponse { return thUpdateFailureMsg(err.Error()) }

func thUpdateFailureMsg(msg string) *types.TaskResponse {
	if msg == "" {
		msg = "Failed to update task"
	}
	return &types.TaskResponse{Success: false, Task: nil, Error: &msg, Message: &msg, Timestamp: thNow()}
}

func thDeleteFailure(err error) *types.DeleteResponse { return thDeleteFailureMsg(err.Error()) }

func thDeleteFailureMsg(msg string) *types.DeleteResponse {
	if msg == "" {
		msg = "Failed to delete task"
	}
	return &types.DeleteResponse{Success: false, Deleted: boolPtr(false), Error: &msg, Message: &msg, Timestamp: thNow()}
}

func thListFailure(err error) *types.TasksResponse { return thListFailureMsg(err.Error()) }

func thListFailureMsg(msg string) *types.TasksResponse {
	if msg == "" {
		msg = "Failed to list tasks"
	}
	return &types.TasksResponse{Success: false, Tasks: []*types.TaskDTO{}, Error: &msg, Message: &msg, Timestamp: thNow()}
}
