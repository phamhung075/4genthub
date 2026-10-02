package entities

import (
	"reflect"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/events"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func newTestTask(t *testing.T) *Task {
	id := value_objects.GenerateNewTaskId()
	task, err := CreateTask(Task{ID: &id, Title: "t", Description: "d"})
	if err != nil {
		t.Fatal(err)
	}
	return task
}

func TestTaskLifecycle(t *testing.T) {
	task := newTestTask(t)
	if task.Status.Value != "todo" || task.Priority.Value != "medium" || task.ProgressState != value_objects.ProgressStateInitial {
		t.Fatal("defaults")
	}
	if err := task.UpdateStatus(mustTaskStatus("blocked")); err == nil || err.Error() != "Cannot transition from todo to blocked" {
		t.Fatalf("transition: %v", err)
	}
	if err := task.UpdateAssignees([]string{"coding-agent", "custom", "", "@x"}); err != nil {
		t.Fatal(err)
	}
	if strings.Join(task.Assignees, ",") != "@coding-agent,custom,@x" {
		t.Fatalf("assignees %v", task.Assignees)
	}
	if _, err := task.ValidateAssigneeList([]string{"custom"}); err == nil || err.Error() != "Invalid assignees: ['custom']. Valid assignees must be from AgentRole enum." {
		t.Fatalf("validate: %v", err)
	}
	if err := task.UpdateDueDate(ptr("2025-10-29")); err != nil || *task.DueDate != "2025-10-29T00:00:00+00:00" {
		t.Fatalf("due: %v %v", err, task.DueDate)
	}
	if err := task.UpdateDueDate(ptr("nope")); err == nil || !strings.HasPrefix(err.Error(), "Invalid due date format: nope.") {
		t.Fatalf("due err: %v", err)
	}
	if err := task.UpdateEstimatedEffort("bogus"); err != nil || task.EstimatedEffort != "medium" {
		t.Fatal("effort")
	}
	if err := task.AppendProgress("hello"); err != nil || task.GetProgressHistoryText() != "=== Progress 1 ===\nhello" {
		t.Fatalf("progress %q", task.GetProgressHistoryText())
	}
	if err := task.CompleteTask(" ", nil); err == nil {
		t.Fatal("summary required")
	}
	if err := task.SetProgressPercentage(101); err == nil || err.Error() != "Progress percentage must be between 0 and 100, got 101" {
		t.Fatalf("pct: %v", err)
	}
	if err := task.CompleteTask("done", nil); err != nil || task.Status.Value != "done" || task.OverallProgress != 100 {
		t.Fatalf("complete: %v", err)
	}
	if n := len(task.GetEvents()); n == 0 || len(task.Events) != 0 {
		t.Fatal("events drained")
	}
}

func TestTaskProgressMilestones(t *testing.T) {
	task := newTestTask(t)
	_ = task.AddProgressMilestone("b", 10)
	_ = task.AddProgressMilestone("a", 20)
	if err := task.UpdateProgress(ProgressUpdate{Type: value_objects.ProgressTypeGeneral, Percentage: 50}); err != nil {
		t.Fatal(err)
	}
	var names []string
	for _, e := range task.Events {
		if m, ok := e.(events.ProgressMilestoneReached); ok {
			names = append(names, m.MilestoneName)
		}
	}
	if strings.Join(names, ",") != "b,a" || !task.OverallProgressIsFloat || task.OverallProgress != 50 {
		t.Fatalf("milestones %v overall %v", names, task.OverallProgress)
	}
}

func TestTaskToDictNeedsResolver(t *testing.T) {
	task := newTestTask(t)
	AgentNameResolver = nil
	if _, err := task.ToDict(); err == nil {
		t.Fatal("expected resolver error")
	}
	AgentNameResolver = func(s string) string { return strings.TrimPrefix(s, "@") }
	defer func() { AgentNameResolver = nil }()
	d, err := task.ToDict()
	if err != nil || d["overall_progress"] != 0 || d["completion_summary"] != "" {
		t.Fatalf("dict: %v %v", err, d)
	}
}

func ptr(s string) *string { return &s }

// Python: TaskCreatedEvent/TaskUpdatedEvent receive the TaskId object, so
// BaseDomainEvent.to_dict (dataclasses.asdict) yields task_id == {'value': '<uuid>'}.
func TestTaskEventsSerializeTaskIDLikeAsdict(t *testing.T) {
	task := newTestTask(t)
	created := task.Events[0].(interface{ ToDict() map[string]any }).ToDict()
	want := map[string]any{"value": task.ID.Value}
	if !reflect.DeepEqual(created["task_id"], want) {
		t.Fatalf("created task_id = %v", created["task_id"])
	}
	if err := task.UpdatePriority(value_objects.PriorityHigh()); err != nil {
		t.Fatal(err)
	}
	last := task.Events[len(task.Events)-1].(interface{ ToDict() map[string]any }).ToDict()
	if !reflect.DeepEqual(last["task_id"], want) || last["event_type"] != "TaskUpdatedEvent" {
		t.Fatalf("updated event = %v", last)
	}
}
