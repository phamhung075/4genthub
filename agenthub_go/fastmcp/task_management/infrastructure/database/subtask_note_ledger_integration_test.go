package database_test

// The MAJOR from GATE c663cca2, end to end against a real PostgreSQL: a manage_subtask update that
// carries a progress note records exactly ONE ledger entry, in the PARENT task's ledger, naming the
// subtask that wrote it - and the task dialog's own render, built from the ledger alone, shows that
// note. The 0003 carry keeps the same shape for the notes it moves out of the dropped columns; this is
// the same shape for a note written after the switch.
//
// The rows are seeded with SQL rather than through the repositories because this environment's schema
// comes from the registry's own DDL, where tasks.created_at carries NO default: the boot path the
// repositories' own test environment uses is a different one. The case's subject is the write path, and
// it reads the rows back through the REAL repositories.
//
// The subtask_id is asserted from the ROW rather than through a reader deliberately: ListAfter (and so
// Events) does not select that column, so a reader cannot yet say which subtask wrote a note. What this
// case has to prove is that the write LANDS, and the row is where it lands.

import (
	"context"
	"strings"
	"testing"

	subtaskdto "agenthub/fastmcp/task_management/application/dtos/subtask"
	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/application/use_cases"
	"agenthub/fastmcp/task_management/infrastructure/database"
	"agenthub/fastmcp/task_management/infrastructure/repositories"
)

// seedTaskRecord inserts the parent task this case updates, with the columns the post-O1c schema
// carries (progress_history and progress_count are gone) and an explicit created_at, which the
// registry's DDL gives no default.
func seedTaskRecord(t *testing.T, sessions *database.SessionManager, user, branchID, title string) string {
	t.Helper()
	var taskID string
	if err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `INSERT INTO tasks
				(id, title, description, git_branch_id, status, priority, estimated_effort, created_at, updated_at,
				 completion_summary, testing_notes, progress_percentage, progress_state, user_id)
			VALUES (gen_random_uuid(), $1, 'd', $2, 'todo', 'medium', '2 hours', now(), now(), '', '', 0, 'INITIAL', $3)
			RETURNING id`, title, branchID, user).Scan(&taskID)
	}); err != nil {
		t.Fatalf("seeding the task failed: %v", err)
	}
	return taskID
}

// seedSubtaskRecord inserts one subtask of that task.
func seedSubtaskRecord(t *testing.T, sessions *database.SessionManager, user, taskID, title string) string {
	t.Helper()
	var subtaskID string
	if err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `INSERT INTO subtasks
				(id, task_id, title, description, status, priority, assignees, progress_percentage,
				 progress_state, progress_notes, blockers, completion_summary, impact_on_parent, insights_found,
				 user_id, created_at, updated_at)
			VALUES (gen_random_uuid(), $1::uuid, $2, '', 'todo', 'medium', '[]'::json, 0,
				'INITIAL', '', '', '', '', '[]'::json, $3, now(), now())
			RETURNING id`, taskID, title, user).Scan(&subtaskID)
	}); err != nil {
		t.Fatalf("seeding the subtask failed: %v", err)
	}
	return subtaskID
}

func TestASubtaskUpdateRecordsItsNoteInTheTaskLedger(t *testing.T) {
	sessions, _ := newMigrationRunnerEnv(t)
	ctx := context.Background()
	const user = "user-subtask-note-1"
	const noteText = "wired the parser and its case"
	branchID := seedBranch(t, sessions, user)
	taskID := seedTaskRecord(t, sessions, user, branchID, "subtask note probe")
	subtaskID := seedSubtaskRecord(t, sessions, user, taskID, "child")

	userID := user
	taskRepo, err := repositories.NewORMTaskRepository(sessions, &branchID, nil, nil, &userID, false)
	if err != nil {
		t.Fatalf("task repository: %v", err)
	}
	subRepo, err := repositories.NewORMSubtaskRepository(sessions, &userID)
	if err != nil {
		t.Fatalf("subtask repository: %v", err)
	}

	// The real ledger: the same recorder over the same repository the composition root wires, so this
	// case runs the production write path rather than a seam shaped like it.
	taskEvents := repositories.NewTaskEventRepository(sessions, user, branchID)
	ledger := use_cases.StatusLedger{
		Tx:     sessions,
		Ledger: services.NewTaskEventRecorder(taskEvents, user),
		Events: taskEvents,
	}

	note := noteText
	if _, err := use_cases.NewUpdateSubtaskUseCase(taskRepo, subRepo).
		WithLedger(ledger).
		Execute(ctx, &subtaskdto.UpdateSubtaskRequest{
			TaskID: taskID, ID: subtaskID, ProgressNotes: &note,
		}); err != nil {
		t.Fatalf("update_subtask: %v", err)
	}

	// What the task dialog renders: built from the ledger's events alone.
	rendered := ledgerProgressText(t, sessions, user, taskID)
	if want := "=== Progress 1 ===\n" + noteText; !strings.Contains(rendered, want) {
		t.Fatalf("the task's rendered notes do not carry the subtask's note %q; render = %q", want, rendered)
	}

	// The row itself: one entry, naming the subtask, numbered in the task's sequence.
	type row struct {
		subtaskID string
		content   string
		number    string
	}
	var rows []row
	if err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rs, err := s.QueryContext(ctx, `SELECT COALESCE("subtask_id"::text, ''), payload ->> 'content', payload ->> 'progress_number'
			FROM task_events WHERE "user_id" = $1 AND "task_id" = $2::uuid AND "kind" = 'progress'
			ORDER BY "seq"`, user, taskID)
		if err != nil {
			return err
		}
		defer rs.Close()
		for rs.Next() {
			var r row
			if err := rs.Scan(&r.subtaskID, &r.content, &r.number); err != nil {
				return err
			}
			rows = append(rows, r)
		}
		return rs.Err()
	}); err != nil {
		t.Fatalf("reading the ledger rows: %v", err)
	}
	if len(rows) != 1 {
		t.Fatalf("ledger progress rows = %d, want 1: the update wrote one note", len(rows))
	}
	if rows[0].subtaskID != subtaskID {
		t.Fatalf("row names subtask %q, want %q: subtask_id is what distinguishes a subtask's note from the task's own",
			rows[0].subtaskID, subtaskID)
	}
	if want := "=== Progress 1 ===\n" + noteText; rows[0].content != want {
		t.Fatalf("row content = %q, want %q", rows[0].content, want)
	}
	if rows[0].number != "1" {
		t.Fatalf("row progress_number = %q, want 1", rows[0].number)
	}
}
