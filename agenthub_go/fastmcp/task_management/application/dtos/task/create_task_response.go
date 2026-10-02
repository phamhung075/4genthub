package task

// CreateTaskResponse is the response DTO for create task operations.
type CreateTaskResponse struct {
	Success bool
	Task    *TaskResponse
	Message string
}

// NewCreateTaskResponseSuccess mirrors success_response (default message
// "Task created successfully" when nil).
func NewCreateTaskResponseSuccess(task *TaskResponse, message *string) *CreateTaskResponse {
	msg := "Task created successfully"
	if message != nil {
		msg = *message
	}
	return &CreateTaskResponse{Success: true, Task: task, Message: msg}
}

// NewCreateTaskResponseError mirrors error_response.
func NewCreateTaskResponseError(message string, task *TaskResponse) *CreateTaskResponse {
	return &CreateTaskResponse{Success: false, Task: task, Message: message}
}
