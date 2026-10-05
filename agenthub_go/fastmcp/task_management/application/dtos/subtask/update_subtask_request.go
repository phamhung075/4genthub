package subtask

// UpdateSubtaskRequest is the request DTO for updating a subtask.
type UpdateSubtaskRequest struct {
	TaskID             any
	ID                 any
	Title              *string
	Description        *string
	Status             *string
	Priority           *string
	Assignees          []any
	ProgressPercentage *int
	ProgressNotes      *string
}
