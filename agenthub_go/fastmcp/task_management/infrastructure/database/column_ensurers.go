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
	"fmt"
	"strings"
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

// ColumnDataMove fills a column's existing rows before that column is made NOT NULL, inside the
// caller's transaction. A NOT NULL column with NO move is added nullable and then SET NOT NULL, which
// passes on an empty table and fails LOUDLY, naming the column, on a populated one - the intended
// outcome, because only an operator knows the value that belongs there.
type ColumnDataMove func(ctx context.Context, tx *sql.Tx, table, column string) error

// EnsureTableColumns derives the COLUMN half of a table's definition, so a column added to the
// TableDef reaches a database that already holds the table without a second, hand-kept list of
// columns - a list that can leave one out, which is the defect this shape exists to remove.
//
// The columns, the data moves, the NOT NULL steps and `then` (the caller's constraint statements) run
// in ONE transaction, so a database either ends up with the whole delta or is left exactly as it was.
// The caller runs its vocabularies afterwards in their own transaction: re-creating a CHECK validates
// every existing row, so a table holding the OLD vocabulary must still get its columns and then fail
// loudly on the constraint an operator has to migrate.
//
// It ends with a verify pass that REPORTS differences and never repairs them: ADD COLUMN IF NOT
// EXISTS says nothing about a column of the wrong type, so without this a missing column (loud) would
// become a wrong shape (silent).
func EnsureTableColumns(ctx context.Context, db *sql.DB, table TableDef, dataMoves map[string]ColumnDataMove, then []string) error {
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	for _, c := range table.Columns {
		if _, err := tx.ExecContext(ctx, addColumnSQL(table.Name, c)); err != nil {
			_ = tx.Rollback()
			return err
		}
	}
	// The NOT NULL steps run only after EVERY column exists: a data move may order by another column
	// the same definition adds, and a move that ran before that column was reached would fail on a
	// table about to have it.
	for _, c := range table.Columns {
		if c.Nullable {
			continue
		}
		if move, ok := dataMoves[c.Name]; ok {
			if err := move(ctx, tx, table.Name, c.Name); err != nil {
				_ = tx.Rollback()
				return err
			}
		}
		if _, err := tx.ExecContext(ctx, "ALTER TABLE "+table.Name+" ALTER COLUMN "+c.Name+" SET NOT NULL"); err != nil {
			_ = tx.Rollback()
			return err
		}
	}
	for _, stmt := range then {
		if _, err := tx.ExecContext(ctx, stmt); err != nil {
			_ = tx.Rollback()
			return err
		}
	}
	if err := tx.Commit(); err != nil {
		return err
	}
	return verifyTableColumns(ctx, db, table)
}

// addColumnSQL is one ColumnDef as an ADD COLUMN. The definition's NOT NULL is deliberately NOT here:
// it is applied by a SET NOT NULL after the column exists, so a populated table fails by column name
// instead of the whole statement failing with nothing named.
func addColumnSQL(table string, c ColumnDef) string {
	stmt := "ALTER TABLE " + table + " ADD COLUMN IF NOT EXISTS " + c.Name + " " + c.SQLType
	if c.ServerDefault != "" {
		stmt += " DEFAULT " + c.ServerDefault
	}
	return stmt
}

// verifyTableColumns compares the table in the catalogue against its TableDef on presence, type and
// nullability, and returns the first difference naming table.column with expected and found. It never
// repairs anything: the derived step owns the shape, and a difference here is something a reader has
// to see.
func verifyTableColumns(ctx context.Context, db *sql.DB, table TableDef) error {
	rows, err := db.QueryContext(ctx,
		`SELECT a.attname, format_type(a.atttypid, a.atttypmod), a.attnotnull
		   FROM pg_attribute a
		   JOIN pg_class c ON c.oid = a.attrelid
		  WHERE c.relname = $1 AND a.attnum > 0 AND NOT a.attisdropped`, table.Name)
	if err != nil {
		return err
	}
	defer rows.Close()
	type foundColumn struct {
		typ     string
		notNull bool
	}
	found := map[string]foundColumn{}
	for rows.Next() {
		var name, typ string
		var notNull bool
		if err := rows.Scan(&name, &typ, &notNull); err != nil {
			return err
		}
		found[name] = foundColumn{typ: typ, notNull: notNull}
	}
	if err := rows.Err(); err != nil {
		return err
	}
	for _, c := range table.Columns {
		got, ok := found[c.Name]
		if !ok {
			return fmt.Errorf("%s.%s is missing after the derived step: expected %s", table.Name, c.Name, c.SQLType)
		}
		if normaliseSQLType(got.typ) != normaliseSQLType(c.SQLType) {
			return fmt.Errorf("%s.%s has type %s, want %s", table.Name, c.Name, got.typ, c.SQLType)
		}
		if got.notNull == c.Nullable {
			return fmt.Errorf("%s.%s is NOT NULL=%v, want NOT NULL=%v", table.Name, c.Name, got.notNull, !c.Nullable)
		}
	}
	return nil
}

// normaliseSQLType maps the one alias pair this schema spells two ways. Everything else in these
// tables compares lowercase-equal.
func normaliseSQLType(s string) string {
	return strings.ReplaceAll(strings.ToLower(s), "varchar(", "character varying(")
}
