package task

// UpdateTaskRequest is the request DTO for updating a task. The Python model is
// a pydantic BaseModel with extra="allow"; unknown fields are not representable
// on a Go struct.
type UpdateTaskRequest struct {
	TaskID             any
	Title              *string
	Description        *string
	Status             *string
	Priority           *string
	Details            *string
	EstimatedEffort    *string
	Assignees          []string
	Labels             []string
	DueDate            *string
	ContextID          *string
	CompletionSummary  *string
	TestingNotes       *string
	CompletedAt        *string
	ProgressPercentage *int
}
