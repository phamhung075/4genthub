package task

// SearchTasksRequest is the request DTO for searching tasks.
type SearchTasksRequest struct {
	Query       string
	GitBranchID *string
	Limit       int
}

// NewSearchTasksRequest applies the Python default limit=10.
func NewSearchTasksRequest(query string, gitBranchID *string, limit *int) *SearchTasksRequest {
	l := 10
	if limit != nil {
		l = *limit
	}
	return &SearchTasksRequest{Query: query, GitBranchID: gitBranchID, Limit: l}
}
