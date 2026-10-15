package database

import (
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

// These are the audit trail's own guards, and they need NO database, so they are real passes on a box
// with no PostgreSQL rather than skips: what they measure is the registry and the DDL string the boot
// path executes.

// TestTaskAuditTableIsRegisteredAndCarriesNoForeignKey asserts the two facts the trail's whole point
// rests on: the table is IN Tables (a hand-written file registering its own table is the kind of
// thing that silently does not happen, which is the ledger's own reason for the same test), and
// task_id is NOT a foreign key - a foreign key to tasks would let the delete cascade remove the record
// that exists to outlive the task.
func TestTaskAuditTableIsRegisteredAndCarriesNoForeignKey(t *testing.T) {
	var ddl string
	for _, td := range Tables {
		if td.Name == "task_audit_records" {
			ddl = strings.Join(td.DDL, "\n")
		}
	}
	if ddl == "" {
		t.Fatal("task_audit_records is not in Tables: the init() append did not run or did not take")
	}
	for _, want := range []string{
		"ck_task_audit_record_kind", // the closed kind vocabulary
		"task_id UUID NOT NULL",     // the task the record describes, as a plain id
		"created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL",
		"idx_task_audit_record_task", // the read a human makes: one task's trail
	} {
		if !strings.Contains(ddl, want) {
			t.Errorf("the DDL does not carry %q:\n%s", want, ddl)
		}
	}
	if strings.Contains(ddl, "REFERENCES") || strings.Contains(ddl, "FOREIGN KEY") {
		t.Fatalf("the audit table declares a foreign key: the record a prune writes must OUTLIVE the task row the delete cascade removes, so task_id is an id here and not a reference:\n%s", ddl)
	}
}

// TestTaskAuditKindVocabularyMatchesTheCheckConstraint holds the Go vocabulary against the CHECK
// constraint that refuses anything else. The two must not drift, because a value the Go side offers
// and the database refuses fails where the bytes land rather than where they are chosen - and the
// order matters too, since the constraint lists the vocabulary in declaration order.
func TestTaskAuditKindVocabularyMatchesTheCheckConstraint(t *testing.T) {
	var ddl string
	for _, td := range Tables {
		if td.Name == "task_audit_records" {
			ddl = strings.Join(td.DDL, "\n")
		}
	}
	if ddl == "" {
		t.Fatal("task_audit_records is not in Tables")
	}
	open := strings.Index(ddl, "kind IN (")
	if open < 0 {
		t.Fatalf("the DDL declares no kind CHECK:\n%s", ddl)
	}
	rest := ddl[open+len("kind IN ("):]
	close := strings.Index(rest, ")")
	if close < 0 {
		t.Fatalf("the kind CHECK is not closed:\n%s", ddl)
	}
	want := make([]string, 0, len(entities.TaskAuditKindValues))
	for _, kind := range entities.TaskAuditKindValues {
		want = append(want, "'"+string(kind)+"'")
	}
	got := strings.Split(rest[:close], ", ")
	if strings.Join(got, ",") != strings.Join(want, ",") {
		t.Fatalf("the CHECK lists %v, the Go vocabulary is %v", got, want)
	}
}
