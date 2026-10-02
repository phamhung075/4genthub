package repositories

// Mock Task Context Repository (Python repositories/mock_task_context_repository.py): an
// in-memory task-context store. Python's `session_factory=None` argument is dropped (it is
// never used) and the returned dicts keep their insertion order through entities.OrderedMap.

import (
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// MockTaskContextRepository is Python's MockTaskContextRepository.
type MockTaskContextRepository struct {
	contexts *entities.OrderedMap[*entities.OrderedMap[any]]
}

// NewMockTaskContextRepository builds an empty repository.
func NewMockTaskContextRepository() *MockTaskContextRepository {
	return &MockTaskContextRepository{contexts: entities.NewOrderedMap[*entities.OrderedMap[any]]()}
}

// GetContext returns the stored context or nil.
func (r *MockTaskContextRepository) GetContext(taskID string) *entities.OrderedMap[any] {
	v, _ := r.contexts.Get(taskID)
	return v
}

// GetByID is an alias for GetContext.
func (r *MockTaskContextRepository) GetByID(taskID string) *entities.OrderedMap[any] {
	return r.GetContext(taskID)
}

func mockTaskContextRepoData(contextData map[string]any) *entities.OrderedMap[any] {
	data := entities.NewOrderedMap[any]()
	for k, v := range contextData {
		data.Set(k, v)
	}
	return data
}

// CreateContext stores a new context (created_at/updated_at are naive local isoformat).
func (r *MockTaskContextRepository) CreateContext(taskID string, contextData map[string]any) *entities.OrderedMap[any] {
	context := entities.NewOrderedMap[any]()
	context.Set("task_id", taskID)
	context.Set("data", mockTaskContextRepoData(contextData))
	context.Set("created_at", tmvo.IsoFormatNaive(time.Now()))
	context.Set("updated_at", tmvo.IsoFormatNaive(time.Now()))
	r.contexts.Set(taskID, context)
	return context
}

// UpdateContext merges into the stored data, creating the context when absent.
func (r *MockTaskContextRepository) UpdateContext(taskID string, contextData map[string]any) *entities.OrderedMap[any] {
	if !r.contexts.Has(taskID) {
		return r.CreateContext(taskID, contextData)
	}
	context := r.GetContext(taskID)
	data, _ := context.Get("data")
	if om, ok := data.(*entities.OrderedMap[any]); ok {
		for k, v := range contextData {
			om.Set(k, v)
		}
	}
	context.Set("updated_at", tmvo.IsoFormatNaive(time.Now()))
	return context
}

// DeleteContext removes a context.
func (r *MockTaskContextRepository) DeleteContext(taskID string) bool {
	if r.contexts.Has(taskID) {
		r.contexts.Delete(taskID)
		return true
	}
	return false
}

// Exists reports whether a context is stored.
func (r *MockTaskContextRepository) Exists(taskID string) bool { return r.contexts.Has(taskID) }

// ListContexts returns every context in insertion order.
func (r *MockTaskContextRepository) ListContexts() []*entities.OrderedMap[any] {
	return r.contexts.Values()
}

// Save creates or updates a context.
func (r *MockTaskContextRepository) Save(taskID string, contextData map[string]any) *entities.OrderedMap[any] {
	if r.contexts.Has(taskID) {
		return r.UpdateContext(taskID, contextData)
	}
	return r.CreateContext(taskID, contextData)
}
