package database

// Database Connection Retry Logic (Python task_management/infrastructure/database/connection_retry.py).
// Retry/backoff around operations that fail with transient connection errors.

import (
	"context"
	"database/sql"
	"database/sql/driver"
	"errors"
	"fmt"
	"math"
	"math/rand"
	"net"
	"strings"
	"sync"
	"time"
)

// OperationalError mirrors sqlalchemy.exc.OperationalError / psycopg2.OperationalError:
// a driver-level failure that may be transient.
type OperationalError struct{ Msg string }

func (e *OperationalError) Error() string { return e.Msg }

// PoolTimeoutError mirrors sqlalchemy.exc.TimeoutError (pool checkout timed out).
type PoolTimeoutError struct{ Msg string }

func (e *PoolTimeoutError) Error() string { return e.Msg }

// ConnectionRetryConfig is the retry behaviour configuration.
type ConnectionRetryConfig struct {
	MaxRetries      int
	InitialDelay    float64
	MaxDelay        float64
	ExponentialBase float64
	Jitter          bool
}

// NewConnectionRetryConfig returns the Python constructor defaults.
func NewConnectionRetryConfig() ConnectionRetryConfig {
	return ConnectionRetryConfig{MaxRetries: 3, InitialDelay: 1.0, MaxDelay: 30.0, ExponentialBase: 2.0, Jitter: true}
}

// DefaultRetryConfig is DEFAULT_RETRY_CONFIG (more retries for cloud databases).
var DefaultRetryConfig = ConnectionRetryConfig{MaxRetries: 5, InitialDelay: 2.0, MaxDelay: 60.0, ExponentialBase: 2.0, Jitter: true}

var retryableConditions = []string{
	"timeout",
	"connection",
	"could not connect",
	"connection refused",
	"connection reset",
	"broken pipe",
	"server closed the connection",
	"terminating connection",
	"connection dropped",
	"no route to host",
	"network is unreachable",
	"connection timed out",
}

// isOperational reports whether err is one of the driver error kinds Python retries on
// (OperationalError, TimeoutError, psycopg2 OperationalError). Go has no psycopg2, so
// network errors, bad-connection and deadline errors map onto the same category.
func isOperational(err error) bool {
	var op *OperationalError
	var pt *PoolTimeoutError
	var ne net.Error
	return errors.As(err, &op) || errors.As(err, &pt) || errors.As(err, &ne) ||
		errors.Is(err, driver.ErrBadConn) || errors.Is(err, context.DeadlineExceeded)
}

// IsRetryableError reports whether err is a transient connection error.
func IsRetryableError(err error) bool {
	if !isOperational(err) {
		return false
	}
	msg := strings.ToLower(err.Error())
	for _, c := range retryableConditions {
		if strings.Contains(msg, c) {
			return true
		}
	}
	return false
}

// CalculateDelay is the delay in seconds before the next attempt (attempt is 0-indexed).
// random returns a value in [0,1).
func CalculateDelay(attempt int, cfg ConnectionRetryConfig, random func() float64) float64 {
	delay := math.Min(cfg.InitialDelay*math.Pow(cfg.ExponentialBase, float64(attempt)), cfg.MaxDelay)
	if cfg.Jitter {
		delay = delay * (0.5 + random())
	}
	return delay
}

// Sleeper is injectable so tests do not wait.
type Sleeper func(time.Duration)

// WithConnectionRetry runs fn, retrying retryable errors per cfg (decorator with_connection_retry).
func WithConnectionRetry[T any](cfg ConnectionRetryConfig, sleep Sleeper, fn func() (T, error)) (T, error) {
	for attempt := 0; attempt <= cfg.MaxRetries; attempt++ {
		v, err := fn()
		if err == nil {
			return v, nil
		}
		if !IsRetryableError(err) || attempt >= cfg.MaxRetries {
			return v, err
		}
		sleep(time.Duration(CalculateDelay(attempt, cfg, rand.Float64) * float64(time.Second)))
	}
	var zero T
	return zero, fmt.Errorf("Unexpected state in retry logic")
}

// ConnectionPool is the enhanced pool wrapper with retry logic and cached health checks.
type ConnectionPool struct {
	DB          *sql.DB
	RetryConfig ConnectionRetryConfig

	mu                  sync.Mutex
	healthy             bool
	lastHealthCheck     time.Time
	healthCheckInterval time.Duration
	now                 func() time.Time
	sleep               Sleeper
}

// NewConnectionPool wraps db; a zero cfg selects the defaults.
func NewConnectionPool(db *sql.DB, cfg *ConnectionRetryConfig) *ConnectionPool {
	rc := NewConnectionRetryConfig()
	if cfg != nil {
		rc = *cfg
	}
	return &ConnectionPool{DB: db, RetryConfig: rc, healthy: true, healthCheckInterval: 30 * time.Second, now: time.Now, sleep: time.Sleep}
}

// GetConnection checks a connection out of the pool with retry logic.
func (p *ConnectionPool) GetConnection(ctx context.Context) (*sql.Conn, error) {
	return WithConnectionRetry(NewConnectionRetryConfig(), p.sleep, func() (*sql.Conn, error) { return p.DB.Conn(ctx) })
}

// IsHealthy returns the cached health, re-checking when the interval has elapsed.
// Python's check ran `conn.execute("SELECT 1")` with a bare string, which SQLAlchemy 2.0
// rejects, so the check always reported unhealthy; that behaviour is kept.
func (p *ConnectionPool) IsHealthy(ctx context.Context) bool {
	p.mu.Lock()
	defer p.mu.Unlock()
	current := p.now()
	if !p.lastHealthCheck.IsZero() && current.Sub(p.lastHealthCheck) < p.healthCheckInterval {
		return p.healthy
	}
	conn, err := p.GetConnection(ctx)
	if err == nil {
		_ = conn.Close()
	}
	p.healthy = false
	p.lastHealthCheck = current
	return p.healthy
}

// Reset disposes the pooled connections.
func (p *ConnectionPool) Reset() {
	if err := p.DB.Close(); err != nil {
		p.healthy = false
		return
	}
	p.healthy = true
}

// ResilientPoolOptions are the pool settings of create_resilient_engine.
type ResilientPoolOptions struct {
	MaxOpen     int
	MaxIdle     int
	ConnMaxLife time.Duration
}

// ResilientDefaults mirrors resilient_defaults (pool_size 3 + max_overflow 5, recycle 180s).
// Python also force-reconnects connections older than 30 minutes at checkout; the recycle
// of 180s makes that unreachable, so it is not ported.
func ResilientDefaults() ResilientPoolOptions {
	return ResilientPoolOptions{MaxOpen: 3 + 5, MaxIdle: 3, ConnMaxLife: 180 * time.Second}
}

// CreateResilientDB opens a database/sql pool with the resilient settings.
func CreateResilientDB(driverName, dsn string, o ResilientPoolOptions) (*sql.DB, error) {
	db, err := sql.Open(driverName, dsn)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(o.MaxOpen)
	db.SetMaxIdleConns(o.MaxIdle)
	db.SetConnMaxLifetime(o.ConnMaxLife)
	return db, nil
}
