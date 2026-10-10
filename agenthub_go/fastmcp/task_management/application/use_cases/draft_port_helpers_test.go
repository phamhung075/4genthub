package use_cases

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// Fakes for the drafting worker's use cases. They embed the repository
// interfaces so only the methods a test needs are implemented.

type draftTaskRepo struct {
	repositories.TaskRepository
	tasks   map[string]*entities.Task
	saved   []*entities.Task
	findErr error
	saveErr error
}

func (r *draftTaskRepo) FindByID(_ context.Context, id value_objects.TaskId) (*entities.Task, error) {
	if r.findErr != nil {
		return nil, r.findErr
	}
	return r.tasks[id.Value], nil
}

func (r *draftTaskRepo) Save(_ context.Context, t *entities.Task) (*entities.Task, error) {
	if r.saveErr != nil {
		return nil, r.saveErr
	}
	if r.tasks == nil {
		r.tasks = map[string]*entities.Task{}
	}
	if t.ID != nil {
		r.tasks[t.ID.Value] = t
	}
	r.saved = append(r.saved, t)
	return t, nil
}

func (r *draftTaskRepo) FindAll(context.Context) ([]*entities.Task, error) {
	out := make([]*entities.Task, 0, len(r.tasks))
	for _, t := range r.tasks {
		out = append(out, t)
	}
	return out, r.findErr
}

type draftSubtaskRepo struct {
	repositories.SubtaskRepository
	subtasks map[string]*entities.Subtask
	saved    []*entities.Subtask
	nextID   value_objects.TaskId
}

func (r *draftSubtaskRepo) GetNextID(context.Context, value_objects.TaskId) (value_objects.TaskId, error) {
	return r.nextID, nil
}

func (r *draftSubtaskRepo) Save(_ context.Context, s *entities.Subtask) (bool, error) {
	if r.subtasks == nil {
		r.subtasks = map[string]*entities.Subtask{}
	}
	if s.ID != nil {
		r.subtasks[s.ID.Value] = s
	}
	r.saved = append(r.saved, s)
	return true, nil
}

func (r *draftSubtaskRepo) FindByID(_ context.Context, id string) (*entities.Subtask, error) {
	return r.subtasks[id], nil
}

type draftContextRepo struct {
	repositories.ContextRepository
	exists           bool
	existsErr        error
	created          *entities.TaskContext
	createResult     map[string]any
	addInsightResult map[string]any
	addInsightErr    error
}

func (r *draftContextRepo) ContextExists(context.Context, string) (bool, error) {
	return r.exists, r.existsErr
}

func (r *draftContextRepo) AddInsight(context.Context, string, entities.ContextInsight) (map[string]any, error) {
	return r.addInsightResult, r.addInsightErr
}

func (r *draftContextRepo) CreateContext(_ context.Context, c *entities.TaskContext) (map[string]any, error) {
	r.created = c
	return r.createResult, nil
}

type draftProjectRepo struct {
	repositories.ProjectRepository
	projects []*entities.Project
	byID     map[string]*entities.Project
	findErr  error
}

func (r *draftProjectRepo) FindAll(context.Context) ([]*entities.Project, error) {
	return r.projects, r.findErr
}

func (r *draftProjectRepo) FindByID(_ context.Context, id string) (*entities.Project, error) {
	return r.byID[id], r.findErr
}

type draftRuleRepo struct {
	repositories.RuleRepository
	rules     map[string]*entities.RuleContent
	exists    map[string]bool
	deps      map[string][]string
	integrity map[string]any
	saveOK    bool
	saveErr   error
}

func (r *draftRuleRepo) GetRule(_ context.Context, path string) (*entities.RuleContent, error) {
	return r.rules[path], nil
}

func (r *draftRuleRepo) SaveRule(context.Context, *entities.RuleContent) (bool, error) {
	return r.saveOK, r.saveErr
}

func (r *draftRuleRepo) RuleExists(_ context.Context, path string) (bool, error) {
	return r.exists[path], nil
}

func (r *draftRuleRepo) GetRuleDependencies(_ context.Context, path string) ([]string, error) {
	return r.deps[path], nil
}

func (r *draftRuleRepo) ValidateRuleIntegrity(context.Context) (map[string]any, error) {
	return r.integrity, nil
}

type draftBatchContextService struct {
	created   []string
	updated   []string
	deleted   []string
	getResult map[string]any
	createErr error
	getErr    error
}

func (s *draftBatchContextService) CreateContext(_ context.Context, _ value_objects.ContextLevel, id string, data map[string]any, _, _, _ *string) (map[string]any, error) {
	s.created = append(s.created, id)
	return map[string]any{"id": id, "op": "create"}, s.createErr
}

func (s *draftBatchContextService) UpdateContext(_ context.Context, _ value_objects.ContextLevel, id string, data map[string]any, _ *string, _ bool) (map[string]any, error) {
	s.updated = append(s.updated, id)
	return map[string]any{"id": id, "op": "update"}, nil
}

func (s *draftBatchContextService) DeleteContext(_ context.Context, _ value_objects.ContextLevel, id string, _ *string) (map[string]any, error) {
	s.deleted = append(s.deleted, id)
	return map[string]any{"id": id, "op": "delete"}, nil
}

func (s *draftBatchContextService) GetContext(context.Context, value_objects.ContextLevel, string, *string, bool) (map[string]any, error) {
	return s.getResult, s.getErr
}

type draftTemplateContextService struct {
	data      *entities.OrderedMap[any]
	level     value_objects.ContextLevel
	contextID string
}

func (s *draftTemplateContextService) CreateContext(_ context.Context, level value_objects.ContextLevel, contextID string, data *entities.OrderedMap[any], _ string, _, _ *string) (map[string]any, error) {
	s.level = level
	s.contextID = contextID
	s.data = data
	return map[string]any{"ok": true}, nil
}

// draftNewTask builds a task with the given title.
func draftNewTask(t *testing.T, title string) *entities.Task {
	t.Helper()
	id := value_objects.GenerateNewTaskId()
	task, err := entities.NewTask(entities.Task{ID: &id, Title: title, Description: "description"})
	if err != nil {
		panic(err)
	}
	return task
}

// draftNewProject builds a project with the given name.
func draftNewProject(name string) *entities.Project {
	id := value_objects.GenerateNewProjectId()
	p, err := entities.NewProject(entities.Project{ID: &id, Name: name})
	if err != nil {
		panic(err)
	}
	return p
}
