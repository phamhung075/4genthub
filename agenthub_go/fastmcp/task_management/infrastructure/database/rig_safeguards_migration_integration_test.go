package database_test

// The 0004 step against a real PostgreSQL, on the database it exists for: one that already holds the
// retired vocabulary. A `rigd` row can only be in the table this step is for, because the constraint
// the step replaces is the only one that admitted the name - so the fixture builds that table by hand
// from the baseline as it stood before the step (`2c05e0a0`) instead of booting the current schema.
//
// What it proves, in the order the step's own acceptance states it: one legacy `rigd` row is gone and
// the machine row is `agent` with the empty rig; the rig-scoped rows are untouched; applying the SQL a
// second time is a no-op; and the two constraints refuse the retired name and a rig on a
// machine-scoped row, which is the rule the ingest states in validate().

import (
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/jackc/pgx/v5/pgconn"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

// sixSafeguardsStep is the step's name, which is also its identity in applied_migrations.
const sixSafeguardsStep = "0004_six_safeguards_and_machine_scope"

// legacyRigSafeguardsTable is that table verbatim as `0001_baseline.sql` created it before this step:
// the four legacy names and no rig rule at all.
const legacyRigSafeguardsTable = `CREATE TABLE rig_safeguards (
	user_id VARCHAR(64) NOT NULL,
	connector_id VARCHAR(64) NOT NULL,
	rig VARCHAR(255) NOT NULL,
	safeguard VARCHAR(32) NOT NULL,
	state VARCHAR(20) NOT NULL,
	pid INTEGER,
	restarts INTEGER NOT NULL,
	age_s INTEGER NOT NULL,
	last_beat_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (user_id, connector_id, rig, safeguard),
	CONSTRAINT ck_rig_safeguards_state CHECK (state IN ('running', 'stopped', 'silent', 'failing')),
	CONSTRAINT ck_rig_safeguards_safeguard CHECK (safeguard IN ('compact', 'watchdog', 'bridge', 'rigd'))
)`

// embeddedStep returns one step of the embedded set by name, so a case runs the SAME bytes the runner
// runs.
func embeddedStep(t *testing.T, name string) database.Migration {
	t.Helper()
	set, err := database.LoadMigrations()
	if err != nil {
		t.Fatal(err)
	}
	names := make([]string, 0, len(set))
	for _, m := range set {
		if m.Name == name {
			return m
		}
		names = append(names, m.Name)
	}
	t.Fatalf("%s is not in the embedded set %v", name, names)
	return database.Migration{}
}

func TestTheSixSafeguardsStepMovesTheStoredVocabulary(t *testing.T) {
	sessions, _ := newBareRunnerEnv(t)
	ctx := context.Background()
	exec := func(sql string) {
		t.Helper()
		if err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
			_, err := s.ExecContext(ctx, sql)
			return err
		}); err != nil {
			t.Fatalf("statement %q failed: %v", strings.SplitN(sql, "\n", 2)[0], err)
		}
	}
	rowsWhere := func(where string) int {
		t.Helper()
		count := 0
		if err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
			return s.QueryRowContext(ctx, `SELECT count(*) FROM rig_safeguards WHERE `+where).Scan(&count)
		}); err != nil {
			t.Fatal(err)
		}
		return count
	}

	exec(legacyRigSafeguardsTable)
	exec(`INSERT INTO rig_safeguards (user_id, connector_id, rig, safeguard, state, restarts, age_s)
	      VALUES ('u1', 'c1', '', 'rigd', 'running', 3, 12)`)
	exec(`INSERT INTO rig_safeguards (user_id, connector_id, rig, safeguard, state, restarts, age_s)
	      VALUES ('u1', 'c1', 'rig-1', 'compact', 'running', 0, 4)`)
	// Two rows the old constraint admitted and the new scope rule cannot: a machine-scoped bridge
	// carrying a rig (the old validate() demanded a rig for EVERY name, so this is the shape a legacy
	// bridge row has) and a rig-scoped name with an empty rig (which only a writer that bypassed
	// validate() could have stored). Both must be dropped rather than carried into a shape no reporter
	// sent.
	exec(`INSERT INTO rig_safeguards (user_id, connector_id, rig, safeguard, state, restarts, age_s)
	      VALUES ('u1', 'c1', 'rig-1', 'bridge', 'running', 0, 5)`)
	exec(`INSERT INTO rig_safeguards (user_id, connector_id, rig, safeguard, state, restarts, age_s)
	      VALUES ('u1', 'c1', '', 'watchdog', 'running', 0, 6)`)

	runner := &database.Runner{Sessions: sessions, Set: []database.Migration{embeddedStep(t, sixSafeguardsStep)}}
	applied, err := runner.Apply(ctx)
	if err != nil {
		t.Fatalf("the step failed: %v", err)
	}
	if len(applied) != 1 || applied[0] != sixSafeguardsStep {
		t.Fatalf("the run applied %v, want just %s", applied, sixSafeguardsStep)
	}

	if got := rowsWhere(`safeguard = 'rigd'`); got != 0 {
		t.Errorf("rigd rows = %d, want 0: the retired name is deleted, not aliased", got)
	}
	if got := rowsWhere(`safeguard = 'agent' AND rig = ''`); got != 1 {
		t.Errorf("agent rows with an empty rig = %d, want 1: the machine row keeps its report under the new name", got)
	}
	if got := rowsWhere(`safeguard = 'agent' AND restarts = 3 AND age_s = 12`); got != 1 {
		t.Errorf("the renamed row's own report was not carried: %d rows hold it, want 1", got)
	}
	if got := rowsWhere(`safeguard = 'compact' AND rig = 'rig-1'`); got != 1 {
		t.Errorf("rig-scoped rows = %d, want the one the fixture wrote, untouched", got)
	}
	if got := rowsWhere(`safeguard = 'bridge' OR safeguard = 'watchdog'`); got != 0 {
		t.Errorf("rows the new scope rule cannot accept = %d, want 0: they are dropped, not merged into a shape no reporter sent", got)
	}

	// THE LEDGER is what stops a second boot, so this runs the step's SQL again to prove the SQL
	// itself is idempotent - which the schema file cannot be (every statement in it is
	// CREATE ... IF NOT EXISTS). DROP CONSTRAINT IF EXISTS plus ADD is, and the UPDATE matches
	// nothing the second time.
	exec(embeddedStep(t, sixSafeguardsStep).SQL)
	if got := rowsWhere(`safeguard = 'agent' AND rig = ''`); got != 1 {
		t.Errorf("a second application left %d agent rows, want still 1", got)
	}
	if applied, err := runner.Apply(ctx); err != nil || len(applied) != 0 {
		t.Errorf("the recorded step ran again: applied %v err %v", applied, err)
	}

	// The DATABASE states the rule too, so a writer that skips the ingest cannot store either half of
	// the retired shape or a rig where the scope forbids one.
	for _, c := range []struct{ what, row string }{
		{"the retired rigd name", `('u1', 'c1', 'rig-1', 'rigd', 'running', 0, 1)`},
		{"a rig on the machine-scoped bridge", `('u1', 'c1', 'rig-1', 'bridge', 'running', 0, 1)`},
		{"a rig on the machine-scoped agent", `('u1', 'c1', 'rig-1', 'agent', 'running', 0, 1)`},
		{"a rig-scoped safeguard with no rig", `('u1', 'c1', '', 'compact', 'running', 0, 1)`},
	} {
		t.Run("the database refuses "+c.what, func(t *testing.T) {
			err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
				_, err := s.ExecContext(ctx,
					`INSERT INTO rig_safeguards (user_id, connector_id, rig, safeguard, state, restarts, age_s) VALUES `+c.row)
				return err
			})
			var pg *pgconn.PgError
			if !errors.As(err, &pg) || pg.Code != "23514" {
				t.Fatalf("the insert answered %v, want a CHECK violation (SQLSTATE 23514)", err)
			}
		})
	}

	// And every name the client reports is storable in its own scope, which is the point of the step.
	for _, c := range []struct{ safeguard, rig string }{
		{"compact", "rig-1"}, {"watchdog", "rig-1"}, {"messages", "rig-1"}, {"roomguard", "rig-1"},
		{"bridge", ""}, {"agent", ""},
	} {
		exec(`INSERT INTO rig_safeguards (user_id, connector_id, rig, safeguard, state, restarts, age_s) ` +
			`VALUES ('u2', 'c2', '` + c.rig + `', '` + c.safeguard + `', 'running', 0, 1)`)
	}
	if got := rowsWhere(`user_id = 'u2'`); got != 6 {
		t.Errorf("stored rows for the six names = %d, want 6", got)
	}
}
