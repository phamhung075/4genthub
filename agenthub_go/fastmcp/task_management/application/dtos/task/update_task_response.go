package task

// UpdateTaskResponse is the response DTO for update task operations.
type UpdateTaskResponse struct {
	Success bool
	Task    *TaskResponse
	Message string
}

// NewUpdateTaskResponseSuccess mirrors success_response (default message
// "Task updated successfully" when nil).
func NewUpdateTaskResponseSuccess(task *TaskResponse, message *string) *UpdateTaskResponse {
	msg := "Task updated successfully"
	if message != nil {
		msg = *message
	}
	return &UpdateTaskResponse{Success: true, Task: task, Message: msg}
}

// NewUpdateTaskResponseError mirrors error_response.
func NewUpdateTaskResponseError(message string, task *TaskResponse) *UpdateTaskResponse {
	return &UpdateTaskResponse{Success: false, Task: task, Message: message}
}
