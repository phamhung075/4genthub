package services

import (
	"context"
	"errors"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

type gbWrapFakeService struct {
	createProjectID   string
	createName        string
	createDescription string
	updateID          string
	updateName        *string
	updateDescription *string
	listProjectID     string
	createdResult     *entities.OrderedMap[any]
}

func (f *gbWrapFakeService) CreateGitBranch(ctx context.Context, projectID, gitBranchName, gitBranchDescription string) (*entities.OrderedMap[any], error) {
	f.createProjectID = projectID
	f.createName = gitBranchName
	f.createDescription = gitBranchDescription
	return f.createdResult, nil
}

func (f *gbWrapFakeService) GetGitBranchByID(ctx context.Context, gitBranchID string) (*entities.OrderedMap[any], error) {
	return nil, nil
}

func (f *gbWrapFakeService) ListGitBranchs(ctx context.Context, projectID string) (*entities.OrderedMap[any], error) {
	f.listProjectID = projectID
	return nil, nil
}

func (f *gbWrapFakeService) UpdateGitBranch(ctx context.Context, gitBranchID string, gitBranchName, gitBranchDescription *string) (*entities.OrderedMap[any], error) {
	f.updateID = gitBranchID
	f.updateName = gitBranchName
	f.updateDescription = gitBranchDescription
	return nil, nil
}

func (f *gbWrapFakeService) DeleteGitBranch(ctx context.Context, projectID, gitBranchID string) (*entities.OrderedMap[any], error) {
	return nil, nil
}

func (f *gbWrapFakeService) AssignAgentToBranch(ctx context.Context, projectID, agentID, gitBranchName string) (*entities.OrderedMap[any], error) {
	return nil, nil
}

func (f *gbWrapFakeService) UnassignAgentFromBranch(ctx context.Context, projectID, agentID, gitBranchName string) (*entities.OrderedMap[any], error) {
	return nil, nil
}

func (f *gbWrapFakeService) GetBranchStatistics(ctx context.Context, projectID, gitBranchID string) (*entities.OrderedMap[any], error) {
	return nil, nil
}

func (f *gbWrapFakeService) ArchiveBranch(ctx context.Context, projectID, gitBranchID string) (*entities.OrderedMap[any], error) {
	return nil, nil
}

func (f *gbWrapFakeService) RestoreBranch(ctx context.Context, projectID, gitBranchID string) (*entities.OrderedMap[any], error) {
	return nil, nil
}

var _ gbWrapGitBranchService = (*gbWrapFakeService)(nil)

func TestGbWrapCreateGitBranchDelegates(t *testing.T) {
	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	fake := &gbWrapFakeService{createdResult: result}
	wrapper, err := NewGitBranchServiceWrapper(fake)
	if err != nil {
		t.Fatalf("NewGitBranchServiceWrapper error: %v", err)
	}

	got, err := wrapper.CreateGitBranch(context.Background(), "proj", "branch", "")
	if err != nil {
		t.Fatalf("CreateGitBranch error: %v", err)
	}
	if got != result {
		t.Fatalf("CreateGitBranch returned %v, want the wrapped result", got)
	}
	if fake.createProjectID != "proj" || fake.createName != "branch" || fake.createDescription != "" {
		t.Fatalf("delegated args = (%q, %q, %q)", fake.createProjectID, fake.createName, fake.createDescription)
	}
}

func TestGbWrapUpdateGitBranchPassesOptionalPointers(t *testing.T) {
	fake := &gbWrapFakeService{}
	wrapper, err := NewGitBranchServiceWrapper(fake)
	if err != nil {
		t.Fatalf("NewGitBranchServiceWrapper error: %v", err)
	}
	name := "new-name"
	if _, err := wrapper.UpdateGitBranch(context.Background(), "b1", &name, nil); err != nil {
		t.Fatalf("UpdateGitBranch error: %v", err)
	}
	if fake.updateID != "b1" {
		t.Fatalf("update id = %q, want b1", fake.updateID)
	}
	if fake.updateName == nil || *fake.updateName != "new-name" {
		t.Fatalf("update name = %v, want new-name", fake.updateName)
	}
	if fake.updateDescription != nil {
		t.Fatalf("update description = %v, want nil", fake.updateDescription)
	}
}

func TestGbWrapListGitBranchsDelegates(t *testing.T) {
	fake := &gbWrapFakeService{}
	wrapper, err := NewGitBranchServiceWrapper(fake)
	if err != nil {
		t.Fatalf("NewGitBranchServiceWrapper error: %v", err)
	}
	if _, err := wrapper.ListGitBranchs(context.Background(), "proj"); err != nil {
		t.Fatalf("ListGitBranchs error: %v", err)
	}
	if fake.listProjectID != "proj" {
		t.Fatalf("list project id = %q, want proj", fake.listProjectID)
	}
}

func TestGbWrapNilServiceRaisesValueError(t *testing.T) {
	_, err := NewGitBranchServiceWrapper(nil)
	var valueErr *value_objects.ValueError
	if !errors.As(err, &valueErr) {
		t.Fatalf("error = %v, want *value_objects.ValueError", err)
	}
}
