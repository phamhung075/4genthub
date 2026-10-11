// Package context ports task_management/application/dtos/context.
package context

import (
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

// CreateContextRequest is the request DTO for creating a context.
type CreateContextRequest struct {
	TaskID          string
	Title           string
	Description     string
	Status          *string
	Priority        *string
	Assignees       []string
	Labels          []string
	EstimatedEffort *string
	DueDate         *time.Time
	Data            *entities.OrderedMap[any]
}

// UpdateContextRequest is the request DTO for updating a context.
type UpdateContextRequest struct {
	TaskID string
	Data   *entities.OrderedMap[any]
}

// GetContextRequest is the request DTO for getting a context.
type GetContextRequest struct {
	TaskID string
}

// DeleteContextRequest is the request DTO for deleting a context.
type DeleteContextRequest struct {
	TaskID string
}

// ListContextsRequest is the request DTO for listing contexts.
type ListContextsRequest struct {
	UserID    *string
	ProjectID string
}

// GetPropertyRequest is the request DTO for getting a context property.
type GetPropertyRequest struct {
	TaskID       string
	PropertyPath string
}

// UpdatePropertyRequest is the request DTO for updating a context property.
type UpdatePropertyRequest struct {
	TaskID       string
	PropertyPath string
	Value        any
}

// MergeContextRequest is the request DTO for merging data into a context.
type MergeContextRequest struct {
	TaskID string
	Data   *entities.OrderedMap[any]
}

// MergeDataRequest is an alias for MergeContextRequest.
type MergeDataRequest struct {
	TaskID string
	Data   *entities.OrderedMap[any]
}

// AddInsightRequest is the request DTO for adding an insight.
type AddInsightRequest struct {
	TaskID     string
	Agent      string
	Category   string
	Content    string
	Importance string
}

// UpdateNextStepsRequest is the request DTO for updating next steps.
type UpdateNextStepsRequest struct {
	TaskID    string
	NextSteps []string
}

// NewAddInsightRequest applies the Python default importance="medium".
func NewAddInsightRequest(r AddInsightRequest) *AddInsightRequest {
	if r.Importance == "" {
		r.Importance = "medium"
	}
	return &r
}
