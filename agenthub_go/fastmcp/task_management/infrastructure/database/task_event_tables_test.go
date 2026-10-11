package database

import (
	"strings"
	"testing"
)

// TestTaskEventTableRegisteredAfterTasks is an O1a acceptance test that needs NO database, so it is
// a real pass on this box rather than a skip.
//
// It asserts two things the schema route depends on: task_events is IN Tables (the append ran, and
// a hand-written file registering its own table is the kind of thing that silently does not happen),
// and it comes AFTER tasks - because createAll walks Tables in slice order and creates each table
// only when absent, with no dependency sort, so a foreign key to a table not yet created fails.
func TestTaskEventTableRegisteredAfterTasks(t *testing.T) {
	tasksIdx, taskEventsIdx := -1, -1
	for i, td := range Tables {
		switch td.Name {
		case "tasks":
			tasksIdx = i
		case "task_events":
			taskEventsIdx = i
		}
	}
	if taskEventsIdx < 0 {
		t.Fatal("task_events is not in Tables: the init() append did not run or did not take")
	}
	if tasksIdx < 0 {
		t.Fatal("tasks is not in Tables, which the ordering claim is relative to")
	}
	if taskEventsIdx < tasksIdx {
		t.Fatalf("task_events is at %d and tasks at %d: createAll walks Tables in order, so the referenced table must come first",
			taskEventsIdx, tasksIdx)
	}
}

// TestTaskEventTableDeclaresItsConstraints checks the DDL carries the constraints the ledger's
// correctness rests on, read from the DDL string rather than from a live database - this is the DDL
// the embedded runner executes through createAll, which is why the columns and their uniques are
// asserted HERE rather than left to whoever runs the SQL by hand. The vocabularies are CHECKs, not
// PostgreSQL types: extending a CHECK is one DDL string and the registry has no lifecycle for
// CREATE TYPE.
func TestTaskEventTableDeclaresItsConstraints(t *testing.T) {
	var ddl string
	for _, td := range Tables {
		if td.Name == "task_events" {
			ddl = strings.Join(td.DDL, "\n")
		}
	}
	if ddl == "" {
		t.Fatal("no DDL for task_events")
	}
	for _, want := range []string{
		"ck_task_event_kind",         // the closed kind vocabulary
		"ck_task_event_actor_kind",   // the closed actor-kind vocabulary
		"uq_task_event_seq",          // the belt to the advisory lock's brace
		"uq_task_event_user_seq",     // the cursor: one user never repeats a user_seq
		"uq_task_event_client_event", // the outbox: a resent client_event_id lands once
		"user_seq BIGINT NOT NULL",   // the cursor column itself
		"client_event_id UUID",       // the outbox key, nullable
		"subtask_id UUID",            // the nullable subtask an entry can be about
	} {
		if !strings.Contains(ddl, want) {
			t.Errorf("task_events DDL does not declare %s", want)
		}
	}
	if strings.Contains(ddl, "ON DELETE CASCADE") {
		t.Error("foreign keys carry no CASCADE by this schema's design: the application layer cascades")
	}
}
