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
	// The COLUMN half of this test is gone with the hand-written list it pinned: the ensurer now takes
	// its columns from the TableDef (EnsureTableColumns, via taskEventDatabaseTables), so "the ensurer
	// adds a column the definition lacks" and "a declared column is left out" are no longer expressible.
	// What that asserted is now measured by behaviour instead of by text, in
	// TestTaskEventEnsurerRestoresEveryColumnOfTheDefinition, which builds the table from the
	// definition minus one column and requires the ensurer to restore it - the case the old fixture
	// could not make, because it modelled the shape the ensurer handles rather than the one production
	// has. The two per-user uniques stay covered by their own behavioural case too.
}
