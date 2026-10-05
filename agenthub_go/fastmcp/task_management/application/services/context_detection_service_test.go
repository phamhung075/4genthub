package services

import (
	"context"
	"errors"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

type zpADetectProjectRepo struct {
	repositories.ProjectRepository
	projects map[string]*entities.Project
	err      error
}

func (r *zpADetectProjectRepo) FindByID(ctx context.Context, projectID string) (*entities.Project, error) {
	if r.err != nil {
		return nil, r.err
	}
	return r.projects[projectID], nil
}

type zpADetectGitRepo struct {
	repositories.GitBranchRepository
	branches map[string]*entities.GitBranch
	err      error
}

func (r *zpADetectGitRepo) FindByID(ctx context.Context, branchID string, projectID *string) (*entities.GitBranch, error) {
	if r.err != nil {
		return nil, r.err
	}
	return r.branches[branchID], nil
}

type zpADetectTaskRepo struct {
	repositories.TaskRepository
	tasks map[string]*entities.Task
	err   error
}

func (r *zpADetectTaskRepo) FindByID(ctx context.Context, taskID value_objects.TaskId) (*entities.Task, error) {
	if r.err != nil {
		return nil, r.err
	}
	return r.tasks[taskID.String()], nil
}

func zpADetectMustTaskID(t *testing.T, value string) value_objects.TaskId {
	t.Helper()
	id, err := value_objects.NewTaskId(value)
	if err != nil {
		t.Fatalf("NewTaskId(%q) failed: %v", value, err)
	}
	return id
}

func TestContextDetectionService_DetectIDType_Empty(t *testing.T) {
	svc := NewContextDetectionService(&zpADetectProjectRepo{}, &zpADetectGitRepo{}, &zpADetectTaskRepo{})
	idType, projectID := svc.DetectIDType(context.Background(), "")
	if idType != "unknown" || projectID != nil {
		t.Fatalf("= (%q, %v), want (unknown, nil)", idType, projectID)
	}
}

func TestContextDetectionService_DetectIDType_Project(t *testing.T) {
	projectRepo := &zpADetectProjectRepo{projects: map[string]*entities.Project{"proj-1": {Name: "p"}}}
	svc := NewContextDetectionService(projectRepo, &zpADetectGitRepo{}, &zpADetectTaskRepo{})
	idType, projectID := svc.DetectIDType(context.Background(), "proj-1")
	if idType != "project" || projectID == nil || *projectID != "proj-1" {
		t.Fatalf("= (%q, %v), want (project, proj-1)", idType, projectID)
	}
}

func TestContextDetectionService_DetectIDType_GitBranch(t *testing.T) {
	projectRepo := &zpADetectProjectRepo{err: errors.New("not a project")}
	gitRepo := &zpADetectGitRepo{branches: map[string]*entities.GitBranch{
		"branch-1": {ProjectID: "proj-9"},
	}}
	svc := NewContextDetectionService(projectRepo, gitRepo, &zpADetectTaskRepo{})
	idType, projectID := svc.DetectIDType(context.Background(), "branch-1")
	if idType != "git_branch" || projectID == nil || *projectID != "proj-9" {
		t.Fatalf("= (%q, %v), want (git_branch, proj-9)", idType, projectID)
	}
}

func TestContextDetectionService_DetectIDType_Task(t *testing.T) {
	taskID := zpADetectMustTaskID(t, "task-1")
	branchID := "branch-1"
	taskRepo := &zpADetectTaskRepo{tasks: map[string]*entities.Task{
		taskID.String(): {GitBranchID: &branchID},
	}}
	gitRepo := &zpADetectGitRepo{branches: map[string]*entities.GitBranch{
		"branch-1": {ProjectID: "proj-9"},
	}}
	svc := NewContextDetectionService(&zpADetectProjectRepo{}, gitRepo, taskRepo)
	idType, projectID := svc.DetectIDType(context.Background(), "task-1")
	if idType != "task" || projectID == nil || *projectID != "proj-9" {
		t.Fatalf("= (%q, %v), want (task, proj-9)", idType, projectID)
	}
}

func TestContextDetectionService_DetectIDType_TaskBranchMissing(t *testing.T) {
	taskID := zpADetectMustTaskID(t, "task-1")
	branchID := "branch-1"
	taskRepo := &zpADetectTaskRepo{tasks: map[string]*entities.Task{
		taskID.String(): {GitBranchID: &branchID},
	}}
	svc := NewContextDetectionService(&zpADetectProjectRepo{}, &zpADetectGitRepo{}, taskRepo)
	idType, projectID := svc.DetectIDType(context.Background(), "task-1")
	if idType != "unknown" || projectID != nil {
		t.Fatalf("= (%q, %v), want (unknown, nil)", idType, projectID)
	}
}

func TestContextDetectionService_DetectIDType_Unknown(t *testing.T) {
	svc := NewContextDetectionService(&zpADetectProjectRepo{}, &zpADetectGitRepo{}, &zpADetectTaskRepo{})
	idType, projectID := svc.DetectIDType(context.Background(), "nothing-1")
	if idType != "unknown" || projectID != nil {
		t.Fatalf("= (%q, %v), want (unknown, nil)", idType, projectID)
	}
}

func TestContextDetectionService_GetContextLevelForID(t *testing.T) {
	projectRepo := &zpADetectProjectRepo{projects: map[string]*entities.Project{"proj-1": {Name: "p"}}}
	gitRepo := &zpADetectGitRepo{branches: map[string]*entities.GitBranch{"branch-1": {ProjectID: "proj-9"}}}
	svc := NewContextDetectionService(projectRepo, gitRepo, &zpADetectTaskRepo{})

	if got := svc.GetContextLevelForID(context.Background(), "proj-1"); got != "project" {
		t.Fatalf("project level = %q", got)
	}
	if got := svc.GetContextLevelForID(context.Background(), "branch-1"); got != "task" {
		t.Fatalf("git_branch level = %q", got)
	}
	if got := svc.GetContextLevelForID(context.Background(), "nothing-1"); got != "task" {
		t.Fatalf("unknown level = %q", got)
	}
}
