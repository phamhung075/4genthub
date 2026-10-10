package use_cases

import (
	"context"
	"reflect"
	"testing"

	contextdto "agenthub/fastmcp/task_management/application/dtos/context"
	subtaskdto "agenthub/fastmcp/task_management/application/dtos/subtask"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func draftCheckError(t *testing.T, err *string, want string) {
	t.Helper()
	if err == nil || *err != want {
		t.Fatalf("error = %v, want %q", err, want)
	}
}

// --- add_context_insight ---

func TestDraftAddContextInsight(t *testing.T) {
	uc := NewAddContextInsightUseCase(&draftContextRepo{exists: false})
	resp := uc.Execute(context.Background(), &contextdto.AddInsightRequest{TaskID: "t1"})
	if resp.Success {
		t.Fatal("expected failure")
	}
	draftCheckError(t, resp.Error, "Context not found for task t1")

	uc = NewAddContextInsightUseCase(&draftContextRepo{exists: true, addInsightResult: map[string]any{"z": 1, "a": 2}})
	resp = uc.Execute(context.Background(), &contextdto.AddInsightRequest{TaskID: "t1", Importance: "high"})
	if !resp.Success || resp.Message != "Insight added successfully" {
		t.Fatalf("resp = %+v", resp)
	}
	if got := resp.Data.Keys(); !reflect.DeepEqual(got, []string{"a", "z"}) {
		t.Fatalf("data keys = %v", got)
	}
}

// --- create_context ---

func TestDraftCreateContext(t *testing.T) {
	repo := &draftContextRepo{exists: false, createResult: map[string]any{"task_id": "t1"}}
	uc := NewCreateContextUseCase(repo)
	resp := uc.Execute(context.Background(), &contextdto.CreateContextRequest{TaskID: "t1", Title: "Title"})
	if !resp.Success || resp.Message != "Context created successfully" {
		t.Fatalf("resp = %+v", resp)
	}
	if repo.created.Metadata.TaskID != "t1" || repo.created.Metadata.Status.String() != "todo" ||
		repo.created.Metadata.Priority.String() != "medium" {
		t.Fatalf("metadata = %+v", repo.created.Metadata)
	}

	uc = NewCreateContextUseCase(&draftContextRepo{exists: true})
	resp = uc.Execute(context.Background(), &contextdto.CreateContextRequest{TaskID: "t1"})
	if resp.Success {
		t.Fatal("expected failure")
	}
	draftCheckError(t, resp.Error, "Context already exists for task t1")
}

// --- get_subtask ---

func TestDraftGetSubtaskFallback(t *testing.T) {
	task := draftNewTask(t, "parent")
	subID := value_objects.GenerateNewTaskId()
	task.Subtasks = []string{subID.Value}
	repo := &draftTaskRepo{tasks: map[string]*entities.Task{task.ID.Value: task}}

	result, err := NewGetSubtaskUseCase(repo, nil).Execute(context.Background(), task.ID.Value, subID.Value)
	if err != nil {
		t.Fatal(err)
	}
	if got := result.Keys(); !reflect.DeepEqual(got, []string{"task_id", "subtask", "progress"}) {
		t.Fatalf("keys = %v", got)
	}
	if v, _ := result.Get("subtask"); v != subID.Value {
		t.Fatalf("subtask = %v", v)
	}
}

// --- add_subtask ---

func TestDraftAddSubtaskInheritance(t *testing.T) {
	task := draftNewTask(t, "parent")
	task.Assignees = []string{"coding-agent"}
	taskRepo := &draftTaskRepo{tasks: map[string]*entities.Task{task.ID.Value: task}}
	subID := value_objects.GenerateSubtaskId(*task.ID, nil)
	subRepo := &draftSubtaskRepo{nextID: subID}
	priority := "high"

	resp, err := NewAddSubtaskUseCase(taskRepo, subRepo).Execute(context.Background(), &subtaskdto.AddSubtaskRequest{
		TaskID: task.ID.Value, Title: "child", Priority: &priority,
	})
	if err != nil {
		t.Fatal(err)
	}
	if !resp.AgentInheritanceApplied || !reflect.DeepEqual(resp.InheritedAssignees, []string{"coding-agent"}) {
		t.Fatalf("inheritance = %v %v", resp.AgentInheritanceApplied, resp.InheritedAssignees)
	}
	wantKeys := []string{"id", "title", "description", "status", "priority", "assignees",
		"progress_percentage", "created_at", "updated_at", "parent_task_id"}
	if got := resp.Subtask.Keys(); !reflect.DeepEqual(got, wantKeys) {
		t.Fatalf("subtask keys = %v", got)
	}
	if v, _ := resp.Subtask.Get("priority"); v != "high" {
		t.Fatalf("priority = %v", v)
	}
	if !ucContainsStr(task.Subtasks, subID.Value) {
		t.Fatalf("parent subtasks = %v", task.Subtasks)
	}
	if v, _ := resp.Progress.Get("total"); v != 1 {
		t.Fatalf("progress total = %v", v)
	}
}

// --- update_subtask ---

func TestDraftUpdateSubtask(t *testing.T) {
	task := draftNewTask(t, "parent")
	subID := value_objects.GenerateSubtaskId(*task.ID, nil)
	sub, err := entities.CreateSubtask(subID, "child", "", *task.ID, nil, nil, entities.SubtaskOptions{})
	if err != nil {
		t.Fatal(err)
	}
	taskRepo := &draftTaskRepo{tasks: map[string]*entities.Task{task.ID.Value: task}}
	subRepo := &draftSubtaskRepo{subtasks: map[string]*entities.Subtask{subID.Value: sub}}
	title := "renamed"

	resp, err := NewUpdateSubtaskUseCase(taskRepo, subRepo).Execute(context.Background(), &subtaskdto.UpdateSubtaskRequest{
		TaskID: task.ID.Value, ID: subID.Value, Title: &title,
	})
	if err != nil {
		t.Fatal(err)
	}
	if sub.Title != "renamed" {
		t.Fatalf("title = %q", sub.Title)
	}
	if v, _ := resp.Subtask.Get("title"); v != "renamed" {
		t.Fatalf("response title = %v", v)
	}
}

// --- remove_dependency ---

func TestDraftRemoveDependency(t *testing.T) {
	task := draftNewTask(t, "task")
	depID := value_objects.GenerateNewTaskId()
	task.Dependencies = []value_objects.TaskId{depID}
	repo := &draftTaskRepo{tasks: map[string]*entities.Task{task.ID.Value: task}}
	uc := NewRemoveDependencyUseCase(repo)

	result, err := uc.Execute(context.Background(), task.ID.Value, depID.Value)
	if err != nil {
		t.Fatal(err)
	}
	if !result.Success || result.Message != "Dependency "+depID.Value+" removed successfully" {
		t.Fatalf("result = %+v", result)
	}
	if len(result.Dependencies) != 0 {
		t.Fatalf("dependencies = %v", result.Dependencies)
	}

	result, err = uc.Execute(context.Background(), task.ID.Value, depID.Value)
	if err != nil {
		t.Fatal(err)
	}
	if result.Success || result.Message != "Dependency "+depID.Value+" does not exist" {
		t.Fatalf("result = %+v", result)
	}
}

// --- list_projects ---

func TestDraftListProjects(t *testing.T) {
	project := draftNewProject("P")
	branchID := value_objects.GenerateNewGitBranchId()
	branch, err := entities.NewGitBranch(entities.GitBranch{ID: &branchID, Name: "main", ProjectID: project.GetEntityID()})
	if err != nil {
		t.Fatal(err)
	}
	project.GitBranchs.Set(branchID.Value, branch)

	result, err := NewListProjectsUseCase(&draftProjectRepo{projects: []*entities.Project{project}}).Execute(context.Background(), true)
	if err != nil {
		t.Fatal(err)
	}
	if got := result.Keys(); !reflect.DeepEqual(got, []string{"success", "projects", "count"}) {
		t.Fatalf("keys = %v", got)
	}
	projects, _ := result.Get("projects")
	info := projects.([]any)[0].(*entities.OrderedMap[any])
	wantInfoKeys := []string{"id", "name", "description", "created_at", "updated_at", "branch_count", "task_count",
		"registered_agents_count", "active_assignments", "active_sessions", "git_branchs"}
	if got := info.Keys(); !reflect.DeepEqual(got, wantInfoKeys) {
		t.Fatalf("info keys = %v", got)
	}
	branches, _ := info.Get("git_branchs")
	branchAny, ok := branches.(*entities.OrderedMap[any]).Get(branchID.Value)
	if !ok {
		t.Fatal("missing branch")
	}
	branchDict := branchAny.(*entities.OrderedMap[any])
	wantBranchKeys := []string{"id", "project_id", "name", "git_branch_name", "description", "created_at", "updated_at",
		"status", "task_count", "completed_tasks", "in_progress_tasks", "blocked_tasks", "todo_tasks",
		"progress_percentage", "agent_assignments"}
	if got := branchDict.Keys(); !reflect.DeepEqual(got, wantBranchKeys) {
		t.Fatalf("branch keys = %v", got)
	}
	if v, _ := branchDict.Get("progress_percentage"); v != 0 {
		t.Fatalf("progress = %v", v)
	}
}

// --- validate_integrity_use_case ---

func TestDraftValidateProjectIntegrity(t *testing.T) {
	project := draftNewProject("P")
	branchID := value_objects.GenerateNewGitBranchId()
	// Constructed directly: NewGitBranch rejects an empty name, which is exactly
	// the corrupt state this integrity check reports.
	branch := &entities.GitBranch{ID: &branchID, Name: "", ProjectID: project.GetEntityID()}
	project.GitBranchs.Set(branchID.Value, branch)
	project.AgentAssignments.Set(branchID.Value, "missing-agent")

	result := validateProjectIntegrity(project)
	if valid, _ := result.Get("is_valid"); valid != false {
		t.Fatalf("is_valid = %v", valid)
	}
	errors, _ := result.Get("errors")
	wantErrors := []string{
		"Task tree " + branchID.Value + " missing name",
		"Task tree " + branchID.Value + " has incorrect project_id",
		"Agent " + branchID.Value + " assigned but not registered",
		"Agent " + branchID.Value + " assigned to non-existent tree missing-agent",
	}
	if !reflect.DeepEqual(errors, wantErrors) {
		t.Fatalf("errors = %v", errors)
	}
}

func TestDraftValidateIntegrityNotFound(t *testing.T) {
	result := NewValidateIntegrityUseCase(&draftProjectRepo{byID: map[string]*entities.Project{}}).Execute(context.Background(), strPtr("p1"))
	if got := result.Keys(); !reflect.DeepEqual(got, []string{"success", "error"}) {
		t.Fatalf("keys = %v", got)
	}
	if v, _ := result.Get("error"); v != "Project p1 not found" {
		t.Fatalf("error = %v", v)
	}
}

// --- update_rule ---

func draftRule(path string) *entities.RuleContent {
	return &entities.RuleContent{
		Metadata:   entities.NewRuleMetadata(path, value_objects.RuleFormatMdc, value_objects.RuleTypeCore, 3, 1.0, "sum", []string{}),
		RawContent: "old",
	}
}

func TestDraftUpdateRule(t *testing.T) {
	rule := draftRule("/r")
	repo := &draftRuleRepo{rules: map[string]*entities.RuleContent{"/r": rule}, saveOK: true}
	updates := entities.NewOrderedMap[any]()
	updates.Set("version", "2.0")
	content := "new content"

	result := NewUpdateRuleUseCase(repo).Execute(context.Background(), "/r", &content, updates)
	if got := result.Keys(); !reflect.DeepEqual(got, []string{"success", "message", "rule_path", "updates_applied"}) {
		t.Fatalf("keys = %v", got)
	}
	if rule.RawContent != "new content" || rule.Metadata.Version != "2.0" || rule.Metadata.Size != len("new content") {
		t.Fatalf("rule = %+v", rule)
	}
	applied, _ := result.Get("updates_applied")
	appliedMap := applied.(*entities.OrderedMap[any])
	if v, _ := appliedMap.Get("content_updated"); v != true {
		t.Fatalf("content_updated = %v", v)
	}
	if v, _ := appliedMap.Get("metadata_updated"); v != true {
		t.Fatalf("metadata_updated = %v", v)
	}
}

func TestDraftUpdateRuleNotFound(t *testing.T) {
	repo := &draftRuleRepo{rules: map[string]*entities.RuleContent{}}
	result := NewUpdateRuleUseCase(repo).Execute(context.Background(), "/missing", nil, nil)
	if v, _ := result.Get("error"); v != "Rule not found at path: /missing" {
		t.Fatalf("error = %v", v)
	}
}

// --- validate_rule ---

func TestDraftValidateRule(t *testing.T) {
	rule := draftRule("/r")
	rule.Metadata.Dependencies = []string{"dep"}
	rule.References = []string{"ref"}
	repo := &draftRuleRepo{
		rules:  map[string]*entities.RuleContent{"/r": rule},
		exists: map[string]bool{"/r": true},
		deps:   map[string][]string{},
	}

	path := "/r"
	result := NewValidateRuleUseCase(repo).Execute(context.Background(), &path)
	if got := result.Keys(); !reflect.DeepEqual(got, []string{"success", "rule_path", "is_valid", "validation_results"}) {
		t.Fatalf("keys = %v", got)
	}
	if valid, _ := result.Get("is_valid"); valid != false {
		t.Fatalf("is_valid = %v", valid)
	}
	results, _ := result.Get("validation_results")
	first := results.([]any)[0].(*entities.OrderedMap[any])
	if v, _ := first.Get("type"); v != "dependency_error" {
		t.Fatalf("type = %v", v)
	}
	if got := first.Keys(); !reflect.DeepEqual(got, []string{"type", "message"}) {
		t.Fatalf("entry keys = %v", got)
	}
}

// --- validate_dependencies (pure helpers) ---

func TestDraftValidateDependenciesInsights(t *testing.T) {
	uc := NewValidateDependenciesUseCase(nil)

	insights := uc.generateChainInsights(map[string]any{"chain_statistics": map[string]any{
		"total_dependencies": 0, "completed_dependencies": 0, "completion_percentage": 0}})
	first := insights[0].(*entities.OrderedMap[any])
	if v, _ := first.Get("type"); v != "no_dependencies" {
		t.Fatalf("type = %v", v)
	}

	insights = uc.generateChainInsights(map[string]any{"chain_statistics": map[string]any{
		"total_dependencies": 4, "completed_dependencies": 3, "completion_percentage": float64(75)}})
	first = insights[0].(*entities.OrderedMap[any])
	if v, _ := first.Get("type"); v != "partial_progress" {
		t.Fatalf("type = %v", v)
	}
	if v, _ := first.Get("message"); v != "Some dependencies are complete (3/4) - moderate progress" {
		t.Fatalf("message = %v", v)
	}
}

func TestDraftValidateDependenciesNextActions(t *testing.T) {
	uc := NewValidateDependenciesUseCase(nil)
	actions := uc.suggestNextActions(map[string]any{"can_proceed": true, "task_id": "t1"})
	first := actions[0].(*entities.OrderedMap[any])
	if v, _ := first.Get("command"); v != "Start working on task t1" {
		t.Fatalf("command = %v", v)
	}

	actions = uc.suggestNextActions(map[string]any{"can_proceed": false, "dependency_chain": []any{
		map[string]any{"is_completed": false, "status": "todo", "title": "Dep", "dependency_id": "d1"}}})
	first = actions[0].(*entities.OrderedMap[any])
	if v, _ := first.Get("action"); v != "work_on_dependency" {
		t.Fatalf("action = %v", v)
	}
	if got := first.Keys(); !reflect.DeepEqual(got, []string{"action", "priority", "description", "command"}) {
		t.Fatalf("keys = %v", got)
	}
}

func TestDraftValidateDependenciesOverall(t *testing.T) {
	uc := NewValidateDependenciesUseCase(nil)
	summary := entities.NewOrderedMap[any]()
	summary.Set("invalid_tasks", 2)
	summary.Set("tasks_with_issues", 1)
	recs := uc.generateOverallRecommendations(summary)
	if len(recs) != 2 {
		t.Fatalf("recs = %v", recs)
	}
	first := recs[0].(*entities.OrderedMap[any])
	if v, _ := first.Get("action"); v != "Fix 2 tasks with invalid dependencies" {
		t.Fatalf("action = %v", v)
	}
}

// --- batch_context_operations ---

func TestDraftBatchTransactionalStop(t *testing.T) {
	svc := &draftBatchContextService{createErr: context.DeadlineExceeded}
	batch := NewBatchContextOperations(svc)
	ops := []*BatchOperation{
		NewBatchOperation(BatchOperationTypeCreate, value_objects.ContextLevelProject, "c1"),
		NewBatchOperation(BatchOperationTypeCreate, value_objects.ContextLevelProject, "c2"),
	}
	results := batch.ExecuteBatch(context.Background(), ops, true, false, true, nil)
	if len(results) != 2 {
		t.Fatalf("results = %d", len(results))
	}
	if results[0].Success || results[0].Error == nil || *results[0].Error != "context deadline exceeded" {
		t.Fatalf("result0 = %+v", results[0])
	}
	if results[1].Error == nil || *results[1].Error != "Transaction rolled back" || results[1].ExecutionTimeMs != nil {
		t.Fatalf("result1 = %+v", results[1])
	}
}

func TestDraftBatchSequentialStop(t *testing.T) {
	svc := &draftBatchContextService{createErr: context.DeadlineExceeded}
	batch := NewBatchContextOperations(svc)
	ops := []*BatchOperation{
		NewBatchOperation(BatchOperationTypeCreate, value_objects.ContextLevelProject, "c1"),
		NewBatchOperation(BatchOperationTypeCreate, value_objects.ContextLevelProject, "c2"),
	}
	results := batch.ExecuteBatch(context.Background(), ops, false, false, true, nil)
	if results[1].Error == nil || *results[1].Error != "Skipped due to previous error" {
		t.Fatalf("result1 = %+v", results[1])
	}
}

func TestDraftBatchUpsert(t *testing.T) {
	svc := &draftBatchContextService{}
	batch := NewBatchContextOperations(svc)
	create := NewBatchOperation(BatchOperationTypeUpsert, value_objects.ContextLevelProject, "c1")
	results := batch.ExecuteBatch(context.Background(), []*BatchOperation{create}, false, false, true, nil)
	if len(svc.created) != 1 || len(svc.updated) != 0 {
		t.Fatalf("created=%v updated=%v", svc.created, svc.updated)
	}
	if !results[0].Success {
		t.Fatalf("result = %+v", results[0])
	}

	svc = &draftBatchContextService{getResult: map[string]any{"id": "c1"}}
	batch = NewBatchContextOperations(svc)
	upsert := NewBatchOperation(BatchOperationTypeUpsert, value_objects.ContextLevelProject, "c1")
	batch.ExecuteBatch(context.Background(), []*BatchOperation{upsert}, false, false, true, nil)
	if len(svc.created) != 0 || len(svc.updated) != 1 {
		t.Fatalf("created=%v updated=%v", svc.created, svc.updated)
	}
}

func TestDraftBatchBulkCreate(t *testing.T) {
	svc := &draftBatchContextService{}
	batch := NewBatchContextOperations(svc)
	entry := entities.NewOrderedMap[any]()
	entry.Set("context_id", "c1")
	entry.Set("data", map[string]any{"a": 1})
	results := batch.BulkCreate(context.Background(), []*entities.OrderedMap[any]{entry}, value_objects.ContextLevelProject, "u1", true)
	if len(results) != 1 || !results[0].Success || !reflect.DeepEqual(svc.created, []string{"c1"}) {
		t.Fatalf("results = %+v created = %v", results, svc.created)
	}
}

// --- context_templates ---

func TestDraftTemplateRegistry(t *testing.T) {
	registry := NewTemplateRegistry()
	if registry.Get("web_app_react") == nil || registry.Get("api_fastapi") == nil ||
		registry.Get("ml_model_training") == nil || registry.Get("task_feature_impl") == nil {
		t.Fatal("missing builtin template")
	}
	if registry.Get("nope") != nil {
		t.Fatal("unexpected template")
	}
	if got := registry.ListByLevel(value_objects.ContextLevelTask); len(got) != 1 || got[0].ID != "task_feature_impl" {
		t.Fatalf("by level = %v", got)
	}
	if got := registry.SearchByTags([]string{"react"}); len(got) != 1 || got[0].ID != "web_app_react" {
		t.Fatalf("by tags = %v", got)
	}
}

func TestDraftTemplateListShape(t *testing.T) {
	svc := NewContextTemplateService(&draftTemplateContextService{})
	list := svc.ListTemplates(nil, nil, nil)
	if len(list) != 4 {
		t.Fatalf("templates = %d", len(list))
	}
	wantKeys := []string{"id", "name", "description", "category", "level", "data_template", "author",
		"variables", "version", "tags", "created_at", "usage_count", "last_used_at"}
	if got := list[0].Keys(); !reflect.DeepEqual(got, wantKeys) {
		t.Fatalf("keys = %v", got)
	}
	if v, _ := list[0].Get("category"); v != "web_app" {
		t.Fatalf("category = %v", v)
	}

	category := TemplateCategoryMLModel
	filtered := svc.ListTemplates(&category, nil, nil)
	if len(filtered) != 1 {
		t.Fatalf("filtered = %d", len(filtered))
	}
}

func TestDraftTemplateApplyVariables(t *testing.T) {
	svc := NewContextTemplateService(&draftTemplateContextService{})
	template := svc.registry.Get("web_app_react")
	data, err := svc.applyVariables(template, nil)
	if err != nil {
		t.Fatal(err)
	}
	testingSection, _ := data.Get("testing")
	coverage, _ := testingSection.(*entities.OrderedMap[any]).Get("coverage_threshold")
	if coverage != int64(80) {
		t.Fatalf("coverage = %#v", coverage)
	}
	conventions, _ := data.Get("conventions")
	pattern, _ := conventions.(*entities.OrderedMap[any]).Get("state_management")
	if pattern != "Context + Hooks" {
		t.Fatalf("pattern = %v", pattern)
	}

	variables := entities.NewOrderedMap[any]()
	variables.Set("ui_library", "MUI")
	data, err = svc.applyVariables(template, variables)
	if err != nil {
		t.Fatal(err)
	}
	deps, _ := data.Get("dependencies")
	ui, _ := deps.(*entities.OrderedMap[any]).Get("ui_library")
	if ui != "MUI" {
		t.Fatalf("ui = %v", ui)
	}
}

func TestDraftTemplateApplyAndStats(t *testing.T) {
	fake := &draftTemplateContextService{}
	svc := NewContextTemplateService(fake)
	result, err := svc.ApplyTemplate(context.Background(), "task_feature_impl", "ctx1", "u1", nil, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(result, map[string]any{"ok": true}) {
		t.Fatalf("result = %v", result)
	}
	if fake.level != value_objects.ContextLevelTask || fake.contextID != "ctx1" {
		t.Fatalf("fake = %+v", fake)
	}
	if fake.data == nil || !fake.data.Has("_template") {
		t.Fatalf("data = %v", fake.data)
	}
	metaAny, _ := fake.data.Get("_template")
	meta := metaAny.(*entities.OrderedMap[any])
	if got := meta.Keys(); !reflect.DeepEqual(got, []string{"id", "name", "version", "applied_at"}) {
		t.Fatalf("meta keys = %v", got)
	}
	if template := svc.registry.Get("task_feature_impl"); template.UsageCount != 1 || template.LastUsedAt == nil {
		t.Fatalf("stats = %+v", template)
	}
}

func TestDraftTemplateRequiredVariable(t *testing.T) {
	svc := NewContextTemplateService(&draftTemplateContextService{})
	template := svc.CreateCustomTemplate("Custom", "desc", value_objects.ContextLevelTask,
		tmplOM("value", "{{required_var}}"), []*TemplateVariable{
			{Name: "required_var", Description: "required", DefaultValue: nil, Required: true},
		}, nil)
	if template == nil || len(template.Tags) != 0 {
		t.Fatalf("template = %+v", template)
	}
	if _, err := svc.ApplyTemplate(context.Background(), template.ID, "ctx", "u", nil, nil, nil); err == nil {
		t.Fatal("expected required variable error")
	}
}

func TestDraftTemplateExportImport(t *testing.T) {
	svc := NewContextTemplateService(&draftTemplateContextService{})
	exported, err := svc.ExportTemplate("api_fastapi")
	if err != nil {
		t.Fatal(err)
	}
	imported, err := svc.ImportTemplate(exported)
	if err != nil {
		t.Fatal(err)
	}
	original := svc.registry.Get("api_fastapi")
	if imported.Category != original.Category || imported.Level != original.Level ||
		imported.Version != original.Version || len(imported.Variables) != len(original.Variables) {
		t.Fatalf("imported = %+v", imported)
	}
	if _, err := svc.ExportTemplate("nope"); err == nil {
		t.Fatal("expected export error")
	}
}
