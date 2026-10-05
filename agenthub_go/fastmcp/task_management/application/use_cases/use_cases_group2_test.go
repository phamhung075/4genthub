package use_cases

import (
	"context"
	"errors"
	"reflect"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ---------------------------------------------------------------------------
// Shared fakes
// ---------------------------------------------------------------------------

type group2FakeProjectRepository struct {
	project     *entities.Project
	findByIDErr error
	findAll     []*entities.Project
	findAllErr  error
	saveErr     error
	updateErr   error
	saveCalls   int
	updateCalls int
	saved       []*entities.Project
	updated     []*entities.Project
}

func (f *group2FakeProjectRepository) Save(_ context.Context, project *entities.Project) error {
	f.saveCalls++
	f.saved = append(f.saved, project)
	return f.saveErr
}

func (f *group2FakeProjectRepository) FindByID(_ context.Context, _ string) (*entities.Project, error) {
	return f.project, f.findByIDErr
}

func (f *group2FakeProjectRepository) FindAll(_ context.Context) ([]*entities.Project, error) {
	return f.findAll, f.findAllErr
}

func (f *group2FakeProjectRepository) Update(_ context.Context, project *entities.Project) error {
	f.updateCalls++
	f.updated = append(f.updated, project)
	return f.updateErr
}

func (f *group2FakeProjectRepository) Delete(_ context.Context, _ string) (bool, error) {
	return false, nil
}

func (f *group2FakeProjectRepository) Exists(_ context.Context, _ string) (bool, error) {
	return false, nil
}

func (f *group2FakeProjectRepository) FindByName(_ context.Context, _ string) (*entities.Project, error) {
	return nil, nil
}

func (f *group2FakeProjectRepository) Count(_ context.Context) (int, error) { return 0, nil }

func (f *group2FakeProjectRepository) FindProjectsWithAgent(_ context.Context, _ string) ([]*entities.Project, error) {
	return nil, nil
}

func (f *group2FakeProjectRepository) FindProjectsByStatus(_ context.Context, _ string) ([]*entities.Project, error) {
	return nil, nil
}

func (f *group2FakeProjectRepository) GetProjectHealthSummary(_ context.Context) (map[string]any, error) {
	return nil, nil
}

func (f *group2FakeProjectRepository) UnassignAgentFromTree(_ context.Context, _, _, _ string) (map[string]any, error) {
	return nil, nil
}

type group2FakeAgentRepository struct {
	assignResult map[string]any
	assignErr    error
	assignCalls  int
	assignArgs   []string
}

func (f *group2FakeAgentRepository) AssignAgentToTree(_ context.Context, projectID, agentID, gitBranchID string) (map[string]any, error) {
	f.assignCalls++
	f.assignArgs = []string{projectID, agentID, gitBranchID}
	return f.assignResult, f.assignErr
}

func (f *group2FakeAgentRepository) RegisterAgent(_ context.Context, _ *entities.Agent) (*entities.Agent, error) {
	return nil, nil
}

func (f *group2FakeAgentRepository) UnregisterAgent(_ context.Context, _, _ string) (map[string]any, error) {
	return nil, nil
}

func (f *group2FakeAgentRepository) UnassignAgentFromTree(_ context.Context, _, _ string, _ *string) (map[string]any, error) {
	return nil, nil
}

func (f *group2FakeAgentRepository) GetAgent(_ context.Context, _, _ string) (map[string]any, error) {
	return nil, nil
}

func (f *group2FakeAgentRepository) ListAgents(_ context.Context, _ string) (map[string]any, error) {
	return nil, nil
}

func (f *group2FakeAgentRepository) UpdateAgent(_ context.Context, _ *entities.Agent) (*entities.Agent, error) {
	return nil, nil
}

func (f *group2FakeAgentRepository) RebalanceAgents(_ context.Context, _ string) (map[string]any, error) {
	return nil, nil
}

// ---------------------------------------------------------------------------
// Shared test helpers (group2 prefix)
// ---------------------------------------------------------------------------

func group2StrPtr(s string) *string { return &s }

func group2NewProjectWithID(t *testing.T, id, name string) *entities.Project {
	t.Helper()
	project, err := entities.CreateProject(name, "")
	if err != nil {
		t.Fatalf("CreateProject: %v", err)
	}
	pid, err := value_objects.NewProjectId(id)
	if err != nil {
		t.Fatalf("NewProjectId(%q): %v", id, err)
	}
	project.ID = &pid
	return project
}

func group2AddBranch(t *testing.T, project *entities.Project, name string) *entities.GitBranch {
	t.Helper()
	id := value_objects.GenerateNewGitBranchId()
	gitBranchName := name
	branch, err := entities.NewGitBranch(entities.GitBranch{
		ID:            &id,
		Name:          name,
		ProjectID:     project.GetEntityID(),
		GitBranchName: &gitBranchName,
	})
	if err != nil {
		t.Fatalf("NewGitBranch: %v", err)
	}
	project.GitBranchs.Set(id.Value, branch)
	return branch
}

func group2AddAgent(t *testing.T, project *entities.Project, key, name string) *entities.Agent {
	t.Helper()
	id, err := value_objects.NewAgentId(value_objects.NewUUIDv4())
	if err != nil {
		t.Fatalf("NewAgentId: %v", err)
	}
	agent, err := entities.NewAgent(entities.Agent{ID: &id, Name: name})
	if err != nil {
		t.Fatalf("NewAgent: %v", err)
	}
	project.RegisteredAgents.Set(key, agent)
	return agent
}

func group2Keys(om *entities.OrderedMap[any]) []string { return om.Keys() }

// ---------------------------------------------------------------------------
// rebalance_agents_use_case_test
// ---------------------------------------------------------------------------

func TestGroup2RebalanceAssignsAndKeyQuirk(t *testing.T) {
	project := group2NewProjectWithID(t, "11111111-2222-3333-4444-555555555555", "P")
	branch1 := group2AddBranch(t, project, "T1")
	branch2 := group2AddBranch(t, project, "T2")
	group2AddBranch(t, project, "T3")
	group2AddAgent(t, project, "A", "A")
	group2AddAgent(t, project, "B", "B")
	project.AgentAssignments.Set(branch1.ID.Value, "A")

	repo := &group2FakeProjectRepository{project: project}
	useCase := NewRebalanceAgentsUseCase(repo)

	projectID := "p1"
	result, err := useCase.Execute(context.Background(), &projectID)
	if err != nil {
		t.Fatalf("Execute error: %v", err)
	}

	if got, want := group2Keys(result), []string{"success", "project_id", "rebalance_result", "message"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("top-level key order = %v, want %v", got, want)
	}
	if v, _ := result.Get("success"); v != true {
		t.Fatalf("success = %v, want true", v)
	}
	if v, _ := result.Get("project_id"); v != "p1" {
		t.Fatalf("project_id = %v, want p1", v)
	}
	if v, _ := result.Get("message"); v != "Agent rebalancing completed for project p1" {
		t.Fatalf("message = %v", v)
	}

	rebalanceAny, _ := result.Get("rebalance_result")
	rebalance, ok := rebalanceAny.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("rebalance_result type = %T", rebalanceAny)
	}
	if got, want := group2Keys(rebalance), []string{"changes_made", "changes"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("rebalance_result key order = %v, want %v", got, want)
	}
	if v, _ := rebalance.Get("changes_made"); v != true {
		t.Fatalf("changes_made = %v, want true", v)
	}
	changesAny, _ := rebalance.Get("changes")
	wantChanges := []string{
		"Assigned agent A to tree " + branch1.ID.Value,
		"Assigned agent B to tree " + branch2.ID.Value,
	}
	if !reflect.DeepEqual(changesAny, wantChanges) {
		t.Fatalf("changes = %v, want %v", changesAny, wantChanges)
	}

	// The Python quirk: the newly written entries use agent_id as the key and
	// tree_id as the value, appended after the pre-existing branch key.
	wantKeys := []string{branch1.ID.Value, "A", "B"}
	if got := project.AgentAssignments.Keys(); !reflect.DeepEqual(got, wantKeys) {
		t.Fatalf("agent_assignments keys = %v, want %v", got, wantKeys)
	}
	if v, _ := project.AgentAssignments.Get(branch1.ID.Value); v != "A" {
		t.Fatalf("agent_assignments[branch1] = %v, want A", v)
	}
	if v, _ := project.AgentAssignments.Get("A"); v != branch1.ID.Value {
		t.Fatalf("agent_assignments[A] = %v, want %v", v, branch1.ID.Value)
	}
	if v, _ := project.AgentAssignments.Get("B"); v != branch2.ID.Value {
		t.Fatalf("agent_assignments[B] = %v, want %v", v, branch2.ID.Value)
	}
	if repo.updateCalls != 1 {
		t.Fatalf("update calls = %d, want 1", repo.updateCalls)
	}
}

func TestGroup2RebalanceAllProjects(t *testing.T) {
	project := group2NewProjectWithID(t, "11111111-2222-3333-4444-555555555555", "P")
	branch := group2AddBranch(t, project, "T1")
	group2AddAgent(t, project, "A", "A")

	repo := &group2FakeProjectRepository{findAll: []*entities.Project{project}}
	useCase := NewRebalanceAgentsUseCase(repo)

	result, err := useCase.Execute(context.Background(), nil)
	if err != nil {
		t.Fatalf("Execute error: %v", err)
	}
	if got, want := group2Keys(result), []string{"success", "total_changes", "rebalance_results", "message"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("top-level key order = %v, want %v", got, want)
	}
	if v, _ := result.Get("total_changes"); v != 1 {
		t.Fatalf("total_changes = %v, want 1", v)
	}
	if v, _ := result.Get("message"); v != "Agent rebalancing completed for all projects. 1 changes made" {
		t.Fatalf("message = %v", v)
	}
	resultsAny, _ := result.Get("rebalance_results")
	results, _ := resultsAny.(*entities.OrderedMap[any])
	if got, want := group2Keys(results), []string{project.GetEntityID()}; !reflect.DeepEqual(got, want) {
		t.Fatalf("rebalance_results keys = %v, want %v", got, want)
	}
	// Key quirk again: key A, value branch id.
	if v, _ := project.AgentAssignments.Get("A"); v != branch.ID.Value {
		t.Fatalf("agent_assignments[A] = %v, want %v", v, branch.ID.Value)
	}
	if repo.updateCalls != 1 {
		t.Fatalf("update calls = %d, want 1", repo.updateCalls)
	}
}

// ---------------------------------------------------------------------------
// cleanup_obsolete_use_case_test
// ---------------------------------------------------------------------------

func TestGroup2CleanupRemovesObsoleteAssignments(t *testing.T) {
	project := group2NewProjectWithID(t, "11111111-2222-3333-4444-555555555555", "P")
	branch := group2AddBranch(t, project, "T1")
	group2AddAgent(t, project, "A1", "A1")
	project.AgentAssignments.Set("ghost", "A1")
	project.AgentAssignments.Set("A1", branch.ID.Value)
	project.AgentAssignments.Set("A9", "T9")
	project.AgentAssignments.Set("A2", branch.ID.Value)

	repo := &group2FakeProjectRepository{project: project}
	useCase := NewCleanupObsoleteUseCase(repo)

	projectID := "p1"
	result, err := useCase.Execute(context.Background(), &projectID)
	if err != nil {
		t.Fatalf("Execute error: %v", err)
	}

	if got, want := group2Keys(result), []string{"success", "project_id", "cleaned_items", "message"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("top-level key order = %v, want %v", got, want)
	}
	if v, _ := result.Get("success"); v != true {
		t.Fatalf("success = %v, want true", v)
	}
	if v, _ := result.Get("message"); v != "Cleanup completed for project p1" {
		t.Fatalf("message = %v", v)
	}
	cleanedAny, _ := result.Get("cleaned_items")
	wantCleaned := []string{
		"Removed assignment of agent ghost to non-existent tree A1",
		"Removed assignment of agent A9 to non-existent tree T9",
		"Removed unregistered agent A2 from assignments",
	}
	if !reflect.DeepEqual(cleanedAny, wantCleaned) {
		t.Fatalf("cleaned_items = %v, want %v", cleanedAny, wantCleaned)
	}

	if got, want := project.AgentAssignments.Keys(), []string{"A1"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("remaining assignment keys = %v, want %v", got, want)
	}
	if v, _ := project.AgentAssignments.Get("A1"); v != branch.ID.Value {
		t.Fatalf("agent_assignments[A1] = %v, want %v", v, branch.ID.Value)
	}
	if repo.updateCalls != 1 {
		t.Fatalf("update calls = %d, want 1", repo.updateCalls)
	}
}

func TestGroup2CleanupAllProjects(t *testing.T) {
	project1 := group2NewProjectWithID(t, "11111111-2222-3333-4444-555555555555", "P1")
	group2AddBranch(t, project1, "T1")
	group2AddAgent(t, project1, "A1", "A1")
	project1.AgentAssignments.Set("ghost", "A1")

	project2 := group2NewProjectWithID(t, "22222222-2222-3333-4444-555555555555", "P2")
	branch2 := group2AddBranch(t, project2, "T1")
	group2AddAgent(t, project2, "A1", "A1")
	project2.AgentAssignments.Set("A1", branch2.ID.Value)

	repo := &group2FakeProjectRepository{findAll: []*entities.Project{project1, project2}}
	useCase := NewCleanupObsoleteUseCase(repo)

	result, err := useCase.Execute(context.Background(), nil)
	if err != nil {
		t.Fatalf("Execute error: %v", err)
	}
	if got, want := group2Keys(result), []string{"success", "total_cleaned", "cleanup_results", "message"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("top-level key order = %v, want %v", got, want)
	}
	if v, _ := result.Get("total_cleaned"); v != 1 {
		t.Fatalf("total_cleaned = %v, want 1", v)
	}
	if v, _ := result.Get("message"); v != "Cleanup completed for all projects. 1 items cleaned" {
		t.Fatalf("message = %v", v)
	}
	resultsAny, _ := result.Get("cleanup_results")
	results, _ := resultsAny.(*entities.OrderedMap[any])
	wantKeys := []string{project1.GetEntityID(), project2.GetEntityID()}
	if got := group2Keys(results); !reflect.DeepEqual(got, wantKeys) {
		t.Fatalf("cleanup_results keys = %v, want %v", got, wantKeys)
	}
	if repo.updateCalls != 1 {
		t.Fatalf("update calls = %d, want 1", repo.updateCalls)
	}
}

// ---------------------------------------------------------------------------
// create_project_test
// ---------------------------------------------------------------------------

func TestGroup2CreateProjectNewConvention(t *testing.T) {
	repo := &group2FakeProjectRepository{}
	useCase := NewCreateProjectUseCase(repo)

	name := "New Proj"
	result, err := useCase.Execute(context.Background(), nil, &name, "desc")
	if err != nil {
		t.Fatalf("Execute error: %v", err)
	}
	if got, want := group2Keys(result), []string{"success", "project"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("top-level key order = %v, want %v", got, want)
	}
	if v, _ := result.Get("success"); v != true {
		t.Fatalf("success = %v, want true", v)
	}
	projectAny, _ := result.Get("project")
	project, _ := projectAny.(*entities.OrderedMap[any])
	wantProjectKeys := []string{"id", "name", "description", "created_at", "updated_at", "git_branchs"}
	if got := group2Keys(project); !reflect.DeepEqual(got, wantProjectKeys) {
		t.Fatalf("project key order = %v, want %v", got, wantProjectKeys)
	}
	idAny, _ := project.Get("id")
	id, _ := idAny.(string)
	if _, err := value_objects.NewProjectId(id); err != nil {
		t.Fatalf("generated id %q is not a valid ProjectId: %v", id, err)
	}
	if v, _ := project.Get("name"); v != "New Proj" {
		t.Fatalf("name = %v", v)
	}
	if v, _ := project.Get("description"); v != "desc" {
		t.Fatalf("description = %v", v)
	}
	if v, _ := project.Get("created_at"); v == "" {
		t.Fatalf("created_at empty")
	}
	if v, _ := project.Get("updated_at"); v == "" {
		t.Fatalf("updated_at empty")
	}
	branchesAny, _ := project.Get("git_branchs")
	branches, _ := branchesAny.(*entities.OrderedMap[any])
	if branches.Len() != 1 {
		t.Fatalf("git_branchs len = %d, want 1", branches.Len())
	}
	branchAny, _ := branches.Get(branches.Keys()[0])
	branchMap, _ := branchAny.(map[string]any)
	if branchMap["name"] != "main" || branchMap["git_branch_name"] != "main" {
		t.Fatalf("branch = %v", branchMap)
	}
	if branchMap["project_id"] != id {
		t.Fatalf("branch project_id = %v, want %v", branchMap["project_id"], id)
	}
	if repo.saveCalls != 1 {
		t.Fatalf("save calls = %d, want 1", repo.saveCalls)
	}
}

func TestGroup2CreateProjectExplicitIDAndNameAsFirstArg(t *testing.T) {
	repo := &group2FakeProjectRepository{}
	useCase := NewCreateProjectUseCase(repo)

	id := "11111111-2222-3333-4444-555555555555"
	name := "Legacy"
	result, err := useCase.Execute(context.Background(), &id, &name, "d")
	if err != nil {
		t.Fatalf("Execute error: %v", err)
	}
	projectAny, _ := result.Get("project")
	project, _ := projectAny.(*entities.OrderedMap[any])
	if v, _ := project.Get("id"); v != id {
		t.Fatalf("explicit id = %v, want %v", v, id)
	}
	if v, _ := project.Get("name"); v != "Legacy" {
		t.Fatalf("name = %v, want Legacy", v)
	}

	// name == nil: the first argument becomes the name and the ID is generated.
	firstArg := "Name From First"
	result2, err := useCase.Execute(context.Background(), &firstArg, nil, "d")
	if err != nil {
		t.Fatalf("Execute error: %v", err)
	}
	project2Any, _ := result2.Get("project")
	project2, _ := project2Any.(*entities.OrderedMap[any])
	if v, _ := project2.Get("name"); v != "Name From First" {
		t.Fatalf("name = %v, want Name From First", v)
	}
	if v, _ := project2.Get("id"); v == firstArg {
		t.Fatalf("id = %v, want a generated id", v)
	}
	if repo.saveCalls != 2 {
		t.Fatalf("save calls = %d, want 2", repo.saveCalls)
	}
}

func TestGroup2CreateProjectNameRequired(t *testing.T) {
	repo := &group2FakeProjectRepository{}
	useCase := NewCreateProjectUseCase(repo)

	result, err := useCase.Execute(context.Background(), nil, nil, "")
	if err != nil {
		t.Fatalf("Execute error: %v", err)
	}
	if got, want := group2Keys(result), []string{"success", "error"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("key order = %v, want %v", got, want)
	}
	if v, _ := result.Get("success"); v != false {
		t.Fatalf("success = %v, want false", v)
	}
	if v, _ := result.Get("error"); v != "Project name is required" {
		t.Fatalf("error = %v", v)
	}
	if repo.saveCalls != 0 {
		t.Fatalf("save calls = %d, want 0", repo.saveCalls)
	}
}

// ---------------------------------------------------------------------------
// get_project_test
// ---------------------------------------------------------------------------

func TestGroup2GetProjectNotFound(t *testing.T) {
	repo := &group2FakeProjectRepository{}
	useCase := NewGetProjectUseCase(repo)

	result, err := useCase.Execute(context.Background(), "missing")
	if err != nil {
		t.Fatalf("Execute error: %v", err)
	}
	if got, want := group2Keys(result), []string{"success", "error"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("key order = %v, want %v", got, want)
	}
	if v, _ := result.Get("success"); v != false {
		t.Fatalf("success = %v, want false", v)
	}
	if v, _ := result.Get("error"); v != "Project with ID 'missing' not found" {
		t.Fatalf("error = %v", v)
	}
}

func TestGroup2GetProjectResponseShape(t *testing.T) {
	project := group2NewProjectWithID(t, "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "Project X")
	project.Description = "D"

	branchEntity := group2AddBranch(t, project, "main")
	branchID := branchEntity.ID.Value

	agentID := "22345678-1234-1234-1234-123456789012"
	agentUUID, err := value_objects.NewAgentId(agentID)
	if err != nil {
		t.Fatalf("NewAgentId: %v", err)
	}
	agent, err := entities.NewAgent(entities.Agent{
		ID:   &agentUUID,
		Name: "Agent A",
		Capabilities: map[entities.AgentCapability]struct{}{
			entities.CapabilityTesting:            {},
			entities.CapabilityBackendDevelopment: {},
		},
	})
	if err != nil {
		t.Fatalf("NewAgent: %v", err)
	}
	project.RegisteredAgents.Set(agentID, agent)

	repo := &group2FakeProjectRepository{project: project}
	useCase := NewGetProjectUseCase(repo)

	result, err := useCase.Execute(context.Background(), "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
	if err != nil {
		t.Fatalf("Execute error: %v", err)
	}
	if got, want := group2Keys(result), []string{"success", "project"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("top-level key order = %v, want %v", got, want)
	}

	projectAny, _ := result.Get("project")
	projectDict, _ := projectAny.(*entities.OrderedMap[any])
	wantProjectKeys := []string{
		"id", "name", "description", "created_at", "updated_at",
		"branch_count", "task_count", "git_branchs", "registered_agents",
		"agent_assignments", "orchestration_status",
	}
	if got := group2Keys(projectDict); !reflect.DeepEqual(got, wantProjectKeys) {
		t.Fatalf("project key order = %v, want %v", got, wantProjectKeys)
	}
	if v, _ := projectDict.Get("id"); v != "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" {
		t.Fatalf("project id = %v", v)
	}
	if v, _ := projectDict.Get("branch_count"); v != 1 {
		t.Fatalf("branch_count = %v, want 1", v)
	}
	if v, _ := projectDict.Get("task_count"); v != 0 {
		t.Fatalf("task_count = %v, want 0", v)
	}

	branchesAny, _ := projectDict.Get("git_branchs")
	branches, _ := branchesAny.(*entities.OrderedMap[any])
	if got, want := group2Keys(branches), []string{branchID}; !reflect.DeepEqual(got, want) {
		t.Fatalf("git_branchs keys = %v, want %v", got, want)
	}
	branchAny, _ := branches.Get(branchID)
	branch, _ := branchAny.(*entities.OrderedMap[any])
	wantBranchKeys := []string{
		"id", "project_id", "name", "git_branch_name", "description",
		"created_at", "updated_at", "status", "task_count", "completed_tasks",
		"in_progress_tasks", "blocked_tasks", "todo_tasks", "progress_percentage",
	}
	if got := group2Keys(branch); !reflect.DeepEqual(got, wantBranchKeys) {
		t.Fatalf("branch key order = %v, want %v", got, wantBranchKeys)
	}
	if v, _ := branch.Get("id"); v != branchID {
		t.Fatalf("branch id = %v", v)
	}
	if v, _ := branch.Get("status"); v != "todo" {
		t.Fatalf("branch status = %v, want todo", v)
	}
	if v, _ := branch.Get("git_branch_name"); v != "main" {
		t.Fatalf("git_branch_name = %v", v)
	}
	if v, _ := branch.Get("progress_percentage"); v != float64(0) {
		t.Fatalf("progress_percentage = %v", v)
	}

	agentsAny, _ := projectDict.Get("registered_agents")
	agents, _ := agentsAny.(*entities.OrderedMap[any])
	if got, want := group2Keys(agents), []string{agentID}; !reflect.DeepEqual(got, want) {
		t.Fatalf("registered_agents keys = %v, want %v", got, want)
	}
	agentAny, _ := agents.Get(agentID)
	agentDict, _ := agentAny.(*entities.OrderedMap[any])
	if got, want := group2Keys(agentDict), []string{"id", "name", "capabilities", "created_at"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("agent key order = %v, want %v", got, want)
	}
	if v, _ := agentDict.Get("id"); v != agentID {
		t.Fatalf("agent id = %v", v)
	}
	capsAny, _ := agentDict.Get("capabilities")
	wantCaps := []string{"backend_development", "testing"}
	if !reflect.DeepEqual(capsAny, wantCaps) {
		t.Fatalf("capabilities = %v, want %v", capsAny, wantCaps)
	}
}

// ---------------------------------------------------------------------------
// assign_agent_test
// ---------------------------------------------------------------------------

func TestGroup2AssignAgentSuccess(t *testing.T) {
	repo := &group2FakeAgentRepository{}
	useCase := NewAssignAgentUseCase(repo)

	response := useCase.Execute(context.Background(), AssignAgentRequest{
		ProjectID: "p", AgentID: "a", GitBranchID: "b",
	})
	if !response.Success {
		t.Fatalf("success = false")
	}
	if response.AgentID != "a" {
		t.Fatalf("agent id = %q", response.AgentID)
	}
	if response.GitBranchID == nil || *response.GitBranchID != "b" {
		t.Fatalf("git_branch_id = %v", response.GitBranchID)
	}
	if response.Message == nil || *response.Message != "Agent a assigned to tree b" {
		t.Fatalf("message = %v", response.Message)
	}
	if response.Error != nil {
		t.Fatalf("error = %v", response.Error)
	}
	if repo.assignCalls != 1 {
		t.Fatalf("assign calls = %d, want 1", repo.assignCalls)
	}
	if want := []string{"p", "a", "b"}; !reflect.DeepEqual(repo.assignArgs, want) {
		t.Fatalf("assign args = %v, want %v", repo.assignArgs, want)
	}
}

func TestGroup2AssignAgentNotFound(t *testing.T) {
	cases := []struct {
		name string
		err  error
	}{
		{"agent", exceptions.NewAgentNotFoundError("Agent a not found")},
		{"project", exceptions.NewProjectNotFoundError("Project p not found")},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			repo := &group2FakeAgentRepository{assignErr: tc.err}
			useCase := NewAssignAgentUseCase(repo)

			response := useCase.Execute(context.Background(), AssignAgentRequest{
				ProjectID: "p", AgentID: "a", GitBranchID: "b",
			})
			if response.Success {
				t.Fatalf("success = true, want false")
			}
			if response.Error == nil || *response.Error != tc.err.Error() {
				t.Fatalf("error = %v, want %v", response.Error, tc.err.Error())
			}
			if response.Message != nil {
				t.Fatalf("message = %v, want nil", response.Message)
			}
			if response.GitBranchID != nil {
				t.Fatalf("git_branch_id = %v, want nil", response.GitBranchID)
			}
		})
	}
}

func TestGroup2AssignAgentUnexpectedError(t *testing.T) {
	repo := &group2FakeAgentRepository{assignErr: errors.New("boom")}
	useCase := NewAssignAgentUseCase(repo)

	response := useCase.Execute(context.Background(), AssignAgentRequest{
		ProjectID: "p", AgentID: "a", GitBranchID: "b",
	})
	if response.Success {
		t.Fatalf("success = true, want false")
	}
	if response.Error == nil || *response.Error != "Unexpected error: boom" {
		t.Fatalf("error = %v", response.Error)
	}
	if response.Message != nil {
		t.Fatalf("message = %v, want nil", response.Message)
	}
}

type createProjectUserRepo struct {
	group2FakeProjectRepository
	user string
}

func (r *createProjectUserRepo) GetCurrentUserID() *string { return &r.user }

type createProjectFakeHooks struct{ users []string }

func (h *createProjectFakeHooks) CreateProjectContext(ctx context.Context, p *entities.Project, userID *string) {
	h.users = append(h.users, "context:"+*userID)
}

func (h *createProjectFakeHooks) NotifyProjectCreated(ctx context.Context, p *entities.Project, userID *string) {
	h.users = append(h.users, "notify:"+*userID)
}

func TestCreateProjectUseCaseHooksReceiveRepositoryUser(t *testing.T) {
	hooks := &createProjectFakeHooks{}
	useCase := NewCreateProjectUseCase(&createProjectUserRepo{user: "u-1"}).WithHooks(hooks)
	name := "Hooked"
	if _, err := useCase.Execute(context.Background(), nil, &name, "d"); err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if want := []string{"context:u-1", "notify:u-1"}; !reflect.DeepEqual(hooks.users, want) {
		t.Fatalf("hook calls = %v, want %v", hooks.users, want)
	}
}
