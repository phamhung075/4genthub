package database

// Column ensurers — the registration seam for a table whose COLUMN was added to its definition
// after the table already existed. createAll creates a table only when it is ABSENT, so a column
// added to a registered definition never reaches a database that already holds the table; that is
// the same trap the ck_modules_kind widening is recorded against, and no later DDL reaches such
// a database without a migration. A domain that owns such a column registers a function here,
// mirroring the Tables registry, so the boot keeps ONE DDL path rather than one per domain.
//
// They run only under AUTO_MIGRATE=true: CreateTables is their only caller, and InitDatabase
// reaches it only under that opt-in. Each ensurer must be idempotent — it inspects or uses
// IF NOT EXISTS — so a boot repeated any number of times changes nothing after the first.

import (
	"context"
	"database/sql"
)

// ColumnEnsurer adds a domain's missing columns, and their indexes, to an existing schema.
type ColumnEnsurer func(ctx context.Context, db *sql.DB) error

// ColumnEnsurers holds the registered ensurers in registration order.
var ColumnEnsurers []ColumnEnsurer

// RunColumnEnsurers runs every registered ensurer and returns the first error. One domain
// failing must not skip the others, so the rest still run.
func RunColumnEnsurers(ctx context.Context, db *sql.DB) error {
	var first error
	for _, ensure := range ColumnEnsurers {
		if err := ensure(ctx, db); err != nil && first == nil {
			first = err
		}
	}
	return first
}
