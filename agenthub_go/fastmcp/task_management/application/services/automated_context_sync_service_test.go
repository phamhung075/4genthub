package services

import (
	"context"
	"errors"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

type zpAutoSyncCall struct {
	taskID, userID, projectID, gitBranchName string
}

type zpAutoSyncFakeSyncer struct {
	calls  []zpAutoSyncCall
	result any
	err    error
}

func (f *zpAutoSyncFakeSyncer) SyncContextAndGetTask(ctx context.Context, taskID, userID, projectID, gitBranchName string) (any, error) {
	f.calls = append(f.calls, zpAutoSyncCall{taskID: taskID, userID: userID, projectID: projectID, gitBranchName: gitBranchName})
	return f.result, f.err
}

type zpAutoSyncFakeTaskRepo struct {
	repositories.TaskRepository
	tasks   map[string]*entities.Task
	findErr error
}

func (f *zpAutoSyncFakeTaskRepo) FindByID(ctx context.Context, taskID value_objects.TaskId) (*entities.Task, error) {
	if f.findErr != nil {
		return nil, f.findErr
	}
	return f.tasks[taskID.Value], nil
}

type zpAutoSyncFakeSubtaskRepo struct {
	repositories.SubtaskRepository
	subtasks []*entities.Subtask
	err      error
}

func (f *zpAutoSyncFakeSubtaskRepo) FindByParentTaskID(ctx context.Context, parentTaskID value_objects.TaskId) ([]*entities.Subtask, error) {
	if f.err != nil {
		return nil, f.err
	}
	return f.subtasks, nil
}

func zpAutoSyncTaskFixture(t *testing.T, id string) *entities.Task {
	t.Helper()
	taskID, err := value_objects.NewTaskId(id)
	if err != nil {
		t.Fatalf("task id %q: %v", id, err)
	}
	return &entities.Task{ID: &taskID}
}

func zpAutoSyncSubtaskFixture(t *testing.T, completed bool) *entities.Subtask {
	t.Helper()
	statusName := "todo"
	progress := 0
	if completed {
		statusName = "done"
		progress = 100
	}
	status, err := value_objects.NewTaskStatus(statusName)
	if err != nil {
		t.Fatalf("status: %v", err)
	}
	return &entities.Subtask{Status: &status, ProgressPercentage: progress}
}

func zpAutoSyncWithProjectID(t *testing.T, projectID string) {
	t.Helper()
	original := zpAutoSyncTaskProjectID
	zpAutoSyncTaskProjectID = func(*entities.Task) *string { return &projectID }
	t.Cleanup(func() { zpAutoSyncTaskProjectID = original })
}

func zpAutoSyncGet(t *testing.T, m *entities.OrderedMap[any], key string) any {
	t.Helper()
	value, ok := m.Get(key)
	if !ok {
		t.Fatalf("missing key %q", key)
	}
	return value
}

func TestAutomatedContextSyncService_Init(t *testing.T) {
	repo := &zpAutoSyncFakeTaskRepo{}
	syncer := &zpAutoSyncFakeSyncer{}
	svc := NewAutomatedContextSyncService(repo, nil, nil, syncer)
	if svc.TaskRepository != repo {
		t.Fatalf("task repository not stored")
	}
	if svc.SubtaskRepository != nil {
		t.Fatalf("subtask repository = %#v, want nil", svc.SubtaskRepository)
	}
	if svc.UserID != nil {
		t.Fatalf("user id = %#v, want nil", svc.UserID)
	}
	if svc.ContextSyncService != syncer {
		t.Fatalf("context sync service not stored")
	}
}

func TestAutomatedContextSyncService_WithUser(t *testing.T) {
	repo := &zpAutoSyncFakeTaskRepo{}
	syncer := &zpAutoSyncFakeSyncer{}
	original := NewAutomatedContextSyncService(repo, nil, nil, syncer)
	scoped := original.WithUser("test_user_456")
	if scoped.UserID == nil || *scoped.UserID != "test_user_456" {
		t.Fatalf("user id = %#v", scoped.UserID)
	}
	if scoped == original {
		t.Fatalf("with_user did not create a new instance")
	}
	if scoped.TaskRepository != repo || scoped.ContextSyncService != syncer {
		t.Fatalf("dependencies not carried over")
	}
}

func TestAutomatedContextSyncService_GetUserScopedRepository(t *testing.T) {
	svc := NewAutomatedContextSyncService(nil, nil, zpAutoSyncStrPtr("test_user"), nil)
	repo := struct{ Name string }{Name: "repo"}
	if svc.getUserScopedRepository(repo) != repo {
		t.Fatalf("repository not returned unchanged")
	}
	if svc.getUserScopedRepository(nil) != nil {
		t.Fatalf("nil repository not returned unchanged")
	}
}

func TestAutomatedContextSyncService_SyncTaskContextAfterUpdateWithoutProjectID(t *testing.T) {
	syncer := &zpAutoSyncFakeSyncer{result: map[string]any{"success": true}}
	svc := NewAutomatedContextSyncService(&zpAutoSyncFakeTaskRepo{}, nil, nil, syncer)
	task := zpAutoSyncTaskFixture(t, "task-1")

	if svc.SyncTaskContextAfterUpdate(context.Background(), task, "update") {
		t.Fatalf("expected false without project_id")
	}
	if len(syncer.calls) != 0 {
		t.Fatalf("syncer was called: %v", syncer.calls)
	}
}

func TestAutomatedContextSyncService_SyncTaskContextAfterUpdateNilSyncer(t *testing.T) {
	svc := NewAutomatedContextSyncService(&zpAutoSyncFakeTaskRepo{}, nil, nil, nil)
	zpAutoSyncWithProjectID(t, "project-456")
	if svc.SyncTaskContextAfterUpdate(context.Background(), zpAutoSyncTaskFixture(t, "task-1"), "update") {
		t.Fatalf("expected false with nil syncer")
	}
}

func TestAutomatedContextSyncService_SyncTaskContextAfterUpdateSuccess(t *testing.T) {
	zpAutoSyncWithProjectID(t, "project-456")
	syncer := &zpAutoSyncFakeSyncer{result: map[string]any{"success": true}}
	svc := NewAutomatedContextSyncService(&zpAutoSyncFakeTaskRepo{}, nil, nil, syncer)
	task := zpAutoSyncTaskFixture(t, "task-123")

	if !svc.SyncTaskContextAfterUpdate(context.Background(), task, "create") {
		t.Fatalf("expected true")
	}
	if len(syncer.calls) != 1 {
		t.Fatalf("calls = %v", syncer.calls)
	}
	call := syncer.calls[0]
	if call.taskID != "task-123" || call.userID != "system_create" || call.projectID != "project-456" || call.gitBranchName != "main" {
		t.Fatalf("call = %#v", call)
	}
}

func TestAutomatedContextSyncService_SyncTaskContextAfterUpdateFalsyResult(t *testing.T) {
	zpAutoSyncWithProjectID(t, "project-456")
	syncer := &zpAutoSyncFakeSyncer{result: nil}
	svc := NewAutomatedContextSyncService(&zpAutoSyncFakeTaskRepo{}, nil, nil, syncer)
	if svc.SyncTaskContextAfterUpdate(context.Background(), zpAutoSyncTaskFixture(t, "task-1"), "update") {
		t.Fatalf("expected false for nil result")
	}
	syncer.result = map[string]any{}
	if svc.SyncTaskContextAfterUpdate(context.Background(), zpAutoSyncTaskFixture(t, "task-1"), "update") {
		t.Fatalf("expected false for empty dict result")
	}
}

func TestAutomatedContextSyncService_SyncTaskContextAfterUpdateError(t *testing.T) {
	zpAutoSyncWithProjectID(t, "project-456")
	syncer := &zpAutoSyncFakeSyncer{err: errors.New("sync failed")}
	svc := NewAutomatedContextSyncService(&zpAutoSyncFakeTaskRepo{}, nil, nil, syncer)
	if svc.SyncTaskContextAfterUpdate(context.Background(), zpAutoSyncTaskFixture(t, "task-1"), "update") {
		t.Fatalf("expected false on syncer error")
	}
}

func TestAutomatedContextSyncService_SyncTaskContextAfterUpdateSyncWrapper(t *testing.T) {
	zpAutoSyncWithProjectID(t, "project-456")
	syncer := &zpAutoSyncFakeSyncer{result: true}
	svc := NewAutomatedContextSyncService(&zpAutoSyncFakeTaskRepo{}, nil, nil, syncer)
	if !svc.SyncTaskContextAfterUpdateSync(context.Background(), zpAutoSyncTaskFixture(t, "task-1"), "update") {
		t.Fatalf("wrapper returned false")
	}
}

func TestAutomatedContextSyncService_SyncParentContextAfterSubtaskUpdate(t *testing.T) {
	zpAutoSyncWithProjectID(t, "project-456")
	syncer := &zpAutoSyncFakeSyncer{result: true}
	subtaskRepo := &zpAutoSyncFakeSubtaskRepo{subtasks: []*entities.Subtask{zpAutoSyncSubtaskFixture(t, true)}}
	svc := NewAutomatedContextSyncService(&zpAutoSyncFakeTaskRepo{}, subtaskRepo, nil, syncer)
	parent := zpAutoSyncTaskFixture(t, "task-1")

	if !svc.SyncParentContextAfterSubtaskUpdate(context.Background(), parent, nil, "subtask_update") {
		t.Fatalf("expected true")
	}
	if len(syncer.calls) != 1 || syncer.calls[0].userID != "system_parent_subtask_update" {
		t.Fatalf("calls = %#v", syncer.calls)
	}
	if !svc.SyncParentContextAfterSubtaskUpdateSync(context.Background(), parent, nil, "subtask_update") {
		t.Fatalf("sync wrapper returned false")
	}
}

func TestAutomatedContextSyncService_CalculateSubtaskProgressNoRepository(t *testing.T) {
	svc := NewAutomatedContextSyncService(&zpAutoSyncFakeTaskRepo{}, nil, nil, nil)
	if got := svc.CalculateSubtaskProgress(context.Background(), zpAutoSyncTaskFixture(t, "task-1")); got != nil {
		t.Fatalf("got %#v, want nil", got)
	}
}

func TestAutomatedContextSyncService_CalculateSubtaskProgressNoSubtasks(t *testing.T) {
	svc := NewAutomatedContextSyncService(&zpAutoSyncFakeTaskRepo{}, &zpAutoSyncFakeSubtaskRepo{}, nil, nil)
	result := svc.CalculateSubtaskProgress(context.Background(), zpAutoSyncTaskFixture(t, "task-1"))
	if result == nil {
		t.Fatalf("got nil")
	}
	zpCtxInhKeyOrder(t, result, []string{"total_subtasks", "completed_subtasks", "progress_percentage", "can_complete_parent"})
	zpAutoSyncAssert(t, zpAutoSyncGet(t, result, "total_subtasks"), 0)
	zpAutoSyncAssert(t, zpAutoSyncGet(t, result, "completed_subtasks"), 0)
	zpAutoSyncAssert(t, zpAutoSyncGet(t, result, "progress_percentage"), 100)
	zpAutoSyncAssert(t, zpAutoSyncGet(t, result, "can_complete_parent"), true)
}

func TestAutomatedContextSyncService_CalculateSubtaskProgressWithSubtasks(t *testing.T) {
	subtasks := []*entities.Subtask{
		zpAutoSyncSubtaskFixture(t, true),
		zpAutoSyncSubtaskFixture(t, true),
		zpAutoSyncSubtaskFixture(t, false),
		zpAutoSyncSubtaskFixture(t, false),
		zpAutoSyncSubtaskFixture(t, false),
	}
	svc := NewAutomatedContextSyncService(&zpAutoSyncFakeTaskRepo{}, &zpAutoSyncFakeSubtaskRepo{subtasks: subtasks}, nil, nil)
	result := svc.CalculateSubtaskProgress(context.Background(), zpAutoSyncTaskFixture(t, "task-1"))
	if result == nil {
		t.Fatalf("got nil")
	}
	zpCtxInhKeyOrder(t, result, []string{"total_subtasks", "completed_subtasks", "incomplete_subtasks", "progress_percentage", "can_complete_parent", "last_updated"})
	zpAutoSyncAssert(t, zpAutoSyncGet(t, result, "total_subtasks"), 5)
	zpAutoSyncAssert(t, zpAutoSyncGet(t, result, "completed_subtasks"), 2)
	zpAutoSyncAssert(t, zpAutoSyncGet(t, result, "incomplete_subtasks"), 3)
	zpAutoSyncAssert(t, zpAutoSyncGet(t, result, "progress_percentage"), 40.0)
	zpAutoSyncAssert(t, zpAutoSyncGet(t, result, "can_complete_parent"), false)
	if _, ok := result.Get("last_updated"); !ok {
		t.Fatalf("missing last_updated")
	}
}

func TestAutomatedContextSyncService_CalculateSubtaskProgressAllCompleted(t *testing.T) {
	subtasks := []*entities.Subtask{
		zpAutoSyncSubtaskFixture(t, true),
		zpAutoSyncSubtaskFixture(t, true),
		zpAutoSyncSubtaskFixture(t, true),
	}
	svc := NewAutomatedContextSyncService(&zpAutoSyncFakeTaskRepo{}, &zpAutoSyncFakeSubtaskRepo{subtasks: subtasks}, nil, nil)
	result := svc.CalculateSubtaskProgress(context.Background(), zpAutoSyncTaskFixture(t, "task-1"))
	zpAutoSyncAssert(t, zpAutoSyncGet(t, result, "total_subtasks"), 3)
	zpAutoSyncAssert(t, zpAutoSyncGet(t, result, "completed_subtasks"), 3)
	zpAutoSyncAssert(t, zpAutoSyncGet(t, result, "progress_percentage"), 100.0)
	zpAutoSyncAssert(t, zpAutoSyncGet(t, result, "can_complete_parent"), true)
}

func TestAutomatedContextSyncService_CalculateSubtaskProgressError(t *testing.T) {
	svc := NewAutomatedContextSyncService(&zpAutoSyncFakeTaskRepo{}, &zpAutoSyncFakeSubtaskRepo{err: errors.New("db error")}, nil, nil)
	if got := svc.CalculateSubtaskProgress(context.Background(), zpAutoSyncTaskFixture(t, "task-1")); got != nil {
		t.Fatalf("got %#v, want nil", got)
	}
}

func TestAutomatedContextSyncService_SyncMultipleTasks(t *testing.T) {
	zpAutoSyncWithProjectID(t, "project-456")
	taskIDs := []string{"task-1", "task-2", "task-3"}
	repo := &zpAutoSyncFakeTaskRepo{tasks: map[string]*entities.Task{}}
	for _, id := range taskIDs {
		repo.tasks[id] = zpAutoSyncTaskFixture(t, id)
	}
	syncer := &zpAutoSyncFakeSyncer{result: map[string]any{"success": true}}
	svc := NewAutomatedContextSyncService(repo, nil, nil, syncer)

	results := svc.SyncMultipleTasks(context.Background(), taskIDs)
	if !value_objects.PyEqual(results.Keys(), taskIDs) {
		t.Fatalf("keys = %v", results.Keys())
	}
	for _, id := range taskIDs {
		if !zpAutoSyncGetBool(t, results, id) {
			t.Fatalf("task %s not synced", id)
		}
	}
}

func TestAutomatedContextSyncService_SyncMultipleTasksNotFound(t *testing.T) {
	repo := &zpAutoSyncFakeTaskRepo{tasks: map[string]*entities.Task{
		"task-1": zpAutoSyncTaskFixture(t, "task-1"),
		"task-3": zpAutoSyncTaskFixture(t, "task-3"),
	}}
	syncer := &zpAutoSyncFakeSyncer{result: true}
	svc := NewAutomatedContextSyncService(repo, nil, nil, syncer)

	results := svc.SyncMultipleTasks(context.Background(), []string{"task-1", "task-2", "task-3"})
	if !value_objects.PyEqual(results.Keys(), []string{"task-1", "task-2", "task-3"}) {
		t.Fatalf("keys = %v", results.Keys())
	}
	if zpAutoSyncGetBool(t, results, "task-1") || zpAutoSyncGetBool(t, results, "task-2") || zpAutoSyncGetBool(t, results, "task-3") {
		t.Fatalf("expected all false without project_id")
	}
}

func TestAutomatedContextSyncService_SyncMultipleTasksInvalidID(t *testing.T) {
	svc := NewAutomatedContextSyncService(&zpAutoSyncFakeTaskRepo{}, nil, nil, &zpAutoSyncFakeSyncer{result: true})
	results := svc.SyncMultipleTasks(context.Background(), []string{"task_1", "task-2"})
	zpAutoSyncAssert(t, zpAutoSyncGetBool(t, results, "task_1"), false)
	zpAutoSyncAssert(t, zpAutoSyncGetBool(t, results, "task-2"), false)
}

func TestAutomatedContextSyncService_GetSyncStatistics(t *testing.T) {
	svc := NewAutomatedContextSyncService(&zpAutoSyncFakeTaskRepo{}, &zpAutoSyncFakeSubtaskRepo{}, nil, &zpAutoSyncFakeSyncer{})
	stats := svc.GetSyncStatistics()
	zpCtxInhKeyOrder(t, stats, []string{"service_status", "sync_service_available", "subtask_repository_available", "last_health_check", "features"})
	zpAutoSyncAssert(t, zpAutoSyncGet(t, stats, "service_status"), "active")
	zpAutoSyncAssert(t, zpAutoSyncGet(t, stats, "sync_service_available"), true)
	zpAutoSyncAssert(t, zpAutoSyncGet(t, stats, "subtask_repository_available"), true)
	features := zpAutoSyncGet(t, stats, "features").(*entities.OrderedMap[any])
	zpCtxInhKeyOrder(t, features, []string{"task_context_sync", "subtask_parent_sync", "batch_operations", "progress_calculation"})
	zpAutoSyncAssert(t, zpAutoSyncGet(t, features, "task_context_sync"), true)
	zpAutoSyncAssert(t, zpAutoSyncGet(t, features, "subtask_parent_sync"), true)
	zpAutoSyncAssert(t, zpAutoSyncGet(t, features, "batch_operations"), true)
	zpAutoSyncAssert(t, zpAutoSyncGet(t, features, "progress_calculation"), true)
}

func TestAutomatedContextSyncService_GetSyncStatisticsMinimal(t *testing.T) {
	svc := NewAutomatedContextSyncService(&zpAutoSyncFakeTaskRepo{}, nil, nil, nil)
	stats := svc.GetSyncStatistics()
	zpAutoSyncAssert(t, zpAutoSyncGet(t, stats, "subtask_repository_available"), false)
	features := zpAutoSyncGet(t, stats, "features").(*entities.OrderedMap[any])
	zpAutoSyncAssert(t, zpAutoSyncGet(t, features, "subtask_parent_sync"), false)
	zpAutoSyncAssert(t, zpAutoSyncGet(t, features, "progress_calculation"), false)
}

func TestAutomatedContextSyncService_ValidateSyncConfiguration(t *testing.T) {
	svc := NewAutomatedContextSyncService(&zpAutoSyncFakeTaskRepo{}, &zpAutoSyncFakeSubtaskRepo{}, nil, &zpAutoSyncFakeSyncer{})
	validation := svc.ValidateSyncConfiguration()
	zpCtxInhKeyOrder(t, validation, []string{"is_valid", "issues", "recommendations", "async_support", "validation_timestamp"})
	zpAutoSyncAssert(t, zpAutoSyncGet(t, validation, "is_valid"), true)
	zpAutoSyncAssert(t, zpAutoSyncGet(t, validation, "issues"), []any{})
	zpAutoSyncAssert(t, zpAutoSyncGet(t, validation, "recommendations"), []any{})
	zpAutoSyncAssert(t, zpAutoSyncGet(t, validation, "async_support"), true)

	missingRepo := NewAutomatedContextSyncService(nil, nil, nil, &zpAutoSyncFakeSyncer{}).ValidateSyncConfiguration()
	zpAutoSyncAssert(t, zpAutoSyncGet(t, missingRepo, "is_valid"), false)
	zpAutoSyncAssert(t, zpAutoSyncGet(t, missingRepo, "issues"), []any{"Task repository not configured"})
	recommendations := zpAutoSyncGet(t, missingRepo, "recommendations").([]any)
	if len(recommendations) != 3 {
		t.Fatalf("recommendations = %v", recommendations)
	}

	missingSyncer := NewAutomatedContextSyncService(&zpAutoSyncFakeTaskRepo{}, nil, nil, nil).ValidateSyncConfiguration()
	zpAutoSyncAssert(t, zpAutoSyncGet(t, missingSyncer, "is_valid"), false)
	zpAutoSyncAssert(t, zpAutoSyncGet(t, missingSyncer, "issues"), []any{"Context sync service not available"})
}

func zpAutoSyncGetBool(t *testing.T, m *entities.OrderedMap[bool], key string) bool {
	t.Helper()
	value, ok := m.Get(key)
	if !ok {
		t.Fatalf("missing key %q", key)
	}
	return value
}

func zpAutoSyncAssert(t *testing.T, got, want any) {
	t.Helper()
	if !value_objects.PyEqual(got, want) {
		t.Fatalf("got %#v, want %#v", got, want)
	}
}

func zpAutoSyncStrPtr(s string) *string { return &s }
