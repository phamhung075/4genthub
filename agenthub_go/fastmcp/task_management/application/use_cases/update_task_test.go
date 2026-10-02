package use_cases

import (
	"context"
	"errors"
	"reflect"
	"testing"

	dtotask "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// updateTaskFakeRepo overrides only the methods exercised by UpdateTaskUseCase.
type updateTaskFakeRepo struct {
	repositories.TaskRepository
	found   *entities.Task
	findErr error
	saved   *entities.Task
	saveErr error
}

func (f *updateTaskFakeRepo) FindByID(ctx context.Context, taskID value_objects.TaskId) (*entities.Task, error) {
	return f.found, f.findErr
}

func (f *updateTaskFakeRepo) Save(ctx context.Context, entity *entities.Task) (*entities.Task, error) {
	f.saved = entity
	if f.saveErr != nil {
		return nil, f.saveErr
	}
	return entity, nil
}

func updateTaskNewEntity(t *testing.T, idValue string) *entities.Task {
	t.Helper()
	id := createTaskMustID(t, idValue)
	status, _ := value_objects.NewTaskStatus("todo")
	priority, _ := value_objects.NewPriority("medium")
	description := "Original description"
	branch := "branch-1"
	entity, err := entities.CreateTask(entities.Task{
		ID:          &id,
		Title:       "Old Title",
		Description: description,
		Status:      &status,
		Priority:    &priority,
		GitBranchID: &branch,
		Assignees:   []string{"bob"},
		Labels:      []string{"old"},
	})
	if err != nil {
		t.Fatalf("CreateTask: %v", err)
	}
	return entity
}

func TestUpdateTaskUseCaseUpdatesFields(t *testing.T) {
	const idValue = "22222222-2222-2222-2222-222222222222"
	entity := updateTaskNewEntity(t, idValue)
	repo := &updateTaskFakeRepo{found: entity}
	uc := NewUpdateTaskUseCase(repo, nil)

	title := "New Title"
	description := "New description"
	status := "in_progress"
	priority := "high"
	details := "did work"
	effort := "3h"
	dueDate := "2025-12-31"
	contextID := "ctx-1"
	progress := 40

	resp, err := uc.Execute(context.Background(), dtotask.UpdateTaskRequest{
		TaskID:             idValue,
		Title:              &title,
		Description:        &description,
		Status:             &status,
		Priority:           &priority,
		Details:            &details,
		EstimatedEffort:    &effort,
		Assignees:          []string{"@alice"},
		Labels:             []string{"new"},
		DueDate:            &dueDate,
		ContextID:          &contextID,
		ProgressPercentage: &progress,
	})
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if !resp.Success || resp.Message != "Task updated successfully" {
		t.Fatalf("resp = %+v", resp)
	}
	if repo.saved != entity {
		t.Fatal("expected the found entity to be saved")
	}
	if entity.Title != "New Title" || entity.Description != "New description" {
		t.Fatalf("title/description = %q/%q", entity.Title, entity.Description)
	}
	if entity.Status.Value != "in_progress" || entity.Priority.Value != "high" {
		t.Fatalf("status/priority = %q/%q", entity.Status.Value, entity.Priority.Value)
	}
	if entity.EstimatedEffort != "3h" {
		t.Fatalf("estimated_effort = %q", entity.EstimatedEffort)
	}
	if !reflect.DeepEqual(entity.Assignees, []string{"@alice"}) {
		t.Fatalf("assignees = %v", entity.Assignees)
	}
	if !reflect.DeepEqual(entity.Labels, []string{"new"}) {
		t.Fatalf("labels = %v", entity.Labels)
	}
	if entity.DueDate == nil || *entity.DueDate != "2025-12-31T00:00:00+00:00" {
		t.Fatalf("due_date = %v", entity.DueDate)
	}
	if entity.OverallProgress != 40 || entity.OverallProgressIsFloat {
		t.Fatalf("overall_progress = %v float=%v", entity.OverallProgress, entity.OverallProgressIsFloat)
	}
	// context_id must survive append_progress (which clears it) because it is set last.
	if entity.ContextID == nil || *entity.ContextID != "ctx-1" {
		t.Fatalf("context_id = %v", entity.ContextID)
	}

	tr := resp.Task
	if tr.Details != "=== Progress 1 ===\ndid work" {
		t.Fatalf("details = %q", tr.Details)
	}
	if tr.ContextID == nil || *tr.ContextID != "ctx-1" {
		t.Fatalf("response context_id = %v", tr.ContextID)
	}
	if tr.ProgressPercentage != 40 {
		t.Fatalf("progress_percentage = %v", tr.ProgressPercentage)
	}
	if !reflect.DeepEqual(tr.Assignees, []string{"alice-agent"}) {
		t.Fatalf("response assignees = %v", tr.Assignees)
	}
	if !reflect.DeepEqual(tr.Labels, []string{"new"}) {
		t.Fatalf("response labels = %v", tr.Labels)
	}

	m, err := tr.ToDict()
	if err != nil {
		t.Fatalf("ToDict: %v", err)
	}
	if !reflect.DeepEqual(m.Keys(), createTaskResponseKeys()) {
		t.Fatalf("keys = %v", m.Keys())
	}
}

func TestUpdateTaskUseCaseTaskNotFound(t *testing.T) {
	repo := &updateTaskFakeRepo{}
	uc := NewUpdateTaskUseCase(repo, nil)

	const idValue = "11111111-1111-1111-1111-111111111111"
	resp, err := uc.Execute(context.Background(), dtotask.UpdateTaskRequest{TaskID: idValue})
	if resp != nil {
		t.Fatalf("response = %+v, want nil", resp)
	}
	var notFound *exceptions.TaskNotFoundError
	if !errors.As(err, &notFound) {
		t.Fatalf("err = %v, want *TaskNotFoundError", err)
	}
	want := "Task " + idValue + " not found"
	if err.Error() != want {
		t.Fatalf("message = %q, want %q", err.Error(), want)
	}
}

func TestUpdateTaskUseCaseUnchangedStatusIsSkipped(t *testing.T) {
	const idValue = "33333333-3333-3333-3333-333333333333"
	entity := updateTaskNewEntity(t, idValue)
	repo := &updateTaskFakeRepo{found: entity}
	uc := NewUpdateTaskUseCase(repo, nil)

	status := "todo"
	resp, err := uc.Execute(context.Background(), dtotask.UpdateTaskRequest{TaskID: idValue, Status: &status})
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if !resp.Success || entity.Status.Value != "todo" {
		t.Fatalf("status = %q", entity.Status.Value)
	}
}

func TestUpdateTaskUseCaseNilFieldsAreNotChanged(t *testing.T) {
	const idValue = "44444444-4444-4444-4444-444444444444"
	entity := updateTaskNewEntity(t, idValue)
	repo := &updateTaskFakeRepo{found: entity}
	uc := NewUpdateTaskUseCase(repo, nil)

	resp, err := uc.Execute(context.Background(), dtotask.UpdateTaskRequest{TaskID: idValue})
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if entity.Title != "Old Title" || !reflect.DeepEqual(entity.Assignees, []string{"bob"}) ||
		!reflect.DeepEqual(entity.Labels, []string{"old"}) {
		t.Fatalf("entity changed: %+v", entity)
	}
	if !reflect.DeepEqual(resp.Task.Assignees, []string{"bob-agent"}) {
		t.Fatalf("response assignees = %v", resp.Task.Assignees)
	}
}

func TestUpdateTaskUseCaseEmptySlicesClearFields(t *testing.T) {
	const idValue = "55555555-5555-5555-5555-555555555555"
	entity := updateTaskNewEntity(t, idValue)
	repo := &updateTaskFakeRepo{found: entity}
	uc := NewUpdateTaskUseCase(repo, nil)

	resp, err := uc.Execute(context.Background(), dtotask.UpdateTaskRequest{
		TaskID: idValue, Assignees: []string{}, Labels: []string{},
	})
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if len(entity.Assignees) != 0 || len(entity.Labels) != 0 {
		t.Fatalf("assignees = %v labels = %v", entity.Assignees, entity.Labels)
	}
	if len(resp.Task.Assignees) != 0 || len(resp.Task.Labels) != 0 {
		t.Fatalf("response assignees = %v labels = %v", resp.Task.Assignees, resp.Task.Labels)
	}
}

func TestUpdateTaskUseCaseContextIDWithoutDetails(t *testing.T) {
	const idValue = "66666666-6666-6666-6666-666666666666"
	entity := updateTaskNewEntity(t, idValue)
	repo := &updateTaskFakeRepo{found: entity}
	uc := NewUpdateTaskUseCase(repo, nil)

	contextID := "ctx-2"
	if _, err := uc.Execute(context.Background(), dtotask.UpdateTaskRequest{
		TaskID: idValue, ContextID: &contextID,
	}); err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if entity.ContextID == nil || *entity.ContextID != "ctx-2" {
		t.Fatalf("context_id = %v", entity.ContextID)
	}
}

func TestUpdateTaskUseCaseInvalidStatusReturnsValueError(t *testing.T) {
	const idValue = "77777777-7777-7777-7777-777777777777"
	entity := updateTaskNewEntity(t, idValue)
	repo := &updateTaskFakeRepo{found: entity}
	uc := NewUpdateTaskUseCase(repo, nil)

	bad := "bogus"
	resp, err := uc.Execute(context.Background(), dtotask.UpdateTaskRequest{TaskID: idValue, Status: &bad})
	if resp != nil {
		t.Fatalf("response = %+v, want nil", resp)
	}
	var ve *value_objects.ValueError
	if !errors.As(err, &ve) {
		t.Fatalf("err = %v, want *ValueError", err)
	}
}

func TestUpdateTaskUseCaseSaveErrorPropagates(t *testing.T) {
	const idValue = "88888888-8888-8888-8888-888888888888"
	entity := updateTaskNewEntity(t, idValue)
	repo := &updateTaskFakeRepo{found: entity, saveErr: errors.New("db down")}
	uc := NewUpdateTaskUseCase(repo, nil)

	resp, err := uc.Execute(context.Background(), dtotask.UpdateTaskRequest{TaskID: idValue})
	if resp != nil {
		t.Fatalf("response = %+v, want nil", resp)
	}
	if err == nil || err.Error() != "db down" {
		t.Fatalf("err = %v", err)
	}
}

func TestUpdateTaskUseCaseHooksSyncAndNotify(t *testing.T) {
	const idValue = "33333333-3333-3333-3333-333333333333"
	repo := &updateTaskFakeRepo{found: updateTaskNewEntity(t, idValue)}
	hooks := &createTaskFakeHooks{}
	uc := NewUpdateTaskUseCase(repo, nil).WithHooks(hooks)
	title := "Hooked"
	if _, err := uc.Execute(context.Background(), dtotask.UpdateTaskRequest{TaskID: idValue, Title: &title}); err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if !reflect.DeepEqual(hooks.calls, []string{"sync", "notify"}) {
		t.Fatalf("hook calls = %v", hooks.calls)
	}
}
