package database_test

// The carry's acceptance, against a real PostgreSQL: a progress note written the way EVERY note was
// written before the dual write - in the column alone - must be visible afterwards from the ledger
// alone, because the ledger timeline is the task dialog's only progress surface and the column is not
// part of it.
//
// The case is the one the frontend gate stopped on: the dialog renders task.ProgressTextWith(events)
// over the LEDGER's events (application/dtos/task/task_response.go), so a pre-switch note is missing
// from that call until the carry has put it in the ledger. This test makes exactly that call, before
// and after.
//
// It needs AGENTHUB_TEST_PG_URL (see tools/testpg/start.sh) and skips loudly without it.

import (
	"context"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
	"agenthub/fastmcp/task_management/infrastructure/repositories"
)

// carryStep returns the embedded backfill step's SQL. The step the boot ran is the artifact under
// test; this case needs it to run again over a row seeded AFTER the boot, so it is applied under a
// name the database has not recorded (the runner records names, and re-running a recorded name is
// what makes a migration one-shot).
func carryStep(t *testing.T) string {
	t.Helper()
	set, err := database.LoadMigrations()
	if err != nil {
		t.Fatalf("the embedded set does not load: %v", err)
	}
	for _, m := range set {
		if strings.Contains(m.Name, "progress_notes_backfill") {
			return m.SQL
		}
	}
	t.Fatalf("the embedded set does not carry the backfill step: %v", set)
	return ""
}

func applyCarry(t *testing.T, sessions *database.SessionManager, name string) {
	t.Helper()
	runner := &database.Runner{Sessions: sessions, Set: []database.Migration{
		{Name: name, SQL: carryStep(t)},
	}}
	if _, err := runner.Apply(context.Background()); err != nil {
		t.Fatalf("applying %s failed: %v", name, err)
	}
}

// ledgerProgressText is the call the task dialog makes: the note text built from the LEDGER's events
// alone, with no column content contributed at all.
func ledgerProgressText(t *testing.T, sessions *database.SessionManager, user, taskID string) string {
	t.Helper()
	events, err := repositories.NewTaskEventRepository(sessions, user, "").Events(context.Background(), taskID)
	if err != nil {
		t.Fatalf("reading the ledger failed: %v", err)
	}
	return (&entities.Task{}).ProgressTextWith(events)
}

// seedBranch writes the chain a task hangs off - projects -> project_git_branchs -> (returned id) -
// and returns the branch id. The foreign keys carry no CASCADE, and a task without a branch is
// refused, so a case that needs a task starts here.
func seedBranch(t *testing.T, sessions *database.SessionManager, user string) string {
	t.Helper()
	var branchID string
	if err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		var projectID string
		if err := s.QueryRowContext(ctx, `INSERT INTO projects
				(id, name, description, created_at, updated_at, user_id, status, metadata)
			VALUES (gen_random_uuid(), 'carry probe project', '', now(), now(), $1, 'active', '{}'::json)
			RETURNING id`, user).Scan(&projectID); err != nil {
			return err
		}
		return s.QueryRowContext(ctx, `INSERT INTO project_git_branchs
				(id, project_id, name, description, created_at, updated_at, priority, status,
				 metadata, task_count, completed_task_count, user_id)
			VALUES (gen_random_uuid(), $1, 'carry probe branch', '', now(), now(), 'medium', 'active',
				'{}'::json, 0, 0, $2)
			RETURNING id`, projectID, user).Scan(&branchID)
	}); err != nil {
		t.Fatalf("seeding the project and branch failed: %v", err)
	}
	return branchID
}

// seedTaskWithColumnNote writes a task whose progress_history holds note under key, and nothing has
// written a ledger event for it - the pre-switch state.
func seedTaskWithColumnNote(t *testing.T, sessions *database.SessionManager, user, branchID, title, key, note string, number int) string {
	t.Helper()
	var taskID string
	if err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `INSERT INTO tasks
				(id, title, description, git_branch_id, status, priority, progress_history, progress_count,
				 estimated_effort, created_at, updated_at, completion_summary, testing_notes,
				 progress_percentage, progress_state, user_id)
			VALUES (gen_random_uuid(), $1, '', $2, 'todo', 'medium',
				json_build_object($3::text, json_build_object('content', $4::text, 'timestamp', '2026-01-01T00:00:00Z', 'progress_number', $5::int)),
				1, '', now(), now(), '', '', 0, 'INITIAL', $6)
			RETURNING id`, title, branchID, key, note, number, user).Scan(&taskID)
	}); err != nil {
		t.Fatalf("seeding the column-only note failed: %v", err)
	}
	return taskID
}

func TestTheCarryMakesAPreSwitchNoteVisibleFromTheLedgerAlone(t *testing.T) {
	sessions, _ := newMigrationRunnerEnv(t)
	ctx := context.Background()

	const user = "user-carry-1"
	const noteText = "1. a note from before the dual write"
	const subtaskText = "3. a subtask note from before the dual write"
	branchID := seedBranch(t, sessions, user)
	taskID := seedTaskWithColumnNote(t, sessions, user, branchID, "carry probe", "progress_1", noteText, 1)

	// A subtask note too: it lives in the subtask's own column and belongs to the TASK's ledger, so
	// the carry has to resolve its task from the subtask row rather than assume the key it reads.
	var subtaskID string
	if err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `INSERT INTO subtasks
				(id, task_id, title, description, status, priority, assignees, progress_percentage,
				 progress_history, progress_count, progress_state, progress_notes, blockers,
				 completion_summary, impact_on_parent, insights_found, user_id, created_at, updated_at)
			VALUES (gen_random_uuid(), $1, 'carry probe subtask', '', 'todo', 'medium', '[]'::json, 0,
				json_build_object('progress_3', json_build_object('content', $2::text, 'timestamp', '2026-01-01T00:00:00Z', 'progress_number', 3)),
				1, 'INITIAL', '', '', '', '', '[]'::json, $3, now(), now())
			RETURNING id`, taskID, subtaskText, user).Scan(&subtaskID)
	}); err != nil {
		t.Fatalf("seeding the subtask's column-only note failed: %v", err)
	}

	// BEFORE: the dialog's call over the ledger alone does not show either note. That absence IS the
	// defect the frontend gate reported, and it is why the union read cannot be the answer by itself.
	if got := ledgerProgressText(t, sessions, user, taskID); strings.Contains(got, noteText) {
		t.Fatalf("the ledger already shows a column-only note, so this case cannot show the carry "+
			"working: %q", got)
	}

	// THE CARRY.
	applyCarry(t, sessions, "9001_carry_under_test")

	// AFTER: the same call, over the ledger alone, shows both notes.
	after := ledgerProgressText(t, sessions, user, taskID)
	if !strings.Contains(after, noteText) {
		t.Errorf("the ledger alone still does not show the task's pre-switch note: %q", after)
	}
	if !strings.Contains(after, subtaskText) {
		t.Errorf("the ledger alone still does not show the subtask's pre-switch note: %q", after)
	}
	if n := strings.Count(after, noteText); n != 1 {
		t.Errorf("the task's note appears %d times in the merged text, want exactly 1: a carried copy "+
			"is a copy of a note that is already there", n)
	}

	// The carried rows carry the ledger contract: the kind and actor the append path uses, the
	// identity ProgressTextWith merges by, and the record that this is a copy rather than a write.
	var kind, actorKind, carriedFrom string
	var subtaskStored string
	var userSeq int64
	if err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `SELECT kind, actor_kind, payload->>'carried_from',
				coalesce(subtask_id::text, ''), user_seq
			FROM task_events
			WHERE task_id = $1 AND kind = 'progress' AND payload->>'carried_from' = 'progress_1'`,
			taskID).Scan(&kind, &actorKind, &carriedFrom, &subtaskStored, &userSeq)
	}); err != nil {
		t.Fatalf("the carried ledger row is not readable: %v", err)
	}
	if kind != "progress" || actorKind != "human" {
		t.Errorf("the carried row is %s/%s, want progress/human: the actor is the user the row belongs to", kind, actorKind)
	}
	if carriedFrom != "progress_1" {
		t.Errorf("the carried row records carried_from=%q, want progress_1: the copy's origin is how a "+
			"reader tells a carried note from a written one", carriedFrom)
	}
	if subtaskStored != "" {
		t.Errorf("the task's own note was carried as a subtask row (%s), want subtask_id NULL", subtaskStored)
	}
	if userSeq < 1 {
		t.Errorf("the carried row's user_seq is %d, want at least 1: the ledger numbers each user's rows", userSeq)
	}

	// The subtask's note is carried onto the TASK's ledger and keeps the subtask it came from.
	var subtaskCarried string
	if err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `SELECT coalesce(subtask_id::text, '') FROM task_events
			WHERE task_id = $1 AND kind = 'progress' AND payload->>'carried_from' = 'progress_3'`,
			taskID).Scan(&subtaskCarried)
	}); err != nil {
		t.Fatalf("the subtask's carried row is not readable: %v", err)
	}
	if subtaskCarried != subtaskID {
		t.Errorf("the subtask's carried row names subtask %q, want %q: it belongs to the task's ledger "+
			"but not to the task's own progress", subtaskCarried, subtaskID)
	}

	// IDEMPOTENT: a second run of the same step adds nothing, so a database that somehow holds part
	// of the carry converges rather than duplicating notes.
	applyCarry(t, sessions, "9002_carry_under_test_again")
	again := ledgerProgressText(t, sessions, user, taskID)
	if n := strings.Count(again, noteText); n != 1 {
		t.Errorf("a second run of the carry changed the merged text: the note appears %d times, want 1", n)
	}
	var rows int
	if err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `SELECT count(*) FROM task_events
			WHERE task_id = $1 AND kind = 'progress'`, taskID).Scan(&rows)
	}); err != nil {
		t.Fatal(err)
	}
	if rows != 2 {
		t.Errorf("the ledger holds %d progress rows for the task, want 2 (the task's note and the "+
			"subtask's): a re-run duplicated a carried note", rows)
	}
}

// A note the ledger ALREADY holds under the same identity is not carried a second time: the guard is
// the identity ProgressTextWith merges by (content and number), not the column key, because a live
// dual write records the note in the ledger while the column key it used is not what the ledger sees.
func TestTheCarrySkipsANoteTheLedgerAlreadyHolds(t *testing.T) {
	sessions, _ := newMigrationRunnerEnv(t)
	ctx := context.Background()

	const user = "user-carry-2"
	const noteText = "2. a note already in the ledger"
	branchID := seedBranch(t, sessions, user)
	taskID := seedTaskWithColumnNote(t, sessions, user, branchID, "carry probe 2", "progress_2", noteText, 2)

	// The ledger already holds this note under the same identity, as the dual write leaves it.
	repo := repositories.NewTaskEventRepository(sessions, user, "")
	if _, err := repo.Append(ctx, entities.AppendTaskEvent{
		TaskID: taskID, Kind: entities.TaskEventKindProgress,
		ActorKind: entities.TaskEventActorHuman, ActorID: user,
		Payload: map[string]any{"content": noteText, "progress_number": float64(2)},
	}); err != nil {
		t.Fatalf("seeding the ledger's copy of the note failed: %v", err)
	}

	applyCarry(t, sessions, "9001_carry_under_test")

	var rows int
	if err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `SELECT count(*) FROM task_events
			WHERE task_id = $1 AND kind = 'progress'`, taskID).Scan(&rows)
	}); err != nil {
		t.Fatal(err)
	}
	if rows != 1 {
		t.Errorf("the ledger holds %d progress rows, want 1: the carry copied a note the ledger already "+
			"had, which is the double-render ProgressTextWith's identity exists to prevent", rows)
	}
}
