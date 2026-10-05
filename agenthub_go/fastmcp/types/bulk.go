package types

// Bulk Operation Models (Python types/bulk.py).
// Handles bulk API operations matching frontend api.types.ts.

import "agenthub/fastmcp/task_management/domain/entities"

// BulkSummaryRequest matches the frontend BulkSummaryRequest interface.
type BulkSummaryRequest struct {
	ProjectIDs      []string
	UserID          *string
	IncludeArchived *bool
}

// NewBulkSummaryRequest applies the pydantic default includeArchived=False.
func NewBulkSummaryRequest() *BulkSummaryRequest {
	f := false
	return &BulkSummaryRequest{IncludeArchived: &f}
}

func (r *BulkSummaryRequest) ModelDump() *entities.OrderedMap[any] {
	return dtoMap(
		"projectIds", dtoStrList(r.ProjectIDs),
		"userId", dtoOpt(r.UserID),
		"includeArchived", dtoBool(r.IncludeArchived),
	)
}

// BulkSummaryMetadata matches the frontend BulkSummaryMetadata interface.
type BulkSummaryMetadata struct {
	Count       int
	QueryTimeMs float64
	FromCache   bool
}

func (m *BulkSummaryMetadata) ModelDump() *entities.OrderedMap[any] {
	return dtoMap(
		"count", m.Count,
		"queryTimeMs", m.QueryTimeMs,
		"fromCache", m.FromCache,
	)
}

// BulkSummaryResponse matches the frontend BulkSummaryResponse interface.
type BulkSummaryResponse struct {
	Success   bool
	Summaries *entities.OrderedMap[any]
	Projects  *entities.OrderedMap[any]
	Metadata  *BulkSummaryMetadata
	Timestamp string
	Message   *string
}

// NewBulkSummaryResponse applies the pydantic defaults success=True and empty
// summaries/projects dicts.
func NewBulkSummaryResponse() *BulkSummaryResponse {
	return &BulkSummaryResponse{
		Success:   true,
		Summaries: entities.NewOrderedMap[any](),
		Projects:  entities.NewOrderedMap[any](),
	}
}

func (r *BulkSummaryResponse) ModelDump() *entities.OrderedMap[any] {
	summaries := any(entities.NewOrderedMap[any]())
	if r.Summaries != nil {
		summaries = r.Summaries
	}
	projects := any(entities.NewOrderedMap[any]())
	if r.Projects != nil {
		projects = r.Projects
	}
	return dtoMap(
		"success", r.Success,
		"summaries", summaries,
		"projects", projects,
		"metadata", dtoModelOrNil(r.Metadata),
		"timestamp", r.Timestamp,
		"message", dtoOpt(r.Message),
	)
}
