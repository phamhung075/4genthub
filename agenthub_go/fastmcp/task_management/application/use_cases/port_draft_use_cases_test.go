package use_cases

import (
	"context"
	"errors"
	"testing"

	dtostask "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/services"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// --- fakes -------------------------------------------------------------

type draftPortRuleRepo struct {
	repositories.RuleRepository
	exists  bool
	saveOK  bool
	getRule *entities.RuleContent
	saved   *entities.RuleContent
}

func (r *draftPortRuleRepo) RuleExists(ctx context.Context, rulePath string) (bool, error) {
	return r.exists, nil
}
func (r *draftPortRuleRepo) SaveRule(ctx context.Context, rule *entities.RuleContent) (bool, error) {
	r.saved = rule
	return r.saveOK, nil
}
func (r *draftPortRuleRepo) GetRule(ctx context.Context, rulePath string) (*entities.RuleContent, error) {
	return r.getRule, nil
}

type draftPortTaskRepo struct {
	repositories.TaskRepository
	byID            map[string]*entities.Task
	all             []*entities.Task
	criteria        []*entities.Task
	completedCounts map[string]int
}

func (r *draftPortTaskRepo) FindByID(ctx context.Context, id value_objects.TaskId) (*entities.Task, error) {
	return r.byID[id.Value], nil
}
func (r *draftPortTaskRepo) FindAll(ctx context.Context) ([]*entities.Task, error) {
	return r.all, nil
}
func (r *draftPortTaskRepo) FindByGitBranchID(ctx context.Context, branchID string) ([]*entities.Task, error) {
	return r.all, nil
}
func (r *draftPortTaskRepo) FindByCriteria(ctx context.Context, filters map[string]any, limit *int) ([]*entities.Task, error) {
	return r.criteria, nil
}
func (r *draftPortTaskRepo) GetCompletedSubtaskCounts(ctx context.Context, taskIDs []string) (map[string]int, error) {
	if r.completedCounts == nil {
		return map[string]int{}, nil
	}
	return r.completedCounts, nil
}
func (r *draftPortTaskRepo) Save(ctx context.Context, task *entities.Task) (*entities.Task, error) {
	return task, nil
}
func (r *draftPortTaskRepo) Delete(ctx context.Context, id value_objects.TaskId) (bool, error) {
	return true, nil
}

type draftPortSubtaskRepo struct {
	repositories.SubtaskRepository
	byID     map[string]*entities.Subtask
	parent   []*entities.Subtask
	removed  bool
	progress map[string]any
}

func (r *draftPortSubtaskRepo) FindByID(ctx context.Context, id string) (*entities.Subtask, error) {
	return r.byID[id], nil
}
func (r *draftPortSubtaskRepo) FindByParentTaskID(ctx context.Context, parent value_objects.TaskId) ([]*entities.Subtask, error) {
	return r.parent, nil
}
func (r *draftPortSubtaskRepo) RemoveSubtask(ctx context.Context, parentTaskID, subtaskID string) (bool, error) {
	return r.removed, nil
}
func (r *draftPortSubtaskRepo) GetSubtaskProgress(ctx context.Context, parent value_objects.TaskId) (map[string]any, error) {
	return r.progress, nil
}

type draftPortProjectRepo struct {
	services.CascadeProjectRepository
	project *entities.Project
}

func (r *draftPortProjectRepo) FindByID(ctx context.Context, projectID string) (*entities.Project, error) {
	return r.project, nil
}

type draftPortAIService struct {
	enhance *entities.OrderedMap[any]
	plan    *entities.OrderedMap[any]
}

func (s *draftPortAIService) EnhanceTaskCreation(ctx context.Context, request *dtostask.CreateTaskRequest,
	enableAIBreakdown, enableSmartAssignment bool) (*entities.OrderedMap[any], error) {
	return s.enhance, nil
}
func (s *draftPortAIService) CreateAIEnhancedTaskPlan(ctx context.Context, requirements, title, description,
	gitBranchID, planningContext string, autoCreateTasks bool, userID *string) (*entities.OrderedMap[any], error) {
	return s.plan, nil
}
func (s *draftPortAIService) AddAIInsightsToTaskResponse(ctx context.Context,
	taskResponse *entities.OrderedMap[any], action string) (*entities.OrderedMap[any], error) {
	return nil, nil
}
func (s *draftPortAIService) GenerateTaskInsights(ctx context.Context, title, description,
	action string) (*entities.OrderedMap[any], error) {
	return nil, nil
}

type draftPortAIFacade struct{}

func (f *draftPortAIFacade) GetTask(ctx context.Context, taskID string,
	includeContext bool) (*entities.OrderedMap[any], error) {
	return nil, nil
}

// --- helpers -----------------------------------------------------------

func draftPortKeys(t *testing.T, m *entities.OrderedMap[any]) []string {
	t.Helper()
	keys := []string{}
	for _, k := range m.Keys() {
		keys = append(keys, k)
	}
	return keys
}

func draftPortAssertKeys(t *testing.T, m *entities.OrderedMap[any], want []string) {
	t.Helper()
	got := draftPortKeys(t, m)
	if len(got) != len(want) {
		t.Fatalf("keys = %v, want %v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("keys = %v, want %v", got, want)
		}
	}
}

func draftPortNewTask(t *testing.T, id value_objects.TaskId, title string) *entities.Task {
	t.Helper()
	task, err := entities.NewTask(entities.Task{ID: &id, Title: title, Description: "desc"})
	if err != nil {
		t.Fatalf("NewTask: %v", err)
	}
	return task
}

// --- tests -------------------------------------------------------------

func TestDraftPortCreateRule(t *testing.T) {
	repo := &draftPortRuleRepo{saveOK: true}
	uc := NewCreateRuleUseCase(repo)
	out := uc.Execute(context.Background(), "rules/a.mdc", "hello",
		value_objects.RuleTypeCore, value_objects.RuleFormatMdc, nil)

	if v, _ := out.Get("success"); v != true {
		t.Fatalf("success = %v", v)
	}
	if repo.saved == nil {
		t.Fatal("rule not saved")
	}
	if repo.saved.Metadata.Size != 5 || repo.saved.Metadata.Version != "1.0" ||
		repo.saved.Metadata.Author != "rule_creator" {
		t.Fatalf("metadata = %+v", repo.saved.Metadata)
	}
	draftPortAssertKeys(t, out, []string{"success", "message", "rule_path", "rule_type", "rule_format"})

	existing := NewCreateRuleUseCase(&draftPortRuleRepo{exists: true})
	out2 := existing.Execute(context.Background(), "rules/a.mdc", "hello",
		value_objects.RuleTypeCore, value_objects.RuleFormatMdc, nil)
	if v, _ := out2.Get("success"); v != false {
		t.Fatalf("exists success = %v", v)
	}
	if v, _ := out2.Get("error"); v != "Rule already exists at path: rules/a.mdc" {
		t.Fatalf("exists error = %v", v)
	}
}

func TestDraftPortGetRule(t *testing.T) {
	sections := entities.NewOrderedMap[string]()
	sections.Set("s1", "c1")
	variables := entities.NewOrderedMap[any]()
	variables.Set("v", 1)
	repo := &draftPortRuleRepo{getRule: &entities.RuleContent{
		Metadata: &entities.RuleMetadata{Path: "rules/x.mdc", Type: value_objects.RuleTypeCore,
			Format: value_objects.RuleFormatMdc, Size: 3, Version: "2.0", Author: "a",
			Description: "d", Tags: []string{"t"}, Dependencies: []string{"dep"}},
		RawContent: "abc", ParsedContent: entities.NewOrderedMap[any](),
		Sections: sections, References: []string{"r"}, Variables: variables,
	}}
	out := NewGetRuleUseCase(repo).Execute(context.Background(), "rules/x.mdc")
	if v, _ := out.Get("success"); v != true {
		t.Fatalf("success = %v", v)
	}
	ruleValue, _ := out.Get("rule")
	rule, ok := ruleValue.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("rule type %T", ruleValue)
	}
	draftPortAssertKeys(t, rule, []string{"path", "type", "format", "content", "size", "version",
		"author", "description", "tags", "dependencies", "sections", "variables", "references"})

	missing := NewGetRuleUseCase(&draftPortRuleRepo{}).Execute(context.Background(), "rules/no.mdc")
	if v, _ := missing.Get("success"); v != false {
		t.Fatalf("missing success = %v", v)
	}
	if v, _ := missing.Get("error"); v != "Rule not found at path: rules/no.mdc" {
		t.Fatalf("missing error = %v", v)
	}
}

func TestDraftPortGetDependencies(t *testing.T) {
	idA := value_objects.GenerateNewTaskId()
	idB := value_objects.GenerateNewTaskId()
	taskA := draftPortNewTask(t, idA, "A")
	taskB := draftPortNewTask(t, idB, "B")
	done, _ := value_objects.NewTaskStatus("done")
	taskB.Status = &done
	taskA.Dependencies = []value_objects.TaskId{idB}

	repo := &draftPortTaskRepo{byID: map[string]*entities.Task{idA.Value: taskA, idB.Value: taskB}}
	out, err := NewGetDependenciesUseCase(repo).Execute(context.Background(), idA.Value)
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	draftPortAssertKeys(t, out, []string{"task_id", "dependency_ids", "dependencies", "can_start"})
	if v, _ := out.Get("can_start"); v != true {
		t.Fatalf("can_start = %v", v)
	}
	depsValue, _ := out.Get("dependencies")
	deps := depsValue.([]any)
	if len(deps) != 1 {
		t.Fatalf("deps len = %d", len(deps))
	}
	dep := deps[0].(*entities.OrderedMap[any])
	draftPortAssertKeys(t, dep, []string{"id", "title", "status", "priority"})
	if v, _ := dep.Get("status"); v != "done" {
		t.Fatalf("dep status = %v", v)
	}
}

func TestDraftPortGetSubtasks(t *testing.T) {
	parentID := value_objects.GenerateNewTaskId()
	subtaskID := value_objects.GenerateNewTaskId()
	parent := draftPortNewTask(t, parentID, "P")
	subtask, err := entities.NewSubtask(entities.Subtask{ID: &subtaskID, ParentTaskID: &parentID,
		Title: "S", Description: "sd"})
	if err != nil {
		t.Fatalf("NewSubtask: %v", err)
	}

	taskRepo := &draftPortTaskRepo{byID: map[string]*entities.Task{parentID.Value: parent}}
	subtaskRepo := &draftPortSubtaskRepo{parent: []*entities.Subtask{subtask}}

	out, err := NewGetSubtasksUseCase(taskRepo, subtaskRepo).Execute(context.Background(), parentID.Value)
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	draftPortAssertKeys(t, out, []string{"task_id", "subtasks", "progress"})
	subtasksValue, _ := out.Get("subtasks")
	subtasks := subtasksValue.([]any)
	if len(subtasks) != 1 {
		t.Fatalf("subtasks len = %d", len(subtasks))
	}
	progressValue, _ := out.Get("progress")
	progress := progressValue.(*entities.OrderedMap[any])
	if v, _ := progress.Get("total"); v != 1 {
		t.Fatalf("progress total = %v", v)
	}
	if v, _ := progress.Get("completed"); v != 0 {
		t.Fatalf("progress completed = %v", v)
	}
}

func TestDraftPortListTasks(t *testing.T) {
	taskID := value_objects.GenerateNewTaskId()
	task := draftPortNewTask(t, taskID, "T")
	repo := &draftPortTaskRepo{criteria: []*entities.Task{task},
		completedCounts: map[string]int{taskID.Value: 0}}
	status := "todo"
	request := &dtostask.ListTasksRequest{Status: &status}
	response, err := NewListTasksUseCase(repo, nil).Execute(context.Background(), request)
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if response.Count != 1 {
		t.Fatalf("count = %d", response.Count)
	}
	draftPortAssertKeys(t, response.FiltersApplied, []string{"status"})
}

func TestDraftPortRemoveSubtask(t *testing.T) {
	parentID := value_objects.GenerateNewTaskId()
	subtaskID := value_objects.GenerateNewTaskId()
	parent := draftPortNewTask(t, parentID, "P")
	parent.Subtasks = []string{subtaskID.Value}
	subtask, err := entities.NewSubtask(entities.Subtask{ID: &subtaskID, ParentTaskID: &parentID,
		Title: "S", Description: "sd"})
	if err != nil {
		t.Fatalf("NewSubtask: %v", err)
	}

	taskRepo := &draftPortTaskRepo{byID: map[string]*entities.Task{parentID.Value: parent}}
	subtaskRepo := &draftPortSubtaskRepo{
		byID:     map[string]*entities.Subtask{subtaskID.Value: subtask},
		removed:  true,
		progress: map[string]any{"total_subtasks": 1, "completed_subtasks": 0, "completion_percentage": 0},
	}

	out, err := NewRemoveSubtaskUseCase(taskRepo, subtaskRepo).Execute(context.Background(),
		parentID.Value, subtaskID.Value, nil)
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	draftPortAssertKeys(t, out, []string{"success", "subtask", "progress"})
	if v, _ := out.Get("success"); v != true {
		t.Fatalf("success = %v", v)
	}
	subtaskValue, _ := out.Get("subtask")
	sub := subtaskValue.(*entities.OrderedMap[any])
	draftPortAssertKeys(t, sub, []string{"id", "title"})
}

func TestDraftPortDeleteTaskNotFound(t *testing.T) {
	taskID := value_objects.GenerateNewTaskId()
	repo := &draftPortTaskRepo{byID: map[string]*entities.Task{}}
	uc := NewDeleteTaskUseCase(repo, nil, nil, nil, nil)
	out, err := uc.Execute(context.Background(), taskID.Value, true, nil)
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	draftPortAssertKeys(t, out, []string{"success", "task_deleted", "message"})
	if v, _ := out.Get("message"); v != "Task "+taskID.Value+" not found" {
		t.Fatalf("message = %v", v)
	}
}

func TestDraftPortDeleteProjectNotFound(t *testing.T) {
	uc := NewDeleteProjectUseCase(&draftPortProjectRepo{}, nil, nil, nil)
	_, err := uc.Execute(context.Background(), "missing", false)
	var notFound *exceptions.ResourceNotFoundException
	if !errors.As(err, &notFound) {
		t.Fatalf("err = %v", err)
	}
	if err.Error() != "Project missing not found" {
		t.Fatalf("message = %v", err.Error())
	}
}

func TestDraftPortAITaskCreation(t *testing.T) {
	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	service := &draftPortAIService{enhance: result}
	uc := NewAITaskCreationUseCase(nil, &draftPortAIFacade{}, service)
	request := NewAITaskCreationRequest("Title", "Desc", "branch-1")
	out := uc.Execute(context.Background(), request)
	draftPortAssertKeys(t, out, []string{"success", "ai_enhanced_features"})
	featuresValue, _ := out.Get("ai_enhanced_features")
	features := featuresValue.(*entities.OrderedMap[any])
	draftPortAssertKeys(t, features, []string{"breakdown_enabled", "smart_assignment_enabled",
		"auto_subtasks_enabled", "ai_requirements_provided"})
}

func TestDraftPortNextTaskNoTasks(t *testing.T) {
	repo := &draftPortTaskRepo{all: []*entities.Task{}}
	uc := NewNextTaskUseCase(repo, nil)
	userID := "user-1"
	response, err := uc.Execute(context.Background(), nil, nil, nil, nil, &userID, false)
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if response.HasNext || response.Message != "No tasks found. Create a task to get started!" {
		t.Fatalf("response = %+v", response)
	}
}

func TestDraftPortNextTaskRequiresUser(t *testing.T) {
	repo := &draftPortTaskRepo{all: []*entities.Task{}}
	uc := NewNextTaskUseCase(repo, nil)
	_, err := uc.Execute(context.Background(), nil, nil, nil, nil, nil, false)
	var valueErr *value_objects.ValueError
	if !errors.As(err, &valueErr) {
		t.Fatalf("err = %v", err)
	}
}

func TestDraftPortNextTaskNoSubtasks(t *testing.T) {
	task := draftPortNewTask(t, value_objects.GenerateNewTaskId(), "T")
	repo := &draftPortTaskRepo{all: []*entities.Task{task}}
	uc := NewNextTaskUseCase(repo, nil)
	userID := "user-1"
	response, err := uc.Execute(context.Background(), nil, nil, nil, nil, &userID, false)
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if !response.HasNext {
		t.Fatalf("has_next = false, message = %s", response.Message)
	}
	draftPortAssertKeys(t, response.NextItem, []string{"type", "task", "context"})
	if v, _ := response.NextItem.Get("type"); v != "task" {
		t.Fatalf("type = %v", v)
	}
}

func TestDraftPortNextTaskSubtaskQuirk(t *testing.T) {
	task := draftPortNewTask(t, value_objects.GenerateNewTaskId(), "T")
	task.Subtasks = []string{"sub-1"}
	repo := &draftPortTaskRepo{all: []*entities.Task{task}}
	uc := NewNextTaskUseCase(repo, nil)
	userID := "user-1"
	_, err := uc.Execute(context.Background(), nil, nil, nil, nil, &userID, false)
	if err == nil || err.Error() != "'str' object has no attribute 'get'" {
		t.Fatalf("err = %v", err)
	}
}
