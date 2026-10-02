package database

// Supabase Database Configuration (Python database/supabase_config.py).

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"

	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/utilities"
)

// Deps are the injectable collaborators of the database configuration objects.
type Deps struct {
	Getenv Getenv
	Open   Opener
	Sleep  Sleeper
	Exists func(string) bool
	Abs    func(string) (string, error)
}

// OSDeps wires the real environment, filesystem and the pgx opener.
func OSDeps() Deps {
	return Deps{
		Getenv: os.LookupEnv,
		Open:   PgxOpener,
		Sleep:  sleepReal,
		Exists: func(p string) bool { _, err := os.Stat(p); return err == nil },
		Abs:    filepath.Abs,
	}
}

var (
	supabaseRefRe = regexp.MustCompile(`^https://([a-zA-Z0-9]+)\.supabase\.co`)
	ipv4Re        = regexp.MustCompile(`[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+`)
)

// SupabaseConfig manages the Supabase PostgreSQL connection.
type SupabaseConfig struct {
	SupabaseURL            string
	SupabaseAnonKey        string
	SupabaseServiceRoleKey string
	SupabaseJWTSecret      string
	DatabaseURL            string
	Engine                 *Engine

	deps Deps
}

// NewSupabaseConfig reads the environment, builds the URL, creates the engine and tests the
// connection, returning the first error (Python raises).
func NewSupabaseConfig(ctx context.Context, deps Deps) (*SupabaseConfig, error) {
	c := &SupabaseConfig{
		SupabaseURL:            deps.Getenv.get("SUPABASE_URL", ""),
		SupabaseAnonKey:        deps.Getenv.get("SUPABASE_ANON_KEY", ""),
		SupabaseServiceRoleKey: deps.Getenv.get("SUPABASE_SERVICE_ROLE_KEY", ""),
		SupabaseJWTSecret:      deps.Getenv.get("SUPABASE_JWT_SECRET", ""),
		deps:                   deps,
	}
	url, err := c.supabaseDatabaseURL()
	if err != nil {
		return nil, err
	}
	c.DatabaseURL = url
	if err := c.initializeDatabase(ctx); err != nil {
		return nil, err
	}
	return c, nil
}

// supabaseDatabaseURL resolves the connection URL: SUPABASE_DATABASE_URL, then a Supabase
// DATABASE_URL, then a URL constructed from the SUPABASE_* variables.
func (c *SupabaseConfig) supabaseDatabaseURL() (string, error) {
	g := c.deps.Getenv
	if v := g.get("SUPABASE_DATABASE_URL", ""); v != "" {
		return v, nil
	}
	databaseURL := g.get("DATABASE_URL", "")
	if databaseURL != "" && (strings.Contains(strings.ToLower(databaseURL), "supabase") || strings.Contains(databaseURL, "PLACEHOLDER_SUPABASE_REF")) {
		return databaseURL, nil
	}
	if c.SupabaseURL != "" {
		if m := supabaseRefRe.FindStringSubmatch(c.SupabaseURL); m != nil {
			ref := m[1]
			password := g.get("SUPABASE_DB_PASSWORD", "")
			if password == "" {
				return "", &tmvo.ValueError{Msg: "SUPABASE_DB_PASSWORD environment variable is required"}
			}
			user := g.get("SUPABASE_DB_USER", "postgres")
			host := g.get("SUPABASE_DB_HOST", "db."+ref+".supabase.co")
			port := g.get("SUPABASE_DB_PORT", "5432")
			name := g.get("SUPABASE_DB_NAME", "postgres")
			url := fmt.Sprintf("postgresql://%s:%s@%s:%s/%s", user, utilities.PyQuote(password), host, port, name)
			if ipv4Re.MatchString(c.SupabaseURL) {
				url += "?sslmode=prefer"
			} else {
				certEnv := g.get("SUPABASE_SSL_CERT_PATH", "prod-ca-2021.crt")
				certPath, err := c.deps.Abs(certEnv)
				if err != nil {
					return "", err
				}
				if c.deps.Exists(certPath) {
					url += "?sslmode=require&sslrootcert=" + certPath
				} else {
					url += "?sslmode=require"
				}
			}
			return url, nil
		}
	}
	set := func(v string) string {
		if v != "" {
			return "SET"
		}
		return "NOT SET"
	}
	return "", &tmvo.ValueError{Msg: "🚫 SUPABASE CONFIGURATION MISSING! 🚫\n" +
		"Required: One of the following configurations:\n" +
		"1. SUPABASE_DATABASE_URL=postgresql://postgres:password@db.project.supabase.co:5432/postgres\n" +
		"2. DATABASE_URL with Supabase connection string\n" +
		"3. Individual Supabase variables: SUPABASE_URL, SUPABASE_DB_PASSWORD, etc.\n" +
		"Current SUPABASE_URL: " + set(c.SupabaseURL) + "\n" +
		"Current DATABASE_URL: " + set(databaseURL)}
}

// engineOptions are the create_resilient_engine arguments of the Supabase engine.
func (c *SupabaseConfig) engineOptions() EngineOptions {
	o := EngineOptions{
		PoolSize: 2, MaxOverflow: 3, PoolTimeout: 120, PoolRecycle: 120, PoolPrePing: true,
		Echo: strings.ToLower(c.deps.Getenv.get("SQL_DEBUG", "false")) == "true",
		AfterConnect: []ConnectStatement{
			{SQL: "SET search_path TO public"},
			{SQL: "SET statement_timeout = '60s'"},
			{SQL: "SET lock_timeout = '30s'"},
			{SQL: "SET auto_explain.log_min_duration = '1s'", Optional: true},
		},
	}
	if strings.Contains(c.DatabaseURL, "supabase") {
		o.ConnectArgs = [][2]string{
			{"connect_timeout", "60"},
			{"application_name", "agenthub"},
			{"keepalives", "1"},
			{"keepalives_idle", "15"},
			{"keepalives_interval", "3"},
			{"keepalives_count", "15"},
			{"tcp_user_timeout", "60000"},
			{"options", "-c statement_timeout=120000 -c idle_in_transaction_session_timeout=90000"},
		}
	}
	return o
}

func (c *SupabaseConfig) initializeDatabase(ctx context.Context) error {
	if c.DatabaseURL == "" {
		return &tmvo.ValueError{Msg: "Database URL not configured. Please set SUPABASE_URL or DATABASE_URL"}
	}
	db, err := c.deps.Open(c.DatabaseURL, c.engineOptions())
	if err != nil {
		return err
	}
	c.Engine = &Engine{DB: db, URL: c.DatabaseURL}
	var version, dbName string
	if err := db.QueryRowContext(ctx, "SELECT version()").Scan(&version); err != nil {
		return err
	}
	return db.QueryRowContext(ctx, "SELECT current_database()").Scan(&dbName)
}

// GetSession checks out a connection and verifies it with SELECT 1, retrying transient errors.
func (c *SupabaseConfig) GetSession(ctx context.Context) (*sql.Conn, error) {
	if c.Engine == nil {
		return nil, fmt.Errorf("Database not initialized")
	}
	return WithConnectionRetry(DefaultRetryConfig, c.deps.Sleep, func() (*sql.Conn, error) {
		conn, err := c.Engine.DB.Conn(ctx)
		if err != nil {
			return nil, err
		}
		if _, err := conn.ExecContext(ctx, "SELECT 1"); err != nil {
			_ = conn.Close()
			return nil, err
		}
		return conn, nil
	})
}

// Dispose closes every pooled connection.
func (c *SupabaseConfig) Dispose() {
	if c.Engine != nil {
		_ = c.Engine.Dispose()
	}
}

var (
	supabaseMu       sync.Mutex
	supabaseInstance *SupabaseConfig
)

// GetSupabaseConfig returns the process-wide Supabase configuration, creating it on first use.
func GetSupabaseConfig(ctx context.Context, deps Deps) (*SupabaseConfig, error) {
	supabaseMu.Lock()
	defer supabaseMu.Unlock()
	if supabaseInstance == nil {
		c, err := NewSupabaseConfig(ctx, deps)
		if err != nil {
			return nil, err
		}
		supabaseInstance = c
	}
	return supabaseInstance, nil
}

// IsSupabaseConfigured reports whether the Supabase variables are present.
func IsSupabaseConfigured(g Getenv) bool {
	has := func(k string) bool { return g.get(k, "") != "" }
	return has("SUPABASE_URL") && has("SUPABASE_ANON_KEY") && (has("DATABASE_URL") || has("SUPABASE_DB_PASSWORD"))
}
