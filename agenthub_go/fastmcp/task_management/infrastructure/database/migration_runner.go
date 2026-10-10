package database

// The schema's own history, as one ordered set of embedded migrations.
//
// WHY THIS EXISTS. The tree evolves its schema three ways today that agree only by discipline: the
// TableDef sets create missing tables, the embedded init SQL (db_initializer.go) is a second full
// DDL source, and the column ensurers (column_ensurers.go) add columns on every boot and record
// nothing. T12's ruling is that one ordered set of embedded migrations becomes the only DDL source.
// THIS FILE IS THE MECHANISM, NOT THE FOLD: it applies an ordered set and records every step it
// applies in the EXISTING applied_migrations table (models_prod.go:118), in the same transaction as
// that step's own effect. Folding createAll and the init SQL into the 0001 baseline, and marking
// 0001 on a database that already exists, are separate steps - the mark belongs to the owner,
// because it touches production.

import (
	"context"
	"database/sql"
	"embed"
	"errors"
	"fmt"
	"io/fs"
	"path"
	"sort"
	"strings"
)

//go:embed migrations
var migrationFS embed.FS

// Migration is one step of the schema's history: the file's base name without its .sql suffix, and
// its SQL. The name is what applied_migrations records, so it is the step's identity and must never
// change once it has been applied anywhere.
type Migration struct {
	Name string
	SQL  string
}

// LoadMigrations returns the embedded set in the order the runner must apply it: filename order,
// which for zero-padded names is numeric order.
func LoadMigrations() ([]Migration, error) {
	return loadMigrations(migrationFS)
}

// loadMigrations reads every .sql file under migrations/ and validates the set it forms. It takes
// the filesystem as an argument so the ordering rule is testable without touching the embedded set.
func loadMigrations(fsys fs.FS) ([]Migration, error) {
	paths, err := fs.Glob(fsys, "migrations/*.sql")
	if err != nil {
		return nil, err
	}
	sort.Strings(paths)
	set := make([]Migration, 0, len(paths))
	for _, p := range paths {
		body, err := fs.ReadFile(fsys, p)
		if err != nil {
			return nil, err
		}
		set = append(set, Migration{Name: strings.TrimSuffix(path.Base(p), ".sql"), SQL: string(body)})
	}
	if err := validateSet(set); err != nil {
		return nil, err
	}
	return set, nil
}

// validateSet refuses a set the runner cannot apply unambiguously: a nameless step, a step with no
// SQL, a duplicate name - which applied_migrations' UNIQUE (migration_name) would refuse mid-run,
// after earlier steps had already committed - or a name out of order, because the runner applies the
// slice as given and that order IS the contract.
func validateSet(set []Migration) error {
	seen := make(map[string]bool, len(set))
	for i, m := range set {
		if m.Name == "" {
			return fmt.Errorf("migration %d has no name", i)
		}
		if strings.TrimSpace(m.SQL) == "" {
			return fmt.Errorf("migration %q has no SQL", m.Name)
		}
		if seen[m.Name] {
			return fmt.Errorf("migration %q appears twice", m.Name)
		}
		if i > 0 && set[i-1].Name >= m.Name {
			return fmt.Errorf("migration %q is out of order after %q: the set must be sorted by name",
				m.Name, set[i-1].Name)
		}
		seen[m.Name] = true
	}
	return nil
}

// Runner applies a set of migrations and records each one it applies.
type Runner struct {
	// Sessions is the transaction seam: a step's SQL and its ledger row are written through one
	// session, inside one transaction.
	Sessions *SessionManager
	// Set is the ordered set, as LoadMigrations returns it.
	Set []Migration
}

// migrationLockKey names the advisory lock that keeps two boots from applying the same step at the
// same time. It is a string rather than a bare number so the lock's owner is readable in the
// catalogue; hashtext maps it into the lock space, exactly as the task-event sequence lock does.
const migrationLockKey = "agenthub_schema_migrations"

// Apply applies, in order, every migration that applied_migrations does not already record, and
// returns the names it applied in this run.
//
// EACH STEP IS ITS OWN TRANSACTION, holding its SQL and its ledger row. A step whose SQL fails
// therefore records nothing and leaves none of its own effect behind, while the steps before it stay
// applied and recorded, so the next run resumes where this one stopped. One transaction for the
// whole set would roll a run's earlier successes back and re-run them - which is how a runner loses
// the record of what actually ran.
//
// The ledger is read INSIDE the migration advisory lock, which is what makes "is it applied?" and
// "record that it is" one decision rather than two a second boot can interleave with.
func (r *Runner) Apply(ctx context.Context) ([]string, error) {
	if r.Sessions == nil {
		return nil, fmt.Errorf("migration runner has no session manager")
	}
	if err := validateSet(r.Set); err != nil {
		return nil, err
	}
	var applied []string
	for _, m := range r.Set {
		didApply := false
		err := r.Sessions.Transaction(ctx, func(txCtx context.Context) error {
			return r.Sessions.WithSession(txCtx, func(ctx context.Context, s DBTX) error {
				if err := lockMigrations(ctx, s); err != nil {
					return err
				}
				if err := ensureLedgerInTx(ctx, s); err != nil {
					return err
				}
				recorded, err := isRecorded(ctx, s, m.Name)
				if err != nil {
					return err
				}
				if recorded {
					return nil
				}
				if _, err := s.ExecContext(ctx, m.SQL); err != nil {
					return fmt.Errorf("the migration's SQL failed: %w", err)
				}
				if _, err := s.ExecContext(ctx,
					`INSERT INTO applied_migrations (migration_name) VALUES ($1)`, m.Name); err != nil {
					return fmt.Errorf("recording the migration failed: %w", err)
				}
				didApply = true
				return nil
			})
		})
		if err != nil {
			return applied, fmt.Errorf("migration %s: %w", m.Name, err)
		}
		if didApply {
			applied = append(applied, m.Name)
		}
	}
	return applied, nil
}

// MarkBaseline records the named migrations as applied WITHOUT running their SQL. That is what an
// existing database needs for the 0001 baseline: its schema is already there, so executing 0001
// would be wrong, and leaving it unrecorded would make every later run try again.
//
// Choosing to mark a database is an owner action; this is only the mechanism. It refuses a name the
// set does not contain, so a typo cannot mark nothing while looking like a successful stamp, and it
// returns the names it marked in this call - a name already recorded is left alone rather than
// failing, because the mark has to be safely repeatable by hand.
func (r *Runner) MarkBaseline(ctx context.Context, names ...string) ([]string, error) {
	if r.Sessions == nil {
		return nil, fmt.Errorf("migration runner has no session manager")
	}
	if err := validateSet(r.Set); err != nil {
		return nil, err
	}
	inSet := make(map[string]bool, len(r.Set))
	for _, m := range r.Set {
		inSet[m.Name] = true
	}
	for _, n := range names {
		if !inSet[n] {
			return nil, fmt.Errorf("migration %q is not in this binary's set, so marking it would record a step the binary does not have", n)
		}
	}
	var marked []string
	for _, n := range names {
		didMark := false
		err := r.Sessions.Transaction(ctx, func(txCtx context.Context) error {
			return r.Sessions.WithSession(txCtx, func(ctx context.Context, s DBTX) error {
				if err := lockMigrations(ctx, s); err != nil {
					return err
				}
				if err := ensureLedgerInTx(ctx, s); err != nil {
					return err
				}
				recorded, err := isRecorded(ctx, s, n)
				if err != nil {
					return err
				}
				if recorded {
					return nil
				}
				if _, err := s.ExecContext(ctx,
					`INSERT INTO applied_migrations (migration_name) VALUES ($1)`, n); err != nil {
					return err
				}
				didMark = true
				return nil
			})
		})
		if err != nil {
			return marked, fmt.Errorf("marking %s as a baseline: %w", n, err)
		}
		if didMark {
			marked = append(marked, n)
		}
	}
	return marked, nil
}

// lockMigrations takes the transaction-scoped migration lock. The transaction form is the one this
// codebase uses everywhere: it releases itself on commit or rollback, so there is no path that
// leaves the lock held.
func lockMigrations(ctx context.Context, s DBTX) error {
	_, err := s.ExecContext(ctx, `SELECT pg_advisory_xact_lock(hashtext($1))`, migrationLockKey)
	return err
}

// ensureLedgerInTx creates applied_migrations when this database lacks it, using the SAME declaration
// the schema carries (ProductionTables), so the ledger is not a second hand-written copy of its own
// table. A database that already has it - production has it from the Python runner and the init-SQL
// path - is left untouched.
//
// The runner owns its bookkeeping, which is why this exists at all: the registry's tables and the
// production tables are created by different paths today (that is the "exactly one schema creator"
// question, its own row), so a database built by the registry alone would otherwise fail the first
// step on a missing table instead of recording it.
func ensureLedgerInTx(ctx context.Context, s DBTX) error {
	var present bool
	if err := s.QueryRowContext(ctx, `SELECT to_regclass('applied_migrations') IS NOT NULL`).Scan(&present); err != nil {
		return err
	}
	if present {
		return nil
	}
	for _, def := range ProductionTables {
		if def.Name != "applied_migrations" {
			continue
		}
		for _, stmt := range def.DDL {
			if _, err := s.ExecContext(ctx, stmt); err != nil {
				return fmt.Errorf("creating the migration ledger: %w", err)
			}
		}
		return nil
	}
	return fmt.Errorf("applied_migrations is not in the table registry, so the migration ledger cannot be created")
}

// isRecorded reports whether applied_migrations already holds this step. A row exists exactly when
// the step applied: the table's legacy success/error_message columns are never written by this
// runner, because a step that fails rolls back and records nothing at all.
func isRecorded(ctx context.Context, s DBTX, name string) (bool, error) {
	var one int
	err := s.QueryRowContext(ctx,
		`SELECT 1 FROM applied_migrations WHERE migration_name = $1`, name).Scan(&one)
	if errors.Is(err, sql.ErrNoRows) {
		return false, nil
	}
	if err != nil {
		return false, err
	}
	return true, nil
}
