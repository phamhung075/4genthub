package task

// NextTaskRequest is the request DTO for getting the next task.
type NextTaskRequest struct {
	GitBranchID    string
	IncludeContext bool
}
