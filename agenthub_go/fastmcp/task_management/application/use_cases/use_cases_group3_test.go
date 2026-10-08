package use_cases

import (
	"context"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// useCasesGroup3FakeTaskRepository is a no-DB TaskRepository. Hooks configure the
// methods the use cases exercise; the rest are inert.
type useCasesGroup3FakeTaskRepository struct {
	findByID      func(ctx context.Context, taskID value_objects.TaskId) (*entities.Task, error)
	save          func(ctx context.Context, task *entities.Task) (*entities.Task, error)
	atomic        func(ctx context.Context, taskID string) (bool, error)
	findByIDCalls int
	atomicCalls   int
}

func (f *useCasesGroup3FakeTaskRepository) FindByID(ctx context.Context, taskID value_objects.TaskId) (*entities.Task, error) {
	f.findByIDCalls++
	if f.findByID != nil {
		return f.findByID(ctx, taskID)
	}
	return nil, nil
}

func (f *useCasesGroup3FakeTaskRepository) Save(ctx context.Context, task *entities.Task) (*entities.Task, error) {
	if f.save != nil {
		return f.save(ctx, task)
	}
	return task, nil
}

func (f *useCasesGroup3FakeTaskRepository) AtomicIncrementCompletedSubtasks(ctx context.Context, taskID string) (bool, error) {
	f.atomicCalls++
	if f.atomic != nil {
		return f.atomic(ctx, taskID)
	}
	return true, nil
}

func (f *useCasesGroup3FakeTaskRepository) FindAll(ctx context.Context) ([]*entities.Task, error) {
	return nil, nil
}

func (f *useCasesGroup3FakeTaskRepository) FindByStatus(ctx context.Context, status value_objects.TaskStatus) ([]*entities.Task, error) {
	return nil, nil
}

func (f *useCasesGroup3FakeTaskRepository) FindByPriority(ctx context.Context, priority value_objects.Priority) ([]*entities.Task, error) {
	return nil, nil
}

func (f *useCasesGroup3FakeTaskRepository) FindByAssignee(ctx context.Context, assignee string) ([]*entities.Task, error) {
	return nil, nil
}

func (f *useCasesGroup3FakeTaskRepository) FindByLabels(ctx context.Context, labels []string) ([]*entities.Task, error) {
	return nil, nil
}

func (f *useCasesGroup3FakeTaskRepository) Search(ctx context.Context, query string, filters map[string]any, limit int) ([]*entities.Task, error) {
	return nil, nil
}

func (f *useCasesGroup3FakeTaskRepository) Delete(ctx context.Context, taskID value_objects.TaskId) (bool, error) {
	return false, nil
}

func (f *useCasesGroup3FakeTaskRepository) Exists(ctx context.Context, taskID value_objects.TaskId) (bool, error) {
	return false, nil
}

func (f *useCasesGroup3FakeTaskRepository) GetNextID(ctx context.Context) (value_objects.TaskId, error) {
	return value_objects.TaskId{}, nil
}

func (f *useCasesGroup3FakeTaskRepository) Count(ctx context.Context) (int, error) {
	return 0, nil
}

func (f *useCasesGroup3FakeTaskRepository) GetStatistics(ctx context.Context) (map[string]any, error) {
	return nil, nil
}

func (f *useCasesGroup3FakeTaskRepository) FindByCriteria(ctx context.Context, filters map[string]any, limit *int) ([]*entities.Task, error) {
	return nil, nil
}

func (f *useCasesGroup3FakeTaskRepository) FindByIDAllStates(ctx context.Context, taskID value_objects.TaskId) (*entities.Task, error) {
	return nil, nil
}

// useCasesGroup3FakeSubtaskRepository is a no-DB SubtaskRepository.
type useCasesGroup3FakeSubtaskRepository struct {
	findByID  func(ctx context.Context, id string) (*entities.Subtask, error)
	save      func(ctx context.Context, subtask *entities.Subtask) (bool, error)
	saveCalls int
}

func (f *useCasesGroup3FakeSubtaskRepository) FindByID(ctx context.Context, id string) (*entities.Subtask, error) {
	if f.findByID != nil {
		return f.findByID(ctx, id)
	}
	return nil, nil
}

func (f *useCasesGroup3FakeSubtaskRepository) Save(ctx context.Context, subtask *entities.Subtask) (bool, error) {
	f.saveCalls++
	if f.save != nil {
		return f.save(ctx, subtask)
	}
	return true, nil
}

func (f *useCasesGroup3FakeSubtaskRepository) FindByParentTaskID(ctx context.Context, parentTaskID value_objects.TaskId) ([]*entities.Subtask, error) {
	return nil, nil
}

func (f *useCasesGroup3FakeSubtaskRepository) FindByAssignee(ctx context.Context, assignee string) ([]*entities.Subtask, error) {
	return nil, nil
}

func (f *useCasesGroup3FakeSubtaskRepository) FindByStatus(ctx context.Context, status string) ([]*entities.Subtask, error) {
	return nil, nil
}

func (f *useCasesGroup3FakeSubtaskRepository) FindCompleted(ctx context.Context, parentTaskID value_objects.TaskId) ([]*entities.Subtask, error) {
	return nil, nil
}

func (f *useCasesGroup3FakeSubtaskRepository) FindPending(ctx context.Context, parentTaskID value_objects.TaskId) ([]*entities.Subtask, error) {
	return nil, nil
}

func (f *useCasesGroup3FakeSubtaskRepository) Delete(ctx context.Context, id string) (bool, error) {
	return false, nil
}

func (f *useCasesGroup3FakeSubtaskRepository) DeleteByParentTaskID(ctx context.Context, parentTaskID value_objects.TaskId) (bool, error) {
	return false, nil
}

func (f *useCasesGroup3FakeSubtaskRepository) Exists(ctx context.Context, id string) (bool, error) {
	return false, nil
}

func (f *useCasesGroup3FakeSubtaskRepository) CountByParentTaskID(ctx context.Context, parentTaskID value_objects.TaskId) (int, error) {
	return 0, nil
}

func (f *useCasesGroup3FakeSubtaskRepository) CountCompletedByParentTaskID(ctx context.Context, parentTaskID value_objects.TaskId) (int, error) {
	return 0, nil
}

func (f *useCasesGroup3FakeSubtaskRepository) GetNextID(ctx context.Context, parentTaskID value_objects.TaskId) (value_objects.TaskId, error) {
	return value_objects.TaskId{}, nil
}

func (f *useCasesGroup3FakeSubtaskRepository) GetSubtaskProgress(ctx context.Context, parentTaskID value_objects.TaskId) (map[string]any, error) {
	return nil, nil
}

func (f *useCasesGroup3FakeSubtaskRepository) BulkUpdateStatus(ctx context.Context, parentTaskID value_objects.TaskId, status string) (bool, error) {
	return false, nil
}

func (f *useCasesGroup3FakeSubtaskRepository) BulkComplete(ctx context.Context, parentTaskID value_objects.TaskId) (bool, error) {
	return false, nil
}

func (f *useCasesGroup3FakeSubtaskRepository) RemoveSubtask(ctx context.Context, parentTaskID, subtaskID string) (bool, error) {
	return false, nil
}

// group3NewTask builds a valid task with the given subtask IDs and completed count.
func group3NewTask(id string, subtasks []string, completed int) *entities.Task {
	taskID, err := value_objects.NewTaskId(id)
	if err != nil {
		panic(err)
	}
	task, err := entities.NewTask(entities.Task{
		Title:             "Test task",
		Description:       "Test description",
		ID:                &taskID,
		Subtasks:          subtasks,
		CompletedSubtasks: completed,
	})
	if err != nil {
		panic(err)
	}
	return task
}

// group3NewSubtask builds a valid todo subtask.
func group3NewSubtask(id, parentID string) *entities.Subtask {
	subtaskID, err := value_objects.NewTaskId(id)
	if err != nil {
		panic(err)
	}
	parent, err := value_objects.NewTaskId(parentID)
	if err != nil {
		panic(err)
	}
	subtask, err := entities.NewSubtask(entities.Subtask{
		ID:           &subtaskID,
		ParentTaskID: &parent,
		Title:        "Test subtask",
		Description:  "Test description",
	})
	if err != nil {
		panic(err)
	}
	return subtask
}

func group3Keys(m *entities.OrderedMap[any]) []string { return m.Keys() }

func group3EqualStrings(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

// TestCompleteSubtaskRetryClassification covers the lookup retry classifier:
// concurrent-conflict errors retry three times, anything else fails once.
func TestCompleteSubtaskRetryClassification(t *testing.T) {
	retryable := &useCasesGroup3FakeTaskRepository{
		findByID: func(ctx context.Context, taskID value_objects.TaskId) (*entities.Task, error) {
			return nil, &value_objects.ValueError{Msg: "database is locked"}
		},
	}
	uc := NewCompleteSubtaskUseCase(retryable, nil)
	if _, err := uc.Execute(context.Background(), "123", "123.001", nil, nil, nil, nil); err == nil {
		t.Fatalf("expected retryable lookup error")
	}
	if retryable.findByIDCalls != 3 {
		t.Fatalf("retryable lookup calls = %d, want 3", retryable.findByIDCalls)
	}

	nonRetryable := &useCasesGroup3FakeTaskRepository{
		findByID: func(ctx context.Context, taskID value_objects.TaskId) (*entities.Task, error) {
			return nil, &value_objects.ValueError{Msg: "boom"}
		},
	}
	uc = NewCompleteSubtaskUseCase(nonRetryable, nil)
	if _, err := uc.Execute(context.Background(), "123", "123.001", nil, nil, nil, nil); err == nil {
		t.Fatalf("expected non-retryable lookup error")
	}
	if nonRetryable.findByIDCalls != 1 {
		t.Fatalf("non-retryable lookup calls = %d, want 1", nonRetryable.findByIDCalls)
	}
}

// TestCompleteSubtaskNotFound covers the dedicated-subtask branch when
// find_by_id(id) returns None.
func TestCompleteSubtaskNotFound(t *testing.T) {
	taskRepo := &useCasesGroup3FakeTaskRepository{
		findByID: func(ctx context.Context, taskID value_objects.TaskId) (*entities.Task, error) {
			return group3NewTask("123", nil, 0), nil
		},
	}
	subtaskRepo := &useCasesGroup3FakeSubtaskRepository{
		findByID: func(ctx context.Context, id string) (*entities.Subtask, error) {
			return nil, nil
		},
	}
	uc := NewCompleteSubtaskUseCase(taskRepo, subtaskRepo)
	_, err := uc.Execute(context.Background(), "123", "123.001", nil, nil, nil, nil)
	if err == nil {
		t.Fatalf("expected subtask-not-found error")
	}
	want := "Subtask 123.001 not found in task 123"
	if err.Error() != want {
		t.Fatalf("error = %q, want %q", err.Error(), want)
	}
}

// TestCompleteSubtaskParentProgress covers the parent percentage calculation and
// the response key order for the dedicated-subtask branch.
func TestCompleteSubtaskParentProgress(t *testing.T) {
	const parent = "11111111-1111-1111-1111-111111111111"
	const firstSubtask = parent + ".001"
	subtaskIDs := []string{firstSubtask, parent + ".002", parent + ".003", parent + ".004"}

	task := group3NewTask(parent, subtaskIDs, 1)
	taskRepo := &useCasesGroup3FakeTaskRepository{
		findByID: func(ctx context.Context, taskID value_objects.TaskId) (*entities.Task, error) {
			return task, nil
		},
		atomic: func(ctx context.Context, taskID string) (bool, error) { return true, nil },
	}
	subtaskRepo := &useCasesGroup3FakeSubtaskRepository{
		findByID: func(ctx context.Context, id string) (*entities.Subtask, error) {
			return group3NewSubtask(firstSubtask, parent), nil
		},
	}

	uc := NewCompleteSubtaskUseCase(taskRepo, subtaskRepo)
	result, err := uc.Execute(context.Background(), parent, firstSubtask, nil, nil, nil, nil)
	if err != nil {
		t.Fatalf("Execute returned error: %v", err)
	}

	wantKeys := []string{"success", "task_id", "subtask_id", "progress", "parent_progress"}
	if got := group3Keys(result); !group3EqualStrings(got, wantKeys) {
		t.Fatalf("response keys = %v, want %v", got, wantKeys)
	}
	if success, _ := result.Get("success"); success != true {
		t.Fatalf("success = %v, want true", success)
	}
	if taskID, _ := result.Get("task_id"); taskID != parent {
		t.Fatalf("task_id = %v, want %s", taskID, parent)
	}
	if subtaskID, _ := result.Get("subtask_id"); subtaskID != firstSubtask {
		t.Fatalf("subtask_id = %v, want %s", subtaskID, firstSubtask)
	}

	progress, _ := result.Get("progress")
	progressMap, ok := progress.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("progress is %T, want *entities.OrderedMap[any]", progress)
	}
	wantProgressKeys := []string{"total", "completed", "percentage"}
	if got := progressMap.Keys(); !group3EqualStrings(got, wantProgressKeys) {
		t.Fatalf("progress keys = %v, want %v", got, wantProgressKeys)
	}
	if total, _ := progressMap.Get("total"); total != 4 {
		t.Fatalf("total = %v, want 4", total)
	}
	if completed, _ := progressMap.Get("completed"); completed != 1 {
		t.Fatalf("completed = %v, want 1", completed)
	}
	if percentage, _ := progressMap.Get("percentage"); percentage != 25.0 {
		t.Fatalf("percentage = %v (%T), want 25.0", percentage, percentage)
	}

	parentProgress, _ := result.Get("parent_progress")
	if parentProgress != progress {
		t.Fatalf("parent_progress and progress should be the same dict")
	}
	if taskRepo.atomicCalls != 1 {
		t.Fatalf("atomic increment calls = %d, want 1", taskRepo.atomicCalls)
	}
	if subtaskRepo.saveCalls != 1 {
		t.Fatalf("subtask save calls = %d, want 1", subtaskRepo.saveCalls)
	}
}

// TestOptimizedCompleteTaskMissingTaskID covers the MISSING_FIELD response.
func TestOptimizedCompleteTaskMissingTaskID(t *testing.T) {
	uc := NewOptimizedCompleteTaskUseCase(&useCasesGroup3FakeTaskRepository{}, nil, nil, nil)
	response, err := uc.Execute(context.Background(), &OptimizedCompleteTaskRequest{})
	if err != nil {
		t.Fatalf("Execute returned error: %v", err)
	}
	wantKeys := []string{"success", "error", "error_code", "field", "expected", "hint"}
	if got := group3Keys(response); !group3EqualStrings(got, wantKeys) {
		t.Fatalf("keys = %v, want %v", got, wantKeys)
	}
	checks := map[string]any{
		"success":    false,
		"error":      "task_id is required",
		"error_code": "MISSING_FIELD",
		"field":      "task_id",
		"expected":   "A valid task_id",
		"hint":       "Provide the ID of the task to complete",
	}
	for key, want := range checks {
		if got, _ := response.Get(key); got != want {
			t.Fatalf("%s = %v, want %v", key, got, want)
		}
	}
}

// TestOptimizedCompleteTaskNotFound covers the NOT_FOUND response.
func TestOptimizedCompleteTaskNotFound(t *testing.T) {
	taskRepo := &useCasesGroup3FakeTaskRepository{
		findByID: func(ctx context.Context, taskID value_objects.TaskId) (*entities.Task, error) {
			return nil, nil
		},
	}
	uc := NewOptimizedCompleteTaskUseCase(taskRepo, nil, nil, nil)
	response, err := uc.Execute(context.Background(), &OptimizedCompleteTaskRequest{TaskID: "123"})
	if err != nil {
		t.Fatalf("Execute returned error: %v", err)
	}
	wantKeys := []string{"success", "error", "error_code", "field", "hint"}
	if got := group3Keys(response); !group3EqualStrings(got, wantKeys) {
		t.Fatalf("keys = %v, want %v", got, wantKeys)
	}
	checks := map[string]any{
		"success":    false,
		"error":      "Task not found: 123",
		"error_code": "NOT_FOUND",
		"field":      "task_id",
		"hint":       "Check that the task ID is correct",
	}
	for key, want := range checks {
		if got, _ := response.Get(key); got != want {
			t.Fatalf("%s = %v, want %v", key, got, want)
		}
	}
}

// TestOptimizedCompleteTaskInvalidTaskIDIsOperationFailed documents that a
// string that cannot become a TaskId follows the Python outer-except path.
func TestOptimizedCompleteTaskInvalidTaskIDIsOperationFailed(t *testing.T) {
	uc := NewOptimizedCompleteTaskUseCase(&useCasesGroup3FakeTaskRepository{}, nil, nil, nil)
	response, err := uc.Execute(context.Background(), &OptimizedCompleteTaskRequest{TaskID: "!!! not an id !!!"})
	if err != nil {
		t.Fatalf("Execute returned error: %v", err)
	}
	if got, _ := response.Get("error_code"); got != "OPERATION_FAILED" {
		t.Fatalf("error_code = %v, want OPERATION_FAILED", got)
	}
	if msg, _ := response.Get("error"); !strings.HasPrefix(msg.(string), "Failed to complete task: ") {
		t.Fatalf("error = %v, want Failed to complete task prefix", msg)
	}
}
