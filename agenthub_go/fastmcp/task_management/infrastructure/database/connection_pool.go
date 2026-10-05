package database

// Connection Pool Management (Python
// task_management/infrastructure/database/connection_pool.py).
//
// Only the Supabase/PostgreSQL pool is ported: the SQLite pool is SQLite-only and has no
// Go counterpart. The Python keyword pool_config overrides and the SQLAlchemy QueuePool
// are not modelled; the defaults are applied through the injected Opener. get_pool_status
// reports the same key set, with Go's database/sql statistics standing in for QueuePool.

import (
	"context"
	"strings"
	"sync"

	"agenthub/fastmcp/task_management/domain/entities"
)

// SupabaseConnectionPool is the optimized pool for a Supabase cloud database.
type SupabaseConnectionPool struct {
	DatabaseURL string
	Engine      *Engine
	PoolSize    int
	MaxOverflow int
}

// NewSupabaseConnectionPool opens the pool with the Python default pool settings
// (pool_size=3, max_overflow=7, pre_ping, recycle 300s, timeout 10s, connect_timeout=5,
// options="-c statement_timeout=15000").
func NewSupabaseConnectionPool(deps Deps, databaseURL string) (*SupabaseConnectionPool, error) {
	opts := EngineOptions{
		PoolSize:    3,
		MaxOverflow: 7,
		PoolPrePing: true,
		PoolRecycle: 300,
		PoolTimeout: 10,
		ConnectArgs: [][2]string{
			{"connect_timeout", "5"},
			{"options", "-c statement_timeout=15000"},
		},
	}
	db, err := deps.Open(databaseURL, opts)
	if err != nil {
		return nil, err
	}
	return &SupabaseConnectionPool{
		DatabaseURL: databaseURL,
		Engine:      &Engine{DB: db, URL: databaseURL},
		PoolSize:    3,
		MaxOverflow: 7,
	}, nil
}

// WithSession checks a connection out and hands it to fn, closing it afterwards. Unlike a
// SQLAlchemy Session there is no enclosing transaction; the callback owns commit/rollback.
func (p *SupabaseConnectionPool) WithSession(ctx context.Context, fn func(DBTX) error) error {
	conn, err := p.Engine.DB.Conn(ctx)
	if err != nil {
		return err
	}
	defer conn.Close()
	return fn(AsDBTX(conn))
}

// GetPoolStatus returns the current pool statistics in the Python key order.
func (p *SupabaseConnectionPool) GetPoolStatus() *entities.OrderedMap[any] {
	st := p.Engine.DB.Stats()
	total := st.Idle + st.InUse
	overflow := total - p.PoolSize
	if overflow < 0 {
		overflow = 0
	}
	out := entities.NewOrderedMap[any]()
	out.Set("size", p.PoolSize)
	out.Set("checked_in", st.Idle)
	out.Set("checked_out", st.InUse)
	out.Set("overflow", overflow)
	out.Set("total", total)
	out.Set("class", "QueuePool")
	return out
}

// Close disposes every pooled connection.
func (p *SupabaseConnectionPool) Close() {
	_ = p.Engine.Dispose()
}

var (
	supabasePoolMu       sync.Mutex
	supabasePoolInstance *SupabaseConnectionPool
)

// GetSupabasePool returns the singleton Supabase pool, creating it when the URL mentions
// "supabase". A nil pool means no Supabase URL is configured.
func GetSupabasePool(deps Deps, databaseURL string) (*SupabaseConnectionPool, error) {
	supabasePoolMu.Lock()
	defer supabasePoolMu.Unlock()
	if supabasePoolInstance != nil {
		return supabasePoolInstance, nil
	}
	if databaseURL == "" {
		databaseURL = deps.Getenv.get("SUPABASE_DATABASE_URL", "")
		if databaseURL == "" {
			databaseURL = deps.Getenv.get("DATABASE_URL", "")
		}
	}
	if databaseURL != "" && strings.Contains(strings.ToLower(databaseURL), "supabase") {
		pool, err := NewSupabaseConnectionPool(deps, databaseURL)
		if err != nil {
			return nil, err
		}
		supabasePoolInstance = pool
	}
	return supabasePoolInstance, nil
}

// CloseSupabasePool closes and drops the singleton.
func CloseSupabasePool() {
	supabasePoolMu.Lock()
	defer supabasePoolMu.Unlock()
	if supabasePoolInstance != nil {
		supabasePoolInstance.Close()
		supabasePoolInstance = nil
	}
}
