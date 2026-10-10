package use_cases

import (
	"context"
	"errors"
	"fmt"
	"reflect"
	"strings"
	"testing"

	dtotask "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// createTaskFakeRepo overrides only the methods exercised by CreateTaskUseCase.
type createTaskFakeRepo struct {
	repositories.TaskRepository
	nextID    value_objects.TaskId
	nextIDErr error
	saved     *entities.Task
	saveNil   bool
	saveErr   error
}

func (f *createTaskFakeRepo) GetNextID(ctx context.Context) (value_objects.TaskId, error) {
	return f.nextID, f.nextIDErr
}

func (f *createTaskFakeRepo) Save(ctx context.Context, entity *entities.Task) (*entities.Task, error) {
	f.saved = entity
	if f.saveErr != nil {
		return nil, f.saveErr
	}
	if f.saveNil {
		return nil, nil
	}
	return entity, nil
}

func createTaskStrPtr(s string) *string { return &s }

func createTaskMustID(t *testing.T, value string) value_objects.TaskId {
	t.Helper()
	id, err := value_objects.NewTaskId(value)
	if err != nil {
		t.Fatalf("NewTaskId(%q): %v", value, err)
	}
	return id
}

func createTaskResponseKeys() []string {
	return []string{"id", "title", "description", "status", "priority", "details", "estimatedEffort",
		"assignees", "labels", "dependencies", "subtasks", "dueDate", "created_at", "updated_at",
		"git_branch_id", "project_id", "context_id", "context_data", "dependency_relationships",
		"progress_percentage", "subtask_count", "completed_subtasks"}
}

func TestCreateTaskUseCaseSuccess(t *testing.T) {
	id := createTaskMustID(t, "11111111-1111-1111-1111-111111111111")
	repo := &createTaskFakeRepo{nextID: id}
	uc := NewCreateTaskUseCase(repo, nil)

	desc := "The description"
	request, err := dtotask.NewCreateTaskRequest(dtotask.CreateTaskRequest{
		Title:           "My Task",
		GitBranchID:     "branch-1",
		Description:     &desc,
		Details:         "first steps",
		EstimatedEffort: "3h",
		Assignees:       []string{"coding-agent", "@bob"},
		Labels:          []string{"bug"},
	})
	if err != nil {
		t.Fatalf("NewCreateTaskRequest: %v", err)
	}

	resp, err := uc.Execute(context.Background(), *request)
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if !resp.Success {
		t.Fatalf("success = false, message = %q", resp.Message)
	}
	if resp.Message != "Task created successfully" {
		t.Fatalf("message = %q", resp.Message)
	}
	tr := resp.Task
	if tr == nil {
		t.Fatal("task is nil")
	}
	if tr.ID != id.Value {
		t.Fatalf("id = %q, want %q", tr.ID, id.Value)
	}
	if tr.Title != "My Task" {
		t.Fatalf("title = %q", tr.Title)
	}
	if tr.Description != "The description" {
		t.Fatalf("description = %q", tr.Description)
	}
	if tr.Status != "todo" {
		t.Fatalf("status = %q", tr.Status)
	}
	if tr.Priority != "medium" {
		t.Fatalf("priority = %q", tr.Priority)
	}
	if tr.EstimatedEffort != "3h" {
		t.Fatalf("estimatedEffort = %q", tr.EstimatedEffort)
	}
	if tr.Details != "=== Progress 1 ===\nfirst steps" {
		t.Fatalf("details = %q", tr.Details)
	}
	if !reflect.DeepEqual(tr.Assignees, []string{"@coding-agent", "@bob"}) {
		t.Fatalf("assignees = %v, want the stored values unchanged", tr.Assignees)
	}
	if !reflect.DeepEqual(tr.Labels, []string{"bug"}) {
		t.Fatalf("labels = %v", tr.Labels)
	}
	if tr.GitBranchID == nil || *tr.GitBranchID != "branch-1" {
		t.Fatalf("git_branch_id = %v", tr.GitBranchID)
	}
	if tr.ContextID != nil {
		t.Fatalf("context_id = %v, want nil (context facade dropped)", *tr.ContextID)
	}
	if repo.saved == nil || repo.saved.ContextID != nil {
		t.Fatalf("saved context_id = %v", repo.saved.ContextID)
	}

	m, err := tr.ToDict()
	if err != nil {
		t.Fatalf("ToDict: %v", err)
	}
	if !reflect.DeepEqual(m.Keys(), createTaskResponseKeys()) {
		t.Fatalf("keys = %v", m.Keys())
	}
}

func TestCreateTaskUseCaseDefaults(t *testing.T) {
	id := createTaskMustID(t, "22222222-2222-2222-2222-222222222222")
	repo := &createTaskFakeRepo{nextID: id}
	uc := NewCreateTaskUseCase(repo, nil)

	desc := "D"
	resp, err := uc.Execute(context.Background(), dtotask.CreateTaskRequest{
		Title: "T", GitBranchID: "branch-1", Description: &desc,
	})
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if resp.Task.Status != "todo" || resp.Task.Priority != "medium" {
		t.Fatalf("defaults = %q/%q", resp.Task.Status, resp.Task.Priority)
	}
}

// TestCreateTaskUseCaseRefusesOverLongContent is the anti-truncation test.
//
// The create path used to slice the title at 200 characters and the description at 2000 SILENTLY: a
// create came back success with a truncated row stored and nothing saying anything had been cut,
// while the update path refused the same input loudly. The limits belong to the entity, so an
// over-limit create must return the entity's error - the message update reports - and store nothing.
func TestCreateTaskUseCaseRefusesOverLongContent(t *testing.T) {
	id := createTaskMustID(t, "22222222-2222-2222-2222-222222222222")
	repo := &createTaskFakeRepo{nextID: id}
	uc := NewCreateTaskUseCase(repo, nil)

	longTitle := strings.Repeat("a", 250)
	longDesc := strings.Repeat("b", 2100)

	cases := []struct {
		name  string
		title string
		desc  string
		want  string
	}{
		{"title over 200", longTitle, "D", "Task title cannot exceed 200 characters"},
		{"description over 2000", "T", longDesc, "Task description cannot exceed 2000 characters"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			desc := tc.desc
			resp, err := uc.Execute(context.Background(), dtotask.CreateTaskRequest{
				Title: tc.title, GitBranchID: "branch-1", Description: &desc,
			})
			if resp != nil {
				t.Fatalf("response = %+v, want nil: a refused create returns the entity's error", resp)
			}
			var ve *value_objects.ValueError
			if !errors.As(err, &ve) {
				t.Fatalf("err = %v, want *ValueError", err)
			}
			if ve.Msg != tc.want {
				t.Fatalf("message = %q, want %q", ve.Msg, tc.want)
			}
			if repo.saved != nil {
				t.Fatal("a refused create must not save a row")
			}
		})
	}

	// The boundary, so the test pins 2000 rather than something smaller: exactly at the limit is
	// accepted and stored intact.
	atLimit := strings.Repeat("c", 2000)
	resp, err := uc.Execute(context.Background(), dtotask.CreateTaskRequest{
		Title: "T", GitBranchID: "branch-1", Description: &atLimit,
	})
	if err != nil {
		t.Fatalf("Execute at the limit: %v", err)
	}
	if !resp.Success || len([]rune(resp.Task.Description)) != 2000 {
		t.Fatalf("at-limit create: success=%v length=%d", resp.Success, len([]rune(resp.Task.Description)))
	}
	if repo.saved == nil || len([]rune(repo.saved.Description)) != 2000 {
		t.Fatal("the saved entity does not carry the full 2000 characters")
	}
}

func TestCreateTaskUseCaseInvalidStatusReRaisesValueError(t *testing.T) {
	id := createTaskMustID(t, "33333333-3333-3333-3333-333333333333")
	repo := &createTaskFakeRepo{nextID: id}
	uc := NewCreateTaskUseCase(repo, nil)

	bad := "bogus"
	desc := "D"
	resp, err := uc.Execute(context.Background(), dtotask.CreateTaskRequest{
		Title: "T", GitBranchID: "b", Description: &desc, Status: &bad,
	})
	if resp != nil {
		t.Fatalf("response = %+v, want nil", resp)
	}
	var ve *value_objects.ValueError
	if !errors.As(err, &ve) {
		t.Fatalf("err = %v, want *ValueError", err)
	}
	want := "Invalid task status: bogus. Valid statuses: todo, in_progress, blocked, review, testing, done, cancelled, archived"
	if ve.Msg != want {
		t.Fatalf("message = %q", ve.Msg)
	}
}

func TestCreateTaskUseCaseSaveFailureReturnsErrorResponse(t *testing.T) {
	id := createTaskMustID(t, "44444444-4444-4444-4444-444444444444")
	repo := &createTaskFakeRepo{nextID: id, saveNil: true}
	uc := NewCreateTaskUseCase(repo, nil)

	desc := "D"
	resp, err := uc.Execute(context.Background(), dtotask.CreateTaskRequest{
		Title: "T", GitBranchID: "b", Description: &desc,
	})
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if resp.Success {
		t.Fatal("success = true")
	}
	want := "Failed to save task to database. This may be due to an invalid git_branch_id or database constraint violation."
	if resp.Message != want {
		t.Fatalf("message = %q", resp.Message)
	}
}

func TestCreateTaskUseCaseSkipsInvalidDependencies(t *testing.T) {
	id := createTaskMustID(t, "55555555-5555-5555-5555-555555555555")
	repo := &createTaskFakeRepo{nextID: id}
	uc := NewCreateTaskUseCase(repo, nil)

	desc := "D"
	_, err := uc.Execute(context.Background(), dtotask.CreateTaskRequest{
		Title: "T", GitBranchID: "b", Description: &desc,
		Dependencies: []string{"", "   ", "not a valid id!!", "dep-1"},
	})
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if repo.saved == nil {
		t.Fatal("task was not saved")
	}
	if got := repo.saved.GetDependencyIDs(); !reflect.DeepEqual(got, []string{"dep-1"}) {
		t.Fatalf("dependencies = %v", got)
	}
}

func TestCreateTaskUseCaseGenericErrorBecomesErrorResponse(t *testing.T) {
	repo := &createTaskFakeRepo{nextIDErr: errors.New("boom")}
	uc := NewCreateTaskUseCase(repo, nil)

	resp, err := uc.Execute(context.Background(), dtotask.CreateTaskRequest{Title: "T", GitBranchID: "b"})
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if resp.Success || resp.Message != "Failed to create task: boom" {
		t.Fatalf("resp = %+v", resp)
	}
}

func TestCreateTaskUseCaseSaveValueErrorIsReRaised(t *testing.T) {
	id := createTaskMustID(t, "66666666-6666-6666-6666-666666666666")
	repo := &createTaskFakeRepo{nextID: id, saveErr: value_objects.ValueErrorf("bad save")}
	uc := NewCreateTaskUseCase(repo, nil)

	desc := "D"
	resp, err := uc.Execute(context.Background(), dtotask.CreateTaskRequest{
		Title: "T", GitBranchID: "b", Description: &desc,
	})
	if resp != nil {
		t.Fatalf("response = %+v, want nil", resp)
	}
	var ve *value_objects.ValueError
	if !errors.As(err, &ve) || ve.Msg != "bad save" {
		t.Fatalf("err = %v", err)
	}
}

type createTaskFakeHooks struct {
	contextOK bool
	calls     []string
}

func (h *createTaskFakeHooks) CreateTaskContext(ctx context.Context, task *entities.Task, userID string, projectID *string, gitBranchID string) (bool, error) {
	h.calls = append(h.calls, "context")
	return h.contextOK, nil
}

func (h *createTaskFakeHooks) SyncTaskMetadata(ctx context.Context, taskID string, task *entities.Task, userID string) error {
	h.calls = append(h.calls, "sync")
	return nil
}

func (h *createTaskFakeHooks) NotifyTaskEvent(ctx context.Context, eventType string, task *entities.Task, response *dtotask.TaskResponse, userID *string, gitBranchID string) {
	h.calls = append(h.calls, "notify")
}

func TestCreateTaskUseCaseHooksSetContextIDAndNotify(t *testing.T) {
	id := createTaskMustID(t, "11111111-1111-1111-1111-111111111111")
	repo := &createTaskFakeRepo{nextID: id}
	hooks := &createTaskFakeHooks{contextOK: true}
	uc := NewCreateTaskUseCase(repo, nil).WithHooks(hooks)
	user := "user-1"
	request, err := dtotask.NewCreateTaskRequest(dtotask.CreateTaskRequest{Title: "T", Description: createTaskStrPtr("d"), GitBranchID: "branch-1", UserID: &user})
	if err != nil {
		t.Fatal(err)
	}
	resp, err := uc.Execute(context.Background(), *request)
	if err != nil || !resp.Success {
		t.Fatalf("execute: %v %v", err, resp)
	}
	if got := fmt.Sprint(hooks.calls); got != "[context sync notify]" {
		t.Fatalf("calls = %s", got)
	}
	if repo.saved.ContextID == nil || *repo.saved.ContextID != id.Value {
		t.Fatalf("context_id not set: %v", repo.saved.ContextID)
	}
	if resp.Task.ContextID == nil || *resp.Task.ContextID != id.Value {
		t.Fatalf("response context_id: %v", resp.Task.ContextID)
	}

	// failed context creation: no context_id, no sync, notification still sent.
	hooks2 := &createTaskFakeHooks{contextOK: false}
	repo2 := &createTaskFakeRepo{nextID: id}
	uc = NewCreateTaskUseCase(repo2, nil).WithHooks(hooks2)
	if _, err := uc.Execute(context.Background(), *request); err != nil {
		t.Fatal(err)
	}
	if got := fmt.Sprint(hooks2.calls); got != "[context notify]" {
		t.Fatalf("calls = %s", got)
	}

	// no user: context creation is skipped (UserAuthenticationRequiredError is swallowed).
	hooks3 := &createTaskFakeHooks{contextOK: true}
	uc = NewCreateTaskUseCase(&createTaskFakeRepo{nextID: id}, nil).WithHooks(hooks3)
	noUser, _ := dtotask.NewCreateTaskRequest(dtotask.CreateTaskRequest{Title: "T", Description: createTaskStrPtr("d"), GitBranchID: "branch-1"})
	if _, err := uc.Execute(context.Background(), *noUser); err != nil {
		t.Fatal(err)
	}
	if got := fmt.Sprint(hooks3.calls); got != "[notify]" {
		t.Fatalf("calls = %s", got)
	}
}
