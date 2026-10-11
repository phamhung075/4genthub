package database

// Tests for the baseline's inert-at-boot gate in Runner.Apply. They drive the runner through the
// scripted fake driver (fakedriver_test.go), which answers the catalogue and ledger queries from its
// own state: the same seam the package's other runner-adjacent cases use, so "the catalogue has
// tables" is expressed by the fake's `tables` map rather than by an interface built for the test.
//
// The parity guard over the baseline FILE lives in migration_baseline_parity_test.go, which is an
// external test file because the registry is completed by packages that import this one.

import (
	"context"
	"errors"
	"reflect"
	"strings"
	"testing"
)

// TestApplySkipsTheBaselineOnAPopulatedCatalogue is the inert-at-boot rule: a catalogue that already
// holds tables skips the baseline - no SQL, no ledger row - and does not fail.
func TestApplySkipsTheBaselineOnAPopulatedCatalogue(t *testing.T) {
	f := newFakeDB() // the fake's catalogue answers with tasks and subtasks
	runner := runnerOverFakeDB(t, f, []Migration{
		{Name: baselineStep, SQL: "CREATE TABLE baseline_probe (id INTEGER)"},
	})

	applied, err := runner.Apply(context.Background())
	if err != nil {
		t.Fatalf("applying to a populated catalogue failed: %v", err)
	}
	if len(applied) != 0 {
		t.Fatalf("the populated-catalogue run applied %v, want nothing: the baseline's schema is already there", applied)
	}
	joined := strings.Join(f.statements, "\n")
	if strings.Contains(joined, "CREATE TABLE baseline_probe") {
		t.Error("the baseline's SQL ran against a populated catalogue")
	}
	if strings.Contains(joined, "CREATE TABLE applied_migrations") {
		t.Error("skipping the baseline created the ledger: a skip writes no bookkeeping")
	}
	if f.ledgerPresent() {
		t.Error("the ledger exists after a skipped baseline")
	}
	if !strings.Contains(joined, "information_schema.tables") {
		t.Error("the gate did not read the catalogue, so the skip rested on nothing")
	}
}

// TestApplyRunsTheBaselineOnAnEmptyCatalogue is the other half: the one case the baseline is for still
// applies, records itself, and creates its own ledger.
func TestApplyRunsTheBaselineOnAnEmptyCatalogue(t *testing.T) {
	f := &fakeDB{tables: map[string][]string{}}
	runner := runnerOverFakeDB(t, f, []Migration{
		{Name: baselineStep, SQL: "CREATE TABLE baseline_probe (id INTEGER)"},
	})

	applied, err := runner.Apply(context.Background())
	if err != nil {
		t.Fatalf("applying to an empty catalogue failed: %v", err)
	}
	if want := []string{baselineStep}; !reflect.DeepEqual(applied, want) {
		t.Fatalf("an empty catalogue applied %v, want %v", applied, want)
	}
	if !strings.Contains(strings.Join(f.statements, "\n"), "CREATE TABLE baseline_probe") {
		t.Error("the baseline did not run against an empty catalogue")
	}
	if !f.ledgerPresent() {
		t.Error("the applied baseline left no ledger behind: the step creates applied_migrations")
	}
	if got, want := f.migrations, []string{baselineStep}; !reflect.DeepEqual(got, want) {
		t.Fatalf("the ledger holds %v, want the applied baseline %v", got, want)
	}
}

// TestApplyLeavesStepsOtherThanTheBaselineUnaffected holds the gate to its own step: the catalogue
// rule is the baseline's, and a later step is applied and recorded exactly as before. A second run
// then applies nothing, which is the recorded-step behaviour unchanged.
func TestApplyLeavesStepsOtherThanTheBaselineUnaffected(t *testing.T) {
	f := &fakeDB{tables: map[string][]string{}}
	later := Migration{Name: "0002_probe", SQL: "CREATE TABLE probe_two (id INTEGER)"}
	runner := runnerOverFakeDB(t, f, []Migration{later})

	applied, err := runner.Apply(context.Background())
	if err != nil {
		t.Fatalf("the first run failed: %v", err)
	}
	if want := []string{later.Name}; !reflect.DeepEqual(applied, want) {
		t.Fatalf("the first run applied %v, want %v", applied, want)
	}
	joined := strings.Join(f.statements, "\n")
	if !strings.Contains(joined, "CREATE TABLE probe_two") {
		t.Error("a step other than the baseline was not applied")
	}
	if strings.Contains(joined, "CREATE TABLE baseline_probe") {
		t.Error("a step other than the baseline triggered the baseline's SQL")
	}

	applied, err = runner.Apply(context.Background())
	if err != nil {
		t.Fatalf("the second run failed: %v", err)
	}
	if len(applied) != 0 {
		t.Fatalf("the second run applied %v: a recorded step must not run again", applied)
	}
}

// TestApplyRefusesTheBaselineWhenTheCatalogueCannotBeRead is the fail-closed half of the gate: an
// unreadable catalogue is neither empty nor populated, and must not be read as licence to run the
// baseline's CREATE TABLE statements.
func TestApplyRefusesTheBaselineWhenTheCatalogueCannotBeRead(t *testing.T) {
	f := &fakeDB{tables: map[string][]string{}}
	f.failTablesRead = func(string) error { return errors.New("the catalogue could not be read") }
	runner := runnerOverFakeDB(t, f, []Migration{
		{Name: baselineStep, SQL: "CREATE TABLE baseline_probe (id INTEGER)"},
	})

	applied, err := runner.Apply(context.Background())
	if err == nil {
		t.Fatal("an unreadable catalogue was accepted and the baseline ran")
	}
	if !strings.Contains(err.Error(), baselineStep) {
		t.Errorf("the refusal does not name the step it refused: %v", err)
	}
	if len(applied) != 0 {
		t.Fatalf("the refused run reported %v applied", applied)
	}
	if strings.Contains(strings.Join(f.statements, "\n"), "CREATE TABLE baseline_probe") {
		t.Error("the baseline's SQL ran although the catalogue could not be read")
	}
}

// runnerOverFakeDB builds a runner whose session manager runs over the scripted fake driver: the
// driver answers the catalogue and ledger queries from its own state instead of a server.
func runnerOverFakeDB(t *testing.T, f *fakeDB, set []Migration) *Runner {
	t.Helper()
	db, err := f.open("", EngineOptions{})
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = db.Close() })
	return &Runner{Sessions: NewSessionManager(&DatabaseConfig{Engine: &Engine{DB: db}}), Set: set}
}
