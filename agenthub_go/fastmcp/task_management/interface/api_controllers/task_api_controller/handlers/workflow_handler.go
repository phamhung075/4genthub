package handlers

import (
	"context"

	"agenthub/fastmcp/types"
)

// TaskWorkflowHandler mirrors workflow_handler.TaskWorkflowHandler.
type TaskWorkflowHandler struct {
	facadeService TaskFacadeService
}

// NewTaskWorkflowHandler builds the handler.
func NewTaskWorkflowHandler(facadeService TaskFacadeService) *TaskWorkflowHandler {
	return &TaskWorkflowHandler{facadeService: facadeService}
}

// CompleteTask mirrors TaskWorkflowHandler.complete_task.
func (h *TaskWorkflowHandler) CompleteTask(ctx context.Context, taskID, completionSummary string, testingNotes *string, userID string) (resp *types.TaskResponse) {
	resp = &types.TaskResponse{Success: false, Timestamp: thNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Task = nil
			resp.Error = thPanicStr(r)
			resp.Message = thMsg("Failed to complete task")
			resp.Timestamp = thNow()
		}
	}()
	raw, err := h.facadeService.GetTaskFacade(strPtr("default_project"), nil, &userID)
	if err != nil {
		return &types.TaskResponse{Success: false, Task: nil, Error: thMsg(err.Error()), Message: thMsg("Failed to complete task"), Timestamp: thNow()}
	}
	facade, ok := raw.(TaskHandlerFacade)
	if !ok {
		return &types.TaskResponse{Success: false, Task: nil, Error: thMsg("Failed to complete task"), Message: thMsg("Failed to complete task"), Timestamp: thNow()}
	}
	result := facade.CompleteTask(ctx, taskID, completionSummary, testingNotes, userID)
	if thSuccess(result) {
		task := thOmGet(result, "task")
		dto, derr := thTaskValue(task, false)
		if derr != nil {
			return &types.TaskResponse{Success: false, Task: nil, Error: thMsg(derr.Error()), Message: thMsg("Failed to complete task"), Timestamp: thNow()}
		}
		return &types.TaskResponse{Success: true, Task: dto, Message: thMsg("Task completed successfully"), Timestamp: thNow()}
	}
	errorMsg := thErrorMsg(result, "Failed to complete task")
	return &types.TaskResponse{Success: false, Task: nil, Error: errorMsg, Message: errorMsg, Timestamp: thNow()}
}
