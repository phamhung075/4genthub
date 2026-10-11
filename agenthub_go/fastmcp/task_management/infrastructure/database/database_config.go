package database

// Database Configuration (Python database/database_config.py): PostgreSQL / Supabase
// configuration, engine creation, connection verification and session checkout.
//
// Deviations from Python: there is no SQLAlchemy Session/scoped_session; GetSession returns a
// verified *sql.Conn (thread-local sessions have no Go meaning). Python's get_db_config calls
// sys.exit(1) when initialisation fails; here the error is returned and the caller decides.
// The .env/.env.dev loading at import time belongs to process start-up, not this package.

import (
	"context"
	"database/sql"
	"fmt"
	"strings"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/utilities"
)

// DatabaseConfig is the singleton database configuration manager.
type DatabaseConfig struct {
	DatabaseType string
	DatabaseURL  string
	Engine       *Engine

	deps Deps
}

var (
	cfgMu              sync.Mutex
	cfgInstance        *DatabaseConfig
	connectionVerified bool
	connectionInfo     string
)

// GetInstance returns the singleton, creating and initialising it on first use.
func GetInstance(ctx context.Context, deps Deps) (*DatabaseConfig, error) {
	cfgMu.Lock()
	defer cfgMu.Unlock()
	return getInstanceLocked(ctx, deps)
}

func getInstanceLocked(ctx context.Context, deps Deps) (*DatabaseConfig, error) {
	if cfgInstance != nil {
		return cfgInstance, nil
	}
	c, err := newDatabaseConfig(ctx, deps)
	if err != nil {
		return nil, err
	}
	cfgInstance = c
	return c, nil
}

// ResetInstance clears the singleton state (testing aid), closing the current instance.
func ResetInstance() {
	cfgMu.Lock()
	defer cfgMu.Unlock()
	resetLocked()
}

func resetLocked() {
	if cfgInstance != nil {
		cfgInstance.Close()
	}
	cfgInstance = nil
	connectionVerified = false
	connectionInfo = ""
}

func newDatabaseConfig(ctx context.Context, deps Deps) (*DatabaseConfig, error) {
	c := &DatabaseConfig{deps: deps}
	dbType, ok := deps.Getenv("DATABASE_TYPE")
	if !ok || dbType == "" {
		return nil, &tmvo.ValueError{Msg: "❌ DATABASE_TYPE environment variable is NOT configured!\n" +
			"The server cannot start without explicit database configuration.\n" +
			"Please set DATABASE_TYPE in your .env or .env.dev file:\n" +
			"  - DATABASE_TYPE=postgresql (for production)\n" +
			"  - DATABASE_TYPE=supabase (for cloud deployment)\n" +
			"\nNo fallback will be used - configuration is required!"}
	}
	c.DatabaseType = tmvo.PyLower(dbType)
	if c.DatabaseType != "postgresql" && c.DatabaseType != "supabase" {
		return nil, &tmvo.ValueError{Msg: "Invalid DATABASE_TYPE: " + c.DatabaseType + "\nSupported types: 'postgresql' or 'supabase'"}
	}
	c.DatabaseURL = c.secureDatabaseURL()
	if c.DatabaseURL == "" {
		required := "SUPABASE_DB_HOST, SUPABASE_DB_PASSWORD"
		if c.DatabaseType == "postgresql" {
			required = "DATABASE_HOST, DATABASE_USER, DATABASE_PASSWORD"
		}
		return nil, &tmvo.ValueError{Msg: "Database configuration missing for " + c.DatabaseType + ".\nRequired environment variables:\n" + required}
	}
	if err := c.initializeDatabase(ctx); err != nil {
		return nil, err
	}
	return c, nil
}

// secureDatabaseURL builds the URL from the individual DATABASE_* / SUPABASE_DB_* variables;
// "" means not configured.
func (c *DatabaseConfig) secureDatabaseURL() string {
	g := c.deps.Getenv
	switch c.DatabaseType {
	case "postgresql":
		host := g.get("DATABASE_HOST", "")
		port := g.get("DATABASE_PORT", "5432")
		name := g.get("DATABASE_NAME", "agenthub")
		user := g.get("DATABASE_USER", "postgres")
		password := g.get("DATABASE_PASSWORD", "")
		sslMode := g.get("DATABASE_SSL_MODE", "prefer")
		if host == "" || user == "" || password == "" {
			return ""
		}
		url := fmt.Sprintf("postgresql://%s:%s@%s:%s/%s", user, utilities.PyQuote(password), host, port, name)
		if sslMode != "" && sslMode != "disable" {
			url += "?sslmode=" + sslMode
		}
		return url
	case "supabase":
		host := g.get("SUPABASE_DB_HOST", "")
		port := g.get("SUPABASE_DB_PORT", "5432")
		name := g.get("SUPABASE_DB_NAME", "postgres")
		user := g.get("SUPABASE_DB_USER", "postgres")
		password := g.get("SUPABASE_DB_PASSWORD", "")
		if host == "" || password == "" {
			return ""
		}
		return fmt.Sprintf("postgresql://%s:%s@%s:%s/%s?sslmode=require", user, utilities.PyQuote(password), host, port, name)
	}
	return ""
}

// IsDatabaseConfigured reports whether the environment carries what newDatabaseConfig requires,
// WITHOUT connecting: a supported DATABASE_TYPE and then a non-empty secureDatabaseURL() for it.
//
// It exists so the health surfaces report the gate the server actually starts up with. The flag
// they used to compute tested SUPABASE_URL and DATABASE_URL, and this code uses neither for the
// connection (SUPABASE_URL is the auth variable), so a deployment configured the supported way
// reported database_configured:false while the database worked.
func IsDatabaseConfigured(getenv Getenv) bool {
	dbType := tmvo.PyLower(getenv.get("DATABASE_TYPE", ""))
	if dbType != "postgresql" && dbType != "supabase" {
		return false
	}
	c := &DatabaseConfig{DatabaseType: dbType, deps: Deps{Getenv: getenv}}
	return c.secureDatabaseURL() != ""
}

// resolveDatabaseURL is _get_database_url: Supabase delegates to supabase_config.
func (c *DatabaseConfig) resolveDatabaseURL(ctx context.Context) (string, error) {
	switch c.DatabaseType {
	case "supabase":
		if !IsSupabaseConfigured(c.deps.Getenv) {
			return "", &tmvo.ValueError{Msg: "SUPABASE NOT PROPERLY CONFIGURED!\n" +
				"Required environment variables:\n" +
				"✅ SUPABASE_URL (your project URL)\n" +
				"✅ SUPABASE_ANON_KEY (from Supabase dashboard)\n" +
				"✅ SUPABASE_DATABASE_URL (direct connection string)\n" +
				"OR set SUPABASE_DB_PASSWORD with project credentials\n" +
				"🔧 Check your .env file and ensure all Supabase variables are set."}
		}
		sc, err := GetSupabaseConfig(ctx, c.deps)
		if err != nil {
			return "", err
		}
		return sc.DatabaseURL, nil
	case "postgresql":
		return c.DatabaseURL, nil
	}
	return "", &tmvo.ValueError{Msg: "Unsupported database type: " + c.DatabaseType}
}

func envInt(g Getenv, key, def string) (int, error) {
	raw := g.get(key, def)
	n, ok := tmvo.PyParseInt(raw)
	if !ok || !n.IsInt64() {
		return 0, &tmvo.ValueError{Msg: "invalid literal for int() with base 10: " + tmvo.PyRepr(raw)}
	}
	return int(n.Int64()), nil
}

// createEngine is _create_engine: validates the URL and applies the pool/connect settings.
func (c *DatabaseConfig) createEngine(url string) (*Engine, error) {
	if !strings.HasPrefix(url, "postgresql") {
		prefix := url
		if len(prefix) > 20 {
			prefix = prefix[:20]
		}
		return nil, &tmvo.ValueError{Msg: "Invalid database URL. Expected PostgreSQL URL but got: " + prefix + "..."}
	}
	g := c.deps.Getenv
	var o EngineOptions
	ints := []struct {
		dst      *int
		key, def string
	}{
		{&o.PoolSize, "DATABASE_POOL_SIZE", "50"},
		{&o.MaxOverflow, "DATABASE_MAX_OVERFLOW", "100"},
		{&o.PoolTimeout, "DATABASE_POOL_TIMEOUT", "60"},
		{&o.PoolRecycle, "DATABASE_POOL_RECYCLE", "1800"},
	}
	for _, i := range ints {
		n, err := envInt(g, i.key, i.def)
		if err != nil {
			return nil, err
		}
		*i.dst = n
	}
	switch strings.ToLower(g.get("DATABASE_POOL_PRE_PING", "true")) {
	case "true", "1", "yes":
		o.PoolPrePing = true
	}
	o.Echo = strings.ToLower(g.get("SQL_DEBUG", "false")) == "true"

	connectArgs := []struct{ key, env, def string }{
		{"connect_timeout", "DATABASE_CONNECT_TIMEOUT", "30"},
		{"application_name", "DATABASE_APPLICATION_NAME", "agenthub"},
		{"options", "DATABASE_OPTIONS", "-c timezone=UTC"},
		{"keepalives", "DATABASE_KEEPALIVES", "1"},
		{"keepalives_idle", "DATABASE_KEEPALIVES_IDLE", "30"},
		{"keepalives_interval", "DATABASE_KEEPALIVES_INTERVAL", "10"},
		{"keepalives_count", "DATABASE_KEEPALIVES_COUNT", "5"},
	}
	for _, a := range connectArgs {
		v := g.get(a.env, a.def)
		if a.key != "application_name" && a.key != "options" {
			n, err := envInt(g, a.env, a.def)
			if err != nil {
				return nil, err
			}
			v = fmt.Sprint(n)
		}
		o.ConnectArgs = append(o.ConnectArgs, [2]string{a.key, v})
	}
	o.AfterConnect = []ConnectStatement{
		{SQL: "SET search_path TO public"},
		{SQL: fmt.Sprintf("SET statement_timeout = '%ss'", g.get("DATABASE_STATEMENT_TIMEOUT", "60"))},
		{SQL: fmt.Sprintf("SET lock_timeout = '%ss'", g.get("DATABASE_LOCK_TIMEOUT", "30"))},
		{SQL: "SET tcp_keepalives_idle = " + g.get("DATABASE_TCP_KEEPALIVES_IDLE", "600")},
		{SQL: "SET tcp_keepalives_interval = " + g.get("DATABASE_TCP_KEEPALIVES_INTERVAL", "30")},
		{SQL: "SET tcp_keepalives_count = " + g.get("DATABASE_TCP_KEEPALIVES_COUNT", "3")},
	}
	db, err := c.deps.Open(url, o)
	if err != nil {
		return nil, err
	}
	return &Engine{DB: db, URL: url}, nil
}

// testConnection verifies the connection with retry logic and records the connection info.
func (c *DatabaseConfig) testConnection(ctx context.Context, url string) error {
	_, err := WithConnectionRetry(DefaultRetryConfig, c.deps.Sleep, func() (struct{}, error) {
		var version string
		if err := c.Engine.DB.QueryRowContext(ctx, "SELECT version()").Scan(&version); err != nil {
			return struct{}{}, err
		}
		if url != "" && strings.Contains(strings.ToLower(url), "supabase") {
			var dbName string
			if err := c.Engine.DB.QueryRowContext(ctx, "SELECT current_database()").Scan(&dbName); err != nil {
				return struct{}{}, err
			}
			connectionInfo = "Supabase PostgreSQL - Database: " + dbName
		} else {
			connectionInfo = "PostgreSQL " + version
		}
		return struct{}{}, nil
	})
	return err
}

func (c *DatabaseConfig) initializeDatabase(ctx context.Context) error {
	url, err := c.resolveDatabaseURL(ctx)
	if err != nil {
		return err
	}
	engine, err := c.createEngine(url)
	if err != nil {
		return err
	}
	c.Engine = engine
	if !connectionVerified {
		if err := c.testConnection(ctx, url); err != nil {
			return err
		}
		EnsureAIColumnsExist(ctx, c.Engine.DB)
		connectionVerified = true
	}
	return nil
}

// GetSession checks out a connection and verifies it with SELECT 1, with retry logic.
func (c *DatabaseConfig) GetSession(ctx context.Context) (*sql.Conn, error) {
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

// GetEngine returns the engine, or an error when the database is not initialised.
func (c *DatabaseConfig) GetEngine() (*Engine, error) {
	if c.Engine == nil {
		return nil, fmt.Errorf("Database not initialized")
	}
	return c.Engine, nil
}

// Close closes the pooled connections.
func (c *DatabaseConfig) Close() {
	if c.Engine != nil {
		_ = c.Engine.Dispose()
	}
}

// GetDatabaseInfo describes the current configuration (pool stats from sql.DBStats).
func (c *DatabaseConfig) GetDatabaseInfo() (*entities.OrderedMap[any], error) {
	pool := entities.NewOrderedMap[any]()
	if c.Engine != nil {
		st := c.Engine.DB.Stats()
		pool.Set("size", st.MaxOpenConnections)
		pool.Set("checked_in", st.Idle)
		pool.Set("checked_out", st.InUse)
		pool.Set("total", st.Idle+st.InUse)
	}
	size, err := envInt(c.deps.Getenv, "DATABASE_POOL_SIZE", "50")
	if err != nil {
		return nil, err
	}
	overflow, err := envInt(c.deps.Getenv, "DATABASE_MAX_OVERFLOW", "100")
	if err != nil {
		return nil, err
	}
	info := entities.NewOrderedMap[any]()
	info.Set("type", c.DatabaseType)
	if c.DatabaseType == "postgresql" {
		info.Set("url", c.DatabaseURL)
	} else {
		info.Set("url", nil)
	}
	if c.Engine != nil {
		info.Set("engine", c.Engine.URL)
	} else {
		info.Set("engine", nil)
	}
	info.Set("pool", pool)
	info.Set("configured_pool_size", size)
	info.Set("configured_max_overflow", overflow)
	return info, nil
}

// GetSession is the module-level session getter: three attempts, resetting the pool between
// attempts with exponential backoff, then a DatabaseException.
func GetSession(ctx context.Context, deps Deps) (*sql.Conn, error) {
	const maxAttempts = 3
	var lastErr error
	for attempt := 0; attempt < maxAttempts; attempt++ {
		cfg, err := GetInstance(ctx, deps)
		if err == nil {
			var conn *sql.Conn
			if conn, err = cfg.GetSession(ctx); err == nil {
				return conn, nil
			}
		}
		lastErr = err
		if attempt < maxAttempts-1 {
			cfgMu.Lock()
			if cfgInstance != nil && cfgInstance.Engine != nil {
				_ = cfgInstance.Engine.Dispose()
				_ = cfgInstance.initializeDatabase(ctx)
			}
			cfgMu.Unlock()
			deps.Sleep(time.Duration(1<<attempt) * time.Second)
		}
	}
	return nil, exceptions.NewDatabaseException(
		fmt.Sprintf("Database session unavailable after %d attempts: %v", maxAttempts, lastErr), "get_session", "N/A")
}

// CloseDB closes the connections and resets the singleton.
func CloseDB() { ResetInstance() }

// createAll is Base.metadata.create_all(checkfirst=True): enum types and tables that do not
// exist yet are created in dependency order, with each table's indexes.
func createAll(ctx context.Context, db *sql.DB) error {
	existing, err := tableNames(ctx, db)
	if err != nil {
		return err
	}
	for _, t := range Tables {
		if contains(existing, t.Name) {
			continue
		}
		for _, c := range t.Columns {
			if c.EnumName == "" {
				continue
			}
			var one int
			err := db.QueryRowContext(ctx, "SELECT 1 FROM pg_type WHERE typname = $1", c.EnumName).Scan(&one)
			if err == sql.ErrNoRows {
				labels := make([]string, len(EnumTypes[c.EnumName]))
				for i, l := range EnumTypes[c.EnumName] {
					labels[i] = "'" + strings.ReplaceAll(l, "'", "''") + "'"
				}
				if _, err := db.ExecContext(ctx, fmt.Sprintf("CREATE TYPE %s AS ENUM (%s)", c.EnumName, strings.Join(labels, ", "))); err != nil {
					return err
				}
			} else if err != nil {
				return err
			}
		}
		for _, stmt := range t.DDL {
			if _, err := db.ExecContext(ctx, stmt); err != nil {
				return err
			}
		}
	}
	return nil
}

// CreateTables creates every table, re-checks the critical context tables once, and ensures the
// AI columns exist (DatabaseConfig.create_tables).
func (c *DatabaseConfig) CreateTables(ctx context.Context) error {
	if c.Engine == nil {
		return fmt.Errorf("Database not initialized")
	}
	if err := createAll(ctx, c.Engine.DB); err != nil {
		return err
	}
	critical := []string{"branch_contexts", "task_contexts", "project_contexts", "global_contexts"}
	existing, err := tableNames(ctx, c.Engine.DB)
	if err != nil {
		return err
	}
	for _, name := range critical {
		if !contains(existing, name) {
			// Python forces one more create_all(checkfirst=True) when context tables are missing.
			if err := createAll(ctx, c.Engine.DB); err != nil {
				return err
			}
			break
		}
	}
	EnsureAIColumnsExist(ctx, c.Engine.DB)
	if err := RunColumnEnsurers(ctx, c.Engine.DB); err != nil {
		return err
	}
	// The embedded migrations run LAST, against the schema createAll and the ensurers have left: a
	// step that creates or alters a registered table needs createAll to have run, and one that builds
	// on an ensurer's column needs the ensurer to have run. Every step and its ledger row commit
	// together (migration_runner.go), so a failure leaves the record of what did run.
	set, err := LoadMigrations()
	if err != nil {
		return err
	}
	_, err = (&Runner{Sessions: NewSessionManager(c), Set: set}).Apply(ctx)
	return err
}
