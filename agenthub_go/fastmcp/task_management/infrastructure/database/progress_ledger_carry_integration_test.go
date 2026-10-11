package database_test

// Fixtures shared with the ruled carry-and-drop step's acceptance
// (progress_history_drop_integration_test.go): seeding the project/branch chain a task hangs off,
// seeding a task whose dropped progress columns hold a note, and reading back the note text the task
// dialog renders from the ledger alone.
//
// The two cases that used to live here ran the ADDITIVE 0002 backfill over a freshly seeded column
// and asserted the union read. That step is superseded by 0003, which carries the same notes and then
// drops the columns, and 0003's own acceptance is in progress_history_drop_integration_test.go - so
// the cases here are gone and only the fixtures they used remain, because that file seeds through
// them.
//
// It needs AGENTHUB_TEST_PG_URL (see tools/testpg/start.sh) and skips loudly without it.

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
	"agenthub/fastmcp/task_management/infrastructure/repositories"
)

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
// written a ledger event for it - the pre-switch state. The column no longer exists on a database the
// boot built from this tree, so the step's own acceptance restores it first
// (progress_history_drop_integration_test.go's restorePreDropColumns) and then calls this.
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
