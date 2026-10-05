package api_controllers

import (
	"context"
	"errors"
	"testing"

	projectdto "agenthub/fastmcp/task_management/application/dtos/project"
	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/domain/entities"
)

// --- fake providers (errors only; the Python paths under test are the
// exception branches, which produce the fixed response shapes asserted below).

type fakeProjectProvider struct{ err error }

func (f fakeProjectProvider) CreateProjectFacade(userID *string) (*facades.ProjectApplicationFacade, error) {
	return nil, f.err
}

type fakeContextProvider struct{ err error }

func (f fakeContextProvider) GetContextFacade(userID, projectID, gitBranchID *string) (*facades.UnifiedContextFacade, error) {
	return nil, f.err
}

func TestProjectCreateProjectFailure(t *testing.T) {
	c := NewProjectAPIController(fakeProjectProvider{err: errors.New("boom")})
	req := &projectdto.CreateProjectRequest{Name: "P"}
	resp := c.CreateProject(context.Background(), req, "user-1", nil)
	if resp.Success {
		t.Fatalf("success = true, want false")
	}
	if resp.Project != nil {
		t.Fatalf("project = %v, want nil", resp.Project)
	}
	if resp.Error == nil || *resp.Error != "boom" {
		t.Fatalf("error = %v, want boom", resp.Error)
	}
	if resp.Message == nil || *resp.Message != "Failed to create project" {
		t.Fatalf("message = %v", resp.Message)
	}
	if resp.Timestamp == nil {
		t.Fatalf("timestamp = nil, want isoformat")
	}
}

func TestContextGetContextFailure(t *testing.T) {
	c := NewContextAPIController(fakeContextProvider{err: errors.New("nope")})
	resp := c.GetContext(context.Background(), "project", "ctx-1", true, "user-1", nil)
	if resp.Success {
		t.Fatalf("success = true, want false")
	}
	if resp.Context != nil {
		t.Fatalf("context = %v, want nil", resp.Context)
	}
	if resp.Error == nil || *resp.Error != "nope" {
		t.Fatalf("error = %v, want nope", resp.Error)
	}
	if resp.Message == nil || *resp.Message != "Failed to get context" {
		t.Fatalf("message = %v", resp.Message)
	}
	// Python leaves timestamp unset for ContextResponse.
	if resp.Timestamp != nil {
		t.Fatalf("timestamp = %v, want nil", resp.Timestamp)
	}
}

// TestBranchDTOFromDict mirrors the inline BranchDTO(...) construction in
// get_branches_with_task_counts for a representative branch dict.
func TestBranchDTOFromDict(t *testing.T) {
	data := entities.NewOrderedMap[any]()
	data.Set("id", "b1")
	data.Set("project_id", "p1")
	data.Set("name", "Main")
	data.Set("git_branch_name", "main")
	data.Set("description", "desc")
	data.Set("status", "active")
	data.Set("is_active", true)
	data.Set("created_at", "2024-01-01T00:00:00")
	data.Set("updated_at", "2024-01-02T00:00:00")
	data.Set("total_tasks", 5)
	data.Set("completed_tasks", 2)

	totalTasks, _ := data.Get("total_tasks")
	dto := brACBranchDTOFromDict(data, totalTasks)
	if dto.ID != "b1" || dto.ProjectID != "p1" || dto.Name != "Main" || dto.GitBranchName != "main" {
		t.Fatalf("identity fields = %+v", dto)
	}
	if dto.Description == nil || *dto.Description != "desc" {
		t.Fatalf("description = %v", dto.Description)
	}
	if dto.Status == nil || *dto.Status != "active" {
		t.Fatalf("status = %v", dto.Status)
	}
	if dto.IsActive == nil || !*dto.IsActive {
		t.Fatalf("is_active = %v", dto.IsActive)
	}
	if dto.TaskCount == nil || *dto.TaskCount != 5 {
		t.Fatalf("task_count = %v, want 5", dto.TaskCount)
	}
	if dto.CompletedTasks == nil || *dto.CompletedTasks != 2 {
		t.Fatalf("completed_tasks = %v, want 2", dto.CompletedTasks)
	}
}

// TestBranchPerformanceMetricsShape checks the fixed metrics dict key order and
// values from the Python literal.
func TestBranchPerformanceMetricsShape(t *testing.T) {
	c := NewBranchAPIController(nil, nil)
	resp := c.GetBranchPerformanceMetrics(context.Background(), "user-1", nil)
	if !resp.Success {
		t.Fatalf("success = false")
	}
	m, ok := resp.Data.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("data type = %T", resp.Data)
	}
	keys := m.Keys()
	want := []string{"optimization_status", "query_strategy", "expected_performance", "cache_status", "recommendations"}
	if len(keys) != len(want) {
		t.Fatalf("keys = %v", keys)
	}
	for i := range want {
		if keys[i] != want[i] {
			t.Fatalf("key[%d] = %q, want %q", i, keys[i], want[i])
		}
	}
	v, _ := m.Get("optimization_status")
	if v != "enabled" {
		t.Fatalf("optimization_status = %v", v)
	}
	recs, _ := m.Get("recommendations")
	if len(recs.([]any)) != 4 {
		t.Fatalf("recommendations len = %d", len(recs.([]any)))
	}
}
