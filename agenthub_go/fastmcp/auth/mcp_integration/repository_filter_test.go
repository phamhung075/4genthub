package mcp_integration

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"

	"agenthub/fastmcp/auth/middleware"
)

type mockRepo struct {
	tasks    map[string]map[string]any
	projects map[string]map[string]any
}

func (m *mockRepo) FindByID(ctx context.Context, id any) (any, error) {
	if t, ok := m.tasks[id.(string)]; ok {
		return t, nil
	}
	if p, ok := m.projects[id.(string)]; ok {
		return p, nil
	}
	return nil, nil
}

func (m *mockRepo) FindAll(ctx context.Context, filters map[string]any) ([]any, error) {
	var res []any
	for _, t := range m.tasks {
		res = append(res, t)
	}
	return res, nil
}

func (m *mockRepo) Save(ctx context.Context, entity any) (any, error) {
	return entity, nil
}

func (m *mockRepo) Delete(ctx context.Context, id any) (bool, error) {
	delete(m.tasks, id.(string))
	return true, nil
}

func TestUserFilteredRepository(t *testing.T) {
	repo := &mockRepo{
		tasks: map[string]map[string]any{
			"task-1": {"id": "task-1", "user_id": "user-A", "title": "Task A"},
			"task-2": {"id": "task-2", "user_id": "user-B", "title": "Task B"},
		},
		projects: map[string]map[string]any{
			"proj-1": {"id": "proj-1", "user_id": "user-A", "name": "Project A"},
		},
	}

	filteredTaskRepo := NewUserFilteredTaskRepository(repo)

	// Test without auth context
	_, err := filteredTaskRepo.FindByID(context.Background(), "task-1")
	if err == nil {
		t.Fatalf("expected error without auth context")
	}

	// Test with auth context for user-A
	uidA := "user-A"
	ctxA := middleware.WithRequestAuthContext(context.Background(), &middleware.RequestAuthContext{
		UserID:        &uidA,
		Authenticated: true,
	})

	// User A can access task-1
	task, err := filteredTaskRepo.FindByID(ctxA, "task-1")
	if err != nil || task == nil {
		t.Fatalf("expected task-1 found, got err: %v", err)
	}

	// User A cannot access task-2 (belongs to user-B)
	task2, err := filteredTaskRepo.FindByID(ctxA, "task-2")
	if err != nil || task2 != nil {
		t.Fatalf("expected task-2 not accessible to user A")
	}

	// Test factory
	created, err := CreateUserFilteredRepository("task", repo)
	if err != nil || created == nil {
		t.Fatalf("expected factory to create task repo wrapper")
	}
}

func TestMCPAuthMiddleware(t *testing.T) {
	mw := NewMCPAuthMiddleware(nil)

	handler := mw.Handler(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("ok"))
	}))

	req := httptest.NewRequest("GET", "/mcp", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
}
