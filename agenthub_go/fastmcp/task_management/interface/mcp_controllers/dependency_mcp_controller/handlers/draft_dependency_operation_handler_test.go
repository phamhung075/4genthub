package handlers

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

type draftFakeFacade struct {
	addedID    string
	removedID  string
	lastAction string
}

func draftResponse(key string, value any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set(key, value)
	return m
}

func (f *draftFakeFacade) AddDependency(ctx context.Context, taskID string, dependencyID string) *entities.OrderedMap[any] {
	f.addedID = dependencyID
	return draftResponse("added", dependencyID)
}

func (f *draftFakeFacade) RemoveDependency(ctx context.Context, taskID string, dependencyID string) *entities.OrderedMap[any] {
	f.removedID = dependencyID
	return draftResponse("removed", dependencyID)
}

func (f *draftFakeFacade) GetDependencies(ctx context.Context, taskID string, userID *string) *entities.OrderedMap[any] {
	f.lastAction = "get"
	return draftResponse("dependencies", []any{})
}

func (f *draftFakeFacade) ClearDependencies(ctx context.Context, taskID string, userID *string) *entities.OrderedMap[any] {
	f.lastAction = "clear"
	return draftResponse("cleared", true)
}

func (f *draftFakeFacade) GetBlockingTasks(ctx context.Context, taskID string, userID *string) *entities.OrderedMap[any] {
	f.lastAction = "blocking"
	return draftResponse("blocking", []any{})
}

func TestDraftHandleOperationMissingTaskID(t *testing.T) {
	h := NewDependencyOperationHandler(&draftFakeFacade{})
	resp := h.HandleOperation(context.Background(), "get_dependencies", "", nil, "main", nil, nil)

	expectedKeys := []string{"success", "error", "error_code", "field", "expected", "hint"}
	keys := resp.Keys()
	if len(keys) != len(expectedKeys) {
		t.Fatalf("keys = %v", keys)
	}
	for i, k := range expectedKeys {
		if keys[i] != k {
			t.Fatalf("key[%d] = %q, want %q", i, keys[i], k)
		}
	}
	if v, _ := resp.Get("error"); v != "Missing required field: task_id" {
		t.Fatalf("error = %v", v)
	}
	if v, _ := resp.Get("expected"); v != "A valid task_id string" {
		t.Fatalf("expected = %v", v)
	}
}

func TestDraftHandleOperationUnknownAction(t *testing.T) {
	h := NewDependencyOperationHandler(&draftFakeFacade{})
	resp := h.HandleOperation(context.Background(), "bogus", "task-1", nil, "main", nil, nil)
	if v, _ := resp.Get("error_code"); v != "UNKNOWN_ACTION" {
		t.Fatalf("error_code = %v", v)
	}
	if v, _ := resp.Get("error"); v != "Unknown dependency action: bogus" {
		t.Fatalf("error = %v", v)
	}
}

func TestDraftHandleOperationAddDependency(t *testing.T) {
	facade := &draftFakeFacade{}
	h := NewDependencyOperationHandler(facade)
	resp := h.HandleOperation(context.Background(), "add_dependency", "task-1", nil, "main", nil, map[string]any{"dependency_id": "dep-1"})
	if facade.addedID != "dep-1" {
		t.Fatalf("addedID = %q", facade.addedID)
	}
	if v, _ := resp.Get("added"); v != "dep-1" {
		t.Fatalf("response added = %v", v)
	}
}

func TestDraftHandleOperationAddDependencyMissingID(t *testing.T) {
	h := NewDependencyOperationHandler(&draftFakeFacade{})
	resp := h.HandleOperation(context.Background(), "add_dependency", "task-1", nil, "main", nil, map[string]any{})
	if v, _ := resp.Get("field"); v != "dependency_data.dependency_id" {
		t.Fatalf("field = %v", v)
	}
	if v, _ := resp.Get("error_code"); v != "MISSING_FIELD" {
		t.Fatalf("error_code = %v", v)
	}
}
