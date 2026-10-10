package use_cases

import (
	"context"
	"reflect"
	"testing"

	dtotask "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// completeTaskFakeTaskRepository overrides only the storage methods exercised.
type completeTaskFakeTaskRepository struct {
	repositories.TaskRepository
	task       *entities.Task
	findErr    error
	allTasks   []*entities.Task
	findAllErr error
	saves      []*entities.Task
	saveErr    error
}

func (f *completeTaskFakeTaskRepository) FindByID(_ context.Context, _ value_objects.TaskId) (*entities.Task, error) {
	return f.task, f.findErr
}

func (f *completeTaskFakeTaskRepository) Save(_ context.Context, task *entities.Task) (*entities.Task, error) {
	f.saves = append(f.saves, task)
	return task, f.saveErr
}

func (f *completeTaskFakeTaskRepository) FindAll(_ context.Context) ([]*entities.Task, error) {
	return f.allTasks, f.findAllErr
}

// completeTaskFakeSubtaskRepository overrides only FindByParentTaskID.
type completeTaskFakeSubtaskRepository struct {
	repositories.SubtaskRepository
	subtasks []*entities.Subtask
	findErr  error
}

func (f *completeTaskFakeSubtaskRepository) FindByParentTaskID(_ context.Context, _ value_objects.TaskId) ([]*entities.Subtask, error) {
	return f.subtasks, f.findErr
}

const completeTaskTestID = "11111111-1111-1111-1111-111111111111"

func completeTaskNewTestTask(t *testing.T) (*entities.Task, value_objects.TaskId) {
	t.Helper()
	id, err := value_objects.NewTaskId(completeTaskTestID)
	if err != nil {
		t.Fatalf("NewTaskId: %v", err)
	}
	task, err := entities.NewTask(entities.Task{ID: &id, Title: "Test task", Description: "a description"})
	if err != nil {
		t.Fatalf("NewTask: %v", err)
	}
	return task, id
}

func completeTaskAssertKeys(t *testing.T, got []string, want []string) {
	t.Helper()
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("key order mismatch:\n got %v\nwant %v", got, want)
	}
}

func TestCompleteTaskNotFound(t *testing.T) {
	repo := &completeTaskFakeTaskRepository{task: nil}
	uc := NewCompleteTaskUseCase(repo, nil, nil, nil).WithLedger(noopLedger())

	resp, err := uc.Execute(context.Background(), completeTaskTestID, nil, nil, nil)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if resp != nil {
		t.Fatalf("expected nil response, got %v", resp)
	}
	want := "Task " + completeTaskTestID + " not found"
	if err.Error() != want {
		t.Fatalf("error = %q, want %q", err.Error(), want)
	}
}

func TestCompleteTaskAlreadyCompletedUpdatesSummary(t *testing.T) {
	task, id := completeTaskNewTestTask(t)
	done, _ := value_objects.NewTaskStatus("done")
	task.Status = &done

	repo := &completeTaskFakeTaskRepository{task: task}
	uc := NewCompleteTaskUseCase(repo, nil, nil, nil).WithLedger(noopLedger())
	summary := "finished the work"

	resp, err := uc.Execute(context.Background(), id.Value, &summary, nil, nil)
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	completeTaskAssertKeys(t, resp.Keys(),
		[]string{"success", "task_id", "message", "status", "was_already_completed"})
	if v, _ := resp.Get("success"); v != true {
		t.Fatalf("success = %v", v)
	}
	if v, _ := resp.Get("task_id"); v != id.Value {
		t.Fatalf("task_id = %v", v)
	}
	if v, _ := resp.Get("message"); v != "Task already completed, summary updated" {
		t.Fatalf("message = %v", v)
	}
	if v, _ := resp.Get("status"); v != "done" {
		t.Fatalf("status = %v", v)
	}
	if v, _ := resp.Get("was_already_completed"); v != true {
		t.Fatalf("was_already_completed = %v", v)
	}
	if task.CompletionSummary == nil || *task.CompletionSummary != summary {
		t.Fatalf("CompletionSummary = %v", task.CompletionSummary)
	}
	if len(repo.saves) != 1 {
		t.Fatalf("expected 1 save, got %d", len(repo.saves))
	}
}

func TestCompleteTaskAlreadyCompletedWithoutSummary(t *testing.T) {
	task, id := completeTaskNewTestTask(t)
	done, _ := value_objects.NewTaskStatus("done")
	task.Status = &done

	repo := &completeTaskFakeTaskRepository{task: task}
	uc := NewCompleteTaskUseCase(repo, nil, nil, nil).WithLedger(noopLedger())

	resp, err := uc.Execute(context.Background(), id.Value, nil, nil, nil)
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if v, _ := resp.Get("message"); v != "Task already completed" {
		t.Fatalf("message = %v", v)
	}
	if task.CompletionSummary != nil {
		t.Fatalf("CompletionSummary = %v, want nil", task.CompletionSummary)
	}
}

func TestCompleteTaskMissingSummary(t *testing.T) {
	task, id := completeTaskNewTestTask(t)
	repo := &completeTaskFakeTaskRepository{task: task}
	uc := NewCompleteTaskUseCase(repo, nil, nil, nil).WithLedger(noopLedger())

	resp, err := uc.Execute(context.Background(), id.Value, nil, nil, nil)
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	completeTaskAssertKeys(t, resp.Keys(),
		[]string{"success", "task_id", "message", "status", "hint"})
	if v, _ := resp.Get("success"); v != false {
		t.Fatalf("success = %v", v)
	}
	wantMessage := "Task '" + id.Value + "' cannot be completed without a completion_summary. " +
		"The Vision System requires a summary of what was accomplished."
	if v, _ := resp.Get("message"); v != wantMessage {
		t.Fatalf("message = %v, want %v", v, wantMessage)
	}
	// Python transitions todo -> in_progress (and saves) before task.complete_task
	// raises MissingCompletionSummaryError, so the status is in_progress here.
	if v, _ := resp.Get("status"); v != "in_progress" {
		t.Fatalf("status = %v", v)
	}
	if v, _ := resp.Get("hint"); v != "Use the 'complete_task_with_context' action or provide 'completion_summary' parameter" {
		t.Fatalf("hint = %v", v)
	}
}

func TestCompleteTaskSuccess(t *testing.T) {
	task, id := completeTaskNewTestTask(t)
	repo := &completeTaskFakeTaskRepository{task: task}
	subRepo := &completeTaskFakeSubtaskRepository{} // no subtasks
	uc := NewCompleteTaskUseCase(repo, subRepo, nil, nil).WithLedger(noopLedger())
	summary := "all done"

	resp, err := uc.Execute(context.Background(), id.Value, &summary, nil, nil)
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	completeTaskAssertKeys(t, resp.Keys(), []string{
		"success", "task_id", "status", "subtask_progress", "message", "was_already_completed", "subtask_summary",
	})
	if v, _ := resp.Get("success"); v != true {
		t.Fatalf("success = %v", v)
	}
	if v, _ := resp.Get("task_id"); v != id.Value {
		t.Fatalf("task_id = %v", v)
	}
	if v, _ := resp.Get("status"); v != "done" {
		t.Fatalf("status = %v", v)
	}
	if v, _ := resp.Get("message"); v != "task "+id.Value+" done, can next_task" {
		t.Fatalf("message = %v", v)
	}
	if v, _ := resp.Get("was_already_completed"); v != false {
		t.Fatalf("was_already_completed = %v", v)
	}

	progress, _ := resp.Get("subtask_progress")
	progressMap, ok := progress.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("subtask_progress type = %T", progress)
	}
	completeTaskAssertKeys(t, progressMap.Keys(), []string{"total", "completed", "percentage"})
	if v, _ := progressMap.Get("total"); v != 0 {
		t.Fatalf("progress.total = %v", v)
	}

	summaryAny, _ := resp.Get("subtask_summary")
	summaryMap, ok := summaryAny.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("subtask_summary type = %T", summaryAny)
	}
	completeTaskAssertKeys(t, summaryMap.Keys(),
		[]string{"total", "completed", "incomplete", "completion_percentage", "can_complete_parent"})
	if v, _ := summaryMap.Get("total"); v != 0 {
		t.Fatalf("summary.total = %v", v)
	}
	if v, _ := summaryMap.Get("completion_percentage"); v != 100 {
		t.Fatalf("summary.completion_percentage = %v (%T)", v, v)
	}
	if v, _ := summaryMap.Get("can_complete_parent"); v != true {
		t.Fatalf("summary.can_complete_parent = %v", v)
	}

	if task.Status.Value != "done" {
		t.Fatalf("task status = %q", task.Status.Value)
	}
	if task.CompletionSummary == nil || *task.CompletionSummary != summary {
		t.Fatalf("CompletionSummary = %v", task.CompletionSummary)
	}
	// One save for todo -> in_progress, one for the final persistence.
	if len(repo.saves) != 2 {
		t.Fatalf("expected 2 saves, got %d", len(repo.saves))
	}
}

// completeTaskFakeHooks records what the completion path asks of its hooks, mirroring
// createTaskFakeHooks. The assertion that matters is WHICH action string reaches the broadcast.
type completeTaskFakeHooks struct {
	notified []string
}

func (h *completeTaskFakeHooks) SyncTaskStatus(_ context.Context, _ string, _ string) error {
	return nil
}

func (h *completeTaskFakeHooks) SyncTaskMetadata(_ context.Context, _ string, _ *entities.Task, _ string) error {
	return nil
}

func (h *completeTaskFakeHooks) NotifyTaskEvent(_ context.Context, eventType string, _ *entities.Task, _ *dtotask.TaskResponse, _ *string, _ string) {
	h.notified = append(h.notified, eventType)
}

// TestCompleteTaskSuccessBroadcasts is the regression this whole change exists for, and it FAILED TO
// COMPILE before it: CompleteTaskHooks declared only SyncTaskStatus and SyncTaskMetadata, so the call
// it asserts could not be written at that site - the object the wiring hands to this use case
// implements the capability and the interface the use case holds did not declare it. A completion
// therefore reached the client only through React Query's own refetch, with no frame and no animation,
// while a created or updated task animated.
//
// "completed" RATHER THAN "updated" IS THE DECISION: it is the terminal transition the client
// animates distinctively, and both names are already in its allowlist. Every OTHER status move emits
// "updated", matching update_task.go's literal - a distinct animation per transition would be a
// vocabulary addition and the owner's decision.
func TestCompleteTaskSuccessBroadcasts(t *testing.T) {
	task, id := completeTaskNewTestTask(t)
	repo := &completeTaskFakeTaskRepository{task: task}
	hooks := &completeTaskFakeHooks{}
	uc := NewCompleteTaskUseCase(repo, &completeTaskFakeSubtaskRepository{}, nil, nil).WithHooks(hooks).WithLedger(noopLedger())
	summary := "all done"

	if _, err := uc.Execute(context.Background(), id.Value, &summary, nil, nil); err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if len(hooks.notified) != 1 || hooks.notified[0] != "completed" {
		t.Fatalf("broadcast actions = %v, want exactly [completed]", hooks.notified)
	}
}

func TestCompleteTaskIncompleteSubtasks(t *testing.T) {
	task, id := completeTaskNewTestTask(t)
	subID, err := value_objects.NewTaskId("22222222-2222-2222-2222-222222222222")
	if err != nil {
		t.Fatalf("NewTaskId: %v", err)
	}
	subtask, err := entities.NewSubtask(entities.Subtask{
		ID: &subID, Title: "Subtask one", Description: "d", ParentTaskID: &id,
	})
	if err != nil {
		t.Fatalf("NewSubtask: %v", err)
	}

	repo := &completeTaskFakeTaskRepository{task: task}
	subRepo := &completeTaskFakeSubtaskRepository{subtasks: []*entities.Subtask{subtask}}
	uc := NewCompleteTaskUseCase(repo, subRepo, nil, nil).WithLedger(noopLedger())
	summary := "trying"

	resp, err := uc.Execute(context.Background(), id.Value, &summary, nil, nil)
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	completeTaskAssertKeys(t, resp.Keys(), []string{"success", "task_id", "message", "status", "error"})
	if v, _ := resp.Get("success"); v != false {
		t.Fatalf("success = %v", v)
	}
	wantMessage := "Cannot complete task: 1 of 1 subtasks are not done"
	if v, _ := resp.Get("message"); v != wantMessage {
		t.Fatalf("message = %v, want %v", v, wantMessage)
	}
	if v, _ := resp.Get("status"); v != "todo" {
		t.Fatalf("status = %v", v)
	}

	errorAny, _ := resp.Get("error")
	errorMap, ok := errorAny.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("error type = %T", errorAny)
	}
	completeTaskAssertKeys(t, errorMap.Keys(), []string{"message", "code", "details"})
	if v, _ := errorMap.Get("message"); v != wantMessage {
		t.Fatalf("error.message = %v", v)
	}
	if v, _ := errorMap.Get("code"); v != "SUBTASKS_NOT_COMPLETE" {
		t.Fatalf("error.code = %v", v)
	}

	detailsAny, _ := errorMap.Get("details")
	detailsMap, ok := detailsAny.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("details type = %T", detailsAny)
	}
	completeTaskAssertKeys(t, detailsMap.Keys(),
		[]string{"incomplete_subtasks", "incomplete_count", "total_count"})
	if v, _ := detailsMap.Get("incomplete_count"); v != 1 {
		t.Fatalf("details.incomplete_count = %v", v)
	}
	if v, _ := detailsMap.Get("total_count"); v != 1 {
		t.Fatalf("details.total_count = %v", v)
	}

	listAny, _ := detailsMap.Get("incomplete_subtasks")
	list, ok := listAny.([]*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("incomplete_subtasks type = %T", listAny)
	}
	if len(list) != 1 {
		t.Fatalf("len(incomplete_subtasks) = %d", len(list))
	}
	completeTaskAssertKeys(t, list[0].Keys(), []string{"id", "title", "status"})
	if v, _ := list[0].Get("id"); v != subID.Value {
		t.Fatalf("detail.id = %v", v)
	}
	if v, _ := list[0].Get("title"); v != "Subtask one" {
		t.Fatalf("detail.title = %v", v)
	}
	if v, _ := list[0].Get("status"); v != "todo" {
		t.Fatalf("detail.status = %v", v)
	}
}

func TestCompleteTaskUnblocksDependentTask(t *testing.T) {
	taskA, idA := completeTaskNewTestTask(t)

	idB, err := value_objects.NewTaskId("33333333-3333-3333-3333-333333333333")
	if err != nil {
		t.Fatalf("NewTaskId: %v", err)
	}
	taskB, err := entities.NewTask(entities.Task{ID: &idB, Title: "Dependent", Description: "d"})
	if err != nil {
		t.Fatalf("NewTask: %v", err)
	}
	blocked, _ := value_objects.NewTaskStatus("blocked")
	taskB.Status = &blocked
	taskB.Dependencies = []value_objects.TaskId{idA}

	repo := &completeTaskFakeTaskRepository{task: taskA, allTasks: []*entities.Task{taskA, taskB}}
	subRepo := &completeTaskFakeSubtaskRepository{}
	uc := NewCompleteTaskUseCase(repo, subRepo, nil, nil).WithLedger(noopLedger())
	summary := "done"

	if _, err := uc.Execute(context.Background(), idA.Value, &summary, nil, nil); err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if taskB.Status.Value != "todo" {
		t.Fatalf("dependent task status = %q, want todo", taskB.Status.Value)
	}
	found := false
	for _, saved := range repo.saves {
		if saved == taskB {
			found = true
		}
	}
	if !found {
		t.Fatal("dependent task was not saved")
	}
}
