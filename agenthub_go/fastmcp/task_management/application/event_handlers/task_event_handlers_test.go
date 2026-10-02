package event_handlers

import (
	"context"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/events"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

type taskEventTestRepo struct {
	created     []any
	archived    []string
	dependents  []string
	accesses    []string
	dependency  []*entities.Task
	archiveTime time.Time
}

func (r *taskEventTestRepo) TrackTaskCreation(ctx context.Context, event any) error {
	r.created = append(r.created, event)
	return nil
}
func (r *taskEventTestRepo) ArchiveTask(ctx context.Context, taskID string, occurredAt time.Time) error {
	r.archived = append(r.archived, taskID)
	r.archiveTime = occurredAt
	return nil
}
func (r *taskEventTestRepo) GetDependentTasks(ctx context.Context, taskID string) ([]string, error) {
	return r.dependents, nil
}
func (r *taskEventTestRepo) TrackTaskAccess(ctx context.Context, taskID string, userID *string, accessedAt time.Time) error {
	r.accesses = append(r.accesses, taskID)
	return nil
}
func (r *taskEventTestRepo) GetTaskDependencies(ctx context.Context, taskID string) ([]*entities.Task, error) {
	return r.dependency, nil
}

type taskEventTestNotifications struct {
	ready []string
	moved []string
}

func (n *taskEventTestNotifications) NotifyTaskAssignment(ctx context.Context, assignee, taskID, title, priority string) error {
	return nil
}
func (n *taskEventTestNotifications) NotifyTaskUpdated(ctx context.Context, taskID string, changedFields []string, previousValues, newValues map[string]any) error {
	return nil
}
func (n *taskEventTestNotifications) NotifyTaskDeleted(ctx context.Context, taskID string, deletedBy *string) error {
	return nil
}
func (n *taskEventTestNotifications) NotifyTaskCompleted(ctx context.Context, taskID, title string, completedBy *string, completionTime float64) error {
	return nil
}
func (n *taskEventTestNotifications) NotifyTaskMoved(ctx context.Context, taskID, previousBranch, newBranch string, movedBy *string) error {
	n.moved = append(n.moved, taskID)
	return nil
}
func (n *taskEventTestNotifications) NotifyTaskStarted(ctx context.Context, taskID string, startedBy *string) error {
	return nil
}
func (n *taskEventTestNotifications) NotifyTaskBlocked(ctx context.Context, taskID string, blockedBy *string, urgent bool) error {
	return nil
}
func (n *taskEventTestNotifications) NotifyTaskNeedsReview(ctx context.Context, taskID string, submittedBy *string) error {
	return nil
}
func (n *taskEventTestNotifications) NotifyTaskReady(ctx context.Context, taskID, message string) error {
	n.ready = append(n.ready, taskID)
	return nil
}

func TestTaskEventHandlersStatisticsAndTransitions(t *testing.T) {
	ctx := context.Background()
	h := NewTaskEventHandlers(nil, nil, nil)

	created := events.NewTaskCreatedEvent()
	created.TaskID = "t1"
	created.Title = "First"
	created.Priority = "high"
	created.Assignees = []string{"alice"}
	h.HandleTaskCreated(ctx, created)

	occurred := time.Date(2024, 5, 1, 10, 0, 0, 0, time.UTC)
	user := "u1"
	changed := events.NewTaskStatusChangedEvent()
	changed.TaskID = "t1"
	changed.OldStatus = "todo"
	changed.NewStatus = "in_progress"
	changed.OccurredAt = occurred
	changed.UserID = &user
	h.HandleTaskStatusChanged(ctx, changed)

	if h.TaskStats["unknown"]["created"] != 1 || h.TaskStats["unknown"]["status_changes"] != 1 {
		t.Fatalf("unexpected stats: %+v", h.TaskStats)
	}

	transition := h.StatusTransitions["t1"][0]
	if got, _ := transition.Get("task_id"); got != "t1" {
		t.Fatalf("task_id = %v", got)
	}
	if got, _ := transition.Get("from"); got != "todo" {
		t.Fatalf("from = %v", got)
	}
	if got, _ := transition.Get("to"); got != "in_progress" {
		t.Fatalf("to = %v", got)
	}
	if got, _ := transition.Get("timestamp"); got != value_objects.IsoFormat(occurred) {
		t.Fatalf("timestamp = %v", got)
	}
	if got, _ := transition.Get("user"); got != "u1" {
		t.Fatalf("user = %v", got)
	}

	out := h.GetTaskStatistics(ctx, nil)
	if keys := out.Keys(); len(keys) != 2 || keys[0] != "summary" || keys[1] != "by_project" {
		t.Fatalf("aggregate keys = %v", keys)
	}
	summaryAny, _ := out.Get("summary")
	summary := summaryAny.(*entities.OrderedMap[any])
	wantSummaryKeys := []string{"created", "updated", "completed", "deleted", "status_changes", "moved", "completion_rate"}
	if got := summary.Keys(); len(got) != len(wantSummaryKeys) {
		t.Fatalf("summary keys = %v", got)
	} else {
		for i, k := range wantSummaryKeys {
			if got[i] != k {
				t.Fatalf("summary key[%d] = %q, want %q", i, got[i], k)
			}
		}
	}
	if rate, _ := summary.Get("completion_rate"); rate != 0.0 {
		t.Fatalf("completion_rate = %v", rate)
	}
	if _, ok := summary.Get("avg_completion_time_seconds"); ok {
		t.Fatalf("avg_completion_time_seconds should be absent")
	}
	byProjectAny, _ := out.Get("by_project")
	byProject := byProjectAny.(*entities.OrderedMap[any])
	if got := byProject.Keys(); len(got) != 1 || got[0] != "unknown" {
		t.Fatalf("by_project keys = %v", got)
	}

	absent := "missing"
	missing := h.GetTaskStatistics(ctx, &absent)
	statsAny, _ := missing.Get("statistics")
	if stats := statsAny.(*entities.OrderedMap[any]); stats.Len() != 0 {
		t.Fatalf("missing project statistics = %v", stats.Keys())
	}
}

func TestTaskEventHandlersCompletionAndDependencies(t *testing.T) {
	ctx := context.Background()
	done := "done"
	status, err := value_objects.NewTaskStatus(done)
	if err != nil {
		t.Fatalf("NewTaskStatus: %v", err)
	}
	repo := &taskEventTestRepo{
		dependents: []string{"t2"},
		dependency: []*entities.Task{{Status: &status}},
	}
	notifications := &taskEventTestNotifications{}
	h := NewTaskEventHandlers(nil, repo, notifications)

	minutes := 30
	completed := events.NewTaskCompletedEvent()
	completed.TaskID = "t1"
	completed.Title = "First"
	completed.TimeSpentMinutes = &minutes
	h.HandleTaskCompleted(ctx, completed)

	if len(h.CompletionTimes) != 1 || h.CompletionTimes[0] != 1800 {
		t.Fatalf("completion times = %v", h.CompletionTimes)
	}
	if len(notifications.ready) != 1 || notifications.ready[0] != "t2" {
		t.Fatalf("ready notifications = %v", notifications.ready)
	}

	stats := h.GetTaskStatistics(ctx, nil)
	summaryAny, _ := stats.Get("summary")
	summary := summaryAny.(*entities.OrderedMap[any])
	if got, _ := summary.Get("avg_completion_time_seconds"); got != 1800.0 {
		t.Fatalf("avg = %v", got)
	}
	if got, _ := summary.Get("completion_rate"); got != 0.0 {
		t.Fatalf("completion_rate = %v", got)
	}

	moved := events.NewTaskMovedToBranchEvent()
	moved.TaskID = "t1"
	moved.OldBranchID = "b1"
	moved.NewBranchID = "b2"
	h.ProcessEvent(ctx, moved)
	if len(notifications.moved) != 1 || h.TaskStats["unknown"]["moved"] != 1 {
		t.Fatalf("moved routing failed: %v %v", notifications.moved, h.TaskStats)
	}
}
