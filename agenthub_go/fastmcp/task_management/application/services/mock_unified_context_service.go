package services

import (
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// MockUnifiedContextService is a database-less, in-memory context service
// (Python application/services/mock_unified_context_service.py). The Python module's
// sys.path/fixture-import header has no Go meaning: this ports the inline fallback
// implementation, which uses datetime.now().isoformat() (naive local) timestamps.
type MockUnifiedContextService struct {
	// contexts maps "level:id" to the stored context dict, preserving insertion order.
	contexts *entities.OrderedMap[*entities.OrderedMap[any]]
}

// NewMockUnifiedContextService mirrors __init__ (empty in-memory storage).
func NewMockUnifiedContextService() *MockUnifiedContextService {
	return &MockUnifiedContextService{contexts: entities.NewOrderedMap[*entities.OrderedMap[any]]()}
}

// GetContext returns the stored context or nil when absent.
func (s *MockUnifiedContextService) GetContext(level string, contextID string, includeInherited bool, forceRefresh bool) *entities.OrderedMap[any] {
	context, _ := s.contexts.Get(level + ":" + contextID)
	return context
}

// CreateContext stores and returns a new context with the exact key order
// id, level, data, parent_id, created_at, updated_at.
func (s *MockUnifiedContextService) CreateContext(level string, contextID string, data *entities.OrderedMap[any], parentID *string) *entities.OrderedMap[any] {
	key := level + ":" + contextID
	context := entities.NewOrderedMap[any]()
	context.Set("id", contextID)
	context.Set("level", level)
	context.Set("data", data)
	context.Set("parent_id", zpAMockOptionalString(parentID))
	context.Set("created_at", value_objects.IsoFormatNaive(time.Now()))
	context.Set("updated_at", value_objects.IsoFormatNaive(time.Now()))
	s.contexts.Set(key, context)
	return context
}

// UpdateContext updates (merge or replace) the stored context, auto-creating it when
// it does not exist.
func (s *MockUnifiedContextService) UpdateContext(level string, contextID string, data *entities.OrderedMap[any], merge bool, propagateChanges bool) *entities.OrderedMap[any] {
	key := level + ":" + contextID
	context, ok := s.contexts.Get(key)
	if !ok {
		return s.CreateContext(level, contextID, data, nil)
	}

	existingData, hasExistingData := context.Get("data")
	if merge && hasExistingData && value_objects.PyTruthy(existingData) {
		zpAMockMergeOrderedMap(existingData, data)
	} else {
		context.Set("data", data)
	}

	context.Set("updated_at", value_objects.IsoFormatNaive(time.Now()))
	return context
}

// DeleteContext deletes a context, reporting whether it existed.
func (s *MockUnifiedContextService) DeleteContext(level string, contextID string) bool {
	key := level + ":" + contextID
	if s.contexts.Has(key) {
		s.contexts.Delete(key)
		return true
	}
	return false
}

// ResolveContext returns the stored context or a fresh default context with key order
// id, level, data, resolved, created_at.
func (s *MockUnifiedContextService) ResolveContext(level string, contextID string, includeInherited bool, forceRefresh bool) *entities.OrderedMap[any] {
	if context, ok := s.contexts.Get(level + ":" + contextID); ok {
		return context
	}

	context := entities.NewOrderedMap[any]()
	context.Set("id", contextID)
	context.Set("level", level)
	context.Set("data", entities.NewOrderedMap[any]())
	context.Set("resolved", true)
	context.Set("created_at", value_objects.IsoFormatNaive(time.Now()))
	return context
}

// DelegateContext records a delegation (no-op storage) and returns
// success, delegated_to, delegation_reason.
func (s *MockUnifiedContextService) DelegateContext(level string, contextID string, delegateTo string, delegateData *entities.OrderedMap[any], delegationReason *string) *entities.OrderedMap[any] {
	context := entities.NewOrderedMap[any]()
	context.Set("success", true)
	context.Set("delegated_to", delegateTo)
	context.Set("delegation_reason", zpAMockOptionalString(delegationReason))
	return context
}

// ListContexts lists stored contexts in insertion order, optionally filtered by level.
func (s *MockUnifiedContextService) ListContexts(level *string, filters *entities.OrderedMap[any]) []*entities.OrderedMap[any] {
	results := []*entities.OrderedMap[any]{}
	prefix := ""
	if level != nil {
		prefix = *level + ":"
	}
	for _, key := range s.contexts.Keys() {
		if level != nil && *level != "" && !strings.HasPrefix(key, prefix) {
			continue
		}
		context, _ := s.contexts.Get(key)
		results = append(results, context)
	}
	return results
}

// AddInsight appends an insight to the context's data.insights, auto-creating the
// context when needed.
func (s *MockUnifiedContextService) AddInsight(level string, contextID string, insight *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	key := level + ":" + contextID
	context, ok := s.contexts.Get(key)
	if !ok {
		seed := entities.NewOrderedMap[any]()
		seed.Set("insights", []any{})
		context = s.CreateContext(level, contextID, seed, nil)
	}

	data := zpAMockDataMap(context)
	if !data.Has("insights") {
		data.Set("insights", []any{})
	}
	insights, _ := data.Get("insights")
	list, _ := insights.([]any)
	list = append(list, insight)
	data.Set("insights", list)

	context.Set("updated_at", value_objects.IsoFormatNaive(time.Now()))
	return context
}

// AddProgress appends a progress update to the context's data.progress, auto-creating
// the context when needed.
func (s *MockUnifiedContextService) AddProgress(level string, contextID string, progress *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	key := level + ":" + contextID
	context, ok := s.contexts.Get(key)
	if !ok {
		seed := entities.NewOrderedMap[any]()
		seed.Set("progress", []any{})
		context = s.CreateContext(level, contextID, seed, nil)
	}

	data := zpAMockDataMap(context)
	if !data.Has("progress") {
		data.Set("progress", []any{})
	}
	progressUpdates, _ := data.Get("progress")
	list, _ := progressUpdates.([]any)
	list = append(list, progress)
	data.Set("progress", list)

	context.Set("updated_at", value_objects.IsoFormatNaive(time.Now()))
	return context
}

// ValidateHierarchy always reports a valid mock hierarchy.
func (s *MockUnifiedContextService) ValidateHierarchy(taskID string, branchID *string, projectID *string) *entities.OrderedMap[any] {
	context := entities.NewOrderedMap[any]()
	context.Set("valid", true)
	context.Set("message", "Mock hierarchy validation - always valid")
	return context
}

// GetHierarchyChain returns the single stored context for the key, or an empty list.
func (s *MockUnifiedContextService) GetHierarchyChain(level string, contextID string) []*entities.OrderedMap[any] {
	if context, ok := s.contexts.Get(level + ":" + contextID); ok {
		return []*entities.OrderedMap[any]{context}
	}
	return []*entities.OrderedMap[any]{}
}

// zpAMockOptionalString converts an optional string parameter to the Python value
// (nil pointer -> None, otherwise the string).
func zpAMockOptionalString(value *string) any {
	if value == nil {
		return nil
	}
	return *value
}

// zpAMockMergeOrderedMap mirrors dict.update: copies data's items into the stored map.
func zpAMockMergeOrderedMap(existing any, data *entities.OrderedMap[any]) {
	if data == nil {
		return
	}
	destination, ok := existing.(*entities.OrderedMap[any])
	if !ok || destination == nil {
		return
	}
	for _, key := range data.Keys() {
		value, _ := data.Get(key)
		destination.Set(key, value)
	}
}

// zpAMockDataMap returns the context's "data" ordered map, installing an empty one if
// the stored value is missing or not a dict.
func zpAMockDataMap(context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	data, _ := context.Get("data")
	if dataMap, ok := data.(*entities.OrderedMap[any]); ok && dataMap != nil {
		return dataMap
	}
	dataMap := entities.NewOrderedMap[any]()
	context.Set("data", dataMap)
	return dataMap
}
