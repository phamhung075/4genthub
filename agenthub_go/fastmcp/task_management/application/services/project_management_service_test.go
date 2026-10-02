package services

import (
	"context"
	"errors"
	"reflect"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

const (
	zpProjTestProjectID = "44444444-4444-4444-8444-444444444444"
	zpProjTestBranchID  = "55555555-5555-4555-8555-555555555555"
	zpProjTestBranch2ID = "66666666-6666-4666-8666-666666666666"
)

func zpProjStrPtr(s string) *string { return &s }

func zpProjTestProject(t *testing.T, id, name string) *entities.Project {
	t.Helper()
	project, err := entities.CreateProject(name, "")
	if err != nil {
		t.Fatalf("CreateProject: %v", err)
	}
	projectID, err := value_objects.NewProjectId(id)
	if err != nil {
		t.Fatalf("NewProjectId: %v", err)
	}
	project.ID = &projectID
	return project
}

func zpProjTestOrdered(pairs ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(pairs); i += 2 {
		m.Set(pairs[i].(string), pairs[i+1])
	}
	return m
}

type zpProjFakeRepo struct {
	repositories.ProjectRepository
	findByIDFn       func(projectID string) (*entities.Project, error)
	findByNameResult *entities.Project
	findByNameErr    error
	updateErr        error
	deleteResult     bool
	deleteErr        error
	deletedProjectID string
}

func (r *zpProjFakeRepo) FindByID(ctx context.Context, projectID string) (*entities.Project, error) {
	if r.findByIDFn != nil {
		return r.findByIDFn(projectID)
	}
	return nil, nil
}

func (r *zpProjFakeRepo) FindByName(ctx context.Context, name string) (*entities.Project, error) {
	return r.findByNameResult, r.findByNameErr
}

func (r *zpProjFakeRepo) Update(ctx context.Context, project *entities.Project) error {
	return r.updateErr
}

func (r *zpProjFakeRepo) Delete(ctx context.Context, projectID string) (bool, error) {
	r.deletedProjectID = projectID
	return r.deleteResult, r.deleteErr
}

type zpProjFakeCreateProject struct {
	result      *entities.OrderedMap[any]
	err         error
	called      bool
	projectID   *string
	name        *string
	description string
}

func (u *zpProjFakeCreateProject) Execute(ctx context.Context, projectID *string, name *string, description string) (*entities.OrderedMap[any], error) {
	u.called = true
	u.projectID = projectID
	u.name = name
	u.description = description
	return u.result, u.err
}

type zpProjFakeGetProject struct {
	result    *entities.OrderedMap[any]
	err       error
	called    bool
	projectID string
}

func (u *zpProjFakeGetProject) Execute(ctx context.Context, projectID string) (*entities.OrderedMap[any], error) {
	u.called = true
	u.projectID = projectID
	return u.result, u.err
}

type zpProjFakeListProjects struct {
	result          *entities.OrderedMap[any]
	err             error
	called          bool
	includeBranches bool
}

func (u *zpProjFakeListProjects) Execute(ctx context.Context, includeBranches bool) (*entities.OrderedMap[any], error) {
	u.called = true
	u.includeBranches = includeBranches
	return u.result, u.err
}

type zpProjFakeUpdateProject struct {
	result      *entities.OrderedMap[any]
	err         error
	called      bool
	projectID   string
	name        *string
	description *string
}

func (u *zpProjFakeUpdateProject) Execute(ctx context.Context, projectID string, name, description *string) (*entities.OrderedMap[any], error) {
	u.called = true
	u.projectID = projectID
	u.name = name
	u.description = description
	return u.result, u.err
}

// zpProjFakeProjectIDUseCase serves the four project_id-only use cases.
type zpProjFakeProjectIDUseCase struct {
	result    *entities.OrderedMap[any]
	err       error
	called    bool
	projectID *string
}

func (u *zpProjFakeProjectIDUseCase) Execute(ctx context.Context, projectID *string) (*entities.OrderedMap[any], error) {
	u.called = true
	u.projectID = projectID
	return u.result, u.err
}

type zpProjFakeBranchRepo struct {
	repositories.GitBranchRepository
	branches    []*entities.GitBranch
	findErr     error
	deleteErr   error
	deleteCalls []string
}

func (r *zpProjFakeBranchRepo) FindAllByProject(ctx context.Context, projectID string) ([]*entities.GitBranch, error) {
	return r.branches, r.findErr
}

func (r *zpProjFakeBranchRepo) DeleteBranch(ctx context.Context, branchID string) (bool, error) {
	r.deleteCalls = append(r.deleteCalls, branchID)
	return true, r.deleteErr
}

type zpProjFakeTaskCounter struct {
	count int
	err   error
}

func (c *zpProjFakeTaskCounter) CountTasksByBranch(ctx context.Context, branchID string) (int, error) {
	return c.count, c.err
}

type zpProjNotifierCall struct {
	eventType   string
	projectID   any
	userID      *string
	projectData *entities.OrderedMap[any]
}

type zpProjFakeNotifier struct {
	calls []zpProjNotifierCall
}

func (n *zpProjFakeNotifier) SyncBroadcastProjectEvent(eventType string, projectID any, userID *string, projectData *entities.OrderedMap[any]) {
	n.calls = append(n.calls, zpProjNotifierCall{eventType, projectID, userID, projectData})
}

type zpProjTestEnv struct {
	service    *ProjectManagementService
	repo       *zpProjFakeRepo
	branchRepo *zpProjFakeBranchRepo
	counter    *zpProjFakeTaskCounter
	notifier   *zpProjFakeNotifier
	deps       zpProjDeps
}

func zpProjNewTestEnv(userID *string) *zpProjTestEnv {
	env := &zpProjTestEnv{
		repo:       &zpProjFakeRepo{},
		branchRepo: &zpProjFakeBranchRepo{},
		counter:    &zpProjFakeTaskCounter{},
		notifier:   &zpProjFakeNotifier{},
	}
	env.service = zpProjNewService(env.repo, userID, env.deps, env.notifier, env.branchRepo, env.counter)
	return env
}

func TestProjectManagementService_CreateProject_BroadcastsPayload(t *testing.T) {
	env := zpProjNewTestEnv(zpProjStrPtr("user-1"))
	projectData := zpProjTestOrdered(
		"id", "proj-1",
		"name", "Test Project",
		"description", "desc",
		"created_at", "2025-01-01T00:00:00+00:00",
		"updated_at", "2025-01-01T00:00:00+00:00",
		"git_branchs", entities.NewOrderedMap[any](),
	)
	result := zpProjTestOrdered("success", true, "project", projectData)
	env.deps.CreateProject = &zpProjFakeCreateProject{result: result}
	env.service = zpProjNewService(env.repo, zpProjStrPtr("user-1"), env.deps, env.notifier, env.branchRepo, env.counter)

	got, err := env.service.CreateProject(context.Background(), "Test Project", "desc")
	if err != nil {
		t.Fatalf("CreateProject: %v", err)
	}
	if got != result {
		t.Fatalf("result not returned unchanged")
	}
	if len(env.notifier.calls) != 1 {
		t.Fatalf("notifier calls = %d", len(env.notifier.calls))
	}
	call := env.notifier.calls[0]
	if call.eventType != "created" || call.projectID != "proj-1" {
		t.Fatalf("notifier call = %+v", call)
	}
	if !reflect.DeepEqual(call.projectData.Keys(), []string{"id", "name", "description", "created_at", "updated_at"}) {
		t.Fatalf("payload keys = %v", call.projectData.Keys())
	}
}

func TestProjectManagementService_CreateProject_NoBroadcastWithoutUser(t *testing.T) {
	env := zpProjNewTestEnv(nil)
	projectData := zpProjTestOrdered("id", "proj-1", "name", "Test")
	env.deps.CreateProject = &zpProjFakeCreateProject{result: zpProjTestOrdered("success", true, "project", projectData)}
	env.service = zpProjNewService(env.repo, nil, env.deps, env.notifier, env.branchRepo, env.counter)

	if _, err := env.service.CreateProject(context.Background(), "Test", ""); err != nil {
		t.Fatalf("CreateProject: %v", err)
	}
	if len(env.notifier.calls) != 0 {
		t.Fatalf("notifier calls = %d", len(env.notifier.calls))
	}
}

func TestProjectManagementService_CreateProject_FallsBackWhenValidationFails(t *testing.T) {
	env := zpProjNewTestEnv(zpProjStrPtr("user-1"))
	// Missing name -> Pydantic validation would raise -> raw dict is broadcast.
	projectData := zpProjTestOrdered("id", "proj-1", "git_branchs", entities.NewOrderedMap[any]())
	env.deps.CreateProject = &zpProjFakeCreateProject{result: zpProjTestOrdered("success", true, "project", projectData)}
	env.service = zpProjNewService(env.repo, zpProjStrPtr("user-1"), env.deps, env.notifier, env.branchRepo, env.counter)

	if _, err := env.service.CreateProject(context.Background(), "Test", ""); err != nil {
		t.Fatalf("CreateProject: %v", err)
	}
	if len(env.notifier.calls) != 1 {
		t.Fatalf("notifier calls = %d", len(env.notifier.calls))
	}
	if !reflect.DeepEqual(env.notifier.calls[0].projectData.Keys(), []string{"id", "git_branchs"}) {
		t.Fatalf("fallback keys = %v", env.notifier.calls[0].projectData.Keys())
	}
}

func TestProjectManagementService_CreateProject_UseCaseError(t *testing.T) {
	env := zpProjNewTestEnv(nil)
	env.deps.CreateProject = &zpProjFakeCreateProject{err: errors.New("boom")}
	env.service = zpProjNewService(env.repo, nil, env.deps, env.notifier, env.branchRepo, env.counter)
	result, _ := env.service.CreateProject(context.Background(), "Test", "")
	if !reflect.DeepEqual(result.Keys(), []string{"success", "error"}) {
		t.Fatalf("keys = %v", result.Keys())
	}
	if v, _ := result.Get("error"); v != "boom" {
		t.Fatalf("error = %v", v)
	}
}

func TestProjectManagementService_GetProject_Delegates(t *testing.T) {
	env := zpProjNewTestEnv(nil)
	env.deps.GetProject = &zpProjFakeGetProject{result: zpProjTestOrdered("success", true)}
	env.service = zpProjNewService(env.repo, nil, env.deps, env.notifier, env.branchRepo, env.counter)

	result, _ := env.service.GetProject(context.Background(), "proj-1")
	if v, _ := result.Get("success"); v != true {
		t.Fatalf("success = %v", v)
	}
	if env.deps.GetProject.(*zpProjFakeGetProject).projectID != "proj-1" {
		t.Fatalf("project id = %q", env.deps.GetProject.(*zpProjFakeGetProject).projectID)
	}
}

func TestProjectManagementService_GetProjectByName(t *testing.T) {
	env := zpProjNewTestEnv(nil)
	env.repo.findByNameResult = zpProjTestProject(t, zpProjTestProjectID, "Test Project")
	env.deps.GetProject = &zpProjFakeGetProject{result: zpProjTestOrdered("success", true)}
	env.service = zpProjNewService(env.repo, nil, env.deps, env.notifier, env.branchRepo, env.counter)

	result, _ := env.service.GetProjectByName(context.Background(), "Test Project")
	if v, _ := result.Get("success"); v != true {
		t.Fatalf("success = %v", v)
	}
	if env.deps.GetProject.(*zpProjFakeGetProject).projectID != zpProjTestProjectID {
		t.Fatalf("project id = %q", env.deps.GetProject.(*zpProjFakeGetProject).projectID)
	}

	env.repo.findByNameResult = nil
	result, _ = env.service.GetProjectByName(context.Background(), "missing")
	if v, _ := result.Get("error"); v != "Project with name 'missing' not found" {
		t.Fatalf("error = %v", v)
	}
}

func TestProjectManagementService_ListProjects_Delegates(t *testing.T) {
	env := zpProjNewTestEnv(nil)
	env.deps.ListProjects = &zpProjFakeListProjects{result: zpProjTestOrdered("success", true)}
	env.service = zpProjNewService(env.repo, nil, env.deps, env.notifier, env.branchRepo, env.counter)

	if _, err := env.service.ListProjects(context.Background(), false); err != nil {
		t.Fatalf("ListProjects: %v", err)
	}
	if env.deps.ListProjects.(*zpProjFakeListProjects).includeBranches {
		t.Fatalf("includeBranches = true, want false")
	}
}

func TestProjectManagementService_UpdateProject_BroadcastsPayload(t *testing.T) {
	env := zpProjNewTestEnv(zpProjStrPtr("user-1"))
	projectData := zpProjTestOrdered(
		"id", "proj-1",
		"name", "Updated",
		"description", "d",
		"created_at", "2025-01-01T00:00:00+00:00",
		"updated_at", "2025-01-02T00:00:00+00:00",
	)
	env.deps.UpdateProject = &zpProjFakeUpdateProject{result: zpProjTestOrdered("success", true, "project", projectData)}
	env.service = zpProjNewService(env.repo, zpProjStrPtr("user-1"), env.deps, env.notifier, env.branchRepo, env.counter)

	if _, err := env.service.UpdateProject(context.Background(), "proj-1", zpProjStrPtr("Updated"), nil); err != nil {
		t.Fatalf("UpdateProject: %v", err)
	}
	if len(env.notifier.calls) != 1 {
		t.Fatalf("notifier calls = %d", len(env.notifier.calls))
	}
	call := env.notifier.calls[0]
	if call.eventType != "updated" || call.projectID != "proj-1" {
		t.Fatalf("notifier call = %+v", call)
	}
	if !reflect.DeepEqual(call.projectData.Keys(), []string{"id", "name", "description", "updated_at"}) {
		t.Fatalf("payload keys = %v", call.projectData.Keys())
	}
}

func TestProjectManagementService_UpdateProject_FallsBackWhenNameMissing(t *testing.T) {
	env := zpProjNewTestEnv(zpProjStrPtr("user-1"))
	projectData := zpProjTestOrdered("id", "proj-1", "updated_at", "2025-01-02T00:00:00+00:00")
	env.deps.UpdateProject = &zpProjFakeUpdateProject{result: zpProjTestOrdered("success", true, "project", projectData)}
	env.service = zpProjNewService(env.repo, zpProjStrPtr("user-1"), env.deps, env.notifier, env.branchRepo, env.counter)

	if _, err := env.service.UpdateProject(context.Background(), "proj-1", nil, nil); err != nil {
		t.Fatalf("UpdateProject: %v", err)
	}
	if len(env.notifier.calls) != 1 {
		t.Fatalf("notifier calls = %d", len(env.notifier.calls))
	}
	if !reflect.DeepEqual(env.notifier.calls[0].projectData.Keys(), []string{"id", "updated_at"}) {
		t.Fatalf("fallback keys = %v", env.notifier.calls[0].projectData.Keys())
	}
}

func TestProjectManagementService_ProjectIDUseCases_Delegate(t *testing.T) {
	env := zpProjNewTestEnv(nil)
	health := &zpProjFakeProjectIDUseCase{result: zpProjTestOrdered("success", true)}
	cleanup := &zpProjFakeProjectIDUseCase{result: zpProjTestOrdered("success", true)}
	validate := &zpProjFakeProjectIDUseCase{result: zpProjTestOrdered("success", true)}
	rebalance := &zpProjFakeProjectIDUseCase{result: zpProjTestOrdered("success", true)}
	env.deps.ProjectHealthCheck = health
	env.deps.CleanupObsolete = cleanup
	env.deps.ValidateIntegrity = validate
	env.deps.RebalanceAgents = rebalance
	env.service = zpProjNewService(env.repo, nil, env.deps, env.notifier, env.branchRepo, env.counter)

	projectID := zpProjStrPtr("proj-1")
	if _, _ = env.service.ProjectHealthCheck(context.Background(), projectID); !health.called {
		t.Fatalf("health not called")
	}
	if _, _ = env.service.CleanupObsolete(context.Background(), projectID); !cleanup.called {
		t.Fatalf("cleanup not called")
	}
	if _, _ = env.service.ValidateIntegrity(context.Background(), projectID); !validate.called {
		t.Fatalf("validate not called")
	}
	if _, _ = env.service.RebalanceAgents(context.Background(), projectID); !rebalance.called {
		t.Fatalf("rebalance not called")
	}
}

func TestProjectManagementService_DeleteProject_NotFound(t *testing.T) {
	env := zpProjNewTestEnv(nil)
	result, _ := env.service.DeleteProject(context.Background(), "missing", false)
	if v, _ := result.Get("error"); v != "Project missing not found" {
		t.Fatalf("error = %v", v)
	}
}

func TestProjectManagementService_DeleteProject_MultipleBranches(t *testing.T) {
	env := zpProjNewTestEnv(nil)
	project := zpProjTestProject(t, zpProjTestProjectID, "Test Project")
	env.repo.findByIDFn = func(projectID string) (*entities.Project, error) { return project, nil }
	env.branchRepo.branches = []*entities.GitBranch{
		zpGitBranchTestBranch(t, zpProjTestBranchID, "main", "", zpProjTestProjectID),
		zpGitBranchTestBranch(t, zpProjTestBranch2ID, "dev", "", zpProjTestProjectID),
	}
	result, _ := env.service.DeleteProject(context.Background(), zpProjTestProjectID, false)
	want := "Cannot delete project with multiple branches (2 branches: main, dev). Delete other branches first, or use force=True"
	if v, _ := result.Get("error"); v != want {
		t.Fatalf("error = %v", v)
	}
}

func TestProjectManagementService_DeleteProject_NonMainBranch(t *testing.T) {
	env := zpProjNewTestEnv(nil)
	project := zpProjTestProject(t, zpProjTestProjectID, "Test Project")
	env.repo.findByIDFn = func(projectID string) (*entities.Project, error) { return project, nil }
	env.branchRepo.branches = []*entities.GitBranch{zpGitBranchTestBranch(t, zpProjTestBranchID, "dev", "", zpProjTestProjectID)}
	result, _ := env.service.DeleteProject(context.Background(), zpProjTestProjectID, false)
	want := "Cannot delete project with non-main branch 'dev'. Project must have only 'main' branch, or use force=True"
	if v, _ := result.Get("error"); v != want {
		t.Fatalf("error = %v", v)
	}
}

func TestProjectManagementService_DeleteProject_TasksInMainBranch(t *testing.T) {
	env := zpProjNewTestEnv(nil)
	project := zpProjTestProject(t, zpProjTestProjectID, "Test Project")
	env.repo.findByIDFn = func(projectID string) (*entities.Project, error) { return project, nil }
	env.branchRepo.branches = []*entities.GitBranch{zpGitBranchTestBranch(t, zpProjTestBranchID, "main", "", zpProjTestProjectID)}
	env.counter.count = 3
	result, _ := env.service.DeleteProject(context.Background(), zpProjTestProjectID, false)
	want := "Cannot delete project with 3 tasks in main branch. Delete all tasks first, or use force=True"
	if v, _ := result.Get("error"); v != want {
		t.Fatalf("error = %v", v)
	}
}

func TestProjectManagementService_DeleteProject_Success(t *testing.T) {
	env := zpProjNewTestEnv(zpProjStrPtr("user-1"))
	project := zpProjTestProject(t, zpProjTestProjectID, "Test Project")
	mainBranch := zpGitBranchTestBranch(t, zpProjTestBranchID, "main", "", zpProjTestProjectID)
	env.branchRepo.branches = []*entities.GitBranch{mainBranch}
	calls := 0
	env.repo.findByIDFn = func(projectID string) (*entities.Project, error) {
		calls++
		if calls == 1 {
			return project, nil
		}
		return nil, nil
	}
	env.repo.deleteResult = true
	env.service = zpProjNewService(env.repo, zpProjStrPtr("user-1"), env.deps, env.notifier, env.branchRepo, env.counter)

	result, err := env.service.DeleteProject(context.Background(), zpProjTestProjectID, false)
	if err != nil {
		t.Fatalf("DeleteProject: %v", err)
	}
	if !reflect.DeepEqual(result.Keys(), []string{"success", "message", "project_id"}) {
		t.Fatalf("keys = %v", result.Keys())
	}
	if v, _ := result.Get("message"); v != "Project 'Test Project' deleted successfully" {
		t.Fatalf("message = %v", v)
	}
	if !reflect.DeepEqual(env.branchRepo.deleteCalls, []string{zpProjTestBranchID}) {
		t.Fatalf("branch delete calls = %v", env.branchRepo.deleteCalls)
	}
	if env.repo.deletedProjectID != zpProjTestProjectID {
		t.Fatalf("deleted project id = %q", env.repo.deletedProjectID)
	}
	if len(env.notifier.calls) != 1 {
		t.Fatalf("notifier calls = %d", len(env.notifier.calls))
	}
	if !reflect.DeepEqual(env.notifier.calls[0].projectData.Keys(), []string{"id", "name"}) {
		t.Fatalf("delete payload keys = %v", env.notifier.calls[0].projectData.Keys())
	}
}

func TestProjectManagementService_DeleteProject_StillExists(t *testing.T) {
	env := zpProjNewTestEnv(nil)
	project := zpProjTestProject(t, zpProjTestProjectID, "Test Project")
	env.repo.findByIDFn = func(projectID string) (*entities.Project, error) { return project, nil }
	env.repo.deleteResult = true
	result, _ := env.service.DeleteProject(context.Background(), zpProjTestProjectID, true)
	if v, _ := result.Get("error"); v != "Failed to delete project "+zpProjTestProjectID+" - project still exists after deletion" {
		t.Fatalf("error = %v", v)
	}
}

func TestProjectManagementService_DeleteProject_RepositoryFalse(t *testing.T) {
	env := zpProjNewTestEnv(nil)
	project := zpProjTestProject(t, zpProjTestProjectID, "Test Project")
	calls := 0
	env.repo.findByIDFn = func(projectID string) (*entities.Project, error) {
		calls++
		if calls == 1 {
			return project, nil
		}
		return nil, nil
	}
	result, _ := env.service.DeleteProject(context.Background(), zpProjTestProjectID, true)
	if v, _ := result.Get("error"); v != "Failed to delete project "+zpProjTestProjectID+" - repository returned False" {
		t.Fatalf("error = %v", v)
	}
}
