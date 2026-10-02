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
	zpGitBranchTestProjectID = "11111111-1111-4111-8111-111111111111"
	zpGitBranchTestBranchID  = "22222222-2222-4222-8222-222222222222"
	zpGitBranchTestBranch2ID = "33333333-3333-4333-8333-333333333333"
)

func zpGitBranchTestBranch(t *testing.T, id, name, description, projectID string) *entities.GitBranch {
	t.Helper()
	branch, err := entities.CreateGitBranch(name, description, projectID)
	if err != nil {
		t.Fatalf("CreateGitBranch: %v", err)
	}
	branchID, err := value_objects.NewGitBranchId(id)
	if err != nil {
		t.Fatalf("NewGitBranchId: %v", err)
	}
	branch.ID = &branchID
	return branch
}

func zpGitBranchTestProject(t *testing.T, id, name string, branches ...*entities.GitBranch) *entities.Project {
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
	for _, branch := range branches {
		if err := project.AddGitBranch(branch); err != nil {
			t.Fatalf("AddGitBranch: %v", err)
		}
	}
	return project
}

type zpGitBranchFakeProjectRepo struct {
	repositories.ProjectRepository
	findByIDResult *entities.Project
	findByIDErr    error
	findByName     *entities.Project
	findByNameErr  error
	updated        *entities.Project
	updateErr      error
}

func (r *zpGitBranchFakeProjectRepo) FindByID(ctx context.Context, projectID string) (*entities.Project, error) {
	return r.findByIDResult, r.findByIDErr
}

func (r *zpGitBranchFakeProjectRepo) FindByName(ctx context.Context, name string) (*entities.Project, error) {
	return r.findByName, r.findByNameErr
}

func (r *zpGitBranchFakeProjectRepo) Update(ctx context.Context, project *entities.Project) error {
	r.updated = project
	return r.updateErr
}

type zpGitBranchFakeRepo struct {
	repositories.GitBranchRepository

	byID          *entities.GitBranch
	findByIDErr   error
	findByNameVal *entities.GitBranch
	findByNameErr error
	createVal     *entities.GitBranch
	createErr     error
	deleteVal     bool
	deleteErr     error
	findAllVal    []*entities.GitBranch
	findAllErr    error
	updateVal     bool
	updateErr     error
	assignVal     bool
	assignErr     error
	unassignVal   bool
	unassignErr   error
	statsVal      map[string]any
	statsErr      error
	archiveVal    map[string]any
	archiveErr    error
	restoreVal    map[string]any
	restoreErr    error

	gotCreateArgs   []string
	gotDeleteBranch string
	gotAssign       []string
}

func (r *zpGitBranchFakeRepo) FindByID(ctx context.Context, branchID string, projectID *string) (*entities.GitBranch, error) {
	return r.byID, r.findByIDErr
}

func (r *zpGitBranchFakeRepo) FindByName(ctx context.Context, projectID, branchName string) (*entities.GitBranch, error) {
	return r.findByNameVal, r.findByNameErr
}

func (r *zpGitBranchFakeRepo) CreateBranch(ctx context.Context, projectID, branchName, description string) (*entities.GitBranch, error) {
	r.gotCreateArgs = []string{projectID, branchName, description}
	return r.createVal, r.createErr
}

func (r *zpGitBranchFakeRepo) DeleteBranch(ctx context.Context, branchID string) (bool, error) {
	r.gotDeleteBranch = branchID
	return r.deleteVal, r.deleteErr
}

func (r *zpGitBranchFakeRepo) FindAll(ctx context.Context) ([]*entities.GitBranch, error) {
	return r.findAllVal, r.findAllErr
}

func (r *zpGitBranchFakeRepo) Update(ctx context.Context, branch *entities.GitBranch) (bool, error) {
	return r.updateVal, r.updateErr
}

func (r *zpGitBranchFakeRepo) AssignAgent(ctx context.Context, projectID, branchID, agentID string) (bool, error) {
	r.gotAssign = []string{projectID, branchID, agentID}
	return r.assignVal, r.assignErr
}

func (r *zpGitBranchFakeRepo) UnassignAgent(ctx context.Context, projectID, branchID string) (bool, error) {
	r.gotAssign = []string{projectID, branchID}
	return r.unassignVal, r.unassignErr
}

func (r *zpGitBranchFakeRepo) GetBranchStatistics(ctx context.Context, projectID, gitBranchID string) (map[string]any, error) {
	return r.statsVal, r.statsErr
}

func (r *zpGitBranchFakeRepo) ArchiveBranch(ctx context.Context, projectID, gitBranchID string) (map[string]any, error) {
	return r.archiveVal, r.archiveErr
}

func (r *zpGitBranchFakeRepo) RestoreBranch(ctx context.Context, projectID, gitBranchID string) (map[string]any, error) {
	return r.restoreVal, r.restoreErr
}

type zpGitBranchFakeContext struct {
	createVal     *entities.OrderedMap[any]
	createErr     error
	deleteVal     *entities.OrderedMap[any]
	deleteErr     error
	createCalls   int
	deleteCalls   int
	lastCreateID  string
	lastCreateArg *entities.OrderedMap[any]
}

func (c *zpGitBranchFakeContext) CreateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], projectID *string) (*entities.OrderedMap[any], error) {
	c.createCalls++
	c.lastCreateID = contextID
	c.lastCreateArg = data
	return c.createVal, c.createErr
}

func (c *zpGitBranchFakeContext) DeleteContext(ctx context.Context, level, contextID string) (*entities.OrderedMap[any], error) {
	c.deleteCalls++
	return c.deleteVal, c.deleteErr
}

type zpGitBranchFakeNotifier struct {
	calls      int
	eventType  string
	branchID   string
	projectID  string
	userID     *string
	branchData *entities.OrderedMap[any]
}

func (n *zpGitBranchFakeNotifier) SyncBroadcastBranchEvent(eventType, branchID, projectID string, userID *string, branchData *entities.OrderedMap[any]) {
	n.calls++
	n.eventType = eventType
	n.branchID = branchID
	n.projectID = projectID
	n.userID = userID
	n.branchData = branchData
}

type zpGitBranchTestEnv struct {
	service    *GitBranchService
	project    *zpGitBranchFakeProjectRepo
	branch     *zpGitBranchFakeRepo
	contextSvc *zpGitBranchFakeContext
	notifier   *zpGitBranchFakeNotifier
}

func zpGitBranchNewTestEnv(t *testing.T, userID *string) *zpGitBranchTestEnv {
	t.Helper()
	env := &zpGitBranchTestEnv{
		project:    &zpGitBranchFakeProjectRepo{},
		branch:     &zpGitBranchFakeRepo{},
		contextSvc: &zpGitBranchFakeContext{createVal: zpGitBranchOKMap()},
		notifier:   &zpGitBranchFakeNotifier{},
	}
	svc, err := zpGitBranchNewService(env.project, env.branch, env.contextSvc, userID, env.notifier)
	if err != nil {
		t.Fatalf("zpGitBranchNewService: %v", err)
	}
	env.service = svc
	return env
}

func zpGitBranchOKMap() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("context", entities.NewOrderedMap[any]())
	return m
}

func TestGitBranchService_ConstructorRequiresRepositories(t *testing.T) {
	if _, err := zpGitBranchNewService(nil, &zpGitBranchFakeRepo{}, nil, nil, nil); err == nil || err.Error() != "Project repository is required" {
		t.Fatalf("nil project repo error = %v", err)
	}
	if _, err := zpGitBranchNewService(&zpGitBranchFakeProjectRepo{}, nil, nil, nil, nil); err == nil || err.Error() != "Git branch repository is required" {
		t.Fatalf("nil git branch repo error = %v", err)
	}
}

func TestGitBranchService_CreateGitBranch_Success(t *testing.T) {
	env := zpGitBranchNewTestEnv(t, nil)
	project := zpGitBranchTestProject(t, zpGitBranchTestProjectID, "Test Project")
	branch := zpGitBranchTestBranch(t, zpGitBranchTestBranchID, "feature/test", "Test branch", zpGitBranchTestProjectID)
	env.project.findByIDResult = project
	env.branch.createVal = branch

	result, err := env.service.CreateGitBranch(context.Background(), zpGitBranchTestProjectID, "feature/test", "Test branch")
	if err != nil {
		t.Fatalf("CreateGitBranch: %v", err)
	}
	if !reflect.DeepEqual(result.Keys(), []string{"success", "git_branch", "message"}) {
		t.Fatalf("keys = %v", result.Keys())
	}
	if v, _ := result.Get("success"); v != true {
		t.Fatalf("success = %v", v)
	}
	gotBranch, _ := result.Get("git_branch")
	branchMap := gotBranch.(*entities.OrderedMap[any])
	if !reflect.DeepEqual(branchMap.Keys(), []string{"id", "name", "git_branch_name", "description", "project_id"}) {
		t.Fatalf("branch keys = %v", branchMap.Keys())
	}
	if v, _ := branchMap.Get("id"); v != zpGitBranchTestBranchID {
		t.Fatalf("id = %v", v)
	}
	if v, _ := branchMap.Get("git_branch_name"); v != "feature/test" {
		t.Fatalf("git_branch_name = %v", v)
	}
	if v, _ := result.Get("message"); v != "Git branch 'feature/test' created successfully" {
		t.Fatalf("message = %v", v)
	}
	if !reflect.DeepEqual(env.branch.gotCreateArgs, []string{zpGitBranchTestProjectID, "feature/test", "Test branch"}) {
		t.Fatalf("create args = %v", env.branch.gotCreateArgs)
	}
	if env.contextSvc.createCalls != 1 {
		t.Fatalf("context create calls = %d", env.contextSvc.createCalls)
	}
	if env.project.updated == nil || !env.project.updated.GitBranchs.Has(zpGitBranchTestBranchID) {
		t.Fatalf("project not updated with new branch")
	}
}

func TestGitBranchService_CreateGitBranch_ProjectNotFound(t *testing.T) {
	env := zpGitBranchNewTestEnv(t, nil)
	result, err := env.service.CreateGitBranch(context.Background(), "missing-project", "feature/test", "")
	if err != nil {
		t.Fatalf("CreateGitBranch: %v", err)
	}
	if !reflect.DeepEqual(result.Keys(), []string{"success", "error"}) {
		t.Fatalf("keys = %v", result.Keys())
	}
	if v, _ := result.Get("error"); v != "Project missing-project not found" {
		t.Fatalf("error = %v", v)
	}
}

func TestGitBranchService_CreateGitBranch_AlreadyExists(t *testing.T) {
	env := zpGitBranchNewTestEnv(t, nil)
	project := zpGitBranchTestProject(t, zpGitBranchTestProjectID, "Test Project")
	branch := zpGitBranchTestBranch(t, zpGitBranchTestBranchID, "feature/test", "", zpGitBranchTestProjectID)
	env.project.findByIDResult = project
	env.branch.findByNameVal = branch

	result, _ := env.service.CreateGitBranch(context.Background(), zpGitBranchTestProjectID, "feature/test", "")
	if v, _ := result.Get("error"); v != "Git branch 'feature/test' already exists in project "+zpGitBranchTestProjectID {
		t.Fatalf("error = %v", v)
	}
}

func TestGitBranchService_CreateGitBranch_ContextErrorStillSucceeds(t *testing.T) {
	env := zpGitBranchNewTestEnv(t, nil)
	project := zpGitBranchTestProject(t, zpGitBranchTestProjectID, "Test Project")
	branch := zpGitBranchTestBranch(t, zpGitBranchTestBranchID, "feature/test", "", zpGitBranchTestProjectID)
	env.project.findByIDResult = project
	env.branch.createVal = branch
	env.contextSvc.createErr = errors.New("context down")

	result, _ := env.service.CreateGitBranch(context.Background(), zpGitBranchTestProjectID, "feature/test", "")
	if v, _ := result.Get("success"); v != true {
		t.Fatalf("success = %v", v)
	}
}

func TestGitBranchService_GetGitBranch_Success(t *testing.T) {
	env := zpGitBranchNewTestEnv(t, nil)
	branch := zpGitBranchTestBranch(t, zpGitBranchTestBranchID, "feature/test", "desc", zpGitBranchTestProjectID)
	project := zpGitBranchTestProject(t, zpGitBranchTestProjectID, "Test Project", branch)
	env.project.findByIDResult = project

	result, err := env.service.GetGitBranch(context.Background(), zpGitBranchTestProjectID, "feature/test")
	if err != nil {
		t.Fatalf("GetGitBranch: %v", err)
	}
	if !reflect.DeepEqual(result.Keys(), []string{"success", "git_branch"}) {
		t.Fatalf("keys = %v", result.Keys())
	}
	gotBranch, _ := result.Get("git_branch")
	if !reflect.DeepEqual(gotBranch.(*entities.OrderedMap[any]).Keys(), []string{
		"id", "name", "git_branch_name", "description", "project_id", "created_at", "updated_at",
		"assigned_agent_id", "assigned_agents", "priority", "status", "archived",
	}) {
		t.Fatalf("branch keys = %v", gotBranch.(*entities.OrderedMap[any]).Keys())
	}
}

func TestGitBranchService_GetGitBranch_NotFound(t *testing.T) {
	env := zpGitBranchNewTestEnv(t, nil)
	project := zpGitBranchTestProject(t, zpGitBranchTestProjectID, "Test Project")
	env.project.findByIDResult = project
	result, _ := env.service.GetGitBranch(context.Background(), zpGitBranchTestProjectID, "nope")
	if v, _ := result.Get("error"); v != "Git branch 'nope' not found in project "+zpGitBranchTestProjectID {
		t.Fatalf("error = %v", v)
	}
}

func TestGitBranchService_ListGitBranchs_Success(t *testing.T) {
	env := zpGitBranchNewTestEnv(t, nil)
	branch := zpGitBranchTestBranch(t, zpGitBranchTestBranchID, "feature/test", "", zpGitBranchTestProjectID)
	project := zpGitBranchTestProject(t, zpGitBranchTestProjectID, "Test Project", branch)
	env.project.findByIDResult = project

	result, _ := env.service.ListGitBranchs(context.Background(), zpGitBranchTestProjectID)
	if !reflect.DeepEqual(result.Keys(), []string{"success", "project_id", "count", "git_branchs"}) {
		t.Fatalf("keys = %v", result.Keys())
	}
	if v, _ := result.Get("count"); v != 1 {
		t.Fatalf("count = %v", v)
	}
}

func TestGitBranchService_DeleteGitBranch_Success(t *testing.T) {
	env := zpGitBranchNewTestEnv(t, nil)
	branch := zpGitBranchTestBranch(t, zpGitBranchTestBranchID, "feature/test", "", zpGitBranchTestProjectID)
	project := zpGitBranchTestProject(t, zpGitBranchTestProjectID, "Test Project", branch)
	env.branch.byID = branch
	env.branch.deleteVal = true
	env.project.findByIDResult = project

	result, err := env.service.DeleteGitBranch(context.Background(), zpGitBranchTestProjectID, zpGitBranchTestBranchID)
	if err != nil {
		t.Fatalf("DeleteGitBranch: %v", err)
	}
	if !reflect.DeepEqual(result.Keys(), []string{"success", "message"}) {
		t.Fatalf("keys = %v", result.Keys())
	}
	if v, _ := result.Get("message"); v != "Git branch "+zpGitBranchTestBranchID+" deleted successfully" {
		t.Fatalf("message = %v", v)
	}
	if env.branch.gotDeleteBranch != zpGitBranchTestBranchID {
		t.Fatalf("delete branch = %q", env.branch.gotDeleteBranch)
	}
	if env.contextSvc.deleteCalls != 1 {
		t.Fatalf("context delete calls = %d", env.contextSvc.deleteCalls)
	}
	if project.GitBranchs.Has(zpGitBranchTestBranchID) {
		t.Fatalf("branch not removed from project entity")
	}
	if env.notifier.calls != 1 || env.notifier.eventType != "deleted" {
		t.Fatalf("notifier = %+v", env.notifier)
	}
	if !reflect.DeepEqual(env.notifier.branchData.Keys(), []string{"id", "name", "project_id"}) {
		t.Fatalf("branch data keys = %v", env.notifier.branchData.Keys())
	}
}

func TestGitBranchService_DeleteGitBranch_NotFound(t *testing.T) {
	env := zpGitBranchNewTestEnv(t, nil)
	result, _ := env.service.DeleteGitBranch(context.Background(), zpGitBranchTestProjectID, "missing")
	if !reflect.DeepEqual(result.Keys(), []string{"success", "error", "error_code"}) {
		t.Fatalf("keys = %v", result.Keys())
	}
	if v, _ := result.Get("error"); v != "Git branch with ID missing not found" {
		t.Fatalf("error = %v", v)
	}
	if v, _ := result.Get("error_code"); v != "DELETE_FAILED" {
		t.Fatalf("error_code = %v", v)
	}
}

func TestGitBranchService_GetGitBranchByID_Success(t *testing.T) {
	env := zpGitBranchNewTestEnv(t, nil)
	branch := zpGitBranchTestBranch(t, zpGitBranchTestBranchID, "feature/test", "", zpGitBranchTestProjectID)
	env.branch.findAllVal = []*entities.GitBranch{branch}

	result, _ := env.service.GetGitBranchByID(context.Background(), zpGitBranchTestBranchID)
	if !reflect.DeepEqual(result.Keys(), []string{"success", "project_id", "branch_name", "git_branch"}) {
		t.Fatalf("keys = %v", result.Keys())
	}
	if v, _ := result.Get("project_id"); v != zpGitBranchTestProjectID {
		t.Fatalf("project_id = %v", v)
	}
	if v, _ := result.Get("branch_name"); v != "feature/test" {
		t.Fatalf("branch_name = %v", v)
	}
}

func TestGitBranchService_GetGitBranchByID_NotFound(t *testing.T) {
	env := zpGitBranchNewTestEnv(t, nil)
	result, _ := env.service.GetGitBranchByID(context.Background(), "missing")
	if v, _ := result.Get("error"); v != "Git branch missing not found" {
		t.Fatalf("error = %v", v)
	}
}

func TestGitBranchService_UpdateGitBranch_Success(t *testing.T) {
	env := zpGitBranchNewTestEnv(t, nil)
	branch := zpGitBranchTestBranch(t, zpGitBranchTestBranchID, "feature/test", "old", zpGitBranchTestProjectID)
	env.branch.findAllVal = []*entities.GitBranch{branch}
	env.branch.updateVal = true

	name := "feature/updated"
	description := "Updated description"
	result, _ := env.service.UpdateGitBranch(context.Background(), zpGitBranchTestBranchID, &name, &description)
	if !reflect.DeepEqual(result.Keys(), []string{"success", "git_branch", "updated_fields"}) {
		t.Fatalf("keys = %v", result.Keys())
	}
	if v, _ := result.Get("updated_fields"); !reflect.DeepEqual(v, []string{"name", "description"}) {
		t.Fatalf("updated_fields = %v", v)
	}
	if branch.Name != "feature/updated" || branch.Description != "Updated description" {
		t.Fatalf("branch not updated: %+v", branch)
	}
}

func TestGitBranchService_UpdateGitBranch_NoFields(t *testing.T) {
	env := zpGitBranchNewTestEnv(t, nil)
	branch := zpGitBranchTestBranch(t, zpGitBranchTestBranchID, "feature/test", "old", zpGitBranchTestProjectID)
	env.branch.findAllVal = []*entities.GitBranch{branch}
	result, _ := env.service.UpdateGitBranch(context.Background(), zpGitBranchTestBranchID, nil, nil)
	if v, _ := result.Get("error"); v != "No fields to update. Provide branch_name and/or description." {
		t.Fatalf("error = %v", v)
	}
}

func TestGitBranchService_UpdateGitBranch_NotFound(t *testing.T) {
	env := zpGitBranchNewTestEnv(t, nil)
	name := "x"
	result, _ := env.service.UpdateGitBranch(context.Background(), "missing", &name, nil)
	if v, _ := result.Get("error"); v != "Git branch with ID missing not found" {
		t.Fatalf("error = %v", v)
	}
}

func TestGitBranchService_UpdateGitBranch_Failed(t *testing.T) {
	env := zpGitBranchNewTestEnv(t, nil)
	branch := zpGitBranchTestBranch(t, zpGitBranchTestBranchID, "feature/test", "", zpGitBranchTestProjectID)
	env.branch.findAllVal = []*entities.GitBranch{branch}
	name := "x"
	result, _ := env.service.UpdateGitBranch(context.Background(), zpGitBranchTestBranchID, &name, nil)
	if v, _ := result.Get("error"); v != "Failed to update git branch" {
		t.Fatalf("error = %v", v)
	}
}

func TestGitBranchService_AssignAgentToBranch_Success(t *testing.T) {
	env := zpGitBranchNewTestEnv(t, nil)
	branch := zpGitBranchTestBranch(t, zpGitBranchTestBranchID, "feature/test", "", zpGitBranchTestProjectID)
	env.branch.findByNameVal = branch
	env.branch.assignVal = true

	result, _ := env.service.AssignAgentToBranch(context.Background(), zpGitBranchTestProjectID, "agent-1", "feature/test")
	if !reflect.DeepEqual(result.Keys(), []string{"success", "message"}) {
		t.Fatalf("keys = %v", result.Keys())
	}
	if v, _ := result.Get("message"); v != "Agent agent-1 assigned to git branch feature/test" {
		t.Fatalf("message = %v", v)
	}
	if !reflect.DeepEqual(env.branch.gotAssign, []string{zpGitBranchTestProjectID, zpGitBranchTestBranchID, "agent-1"}) {
		t.Fatalf("assign args = %v", env.branch.gotAssign)
	}
	if !reflect.DeepEqual(branch.AssignedAgents, []string{"agent-1"}) {
		t.Fatalf("assigned agents = %v", branch.AssignedAgents)
	}
}

func TestGitBranchService_AssignAgentToBranch_NotFound(t *testing.T) {
	env := zpGitBranchNewTestEnv(t, nil)
	result, _ := env.service.AssignAgentToBranch(context.Background(), zpGitBranchTestProjectID, "agent-1", "nope")
	if v, _ := result.Get("error"); v != "Git branch nope not found in project "+zpGitBranchTestProjectID {
		t.Fatalf("error = %v", v)
	}
}

func TestGitBranchService_UnassignAgentFromBranch_Success(t *testing.T) {
	env := zpGitBranchNewTestEnv(t, nil)
	branch := zpGitBranchTestBranch(t, zpGitBranchTestBranchID, "feature/test", "", zpGitBranchTestProjectID)
	branch.AssignedAgents = []string{"agent-1", "agent-2"}
	env.branch.findByNameVal = branch
	env.branch.unassignVal = true

	result, _ := env.service.UnassignAgentFromBranch(context.Background(), zpGitBranchTestProjectID, "agent-1", "feature/test")
	if v, _ := result.Get("message"); v != "Agent agent-1 unassigned from git branch feature/test" {
		t.Fatalf("message = %v", v)
	}
	if !reflect.DeepEqual(branch.AssignedAgents, []string{"agent-2"}) {
		t.Fatalf("assigned agents = %v", branch.AssignedAgents)
	}
	if len(env.branch.gotAssign) != 2 {
		t.Fatalf("unassign args = %v", env.branch.gotAssign)
	}
}

func TestGitBranchService_GetBranchStatistics(t *testing.T) {
	env := zpGitBranchNewTestEnv(t, nil)
	env.branch.statsVal = map[string]any{"total_tasks": 10}
	result, _ := env.service.GetBranchStatistics(context.Background(), zpGitBranchTestProjectID, zpGitBranchTestBranchID)
	if v, _ := result.Get("success"); v != true {
		t.Fatalf("success = %v", v)
	}
	if v, _ := result.Get("statistics"); !reflect.DeepEqual(v, map[string]any{"total_tasks": 10}) {
		t.Fatalf("statistics = %v", v)
	}

	env.branch.statsVal = map[string]any{"error": "Branch not found"}
	result, _ = env.service.GetBranchStatistics(context.Background(), zpGitBranchTestProjectID, "missing")
	if !reflect.DeepEqual(result.Keys(), []string{"success", "error"}) {
		t.Fatalf("keys = %v", result.Keys())
	}
	if v, _ := result.Get("error"); v != "Branch not found" {
		t.Fatalf("error = %v", v)
	}
}

func TestGitBranchService_ArchiveAndRestore(t *testing.T) {
	env := zpGitBranchNewTestEnv(t, nil)
	env.branch.archiveVal = map[string]any{"success": true}
	result, _ := env.service.ArchiveBranch(context.Background(), zpGitBranchTestProjectID, zpGitBranchTestBranchID)
	if v, _ := result.Get("message"); v != "Git branch "+zpGitBranchTestBranchID+" archived successfully" {
		t.Fatalf("archive message = %v", v)
	}

	// Python truthiness treats any non-empty dict as success, so a failure dict still
	// reports success; only an empty dict reaches the failure branch.
	env.branch.archiveVal = map[string]any{"success": false, "error": "nope"}
	result, _ = env.service.ArchiveBranch(context.Background(), zpGitBranchTestProjectID, zpGitBranchTestBranchID)
	if v, _ := result.Get("success"); v != true {
		t.Fatalf("archive failure-dict success = %v", v)
	}

	env.branch.archiveVal = map[string]any{}
	result, _ = env.service.ArchiveBranch(context.Background(), zpGitBranchTestProjectID, zpGitBranchTestBranchID)
	if v, _ := result.Get("error"); v != "Failed to archive git branch "+zpGitBranchTestBranchID {
		t.Fatalf("archive empty error = %v", v)
	}

	env.branch.restoreVal = map[string]any{"success": true}
	result, _ = env.service.RestoreBranch(context.Background(), zpGitBranchTestProjectID, zpGitBranchTestBranchID)
	if v, _ := result.Get("message"); v != "Git branch "+zpGitBranchTestBranchID+" restored successfully" {
		t.Fatalf("restore message = %v", v)
	}
}

func TestGitBranchService_CreateMissingBranchContext(t *testing.T) {
	env := zpGitBranchNewTestEnv(t, nil)
	branch := zpGitBranchTestBranch(t, zpGitBranchTestBranchID, "feature/test", "descr", zpGitBranchTestProjectID)
	env.branch.byID = branch
	env.contextSvc.createVal = zpGitBranchOKMap()

	result, _ := env.service.CreateMissingBranchContext(context.Background(), zpGitBranchTestBranchID, nil, "", "")
	if !reflect.DeepEqual(result.Keys(), []string{"success", "branch_context", "message"}) {
		t.Fatalf("keys = %v", result.Keys())
	}
	if v, _ := result.Get("message"); v != "Branch context created for branch "+zpGitBranchTestBranchID {
		t.Fatalf("message = %v", v)
	}
	if env.contextSvc.lastCreateID != zpGitBranchTestBranchID {
		t.Fatalf("context id = %q", env.contextSvc.lastCreateID)
	}

	env.branch.byID = nil
	result, _ = env.service.CreateMissingBranchContext(context.Background(), "missing", nil, "", "")
	if v, _ := result.Get("error"); v != "Git branch missing not found" {
		t.Fatalf("error = %v", v)
	}
}

func TestGitBranchService_WithUser(t *testing.T) {
	env := zpGitBranchNewTestEnv(t, nil)
	scoped := env.service.WithUser("user-456")
	if scoped == nil || scoped.userID == nil || *scoped.userID != "user-456" {
		t.Fatalf("WithUser did not scope the service")
	}
	if scoped.projectRepo != env.project {
		t.Fatalf("WithUser changed the project repository")
	}
}
