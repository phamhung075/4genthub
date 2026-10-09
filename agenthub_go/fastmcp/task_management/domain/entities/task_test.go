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
	if err := task.UpdateAssignees([]string{"coding-agent", "", "@x"}); err != nil {
		t.Fatal(err)
	}
	if strings.Join(task.Assignees, ",") != "@coding-agent,@x" {
		t.Fatalf("assignees %v", task.Assignees)
	}
	if err := task.UpdateAssignees([]string{"custom"}); err == nil || err.Error() != "Invalid assignees: ['custom']. An assignee is '@<seat_key>' or a known agent role." {
		t.Fatalf("validate: %v", err)
	}
	if strings.Join(task.Assignees, ",") != "@coding-agent,@x" {
		t.Fatalf("a rejected update must leave assignees unchanged: %v", task.Assignees)
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

// ToDict carries assignees as stored: the client compares the response's assignees against
// '@<seat_key>' values, so resolving them here (which stripped the '@' and appended '-agent') made
// every comparison miss. The Python normalised in to_dict; this departure is deliberate.
func TestTaskToDictCarriesAssigneesAsStored(t *testing.T) {
	task := newTestTask(t)
	task.Assignees = []string{"@coding-agent", "bob"}
	d, err := task.ToDict()
	if err != nil || d["overall_progress"] != 0 || d["completion_summary"] != "" {
		t.Fatalf("dict: %v %v", err, d)
	}
	if got, ok := d["assignees"].([]string); !ok || !reflect.DeepEqual(got, []string{"@coding-agent", "bob"}) {
		t.Fatalf("assignees = %#v, want the stored values unchanged", d["assignees"])
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

// A seat key is an '@'-prefixed assignee: NormalizeAssignees keeps it as given, a bare
// known role gets the prefix and a bare name that is no role is rejected.
func TestNormalizeAssigneesAcceptsSeatKeysAndRejectsBareUnknownNames(t *testing.T) {
	got, err := NormalizeAssignees([]string{"@go-dev", " @lead ", "coding-agent", ""})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if strings.Join(got, ",") != "@go-dev,@lead,@coding-agent" {
		t.Fatalf("validated = %v", got)
	}
	if _, err := NormalizeAssignees([]string{"go-dev"}); err == nil {
		t.Fatal("a bare name that is no role must be rejected")
	}
}

func TestTaskAddAssigneeUsesTheOneRule(t *testing.T) {
	task := newTestTask(t)
	for _, a := range []string{"coding-agent", "@go-dev", "@go-dev"} {
		if err := task.AddAssignee(a); err != nil {
			t.Fatalf("AddAssignee(%q): %v", a, err)
		}
	}
	if strings.Join(task.Assignees, ",") != "@coding-agent,@go-dev" {
		t.Fatalf("assignees = %v", task.Assignees)
	}
	if err := task.AddAssignee("go-dev"); err == nil {
		t.Fatal("a bare name that is no role must be refused")
	}
	if strings.Join(task.Assignees, ",") != "@coding-agent,@go-dev" {
		t.Fatalf("a refused add must change nothing: %v", task.Assignees)
	}
}
