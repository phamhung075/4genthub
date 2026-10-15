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
	if err := task.UpdateAssignees([]string{"@go-dev", "", "@x"}); err != nil {
		t.Fatal(err)
	}
	if strings.Join(task.Assignees, ",") != "@go-dev,@x" {
		t.Fatalf("assignees %v", task.Assignees)
	}
	if err := task.UpdateAssignees([]string{"coding-agent"}); err == nil || err.Error() != "Invalid assignees: ['coding-agent']. An assignee is '@<seat_key>'." {
		t.Fatalf("validate bare name: %v", err)
	}
	if err := task.UpdateAssignees([]string{"custom"}); err == nil || err.Error() != "Invalid assignees: ['custom']. An assignee is '@<seat_key>'." {
		t.Fatalf("validate: %v", err)
	}
	if strings.Join(task.Assignees, ",") != "@go-dev,@x" {
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
	// The note is the ledger's to build and number (NewProgressEntry); what is left on the entity is the
	// touch the write makes, and the entity keeps no copy of the note (the progress_history column is
	// gone).
	before := task.UpdatedAt
	if err := task.TouchForProgress(); err != nil {
		t.Fatalf("TouchForProgress: %v", err)
	}
	if task.UpdatedAt == before {
		t.Fatal("TouchForProgress did not advance updated_at")
	}
	note := NewProgressEntry(1, "hello", value_objects.IsoFormat(*task.UpdatedAt))
	if note.Content != "=== Progress 1 ===\nhello" || note.Number != 1 {
		t.Fatalf("progress note = %+v", note)
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

func TestProgressTextWithRendersALedgerNoteOnce(t *testing.T) {
	// The ledger is the only progress source. A reader renders its `progress` events ONCE each, in
	// progress order, deduped by the identity the payload declares - content and progress_number
	// together - which is the identity a carried copy shares with the note it copies. The ledger's
	// copies arrive OUT of order here, one of them is the carry's copy of another (carried_from), and
	// one note exists only in the ledger.
	task := newTestTask(t)
	written := NewProgressEntry(1, "first", "2026-01-01T00:00:00Z")

	liveEvent := &TaskEvent{
		Kind: TaskEventKindProgress,
		Payload: map[string]any{
			"content":         written.Content,
			"progress_number": written.Number,
			"timestamp":       written.Timestamp,
		},
	}
	carriedCopy := &TaskEvent{
		Kind: TaskEventKindProgress,
		Payload: map[string]any{
			"content":         written.Content,
			"progress_number": written.Number,
			"carried_from":    "progress_1",
		},
	}
	laterNoteOnlyInTheLedger := &TaskEvent{
		Kind:    TaskEventKindProgress,
		Payload: map[string]any{"content": "=== Progress 2 ===\nlater", "progress_number": float64(2)},
	}

	want := "=== Progress 1 ===\nfirst\n\n=== Progress 2 ===\nlater"
	if got := task.ProgressTextWith([]*TaskEvent{laterNoteOnlyInTheLedger, carriedCopy, liveEvent}); got != want {
		t.Fatalf("a copied note must render once, in order\n got: %q\nwant: %q", got, want)
	}

	// A kind that is not `progress` is not a note, whatever its payload happens to carry. This input
	// holds only the later ledger note and the claimed event, so the render is that one note: the
	// assertion is that the claimed event contributed nothing, not that a note it never received
	// appears.
	notANote := &TaskEvent{Kind: TaskEventKindClaimed, Payload: map[string]any{
		"content": "nope", "progress_number": float64(3),
	}}
	if got := task.ProgressTextWith([]*TaskEvent{laterNoteOnlyInTheLedger, notANote}); got != laterNoteOnlyInTheLedger.Payload["content"] {
		t.Fatalf("a non-progress event reached the notes: %q", got)
	}

	// The ledger is the whole source now: with no events there is nothing to render.
	if got := task.ProgressTextWith(nil); got != "" {
		t.Fatalf("nil events must render nothing, got %q", got)
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
	task.Assignees = []string{"@go-dev", "@lead"}
	d, err := task.ToDict()
	if err != nil || d["overall_progress"] != 0 || d["completion_summary"] != "" {
		t.Fatalf("dict: %v %v", err, d)
	}
	if got, ok := d["assignees"].([]string); !ok || !reflect.DeepEqual(got, []string{"@go-dev", "@lead"}) {
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

// A seat key is an '@'-prefixed assignee: NormalizeAssignees keeps it as given and
// any bare name (a role or otherwise) is refused.
func TestNormalizeAssigneesAcceptsSeatKeysAndRejectsBareUnknownNames(t *testing.T) {
	got, err := NormalizeAssignees([]string{"@go-dev", " @lead ", ""})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if strings.Join(got, ",") != "@go-dev,@lead" {
		t.Fatalf("validated = %v", got)
	}
	if _, err := NormalizeAssignees([]string{"go-dev"}); err == nil {
		t.Fatal("a bare name must be rejected")
	}
}

func TestTaskAddAssigneeUsesTheOneRule(t *testing.T) {
	task := newTestTask(t)
	for _, a := range []string{"@fe-dev", "@go-dev", "@go-dev"} {
		if err := task.AddAssignee(a); err != nil {
			t.Fatalf("AddAssignee(%q): %v", a, err)
		}
	}
	if strings.Join(task.Assignees, ",") != "@fe-dev,@go-dev" {
		t.Fatalf("assignees = %v", task.Assignees)
	}
	if err := task.AddAssignee("go-dev"); err == nil {
		t.Fatal("a bare name must be refused")
	}
	if strings.Join(task.Assignees, ",") != "@fe-dev,@go-dev" {
		t.Fatalf("a refused add must change nothing: %v", task.Assignees)
	}
}

// STEP 1(b) of the agent-library retirement (item 3, CHOICE B). A bare role name is no longer an
// assignee: '@<seat_key>' is the only assignee identity, so a bare name is refused whether or not it
// once named a role. The seat keys themselves are untouched.
func TestNormalizeAssigneesRefusesABareRoleName(t *testing.T) {
	if got, err := NormalizeAssignees([]string{"coding-agent"}); err == nil {
		t.Fatalf("NormalizeAssignees([\"coding-agent\"]) = %v, want a refusal: a bare role name is not an assignee", got)
	}

	got, err := NormalizeAssignees([]string{"@go-dev", " @lead "})
	if err != nil {
		t.Fatalf("seat keys must stay accepted: %v", err)
	}
	if strings.Join(got, ",") != "@go-dev,@lead" {
		t.Fatalf("validated = %v, want the seat keys kept", got)
	}
}

// The progress reader is honest about entries it cannot read (the post-gate minor on 2c4582de, board
// b668b4f6's item 1). WHY IT MATTERS: this function once rendered a history value that was not an object as an
// EMPTY line, because reading a non-map through a nil map yields "" - and an empty line joined into the details
// is indistinguishable from a real note whose text is blank. That is the shape that reported two notes as lost,
// so the entry now contributes NOTHING rather than a blank.
func TestTheProgressReaderSkipsEntriesItCannotRead(t *testing.T) {
	// Called as the package function, which is how the subtask route reaches it (converters.go:182):
	// the ledger line removed the entity's progress column, so no Task is built with one any more.
	got := ProgressHistoryText(map[string]any{
		"1": map[string]any{"content": "=== Progress 1 ===\nfirst", "progress_number": 1},
		"2": "not an object at all",                              // the value that used to be read through a nil map
		"3": map[string]any{"content": 42, "progress_number": 3}, // a content that is not a string
		"4": map[string]any{"progress_number": 4},                // no content at all
		"5": map[string]any{"content": "=== Progress 5 ===\nlast", "progress_number": 5},
	})

	want := "=== Progress 1 ===\nfirst\n\n=== Progress 5 ===\nlast"
	if got != want {
		t.Fatalf("ProgressHistoryText() = %q, want %q: an unreadable entry must contribute nothing rather than a blank line", got, want)
	}
	if strings.Contains(got, "\n\n\n") {
		t.Fatalf("ProgressHistoryText() = %q has an empty entry between the separators", got)
	}
}
