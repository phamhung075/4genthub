package use_cases

import (
	"context"
	"errors"
	"reflect"
	"testing"

	contextdto "agenthub/fastmcp/task_management/application/dtos/context"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// --- fakes (embedded interfaces so only exercised methods need implementing) ---

type smallUCFakeContextRepo struct {
	repositories.ContextRepository
	exists    bool
	existsErr error
	contexts  []*entities.TaskContext
	listErr   error
}

func (f *smallUCFakeContextRepo) ContextExists(context.Context, string) (bool, error) {
	return f.exists, f.existsErr
}
func (f *smallUCFakeContextRepo) ListContexts(context.Context) ([]*entities.TaskContext, error) {
	return f.contexts, f.listErr
}

type smallUCFakeRuleRepo struct {
	repositories.RuleRepository
	exists       bool
	existsErr    error
	dependent    []string
	dependentErr error
	deleteOK     bool
	deleteErr    error
	metadata     []*entities.RuleMetadata
	rules        []*entities.RuleContent
	listErr      error
}

func (f *smallUCFakeRuleRepo) RuleExists(context.Context, string) (bool, error) {
	return f.exists, f.existsErr
}
func (f *smallUCFakeRuleRepo) GetDependentRules(context.Context, string) ([]string, error) {
	return f.dependent, f.dependentErr
}
func (f *smallUCFakeRuleRepo) DeleteRule(context.Context, string) (bool, error) {
	return f.deleteOK, f.deleteErr
}
func (f *smallUCFakeRuleRepo) ListRules(context.Context, map[string]any) ([]*entities.RuleContent, error) {
	return f.rules, f.listErr
}
func (f *smallUCFakeRuleRepo) ListRuleMetadata(context.Context, map[string]any) ([]*entities.RuleMetadata, error) {
	return f.metadata, f.listErr
}

type smallUCFakeTaskRepo struct {
	repositories.TaskRepository
	byID          map[string]*entities.Task
	byIDAllStates map[string]*entities.Task
	all           []*entities.Task
	findErr       error
	saveErr       error
	saved         []*entities.Task
}

func (f *smallUCFakeTaskRepo) FindByID(_ context.Context, id value_objects.TaskId) (*entities.Task, error) {
	if f.findErr != nil {
		return nil, f.findErr
	}
	return f.byID[id.Value], nil
}
func (f *smallUCFakeTaskRepo) FindByIDAllStates(_ context.Context, id value_objects.TaskId) (*entities.Task, error) {
	if f.findErr != nil {
		return nil, f.findErr
	}
	return f.byIDAllStates[id.Value], nil
}
func (f *smallUCFakeTaskRepo) FindAll(context.Context) ([]*entities.Task, error) {
	return f.all, f.findErr
}
func (f *smallUCFakeTaskRepo) Save(_ context.Context, task *entities.Task) (*entities.Task, error) {
	if f.saveErr != nil {
		return nil, f.saveErr
	}
	f.saved = append(f.saved, task)
	return task, nil
}

type smallUCFakeProjectRepo struct {
	repositories.ProjectRepository
	projects  map[string]*entities.Project
	all       []*entities.Project
	findErr   error
	saveErr   error
	updateErr error
	saved     []*entities.Project
	updated   []*entities.Project
}

func (f *smallUCFakeProjectRepo) FindByID(_ context.Context, id string) (*entities.Project, error) {
	if f.findErr != nil {
		return nil, f.findErr
	}
	return f.projects[id], nil
}
func (f *smallUCFakeProjectRepo) FindAll(context.Context) ([]*entities.Project, error) {
	return f.all, f.findErr
}
func (f *smallUCFakeProjectRepo) Save(_ context.Context, p *entities.Project) error {
	if f.saveErr != nil {
		return f.saveErr
	}
	f.saved = append(f.saved, p)
	return nil
}
func (f *smallUCFakeProjectRepo) Update(_ context.Context, p *entities.Project) error {
	if f.updateErr != nil {
		return f.updateErr
	}
	f.updated = append(f.updated, p)
	return nil
}

// --- helpers ---

func smallUCNewTask(id int, title string) *entities.Task {
	tid, err := value_objects.TaskIdFromInt(id)
	if err != nil {
		panic(err)
	}
	task, err := entities.NewTask(entities.Task{ID: &tid, Title: title, Description: "description"})
	if err != nil {
		panic(err)
	}
	return task
}

// --- list_contexts ---

func TestSmallUCListContextsEmpty(t *testing.T) {
	uc := NewListContextsUseCase(&smallUCFakeContextRepo{})
	resp := uc.Execute(context.Background(), &contextdto.ListContextsRequest{})
	if !resp.Success || resp.Message != "Retrieved 0 contexts" {
		t.Fatalf("resp = %+v", resp)
	}
	dict := resp.ToDict()
	if !reflect.DeepEqual(dict.Keys(), []string{"success", "message", "contexts"}) {
		t.Fatalf("keys = %v", dict.Keys())
	}
	if contexts, _ := dict.Get("contexts"); !reflect.DeepEqual(contexts, []any{}) {
		t.Fatalf("contexts = %#v", contexts)
	}
}

// --- list_rules ---

func smallUCRuleMetadata() *entities.RuleMetadata {
	m := entities.NewRuleMetadata("/rules/a.mdc", value_objects.RuleFormatMdc, value_objects.RuleTypeCore,
		10, 1.5, "abc", []string{"dep"})
	m.Author, m.Version, m.Description, m.Tags = "me", "2.0", "desc", []string{"tag"}
	return m
}

func TestSmallUCListRulesMetadataOnly(t *testing.T) {
	repo := &smallUCFakeRuleRepo{metadata: []*entities.RuleMetadata{smallUCRuleMetadata()}}
	uc := NewListRulesUseCase(repo)
	result := uc.Execute(context.Background(), nil, true)

	if !reflect.DeepEqual(result.Keys(), []string{"success", "rules", "count", "filters_applied", "metadata_only"}) {
		t.Fatalf("top keys = %v", result.Keys())
	}
	rules, _ := result.Get("rules")
	rule := rules.([]any)[0].(*entities.OrderedMap[any])
	want := []string{"path", "type", "format", "size", "version", "author", "description", "tags", "dependencies", "modified", "checksum"}
	if !reflect.DeepEqual(rule.Keys(), want) {
		t.Fatalf("rule keys = %v", rule.Keys())
	}
	if v, _ := rule.Get("type"); v != "core" {
		t.Fatalf("type = %v", v)
	}
	if v, _ := rule.Get("format"); v != "mdc" {
		t.Fatalf("format = %v", v)
	}
	if v, _ := rule.Get("modified"); v != 1.5 {
		t.Fatalf("modified = %v", v)
	}
}

func TestSmallUCListRulesFullContent(t *testing.T) {
	rule := &entities.RuleContent{
		Metadata:   smallUCRuleMetadata(),
		RawContent: "body",
		Sections:   entities.NewOrderedMap[string](),
		Variables:  entities.NewOrderedMap[any](),
		References: []string{"ref"},
	}
	repo := &smallUCFakeRuleRepo{rules: []*entities.RuleContent{rule}}
	uc := NewListRulesUseCase(repo)
	result := uc.Execute(context.Background(), map[string]any{"type": "core"}, false)

	rules, _ := result.Get("rules")
	inner := rules.([]any)[0].(*entities.OrderedMap[any])
	want := []string{"path", "type", "format", "content", "size", "version", "author", "description", "tags", "dependencies", "sections", "variables", "references", "modified", "checksum"}
	if !reflect.DeepEqual(inner.Keys(), want) {
		t.Fatalf("rule keys = %v", inner.Keys())
	}
	if v, _ := inner.Get("content"); v != "body" {
		t.Fatalf("content = %v", v)
	}
}

// --- delete_rule ---

func TestSmallUCDeleteRuleNotFound(t *testing.T) {
	uc := NewDeleteRuleUseCase(&smallUCFakeRuleRepo{exists: false})
	result := uc.Execute(context.Background(), "/x", false)
	if !reflect.DeepEqual(result.Keys(), []string{"success", "error"}) {
		t.Fatalf("keys = %v", result.Keys())
	}
	if v, _ := result.Get("error"); v != "Rule not found at path: /x" {
		t.Fatalf("error = %v", v)
	}
}

func TestSmallUCDeleteRuleDependent(t *testing.T) {
	uc := NewDeleteRuleUseCase(&smallUCFakeRuleRepo{exists: true, dependent: []string{"a", "b"}})
	result := uc.Execute(context.Background(), "/x", false)
	want := []string{"success", "error", "dependent_rules", "suggestion"}
	if !reflect.DeepEqual(result.Keys(), want) {
		t.Fatalf("keys = %v", result.Keys())
	}
	if v, _ := result.Get("error"); v != "Cannot delete rule: 2 dependent rules found" {
		t.Fatalf("error = %v", v)
	}
}

func TestSmallUCDeleteRuleSuccess(t *testing.T) {
	uc := NewDeleteRuleUseCase(&smallUCFakeRuleRepo{exists: true, deleteOK: true})
	result := uc.Execute(context.Background(), "/x", true)
	want := []string{"success", "message", "rule_path", "forced"}
	if !reflect.DeepEqual(result.Keys(), want) {
		t.Fatalf("keys = %v", result.Keys())
	}
	if v, _ := result.Get("forced"); v != true {
		t.Fatalf("forced = %v", v)
	}
}

// --- get_blocking_tasks / manage_dependencies ---

func smallUCTaskRepo() *smallUCFakeTaskRepo {
	t1 := smallUCNewTask(1, "one")
	t2 := smallUCNewTask(2, "two")
	return &smallUCFakeTaskRepo{
		byID:          map[string]*entities.Task{"1": t1, "2": t2},
		byIDAllStates: map[string]*entities.Task{"1": t1, "2": t2},
		all:           []*entities.Task{t1, t2},
	}
}

// smallUCTaskRepoWithDep returns the same repo with task 2 depending on task 1.
func smallUCTaskRepoWithDep() *smallUCFakeTaskRepo {
	repo := smallUCTaskRepo()
	dep, _ := value_objects.TaskIdFromInt(1)
	if err := repo.byID["2"].AddDependency(dep); err != nil {
		panic(err)
	}
	return repo
}

func TestSmallUCGetBlockingTasks(t *testing.T) {
	uc := NewGetBlockingTasksUseCase(smallUCTaskRepoWithDep())
	result, err := uc.Execute(context.Background(), "1")
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(result.Keys(), []string{"task_id", "blocking_tasks", "blocking_count"}) {
		t.Fatalf("keys = %v", result.Keys())
	}
	if v, _ := result.Get("blocking_count"); v != 1 {
		t.Fatalf("count = %v", v)
	}
	tasks, _ := result.Get("blocking_tasks")
	entry := tasks.([]any)[0].(*entities.OrderedMap[any])
	if !reflect.DeepEqual(entry.Keys(), []string{"id", "title", "status", "priority"}) {
		t.Fatalf("entry keys = %v", entry.Keys())
	}
	if v, _ := entry.Get("id"); v != "2" {
		t.Fatalf("id = %v", v)
	}
	if v, _ := entry.Get("status"); v != "todo" {
		t.Fatalf("status = %v", v)
	}
	if v, _ := entry.Get("priority"); v != "medium" {
		t.Fatalf("priority = %v", v)
	}
}

func TestSmallUCGetBlockingTasksMissing(t *testing.T) {
	uc := NewGetBlockingTasksUseCase(&smallUCFakeTaskRepo{byID: map[string]*entities.Task{}})
	_, err := uc.Execute(context.Background(), "9")
	var notFound *exceptions.TaskNotFoundError
	if !errors.As(err, &notFound) {
		t.Fatalf("err = %v (%T), want TaskNotFoundError", err, err)
	}
	if err.Error() != "Task 9 not found" {
		t.Fatalf("err = %v", err)
	}
}

func TestSmallUCManageDependenciesAdd(t *testing.T) {
	uc := NewManageDependenciesUseCase(smallUCTaskRepo())
	resp, err := uc.AddDependency(context.Background(), &AddDependencyRequest{TaskID: 2, DependencyID: 1})
	if err != nil {
		t.Fatal(err)
	}
	if !resp.Success || resp.TaskID != "2" || !reflect.DeepEqual(resp.Dependencies, []string{"1"}) {
		t.Fatalf("resp = %+v", resp)
	}
	if resp.Message != "Dependency 1 added successfully" {
		t.Fatalf("message = %q", resp.Message)
	}
}

func TestSmallUCManageDependenciesAddDuplicate(t *testing.T) {
	repo := smallUCTaskRepo()
	uc := NewManageDependenciesUseCase(repo)
	_, _ = uc.AddDependency(context.Background(), &AddDependencyRequest{TaskID: 2, DependencyID: 1})
	resp, err := uc.AddDependency(context.Background(), &AddDependencyRequest{TaskID: 2, DependencyID: 1})
	if err != nil {
		t.Fatal(err)
	}
	if resp.Success || resp.Message != "Dependency 1 already exists" {
		t.Fatalf("resp = %+v", resp)
	}
}

func TestSmallUCManageDependenciesAddSelfCircular(t *testing.T) {
	uc := NewManageDependenciesUseCase(smallUCTaskRepo())
	resp, err := uc.AddDependency(context.Background(), &AddDependencyRequest{TaskID: 2, DependencyID: 2})
	if err != nil {
		t.Fatal(err)
	}
	if resp.Success || resp.Message != "Cannot add dependency: would create circular reference" {
		t.Fatalf("resp = %+v", resp)
	}
}

func TestSmallUCManageDependenciesGetAndClear(t *testing.T) {
	repo := smallUCTaskRepoWithDep()
	uc := NewManageDependenciesUseCase(repo)
	result, err := uc.GetDependencies(context.Background(), 2)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(result.Keys(), []string{"task_id", "dependency_ids", "dependencies", "can_start"}) {
		t.Fatalf("keys = %v", result.Keys())
	}
	if v, _ := result.Get("can_start"); v != true {
		t.Fatalf("can_start = %v", v)
	}
	deps, _ := result.Get("dependencies")
	entry := deps.([]any)[0].(*entities.OrderedMap[any])
	if v, _ := entry.Get("title"); v != "one" {
		t.Fatalf("title = %v", v)
	}

	clear, err := uc.ClearDependencies(context.Background(), 2)
	if err != nil {
		t.Fatal(err)
	}
	if !clear.Success || clear.Message != "Cleared 1 dependencies" || len(clear.Dependencies) != 0 {
		t.Fatalf("clear = %+v", clear)
	}
}

// --- create_git_branch / update_project ---

func smallUCProject(t *testing.T) *entities.Project {
	t.Helper()
	project, err := entities.CreateProject("P", "D")
	if err != nil {
		t.Fatal(err)
	}
	return project
}

func TestSmallUCCreateGitBranch(t *testing.T) {
	project := smallUCProject(t)
	repo := &smallUCFakeProjectRepo{projects: map[string]*entities.Project{project.ID.Value: project}}
	uc := NewCreateGitBranchUseCase(repo)
	result, err := uc.Execute(context.Background(), project.ID.Value, "feature-x", "Feature X", "desc")
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(result.Keys(), []string{"success", "git_branch", "message"}) {
		t.Fatalf("keys = %v", result.Keys())
	}
	branchAny, _ := result.Get("git_branch")
	branch := branchAny.(*entities.OrderedMap[any])
	want := []string{"id", "name", "description", "project_id", "created_at", "completed_tasks", "progress"}
	if !reflect.DeepEqual(branch.Keys(), want) {
		t.Fatalf("branch keys = %v", branch.Keys())
	}
	if v, _ := branch.Get("name"); v != "Feature X" {
		t.Fatalf("name = %v", v)
	}
	if v, _ := branch.Get("completed_tasks"); v != 0 {
		t.Fatalf("completed_tasks = %v", v)
	}
	if v, _ := branch.Get("progress"); v != 0.0 {
		t.Fatalf("progress = %v", v)
	}
	if len(repo.saved) != 1 {
		t.Fatalf("save calls = %d", len(repo.saved))
	}
}

func TestSmallUCCreateGitBranchDuplicate(t *testing.T) {
	project := smallUCProject(t)
	repo := &smallUCFakeProjectRepo{projects: map[string]*entities.Project{project.ID.Value: project}}
	uc := NewCreateGitBranchUseCase(repo)
	_, _ = uc.Execute(context.Background(), project.ID.Value, "feature-x", "Feature X", "desc")
	result, err := uc.Execute(context.Background(), project.ID.Value, "feature-x", "Feature X", "desc")
	if err != nil {
		t.Fatal(err)
	}
	if v, _ := result.Get("success"); v != false {
		t.Fatalf("success = %v", v)
	}
	if v, _ := result.Get("error"); v != "Git branch feature-x already exists" {
		t.Fatalf("error = %v", v)
	}
}

func TestSmallUCCreateGitBranchMissingProject(t *testing.T) {
	uc := NewCreateGitBranchUseCase(&smallUCFakeProjectRepo{projects: map[string]*entities.Project{}})
	result, err := uc.Execute(context.Background(), "nope", "b", "B", "")
	if err != nil {
		t.Fatal(err)
	}
	if v, _ := result.Get("error"); v != "Project with ID 'nope' not found" {
		t.Fatalf("error = %v", v)
	}
}

func TestSmallUCUpdateProject(t *testing.T) {
	project := smallUCProject(t)
	repo := &smallUCFakeProjectRepo{projects: map[string]*entities.Project{project.ID.Value: project}}
	uc := NewUpdateProjectUseCase(repo)
	name := "New"
	result, err := uc.Execute(context.Background(), project.ID.Value, &name, nil)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(result.Keys(), []string{"success", "project", "updated_fields", "message"}) {
		t.Fatalf("keys = %v", result.Keys())
	}
	if v, _ := result.Get("updated_fields"); !reflect.DeepEqual(v, []string{"name"}) {
		t.Fatalf("updated_fields = %v", v)
	}
	if len(repo.updated) != 1 {
		t.Fatalf("update calls = %d", len(repo.updated))
	}
}

func TestSmallUCUpdateProjectNoFields(t *testing.T) {
	project := smallUCProject(t)
	repo := &smallUCFakeProjectRepo{projects: map[string]*entities.Project{project.ID.Value: project}}
	uc := NewUpdateProjectUseCase(repo)
	result, err := uc.Execute(context.Background(), project.ID.Value, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if v, _ := result.Get("error"); v != "No fields to update. Provide name and/or description." {
		t.Fatalf("error = %v", v)
	}
}

// --- project_health_check ---

func TestSmallUCProjectHealthCheckSingle(t *testing.T) {
	project := smallUCProject(t)
	repo := &smallUCFakeProjectRepo{projects: map[string]*entities.Project{project.ID.Value: project}}
	uc := NewProjectHealthCheckUseCase(repo)
	result, err := uc.Execute(context.Background(), &project.ID.Value)
	if err != nil {
		t.Fatal(err)
	}
	healthAny, _ := result.Get("health_status")
	health := healthAny.(*entities.OrderedMap[any])
	want := []string{"status", "issues", "warnings", "checked_at", "registered_agents_count", "active_assignments", "active_sessions", "cross_tree_dependencies"}
	if !reflect.DeepEqual(health.Keys(), want) {
		t.Fatalf("health keys = %v", health.Keys())
	}
	if v, _ := health.Get("status"); v != "warning" {
		t.Fatalf("status = %v", v)
	}
	if v, _ := health.Get("warnings"); !reflect.DeepEqual(v, []string{"No task trees defined"}) {
		t.Fatalf("warnings = %v", v)
	}
}

func TestSmallUCProjectHealthCheckAll(t *testing.T) {
	project := smallUCProject(t)
	repo := &smallUCFakeProjectRepo{
		projects: map[string]*entities.Project{project.ID.Value: project},
		all:      []*entities.Project{project},
	}
	uc := NewProjectHealthCheckUseCase(repo)
	result, err := uc.Execute(context.Background(), nil)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(result.Keys(), []string{"success", "overall_health", "project_health", "total_projects", "message"}) {
		t.Fatalf("keys = %v", result.Keys())
	}
	if v, _ := result.Get("overall_health"); v != "warning" {
		t.Fatalf("overall = %v", v)
	}
	if v, _ := result.Get("total_projects"); v != 1 {
		t.Fatalf("total = %v", v)
	}
}

func TestSmallUCProjectHealthCheckCircular(t *testing.T) {
	project := smallUCProject(t)
	a := &entities.StringSet{}
	a.Add("b")
	b := &entities.StringSet{}
	b.Add("a")
	project.CrossTreeDependencies.Set("a", a)
	project.CrossTreeDependencies.Set("b", b)
	repo := &smallUCFakeProjectRepo{projects: map[string]*entities.Project{project.ID.Value: project}}
	uc := NewProjectHealthCheckUseCase(repo)
	result, err := uc.Execute(context.Background(), &project.ID.Value)
	if err != nil {
		t.Fatal(err)
	}
	healthAny, _ := result.Get("health_status")
	health := healthAny.(*entities.OrderedMap[any])
	if v, _ := health.Get("status"); v != "critical" {
		t.Fatalf("status = %v", v)
	}
	if v, _ := health.Get("cross_tree_dependencies"); v != 2 {
		t.Fatalf("cross_tree_dependencies = %v", v)
	}
}
