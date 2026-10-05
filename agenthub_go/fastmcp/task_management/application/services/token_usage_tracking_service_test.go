package services

import (
	"context"
	"errors"
	"testing"
)

type zpATokenUsageFakeRepo struct {
	calls   []string
	success bool
	err     error
}

func (r *zpATokenUsageFakeRepo) UpdateTokenUsage(ctx context.Context, tokenID string, operation string) (bool, error) {
	r.calls = append(r.calls, tokenID+":"+operation)
	if r.err != nil {
		return false, r.err
	}
	return r.success, nil
}

func TestTokenUsageTrackingService_TrackTokenOperation_NoToken(t *testing.T) {
	repo := &zpATokenUsageFakeRepo{success: true}
	if TrackTokenOperation(context.Background(), nil, "task_create", repo) {
		t.Fatalf("nil token = true, want false")
	}
	empty := ""
	if TrackTokenOperation(context.Background(), &empty, "task_create", repo) {
		t.Fatalf("empty token = true, want false")
	}
	if len(repo.calls) != 0 {
		t.Fatalf("calls = %v, want none", repo.calls)
	}
}

func TestTokenUsageTrackingService_TrackTokenOperation_Delegates(t *testing.T) {
	repo := &zpATokenUsageFakeRepo{success: true}
	tokenID := "tok-1"
	if !TrackTokenOperation(context.Background(), &tokenID, "task_create", repo) {
		t.Fatalf("= false, want true")
	}
	if len(repo.calls) != 1 || repo.calls[0] != "tok-1:task_create" {
		t.Fatalf("calls = %v", repo.calls)
	}
}

func TestTokenUsageTrackingService_TrackTokenOperation_ReturnsFalse(t *testing.T) {
	tokenID := "tok-1"
	repo := &zpATokenUsageFakeRepo{success: false}
	if TrackTokenOperation(context.Background(), &tokenID, "task_create", repo) {
		t.Fatalf("= true, want false")
	}
}

func TestTokenUsageTrackingService_TrackTokenOperation_RecoversFromError(t *testing.T) {
	tokenID := "tok-1"
	repo := &zpATokenUsageFakeRepo{success: true, err: errors.New("boom")}
	if TrackTokenOperation(context.Background(), &tokenID, "task_create", repo) {
		t.Fatalf("= true, want false")
	}
}

func TestTokenUsageTrackingService_GetOperationName(t *testing.T) {
	if got := GetOperationName("task", "create"); got != "task_create" {
		t.Fatalf("= %q, want task_create", got)
	}
	if got := GetOperationName("TASK", "Create"); got != "task_create" {
		t.Fatalf("= %q, want task_create", got)
	}
}

func TestTokenUsageTrackingService_OperationNames(t *testing.T) {
	cases := []struct {
		name OperationNames
		want string
	}{
		{OperationNamesTaskCreate, "task_create"},
		{OperationNamesTaskUpdate, "task_update"},
		{OperationNamesTaskDelete, "task_delete"},
		{OperationNamesTaskComplete, "task_complete"},
		{OperationNamesTaskList, "task_list"},
		{OperationNamesTaskGet, "task_get"},
		{OperationNamesSubtaskCreate, "subtask_create"},
		{OperationNamesSubtaskUpdate, "subtask_update"},
		{OperationNamesSubtaskDelete, "subtask_delete"},
		{OperationNamesSubtaskComplete, "subtask_complete"},
		{OperationNamesSubtaskList, "subtask_list"},
		{OperationNamesSubtaskGet, "subtask_get"},
		{OperationNamesProjectCreate, "project_create"},
		{OperationNamesProjectUpdate, "project_update"},
		{OperationNamesProjectDelete, "project_delete"},
		{OperationNamesProjectGet, "project_get"},
		{OperationNamesProjectList, "project_list"},
		{OperationNamesBranchCreate, "branch_create"},
		{OperationNamesBranchUpdate, "branch_update"},
		{OperationNamesBranchDelete, "branch_delete"},
		{OperationNamesBranchGet, "branch_get"},
		{OperationNamesBranchList, "branch_list"},
		{OperationNamesAgentRegister, "agent_register"},
		{OperationNamesAgentUpdate, "agent_update"},
		{OperationNamesAgentDelete, "agent_delete"},
		{OperationNamesAgentAssign, "agent_assign"},
		{OperationNamesAgentUnassign, "agent_unassign"},
		{OperationNamesAgentCall, "agent_call"},
		{OperationNamesContextCreate, "context_create"},
		{OperationNamesContextUpdate, "context_update"},
		{OperationNamesContextDelete, "context_delete"},
		{OperationNamesContextGet, "context_get"},
	}
	for _, c := range cases {
		if string(c.name) != c.want {
			t.Fatalf("%v = %q, want %q", c.name, string(c.name), c.want)
		}
	}
}
