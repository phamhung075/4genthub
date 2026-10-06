package routes

import (
	"context"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	"agenthub/fastmcp/task_management/domain/entities"
)

// SubtaskController is the minimal SubtaskAPIController surface used by the
// routes (ctx first).
type SubtaskController interface {
	CreateSubtask(ctx context.Context, taskID, title string, description *string, userID string) (ControllerResult, error)
	GetSubtask(ctx context.Context, subtaskID, userID string) (ControllerResult, error)
	UpdateSubtask(ctx context.Context, subtaskID string, updateData *entities.OrderedMap[any], userID string) (ControllerResult, error)
	DeleteSubtask(ctx context.Context, subtaskID, userID string) (ControllerResult, error)
	ListSubtasks(ctx context.Context, taskID, userID string) (ControllerResult, error)
	CompleteSubtask(ctx context.Context, subtaskID string, completionSummary *string, userID string) (ControllerResult, error)
}

// CreateSubtask is create_subtask POST "".
func CreateSubtask(ctx context.Context, taskID, title string, description *string, currentUser *authdomain.User, c SubtaskController) (*entities.OrderedMap[any], error) {
	result, err := c.CreateSubtask(ctx, taskID, title, description, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, err.Error())
	}
	if !result.Success {
		return nil, httpErr(400, pyOrStr(result.Error, "Failed to create subtask"))
	}
	return result.Body, nil
}

// GetSubtask is get_subtask GET /{subtask_id}.
func GetSubtask(ctx context.Context, subtaskID string, currentUser *authdomain.User, c SubtaskController) (*entities.OrderedMap[any], error) {
	result, err := c.GetSubtask(ctx, subtaskID, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, err.Error())
	}
	if !result.Success {
		return nil, httpErr(404, pyOrStr(result.Error, "Subtask not found"))
	}
	return result.Body, nil
}

// UpdateSubtask is update_subtask PUT /{subtask_id}. update_data is built in
// Python insertion order: title, description, status, progress_percentage.
func UpdateSubtask(ctx context.Context, subtaskID string, title, description, status *string, progressPercentage *int, currentUser *authdomain.User, c SubtaskController) (*entities.OrderedMap[any], error) {
	updateData := entities.NewOrderedMap[any]()
	if title != nil {
		updateData.Set("title", *title)
	}
	if description != nil {
		updateData.Set("description", *description)
	}
	if status != nil {
		updateData.Set("status", *status)
	}
	if progressPercentage != nil {
		updateData.Set("progress_percentage", *progressPercentage)
	}
	result, err := c.UpdateSubtask(ctx, subtaskID, updateData, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, err.Error())
	}
	if !result.Success {
		return nil, httpErr(400, pyOrStr(result.Error, "Failed to update subtask"))
	}
	return result.Body, nil
}

// DeleteSubtask is delete_subtask DELETE /{subtask_id}.
func DeleteSubtask(ctx context.Context, subtaskID string, currentUser *authdomain.User, c SubtaskController) (*entities.OrderedMap[any], error) {
	result, err := c.DeleteSubtask(ctx, subtaskID, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, err.Error())
	}
	if !result.Success {
		return nil, httpErr(400, pyOrStr(result.Error, "Failed to delete subtask"))
	}
	return result.Body, nil
}

// ListSubtasks is list_subtasks_for_task GET /task/{task_id}.
func ListSubtasks(ctx context.Context, taskID string, currentUser *authdomain.User, c SubtaskController) (*entities.OrderedMap[any], error) {
	result, err := c.ListSubtasks(ctx, taskID, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, err.Error())
	}
	if !result.Success {
		return nil, httpErr(400, pyOrStr(result.Error, "Failed to list subtasks"))
	}
	return result.Body, nil
}

// CompleteSubtask is complete_subtask POST /{subtask_id}/complete.
func CompleteSubtask(ctx context.Context, subtaskID string, completionNotes *string, currentUser *authdomain.User, c SubtaskController) (*entities.OrderedMap[any], error) {
	result, err := c.CompleteSubtask(ctx, subtaskID, completionNotes, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, err.Error())
	}
	if !result.Success {
		return nil, httpErr(400, pyOrStr(result.Error, "Failed to complete subtask"))
	}
	return result.Body, nil
}
