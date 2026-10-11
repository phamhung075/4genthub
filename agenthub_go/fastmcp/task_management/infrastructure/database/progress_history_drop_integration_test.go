package database_test

// The ruled carry step's acceptance, against a real PostgreSQL: the step that MOVES the column's
// progress notes into the ledger and then DROPs the column.
//
// 0002 is the additive bridge - it copies the notes and leaves the columns, which is what kept the
// union read correct while the switch was half landed. This step is the one O1c rules (decision D1
// 3a), and its difference is that it destroys the source, so its acceptance has two halves: the notes
// really are in the ledger afterwards, and a note the step CANNOT read fails the step rather than
// being destroyed with the column.
//
// The boot applies the embedded set, so on a database built by this tree the columns are already gone
// by the time a test runs; each case recreates the pre-drop columns first, which is the schema the
// step exists to meet. Everything the step touches is seeded through helpers beside this file
// (`seedBranch`, `seedTaskWithColumnNote`), so the fixture is the same one the 0002 carry's cases use.
//
// It needs AGENTHUB_TEST_PG_URL (see tools/testpg/start.sh) and skips loudly without it.

import (
	"context"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

// ruledCarryStep returns the embedded carry-and-drop step's name and SQL. The artifact under test is
// the file the boot runs; a case needs it to run over rows seeded AFTER the boot, so it is applied
// under a name the database has not recorded - the runner records names, and re-recording one is what
// makes a migration one-shot.
func ruledCarryStep(t *testing.T) (string, string) {
	t.Helper()
	set, err := database.LoadMigrations()
	if err != nil {
		t.Fatalf("the embedded set does not load: %v", err)
	}
	for _, m := range set {
		if strings.Contains(m.Name, "carry_and_drop") {
			return m.Name, m.SQL
		}
	}
	t.Fatalf("the embedded set does not carry the ruled carry-and-drop step: %v", set)
	return "", ""
}

// applyRuledCarry applies the step under the given name and returns the runner's error, because one
// case is about the step REFUSING.
func applyRuledCarry(t *testing.T, sessions *database.SessionManager, name string) error {
	t.Helper()
	_, sql := ruledCarryStep(t)
	runner := &database.Runner{Sessions: sessions, Set: []database.Migration{{Name: name, SQL: sql}}}
	_, err := runner.Apply(context.Background())
	return err
}

// restorePreDropColumns puts back the four columns the step drops, with the declarations the old DDL
// carried (init_schema_postgresql.sql:259-260, :329-330), so a case starts where the step meets a
// database that has not been carried yet.
func restorePreDropColumns(t *testing.T, sessions *database.SessionManager) {
	t.Helper()
	if err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		if _, err := s.ExecContext(ctx, `
			ALTER TABLE tasks ADD COLUMN progress_history JSONB NOT NULL DEFAULT '{}'::jsonb;
			ALTER TABLE tasks ADD COLUMN progress_count INTEGER NOT NULL DEFAULT 0;
			ALTER TABLE subtasks ADD COLUMN progress_history JSONB NOT NULL DEFAULT '{}'::jsonb;
			ALTER TABLE subtasks ADD COLUMN progress_count INTEGER NOT NULL DEFAULT 0;`); err != nil {
			return err
		}
		return nil
	}); err != nil {
		t.Fatalf("restoring the pre-drop columns failed: %v", err)
	}
}

// columnExists reports whether the table still carries the column, which is the one thing the step's
// "the column goes" half needs to be read from the catalogue rather than inferred.
func columnExists(t *testing.T, sessions *database.SessionManager, table, column string) bool {
	t.Helper()
	exists := false
	if err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `SELECT EXISTS (
				SELECT 1 FROM information_schema.columns
				WHERE table_schema = current_schema() AND table_name = $1 AND column_name = $2)`,
			table, column).Scan(&exists)
	}); err != nil {
		t.Fatalf("reading the catalogue for %s.%s failed: %v", table, column, err)
	}
	return exists
}

// carriedEvents returns the ledger's progress events for a task as "content|number|timestamp|carried_from"
// tuples, so a case can assert both that the note arrived and that it arrived as a CARRY.
func carriedEvents(t *testing.T, sessions *database.SessionManager, user, taskID string) []string {
	t.Helper()
	var out []string
	if err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		rows, err := s.QueryContext(ctx, `SELECT payload ->> 'content', payload ->> 'progress_number',
				payload ->> 'timestamp', COALESCE(payload ->> 'carried_from', '')
			FROM task_events
			WHERE user_id = $1 AND task_id = $2::uuid AND kind = 'progress'
			ORDER BY seq`, user, taskID)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			var content, number, ts, from string
			if err := rows.Scan(&content, &number, &ts, &from); err != nil {
				return err
			}
			out = append(out, content+"|"+number+"|"+ts+"|"+from)
		}
		return rows.Err()
	}); err != nil {
		t.Fatalf("reading the ledger's progress events failed: %v", err)
	}
	return out
}

// idempotentCaseName names the step under a name the database has not recorded, so the runner applies
// it again. The name must be stable per case because a re-run of a case that half-applied would
// otherwise see a recorded name and skip the very step under test.
func idempotentCaseName(caseName string) string {
	return "test_rerun_" + caseName + "_carry_and_drop"
}

func TestTheRuledCarryStepCarriesTheNotesAndDropsTheColumns(t *testing.T) {
	sessions, _ := newMigrationRunnerEnv(t)
	restorePreDropColumns(t, sessions)

	const user = "user-drop-carry-1"
	const noteText = "1. a note written before the ledger existed"
	const subtaskText = "3. a subtask note written before the ledger existed"
	branchID := seedBranch(t, sessions, user)
	taskID := seedTaskWithColumnNote(t, sessions, user, branchID, "drop carry probe", "progress_1", noteText, 1)

	// The subtask's note lives in the subtask's own column and belongs to the TASK's ledger, so the
	// step has to resolve its task from the subtask row rather than assume the key it reads.
	if err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx, `INSERT INTO subtasks
				(id, task_id, title, description, status, priority, assignees, progress_percentage,
				 progress_history, progress_count, progress_state, progress_notes, blockers,
				 completion_summary, impact_on_parent, insights_found, user_id, created_at, updated_at)
			VALUES (gen_random_uuid(), $1::uuid, 'a subtask', '', 'todo', 'medium', '[]'::json, 0,
				json_build_object('progress_2', json_build_object('content', $2::text,
					'timestamp', '2026-01-01T00:00:00Z', 'progress_number', 2)),
				1, 'INITIAL', '', '[]'::json, '', '', '[]'::json, $3, now(), now())`, taskID, subtaskText, user)
		return err
	}); err != nil {
		t.Fatalf("seeding the subtask's column note failed: %v", err)
	}

	if err := applyRuledCarry(t, sessions, idempotentCaseName("carries")); err != nil {
		t.Fatalf("the carry-and-drop step failed on a well-formed column: %v", err)
	}

	// The notes are in the ledger, byte for byte, with the timestamp the column stored and the record
	// that they are copies rather than writes.
	events := carriedEvents(t, sessions, user, taskID)
	if len(events) != 2 {
		t.Fatalf("the ledger holds %d progress events, want 2 (the task's note and the subtask's): %v",
			len(events), events)
	}
	want := []string{
		noteText + "|1|2026-01-01T00:00:00Z|progress_1",
		subtaskText + "|2|2026-01-01T00:00:00Z|progress_2",
	}
	for _, w := range want {
		if !containsString(events, w) {
			t.Errorf("the ledger holds no %q; it holds %v", w, events)
		}
	}

	// The dialog's own call - the note text built from the ledger alone - shows them.
	text := ledgerProgressText(t, sessions, user, taskID)
	if !strings.Contains(text, noteText) || !strings.Contains(text, subtaskText) {
		t.Errorf("the ledger's own render is missing a carried note: %q", text)
	}

	// And only then are the columns gone, on both tables.
	for _, c := range []struct{ table, column string }{
		{"tasks", "progress_history"}, {"tasks", "progress_count"},
		{"subtasks", "progress_history"}, {"subtasks", "progress_count"},
	} {
		if columnExists(t, sessions, c.table, c.column) {
			t.Errorf("%s.%s still exists after the step; the step must drop it once the carry is in the ledger",
				c.table, c.column)
		}
	}
}

func TestTheRuledCarryStepFailsOnAMalformedEntryAndLeavesTheColumnIntact(t *testing.T) {
	sessions, _ := newMigrationRunnerEnv(t)
	restorePreDropColumns(t, sessions)

	const user = "user-drop-carry-2"
	const noteText = "5. a note whose stored entry has no timestamp"
	branchID := seedBranch(t, sessions, user)

	// An entry without a timestamp: the step cannot express it in the ledger, and because the step
	// destroys the source, the ruling is that it FAILS rather than drops a note it could not read
	// (NEXT_GEN.md's O1c check: "a malformed entry -> step fails, column intact"). 0002 could skip
	// these because it destroyed nothing; this step cannot.
	var taskID string
	if err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `INSERT INTO tasks
				(id, title, description, git_branch_id, status, priority, progress_history, progress_count,
				 estimated_effort, created_at, updated_at, completion_summary, testing_notes,
				 progress_percentage, progress_state, user_id)
			VALUES (gen_random_uuid(), 'malformed probe', '', $1::uuid, 'todo', 'medium',
				json_build_object('progress_5', json_build_object('content', $2::text, 'progress_number', 5)),
				1, '', now(), now(), '', '', 0, 'INITIAL', $3)
			RETURNING id`, branchID, noteText, user).Scan(&taskID)
	}); err != nil {
		t.Fatalf("seeding the malformed entry failed: %v", err)
	}

	name := idempotentCaseName("malformed")
	if err := applyRuledCarry(t, sessions, name); err == nil {
		t.Fatalf("the step accepted an entry with no timestamp; it must fail rather than drop a note it cannot carry")
	} else if !strings.Contains(err.Error(), "progress entr") {
		t.Errorf("the step failed, but not for the reason under test: %v", err)
	}

	// The column is intact and the note is still readable from it: the 0002-style reader's union is
	// gone, but a failed step must not have destroyed the note.
	var stored string
	if err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `SELECT progress_history -> 'progress_5' ->> 'content'
			FROM tasks WHERE id = $1::uuid`, taskID).Scan(&stored)
	}); err != nil {
		t.Fatalf("reading the column after the failed step failed: %v", err)
	}
	if stored != noteText {
		t.Errorf("the column holds %q after the failed step, want the note intact: %q", stored, noteText)
	}
	for _, c := range []struct{ table, column string }{
		{"tasks", "progress_history"}, {"tasks", "progress_count"},
	} {
		if !columnExists(t, sessions, c.table, c.column) {
			t.Errorf("%s.%s was dropped although the step failed; a failure must roll the whole step back",
				c.table, c.column)
		}
	}

	// Nothing was carried and nothing was recorded: the runner's ledger row is the record of a step
	// that applied, and this one did not.
	if events := carriedEvents(t, sessions, user, taskID); len(events) != 0 {
		t.Errorf("the failed step carried %v; a failure must leave no event behind", events)
	}
	if recorded := recordedMigrations(t, sessions); containsString(recorded, name) {
		t.Errorf("the failed step is recorded as applied: %v", recorded)
	}
}

func TestTheRuledCarryStepDoesNotDuplicateANoteTheLedgerAlreadyHolds(t *testing.T) {
	sessions, _ := newMigrationRunnerEnv(t)
	restorePreDropColumns(t, sessions)

	const user = "user-drop-carry-3"
	const noteText = "2. a note the ledger already holds"
	branchID := seedBranch(t, sessions, user)
	taskID := seedTaskWithColumnNote(t, sessions, user, branchID, "duplicate probe", "progress_2", noteText, 2)

	// The ledger already holds this note under the identity ProgressTextWith merges by - content and
	// number, NOT the column key - which is what a live dual write leaves behind.
	if err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx, `INSERT INTO task_events
				(id, user_id, task_id, subtask_id, seq, user_seq, kind, actor_kind, actor_id, payload)
			VALUES (gen_random_uuid(), $1, $2::uuid, NULL, 1, 1, 'progress', 'seat', 'a-seat',
				json_build_object('content', $3::text, 'progress_number', 2,
					'timestamp', '2026-01-01T00:00:00Z'))`, user, taskID, noteText)
		return err
	}); err != nil {
		t.Fatalf("seeding the ledger's own copy failed: %v", err)
	}

	if err := applyRuledCarry(t, sessions, idempotentCaseName("duplicate")); err != nil {
		t.Fatalf("the carry-and-drop step failed with the ledger already holding the note: %v", err)
	}

	if events := carriedEvents(t, sessions, user, taskID); len(events) != 1 {
		t.Errorf("the ledger holds %d events, want 1: a note the ledger already holds must not be carried twice: %v",
			len(events), events)
	}
	if columnExists(t, sessions, "tasks", "progress_history") {
		t.Errorf("tasks.progress_history still exists after the step; the drop must happen whether or not this step did the carrying")
	}
}

// TestTheRuledCarryStepRefusesWithoutTheBaselineMark pins the gate the architect's ruling puts on this
// step (ARCH-RULING-0001-baseline-canonicity). The step destroys its source and NOTHING tied it to the
// owner's baseline mark: validateSet checks a set's names, order and duplicates, never the provenance
// of a step, so a database where 0001 was SKIPPED - which is what main's runner does whenever the
// catalogue is not empty, i.e. every boot - reached the DROP with no 0001_baseline row and no owner
// action. The instrument is applyRuledCarry's ONE-STEP set on purpose: it reaches the runner with the
// rest of the set out of the way, which is exactly the state the gate is written for.
//
// The ledger under test holds no 0001_baseline row. The fixture boots as an OPERATOR does - it records
// the owner's mark with Runner.MarkBaseline - so the row is REMOVED here to reach the unmarked state
// rather than argued to be absent. That state is not hypothetical: it is the one the shipping runner
// leaves on a database that already has the schema, and
// TestTheBootRefusesTheCarryStepOnAPopulatedDatabaseWithoutTheMark measures exactly that, through
// CreateTables, with both columns surviving.
func TestTheRuledCarryStepRefusesWithoutTheBaselineMark(t *testing.T) {
	sessions, _ := newMigrationRunnerEnv(t)
	// The boot has already applied the step and dropped the columns; the case needs the schema the
	// step exists to meet, which is a database that still has them.
	restorePreDropColumns(t, sessions)
	if err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx, `DELETE FROM applied_migrations WHERE migration_name = '0001_baseline'`)
		return err
	}); err != nil {
		t.Fatalf("clearing the baseline's row failed: %v", err)
	}

	name := idempotentCaseName("unmarked")
	err := applyRuledCarry(t, sessions, name)
	if err == nil {
		t.Fatalf("the step ran with no 0001_baseline row: nothing ties the destructive step to the owner's mark")
	}
	if !strings.Contains(err.Error(), "0001 baseline mark") {
		t.Errorf("the step refused, but not for the reason under test: %v", err)
	}

	// The refusal rolls the step's own transaction back, so the columns STAY - on both tables, because
	// the gate is the step's first statement and neither table has been touched when it raises.
	for _, c := range []struct{ table, column string }{
		{"tasks", "progress_history"}, {"tasks", "progress_count"},
		{"subtasks", "progress_history"}, {"subtasks", "progress_count"},
	} {
		if !columnExists(t, sessions, c.table, c.column) {
			t.Errorf("%s.%s is gone although the step refused; a refusal must leave the schema untouched",
				c.table, c.column)
		}
	}
	if recorded := recordedMigrations(t, sessions); containsString(recorded, name) {
		t.Errorf("the refused step is recorded as applied: %v", recorded)
	}
}

// TestTheRuledCarryStepProceedsUnderTheBaselineMark is the gate's other side, and it is the control
// that stops the refusal above from passing vacuously: the same step, the same pre-drop schema, the
// owner's mark in the ledger - and the step carries and drops. MarkBaseline is the owner's action; the
// runner only provides the mechanism, and it refuses to mark a name its set does not contain, which is
// why the set is the embedded one.
func TestTheRuledCarryStepProceedsUnderTheBaselineMark(t *testing.T) {
	sessions, _ := newMigrationRunnerEnv(t)
	restorePreDropColumns(t, sessions)

	set, err := database.LoadMigrations()
	if err != nil {
		t.Fatalf("the embedded set does not load: %v", err)
	}
	runner := &database.Runner{Sessions: sessions, Set: set}
	if _, err := runner.MarkBaseline(context.Background(), "0001_baseline"); err != nil {
		t.Fatalf("the owner's mark could not be recorded: %v", err)
	}

	name := idempotentCaseName("marked")
	if err := applyRuledCarry(t, sessions, name); err != nil {
		t.Fatalf("the step refused although the owner's 0001_baseline mark is in the ledger: %v", err)
	}
	for _, c := range []struct{ table, column string }{
		{"tasks", "progress_history"}, {"tasks", "progress_count"},
		{"subtasks", "progress_history"}, {"subtasks", "progress_count"},
	} {
		if columnExists(t, sessions, c.table, c.column) {
			t.Errorf("%s.%s still exists under the mark; the step must carry and then drop",
				c.table, c.column)
		}
	}
	if recorded := recordedMigrations(t, sessions); !containsString(recorded, name) {
		t.Errorf("the step ran under the mark but is not recorded: %v", recorded)
	}
}

// TestTheBootRefusesTheCarryStepOnAPopulatedDatabaseWithoutTheMark IS THE PAIR'S PROOF, and it is
// deliberately NOT a test that the gate exists: on the shipping runner (main's, whose 0001 baseline is
// inert) a boot meets a database that already has the schema - createAll has just built it - skips
// 0001 WITHOUT recording it, and so reaches the step that destroys two columns with no mark. The step
// REFUSES, its own transaction rolls back, BOTH COLUMNS SURVIVE and no ledger row is written. A gate
// that PASSES here is the failure mode this case exists for: the boot would carry and drop the columns
// unattended. The other half - the same boot under the owner's mark, which carries and then drops - is
// TestTheRuledCarryStepProceedsUnderTheBaselineMark.
func TestTheBootRefusesTheCarryStepOnAPopulatedDatabaseWithoutTheMark(t *testing.T) {
	dsn := newTestDatabase(t)
	db, err := database.PgxOpener(dsn, database.EngineOptions{PoolSize: 2, MaxOverflow: 2, PoolRecycle: 60})
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	cfg := &database.DatabaseConfig{Engine: &database.Engine{DB: db, URL: dsn}}
	ctx := context.Background()

	err = cfg.CreateTables(ctx)
	if err == nil {
		t.Fatal("the boot applied the destructive carry step on a populated database with no 0001_baseline row")
	}
	if !strings.Contains(err.Error(), "0001_baseline") {
		t.Fatalf("the boot refused, but not for the missing baseline mark: %v", err)
	}
	sessions := database.NewSessionManager(cfg)
	for _, c := range []struct{ table, column string }{
		{"tasks", "progress_history"},
		{"tasks", "progress_count"},
		{"subtasks", "progress_history"},
		{"subtasks", "progress_count"},
	} {
		if !columnExists(t, sessions, c.table, c.column) {
			t.Errorf("%s.%s is gone although the boot refused: the refusal must leave the schema untouched",
				c.table, c.column)
		}
	}
	if recorded := recordedMigrations(t, sessions); containsString(recorded, "0003_progress_history_carry_and_drop") {
		t.Errorf("the refused step is recorded as applied: %v", recorded)
	}
}

func containsString(haystack []string, needle string) bool {
	for _, h := range haystack {
		if h == needle {
			return true
		}
	}
	return false
}
