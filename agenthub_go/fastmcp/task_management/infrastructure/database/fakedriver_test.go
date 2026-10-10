package database

import (
	"context"
	"database/sql"
	"database/sql/driver"
	"fmt"
	"io"
	"strings"
	"sync"
)

// fakeDB is a scripted database/sql driver: it records every statement and answers the
// catalogue queries the database package issues.
type fakeDB struct {
	mu         sync.Mutex
	statements []string
	tables     map[string][]string
	failExec   func(q string) error
	// failTablesRead fails the information_schema.tables read specifically: a failed catalogue read and
	// an empty database must be distinguishable, and only a seam that fails THAT query can show it.
	failTablesRead func(q string) error
	// schema is what the column drift query returns; blocking marks a NOT NULL column without a default.
	schema    []fakeColumn
	failQuery func(q string) error
}

type fakeColumn struct {
	table, column string
	blocking      bool
}

func newFakeDB() *fakeDB {
	return &fakeDB{tables: map[string][]string{"tasks": {"id", "title"}, "subtasks": {"id", "ai_system_prompt"}}}
}

func (f *fakeDB) record(q string) { f.mu.Lock(); f.statements = append(f.statements, q); f.mu.Unlock() }

func (f *fakeDB) open(string, EngineOptions) (*sql.DB, error) {
	return sql.OpenDB(fakeConnector{f}), nil
}

type fakeConnector struct{ f *fakeDB }

func (c fakeConnector) Connect(context.Context) (driver.Conn, error) { return &fakeConn{c.f}, nil }
func (c fakeConnector) Driver() driver.Driver                        { return nil }

type fakeConn struct{ f *fakeDB }

func (c *fakeConn) Prepare(q string) (driver.Stmt, error) { return &fakeStmt{c.f, q}, nil }
func (c *fakeConn) Close() error                          { return nil }
func (c *fakeConn) Begin() (driver.Tx, error)             { c.f.record("BEGIN"); return fakeTx{c.f}, nil }

type fakeTx struct{ f *fakeDB }

func (t fakeTx) Commit() error   { t.f.record("COMMIT"); return nil }
func (t fakeTx) Rollback() error { t.f.record("ROLLBACK"); return nil }

type fakeStmt struct {
	f *fakeDB
	q string
}

func (s *fakeStmt) Close() error  { return nil }
func (s *fakeStmt) NumInput() int { return -1 }
func (s *fakeStmt) Exec(args []driver.Value) (driver.Result, error) {
	s.f.record(s.q)
	if s.f.failExec != nil {
		if err := s.f.failExec(s.q); err != nil {
			return nil, err
		}
	}
	return driver.RowsAffected(0), nil
}
func (s *fakeStmt) Query(args []driver.Value) (driver.Rows, error) {
	s.f.record(s.q)
	switch {
	case strings.Contains(s.q, "information_schema.tables"):
		if s.f.failTablesRead != nil {
			if err := s.f.failTablesRead(s.q); err != nil {
				return nil, err
			}
		}
		var rows [][]driver.Value
		for _, t := range []string{"subtasks", "tasks"} {
			if _, ok := s.f.tables[t]; ok {
				rows = append(rows, []driver.Value{t})
			}
		}
		return &fakeRows{cols: []string{"table_name"}, rows: rows}, nil
	case strings.Contains(s.q, "information_schema.columns") && strings.Contains(s.q, "column_default"):
		if s.f.failQuery != nil {
			if err := s.f.failQuery(s.q); err != nil {
				return nil, err
			}
		}
		var rows [][]driver.Value
		for _, c := range s.f.schema {
			rows = append(rows, []driver.Value{c.table, c.column, c.blocking})
		}
		return &fakeRows{cols: []string{"table_name", "column_name", "blocking"}, rows: rows}, nil
	case strings.Contains(s.q, "information_schema.columns"):
		var rows [][]driver.Value
		for _, c := range s.f.tables[args[0].(string)] {
			rows = append(rows, []driver.Value{c})
		}
		return &fakeRows{cols: []string{"column_name"}, rows: rows}, nil
	case strings.Contains(s.q, "pg_attribute"):
		// The ensurer's verify pass reads the catalogue back. This double exists to model the DDL path,
		// not to disagree with it, so it answers from the same TableDef the schema is built from: a
		// relation the registry does not know returns no rows, which is how a fake database says it
		// does not have that table.
		if s.f.failQuery != nil {
			if err := s.f.failQuery(s.q); err != nil {
				return nil, err
			}
		}
		var rows [][]driver.Value
		for _, def := range Tables {
			if def.Name != args[0].(string) {
				continue
			}
			for _, c := range def.Columns {
				rows = append(rows, []driver.Value{c.Name, c.SQLType, !c.Nullable})
			}
		}
		return &fakeRows{cols: []string{"attname", "format_type", "attnotnull"}, rows: rows}, nil
	case s.q == "SELECT version()":
		return &fakeRows{cols: []string{"version"}, rows: [][]driver.Value{{"PostgreSQL 16 fake"}}}, nil
	case s.q == "SELECT current_database()":
		return &fakeRows{cols: []string{"db"}, rows: [][]driver.Value{{"fakedb"}}}, nil
	}
	return nil, fmt.Errorf("unexpected query %q", s.q)
}

type fakeRows struct {
	cols []string
	rows [][]driver.Value
	i    int
}

func (r *fakeRows) Columns() []string { return r.cols }
func (r *fakeRows) Close() error      { return nil }
func (r *fakeRows) Next(dest []driver.Value) error {
	if r.i >= len(r.rows) {
		return io.EOF
	}
	copy(dest, r.rows[r.i])
	r.i++
	return nil
}
