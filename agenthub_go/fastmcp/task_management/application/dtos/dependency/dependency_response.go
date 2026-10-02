package dependency

// DependencyResponse is the response DTO for dependency operations.
type DependencyResponse struct {
	Success         bool
	Message         *string
	TaskID          any
	DependsOnTaskID any
	DependencyType  *string
	Errors          []string
}
