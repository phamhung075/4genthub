package task

// ListTasksRequest is the request DTO for listing tasks.
type ListTasksRequest struct {
	GitBranchID *string
	Status      *string
	Priority    *string
	Assignees   []string
	Labels      []string
	Limit       *int
}
