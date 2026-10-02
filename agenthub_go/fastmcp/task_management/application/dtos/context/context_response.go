package context

import (
	"agenthub/fastmcp/task_management/domain/entities"
)

// ContextResponse is the response DTO for context operations.
type ContextResponse struct {
	Success bool
	Message string
	Data    *entities.OrderedMap[any]
	Error   *string
	Context *entities.TaskContext
}

// NewContextResponseSuccess mirrors ContextResponse.success_response; a nil message
// uses "Operation successful".
func NewContextResponseSuccess(context *entities.TaskContext, data *entities.OrderedMap[any], message *string) *ContextResponse {
	msg := "Operation successful"
	if message != nil {
		msg = *message
	}
	return &ContextResponse{Success: true, Message: msg, Data: data, Context: context}
}

// NewContextResponseError mirrors ContextResponse.error_response; a nil message
// uses "Operation failed".
func NewContextResponseError(err string, message *string) *ContextResponse {
	msg := "Operation failed"
	if message != nil {
		msg = *message
	}
	return &ContextResponse{Success: false, Message: msg, Error: &err}
}

// ToDict mirrors to_dict: success, message, then data/error/context only when truthy.
func (r *ContextResponse) ToDict() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", r.Success)
	m.Set("message", r.Message)
	if r.Data != nil && r.Data.Len() > 0 {
		m.Set("data", r.Data)
	}
	if r.Error != nil && *r.Error != "" {
		m.Set("error", *r.Error)
	}
	if r.Context != nil {
		m.Set("context", r.Context.ToDict(false))
	}
	return m
}

// The plain subclasses only inherit ContextResponse and add no behaviour.
type (
	CreateContextResponse   = ContextResponse
	UpdateContextResponse   = ContextResponse
	DeleteContextResponse   = ContextResponse
	UpdatePropertyResponse  = ContextResponse
	MergeContextResponse    = ContextResponse
	MergeDataResponse       = ContextResponse
	AddInsightResponse      = ContextResponse
	AddProgressResponse     = ContextResponse
	UpdateNextStepsResponse = ContextResponse
)

// ListContextsResponse is the response DTO for listing contexts.
type ListContextsResponse struct {
	ContextResponse
	Contexts []*entities.TaskContext
}

// NewListContextsResponseSuccess mirrors ListContextsResponse.success_response.
func NewListContextsResponseSuccess(contexts []*entities.TaskContext, message *string) *ListContextsResponse {
	msg := "Contexts retrieved successfully"
	if message != nil {
		msg = *message
	}
	return &ListContextsResponse{ContextResponse: ContextResponse{Success: true, Message: msg}, Contexts: contexts}
}

// ToDict mirrors to_dict: the base dict plus a "contexts" key.
func (r *ListContextsResponse) ToDict() *entities.OrderedMap[any] {
	m := r.ContextResponse.ToDict()
	contexts := make([]any, 0, len(r.Contexts))
	for _, c := range r.Contexts {
		contexts = append(contexts, c.ToDict(false))
	}
	m.Set("contexts", contexts)
	return m
}

// GetPropertyResponse is the response DTO for getting a property.
type GetPropertyResponse struct {
	ContextResponse
	Value any
}

// NewGetPropertyResponseSuccess mirrors GetPropertyResponse.success_response.
func NewGetPropertyResponseSuccess(value any, message *string) *GetPropertyResponse {
	msg := "Property retrieved successfully"
	if message != nil {
		msg = *message
	}
	return &GetPropertyResponse{ContextResponse: ContextResponse{Success: true, Message: msg}, Value: value}
}

// ToDict mirrors to_dict: the base dict plus a "value" key.
func (r *GetPropertyResponse) ToDict() *entities.OrderedMap[any] {
	m := r.ContextResponse.ToDict()
	m.Set("value", r.Value)
	return m
}
