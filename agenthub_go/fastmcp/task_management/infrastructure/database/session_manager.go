package database

// SQLAlchemy Session Manager (Python database/session_manager.py): session and transaction
// management over database/sql.
//
// A "session" is a transaction on a checked-out connection: it commits when the callback
// succeeds and rolls back when it fails (SQLAlchemy sessions are closed without commit on
// error). Python keeps the active transaction session in thread-local storage; Go carries it
// in the context.Context passed to the callbacks, so nested WithSession/Transaction calls on
// that context reuse the transaction exactly as the thread-local lookup did.

import (
	"context"
	"database/sql"
	"database/sql/driver"
	"errors"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"github.com/jackc/pgx/v5/pgconn"
)

// DBTX is the query surface shared by *sql.Tx and *sql.Conn (the Session counterpart).
type DBTX interface {
	ExecContext(ctx context.Context, query string, args ...any) (sql.Result, error)
	QueryContext(ctx context.Context, query string, args ...any) (*sql.Rows, error)
	QueryRowContext(ctx context.Context, query string, args ...any) *Row
}

// DriverError marks an error raised by a database call itself (statement execution, row
// scanning, begin, commit), the sqlalchemy.exc.SQLAlchemyError counterpart. Errors returned
// by callbacks are never marked, so they propagate unchanged like in Python.
type DriverError struct{ Err error }

func (e *DriverError) Error() string { return e.Err.Error() }
func (e *DriverError) Unwrap() error { return e.Err }

// markDriver marks err as a DriverError. sql.ErrNoRows is a result, not a driver failure.
func markDriver(err error) error {
	if err == nil || errors.Is(err, sql.ErrNoRows) {
		return err
	}
	return &DriverError{Err: err}
}

// Row is *sql.Row whose Scan errors are marked as driver errors.
type Row struct{ row *sql.Row }

func (r *Row) Scan(dest ...any) error { return markDriver(r.row.Scan(dest...)) }
func (r *Row) Err() error             { return markDriver(r.row.Err()) }

// driverDB marks the errors of every call made through it.
type driverDB struct{ db DBTX }

func (d driverDB) ExecContext(ctx context.Context, q string, args ...any) (sql.Result, error) {
	res, err := d.db.ExecContext(ctx, q, args...)
	return res, markDriver(err)
}

func (d driverDB) QueryContext(ctx context.Context, q string, args ...any) (*sql.Rows, error) {
	rows, err := d.db.QueryContext(ctx, q, args...)
	return rows, markDriver(err)
}

func (d driverDB) QueryRowContext(ctx context.Context, q string, args ...any) *Row {
	return d.db.QueryRowContext(ctx, q, args...)
}

// SQLConn is the query surface of *sql.Tx and *sql.Conn.
type SQLConn interface {
	ExecContext(ctx context.Context, query string, args ...any) (sql.Result, error)
	QueryContext(ctx context.Context, query string, args ...any) (*sql.Rows, error)
	QueryRowContext(ctx context.Context, query string, args ...any) *sql.Row
}

type sqlDB struct{ c SQLConn }

func (d sqlDB) ExecContext(ctx context.Context, q string, args ...any) (sql.Result, error) {
	return d.c.ExecContext(ctx, q, args...)
}
func (d sqlDB) QueryContext(ctx context.Context, q string, args ...any) (*sql.Rows, error) {
	return d.c.QueryContext(ctx, q, args...)
}
func (d sqlDB) QueryRowContext(ctx context.Context, q string, args ...any) *Row {
	return &Row{row: d.c.QueryRowContext(ctx, q, args...)}
}

// AsDBTX adapts a *sql.Tx or *sql.Conn to DBTX, marking its driver errors.
func AsDBTX(c SQLConn) DBTX { return driverDB{db: sqlDB{c: c}} }

func sessionDB(tx *sql.Tx) DBTX { return AsDBTX(tx) }

// SessionStats is the session usage statistics.
type SessionStats struct {
	SessionsCreated        int
	SessionsClosed         int
	TransactionsCommitted  int
	TransactionsRolledBack int
	SessionWaitTimeTotal   float64
	SessionCount           int
	SessionErrors          int
}

// GetAvgWaitTime is the average session wait time.
func (s SessionStats) GetAvgWaitTime() float64 {
	if s.SessionCount > 0 {
		return s.SessionWaitTimeTotal / float64(s.SessionCount)
	}
	return 0.0
}

type txKey struct{}

// SessionManager manages sessions and transactions.
type SessionManager struct {
	cfg *DatabaseConfig
	now func() time.Time

	mu    sync.Mutex
	stats SessionStats
}

// NewSessionManager builds a manager over the database configuration.
func NewSessionManager(cfg *DatabaseConfig) *SessionManager {
	return &SessionManager{cfg: cfg, now: time.Now}
}

// IsSQLAlchemyError reports whether err is a database-layer error (SQLAlchemyError), as
// opposed to an application error raised by the callback.
func IsSQLAlchemyError(err error) bool {
	var pg *pgconn.PgError
	var op *OperationalError
	var pt *PoolTimeoutError
	var st *StatementError
	var dr *DriverError
	return errors.As(err, &dr) || errors.As(err, &pg) || errors.As(err, &op) || errors.As(err, &pt) || errors.As(err, &st) ||
		errors.Is(err, sql.ErrTxDone) || errors.Is(err, sql.ErrConnDone) || errors.Is(err, driver.ErrBadConn)
}

func (m *SessionManager) record(f func(*SessionStats)) {
	m.mu.Lock()
	f(&m.stats)
	m.mu.Unlock()
}

// WithSession runs fn in a session. Inside a transaction the transaction session is reused
// and commit/rollback are left to the transaction; otherwise a new session is created,
// committed on success and rolled back on error.
func (m *SessionManager) WithSession(ctx context.Context, fn func(ctx context.Context, s DBTX) error) error {
	if tx, ok := ctx.Value(txKey{}).(*sql.Tx); ok {
		return fn(ctx, sessionDB(tx))
	}
	start := m.now()
	conn, err := m.cfg.GetSession(ctx)
	if err != nil {
		return err
	}
	defer func() {
		m.record(func(s *SessionStats) {
			s.SessionWaitTimeTotal += m.now().Sub(start).Seconds()
			s.SessionsClosed++
		})
		_ = conn.Close()
	}()
	tx, err := conn.BeginTx(ctx, nil)
	if err != nil {
		return markDriver(err)
	}
	m.record(func(s *SessionStats) { s.SessionsCreated++; s.SessionCount++ })

	if err := fn(ctx, sessionDB(tx)); err != nil {
		_ = tx.Rollback()
		if IsSQLAlchemyError(err) {
			m.record(func(s *SessionStats) { s.SessionErrors++; s.TransactionsRolledBack++ })
		}
		return err
	}
	if err := tx.Commit(); err != nil {
		// a commit failure is always a driver error
		m.record(func(s *SessionStats) { s.SessionErrors++; s.TransactionsRolledBack++ })
		return markDriver(err)
	}
	m.record(func(s *SessionStats) { s.TransactionsCommitted++ })
	return nil
}

// Transaction runs fn in one transaction: every WithSession on the context passed to fn shares
// it. A nested Transaction reuses the outer one.
func (m *SessionManager) Transaction(ctx context.Context, fn func(ctx context.Context) error) error {
	if _, ok := ctx.Value(txKey{}).(*sql.Tx); ok {
		return fn(ctx)
	}
	conn, err := m.cfg.GetSession(ctx)
	if err != nil {
		return err
	}
	defer func() {
		m.record(func(s *SessionStats) { s.SessionsClosed++ })
		_ = conn.Close()
	}()
	tx, err := conn.BeginTx(ctx, nil)
	if err != nil {
		return markDriver(err)
	}
	m.record(func(s *SessionStats) { s.SessionsCreated++ })

	if err := fn(context.WithValue(ctx, txKey{}, tx)); err != nil {
		_ = tx.Rollback()
		if IsSQLAlchemyError(err) {
			m.record(func(s *SessionStats) { s.SessionErrors++; s.TransactionsRolledBack++ })
		}
		return err
	}
	if err := tx.Commit(); err != nil {
		// a commit failure is always a driver error
		m.record(func(s *SessionStats) { s.SessionErrors++; s.TransactionsRolledBack++ })
		return markDriver(err)
	}
	m.record(func(s *SessionStats) { s.TransactionsCommitted++ })
	return nil
}

// ExecuteQuery runs queryFunc with a managed session (execute_query).
func ExecuteQuery[T any](ctx context.Context, m *SessionManager, queryFunc func(ctx context.Context, s DBTX) (T, error)) (T, error) {
	var out T
	err := m.WithSession(ctx, func(ctx context.Context, s DBTX) error {
		v, err := queryFunc(ctx, s)
		out = v
		return err
	})
	return out, err
}

// GetStats returns the usage statistics plus the database type and URL.
func (m *SessionManager) GetStats() (*entities.OrderedMap[any], error) {
	m.mu.Lock()
	st := m.stats
	m.mu.Unlock()
	info, err := m.cfg.GetDatabaseInfo()
	if err != nil {
		return nil, err
	}
	out := entities.NewOrderedMap[any]()
	out.Set("sessions_created", st.SessionsCreated)
	out.Set("sessions_closed", st.SessionsClosed)
	out.Set("transactions_committed", st.TransactionsCommitted)
	out.Set("transactions_rolled_back", st.TransactionsRolledBack)
	out.Set("session_errors", st.SessionErrors)
	out.Set("avg_wait_time", st.GetAvgWaitTime())
	out.Set("total_wait_time", st.SessionWaitTimeTotal)
	out.Set("session_count", st.SessionCount)
	typ, _ := info.Get("type")
	out.Set("database_type", typ)
	url, ok := info.Get("url")
	if !ok {
		url = "N/A"
	}
	out.Set("database_url", url)
	return out, nil
}

// ResetStats clears the statistics.
func (m *SessionManager) ResetStats() {
	m.mu.Lock()
	m.stats = SessionStats{}
	m.mu.Unlock()
}

var (
	managerMu     sync.Mutex
	globalManager *SessionManager
)

// GetSessionManager returns the global session manager, creating it on first use.
func GetSessionManager(ctx context.Context, deps Deps) (*SessionManager, error) {
	managerMu.Lock()
	defer managerMu.Unlock()
	if globalManager == nil {
		cfg, err := GetInstance(ctx, deps)
		if err != nil {
			return nil, err
		}
		globalManager = NewSessionManager(cfg)
	}
	return globalManager, nil
}

// CloseSessionManager drops the global session manager.
func CloseSessionManager() {
	managerMu.Lock()
	globalManager = nil
	managerMu.Unlock()
}

// StatementError wraps an error raised while binding statement parameters (sqlalchemy
// StatementError), which Python treats as a SQLAlchemyError.
type StatementError struct{ Err error }

func (e *StatementError) Error() string { return e.Err.Error() }
func (e *StatementError) Unwrap() error { return e.Err }

// IsIntegrityError reports a PostgreSQL integrity constraint violation (SQLSTATE class 23),
// the sqlalchemy.exc.IntegrityError counterpart.
func IsIntegrityError(err error) bool {
	var pg *pgconn.PgError
	return errors.As(err, &pg) && len(pg.Code) >= 2 && pg.Code[:2] == "23"
}
