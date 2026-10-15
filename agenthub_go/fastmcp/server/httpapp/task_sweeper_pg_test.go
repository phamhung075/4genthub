package httpapp

// The lifecycle sweep and its advisory lock against a REAL database: rows in, the production
// composition, and the rows it leaves behind read back.
//
// IT SKIPS WITHOUT AGENTHUB_TEST_PG_URL, like its neighbours in this package, and the skip says so
// loudly. What ONLY a database can answer, and a fake cannot:
//
//   - the prune really takes the task's ledger rows with it (the foreign key the delete cascade
//     exists for) while the audit record SURVIVES - a claim about two tables and a constraint, which
//     is exactly the claim "evidence is kept" reduces to;
//   - the escalation really went through the application layer's status ledger: a progress entry is
//     in task_events, under the task's OWN user, which is also what the events read shows the owner;
//   - the advisory lock really is exclusive: two attempts from two sessions, one taken and one
//     refused WHILE the first is held.
//
// To run it:
//
//	bash tools/testpg/start.sh
//	AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55432/postgres go test -count=1 -run 'TestTaskLifecycleSweep|TestSweepAdvisoryLock' ./fastmcp/server/httpapp/

import (
	"context"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/infrastructure/database"
	infrarepos "agenthub/fastmcp/task_management/infrastructure/repositories"
)

// The project and branch the seeded tasks hang off. Each test gets a throwaway database, so the ids
// only have to be unique inside one test.
const (
	sweepTestProjectID = "55555555-5555-4555-8555-555555555555"
	sweepTestBranchID  = "66666666-6666-4666-8666-666666666666"
)

// sweepSeedBranch writes the project and the branch the seeded tasks need: tasks carries a foreign
// key to project_git_branchs, which carries one to projects.
//
// THE TIMESTAMPS ARE EXPLICIT UTC INSTANTS rather than the SQL `now()` its neighbours use, and that
// is not a style choice: this cluster runs with a session timezone (Europe/Paris on the box this was
// written on), so `now()` writes a LOCAL wall clock into a `timestamp without time zone` column that
// the application reads as UTC - and the delete path writes UTC into the same column, so a sweep that
// prunes one task and then escalates another sees a branch whose updated_at is two hours BEHIND its
// created_at and refuses to read it. Seeding what the application writes keeps the two halves of this
// test measuring the sweep instead of that skew.
func sweepSeedBranch(t *testing.T, sm *database.SessionManager, userID string) {
	t.Helper()
	now := time.Now().UTC().Truncate(time.Microsecond)
	ledgerExec(t, sm, `INSERT INTO projects (id,name,description,created_at,updated_at,user_id,status,metadata)
		VALUES ($1,'sweep project','',$2,$2,$3,'active','{}') ON CONFLICT (id) DO NOTHING`, sweepTestProjectID, now, userID)
	ledgerExec(t, sm, `INSERT INTO project_git_branchs (id, project_id, name, description, created_at, updated_at, priority, status, metadata, task_count, completed_task_count, user_id)
		VALUES ($1,$2,'sweep branch','',$3,$3,'medium','todo','{}',0,0,$4) ON CONFLICT (id) DO NOTHING`, sweepTestBranchID, sweepTestProjectID, now, userID)
}

// sweepSeedTask inserts one task whose ages are stated rather than derived from now(): created_at is
// 40 days back, updated_at `updatedAge` back, and completed_at `completedAge` back when the status is
// completed. The application writes UTC and refuses a row whose updated_at precedes its created_at,
// so both are set together - a hand-seeded row with now() created_at and an aged updated_at would be
// read by the update path as "not found" and the case would measure that instead of the sweep.
func sweepSeedTask(t *testing.T, sm *database.SessionManager, taskID, userID, status, priority, summary string,
	updatedAge time.Duration, completedAge *time.Duration) {
	t.Helper()
	var completedAt any
	if completedAge != nil {
		completedAt = time.Now().UTC().Add(-*completedAge).Truncate(time.Microsecond)
	}
	ledgerExec(t, sm, `
		INSERT INTO tasks (id, title, description, git_branch_id, status, priority,
			estimated_effort, created_at, updated_at, completed_at, completion_summary, testing_notes,
			progress_percentage, progress_state, user_id)
		VALUES ($1::uuid, $2, 'what the task was for', $3::uuid, $4, $5, '',
			$6, $7, $8, $9, '', 0, 'INITIAL', $10)`,
		taskID, "seeded "+status, sweepTestBranchID, status, priority,
		time.Now().UTC().Add(-40*24*time.Hour).Truncate(time.Microsecond),
		time.Now().UTC().Add(-updatedAge).Truncate(time.Microsecond),
		completedAt, summary, userID)
}

// sweepSeedEvidence writes the ledger entry the prune has to keep.
func sweepSeedEvidence(t *testing.T, sm *database.SessionManager, taskID, userID, headSHA string) {
	t.Helper()
	ledgerExec(t, sm, `
		INSERT INTO task_events (id, task_id, user_id, seq, user_seq, kind, actor_kind, actor_id, payload)
		VALUES (gen_random_uuid(), $1::uuid, $2, 1, 1, 'evidence_submitted', 'client', 'machine-1', $3::jsonb)`,
		taskID, userID, `{"base_sha":"`+strings.Repeat("a", 40)+`","head_sha":"`+headSHA+`","numstat":"3\t1\tfile.go"}`)
}

// sweepRowCount counts the rows a claim is about.
func sweepRowCount(t *testing.T, sm *database.SessionManager, table, where string, args ...any) int {
	t.Helper()
	n := 0
	if err := sm.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `SELECT count(*) FROM `+table+` WHERE `+where, args...).Scan(&n)
	}); err != nil {
		t.Fatalf("counting %s: %v", table, err)
	}
	return n
}

// sweepTaskRow reads one task's status and priority.
func sweepTaskRow(t *testing.T, sm *database.SessionManager, taskID string) (string, string) {
	t.Helper()
	var status, priority string
	if err := sm.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `SELECT "status", "priority" FROM tasks WHERE id = $1::uuid`, taskID).Scan(&status, &priority)
	}); err != nil {
		t.Fatalf("reading tasks.status/priority: %v", err)
	}
	return status, priority
}

// TestTaskLifecycleSweepOnPostgres drives one sweep over four seeded tasks and reads back what it
// left: the prune's cascade and its surviving record, the escalation's ledger entry, and the two
// rows it must not touch.
func TestTaskLifecycleSweepOnPostgres(t *testing.T) {
	sm := newMissedNotificationAppEnv(t)
	t.Setenv("AUTH_ENABLED", "true")
	wsWireRESTAuth(t)
	ctx := context.Background()
	// The app is built for the wiring the sweep shares with the routes (the ownership checker the
	// notifier asks, among others), exactly as main.go builds it before starting the sweep.
	if _, err := NewApp(ctx, sm); err != nil {
		t.Fatalf("NewApp: %v", err)
	}

	const userID = "user-lifecycle-sweep"
	const (
		pruneID    = "aaaa1111-1111-4111-8111-111111111111"
		escalateID = "bbbb2222-2222-4222-8222-222222222222"
		blockedID  = "cccc3333-3333-4333-8333-333333333333"
		youngID    = "dddd4444-4444-4444-8444-444444444444"
		headSHA    = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
	)
	sweepSeedBranch(t, sm, userID)

	// Done 8 days ago, with a summary and one evidence entry.
	aged := 8 * 24 * time.Hour
	sweepSeedTask(t, sm, pruneID, userID, "done", "medium", "shipped the sweeper", aged, &aged)
	sweepSeedEvidence(t, sm, pruneID, userID, headSHA)
	// Open, low, 2 days stale: one level to climb.
	sweepSeedTask(t, sm, escalateID, userID, "todo", "low", "", 2*24*time.Hour, nil)
	// Blocked 30 days ago: never pruned, never escalated.
	sweepSeedTask(t, sm, blockedID, userID, "blocked", "critical", "", 30*24*time.Hour, nil)
	// Open and young: nothing to do.
	sweepSeedTask(t, sm, youngID, userID, "todo", "low", "", time.Hour, nil)

	sweeper, err := NewTaskLifecycleSweeper(ctx, sm)
	if err != nil {
		t.Fatalf("NewTaskLifecycleSweeper: %v", err)
	}
	report, err := sweeper.SweepOnce(ctx)
	if err != nil {
		t.Fatalf("the sweep failed: %v", err)
	}
	t.Logf("OBSERVED one sweep: pruned %d, escalated %d, blocked %d, refused %d, failed %d",
		report.Pruned, report.Escalated, report.Blocked, report.Refused, report.Failed)
	if report.Pruned != 1 || report.Escalated != 1 || report.Failed != 0 {
		t.Fatalf("the sweep reported %+v, want one prune and one escalation and no failure", report)
	}

	// ---- the prune: the task and its ledger rows are gone, its record is not --------------------
	if rows := sweepRowCount(t, sm, "tasks", "id = $1::uuid", pruneID); rows != 0 {
		t.Errorf("tasks rows for the pruned task = %d, want 0", rows)
	}
	if rows := sweepRowCount(t, sm, "task_events", "task_id = $1::uuid", pruneID); rows != 0 {
		t.Errorf("task_events rows for the pruned task = %d, want 0: the delete cascade must take them", rows)
	}
	trail := infrarepos.NewTaskAuditRecordRepository(sm)
	records, err := trail.ListForTask(ctx, pruneID)
	if err != nil {
		t.Fatalf("reading the audit trail of the pruned task: %v", err)
	}
	if len(records) != 1 {
		t.Fatalf("the trail holds %d records for the pruned task, want exactly 1", len(records))
	}
	record := records[0]
	if record.Kind != "pruned" {
		t.Errorf("the record's kind is %q, want pruned", record.Kind)
	}
	if record.CompletionSummary != "shipped the sweeper" {
		t.Errorf("the record's summary is %q, want the task's own", record.CompletionSummary)
	}
	if record.Title != "seeded done" || record.UserID != userID {
		t.Errorf("the record does not name the task: %+v", record)
	}
	if len(record.Evidence) != 1 || record.Evidence[0]["head_sha"] != headSHA {
		t.Errorf("the record's evidence is %v, want the task's own evidence entry", record.Evidence)
	}
	if record.TaskCompletedAt == nil {
		t.Error("the record carries no task completed_at, which is the age the prune was measured from")
	}
	if record.TaskCreatedAt.IsZero() || record.TaskUpdatedAt.IsZero() {
		t.Errorf("the record carries no task timestamps: %+v", record)
	}

	// ---- the escalation: the priority moved ONE level, with the note in the task's own ledger -----
	status, priority := sweepTaskRow(t, sm, escalateID)
	if status != "todo" || priority != "medium" {
		t.Errorf("the escalated task is %s/%s, want todo/medium (one level from low)", status, priority)
	}
	notes := sweepProgressNotes(t, sm, escalateID, userID)
	if len(notes) != 1 {
		t.Fatalf("the escalation wrote %d progress entries, want 1: %v", len(notes), notes)
	}
	if !strings.Contains(notes[0], "escalated to medium") {
		t.Errorf("the progress note is %q, want it to name the step it reached", notes[0])
	}
	escalationRecords, err := trail.ListForTask(ctx, escalateID)
	if err != nil {
		t.Fatalf("reading the audit trail of the escalated task: %v", err)
	}
	if len(escalationRecords) != 1 || escalationRecords[0].Kind != "escalated" || escalationRecords[0].Priority != "medium" {
		t.Fatalf("the escalation's trail is %+v, want one escalated record at medium", escalationRecords)
	}

	// ---- the rows the sweep must not touch ------------------------------------------------------
	blockedStatus, blockedPriority := sweepTaskRow(t, sm, blockedID)
	if blockedStatus != "blocked" || blockedPriority != "critical" {
		t.Errorf("the blocked task is %s/%s, want blocked/critical: it must never be pruned or escalated", blockedStatus, blockedPriority)
	}
	if rows := sweepRowCount(t, sm, "task_audit_records", "task_id = $1::uuid", blockedID); rows != 0 {
		t.Errorf("the blocked task has %d audit records, want 0", rows)
	}
	youngStatus, youngPriority := sweepTaskRow(t, sm, youngID)
	if youngStatus != "todo" || youngPriority != "low" {
		t.Errorf("the young task is %s/%s, want todo/low", youngStatus, youngPriority)
	}
	if rows := sweepRowCount(t, sm, "task_audit_records", "task_id = $1::uuid", youngID); rows != 0 {
		t.Errorf("the young task has %d audit records, want 0", rows)
	}
}

// sweepProgressNotes reads the task's progress entries' text, oldest first, through the same
// user-scoped repository the events route reads with.
func sweepProgressNotes(t *testing.T, sm *database.SessionManager, taskID, userID string) []string {
	t.Helper()
	events, err := infrarepos.NewTaskEventRepository(sm, userID, "").Events(context.Background(), taskID)
	if err != nil {
		t.Fatalf("reading the task's ledger: %v", err)
	}
	out := []string{}
	for _, event := range events {
		if event.Kind != "progress" {
			continue
		}
		out = append(out, valueOf(event.Payload["content"]))
	}
	return out
}

// valueOf renders a payload field for an assertion without caring which JSON type it arrived as.
func valueOf(v any) string {
	if s, ok := v.(string); ok {
		return s
	}
	return ""
}

// TestSweepAdvisoryLockIsExclusiveOnPostgres is the "two server instances do not sweep twice" claim,
// measured: one session takes the lock and STAYS inside it, and a second attempt from another session
// is refused rather than queued behind it. After the first releases, the lock is free again - which is
// the other half: a lock that never came back would stop every later sweep.
func TestSweepAdvisoryLockIsExclusiveOnPostgres(t *testing.T) {
	sm := newMissedNotificationAppEnv(t)
	lock := sweepLock{sessions: sm}

	held := make(chan struct{})
	release := make(chan struct{})
	holderDone := make(chan struct{})
	go func() {
		defer close(holderDone)
		_, _ = lock.WithLock(context.Background(), func() error {
			close(held)
			<-release
			return nil
		})
	}()
	<-held

	secondRan := false
	ran, err := lock.WithLock(context.Background(), func() error {
		secondRan = true
		return nil
	})
	if err != nil {
		t.Fatalf("the second attempt failed rather than being refused: %v", err)
	}
	if ran || secondRan {
		t.Fatal("the second attempt RAN while the first held the lock: two instances would sweep twice")
	}

	close(release)
	<-holderDone

	// The lock is released with the session that held it, so the next interval runs.
	thirdRan := false
	ran, err = lock.WithLock(context.Background(), func() error {
		thirdRan = true
		return nil
	})
	if err != nil {
		t.Fatalf("the third attempt failed: %v", err)
	}
	if !ran || !thirdRan {
		t.Fatal("the lock was not released when its sweep returned: the next sweep could never run")
	}
}
