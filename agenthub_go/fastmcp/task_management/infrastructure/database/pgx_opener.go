package database

// PgxOpener is the production Opener: database/sql over the pgx stdlib driver. It replaces
// SQLAlchemy's create_engine + psycopg2. pgx has no libpq keepalives_* parameters (TCP
// keepalives are on by default in its dialer) so those connect args are not forwarded.

import (
	"context"
	"database/sql"
	"strconv"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/stdlib"
)

func sleepReal(d time.Duration) { time.Sleep(d) }

// PgxOpener builds the pool: pool_size+max_overflow connections, recycle, and the
// per-connection statements.
func PgxOpener(url string, o EngineOptions) (*sql.DB, error) {
	cfg, err := pgx.ParseConfig(url)
	if err != nil {
		return nil, err
	}
	for _, kv := range o.ConnectArgs {
		switch kv[0] {
		case "connect_timeout":
			if n, err := strconv.Atoi(kv[1]); err == nil {
				cfg.ConnectTimeout = time.Duration(n) * time.Second
			}
		case "application_name", "options":
			cfg.RuntimeParams[kv[0]] = kv[1]
		}
	}
	stmts := o.AfterConnect
	db := stdlib.OpenDB(*cfg, stdlib.OptionAfterConnect(func(ctx context.Context, c *pgx.Conn) error {
		for _, s := range stmts {
			if _, err := c.Exec(ctx, s.SQL); err != nil && !s.Optional {
				return err
			}
		}
		return nil
	}))
	db.SetMaxOpenConns(o.PoolSize + o.MaxOverflow)
	db.SetMaxIdleConns(o.PoolSize)
	db.SetConnMaxLifetime(time.Duration(o.PoolRecycle) * time.Second)
	return db, nil
}
