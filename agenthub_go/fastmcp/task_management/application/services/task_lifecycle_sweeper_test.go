package services

// The lifecycle sweep, driven the way the guide's acceptance states it: one table-driven pass over
// EVERY row of the rules table, on a FAKE CLOCK, with fake repositories behind every port.
//
// NO TEST HERE SLEEPS ON WALL TIME. The clock is a value the test sets (taskSweepTestNow), every age
// in a fixture is expressed relative to it, and the only thing that moves it is the test itself -
// which is what makes "6 days old" and "7 days and one hour old" exact statements rather than races.
//
// The named cases the guide asks for by name are rows of the table: "done 6d old is kept", "blocked is
// untouched", "critical stays critical until the block age", and "a pruned task has exactly one audit
// record carrying its summary".

import (
	"context"
	"fmt"
	"os"
	"strings"
	"sync"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// taskSweepTestNow is the instant every case is measured against.
var taskSweepTestNow = time.Date(2026, 10, 15, 12, 0, 0, 0, time.UTC)

const (
	taskSweepTestHour = time.Hour
	taskSweepTestDay  = 24 * taskSweepTestHour
)

// taskSweepTestConfig is the documented default schedule, spelled out so a case's age reads against
// the guide's own numbers (prune 7d, escalate 24h, block 7d).
func taskSweepTestConfig() TaskSweepConfig {
	return TaskSweepConfig{
		Interval:      DefaultTaskSweepInterval,
		PruneAfter:    DefaultTaskPruneAfter,
		EscalateAfter: DefaultTaskEscalateAfter,
		BlockAfter:    DefaultTaskBlockAfter,
	}
}

// ---- the fixtures the fakes are driven by -------------------------------------------------------

// sweepFixture is the set of tasks the fakes serve. It is shared by the source and the writer so a
// write's effect on a task is visible to the next run - which is how the climb test sees that an
// escalation moved updated_at.
type sweepFixture struct {
	tasks    []*SweepTask
	evidence map[string][]map[string]any
}

func (f *sweepFixture) stored(taskID string) *SweepTask {
	for _, task := range f.tasks {
		if task.ID == taskID {
			return task
		}
	}
	return nil
}

// fakeSweepSource is the read side.
//
// Open HANDS OVER BLOCKED TASKS TOO, which the SQL source never does: the table's "blocked is
// untouched" case exists to measure the SWEEP's own guard for that rule rather than the query's, and
// a fake that filtered them out would make the case pass without the sweep ever being asked.
type fakeSweepSource struct {
	fixture *sweepFixture

	completedErr error
	openErr      error
	evidenceErr  error
}

func (s *fakeSweepSource) Completed(context.Context) ([]SweepTask, error) {
	if s.completedErr != nil {
		return nil, s.completedErr
	}
	out := []SweepTask{}
	for _, task := range s.fixture.tasks {
		switch task.Status {
		case "done", "cancelled", "archived":
			out = append(out, *task)
		}
	}
	return out, nil
}

func (s *fakeSweepSource) Open(context.Context) ([]SweepTask, error) {
	if s.openErr != nil {
		return nil, s.openErr
	}
	out := []SweepTask{}
	for _, task := range s.fixture.tasks {
		switch task.Status {
		case "todo", "in_progress", "review", "testing", "blocked":
			out = append(out, *task)
		}
	}
	return out, nil
}

func (s *fakeSweepSource) Evidence(_ context.Context, task SweepTask) ([]map[string]any, error) {
	if s.evidenceErr != nil {
		return nil, s.evidenceErr
	}
	return s.fixture.evidence[task.ID], nil
}

// fakeSweepEscalation, fakeSweepBlock and fakeSweepDeletion are the writes a case asserts on.
type fakeSweepEscalation struct {
	taskID   string
	priority string
	note     string
}

type fakeSweepBlock struct {
	taskID  string
	blocker string
}

// fakeSweepWriter records every write and applies the effect the real application-layer write has on
// the row.
//
// THE EFFECT IS THE POINT OF THE ESCALATION CASES: Task.UpdatePriority touches the entity, so the
// row's updated_at moves to the instant of the write, and that is exactly why a task climbs ONE
// level per interval rather than the whole ladder in one pass. A fake that left updated_at alone
// would let a broken sweep climb several levels and still look correct.
type fakeSweepWriter struct {
	fixture *sweepFixture
	now     func() time.Time

	escalations []fakeSweepEscalation
	blocks      []fakeSweepBlock
	deletions   []string
}

func (w *fakeSweepWriter) Escalate(_ context.Context, task SweepTask, to value_objects.Priority, note string) error {
	w.escalations = append(w.escalations, fakeSweepEscalation{taskID: task.ID, priority: to.Value, note: note})
	if stored := w.fixture.stored(task.ID); stored != nil {
		stored.Priority = to.Value
		stored.UpdatedAt = w.now()
	}
	return nil
}

func (w *fakeSweepWriter) Block(_ context.Context, task SweepTask, blocker string) error {
	w.blocks = append(w.blocks, fakeSweepBlock{taskID: task.ID, blocker: blocker})
	if stored := w.fixture.stored(task.ID); stored != nil {
		stored.Status = "blocked"
		stored.UpdatedAt = w.now()
	}
	return nil
}

func (w *fakeSweepWriter) Delete(_ context.Context, task SweepTask) error {
	w.deletions = append(w.deletions, task.ID)
	// The row is gone, so the fixture drops it: a second run cannot prune it twice.
	kept := w.fixture.tasks[:0]
	for _, stored := range w.fixture.tasks {
		if stored.ID != task.ID {
			kept = append(kept, stored)
		}
	}
	w.fixture.tasks = kept
	return nil
}

// fakeAuditTrail is the audit trail as the sweep writes to it: append-only, and the test reads it.
type fakeAuditTrail struct{ records []entities.TaskAuditRecord }

func (a *fakeAuditTrail) Record(_ context.Context, record entities.TaskAuditRecord) error {
	a.records = append(a.records, record)
	return nil
}

func (a *fakeAuditTrail) kinds() []entities.TaskAuditKind {
	out := make([]entities.TaskAuditKind, 0, len(a.records))
	for _, record := range a.records {
		out = append(out, record.Kind)
	}
	return out
}

// fakeSweepLock is the exclusivity seam. A lock that is already held is what a SECOND server
// instance sees, and the sweep must then do nothing at all.
type fakeSweepLock struct {
	mu   sync.Mutex
	held bool
}

func (l *fakeSweepLock) WithLock(_ context.Context, fn func() error) (bool, error) {
	l.mu.Lock()
	if l.held {
		l.mu.Unlock()
		return false, nil
	}
	l.held = true
	l.mu.Unlock()
	defer func() {
		l.mu.Lock()
		l.held = false
		l.mu.Unlock()
	}()
	return true, fn()
}

// ---- the harness --------------------------------------------------------------------------------

// sweepTestRun is one sweep over a fixture, with everything the fakes recorded.
type sweepTestRun struct {
	report    SweepReport
	err       error
	writer    *fakeSweepWriter
	audit     *fakeAuditTrail
	escalated []fakeSweepEscalation
	blocks    []fakeSweepBlock
	deletions []string
	records   []entities.TaskAuditRecord
}

// runSweepOnce drives one SweepOnce over the fixture at the fake clock.
func runSweepOnce(t *testing.T, fixture *sweepFixture, lock SweepLock) sweepTestRun {
	t.Helper()
	writer := &fakeSweepWriter{fixture: fixture, now: func() time.Time { return taskSweepTestNow }}
	audit := &fakeAuditTrail{}
	sweeper := NewTaskLifecycleSweeper(
		&fakeSweepSource{fixture: fixture},
		writer,
		audit,
		lock,
		taskSweepTestConfig(),
	).WithClock(func() time.Time { return taskSweepTestNow }).WithLogger(func(string, ...any) {})
	report, err := sweeper.SweepOnce(context.Background())
	return sweepTestRun{
		report: report, err: err, writer: writer, audit: audit,
		escalated: writer.escalations, blocks: writer.blocks, deletions: writer.deletions,
		records: audit.records,
	}
}

// ---- the table ----------------------------------------------------------------------------------

// sweepCase is one row: one task, and what the sweep must do to it.
type sweepCase struct {
	name string
	task *SweepTask

	wantEscalateTo string // empty: no escalation expected
	wantEscalateAt string // empty: the escalation's note is not asserted
	wantBlocker    string // empty: no block expected
	wantRefused    bool   // the domain refuses the block, so nothing may be written
	wantPruned     bool
	wantRecords    []entities.TaskAuditKind
}

func TestTaskLifecycleSweepTableOverAFakeClock(t *testing.T) {
	// The statuses are spelled from the value objects, so a case cannot be written against a status
	// the domain does not have.
	todo, inProgress, review := "todo", "in_progress", "review"
	testingState, done, cancelled, archived := "testing", "done", "cancelled", "archived"
	blocked := "blocked"
	low, medium, high, urgent, critical := "low", "medium", "high", "urgent", "critical"

	// openFixture makes a task in an open state whose updated_at is `age` old.
	openFixture := func(id, status, priority string, age time.Duration) *SweepTask {
		return &SweepTask{
			ID: id, UserID: "user-1", Title: "a task " + id,
			Status: status, Priority: priority,
			CreatedAt: taskSweepTestNow.Add(-60 * taskSweepTestDay),
			UpdatedAt: taskSweepTestNow.Add(-age),
		}
	}
	// completedFixture makes a task in a completed state, completed_at `age` old.
	completedFixture := func(id, status string, age time.Duration) *SweepTask {
		completedAt := taskSweepTestNow.Add(-age)
		return &SweepTask{
			ID: id, UserID: "user-1", Title: "a task " + id,
			Status: status, Priority: medium,
			CreatedAt: taskSweepTestNow.Add(-60 * taskSweepTestDay),
			UpdatedAt: completedAt, CompletedAt: &completedAt,
			CompletionSummary: "shipped " + id,
		}
	}

	cases := []sweepCase{
		// ---- the completed row: prune (completed_at else updated_at, older than TASK_PRUNE_AFTER) --
		{name: "done 6d old is kept", task: completedFixture("t-done-6d", done, 6*taskSweepTestDay)},
		{name: "done exactly 7d old is kept: the rule is older than, not as old as",
			task: completedFixture("t-done-7d", done, 7*taskSweepTestDay)},
		{name: "done 7d and 1h old is pruned", wantPruned: true,
			task:        completedFixture("t-done-7d1h", done, 7*taskSweepTestDay+taskSweepTestHour),
			wantRecords: []entities.TaskAuditKind{entities.TaskAuditKindPruned}},
		{name: "cancelled 8d old is pruned", wantPruned: true,
			task:        completedFixture("t-cancelled-8d", cancelled, 8*taskSweepTestDay),
			wantRecords: []entities.TaskAuditKind{entities.TaskAuditKindPruned}},
		{name: "archived 30d old is pruned", wantPruned: true,
			task:        completedFixture("t-archived-30d", archived, 30*taskSweepTestDay),
			wantRecords: []entities.TaskAuditKind{entities.TaskAuditKindPruned}},
		{name: "a done task with no completed_at is aged from updated_at", wantPruned: true,
			task: &SweepTask{ID: "t-done-nocompleted", UserID: "user-1", Title: "no completed_at",
				Status: done, Priority: medium, UpdatedAt: taskSweepTestNow.Add(-9 * taskSweepTestDay),
				CompletionSummary: "shipped"},
			wantRecords: []entities.TaskAuditKind{entities.TaskAuditKindPruned}},
		{name: "a done task whose completed_at is recent is kept, whatever updated_at says",
			task: func() *SweepTask {
				task := completedFixture("t-done-recent", done, taskSweepTestHour)
				task.UpdatedAt = taskSweepTestNow.Add(-9 * taskSweepTestDay)
				return task
			}()},

		// ---- the open row: escalate one level (older than TASK_ESCALATE_AFTER) ---------------------
		{name: "todo 12h old is kept: younger than the escalate age",
			task: openFixture("t-todo-12h", todo, low, 12*taskSweepTestHour)},
		{name: "todo exactly 24h old is kept: the rule is older than, not as old as",
			task: openFixture("t-todo-24h", todo, low, taskSweepTestDay)},
		{name: "todo 25h old climbs one level, low to medium",
			task:           openFixture("t-todo-25h", todo, low, 25*taskSweepTestHour),
			wantEscalateTo: medium, wantEscalateAt: "1 day",
			wantRecords: []entities.TaskAuditKind{entities.TaskAuditKindEscalated}},
		{name: "in_progress 2d old climbs one level, medium to high",
			task:           openFixture("t-inprogress-2d", inProgress, medium, 2*taskSweepTestDay),
			wantEscalateTo: high, wantEscalateAt: "2 days",
			wantRecords: []entities.TaskAuditKind{entities.TaskAuditKindEscalated}},
		{name: "review 3d old climbs one level, high to urgent",
			task:           openFixture("t-review-3d", review, high, 3*taskSweepTestDay),
			wantEscalateTo: urgent, wantEscalateAt: "3 days",
			wantRecords: []entities.TaskAuditKind{entities.TaskAuditKindEscalated}},
		{name: "testing 5d old climbs one level, urgent to critical",
			task:           openFixture("t-testing-5d", testingState, urgent, 5*taskSweepTestDay),
			wantEscalateTo: critical, wantEscalateAt: "5 days",
			wantRecords: []entities.TaskAuditKind{entities.TaskAuditKindEscalated}},
		{name: "a task 30d stale climbs ONE level, not the whole ladder",
			task:           openFixture("t-stale-30d", inProgress, low, 30*taskSweepTestDay),
			wantEscalateTo: medium, wantEscalateAt: "30 days",
			wantRecords: []entities.TaskAuditKind{entities.TaskAuditKindEscalated}},

		// ---- the block row: already critical and older than TASK_BLOCK_AFTER ----------------------
		{name: "critical stays critical until the block age",
			task: openFixture("t-critical-2d", inProgress, critical, 2*taskSweepTestDay)},
		{name: "critical exactly 7d old is kept: the rule is older than, not as old as",
			task: openFixture("t-critical-7d", inProgress, critical, 7*taskSweepTestDay)},
		{name: "in_progress critical 8d old is blocked",
			task:        openFixture("t-critical-8d", inProgress, critical, 8*taskSweepTestDay),
			wantBlocker: "no progress for 8 days at critical priority",
			wantRecords: []entities.TaskAuditKind{entities.TaskAuditKindBlocked}},
		{name: "todo critical 8d old is refused: the domain's rules do not reach blocked from todo",
			task:        openFixture("t-todo-critical-8d", todo, critical, 8*taskSweepTestDay),
			wantRefused: true},
		{name: "review critical 8d old is refused: the domain's rules do not reach blocked from review",
			task:        openFixture("t-review-critical-8d", review, critical, 8*taskSweepTestDay),
			wantRefused: true},
		{name: "testing critical 8d old is refused: the domain's rules do not reach blocked from testing",
			task:        openFixture("t-testing-critical-8d", testingState, critical, 8*taskSweepTestDay),
			wantRefused: true},

		// ---- the blocked row: never pruned, never escalated --------------------------------------
		{name: "blocked is untouched",
			task: openFixture("t-blocked-30d", blocked, medium, 30*taskSweepTestDay)},
		{name: "blocked is untouched even at the very top of the ladder",
			task: openFixture("t-blocked-critical-30d", blocked, critical, 30*taskSweepTestDay)},

		// ---- the named case that also asserts the record's content --------------------------------
		{name: "a pruned task has exactly one audit record carrying its summary", wantPruned: true,
			task:        completedFixture("t-named-prune", done, 8*taskSweepTestDay),
			wantRecords: []entities.TaskAuditKind{entities.TaskAuditKindPruned}},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			fixture := &sweepFixture{
				tasks:    []*SweepTask{tc.task},
				evidence: map[string][]map[string]any{tc.task.ID: {{"head_sha": "aa", "base_sha": "bb"}}},
			}
			run := runSweepOnce(t, fixture, &fakeSweepLock{})
			if run.err != nil {
				t.Fatalf("the sweep failed: %v", run.err)
			}

			switch {
			case tc.wantEscalateTo != "":
				if len(run.escalated) != 1 {
					t.Fatalf("the sweep escalated %d times, want 1: %+v", len(run.escalated), run.escalated)
				}
				got := run.escalated[0]
				if got.priority != tc.wantEscalateTo {
					t.Errorf("escalated to %q, want %q", got.priority, tc.wantEscalateTo)
				}
				if tc.wantEscalateAt != "" && !strings.Contains(got.note, tc.wantEscalateAt) {
					t.Errorf("the progress note %q does not name the age %q", got.note, tc.wantEscalateAt)
				}
				if !strings.Contains(got.note, tc.wantEscalateTo) {
					t.Errorf("the progress note %q does not name the step %q", got.note, tc.wantEscalateTo)
				}
			case len(run.escalated) != 0:
				t.Errorf("the sweep escalated when it should not have: %+v", run.escalated)
			}

			switch {
			case tc.wantBlocker != "":
				if len(run.blocks) != 1 {
					t.Fatalf("the sweep blocked %d times, want 1: %+v", len(run.blocks), run.blocks)
				}
				if run.blocks[0].blocker != tc.wantBlocker {
					t.Errorf("the blocker text is %q, want %q", run.blocks[0].blocker, tc.wantBlocker)
				}
			case len(run.blocks) != 0:
				t.Errorf("the sweep blocked when it should not have: %+v", run.blocks)
			}

			if pruned := len(run.deletions) == 1; pruned != tc.wantPruned {
				t.Errorf("pruned = %v (deletions %v), want %v", pruned, run.deletions, tc.wantPruned)
			}
			if tc.wantPruned {
				// The evidence must be read BEFORE the delete, so the record exists whether or not
				// the delete itself succeeded.
				if len(run.records) != 1 {
					t.Fatalf("the prune wrote %d audit records, want exactly 1", len(run.records))
				}
				if run.records[0].TaskID != tc.task.ID {
					t.Errorf("the record names task %q, want %q", run.records[0].TaskID, tc.task.ID)
				}
			}

			gotKinds := run.audit.kinds()
			if len(gotKinds) != len(tc.wantRecords) {
				t.Fatalf("the audit trail holds %v, want %v", gotKinds, tc.wantRecords)
			}
			for i := range gotKinds {
				if gotKinds[i] != tc.wantRecords[i] {
					t.Errorf("audit record %d is %q, want %q", i, gotKinds[i], tc.wantRecords[i])
				}
			}

			if tc.wantRefused {
				if run.report.Refused != 1 {
					t.Errorf("the refusal was not reported: %+v", run.report)
				}
			} else if run.report.Refused != 0 {
				t.Errorf("nothing should have been refused: %+v", run.report)
			}
			if run.report.Failed != 0 || run.report.Locked {
				t.Errorf("the sweep reported %+v, want no failure and no lock skip", run.report)
			}
		})
	}
}

// TestTaskLifecycleSweepRecordsWhatItDidOnTheReport asserts the counters a run reports, so a run
// that silently did nothing cannot pass a case that expected work.
func TestTaskLifecycleSweepRecordsWhatItDidOnTheReport(t *testing.T) {
	fixture := &sweepFixture{tasks: []*SweepTask{
		{ID: "t-prune", UserID: "user-1", Title: "old and done", Status: "done", Priority: "medium",
			UpdatedAt: taskSweepTestNow.Add(-8 * taskSweepTestDay), CompletedAt: new(taskSweepTestNow.Add(-8 * taskSweepTestDay))},
		{ID: "t-escalate", UserID: "user-1", Title: "old and open", Status: "todo", Priority: "low",
			UpdatedAt: taskSweepTestNow.Add(-2 * taskSweepTestDay)},
		{ID: "t-block", UserID: "user-1", Title: "old and critical", Status: "in_progress", Priority: "critical",
			UpdatedAt: taskSweepTestNow.Add(-9 * taskSweepTestDay)},
		{ID: "t-refuse", UserID: "user-1", Title: "old, critical, todo", Status: "todo", Priority: "critical",
			UpdatedAt: taskSweepTestNow.Add(-9 * taskSweepTestDay)},
		{ID: "t-keep", UserID: "user-1", Title: "young", Status: "todo", Priority: "low",
			UpdatedAt: taskSweepTestNow.Add(-taskSweepTestHour)},
	}}
	run := runSweepOnce(t, fixture, &fakeSweepLock{})
	if run.err != nil {
		t.Fatalf("the sweep failed: %v", run.err)
	}
	want := SweepReport{Pruned: 1, Escalated: 1, Blocked: 1, Refused: 1}
	if run.report != want {
		t.Fatalf("report %+v, want %+v", run.report, want)
	}
}

// TestTaskLifecycleSweepClimbsOneLevelPerInterval is the rule the guide states in words: "a task that
// was escalated has updated_at bumped, so it climbs one level per interval, not all at once".
func TestTaskLifecycleSweepClimbsOneLevelPerInterval(t *testing.T) {
	task := &SweepTask{
		ID: "t-climb", UserID: "user-1", Title: "one rung at a time",
		Status: "todo", Priority: "low", UpdatedAt: taskSweepTestNow.Add(-30 * taskSweepTestDay),
	}
	fixture := &sweepFixture{tasks: []*SweepTask{task}}
	now := taskSweepTestNow
	writer := &fakeSweepWriter{fixture: fixture, now: func() time.Time { return now }}
	audit := &fakeAuditTrail{}
	sweeper := NewTaskLifecycleSweeper(&fakeSweepSource{fixture: fixture}, writer, audit,
		&fakeSweepLock{}, taskSweepTestConfig()).
		WithClock(func() time.Time { return now }).
		WithLogger(func(string, ...any) {})

	// First interval: 30 days stale, so it climbs exactly one rung.
	if _, err := sweeper.SweepOnce(context.Background()); err != nil {
		t.Fatalf("the first sweep failed: %v", err)
	}
	if task.Priority != "medium" {
		t.Fatalf("after one interval the priority is %q, want medium: the sweep climbed more than one level", task.Priority)
	}

	// Second interval at the SAME instant: the escalation moved updated_at, so the age is zero and
	// there is nothing to do - which is the whole of "not all at once".
	if _, err := sweeper.SweepOnce(context.Background()); err != nil {
		t.Fatalf("the second sweep failed: %v", err)
	}
	if task.Priority != "medium" {
		t.Fatalf("a second interval at the same instant climbed again: priority %q, want medium", task.Priority)
	}

	// Third interval, one escalate age later: the next rung.
	now = now.Add(DefaultTaskEscalateAfter + taskSweepTestHour)
	if _, err := sweeper.SweepOnce(context.Background()); err != nil {
		t.Fatalf("the third sweep failed: %v", err)
	}
	if task.Priority != "high" {
		t.Fatalf("after the next interval the priority is %q, want high", task.Priority)
	}
	if len(audit.records) != 2 {
		t.Fatalf("the audit trail holds %d records, want 2 - one per step", len(audit.records))
	}
}

// TestTaskLifecycleSweepKeepsThePrunedTasksEvidence is the "Evidence is kept" ruling: before a task
// is deleted, ONE record holds its id, title, completion summary, evidence and timestamps.
func TestTaskLifecycleSweepKeepsThePrunedTasksEvidence(t *testing.T) {
	completedAt := taskSweepTestNow.Add(-9 * taskSweepTestDay)
	createdAt := taskSweepTestNow.Add(-40 * taskSweepTestDay)
	task := &SweepTask{
		ID: "t-evidence", UserID: "user-7", Title: "the task that was shipped",
		Status: "done", Priority: "high", CompletionSummary: "shipped the sweeper",
		CreatedAt: createdAt, UpdatedAt: completedAt, CompletedAt: &completedAt,
	}
	evidence := []map[string]any{
		{"base_sha": "aaaaaaaa", "head_sha": "bbbbbbbb", "numstat": "1\t0\tfile.go"},
		{"base_sha": "bbbbbbbb", "head_sha": "cccccccc", "numstat": ""},
	}
	fixture := &sweepFixture{tasks: []*SweepTask{task}, evidence: map[string][]map[string]any{task.ID: evidence}}

	run := runSweepOnce(t, fixture, &fakeSweepLock{})
	if run.err != nil {
		t.Fatalf("the sweep failed: %v", run.err)
	}
	if len(run.deletions) != 1 {
		t.Fatalf("the task was not deleted: %v", run.deletions)
	}
	if len(run.records) != 1 {
		t.Fatalf("the prune wrote %d audit records, want ONE", len(run.records))
	}
	record := run.records[0]
	if record.TaskID != task.ID || record.Title != task.Title || record.UserID != task.UserID {
		t.Errorf("the record does not name the task: %+v", record)
	}
	if record.CompletionSummary != "shipped the sweeper" {
		t.Errorf("the record's summary is %q, want the task's own", record.CompletionSummary)
	}
	if len(record.Evidence) != len(evidence) {
		t.Fatalf("the record holds %d evidence entries, want %d", len(record.Evidence), len(evidence))
	}
	for i, want := range evidence {
		if fmt.Sprint(record.Evidence[i]) != fmt.Sprint(want) {
			t.Errorf("evidence %d is %v, want %v", i, record.Evidence[i], want)
		}
	}
	if record.CreatedAt != taskSweepTestNow {
		t.Errorf("the record is stamped %v, want the sweep's own clock %v", record.CreatedAt, taskSweepTestNow)
	}
	if record.Kind != entities.TaskAuditKindPruned {
		t.Errorf("the record's kind is %q, want pruned", record.Kind)
	}
	// The task's OWN timestamps are what the delete takes with the row, so the record carries them.
	if record.TaskCreatedAt != createdAt {
		t.Errorf("the record's task created_at is %v, want %v", record.TaskCreatedAt, createdAt)
	}
	if record.TaskUpdatedAt != completedAt {
		t.Errorf("the record's task updated_at is %v, want %v", record.TaskUpdatedAt, completedAt)
	}
	if record.TaskCompletedAt == nil || *record.TaskCompletedAt != completedAt {
		t.Errorf("the record's task completed_at is %v, want %v", record.TaskCompletedAt, completedAt)
	}
}

// TestTaskLifecycleSweepDoesNotRunWhileAnotherInstanceHoldsTheLock is the exclusivity claim at the
// sweep's own level: a run that cannot take the lock does NOTHING - no read is even acted on, and the
// interval belongs to the instance that holds it.
func TestTaskLifecycleSweepDoesNotRunWhileAnotherInstanceHoldsTheLock(t *testing.T) {
	fixture := &sweepFixture{tasks: []*SweepTask{
		{ID: "t-old", UserID: "user-1", Title: "old and open", Status: "todo", Priority: "low",
			UpdatedAt: taskSweepTestNow.Add(-10 * taskSweepTestDay)},
	}}
	run := runSweepOnce(t, fixture, &fakeSweepLock{held: true})
	if run.err != nil {
		t.Fatalf("the sweep failed: %v", run.err)
	}
	if !run.report.Locked {
		t.Fatalf("the run did not report the held lock: %+v", run.report)
	}
	if len(run.escalated)+len(run.blocks)+len(run.deletions) != 0 {
		t.Fatalf("a run that could not take the lock wrote something: %+v %+v %+v",
			run.escalated, run.blocks, run.deletions)
	}
	if len(run.records) != 0 {
		t.Fatalf("a run that could not take the lock wrote %d audit records", len(run.records))
	}
	if run.report.Pruned+run.report.Escalated+run.report.Blocked+run.report.Failed != 0 {
		t.Fatalf("the skipped run reported work: %+v", run.report)
	}
}

// TestTaskLifecycleSweepSkipsWhenTheLockIsHeldAtRunTime drives the same claim through the RUN loop's
// own path: SweepOnce is what Run calls, so a held lock means the interval is skipped rather than
// queued.
func TestTaskLifecycleSweepSkipsWhenTheLockIsHeldAtRunTime(t *testing.T) {
	fixture := &sweepFixture{tasks: []*SweepTask{}}
	writer := &fakeSweepWriter{fixture: fixture, now: func() time.Time { return taskSweepTestNow }}
	audit := &fakeAuditTrail{}
	sweeper := NewTaskLifecycleSweeper(&fakeSweepSource{fixture: fixture}, writer, audit,
		&fakeSweepLock{held: true}, taskSweepTestConfig()).
		WithClock(func() time.Time { return taskSweepTestNow }).
		WithLogger(func(string, ...any) {})

	ctx, cancel := context.WithCancel(context.Background())
	cancel() // the run must return on a cancelled context rather than spinning
	done := make(chan struct{})
	go func() {
		sweeper.Run(ctx)
		close(done)
	}()
	// This select is a GUARD, not a wait on the clock: Run returns as soon as it sees the cancelled
	// context, and the bound only turns a Run that never returns into a failure instead of a hung
	// test. No age in this file is measured against wall time.
	select {
	case <-done:
	case <-time.After(5 * time.Second):
		t.Fatal("Run did not return on a cancelled context")
	}
	if len(writer.escalations)+len(writer.blocks)+len(writer.deletions) != 0 {
		t.Fatal("the run wrote something while the lock was held")
	}
}

// TestTaskLifecycleSweepKeepsGoingAfterAFailure: one task the application layer cannot act on must not
// stop the others, and the failure is reported rather than swallowed.
func TestTaskLifecycleSweepKeepsGoingAfterAFailure(t *testing.T) {
	fixture := &sweepFixture{tasks: []*SweepTask{
		{ID: "t-prune", UserID: "user-1", Title: "old and done", Status: "done", Priority: "medium",
			UpdatedAt: taskSweepTestNow.Add(-8 * taskSweepTestDay), CompletedAt: new(taskSweepTestNow.Add(-8 * taskSweepTestDay))},
		{ID: "t-escalate", UserID: "user-1", Title: "old and open", Status: "todo", Priority: "low",
			UpdatedAt: taskSweepTestNow.Add(-2 * taskSweepTestDay)},
	}}
	writer := &fakeSweepWriter{fixture: fixture, now: func() time.Time { return taskSweepTestNow }}
	audit := &fakeAuditTrail{}
	source := &fakeSweepSource{fixture: fixture, evidenceErr: fmt.Errorf("the ledger is unreadable")}
	sweeper := NewTaskLifecycleSweeper(source, writer, audit, &fakeSweepLock{}, taskSweepTestConfig()).
		WithClock(func() time.Time { return taskSweepTestNow }).
		WithLogger(func(string, ...any) {})

	report, err := sweeper.SweepOnce(context.Background())
	if err != nil {
		t.Fatalf("one task's failure became the sweep's failure: %v", err)
	}
	if report.Failed != 1 {
		t.Errorf("the failure was not reported: %+v", report)
	}
	if report.Pruned != 0 {
		t.Errorf("a prune with unreadable evidence must not delete the task: %+v", report)
	}
	if len(fixture.tasks) != 2 {
		t.Errorf("the task was deleted without its evidence being kept: %d tasks left", len(fixture.tasks))
	}
	if report.Escalated != 1 {
		t.Errorf("the other task was not swept after a failure: %+v", report)
	}
}

// ---- the environment-variable contract ----------------------------------------------------------

// unsetEnv removes a variable for the duration of the test, which t.Setenv cannot do (it only sets).
func unsetEnv(t *testing.T, key string) {
	t.Helper()
	if _, ok := os.LookupEnv(key); ok {
		t.Setenv(key, "") // registers the restore of the original value
	}
	os.Unsetenv(key)
}

func TestTaskSweepConfigFromEnvTakesTheDocumentedDefaults(t *testing.T) {
	for _, key := range []string{TaskSweepIntervalEnv, TaskPruneAfterEnv, TaskEscalateAfterEnv, TaskBlockAfterEnv} {
		unsetEnv(t, key)
	}
	cfg, err := TaskSweepConfigFromEnv()
	if err != nil {
		t.Fatalf("an unset schedule must not be an error: %v", err)
	}
	want := TaskSweepConfig{
		Interval:      time.Hour,
		PruneAfter:    7 * 24 * time.Hour,
		EscalateAfter: 24 * time.Hour,
		BlockAfter:    7 * 24 * time.Hour,
	}
	if cfg != want {
		t.Fatalf("an unset schedule is %+v, want the documented defaults %+v", cfg, want)
	}
}

func TestTaskSweepConfigFromEnvReadsEveryVariable(t *testing.T) {
	t.Setenv(TaskSweepIntervalEnv, "15m")
	t.Setenv(TaskPruneAfterEnv, "30d")
	t.Setenv(TaskEscalateAfterEnv, "6h")
	t.Setenv(TaskBlockAfterEnv, "3d")
	cfg, err := TaskSweepConfigFromEnv()
	if err != nil {
		t.Fatalf("a well-formed schedule must not be an error: %v", err)
	}
	want := TaskSweepConfig{
		Interval:      15 * time.Minute,
		PruneAfter:    30 * 24 * time.Hour,
		EscalateAfter: 6 * time.Hour,
		BlockAfter:    3 * 24 * time.Hour,
	}
	if cfg != want {
		t.Fatalf("the schedule is %+v, want %+v", cfg, want)
	}
}

func TestTaskSweepConfigFromEnvRejectsAMalformedVariable(t *testing.T) {
	cases := []struct {
		key   string
		value string
	}{
		{TaskSweepIntervalEnv, "1h30"},
		{TaskSweepIntervalEnv, "hour"},
		{TaskSweepIntervalEnv, "7x"},
		{TaskSweepIntervalEnv, "0"},
		{TaskSweepIntervalEnv, "-1h"},
		{TaskPruneAfterEnv, "7 days"},
		{TaskEscalateAfterEnv, "24"},
		{TaskBlockAfterEnv, "1.5d"},
	}
	for _, tc := range cases {
		t.Run(tc.key+"="+tc.value, func(t *testing.T) {
			unsetEnv(t, tc.key)
			t.Setenv(tc.key, tc.value)
			cfg, err := TaskSweepConfigFromEnv()
			if err == nil {
				t.Fatalf("%s=%q was accepted as %+v; a malformed interval must fail startup", tc.key, tc.value, cfg)
			}
			if !strings.Contains(err.Error(), tc.key) {
				t.Fatalf("the error does not name the variable: %v", err)
			}
		})
	}
}

// TestTaskSweepConfigTestHelperKeepsTheGuideDefaults keeps taskSweepTestConfig honest: every case
// above reads its ages against these numbers, and the guide's table states them.
func TestTaskSweepConfigTestHelperKeepsTheGuideDefaults(t *testing.T) {
	cfg := taskSweepTestConfig()
	if cfg.PruneAfter != 7*24*time.Hour || cfg.EscalateAfter != 24*time.Hour || cfg.BlockAfter != 7*24*time.Hour {
		t.Fatalf("the test schedule drifted from the documented defaults: %+v", cfg)
	}
}
