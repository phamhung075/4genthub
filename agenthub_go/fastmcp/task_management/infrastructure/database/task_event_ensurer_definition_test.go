package database

import (
	"strings"
	"testing"
)

// The ensurer carries task_events' kind and actor vocabularies so that a database predating them can
// be brought to the definition. This pins those lists to the definition itself: a later vocabulary
// change must fail HERE, rather than shipping an ensurer that widens an existing database to a list
// nobody uses any more - which is the same "agreed only by discipline" failure the seam exists for,
// moved one level up.
func TestEnsureTaskEventColumnsMatchTheDefinition(t *testing.T) {
	var ddl string
	for _, def := range Tables {
		if def.Name == "task_events" {
			ddl = strings.Join(def.DDL, "\n")
			break
		}
	}
	if ddl == "" {
		t.Fatal("task_events is not in the runtime registry")
	}
	for _, vocabulary := range []struct{ column, ensurer string }{
		{"kind", taskEventKindVocabulary},
		{"actor_kind", taskEventActorKindVocabulary},
	} {
		clause := "CHECK (" + vocabulary.column + " IN (" + vocabulary.ensurer + "))"
		if !strings.Contains(ddl, clause) {
			t.Errorf("the ensurer's %s vocabulary is not the definition's: the TableDef's DDL does not contain %s",
				vocabulary.column, clause)
		}
	}
	statements := strings.Join(append(append([]string{}, taskEventDefinitionStatements...), taskEventUniqueStatements...), "\n")
	for _, want := range []string{
		"ADD COLUMN IF NOT EXISTS user_seq BIGINT",
		"ADD COLUMN IF NOT EXISTS client_event_id UUID",
		"ALTER COLUMN user_seq SET NOT NULL",
		"uq_task_event_user_seq",
		"uq_task_event_client_event",
	} {
		if !strings.Contains(statements, want) {
			t.Errorf("the ensurer no longer performs %q", want)
		}
	}
	for _, declared := range []string{"user_seq BIGINT", "client_event_id UUID"} {
		if !strings.Contains(ddl, declared) {
			t.Errorf("the TableDef no longer declares %q, so the ensurer adds a column the definition does not have", declared)
		}
	}
}
