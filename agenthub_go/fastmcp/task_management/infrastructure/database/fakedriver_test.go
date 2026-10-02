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
		var rows [][]driver.Value
		for _, t := range []string{"subtasks", "tasks"} {
			if _, ok := s.f.tables[t]; ok {
				rows = append(rows, []driver.Value{t})
			}
		}
		return &fakeRows{cols: []string{"table_name"}, rows: rows}, nil
	case strings.Contains(s.q, "information_schema.columns"):
		var rows [][]driver.Value
		for _, c := range s.f.tables[args[0].(string)] {
			rows = append(rows, []driver.Value{c})
		}
		return &fakeRows{cols: []string{"column_name"}, rows: rows}, nil
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
