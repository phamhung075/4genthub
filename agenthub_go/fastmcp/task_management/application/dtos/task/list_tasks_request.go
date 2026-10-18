package task

// ListTasksRequest is the request DTO for listing tasks. Limit/Offset page the set and
// SortBy/SortOrder order it; the repository rejects an ordering it cannot serve.
type ListTasksRequest struct {
	GitBranchID *string
	Status      *string
	Priority    *string
	Assignees   []string
	Labels      []string
	Limit       *int
	Offset      *int
	SortBy      *string
	SortOrder   *string
}
