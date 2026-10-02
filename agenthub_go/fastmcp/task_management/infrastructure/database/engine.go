package database

// Engine plumbing shared by database_config and supabase_config: the Go counterpart of the
// SQLAlchemy Engine (a pooled *sql.DB) and of create_engine's pool/connect arguments.

import (
	"context"
	"database/sql"
)

// Getenv is os.getenv(key) with presence reporting (Python distinguishes unset from empty).
type Getenv func(string) (string, bool)

func (g Getenv) get(key, def string) string {
	if v, ok := g(key); ok {
		return v
	}
	return def
}

// ConnectStatement is one statement run on every new connection (the SQLAlchemy "connect"
// event). Optional statements ignore errors (Python wraps them in try/except).
type ConnectStatement struct {
	SQL      string
	Optional bool
}

// EngineOptions are the create_engine arguments the Python code passes.
type EngineOptions struct {
	PoolSize    int
	MaxOverflow int
	PoolTimeout int
	PoolRecycle int
	PoolPrePing bool
	Echo        bool
	// ConnectArgs are libpq connection parameters in Python dict order.
	ConnectArgs  [][2]string
	AfterConnect []ConnectStatement
}

// Opener creates the pooled database handle for a PostgreSQL URL.
type Opener func(url string, o EngineOptions) (*sql.DB, error)

// Engine is a pooled database handle.
type Engine struct {
	DB  *sql.DB
	URL string
}

// Dispose closes every pooled connection.
func (e *Engine) Dispose() error { return e.DB.Close() }

// tableNames lists the tables of the current schema (Inspector.get_table_names).
func tableNames(ctx context.Context, q interface {
	QueryContext(context.Context, string, ...any) (*sql.Rows, error)
}) ([]string, error) {
	rows, err := q.QueryContext(ctx, "SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema() AND table_type = 'BASE TABLE' ORDER BY table_name")
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []string
	for rows.Next() {
		var n string
		if err := rows.Scan(&n); err != nil {
			return nil, err
		}
		out = append(out, n)
	}
	return out, rows.Err()
}

// columnNames lists a table's columns in ordinal order (Inspector.get_columns).
func columnNames(ctx context.Context, q interface {
	QueryContext(context.Context, string, ...any) (*sql.Rows, error)
}, table string) ([]string, error) {
	rows, err := q.QueryContext(ctx, "SELECT column_name FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = $1 ORDER BY ordinal_position", table)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []string
	for rows.Next() {
		var n string
		if err := rows.Scan(&n); err != nil {
			return nil, err
		}
		out = append(out, n)
	}
	return out, rows.Err()
}

func contains(list []string, s string) bool {
	for _, x := range list {
		if x == s {
			return true
		}
	}
	return false
}
